"""
Wifipiano 2

This file has been written taking by reference code from
osu-performance (https://github.com/ppy/osu-performance)
by Tom94, licensed under the GNU AGPL 3 License.
"""
from typing import TYPE_CHECKING

from common.constants import gameModes, mods
from common.log import logUtils as log
from constants import exceptions
from helpers import mapsHelper, osuapiHelper
from objects import glob

if TYPE_CHECKING:
    from objects.beatmap import beatmap

class piano:
    __slots__ = ("beatmap", "score", "pp")

    def __init__(self, __beatmap: 'beatmap', __score):
        self.beatmap = __beatmap
        self.score = __score
        self.pp = 0.0
        self.getPP()

    def getPP(self):
        try:
            if self.beatmap.starsMania == 0:
                # if the map isn't native mania or std (convertible)
                # XXX: native mania should already have SR? is this even needed?
                if self.beatmap.gameMode not in (gameModes.STD, gameModes.MANIA):
                    # map not native mania & can't be converted
                    raise exceptions.invalidBeatmapException()

                beatmap_md5 = self.beatmap.fileMD5

                # get mania star rating from osuapi
                stars = float(osuapiHelper.osuApiMapRequest(
                    request='get_beatmaps', params=f'h={beatmap_md5}&a=1&m=3'
                )['difficultyrating'])

                # cache in sql for future use
                glob.db.execute(
                    'UPDATE beatmaps '
                    'SET difficulty_mania = %s '
                    'WHERE beatmap_md5 = %s',
                    [stars, beatmap_md5]
                )

                self.beatmap.starsMania = stars
                log.info(f'Cached mania sr for {self.beatmap.songName} ({stars}*).')
            else:
                stars = self.beatmap.starsMania

            # Cache beatmap for cono
            mapsHelper.cacheMap(mapsHelper.cachedMapPath(self.beatmap.beatmapID), self.beatmap)

            od = self.beatmap.OD
            objects = (self.score.c50 + self.score.c100 + self.score.c300 +
                       self.score.cKatu + self.score.cGeki + self.score.cMiss)

            score = self.score.score
            accuracy = self.score.accuracy
            scoreMods = self.score.mods

            # stuff checked multiple times (tiny optimization)
            if scoreMods & mods.DOUBLETIME != 0:
                is_dt = True
                is_ht = False
            elif scoreMods & mods.HALFTIME != 0:
                is_dt = False
                is_ht = True
            else:
                is_dt = is_ht = False

            is_ez = scoreMods & mods.EASY != 0

            log.debug(
                f'[WIFIPIANO2] SCORE DATA: Stars: {stars}, '
                f'OD: {od}, obj: {objects}, score: {score}, '
                f'acc: {accuracy}, mods: {scoreMods}'
            )

            # ---------- STRAIN PP
            # Scale score to mods multiplier
            scoreMultiplier = 1.0

            # Doubles score if EZ/HT
            if is_ez:
                scoreMultiplier *= 0.50
            #if is_ht:
            #	scoreMultiplier *= 0.50

            # Calculate strain PP
            if scoreMultiplier <= 0:
                strainPP = 0
            else:
                score *= 1.0 / scoreMultiplier
                strainPP = ((5.0 * max(1.0, stars / 0.0825) - 4.0) ** 3.0) / 110000.0
                strainPP *= 1 + 0.1 * min(1.0, objects / 1500.0)
                if score <= 500000:
                    strainPP *= (score / 500000.0) * 0.1
                elif score <= 600000:
                    strainPP *= 0.1 + (score - 500000) / 100000.0 * 0.2
                elif score <= 700000:
                    strainPP *= 0.3 + (score - 600000) / 100000.0 * 0.35
                elif score <= 800000:
                    strainPP *= 0.65 + (score - 700000) / 100000.0 * 0.20
                elif score <= 900000:
                    strainPP *= 0.85 + (score - 800000) / 100000.0 * 0.1
                else:
                    strainPP *= 0.95 + (score - 900000) / 100000.0 * 0.05

            # ---------- ACC PP
            # Makes sure OD is in range 0-10. If this is done elsewhere, remove this.
            scrubbedOD = min(10.0, max(0, 10.0 - od))

            # Old formula but done backwards.
            hitWindow300 = 34 + 3 * scrubbedOD

            # Increases hitWindow if EZ is on
            if is_ez:
                hitWindow300 *= 1.4

            # Fiddles with DT and HT to make them match hitWindow300's ingame.
            if is_dt:
                hitWindow300 *= 1.5
            elif is_ht:
                hitWindow300 *= 0.75

            # makes hit window match what it is ingame.
            hitWindow300 = int(hitWindow300) + 0.5
            if is_dt:
                hitWindow300 /= 1.5
            elif is_ht:
                hitWindow300 /= 0.75

            # Calculate accuracy PP
            accPP = (((150.0 / hitWindow300) * (accuracy ** 16)) ** 1.8) * 2.5
            accPP *= min(1.15, (objects / 1500.0) ** 0.3)

            # ---------- TOTAL PP
            multiplier = 1.1
            if scoreMods & mods.NOFAIL != 0:
                multiplier *= 0.90
            if scoreMods & mods.SPUNOUT != 0:
                multiplier *= 0.95
            if is_ez:
                multiplier *= 0.50
            if is_dt:
                multiplier *= 2.45
            elif is_ht:
                multiplier *= 0.50
            pp = (((strainPP ** 1.1) + (accPP ** 1.1)) ** (1.0 / 1.1)) * multiplier
            log.debug(f"[WIFIPIANO2] Calculated PP: {pp}")

            self.pp = pp
        except exceptions.invalidBeatmapException:
            log.warning(f"Invalid beatmap {self.beatmap.beatmapID}")
            self.pp = 0.0
        finally:
            return self.pp
