from os import path, remove

from common import generalUtils
from common.log import logUtils as log
from constants import exceptions
from helpers import osuapiHelper
from objects import glob


def isBeatmap(fileName=None, content=None):
    if fileName:
        with open(fileName, "rb") as f:
            firstLine = f.readline().decode("utf-8-sig").strip()
    elif content:
        try:
            firstLine = content.decode("utf-8-sig").split("\n")[0].strip()
        except IndexError:
            return False
    else:
        raise ValueError("Either `fileName` or `content` must be provided.")
    return firstLine.lower().startswith("osu file format v")

def cacheMap(mapFile, _beatmap):
    # Check if we have to download the .osu file
    download = False
    if not path.isfile(mapFile):
        # .osu file doesn't exist. We must download it
        download = True
    else:
        # File exists, check md5
        if generalUtils.fileMd5(mapFile) != _beatmap.fileMD5 or not isBeatmap(mapFile):
            # MD5 don't match, redownload .osu file
            download = True

    # Download .osu file if needed
    if download:
        log.debug(f"maps ~> Downloading {_beatmap.beatmapID} osu file")

        # Get .osu file from osu servers
        fileContent = osuapiHelper.getOsuFileFromID(_beatmap.beatmapID)

        # Make sure osu servers returned something
        if not fileContent: #or not isBeatmap(content=fileContent):
            print(fileContent)
            raise exceptions.osuApiFailException("maps")

        # Delete old .osu file if it exists
        if path.isfile(mapFile):
            remove(mapFile)

        # Save .osu file
        with open(mapFile, "wb+") as f:
            f.write(fileContent)
    else:
        # Map file is already in folder
        log.debug("maps ~> Beatmap found in cache!")

def cachedMapPath(beatmap_id):
    return f".data/beatmaps/{beatmap_id}.osu" if beatmap_id < glob.BEATMAPS_START_INDEX else f"{glob.BEATMAPS_PATH}/osu/{beatmap_id}.osu"
