import tornado.gen
import tornado.web

from common.web import requestsManager

MODULE_NAME = "direct_download"


class handler(requestsManager.asyncRequestHandler):
    """
    Handler for /d/
    """

    @tornado.web.asynchronous
    @tornado.gen.engine
    def asyncGet(self, beatmap_id_str: str) -> None:
        try:
            # TODO: re-add no-video support??
            no_video = int(beatmap_id_str.endswith("n"))
            if no_video:
                beatmap_id_str = beatmap_id_str[:-1]

            beatmap_id = int(beatmap_id_str)
            self.redirect(
                url=f"https://catboy.best/d/{beatmap_id}",
                permanent=False,
            )

            # req = requests.get(f"http://localhost:9292/d/{bid}")
            # req = requests.get(f"https://catboy.best/d/{bid}")
            # map_bytes = req.content

            # self.add_header("Cache-Control", "no-cache")
            # self.add_header("Pragma", "no-cache")
            # self.add_header("Content-Type", "application/octet-stream")
            # self.add_header("Content-Description", "File Transfer")
            # self.add_header("Content-Disposition", req.headers["Content-Disposition"])

            # self.set_status(200)
            # self.write(map_bytes)
        except ValueError:
            self.set_status(400)
            self.write("Invalid set id")
