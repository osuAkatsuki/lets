from imghdr import test_jpeg, test_png
from os import path

import tornado.gen
import tornado.web

from common import generalUtils
from common.ripple import userUtils
from common.web import requestsManager
from constants import exceptions
from objects import glob

#from PIL import Image


MODULE_NAME = "screenshot"
SCREENSHOT_PATH = "/home/akatsuki/screenshots/{}.png"

class handler(requestsManager.asyncRequestHandler):
    """
    Handler for /web/osu-screenshot.php
    """
    @tornado.web.asynchronous
    @tornado.gen.engine
    def asyncPost(self) -> None:
        try:
            if glob.debug: requestsManager.printArguments(self)

            # Check user auth because of sneaky people + verify a file is acc being sent
            if not (
                requestsManager.checkArguments(self.request.arguments, ("u", "p")) and
                "ss" in self.request.files
            ): raise exceptions.invalidArgumentsException(MODULE_NAME)
            username = self.get_argument("u")
            password = self.get_argument("p")

            userID = userUtils.getID(username)
            if not userUtils.checkLogin(userID, password):
                raise exceptions.loginFailedException(MODULE_NAME, username)

            # Rate limit
            if glob.redis.get(f"lets:screenshot:{userID}"):
                return self.write("no")
            glob.redis.set(f"lets:screenshot:{userID}", 1, ex=30)

            file = self.request.files["ss"][0]["body"]

            # Ensure the file actually being uploaded is an image.
            if not (
                test_jpeg(file, None) or
                test_png(file, None)
            ): raise exceptions.invalidArgumentsException(MODULE_NAME)

            # Get a random screenshot id
            screenshotID = generalUtils.randomString(8)
            while path.exists(SCREENSHOT_PATH.format(screenshotID)):
                pass # avoid overwriting

            # Write screenshot file to .data folder
            with open(SCREENSHOT_PATH.format(screenshotID), "wb") as f:
                f.write(file)

            # Add Akatsuki's watermark
            # Disabled for the time being..
            """
            base_screenshot = Image.open(f'/home/akatsuki/screenshots/{screenshotID}.png')
            _watermark = Image.open('../hanayo/static/logos/logo.png')
            watermark = _watermark.resize((_watermark.width // 3, _watermark.height // 3))
            width, height = base_screenshot.size

            transparent = Image.new('RGBA', (width, height), (0,0,0,0))
            transparent.paste(base_screenshot, (0,0))
            transparent.paste(watermark, (width - 330, height - 200), mask=watermark)
            watermark.close()
            transparent.save(f'/home/akatsuki/screenshots/{screenshotID}.png')
            transparent.close()
            """

            # Output
            #log.info("New screenshot ({})".format(screenshotID))

            # Return screenshot link
            self.write(f"{glob.conf.config['server']['servername']}/ss/{screenshotID}.png")
        except exceptions.invalidArgumentsException:
            pass
        except exceptions.loginFailedException:
            pass
