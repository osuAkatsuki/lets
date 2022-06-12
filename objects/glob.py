import threading
from typing import TYPE_CHECKING

from common.ddog import datadogClient
from common.files import fileBuffer, fileLocks
from common.web import schiavo
from helpers.cache import LeaderboardCache, PersonalBestCache
from personalBestCache import personalBestCache
from userStatsCache import userStatsCache

if TYPE_CHECKING:
    from multiprocessing.pool import ThreadPool
    from typing import TYPE_CHECKING
    from typing import Optional

    from ftplib import FTP
    from redis import Redis
    from tornado.web import Application

    from common.db import dbConnector
    from helpers import config

try:
    with open("version") as f:
        VERSION = f.read().strip()
except:
    VERSION = "Unknown"
ACHIEVEMENTS_VERSION = 1

DATADOG_PREFIX = "lets"
BOT_NAME = "Aika"
BEATMAPS_START_INDEX = 0x3fffffff
BEATMAPS_PATH = '.data/akatsuki_beatmaps'
db: 'dbConnector.db' = None

ftp: 'Optional[FTP]' = None
ftp_lock = threading.Lock()

redis: 'Redis' = None
conf: 'config' = None
application: 'Application' = None
pool: 'ThreadPool' = None

busyThreads = 0
debug = False
sentry = False

# Cache and objects
fLocks = fileLocks.fileLocks()
userStatsCache = userStatsCache()
personalBestCache = personalBestCache()
fileBuffers = fileBuffer.buffersList()
dog = datadogClient.datadogClient()
schiavo = schiavo.schiavo()
achievementClasses = {}

ignoreMapsCache = {} # getscores optimization

bcrypt_cache = {}
topPlays = {'relax': 9999, 'vanilla': 9999}

last_inserted_set_id: int = 0
last_inserted_map_id: int = 0

# TODO: Experiment with these, which yields the best perf
pb_cache = PersonalBestCache()
lb_cache = LeaderboardCache()
