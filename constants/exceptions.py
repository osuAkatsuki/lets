from common.log import logUtils as log


class invalidArgumentsException(Exception):
    def __init__(self, handler):
        log.warning(f'{handler} - Invalid arguments.')

class loginFailedException(Exception):
    def __init__(self, handler, who):
        log.warning(f"{handler} - {who}'s login failed.")

class beatmapSubmitAuthException(Exception):
    def __init__(self, handler, who):
        log.warning(f"{handler} - {who}'s login failed.")

class beatmapSubmitRestrictionException(Exception):
    def __init__(self, handler, who):
        log.warning(f"{handler} - {who}'s tried to submit beatmap while being restricted.")

class beatmapSubmitOwnershipException(Exception):
    def __init__(self, handler, who):
        log.warning(f"{handler} - {who}'s tried to submit beatmap that isn't owned by him.")

class beatmapSubmitRankedException(Exception):
    def __init__(self, handler, who):
        log.warning(f"{handler} - {who}'s tried to update already ranked beatmap.")

class beatmapSubmitNotExistException(Exception):
    def __init__(self, handler, who):
        log.warning(f"{handler} - {who}'s tried to update non-existent beatmap.")

class beatmapSubmitParseException(Exception):
    def __init__(self, handler, who):
        log.warning(f"{handler} - {who} osz2 parse failed.")
class beatmapSubmitLongTagsException(Exception):
    pass
class beatmapSubmitSubmissionCapException(Exception):
    pass

class userBannedException(Exception):
    def __init__(self, handler, who):
        log.warning(f'{handler} - {who} is banned.')

class userLockedException(Exception):
    def __init__(self, handler, who):
        log.warning(f'{handler} - {who} is locked.')

class userNoAnticheatException(Exception):
    def __init__(self, handler, who):
        log.warning(f'{handler} - {who} has tried to submit a score without Token header.')

class noBanchoSessionException(Exception):
    def __init__(self, handler, who, ip):
        log.warning(f'{handler} - {who} has tried to submit a score from {ip} without an active bancho session from that IP.', discord='ac_confidential')

class osuApiFailException(Exception):
    def __init__(self, handler):
        log.warning(f'{handler} - Invalid data from osu!api.')

class fileNotFoundException(Exception):
    def __init__(self, handler, f):
        log.warning(f'{handler} - File not found ({f}).')

class invalidBeatmapException(Exception):
    pass

class unsupportedGameModeException(Exception):
    pass

class myServerSucksException(Exception):
    def __init__(self, handler):
        log.warning(f'{handler} - Requested beatmap is too long.')

class noAPIDataError(Exception):
    pass

class ppCalcException(Exception):
    def __init__(self, exception):
        self.exception = exception
