import tornado.gen
import tornado.web

from common.log import logUtils as log
from common.ripple import userUtils
from common.web import requestsManager
from constants import exceptions
from objects import glob

MODULE_NAME = "comments"

class handler(requestsManager.asyncRequestHandler):
    CLIENT_WHO = {"normal": "", "player": "player", "admin": "bat", "donor": "subscriber"}

    @tornado.web.asynchronous
    @tornado.gen.engine
    def asyncPost(self) -> None:
        try:
            # Required arguments check
            if not requestsManager.checkArguments(self.request.arguments, ("u", "p", "a")):
                raise exceptions.invalidArgumentsException(MODULE_NAME)

            # Get arguments
            username = self.get_argument("u")
            password = self.get_argument("p")
            action = self.get_argument("a").strip().lower()

            # IP for session check
            ip = self.getRequestIP()

            # Login and ban check
            userID = userUtils.getID(username)
            if userID == 0:
                raise exceptions.loginFailedException(MODULE_NAME, userID)
            if not userUtils.checkLogin(userID, password, ip):
                raise exceptions.loginFailedException(MODULE_NAME, username)
            if userUtils.isBanned(userID):
                raise exceptions.userBannedException(MODULE_NAME, username)

            # Action (depends on 'action' parameter, not on HTTP method)
            if action == "get":
                self.write(self._getComments())
            elif action == "post":
                self._addComment()
        except (exceptions.loginFailedException, exceptions.userBannedException):
            self.write("error: no")

    @staticmethod
    def clientWho(y):
        return handler.CLIENT_WHO[y["who"]] + (
            (f"|{y['special_format']}") if y["special_format"] else ""
        )

    def _getComments(self):
        output = ""

        try:
            beatmapID = int(self.get_argument("b", default=0))
            beatmapSetID = int(self.get_argument("s", default=0))
            scoreID = int(self.get_argument("r", default=0))
        except ValueError:
            raise exceptions.invalidArgumentsException(MODULE_NAME)

        if beatmapID <= 0:
            return

        log.info(f"Requested comments for beatmap id {beatmapID}")

        # Merge beatmap, beatmapset and score comments
        for x in (
                {"db_type": "beatmap_id", "client_type": "map", "value": beatmapID},
                {"db_type": "beatmapset_id", "client_type": "song", "value": beatmapSetID},
                {"db_type": "score_id", "client_type": "replay", "value": scoreID},
        ):
            # Add this set of comments only if the client has set the value
            if x["value"] <= 0:
                continue

            # Fetch these comments
            comments = glob.db.fetchAll(
                f"SELECT * FROM comments WHERE {x['db_type']} = %s ORDER BY `time`",
                (x["value"],)
            )

            # Output comments
            output += "\n".join([
                "{y[time]}\t{client_name}\t{client_who}\t{y[comment]}".format(
                    y=y,
                    client_name=x["client_type"],
                    client_who=self.clientWho(y)
                ) for y in comments
            ]) + "\n"
        return output

    def _addComment(self):
        username = self.get_argument("u")
        target = self.get_argument("target", default=None)
        specialFormat = self.get_argument("f", default=None)
        userID = userUtils.getID(username)

        # Technically useless
        if userID < 0:
            return

        # Get beatmap/set/score ids
        try:
            beatmapID = int(self.get_argument("b", default=0))
            beatmapSetID = int(self.get_argument("s", default=0))
            scoreID = int(self.get_argument("r", default=0))
        except ValueError:
            raise exceptions.invalidArgumentsException(MODULE_NAME)

        # Add a comment, removing all illegal characters and trimming after 128 characters
        comment = self.get_argument("comment").replace("\r", "").replace("\t", "").replace("\n", "")[:128]
        try:
            time_ = int(self.get_argument("starttime"))
        except ValueError:
            raise exceptions.invalidArgumentsException(MODULE_NAME)

        # Get users privileges to check if they are staff or donor
        privileges = userUtils.getPrivileges(userID)

        # Type of comment
        who = "normal"
        if target == "replay" and glob.db.fetch(
            "SELECT COUNT(*) AS c FROM scores WHERE id = %s AND userid = %s AND completed = 3",
            (scoreID, userID)
        )["c"] > 0:
            # From player, on their score
            who = "player"
        elif privileges & 8:
            # From Akatsuki staff member
            who = "admin"
        elif privileges & 4:
            # Akatsuki Premium Member
            who = "donor"

        if target == "song":
            # Set comment
            if beatmapSetID <= 0:
                return
            value = beatmapSetID
            column = "beatmapset_id"
        elif target == "map":
            # Beatmap comment
            if beatmapID <= 0:
                return
            value = beatmapID
            column = "beatmap_id"
        elif target == "replay":
            # Score comment
            if scoreID <= 0:
                return
            value = scoreID
            column = "score_id"
        else:
            # Invalid target
            return

        # Make sure the user hasn't submitted another comment on the same map/set/song in a 5 seconds range
        if glob.db.fetch(
            f"SELECT COUNT(*) AS c FROM comments WHERE user_id = %s AND {column} = %s AND `time` BETWEEN %s AND %s",
            (userID, value, time_ - 5000, time_ + 5000)
        )["c"] > 0:
            return

        # Store the comment
        glob.db.execute(
            f"INSERT INTO comments ({column}, user_id, comment, `time`, who, special_format) "
            "VALUES (%s, %s, %s, %s, %s, %s)",
            (value, userID, comment, time_, who, specialFormat)
        )
        log.info(f"Submitted {column} ({value}) comment, user {userID}: '{comment}'")
