import hashlib
import os
import tempfile
from typing import Dict, Optional, Tuple
from zipfile import ZipFile

import tornado.gen
import tornado.web

from common.log import logUtils as log
from common.ripple import userUtils
from common.web import requestsManager
from constants import exceptions
from objects import glob
from osz2_decryptor.osz2_decryptor import Osz2Package

MODULE_NAME = "osu-osz2-bmsubmit-upload"
class handler(requestsManager.asyncRequestHandler):
    """
    Handler for /web/osu-osz2-bmsubmit-upload.php
    """
    @tornado.web.asynchronous
    @tornado.gen.engine
    def asyncPost(self) -> None:
        try:
            # Get request ip
            ip = self.getRequestIP()

            # Argument check
            if not requestsManager.checkArguments(self.request.arguments, ["u", "h", "s", "t", "z"]):
                raise exceptions.invalidArgumentsException(MODULE_NAME)

            username: str = self.get_argument("u")
            user_id = userUtils.getID(username)
            if not user_id:
                raise exceptions.beatmapSubmitAuthException(MODULE_NAME, username)

            password: str = self.get_argument("h")

            if not userUtils.checkLogin(user_id, password, ip):
                raise exceptions.beatmapSubmitAuthException(MODULE_NAME, username)

            beatmap_set_id = int(self.get_argument("s"))
            full_submit = self.get_argument("t") == '1'
            client_osz2_hash = self.get_argument("z")

            osz2_hash = None
            ranked_status = 0
            creator_id = 0

            info = self.fetch_info(beatmap_set_id)
            if info is None:
                raise exceptions.beatmapSubmitNotExistException(MODULE_NAME, username)

            (creator_id, ranked_status) = info

            if user_id != creator_id:
                raise exceptions.beatmapSubmitOwnershipException(MODULE_NAME, username)

            if ranked_status > 1:
                raise exceptions.beatmapSubmitRankedException(MODULE_NAME, username)

            osz2_file: bytes = self.request.files['osz2'][0]['body']

            package: Optional[Osz2Package] = None

            fd, tmp_path = tempfile.mkstemp()
            try:
                with os.fdopen(fd, 'wb') as tmp:
                    tmp.write(osz2_file)
                    # We're can use path only because of how C#'s FileStream.Position works
                    package = Osz2Package(tmp_path)
                    if not package.read():
                        raise exceptions.beatmapSubmitParseException(MODULE_NAME, username)
            # TODO: catch
            finally:
                os.remove(tmp_path)

            first = True
            new_submission = glob.db.fetch('SELECT bpm '
                                           'FROM beatmaps '
                                           'WHERE beatmapset_id = %s', (beatmap_set_id,))['bpm'] == 0
            beatmap_id_list_raw = glob.db.fetchAll('SELECT beatmap_id '
                                                   'FROM beatmaps '
                                                   'WHERE beatmapset_id = %s', (beatmap_set_id,))
            beatmap_id_list = [row['beatmap_id'] for row in beatmap_id_list_raw]
            tags = ''

            for beatmap_id in beatmap_id_list:
                if beatmap_id not in package.file_ids:
                    continue

                file_name = package.file_ids[beatmap_id]
                beatmap_contents = package.files[file_name]
                beatmap_contents_str = beatmap_contents.decode("utf-8")
                beatmap_info = self.beatmap_parse(beatmap_contents_str)

                if first:
                    tags = beatmap_info['Tags'].replace(',', ' ')
                    tags = tags.replace('  ', ' ')
                    tags = tags.lower()

                    if len(tags) >= 1000:
                        raise exceptions.beatmapSubmitLongTagsException()

                    first = False

                song_name = '{Artist} - {Title} [{Version}]'.format(**beatmap_info)
                beatmap_md5 = hashlib.md5(beatmap_contents).hexdigest()
                ar = float(beatmap_info["ApproachRate"])
                od = float(beatmap_info["OverallDifficulty"])
                mode = int(beatmap_info["Mode"])
                bpm = float(beatmap_info["BPM"])

                osu_path = os.path.join(glob.BEATMAPS_PATH, f'osu/{beatmap_id}.osu')
                with open(osu_path, 'w') as file:
                    file.write(beatmap_contents_str)

                # TODO: calculate beatmap md5 before file creation
                md5 = hashlib.md5()
                beatmap_md5: str = ''
                with open(osu_path, "rb") as f:
                    for chunk in iter(lambda: f.read(4096), b""):
                        md5.update(chunk)
                    beatmap_md5 = md5.hexdigest()

                glob.db.execute('UPDATE beatmaps '
                                'SET song_name = %s, file_name = %s, beatmap_md5 = %s, tags = %s, ar = %s, od = %s, mode = %s, bpm = %s, latest_update = UNIX_TIMESTAMP() '
                                'WHERE beatmap_id = %s', (song_name, file_name, beatmap_md5, tags, ar, od, mode, bpm, beatmap_id,))

            self.save_package(beatmap_set_id, package)

            if new_submission:
                log.info(f'{username} has submitted new map!')
            else:
                log.info(f'{username} has updated his map!')

            self.write('0')

        except exceptions.beatmapSubmitAuthException:
            self.write(f'5\nAuthentication failure. Please check your login details.')
        except exceptions.beatmapSubmitRestrictionException:
            self.write(f'5\nYour account is currently restricted.')
        except exceptions.beatmapSubmitNotExistException:
            self.write(f'6\nThe beatmap you are trying to upload does not exist on the server.')
        except exceptions.beatmapSubmitOwnershipException:
            self.write(f'1\nYou are not the creator of this map set')
        except exceptions.beatmapSubmitRankedException:
            self.write(f'3\nAlready ranked to some extent! Can not submit.')
        except exceptions.beatmapSubmitLongTagsException:
            self.write(f'3\nTags are too long.')
        except exceptions.beatmapSubmitParseException:
            self.write(f'3\nSomething happend while uploading beatmap.')
        except exceptions.invalidArgumentsException:
            pass

    def fetch_info(self, beatmap_set_id: int) -> Optional[Tuple[int, int]]:
        info = glob.db.fetch('SELECT submitted_by, ranked '
                             'FROM beatmaps '
                             'WHERE beatmapset_id = %s', (beatmap_set_id,))
        if info is None:
            return

        return (info['submitted_by'], info['ranked'])

    def beatmap_parse(self, contents: str) -> Dict[str, str]:
        lines = contents.splitlines()
        current_section = 0

        kvp: dict[str, str] = {}

        for line in lines:
            if not line:
                current_section = 0
            elif line == '[General]':
                current_section = 1
            elif line == '[Metadata]':
                current_section = 2
            elif line == '[Difficulty]':
                current_section = 3
            elif line == '[TimingPoints]':
                current_section = 4

            if current_section in (1, 2, 3):
                split = line.split(':')
                if len(split) == 2:
                    kvp[split[0]] = split[1].lstrip()
                else:
                    kvp[split[0]] = ''
            elif current_section == 4:
                if 'BPM' not in kvp:
                    split = line.split(',')
                    if len(split) > 1:
                        beat_length = float(split[1])
                        if beat_length > 0:
                            kvp['BPM'] = str(1000 / beat_length * 60)
        return kvp

    def save_package(self, beatmap_set_id: int, package: Osz2Package) -> None:
        osz_path = os.path.join(glob.BEATMAPS_PATH, f'osz/{beatmap_set_id}.osz')

        with ZipFile(osz_path, 'w') as zip:
            for file_name, contents in package.files.items():
                zip.writestr(file_name, contents)
