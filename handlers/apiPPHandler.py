from typing import cast

import tornado.gen
import tornado.web

import orjson
from common.constants import gameModes
from common.log import logUtils as log
from common.web import requestsManager
from constants import exceptions
from helpers import osuapiHelper
from objects import beatmap, glob
from pp import cicciobello, rippoppai

MODULE_NAME = "api/pp"


class handler(requestsManager.asyncRequestHandler):
    """
    Handler for /api/v1/pp
    """

    @tornado.web.asynchronous
    @tornado.gen.engine
    def asyncGet(self) -> None:
        statusCode = 400
        data = {"message": "unknown error"}
        try:
            # Check arguments
            if not requestsManager.checkArguments(self.request.arguments, ["b"]):
                raise exceptions.invalidArgumentsException(MODULE_NAME)

            # Get beatmap ID and make sure it's a valid number
            try:
                beatmapID = int(cast(str, self.get_argument("b")))
            except ValueError:
                raise exceptions.invalidArgumentsException(MODULE_NAME)

            # Get mods
            if "m" in self.request.arguments:
                try:
                    modsEnum = int(cast(str, self.get_argument("m")))
                except ValueError:
                    raise exceptions.invalidArgumentsException(MODULE_NAME)
            else:
                modsEnum = 0

            # Get game mode
            if "g" in self.request.arguments:
                try:
                    gameMode = int(cast(str, self.get_argument("g")))
                except ValueError:
                    raise exceptions.invalidArgumentsException(MODULE_NAME)
            else:
                # use bmap mode as default (once we get it)
                gameMode = None

            # Get acc
            if "a" in self.request.arguments:
                try:
                    accuracy = float(cast(str, self.get_argument("g")))
                except ValueError:
                    raise exceptions.invalidArgumentsException(MODULE_NAME)
            else:
                accuracy = -1.0

            # Print message
            log.info(f"Requested pp for beatmap {beatmapID}")

            # Get beatmap md5 from osuapi
            # TODO: Move this to beatmap object
            beatmapMd5 = ""
            beatmapSetID = 0
            if beatmapID < glob.BEATMAPS_START_INDEX:
                osuapiData = osuapiHelper.osuApiMapRequest(f"?b={beatmapID}")
                if not osuapiData:
                    raise exceptions.invalidBeatmapException(MODULE_NAME)
                if isinstance(osuapiData, str):
                    osuapiData = orjson.loads(osuapiData)
                if (
                    not osuapiData
                    or "file_md5" not in osuapiData
                    or "beatmapset_id" not in osuapiData
                ):
                    raise exceptions.invalidBeatmapException(MODULE_NAME)
                beatmapMd5 = osuapiData["file_md5"]
                beatmapSetID = osuapiData["beatmapset_id"]
            else:
                dbResult = glob.db.fetch(
                    "SELECT beatmap_md5, beatmapset_id FROM beatmaps WHERE beatmap_id = %s",
                    (beatmapID,),
                )
                beatmapMd5 = dbResult["beatmap_md5"]
                beatmapSetID = dbResult["beatmapset_id"]

            # Create beatmap object
            bmap = beatmap.beatmap(beatmapMd5, beatmapSetID)

            # Check beatmap length
            if bmap.hitLength > 900:
                raise exceptions.myServerSucksException(MODULE_NAME)

            if gameMode is None:
                gameMode = bmap.gameMode

            returnPP = []
            returnSR = 0.0

            # Calculate pp
            if gameMode in (gameModes.STD, gameModes.TAIKO):
                # Std pp
                if accuracy < 0 and modsEnum == 0:
                    # Generic acc
                    oppai = rippoppai.oppai(bmap, mods=modsEnum, tillerino=True)
                    returnPP = oppai.pp
                    returnSR = oppai.stars

                else:
                    # Specific accuracy, calculate
                    # Create oppai instance
                    log.debug(
                        f"Specific request ({accuracy}%/{modsEnum}). "
                        "Calculating pp with oppai..."
                    )
                    oppai = rippoppai.oppai(bmap, mods=modsEnum, tillerino=True)
                    returnSR = oppai.stars
                    if accuracy > 0:
                        returnPP.append(calculatePPFromAcc(oppai, accuracy))
                    else:
                        returnPP = oppai.pp
            elif gameMode == gameModes.CTB:
                # osu!catch
                ciccio = cicciobello.Cicciobello(
                    bmap, mods_=modsEnum, tillerino=accuracy is None, accuracy=accuracy
                )
                returnSR = ciccio.stars
                returnPP = ciccio.pp
            else:
                raise exceptions.unsupportedGameModeException

            # Data to return
            data = {
                "song_name": bmap.songName,
                "pp": returnPP if isinstance(returnPP, list) else returnPP,
                "game_mode": gameMode,
                "length": bmap.hitLength,
                "stars": returnSR,
                "ar": bmap.AR,
                "bpm": bmap.bpm,
            }

            # Set status code and message
            statusCode = 200
            data["message"] = "ok"
        except exceptions.invalidArgumentsException:
            # Set error and message
            statusCode = 400
            data["message"] = "missing required arguments"
        except exceptions.invalidBeatmapException:
            statusCode = 400
            data["message"] = "beatmap not found"
        except exceptions.myServerSucksException:
            statusCode = 400
            data["message"] = "requested beatmap is too long"
        except exceptions.unsupportedGameModeException:
            statusCode = 400
            data["message"] = "Unsupported gamemode"
        finally:
            # Add status code to data
            data["status"] = statusCode

            # Debug output
            log.debug(str(data))

            # Send response
            # self.clear()
            self.write(orjson.dumps(data))
            self.set_header("Content-Type", "application/json")
            self.set_status(statusCode)


def calculatePPFromAcc(ppcalc, acc):
    ppcalc.acc = acc
    ppcalc.calculatePP()
    return ppcalc.pp
