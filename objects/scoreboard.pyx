from typing import List
from typing import Optional
from typing import TYPE_CHECKING

from common.ripple import userUtils
from constants import rankedStatuses
from objects import score
from objects import glob

if TYPE_CHECKING:
    from beatmap import beatmap

class scoreboard:
    def __init__(
        self, username: str, gameMode: int, beatmap: 'beatmap',
        setScores: bool = True, country: bool = False, friends: bool = False,
        mods: int = -1, relax: bool = False
    ) -> None:
        """
        Initialize a leaderboard object
        username -- username of who's requesting the scoreboard. None if not known
        gameMode -- requested gameMode
        beatmap -- beatmap objecy relative to this leaderboard
        setScores -- if True, will get personal/top 50 scores automatically. Optional. Default: True
        """

        self.scores = [] # list containing all top 50 scores objects. First object is personal best
        self.totalScores = 0
        self.personalBestRank = -1 # our personal best rank, -1 if not found yet
        self.username = username
        self.userID = userUtils.getID(self.username)
        self.gameMode = gameMode
        self.beatmap = beatmap
        self.country = country
        self.friends = friends
        self.mods = mods
        self.relax = relax

        if setScores:
            self.setScores()

        self.score_rows = [] # for caching

    @staticmethod
    def buildQuery(params, table) -> str:
        return '{select} {joins} {country} {mods} {friends} {order} {limit}'.format(**params).format(t=table)

    def getPersonalBestID(self) -> Optional[int]:
        if self.userID == 0:
            return

        # Query parts
        cdef str select = ""
        cdef str joins = ""
        cdef str country = ""
        cdef str mods = ""
        cdef str friends = ""
        cdef str order = ""
        cdef str limit = ""
        select = (
            'SELECT id FROM {t} WHERE userid = %(userid)s '
            'AND beatmap_md5 = %(md5)s AND play_mode = %(mode)s AND completed = 3'
        )

        # Mods
        if self.mods > -1:
            mods = 'AND mods = %(mods)s'

        # Friends ranking
        if self.friends:
            friends = (
                'AND ({t}.userid IN '
                '(SELECT user2 FROM users_relationships WHERE user1 = %(userid)s) '
                'OR {t}.userid = %(userid)s)'
            )

        # Sort and limit at the end
        if (self.relax and self.beatmap.rankedStatus != rankedStatuses.LOVED):
            order = 'ORDER BY pp DESC'
        else:
            order = 'ORDER BY score DESC'

        limit = 'LIMIT 1'

        # Build query, get params and run query
        id_ = glob.db.fetch(self.buildQuery(locals(), 'scores_relax' if self.relax else 'scores'), {
            "userid": self.userID,
            "md5": self.beatmap.fileMD5,
            "mode": self.gameMode,
            "mods": self.mods
        })
        return id_["id"] if id_ else None

    def setScores(self) -> None:
        """
        Set scores list
        """

        # Reset score list
        self.scores = []
        self.scores.append(-1)

        # Make sure the beatmap is ranked
        if self.beatmap.rankedStatus < rankedStatuses.RANKED:
            return

        # Query parts
        cdef str select = ""
        cdef str joins = ""
        cdef str country = ""
        cdef str mods = ""
        cdef str friends = ""
        cdef str order = ""
        cdef str limit = ""

        # Find personal best score
        personalBestScoreID = self.getPersonalBestID()

        # Output our personal best if found
        if personalBestScoreID is not None:
            s = score.score(personalBestScoreID, relax = self.relax)
            self.scores[0] = s
        else:
            # No personal best
            self.scores[0] = -1

        # Get top n scores
        select = (
            'SELECT {t}.id, {t}.userid, {t}.score, {t}.max_combo, {t}.play_mode, '
            '{t}.50_count, {t}.100_count, {t}.300_count, {t}.misses_count, {t}.katus_count, '
            '{t}.gekis_count, {t}.full_combo, {t}.mods, {t}.time, {t}.beatmap_md5, {t}.completed, {t}.pp'
        )

        joins = (
            'FROM {t} '
            'STRAIGHT_JOIN users ON {t}.userid = users.id '
            'STRAIGHT_JOIN users_stats ON users.id = users_stats.id '
            'WHERE {t}.beatmap_md5 = %(beatmap_md5)s AND {t}.play_mode = %(play_mode)s '
            'AND {t}.completed = 3 AND (users.privileges & 1 OR users.id = %(userid)s)'
        )

        # Country ranking
        if self.country:
            country = (
                'AND users_stats.country = '
                '(SELECT country FROM users_stats WHERE id = %(userid)s LIMIT 1)'
            )
        else:
            country = ''

        # Mods ranking (ignore auto, since we use it for pp sorting)
        if self.mods > -1:
            mods = 'AND {t}.mods = %(mods)s'
        else:
            mods = ''

        # Friends ranking
        if self.friends:
            friends = (
                'AND ({t}.userid IN '
                '(SELECT user2 FROM users_relationships WHERE user1 = %(userid)s) '
                'OR {t}.userid = %(userid)s)'
            )
        else:
            friends = ''


        if self.relax and self.beatmap.rankedStatus != rankedStatuses.LOVED:
            order = 'ORDER BY pp DESC'
        else:
            order = 'ORDER BY score DESC'

        limit = 'LIMIT 50'


        params = {
            "beatmap_md5": self.beatmap.fileMD5,
            "play_mode": self.gameMode,
            "userid": self.userID,
            "mods": self.mods
        }

        table = 'scores_relax' if self.relax else 'scores'

        # Build query, get params and run query
        topScores = glob.db.fetchAll(self.buildQuery(locals(), table), params)
        self.score_rows = topScores

        # Set data for all scores
        cdef int c = 1
        cdef dict topScore
        if topScores is not None:
            for topScore in topScores:
                # Create score object
                s = score.score(topScore["id"], setData=False)

                # Set data and rank from topScores's row
                s.setDataFromDict(topScore)
                s.rank = c

                # Check if this top 50 score is our personal best
                if s.playerName == self.username:
                    self.personalBestRank = c

                # Add this score to scores list and increment rank
                self.scores.append(s)
                c += 1

        # If we have more than 50 scores, run query to get scores count
        # TODO: optimize this.. it's a ~20% decrease in speed to this request
        if c >= 50:
            # Count all scores on this map
            select = 'SELECT COUNT(*) AS count'
            limit = 'LIMIT 1'
            # Build query, get params and run query
            count = glob.db.fetch(self.buildQuery(locals(), table), params)
            if count is None:
                self.totalScores = 0
            else:
                self.totalScores = count["count"]
        else:
            self.totalScores = c - 1

        # If personal best score was not in top 50, try to get it from cache
        if personalBestScoreID is not None and self.personalBestRank < 1:
            self.personalBestRank = glob.personalBestCache.get(
                self.userID, self.beatmap.fileMD5,
                self.country, self.friends, self.mods
            )

        # It's not even in cache, get it from db
        if personalBestScoreID is not None and self.personalBestRank < 1:
            self.setPersonalBestRank()

        #print(self.personalBestRank)

        # Cache our personal best rank so we can eventually use it later as
        # before personal best rank" in submit modular when building ranking panel
        if self.personalBestRank >= 1:
            glob.personalBestCache.set(
                self.userID, self.personalBestRank,
                self.beatmap.fileMD5
            )

    def setPersonalBestRank(self) -> None:
        """
        Set personal best rank ONLY
        Ikr, that query is HUGE but xd
        """
        # Before running the HUGE query, make sure we have a score on that map

        query = [
            'SELECT id FROM {t} '
            'WHERE beatmap_md5 = %(md5)s AND userid = %(userid)s '
            'AND play_mode = %(mode)s AND completed = 3'
        ]

        # Mods
        if self.mods > -1:
            query.append('AND {t}.mods = %(mods)s')

        # Friends ranking
        if self.friends:
            query.append(
                'AND ({t}.userid IN '
                '(SELECT user2 FROM users_relationships WHERE user1 = %(userid)s) '
                'OR {t}.userid = %(userid)s)'
            )

        # Sort and limit at the end
        query.append('LIMIT 1')

        hasScore = glob.db.fetch(' '.join(query).format(
            t = 'scores_relax' if self.relax else 'scores'
        ), {
            "md5": self.beatmap.fileMD5,
            "userid": self.userID,
            "mode": self.gameMode,
            "mods": self.mods
        })

        if not hasScore:
            return

        # We have a score, run the huge query
        # Base query
        query = [
            'SELECT COUNT(*) AS rank '
            'FROM {t} '
            'STRAIGHT_JOIN users ON {t}.userid = users.id '
            'STRAIGHT_JOIN users_stats ON users.id = users_stats.id '
            'WHERE {t}.{PPorScore} >= ( '
            '    SELECT {PPorScore} '
            '    FROM {t} '
            '    WHERE beatmap_md5 = %(md5)s '
            '        AND play_mode = %(mode)s '
            '        AND completed = 3 '
            '        AND userid = %(userid)s '
            '    LIMIT 1 '
            ') '
            'AND {t}.beatmap_md5 = %(md5)s '
            'AND {t}.play_mode = %(mode)s '
            'AND {t}.completed = 3 '
            'AND users.privileges & 1 > 0 '
        ]

        # Country
        if self.country:
            query.append(
                'AND users_stats.country = '
                '(SELECT country FROM users_stats WHERE id = %(userid)s LIMIT 1)'
            )

        # Mods
        if self.mods > -1:
            query.append('AND {t}.mods = %(mods)s')

        # Friends
        if self.friends:
            query.append(
                'AND ({t}.userid IN '
                '(SELECT user2 FROM users_relationships WHERE user1 = %(userid)s) '
                'OR {t}.userid = %(userid)s)'
            )

        # Sort and limit at the end
        query.append('ORDER BY score DESC LIMIT 1')

        result = glob.db.fetch(' '.join(query).format(
            t = 'scores_relax' if self.relax else 'scores',
            PPorScore = 'pp' if self.relax and self.beatmap.rankedStatus != rankedStatuses.LOVED else 'score'
        ), {
            "md5": self.beatmap.fileMD5,
            "userid": self.userID,
            "mode": self.gameMode,
            "mods": self.mods
        })

        if result is not None:
            self.personalBestRank = result["rank"]

    def getScoresData(self) -> str:
        """
        Return scores data for getscores
        return -- score data in getscores format
        """

        data: List[str] = ['']

        use_pp = (self.relax and self.beatmap.rankedStatus != rankedStatuses.LOVED) or self.mods > -1

        # Output personal best
        if self.scores[0] == -1:
            # We don't have a personal best score
            data.append('\n')
        else:
            # Set personal best score rank
            self.setPersonalBestRank()	# sets self.personalBestRank with the huge query
            self.scores[0].rank = self.personalBestRank
            data.append(self.scores[0].getData(pp = use_pp))

        # Output top 50 scores
        for i in self.scores[1:]:
            data.append(i.getData(pp = use_pp))

        return ''.join(data)
