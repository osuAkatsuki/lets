import tornado.gen
import tornado.web

from common.web import cheesegull, requestsManager
from constants import exceptions

MODULE_NAME = "direct_np"
class handler(requestsManager.asyncRequestHandler):
    """
    Handler for /web/osu-search-set.php
    """
    @tornado.web.asynchronous
    @tornado.gen.engine
    def asyncGet(self) -> None:
        output = ""
        try:
            # Get data by beatmap id or beatmapset id
            if "b" in self.request.arguments:
                _id = self.get_argument("b")
                data = cheesegull.getBeatmap(_id)
            elif "s" in self.request.arguments:
                _id = self.get_argument("s")
                data = cheesegull.getBeatmapSet(_id)
            else:
                raise exceptions.invalidArgumentsException(MODULE_NAME)

            #log.info("Requested osu!direct np: {}/{}".format("b" if "b" in self.request.arguments else "s", _id))

            # Make sure cheesegull returned some valid data
            if not data or len(data) == 0:
                raise exceptions.osuApiFailException(MODULE_NAME)

            # Write the response
            output = cheesegull.toDirectNp(data) + "\r\n"
        except (exceptions.invalidArgumentsException, exceptions.osuApiFailException, KeyError):
            output = ""
        finally:
            self.write(output)
