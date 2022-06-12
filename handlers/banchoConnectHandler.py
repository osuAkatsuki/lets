import tornado.gen
import tornado.web

from common.log import logUtils as log
from common.ripple import userUtils
from common.web import requestsManager
from constants import exceptions
from objects import glob

MODULE_NAME = "bancho_connect"
class handler(requestsManager.asyncRequestHandler):
    """
    Handler for /web/bancho_connect.php
    """
    @tornado.web.asynchronous
    @tornado.gen.engine
    def asyncGet(self) -> None:
        try:
            # Get request ip
            ip = self.getRequestIP()

            # Argument check
            if not requestsManager.checkArguments(self.request.arguments, ["u", "h", "retry"]):
                raise exceptions.invalidArgumentsException(MODULE_NAME)

            # XXX: tempfix for outdated stable builds
            # that doesn't yet support -devbuild.
            if self.get_argument("retry") == "1":
                return self.write("https://ct.akatsuki.pw")

            # Get user ID
            username = self.get_argument("u")
            userID = userUtils.getID(username)
            if not userID:
                raise exceptions.loginFailedException(MODULE_NAME, username)

            # Check login
            log.info(f"{username} ({userID}) wants to connect")
            if not userUtils.checkLogin(userID, self.get_argument("h"), ip):
                raise exceptions.loginFailedException(MODULE_NAME, username)

            # Ban check
            if userUtils.isBanned(userID):
                raise exceptions.userBannedException(MODULE_NAME, username)

            # Lock check
            if userUtils.isLocked(userID):
                raise exceptions.userLockedException(MODULE_NAME, username)

            # Update latest activity
            userUtils.updateLatestActivity(userID)

            # Get country and output it
            self.write(glob.db.fetch("SELECT country FROM users_stats WHERE id = %s", [userID])["country"])
        except exceptions.invalidArgumentsException:
            pass
        except exceptions.loginFailedException:
            self.write("error: pass\n")
        except exceptions.userBannedException:
            pass
        except exceptions.userLockedException:
            pass
