import tornado.gen
import tornado.web

from common.web import cheesegull, requestsManager
from constants import exceptions
from objects import glob

MODULE_NAME = "direct"


class handler(requestsManager.asyncRequestHandler):
    """
    Handler for /web/osu-search.php
    """

    @tornado.web.asynchronous
    @tornado.gen.engine
    def asyncGet(self) -> None:
        output: list[str] = []
        try:
            try:
                # Get arguments
                gameMode = self.get_argument("m", None)
                if gameMode is not None and gameMode.isdecimal():
                    gameMode = int(gameMode)
                    if gameMode < 0 or gameMode > 3:
                        gameMode = None

                if gameMode == "-1" or gameMode == -1:
                    gameMode = None

                rankedStatus = self.get_argument("r", None)
                if rankedStatus:
                    rankedStatus = int(rankedStatus)

                query = self.get_argument("q", "")
                page = int(self.get_argument("p", "0"))

                # TODO
                if query.lower() in {"newest", "top rated", "most played"}:
                    query = ""
            except ValueError:
                raise exceptions.invalidArgumentsException(MODULE_NAME)

            # Get data from cheesegull API
            # log.info("Requested osu!direct search: {}".format(query if query != "" else "index"))
            MINO = "catboy.best" in glob.conf.config["mirror"]["apiurl"]

            searchData = cheesegull.getListing(
                rankedStatus=cheesegull.directToApiStatus(rankedStatus),
                page=page * 100 if not MINO else page,
                gameMode=gameMode,
                query=query,
            )
            if MINO:
                if searchData:
                    self.write(searchData)

                return

            if not searchData or not searchData:
                raise exceptions.noAPIDataError()

            # Write output
            if len(searchData) == 100:
                output.append("101")  # send >100 so they know mores available
            else:
                output.append(str(len(searchData)))

            for beatmapSet in searchData:
                try:
                    output.append(cheesegull.toDirect(beatmapSet))
                except ValueError:
                    # Invalid cheesegull beatmap (empty beatmapset, cheesegull bug? See Sentry #LETS-00-32)
                    pass
        except (exceptions.noAPIDataError, exceptions.invalidArgumentsException):
            output.append("0\n")
        finally:
            self.write("\n".join(output))
