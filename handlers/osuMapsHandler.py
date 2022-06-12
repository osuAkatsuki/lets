import os
from urllib import parse

import tornado.gen
import tornado.web

from common.web import requestsManager
from objects import glob


class handler(requestsManager.asyncRequestHandler):
    """
    Handler for /web/maps
    """
    @tornado.web.asynchronous
    @tornado.gen.engine
    def asyncGet(self, args: str) -> None:
        file_name = parse.unquote(self.request.path.split('/')[3])
        result = glob.db.fetch('SELECT beatmap_id FROM beatmaps WHERE file_name = %s', (file_name,))
        if result:
            beatmap_id = result['beatmap_id']
            osu_path = os.path.join(glob.BEATMAPS_PATH, f'osu/{beatmap_id}.osu')

            with open(osu_path, 'rb') as f:
                while True:
                    chunk = f.read(4096)
                    if not chunk:
                        break
                    self.write(chunk)
            self.finish()
        else:
            self.destination = 'https://osu.ppy.sh/web/maps/{0}'
            self.set_status(302)
            self.add_header("location", self.destination.format(args))
