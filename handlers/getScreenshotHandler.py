from os import path
from typing import Optional

import tornado.gen
import tornado.web

from common.web import requestsManager
from constants import exceptions

MODULE_NAME = "get_screenshot"
class handler(requestsManager.asyncRequestHandler):
    """
    Handler for /ss/
    """
    @tornado.web.asynchronous
    @tornado.gen.engine
    def asyncGet(self, screenshotID: Optional[str] = None) -> None:
        try:
            # Make sure the screenshot exists
            if not screenshotID or not path.isfile(f"/home/akatsuki/screenshots/{screenshotID}"):
                raise exceptions.fileNotFoundException(MODULE_NAME, screenshotID)

            # Read screenshot
            with open(f"/home/akatsuki/screenshots/{screenshotID}") as f:
                data = f.read()

            # Display screenshot
            self.write(data)
            self.set_header("Content-type", "image/png")
            self.set_header("Content-length", len(data))
        except exceptions.fileNotFoundException:
            self.set_status(404)
