import random
import time

import requests

import orjson
from common import generalUtils
from common.log import logUtils as log
from objects import glob


def osuApiRequest(request, params, getFirst=True):
    """
    Send a request to osu!api.

    request -- request type, string (es: get_beatmaps)
    params -- GET parameters, without api key or trailing ?/& (es: h=a5b99395a42bd55bc5eb1d2411cbdf8b&limit=10)
    return -- dictionary with json response if success, None if failed or empty response.
    """
    # Make sure osuapi is enabled
    if not generalUtils.stringToBool(glob.conf.config["osuapi"]["enable"]):
        log.warning("osu!api is disabled")
        return

    # Api request
    resp = None
    try:
        api_base = glob.conf.config["osuapi"]["apiurl"]
        api_key = random.choice(glob.conf.config["osuapi"]["apikeys"].split(","))

        final_url = f"{api_base}/api/{request}?k={api_key}&{params}"
        log.debug(final_url)

        t = time.time()
        resp = requests.get(final_url, timeout=5).text
        data = orjson.loads(resp)

        if data and isinstance(data, str):
            data = None

        print(f"osu!api request to {final_url} took {(time.time() - t) * 1000}")

        if getFirst:
            if len(data) >= 1:
                resp = data[0]
            else:
                resp = None
        else:
            resp = data
    finally:
        glob.dog.increment(f"{glob.DATADOG_PREFIX}.osu_api.requests")
        log.debug(resp)
        return resp


def osuApiMapRequest(params, getFirst=True):
    # Api request
    resp = None
    try:
        api_key = random.choice(glob.conf.config["osuapi"]["apikeys"].split(","))
        final_url = f"https://old.ppy.sh/api/get_beatmaps{params}&k={api_key}"
        log.debug(final_url)

        t = time.time()
        resp = requests.get(final_url, timeout=5).text
        data = orjson.loads(resp)

        print(f"osu!api request to {final_url} took {(time.time() - t) * 1000}")

        if getFirst:
            if len(data) >= 1:
                resp = data[0]
            else:
                resp = None
        else:
            resp = data
    finally:
        glob.dog.increment(f"{glob.DATADOG_PREFIX}.osu_api.requests")
        log.debug(resp)
        return resp


def getOsuFileFromID(beatmapID):
    """
    Send a request to osu! servers to download a .osu file from beatmap ID
    Used to get .osu files for oppai

    beatmapID -- ID of beatmap (not beatmapset) to download
    return -- .osu file content if success, None if failed
    """
    # Make sure osuapi is enabled
    if not generalUtils.stringToBool(glob.conf.config["osuapi"]["enable"]):
        log.warning("osuapi is disabled")
        return
    response = None
    try:
        url = f'{glob.conf.config["osuapi"]["apiurl"]}/osu/{beatmapID}'
        response = requests.get(url, timeout=10).content
    finally:
        glob.dog.increment(glob.DATADOG_PREFIX + ".osu_api.osu_file_requests")
        return response
