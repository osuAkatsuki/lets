import io
import requests
import datetime
import time
import traceback
from datetime import date
from collections import OrderedDict
from math import ceil
from sys import exc_info
from typing import List
from typing import Optional
from urllib.parse import urlencode

import orjson
import tornado.gen
import tornado.web

import secret.achievements.utils
from common.constants import gameModes
from common.constants import mods
from common.constants import akatsukiModes as akatsuki
from common.constants import osuFlags as osu_flags
from common.log import logUtils as log
from common.ripple import userUtils
from common.ripple import scoreUtils
from common.web import requestsManager
from constants import exceptions
from constants import rankedStatuses
from constants.exceptions import ppCalcException
from helpers import aeshelper
from helpers import leaderboardHelper
from objects import beatmap
from objects import glob
from objects import score
from objects import scoreboard
from helpers.generalHelper import zingonify
from objects.charts import BeatmapChart, OverallChart
from common import generalUtils

MODULE_NAME = 'submit_modular'
class handler(requestsManager.asyncRequestHandler):
    '''
    Handler for /web/osu-submit-modular.php
    '''
    @tornado.web.asynchronous
    @tornado.gen.engine
    #@sentry.captureTornado
    def asyncPost(self, endpoint: str) -> None:
        start_time = time.perf_counter()

        # Akatsuki's score-submission anti-cheat for custom clients.
        _cc_flags        = 0 # Base flag, nothing unusual detected.
        _cc_invalid_url  = 1 << 0 # Requested to osu-submit-modular.php rather than newer osu-submit-modular-selector.php
        _cc_args_missing = 1 << 1 # Required args were not sent (probably "ft" and "x")
        _cc_args_invalid = 1 << 2 # Sent additional/invalid arguments (probably known to be used in old clients like "pl" and "bmk"/"bml")

        try:
            # Resend the score in case of unhandled exceptions
            keepSending = True

            # Get request ip
            ip = self.getRequestIP()

            # Print arguments
            if glob.debug:
                requestsManager.printArguments(self)

            # Check arguments
            if not requestsManager.checkArguments(self.request.arguments, ['score', 'iv', 'pass']):
                raise exceptions.invalidArgumentsException(MODULE_NAME)

            # TODO: Maintenance check

            # Get parameters and IP
            scoreDataEnc = self.get_argument('score', None)
            iv = self.get_argument('iv', None)
            password = self.get_argument('pass', None)

            # Get right AES Key
            if 'osuver' in self.request.arguments:
                aeskey = f'osu!-scoreburgr---------{self.get_argument("osuver")}'
            else:
                aeskey = 'h89f2-890h2h89b34g-h80g134n90133'

            # Get score data
            log.debug('Decrypting score data...')
            scoreData: List[str] = aeshelper.decryptRinjdael(aeskey, iv, scoreDataEnc, True).split(':')

            username = scoreData[1].strip()

            if "Token" not in self.request.headers:
                raise exceptions.userNoAnticheatException(MODULE_NAME, username)

            # Login and ban check
            userID = userUtils.getID(username)
            # User exists check
            if not userID:
                raise exceptions.loginFailedException(MODULE_NAME, userID)
            # Bancho session/username-pass combo check
            if not userUtils.checkLogin(userID, password, ip):
                raise exceptions.loginFailedException(MODULE_NAME, username)
            # Generic bancho session check
            #if not userUtils.checkBanchoSession(userID):
                # TODO: Ban (see except exceptions.noBanchoSessionException block)
            #	raise exceptions.noBanchoSessionException(MODULE_NAME, username, ip)
            # Ban check
            if userUtils.isBanned(userID):
                raise exceptions.userBannedException(MODULE_NAME, username)
            # Data length check
            if len(scoreData) < 16:
                raise exceptions.invalidArgumentsException(MODULE_NAME)

            restricted = userUtils.isRestricted(userID)

            # Create score object and set its data
            s = score.score()
            s.setDataFromScoreData(scoreData)

            if s.completed == -1:
                log.warning(f'Duplicated score detected, this is normal right after restarting the server [{username} ({userID})].')
                self.write('error: no')
                return

            # Set score stuff missing in score data
            s.playerUserID = userID

            # Get beatmap info
            beatmapInfo = beatmap.beatmap()
            beatmapInfo.setDataFromDB(s.fileMd5)

            # Make sure the beatmap is submitted and updated
            if beatmapInfo.rankedStatus in (rankedStatuses.NOT_SUBMITTED,
                                            rankedStatuses.NEED_UPDATE,
                                            rankedStatuses.UNKNOWN):
                log.debug(f'Beatmap {beatmapInfo.beatmapID} is not submitted/outdated/unknown. Score submission aborted.')
                self.write('error: no')
                return

            # Increment user playtime.
            length = 0
            if s.passed:
                if not (
                    restricted or
                    any([i in self.request.arguments for i in ('ft', 'x')])
                ):
                    _cc_flags |= _cc_args_missing

                #try: # Custom client check based on arguments missing
                #	self.get_argument('ft')
                #	self.get_argument('x')
                #except:
                #	# Custom client check 2
                #	# User did not sent 'ft' and 'x' params
                #	if not restricted:
                #		custom_client |= 2
                length = userUtils.getBeatmapTime(beatmapInfo.beatmapID)
            else:
                length = ceil(int(self.get_argument('ft')) / 1000)

            # Edit length based on mods; this is not done automatically!
            if s.mods & mods.HALFTIME:
                length *= 1.5
            elif s.mods & (mods.DOUBLETIME | mods.NIGHTCORE):
                length /= 1.5

            userUtils.incrementPlaytime(userID, s.gameMode, length)

            # Calculate PP
            midPPCalcException = None
            try:
                s.calculatePP()
            except Exception as e:
                # Intercept ALL exceptions and bypass them.
                # We want to save scores even in case PP calc fails
                # due to some rippoppai bugs.
                # I know this is bad, but who cares since I'll rewrite
                # the scores server again.
                log.error('Caught an exception in pp calculation, re-raising after saving score in db.')
                s.pp = 0
                midPPCalcException = e

            oldPersonalBestRank = 0
            oldPersonalBest = None

            if s.passed:
                # Right before submitting the score, get the personal best score object (we need it for charts)
                if s.oldPersonalBest > 0:
                    oldPersonalBestRank = glob.personalBestCache.get(userID, s.fileMd5)
                    if oldPersonalBestRank == 0:
                        oldScoreboard = scoreboard.scoreboard(username, s.gameMode, beatmapInfo, False)
                        oldScoreboard.setPersonalBestRank()
                        oldPersonalBestRank = max(oldScoreboard.personalBestRank, 0)
                    oldPersonalBest = score.score(s.oldPersonalBest, oldPersonalBestRank)

            # Save score in db
            s.saveScoreInDB()

            # some useful stuff - not always used but used enough that i'll add it here
            relax = s.mods & mods.RELAX > 0
            pp_limit = scoreUtils.getPPLimit(s.gameMode, s.mods)
            whitelisted = userUtils.checkWhitelist(
                userID, akatsuki.RELAX if relax else akatsuki.VANILLA
            )

            # Increment per-user beatmap playcount
            userUtils.updateBeatmapPlaycount(userID, s.fileMd5, s.gameMode, relax)

            if not restricted:
                if endpoint != '-selector':
                    _cc_flags |= _cc_invalid_url

                if any([i in self.request.arguments for i in ('bml', 'pl')]):
                    log.warning(f'_cc_args_invalid triggered: {username}\n\n{self.request.arguments}\n\n')
                     #_cc_flags |= _cc_args_invalid

                if s.pp >= pp_limit and not whitelisted:
                    userUtils.restrict(userID)
                    restricted = True

                    _mods = []
                    if s.mods & mods.FLASHLIGHT:
                        _mods.append('FL')
                    if relax:
                        _mods.append('RX')

                    if _mods:
                        _mods = ''.join(_mods)
                    else:
                        _mods = 'Nomod'

                    userUtils.appendNotes(userID, f'[GM {s.gameMode}] Restricted from breaking PP limit ({_mods}) - {s.pp:.2f}pp.')
                    log.warning(f'[GM {s.gameMode}] [{username}](https://akatsuki.pw/u/{userID}) restricted from breaking PP limit ({_mods}) - **{s.pp:.2f}**pp.', discord='ac_general')

                # Custom client detection flags
                if _cc_flags and not userUtils.checkDelayBan(userID):
                    userUtils.appendNotes(userID, f'Submitted a score using a custom client ({_cc_flags}).')
                    log.warning(f'**[{username}](https://akatsuki.pw/u/{userID}) has submitted a score using a custom client.\n\nFlags: {_cc_flags}**', discord='ac_general')
                    userUtils.setDelayBan(userID, True)

                # osu's client anticheat flags
                client_flags = scoreData[17].count(' ')
                if client_flags not in {osu_flags.Clean, osu_flags.IncorrectModValue} and s.completed > 1:
                    client_flags_readable = generalUtils.osuFlagsReadable(client_flags)

                    userUtils.appendNotes(userID, f'Received clientside flags: {client_flags} [{" | ".join(client_flags_readable)}] (cheated score id: {s.scoreID})')
                    log.warning('\n\n'.join([
                        f'[{username}](https://akatsuki.pw/u/{userID}) has recieved client flags: **{client_flags}**.',
                        '**Breakdown**\n' + '\n'.join(client_flags_readable),
                        f'**[Replay](https://akatsuki.pw/web/replays/{s.scoreID})**'
                    ]), discord='ac_general')

                # nyo checks cuz of solis and i lol

                if (
                    s.gameMode == gameModes.MANIA and
                    s.score > 1000000
                ):
                    userUtils.ban(userID)
                    userUtils.appendNotes(userID, f'Banned due to {s.score} mania score.')

                if (
                    ((s.mods & mods.DOUBLETIME) > 0 and (s.mods & mods.HALFTIME) > 0) or
                    ((s.mods & mods.HARDROCK) > 0 and (s.mods & mods.EASY) > 0) or
                    ((s.mods & mods.SUDDENDEATH) > 0 and (s.mods & mods.NOFAIL) > 0) or
                    (relax and (s.mods & mods.RELAX2) > 0)
                ):
                    userUtils.ban(userID)
                    userUtils.appendNotes(userID, f'Impossible mod combination ({s.mods}).')

            # NOTE: Process logging was removed from the client starting from 2018-03-22
            # Save replay for all passed scores
            # Make sure the score has an id as well (duplicated?, query error?)
            if s.passed and s.scoreID > 0:
                if 'score' in self.request.files:
                    # Save the replay if it was provided
                    log.debug(f'Saving replay ({s.scoreID})')

                    rawReplay = self.request.files['score'][0]['body']

                    if generalUtils.stringToBool(glob.conf.config['ftp']['enable']):
                        t0 = time.perf_counter()
                        try:
                            with io.BytesIO(rawReplay) as data:
                                with glob.ftp_lock:
                                    glob.ftp.storbinary(f'STOR /replays/replay_{s.scoreID}.osr', data)
                        except Exception as e:
                            log.warning(f'submitModularHandler ({e})\n\n{traceback.format_exc()}')

                            # in the event of ftp fail, save to disk
                            # (we don't want to lose any replays)
                            with open(f'.data/replays/replay_{s.scoreID}.osr', 'wb') as f:
                                f.write(rawReplay)

                        time_taken_ftp = time.perf_counter() - t0
                        if time_taken_ftp > 2:
                            log.warning(f'FTP replay submission took {time_taken_ftp:.2f}s!')
                    else:
                        with open(f'.data/replays/replay_{s.scoreID}.osr', 'wb') as f:
                            f.write(rawReplay)

                elif not restricted: # Restrict if no replay was provided
                    userUtils.restrict(userID)
                    restricted = True

                    userUtils.appendNotes(userID, f'Restricted due to missing replay while submitting a score ({s.scoreID}).')
                    log.warning(f'**{username}** {userID} has been restricted due to not submitting a replay on {beatmap.songName} ({beatmap.BeatmapID}).', discord='ac_general')

            # Update beatmap playcount (and passcount)
            beatmap.incrementPlaycount(s.fileMd5, s.passed)

            # Let the api know of this score
            if s.scoreID and not restricted:
                glob.redis.publish('api:score_submission', f'{s.scoreID},{relax}')

            # Re-raise pp calc exception after saving score, cake, replay etc
            # so Sentry can track it without breaking score submission
            if midPPCalcException:
                raise ppCalcException(midPPCalcException)

            # If there was no exception, update stats and build score submitted panel
            # Get "before" stats for ranking panel (only if passed)
            if s.passed:
                # Get stats and rank
                oldUserData = glob.userStatsCache.get(userID, s.gameMode, relax)
                oldRank = userUtils.getGameRank(userID, s.gameMode, relax)

            # Always update users stats (total/ranked score, playcount, level, acc and pp)
            # even if not passed

            log.debug(f"[{'R' if relax else 'V'}] Updating {username}'s stats...")
            userUtils.updateStats(userID, s)

            # Get "after" stats for ranking panel
            # and to determine if we should update the leaderboard
            # (only if we passed that song)
            if s.passed:
                # Get new stats
                maxCombo = 0 if relax else userUtils.getMaxCombo(userID, s.gameMode)
                newUserData = userUtils.getUserStats(userID, s.gameMode, relax)
                glob.userStatsCache.update(userID, s.gameMode, relax, newUserData)

                # Update leaderboard (global and country) if score/pp has changed
                if s.completed == 3 and newUserData['pp'] != oldUserData['pp']:
                    leaderboardHelper.update(userID, newUserData['pp'], s.gameMode, relax)
                    leaderboardHelper.updateCountry(userID, newUserData['pp'], s.gameMode, relax)

            # TODO: Update total hits and max combo
            userUtils.updateLatestActivity(userID)
            userUtils.IPLog(userID, ip)

            log.debug('Score submission and user stats update done!')

            # Score has been submitted, do not retry sending the score if
            # there are exceptions while building the ranking panel
            keepSending = False

            # At the end, check achievements
            if s.passed:
                new_achievements = secret.achievements.utils.unlock_achievements(s, beatmapInfo, newUserData)

            # Output ranking panel only if we passed the song
            # and we got valid beatmap info from db
            if beatmapInfo and s.passed:
                log.debug('Started building ranking panel.')

                glob.redis.publish('peppy:update_cached_stats', userID)
                newScoreboard = scoreboard.scoreboard(username, s.gameMode, beatmapInfo, False, relax = relax)
                newScoreboard.setPersonalBestRank()
                personalBestID = newScoreboard.getPersonalBestID()
                assert personalBestID is not None
                currentPersonalBest = score.score(personalBestID, newScoreboard.personalBestRank)

                # Get rank info (current rank, pp/score to next rank, user who is 1 rank above us)
                rankInfo = leaderboardHelper.getRankInfo(userID, s.gameMode, relax)

                output = 'error: no' if relax else '\n'.join(map(zingonify, [
                    OrderedDict([
                        ('beatmapId', beatmapInfo.beatmapID),
                        ('beatmapSetId', beatmapInfo.beatmapSetID),
                        ('beatmapPlaycount', beatmapInfo.playcount + 1),
                        ('beatmapPasscount', beatmapInfo.passcount + (s.completed == 3)),
                        ('approvedDate', '')
                    ]),
                    BeatmapChart(
                        oldPersonalBest if s.completed == 3 else currentPersonalBest,
                        currentPersonalBest if s.completed == 3 else s,
                        beatmapInfo.beatmapID,
                    ),
                    OverallChart(
                        userID, oldUserData, newUserData, maxCombo, s, new_achievements, oldRank, rankInfo['currentRank']
                    )
                ]))

                """ Globally announcing plays. """
                if s.completed == 3 and not restricted and beatmapInfo.rankedStatus >= rankedStatuses.RANKED:
                    annmsg: Optional[str] = None
                    if newScoreboard.personalBestRank == 1:
                        scoreUtils.newFirst(s.scoreID, userID, s.fileMd5, s.gameMode, relax)

                        profile_embed = userUtils.getProfileEmbed(userID, clan=True)

                        # New server top play (TODO: other gamemodes?)
                        # Since we've already autorestricted & also
                        # checked if the user is restricted, this is safe.
                        if s.gameMode == gameModes.STD and s.pp > glob.topPlays['relax' if relax else 'vanilla']:
                            annmsg = f"[{'R' if relax else 'V'}] {profile_embed} achieved the server's highest PP play on {beatmapInfo.embed} ({gameModes.getGamemodeFull(s.gameMode)}) - {s.pp:.2f}pp"
                            glob.topPlays['relax' if relax else 'vanilla'] = s.pp
                        else:
                            annmsg = f'[{"R" if relax else "V"}] {profile_embed} achieved rank #1 on {beatmapInfo.embed} ({gameModes.getGamemodeFull(s.gameMode)}) - {s.pp:.2f}pp'

                        """
                        # Is the map the contest map? Try to fetch it by beatmapID, rx, and gamemode.
                        contest = glob.db.fetch('SELECT id, relax, gamemode FROM competitions WHERE map = %s AND relax = %s AND gamemode = %s', [beatmapInfo.beatmapID, int(relax), s.gameMode]) # TODO: scoreUtils
                        if contest is not None: # TODO: Add contest stuff to scoreUtils
                            glob.db.execute('UPDATE competitions SET leader = %s WHERE id = %s', [userID, contest['id']])
                            annmsg = f'[{"R" if relax else "V"}] {profile_embed} has taken the lead on {beatmapInfo.embed}! ({gameModes.getGamemodeFull(s.gameMode)}) - {s.pp:.2f}pp'
                        """

                    if annmsg:
                        params = urlencode({
                            'k': glob.conf.config['server']['apikey'],
                            'to': '#announce',
                            'msg': annmsg
                        })
                        requests.get(f'{glob.conf.config["server"]["banchourl"]}/api/v1/fokabotMessage?{params}', timeout= 2)

                # Write message to client
                self.write(output)
            else:
                # No ranking panel, send just 'error: no'
                # so their client know to stop communicating.
                self.write('error: no')

            # Send username change request to bancho if needed
            # (key is deleted bancho-side)
            newUsername = glob.redis.get(f'ripple:change_username_pending:{userID}')
            if newUsername:
                log.debug(f'Sending username change request for user {userID} to Bancho')
                glob.redis.publish('peppy:change_username', orjson.dumps({
                    'userID': userID,
                    'newUsername': newUsername.decode('utf-8')
                }))
                glob.redis.publish('api:change_username', f'{userID}')

            # Datadog stats
            glob.dog.increment(f'{glob.DATADOG_PREFIX}.submitted_scores')

            if s.completed == 3:
                lb_cache = glob.lb_cache.get_lb_cache(s.gameMode, relax)
                glob.lb_cache.clear_lb_cache(lb_cache, beatmapInfo.fileMD5)

                glob.pb_cache.del_user_pb(s.gameMode, userID, beatmapInfo.fileMD5, relax)

            log.info(f'Score took {(time.perf_counter() - start_time) * 1000:.2f}ms.')
        except exceptions.invalidArgumentsException:
            pass
        except exceptions.loginFailedException:
            self.write('error: pass')
        except exceptions.userBannedException:
            self.write('error: ban')
        except exceptions.userNoAnticheatException:
            self.write('error: oldver')
        except exceptions.noBanchoSessionException:
            # We don't have an active bancho session.
            # Don't ban the user but tell the client to send the score again.
            # Once we are sure that this error doesn't get triggered when it
            # shouldn't (eg: bancho restart), we'll ban users that submit
            # scores without an active bancho session.
            # We only log through schiavo atm (see exceptions.py).
            self.set_status(408)
            self.write('error: pass')
        except:
            # Try except block to avoid more errors
            try:
                log.error(f'Unknown error in {MODULE_NAME}!\n```{exc_info()}\n{traceback.format_exc()}```')
                if glob.sentry:
                    yield tornado.gen.Task(self.captureException, exc_info=True)
            except:
                pass

            # Every other exception returns a 408 error (timeout)
            # This avoids lost scores due to score server crash
            # because the client will send the score again after some time.
            if keepSending:
                self.set_status(408)

    def save_current_graph(user_id: int, pp: int, rank: int, ranked_score: int, total_score: int, mode: int, is_relax: bool) -> None:
        today: date = datetime.today().date()

        result = glob.db.fetch('SELECT TOP 1 timestamp '
                               'FROM akatsuki_graphs WHERE user_id = %s', (user_id,))
        if not result:
            glob.db.execute('INSERT INTO akatsuki_graphs (user_id, pp, rank, ranked_score, total_score, mode, is_relax, timestamp) '
                            'VALUES (%s, %s, %s, %s, %s, %s, %s, %s)')
        else:
            last_timestamp: datetime = result["timestamp"]
            if today == last_timestamp.date():
                ...
