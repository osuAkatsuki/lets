from common import generalUtils
from common.log import logUtils as log
from objects import glob


class cacheMiss(Exception):
    pass

class personalBestCache:
    def get(self, userID: int, fileMd5: str, country: bool = False, friends: bool = False, mods: int = -1) -> int:
        """
        Get cached personal best rank

        :param userID: userID
        :param fileMd5: beatmap md5
        :param country: True if country leaderboard, otherwise False
        :param friends: True if friends leaderboard, otherwise False
        :param mods: leaderboard mods
        :return: 0 if cache miss, otherwise rank number
        """
        try:
            # Make sure the value is in cache
            data = glob.redis.get(f"lets:personal_best_cache:{userID}")
            if data is None:
                raise cacheMiss()

            # Unpack cached data
            data = data.decode().split("|")

            # Check if everything matches
            if (
                fileMd5 != data[1] or
                country != generalUtils.stringToBool(data[2]) or
                friends != generalUtils.stringToBool(data[3]) or
                mods != int(data[4])
            ):
                raise cacheMiss()

            # Cache hit
            log.debug("personalBestCache hit")
            return int(data[0])
        except cacheMiss:
            log.debug("personalBestCache miss")
            return 0

    def set(self, userID: int, rank: int, fileMd5: str, country: bool = False, friends: bool = False, mods: int = -1) -> None:
        """
        Set userID's redis personal best cache

        :param userID: userID
        :param rank: leaderboard rank
        :param fileMd5: beatmap md5
        :param country: True if country leaderboard, otherwise False
        :param friends: True if friends leaderboard, otherwise False
        :param mods: leaderboard mods
        :return:
        """
        glob.redis.set(f"lets:personal_best_cache:{userID}", f"{rank}|{fileMd5}|{country}|{friends}|{mods}", 1800)
        log.debug("personalBestCache set")
