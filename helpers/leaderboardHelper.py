from common.constants import gameModes
from common.log import logUtils as log
from common.ripple import userUtils
from objects import glob


def getRankInfo(userID: int, gameMode: int, relax: bool):
    """
    Get userID's current rank, user above us and pp/score difference

    :param userID: user
    :param gameMode: gameMode number
    :param relax: whether to update rx or regular board
    :return: {"nextUsername": "", "difference": 0, "currentRank": 0}
    """
    data = {"nextUsername": "", "difference": 0, "currentRank": 0}

    board = 'relaxboard' if relax else 'leaderboard'
    k = f'ripple:{board}:{gameModes.getGameModeForDB(gameMode)}'
    position = userUtils.getGameRank(userID, gameMode, relax) - 1
    log.debug(f"Our position is {position}")

    if position and position > 0:
        aboveUs = glob.redis.zrevrange(k, position - 1, position)
        log.debug(f"{aboveUs} is above us")

        if aboveUs and len(aboveUs) > 0 and aboveUs[0].isdigit():
            # Get our rank, next rank username and pp/score difference
            myScore = glob.redis.zscore(k, userID)
            otherScore = glob.redis.zscore(k, aboveUs[0])
            nextUsername = userUtils.getUsername(aboveUs[0])

            if nextUsername and myScore and otherScore:
                data["nextUsername"] = nextUsername
                data["difference"] = int(myScore) - int(otherScore)
    else:
        position = 0

    data["currentRank"] = position + 1
    return data

def update(userID: int, newScore: int, gameMode: int, relax: bool):
    """
    Update gamemode's leaderboard.
    Doesn't do anything if userID is banned/restricted.

    :param userID: user
    :param newScore: new score or pp
    :param gameMode: gameMode number
    :param relax: whether to update rx or regular board
    """
    if userUtils.isAllowed(userID):
        log.debug('Updating leaderboard...')

        board = 'relaxboard' if relax else 'leaderboard'
        glob.redis.zadd(f'ripple:{board}:{gameModes.getGameModeForDB(gameMode)}', str(userID), str(newScore))
    else:
        log.debug(f'Leaderboard update for user {userID} skipped (not allowed)')

def updateCountry(userID, newScore: int, gameMode: int, relax: bool):
    """
    Update gamemode's country leaderboard.
    Doesn't do anything if userID is banned/restricted.

    :param userID: user, country is determined by the user
    :param newScore: new score or pp
    :param gameMode: gameMode number
    :param relax: whether to update rx or regular board
    :return:
    """
    if userUtils.isAllowed(userID):
        country = userUtils.getCountry(userID).lower()
        if country and country != "xx":
            log.debug(f'Updating {country} country leaderboard...')

            board = 'relaxboard' if relax else 'leaderboard'
            k = f'ripple:{board}:{gameModes.getGameModeForDB(gameMode)}:{country}'
            glob.redis.zadd(k, str(userID), str(newScore))
    else:
        log.debug(f'Country leaderboard update for user {userID} skipped (not allowed)')
