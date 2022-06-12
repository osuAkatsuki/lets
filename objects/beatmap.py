import re
import time
from typing import Optional

import orjson
from common.log import logUtils as log
from constants import rankedStatuses
from helpers import osuapiHelper
from objects import glob

MAPFILE_RGX = re.compile(
    r"^(?P<artist>.+) - (?P<title>.+) \((?P<creator>.+)\) "
    r"\[(?P<version>.+)\]\.osu$"  # ver can technically be 0 chars?
)


class beatmap:
    __slots__ = (
        "songName",
        "fileMD5",
        "rankedStatus",
        "rankedStatusFrozen",
        "beatmapID",
        "beatmapSetID",
        "gameMode",
        "offset",
        "rating",
        #'starsStd', 'starsTaiko', 'starsCtb',
        "starsMania",  # needed from osuapi since ripple has no mania sr calculator
        "AR",
        "OD",
        "maxCombo",
        "hitLength",
        "bpm",
        "playcount",
        "passcount",
        "refresh",
    )

    def __init__(
        self,
        md5: Optional[str] = None,
        beatmapSetID: Optional[int] = None,
        fileName: Optional[str] = None,
        refresh: bool = False,
    ) -> None:
        """
        Initialize a beatmap object.

        md5 -- beatmap md5. Optional.
        beatmapSetID -- beatmapSetID. Optional.
        """
        self.songName = ""
        self.fileMD5 = ""
        self.rankedStatus = rankedStatuses.NOT_SUBMITTED
        self.rankedStatusFrozen = 0
        self.beatmapID = 0
        self.beatmapSetID = 0

        self.gameMode = 0
        self.offset = 0  # Won't implement
        self.rating = 0.0

        # NOTE: possibly converted sr's
        # self.starsStd = 0.0
        # self.starsTaiko = 0.0
        # self.starsCtb = 0.0
        self.starsMania = 0.0

        self.AR = 0.0
        self.OD = 0.0

        self.maxCombo = 0
        self.hitLength = 0
        self.bpm = 0

        # Statistics for ranking panel
        self.playcount = 0

        # Force refresh from osu api
        self.refresh = refresh

        if md5 is not None and beatmapSetID is not None:
            self.setData(md5, beatmapSetID, fileName)

    @property
    def embed(self):
        return f"[https://osu.ppy.sh/beatmapsets/{self.beatmapSetID}#{self.beatmapID} {self.songName}]"

    def addBeatmapToDB(self):
        """
        Add current beatmap data in db if not in yet
        """
        # Make sure the beatmap is not already in db
        print("saving to db")
        # print(self.__dict__)
        bdata = glob.db.fetch(
            "SELECT id, ranked_status_freezed, ranked, rankedby "
            "FROM beatmaps WHERE beatmap_md5 = %s "
            "OR beatmap_id = %s LIMIT 1",
            [self.fileMD5, self.beatmapID],
        )

        if bdata:
            # This beatmap is already in db, remove old record
            # Get current frozen status
            frozen = bdata["ranked_status_freezed"]
            rankedby = bdata["rankedby"]
            if frozen:
                self.rankedStatus = bdata["ranked"]

            log.debug(f'Deleting old beatmap data ({bdata["id"]})')
            glob.db.execute("DELETE FROM beatmaps WHERE id = %s LIMIT 1", [bdata["id"]])
        else:
            frozen = 0  # Unfreeze beatmap status
            rankedby = 0

        # Add new beatmap data
        log.debug("Saving beatmap data in db...")

        glob.db.execute(
            "INSERT INTO `beatmaps` ("
            "`id`, `beatmap_id`, `beatmapset_id`, "
            "`beatmap_md5`, `song_name`, `ar`, `od`, `mode`, "
            "`difficulty_mania`, `max_combo`, `hit_length`, "
            "`bpm`, `ranked`, `latest_update`, "
            "`ranked_status_freezed`, `rankedby`"
            ") VALUES (NULL, %s, %s, %s, %s, %s, %s, "
            "%s, %s, %s, %s, %s, %s, %s, %s, %s)",
            [
                self.beatmapID,
                self.beatmapSetID,
                self.fileMD5,
                self.songName.encode("utf-8", "ignore").decode("utf-8"),
                self.AR,
                self.OD,
                self.gameMode,
                self.starsMania,  # only need mania
                self.maxCombo,
                self.hitLength,
                self.bpm if self.bpm <= 0x7FFFFFFF else 0,
                self.rankedStatus,
                # self.rankedStatus if frozen == 0 else 2,
                int(time.time()),
                frozen,
                rankedby,
            ],
        )

    def setDataFromDB(self, md5):
        """
        Set this object's beatmap data from db.

        md5 -- beatmap md5
        return -- True if set, False if not set
        """
        # Get data from DB
        data = glob.db.fetch(
            "SELECT * FROM beatmaps WHERE beatmap_md5 = %s LIMIT 1", [md5]
        )
        # Make sure the query returned something
        if data is None:
            return False

        # Make sure the beatmap is not an old one
        # if all(data[f'difficulty_{m}'] == 0 for m in ('taiko', 'ctb', 'mania')):
        #    log.debug("Difficulty for non-std gamemodes not found in DB, refreshing data from osu!api...")
        #    return False

        # Set cached data period
        expire = int(glob.conf.config["server"]["beatmapcacheexpire"])

        # If the beatmap is ranked, we don't need to refresh data from osu!api that often
        if (
            data["ranked"] >= rankedStatuses.RANKED
            and data["ranked_status_freezed"] == 0
        ):
            expire *= 5

        # Make sure the beatmap data in db is not too old
        if expire > 0 and time.time() > data["latest_update"] + expire:
            if data["ranked_status_freezed"] == 1:
                self.setDataFromDict(data)
            return False

        # Data in DB, set beatmap data
        log.debug("Got beatmap data from db")
        self.setDataFromDict(data)
        return True

    def setDataFromDict(self, data):
        """
        Set this object's beatmap data from data dictionary.

        data -- data dictionary
        return -- True if set, False if not set
        """
        self.songName = data["song_name"]
        self.fileMD5 = data["beatmap_md5"]
        self.rankedStatus = int(data["ranked"])
        self.rankedStatusFrozen = int(data["ranked_status_freezed"])
        self.beatmapID = int(data["beatmap_id"])
        self.beatmapSetID = int(data["beatmapset_id"])
        self.AR = float(data["ar"])
        self.OD = float(data["od"])
        self.gameMode = int(data["mode"])
        # self.starsStd = float(data["difficulty_std"])
        # self.starsTaiko = float(data["difficulty_taiko"])
        # self.starsCtb = float(data["difficulty_ctb"])
        self.starsMania = float(data["difficulty_mania"])
        self.maxCombo = int(data["max_combo"])
        self.hitLength = int(data["hit_length"])
        self.bpm = int(data["bpm"])
        # Ranking panel statistics
        self.playcount = int(data["playcount"]) if "playcount" in data else 0
        self.passcount = int(data["passcount"]) if "passcount" in data else 0

    def setDataFromOsuApiMD5(self, md5):
        """
        Set this object's beatmap data from osu!api.

        md5 -- beatmap md5
        beatmapSetID -- beatmap set ID, used to check if a map is outdated
        return -- True if set, False if not set
        """
        # Check if osuapi is enabled

        # TODO: set caching with setid

        # h = map md5, a = include converts, m = gamemode
        api_data = osuapiHelper.osuApiRequest("get_beatmaps", f"h={md5}&a=1")
        if isinstance(api_data, str):
            api_data = orjson.loads(api_data)
        print(f"test: {api_data is None}")
        if api_data is None:
            return False

        if self.rankedStatusFrozen:
            # map is still valid from md5 & ranked
            # status is frozen, no need to update.
            return True

        # save new values from osu!api
        self.songName = "{artist} - {title} [{version}]".format(**api_data)
        self.fileMD5 = md5
        self.rankedStatus = convertRankedStatus(int(api_data["approved"]))

        self.beatmapID = int(api_data["beatmap_id"])
        self.beatmapSetID = int(api_data["beatmapset_id"])

        self.AR = float(api_data["diff_approach"])
        self.OD = float(api_data["diff_overall"])
        self.gameMode = int(api_data["mode"])

        self.maxCombo = (
            int(api_data["max_combo"]) if api_data["max_combo"] is not None else 0
        )
        self.hitLength = int(api_data["hit_length"])
        if api_data["bpm"] is not None:
            self.bpm = int(float(api_data["bpm"]))
        else:
            self.bpm = -1
        return True

    def setData(self, md5: str, beatmapSetID: int, fileName: str) -> None:
        """
        Set this object's beatmap data from highest level possible.

        md5 -- beatmap MD5
        beatmapSetID -- beatmap set ID
        """
        # Get beatmap from db
        dbResult = self.setDataFromDB(md5)

        # Force refresh from osu api.
        # We get data before to keep frozen maps ranked
        # if they haven't been updated
        if dbResult and self.refresh:
            dbResult = False

        if not dbResult:
            # get from the osu!api
            # TODO: optimize by getting all maps at once using
            # the setid (provided in getscores when client has it)

            apiResult = self.setDataFromOsuApiMD5(md5)

            if not apiResult:
                if not fileName:  # no filename to search
                    self.rankedStatus = rankedStatuses.NOT_SUBMITTED
                    return

                rgx_m = MAPFILE_RGX.match(fileName)
                if not rgx_m:
                    print(f"Invalid filename objects/beatmap.py {fileName}")
                    self.rankedStatus = rankedStatuses.NOT_SUBMITTED
                    return

                rgx_m = rgx_m.groupdict()

                # ripple only stores the song name
                # without the mapper's name so :v
                # TODO: store filename with creator in db for more correct
                # XXX: maybe could also use setid if available?
                map_exists = (
                    glob.db.fetch(
                        "SELECT 1 FROM beatmaps WHERE song_name = %s",
                        ["{artist} - {title} [{version}]".format(**rgx_m)],
                    )
                    is not None
                )

                if map_exists:
                    self.rankedStatus = rankedStatuses.NEED_UPDATE
                else:
                    self.rankedStatus = rankedStatuses.NOT_SUBMITTED

            elif self.rankedStatus not in (
                rankedStatuses.NOT_SUBMITTED,
                rankedStatuses.NEED_UPDATE,
            ):
                # We get beatmap data from osu!api, save it in db
                self.addBeatmapToDB()
        else:
            log.debug("Beatmap found in db")

        # log.debug(f"{self.starsStd}\n{self.starsTaiko}\n{self.starsCtb}\n{self.starsMania}")
        # print(self.__dict__)

    def getData(self, totalScores=0):
        """
        Return this beatmap's data (header) for getscores

        return -- beatmap header for getscores
        """

        data = [f"{self.rankedStatus}|false"]

        if self.rankedStatus not in (
            rankedStatuses.NOT_SUBMITTED,
            rankedStatuses.NEED_UPDATE,
            rankedStatuses.UNKNOWN,
        ):
            # If the beatmap is updated and exists, the client needs more data
            data.append(
                f"|{self.beatmapID}|{self.beatmapSetID}|{totalScores}"
                f"\n{self.offset}\n{self.songName}\n{self.rating}\n"
            )

        # Return the header
        return "".join(data)

    def getCachedTillerinoPP(self):
        """
        Returned cached pp values for 100, 99, 98 and 95 acc nomod
        (used ONLY with Tillerino, pp is always calculated with oppai when submitting scores)

        return -- list with pp values. [0, 0, 0, 0] if not cached.
        """
        data = glob.db.fetch(
            "SELECT pp_100, pp_99, pp_98, pp_95 FROM beatmaps WHERE beatmap_md5 = %s LIMIT 1",
            [self.fileMD5],
        )
        return (
            [data["pp_100"], data["pp_99"], data["pp_98"], data["pp_95"]]
            if data
            else [0, 0, 0, 0]
        )

    def saveCachedTillerinoPP(self, l):
        """
        Save cached pp for tillerino

        l -- list with 4 default pp values ([100, 99, 98, 95])
        """
        glob.db.execute(
            "UPDATE beatmaps SET pp_100 = %s, pp_99 = %s, pp_98 = %s, pp_95 = %s WHERE beatmap_md5 = %s",
            [l[0], l[1], l[2], l[3], self.fileMD5],
        )

    @property
    def is_rankable(self):
        return self.rankedStatus >= rankedStatuses.RANKED


api2getscores_dict = {
    -2: rankedStatuses.PENDING,
    -1: rankedStatuses.PENDING,
    0: rankedStatuses.PENDING,
    1: rankedStatuses.RANKED,
    2: rankedStatuses.APPROVED,
    3: rankedStatuses.QUALIFIED,
    4: rankedStatuses.LOVED,
}


def convertRankedStatus(approvedStatus):
    """Convert approved_status (from osu!api) to ranked status (for getscores)"""
    if approvedStatus in api2getscores_dict:
        return api2getscores_dict[approvedStatus]
    else:
        return rankedStatuses.UNKNOWN


def incrementPlaycount(md5, passed):
    """
    Increment playcount (and passcount) for a beatmap

    md5 -- beatmap md5
    passed -- if True, increment passcount too
    """
    updates = "SET playcount = playcount + 1"
    if passed:
        updates += ", passcount = passcount + 1"
    glob.db.execute(f"UPDATE beatmaps {updates} WHERE beatmap_md5 = %s", [md5])
