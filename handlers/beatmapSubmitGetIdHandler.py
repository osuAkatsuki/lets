import os
from typing import List, Optional, Tuple

import tornado.gen
import tornado.web

from common.ripple import userUtils
from common.web import requestsManager
from constants import exceptions
from objects import glob

MODULE_NAME = "osu-osz2-bmsubmit-getid"
class handler(requestsManager.asyncRequestHandler):
    """
    Handler for /web/osu-osz2-bmsubmit-getid.php
    """
    @tornado.web.asynchronous
    @tornado.gen.engine
    def asyncGet(self) -> None:
        try:
            # Get request ip
            ip = self.getRequestIP()

            # Argument check
            if not requestsManager.checkArguments(self.request.arguments, ["u", "h", "s", "b", "z"]):
                raise exceptions.invalidArgumentsException(MODULE_NAME)

            username: str = self.get_argument("u")
            user_id = userUtils.getID(username)
            if not user_id:
                raise exceptions.beatmapSubmitAuthException(MODULE_NAME, username)

            password: str = self.get_argument("h")

            if not userUtils.checkLogin(user_id, password, ip):
                raise exceptions.beatmapSubmitAuthException(MODULE_NAME, username)

            beatmap_set_id = int(self.get_argument("s"))
            beatmap_ids_raw: str = self.get_argument("b")
            old_osz2_hash: str = self.get_argument("z")

            new_submit = False
            upload_cap = 0
            creator_id = -1
            ranked_status = 0

            info = self.fetch_info(beatmap_set_id)
            if beatmap_set_id > 0 and info:
                (creator_id, ranked_status) = info

                if creator_id != user_id:
                    raise exceptions.beatmapSubmitOwnershipException(MODULE_NAME, username)
                if ranked_status > 1:
                    raise exceptions.beatmapSubmitRankedException(MODULE_NAME, username)
            else:
                upload_cap = self.get_upload_cap(user_id)
                beatmap_set_id = self.create_beatmap_set(user_id)
                new_submit = True

            beatmap_ids = beatmap_ids_raw.split(',')

            beatmap_ids = self.renew_invalid_beatmaps(beatmap_ids, beatmap_set_id, user_id)

            server_osz2_hash = self.get_osz2_hash(beatmap_set_id)
            full_submit = new_submit or old_osz2_hash == '0' or not server_osz2_hash or server_osz2_hash != old_osz2_hash

            beatmap_ids_str = ",".join(map(str, beatmap_ids))

            # inline
            self.write(f'0\n{beatmap_set_id}\n{beatmap_ids_str}\n{"1" if full_submit else "2"}\n{upload_cap}\n0\n{ranked_status}')

        except exceptions.beatmapSubmitAuthException:
            self.write(f'5\nAuthentication failure. Please check your login details.')
        except exceptions.beatmapSubmitRestrictionException:
            self.write(f'5\nYour account is currently restricted.')
        except exceptions.beatmapSubmitOwnershipException:
            self.write(f'1\n')
        except exceptions.beatmapSubmitRankedException:
            self.write(f'3\n')
        except exceptions.invalidArgumentsException:
            pass

    def fetch_info(self, beatmap_set_id: int) -> Optional[Tuple[int, int]]:
        row = glob.db.fetch('SELECT submitted_by, ranked '
                            'FROM beatmaps '
                            'WHERE beatmapset_id = %s', (beatmap_set_id,))
        if row is None:
            return

        return (row['submitted_by'], row['ranked'])

    def get_osz2_hash(self, beatmap_set_id: int) -> Optional[str]:
        row = glob.db.fetch('SELECT osz2_hash '
                            'FROM beatmaps '
                            'WHERE beatmapset_id = %s', (beatmap_set_id,))
        if row is None:
            return

        return row['osz2_hash']

    def get_upload_cap(self, user_id: int) -> int:
        try:
            unranked_count = glob.db.fetch('SELECT COUNT(*) AS count '
                                           'FROM beatmaps '
                                           'WHERE ranked = 0 '
                                           'AND submitted_by = %s AND osz2_hash IS NOT NULL', (user_id,))['count']

            ranked_count = glob.db.fetch('SELECT COUNT(*) AS count '
                                         'FROM beatmaps '
                                         'WHERE ranked > 1 '
                                         'AND submitted_by = %s AND osz2_hash IS NOT NULL', (user_id,))['count']

            # TODO: if user is supporter adjust upload cap
            map_allowance = 5 + min(3, ranked_count)

            if unranked_count + 1 > map_allowance:
                raise exceptions.beatmapSubmitSubmissionCapException

        except exceptions.beatmapSubmitSubmissionCapException:
            self.write(f'6\nYou have exceeded your submission cap.')

        return map_allowance - unranked_count

    def create_beatmap_set(self, user_id: int) -> int:
        if glob.last_inserted_set_id == 0:
            result = glob.db.fetch('SELECT MAX(beatmapset_id) as last_set_id '
                                   'FROM beatmaps')['last_set_id']

            glob.last_inserted_set_id = result if result and result >= glob.BEATMAPS_START_INDEX else glob.BEATMAPS_START_INDEX

        if glob.last_inserted_map_id == 0:
            result = glob.db.fetch('SELECT MAX(beatmap_id) as last_map_id '
                                   'FROM beatmaps')['last_map_id']

            glob.last_inserted_map_id = result if result and result >= glob.BEATMAPS_START_INDEX else glob.BEATMAPS_START_INDEX
        glob.last_inserted_map_id += 1

        glob.db.execute('INSERT INTO beatmaps (beatmap_id, song_name, beatmap_md5, submitted_by, ranked, submitted_on) '
                        'VALUES (%s, NULL, NULL, %s, 0, CURRENT_TIMESTAMP())', (glob.last_inserted_map_id, user_id, ))

        glob.last_inserted_set_id += 1
        return glob.last_inserted_set_id

    def renew_invalid_beatmaps(self, beatmap_ids: List[str], beatmap_set_id: int, user_id: int) -> List[int]:
        current_beatmap_ids_raw = glob.db.fetchAll('SELECT beatmap_id '
                                                   'FROM beatmaps '
                                                   'WHERE beatmapset_id = %s', (beatmap_set_id,))
        current_beatmap_ids = [row['beatmap_id'] for row in current_beatmap_ids_raw]

        for i in range(len(beatmap_ids)):
            beatmap_id_str = beatmap_ids[i]
            if not beatmap_id_str.isdecimal():
                continue

            beatmap_id = int(beatmap_id_str)
            if beatmap_id > 0 and beatmap_id in current_beatmap_ids:
                current_beatmap_ids.remove(beatmap_id)
                continue

            if glob.last_inserted_map_id == 0:
                result = glob.db.fetch('SELECT MAX(beatmap_id) as last_map_id '
                                       'FROM beatmaps')['last_map_id']

                glob.last_inserted_map_id = result if result and result >= glob.BEATMAPS_START_INDEX else glob.BEATMAPS_START_INDEX

            glob.last_inserted_map_id += 1

            glob.db.execute('INSERT INTO beatmaps (beatmap_id, submitted_by, beatmapset_id, ranked) '
                            'VALUES (%s, %s, %s, 0)', ([glob.last_inserted_map_id, user_id, beatmap_set_id,]))

            beatmap_ids[i] = glob.last_inserted_map_id

        # delete files that have not been removed from current_beatmap_ids list
        # because they're most likely not used anymore and just take up space on the server
        for beatmap_id in current_beatmap_ids:
            glob.db.execute('DELETE FROM beatmaps '
                            'WHERE beatmap_id = %s', (beatmap_id,))
            self.delete_osu_file(beatmap_id)

        return beatmap_ids

    def delete_osu_file(self, beatmap_id: int) -> None:
        path = os.path.join(glob.BEATMAPS_PATH, f'osu/{beatmap_id}.osu')
        if os.path.exists(path):
            os.remove(path)
