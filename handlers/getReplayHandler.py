import requests
import tornado.gen
import tornado.web

from common.log import logUtils as log
from common.ripple import userUtils
from common.web import requestsManager
from constants import exceptions
from objects import glob

MODULE_NAME = "get_replay"


class handler(requestsManager.asyncRequestHandler):
    """
    Handler for osu-getreplay.php
    """

    @tornado.web.asynchronous
    @tornado.gen.engine
    def asyncGet(self) -> None:
        try:
            # Check arguments
            if not requestsManager.checkArguments(
                self.request.arguments, ["c", "u", "h"]
            ):
                raise exceptions.invalidArgumentsException(MODULE_NAME)

            # Get arguments
            username = self.get_argument("u")
            replayID = self.get_argument("c")

            # Login check
            userID = userUtils.getID(username)
            if userID == 0:
                raise exceptions.loginFailedException(MODULE_NAME, userID)
            if not userUtils.checkLogin(
                userID, self.get_argument("h"), self.getRequestIP()
            ):
                raise exceptions.loginFailedException(MODULE_NAME, username)

            replayData = glob.db.fetch(
                "SELECT scores{_relax}.userid, scores{_relax}.play_mode, scores{_relax}.mods, users.username AS uname FROM scores{_relax} LEFT JOIN users ON scores{_relax}.userid = users.id WHERE scores{_relax}.id = %s LIMIT 1".format(
                    _relax="_relax" if int(replayID) < 500000000 else ""
                ),
                [replayID],
            )

            # Increment 'replays watched by others' if needed
            if replayData:
                if username != replayData["uname"]:
                    userUtils.incrementReplaysWatched(
                        replayData["userid"],
                        replayData["play_mode"],
                        replayData["mods"],
                    )

            log.info(f"Serving replay_{replayID}.osr")

            req = requests.get(f"http://localhost:8484/get?id={replayID}")
            if not req or req.status_code != 200:
                return self.write("")

            return self.write(req.content)

        except exceptions.invalidArgumentsException:
            pass
        except exceptions.loginFailedException:
            pass
