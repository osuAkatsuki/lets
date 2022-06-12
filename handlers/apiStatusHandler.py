import tornado.gen
import tornado.web

import orjson
from common.web import requestsManager


class handler(requestsManager.asyncRequestHandler):
    """
    Handler for /api/v1/status
    """
    @tornado.web.asynchronous
    @tornado.gen.engine
    def asyncGet(self) -> None:
        self.write(orjson.dumps({"status": 200, "server_status": 1}))
