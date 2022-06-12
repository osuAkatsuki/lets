from datetime import datetime as dt

import tornado.gen
import tornado.web

from common.web import requestsManager
from helpers import replayHelper
from objects import glob

MODULE_NAME = "get_full_replay"
class handler(requestsManager.asyncRequestHandler):
    """
    Handler for /replay/
    """
    @tornado.web.asynchronous
    @tornado.gen.engine
    def asyncGet(self, score_id_str: str) -> None:
        try:
            score_id = int(score_id_str)
        except ValueError:
            self.set_status(400)
            self.write("Invalid set id")
            return

        relax = score_id < 500000000

        replay = replayHelper.buildFullReplay(
            scoreID=score_id,
            relax=relax,
        )
        if replay is not None:
            self.write(replay)
            self.add_header("Content-type", "application/octet-stream")
            self.set_header("Content-length", len(replay))
            self.set_header("Content-Description", "File Transfer")

            table = 'scores_relax' if relax else 'scores'

            res = glob.db.fetch(
                'SELECT beatmaps.song_name, users.username, {0}.time FROM {0} '
                'LEFT JOIN beatmaps USING(beatmap_md5) '
                'LEFT JOIN users ON {0}.userid = users.id '
                'WHERE {0}.id = %s'.format(table), [score_id_str]
            )

            self.set_header(
                'Content-Disposition',
                f'attachment; filename="{res["username"]} - {res["song_name"]} ({dt.fromtimestamp(res["time"]):%Y-%m-%d}).osr"')
        else:
            self.write(
                'Sorry, that replay could not be found.\n\n'
                'It is either no longer available, or has not yet been transferred from the old server.'
            )
