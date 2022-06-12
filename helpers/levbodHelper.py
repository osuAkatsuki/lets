from requests import RequestException, get

import orjson
from constants import exceptions
from objects import glob


def levbodRequest(handler, params=None):
    if params is None:
        params = {}

    result = get(f"{glob.conf.config['levbod']['url']}/{handler}", params=params)

    try:
        data = orjson.loads(result.text)
    except (orjson.JSONDecodeError, ValueError, RequestException, KeyError, exceptions.noAPIDataError):
        return

    if result.status_code != 200 or 'data' not in data:
        return

    return data['data']

def getListing(rankedStatus=4, page=0, gameMode=-1, query=''):
    return levbodRequest('listing', {
        'mode': gameMode,
        'status': rankedStatus,
        'query': query,
        'page': page,
    })

def getBeatmapSet(id):
    return levbodRequest('beatmapset', {
        'id': id
    })

def getBeatmap(id):
    return levbodRequest('beatmap', {
        'id': id
    })

def levbodToDirect(data):
    s = [('{beatmapset_id}.osz|{artist}|{title}|{creator}|{ranked_status}|'
         '10.00|0|{beatmapset_id}|').format(**data)]
    if len(data['beatmaps']) > 0:
        s.append(f"{data['beatmaps'][0]['beatmap_id']}|0|0|0||")
        for i in data['beatmaps']:
            s.append('{difficulty_name}@{game_mode},'.format(**i))

    return f"{''.join(s).strip(',')}|"

def levbodToDirectNp(data):
    return ('{beatmapset_id}.osz|{artist}|{title}|{creator}|{ranked_status}|'
            '10.00|0|{beatmapset_id}|{beatmapset_id}|0|0|0|').format(**data)
