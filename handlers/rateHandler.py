import tornado.gen
import tornado.web

from common.ripple import userUtils
from common.web import requestsManager
from constants import exceptions, rankedStatuses
from objects import glob

MODULE_NAME = "rate"


class handler(requestsManager.asyncRequestHandler):
    @tornado.web.asynchronous
    @tornado.gen.engine
    def asyncGet(self) -> None:
        output: str = ""

        try:
            if not requestsManager.checkArguments(self.request.arguments, ["c", "u", "p"]):
                raise exceptions.invalidArgumentsException(MODULE_NAME)

            username = self.get_argument("u", None)
            checksum = self.get_argument("c", None)

            userID = userUtils.getID(username)

            if not userID:
                raise exceptions.loginFailedException(MODULE_NAME, userID)
            if not userUtils.checkLogin(userID, self.get_argument("p"), self.getRequestIP()):
                raise exceptions.loginFailedException(MODULE_NAME, username)

            ranked = glob.db.fetch(
                "SELECT ranked FROM beatmaps WHERE beatmap_md5 = %s LIMIT 1",
                (checksum,)
            )
            if not ranked:
                output = "no exist"
                return
            if ranked["ranked"] < rankedStatuses.RANKED:
                output = "not ranked"
                return

            rating = glob.db.fetch("SELECT rating FROM beatmaps WHERE beatmap_md5 = %s LIMIT 1", (checksum,))
            has_voted = glob.db.fetch(
                "SELECT id FROM beatmaps_rating WHERE user_id = %s AND beatmap_md5 = %s LIMIT 1",
                (userID, checksum)
            )
            if has_voted:
                output = f"alreadyvoted\n{rating['rating']:.2f}"
                return
            vote = self.get_argument("v", default=None)
            if not vote:
                output = "ok"
                return
            try:
                vote = int(vote)
            except ValueError:
                raise exceptions.invalidArgumentsException(MODULE_NAME)

            if not 0 <= vote <= 10:
                output = "out of range"
                return

            glob.db.execute(
                "REPLACE INTO beatmaps_rating (beatmap_md5, user_id, rating) VALUES (%s, %s, %s)",
                (checksum, userID, vote)
            )
            glob.db.execute(
                "UPDATE beatmaps SET rating = (SELECT SUM(rating)/COUNT(rating) FROM beatmaps_rating "
                "WHERE beatmap_md5 = %(md5)s) WHERE beatmap_md5 = %(md5)s LIMIT 1",
                {"md5": checksum}
            )

            rating = glob.db.fetch("SELECT rating FROM beatmaps WHERE beatmap_md5 = %s LIMIT 1", (checksum,))
            output = f"{rating['rating']:.2f}"
        except exceptions.loginFailedException:
            output = "auth failed"
        except exceptions.invalidArgumentsException:
            output = "no"
        finally:
            self.write(output)
