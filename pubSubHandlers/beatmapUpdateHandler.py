from common.redis import generalPubSubHandler
from helpers import osuapiHelper
from objects import beatmap, glob


def updateSet(beatmapSetID):
    apiResponse = osuapiHelper.osuApiRequest("get_beatmaps", f"s={beatmapSetID}", False)
    if len(apiResponse) == 0:
        return
    for i in apiResponse:
        beatmap.beatmap(i["file_md5"], int(i["beatmapset_id"]), refresh=True)

        for mode in (0, 1, 2, 3):
            lb_cache_vn = glob.lb_cache.get_lb_cache(mode, False)
            lb_cache_rx = glob.lb_cache.get_lb_cache(mode, True)
            glob.lb_cache.clear_lb_cache(lb_cache_vn, i["file_md5"])
            glob.lb_cache.clear_lb_cache(lb_cache_rx, i["file_md5"])

            glob.pb_cache.nuke_bmap_pbs(mode, i["file_md5"], False)
            glob.pb_cache.nuke_bmap_pbs(mode, i["file_md5"], True)


class handler(generalPubSubHandler.generalPubSubHandler):
    def __init__(self):
        super().__init__()
        self.structure = {}
        self.strict = False

    def handle(self, data):
        data = super().parseData(data)
        if data is None:
            return
        if "id" in data:
            beatmapData = osuapiHelper.osuApiRequest("get_beatmaps", f"b={data['id']}")
            if beatmapData and "beatmapset_id" in beatmapData:
                updateSet(beatmapData["beatmapset_id"])
        elif "set_id" in data:
            updateSet(data["set_id"])
