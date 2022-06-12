import orjson
from common.log import logUtils as log
from common.ripple import userUtils
from objects import glob


class userStatsCache:
    def get(self, userID: int, gameMode: int, relax: bool):
        """
        Get cached user stats from redis.
        If user stats are not cached, they'll be read from db, cached and returned

        :param userID: userID
        :param gameMode: game mode number
        :return: userStats dictionary (rankedScore, totalScore, pp, accuracy, playcount)
        """

        data = glob.redis.get(f'lets:users_stats_cache:{gameMode}:{int(relax)}:{userID}')

        if data is None:
            # If data is not cached, cache it and call get function again
            log.debug("userStatsCache miss")
            self.update(userID, gameMode, relax)
            return self.get(userID, gameMode, relax)

        log.debug("userStatsCache hit")
        retData = orjson.loads(data.decode("utf-8"))
        return retData

    def update(self, userID: int, gameMode: int, relax: bool, data = None):
        """
        Update cached user stats in redis with new values

        :param userID: userID
        :param gameMode: game mode number
        :param data: data to cache. Optional. If not passed, will get from db
        :return:
        """
        if data is None:
            data = {}
        if len(data) == 0:
            data = userUtils.getUserStats(userID, gameMode, relax)
        log.debug(f"userStatsCache set {data}")

        glob.redis.set(f'lets:users_stats_cache:{gameMode}:{int(relax)}:{userID}', orjson.dumps(data), 1800)
