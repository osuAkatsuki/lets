import hashlib
from typing import Any, Dict, Optional

import requests

from common import generalUtils
from common.log import logUtils as log
from constants import dataTypes
from helpers import binaryHelper
from objects import glob

DOTNET_OFFSET = 0x89F7FF5F7B58000


def buildFullReplay(
    scoreID: Optional[int] = None,
    scoreData: Optional[Dict[str, Any]] = None,
    rawReplay: Optional[bytes] = None,
    relax: bool = False,
) -> Optional[bytes]:
    if not any([v for v in (scoreID, scoreData)]) or all((scoreID, scoreData)):
        raise AttributeError(
            "Either scoreID or scoreData must be provided, not neither or both"
        )

    if not scoreData:
        table = "scores_relax" if relax else "scores"
        scoreData = glob.db.fetch(
            "SELECT {0}.*, users.username FROM {0} "
            "LEFT JOIN users ON {0}.userid = users.id "
            "WHERE {0}.id = %s".format(table),
            [scoreID],
        )
    else:
        scoreID = scoreData["id"]

    if not scoreData or not scoreID:
        log.warning(f"Requested replay for non-existant score {scoreID}.")
        return

    req = requests.get(f"http://localhost:3030/get?id={scoreID}")
    if not req or req.status_code != 200:
        rawReplay = b""
    else:
        rawReplay = req.content

    # Calculate missing replay data
    rank = generalUtils.getRank(
        int(scoreData["play_mode"]),
        int(scoreData["mods"]),
        int(scoreData["accuracy"]),
        int(scoreData["300_count"]),
        int(scoreData["100_count"]),
        int(scoreData["50_count"]),
        int(scoreData["misses_count"]),
    )

    magicHash = hashlib.md5(
        "{}p{}o{}o{}t{}a{}r{}e{}y{}o{}u{}{}{}".format(
            scoreData["100_count"] + scoreData["300_count"],
            scoreData["50_count"],
            scoreData["gekis_count"],
            scoreData["katus_count"],
            scoreData["misses_count"],
            scoreData["beatmap_md5"],
            scoreData["max_combo"],
            "True" if scoreData["full_combo"] == "1" else "False",
            scoreData["username"],
            scoreData["score"],
            rank,
            scoreData["mods"],
            "True",
        ).encode()
    ).hexdigest()

    # Add headers (convert to full replay)
    fullReplay = binaryHelper.binaryWrite(
        [
            (scoreData["play_mode"], dataTypes.byte),
            (2015_04_14, dataTypes.uInt32),
            (scoreData["beatmap_md5"], dataTypes.string),
            (scoreData["username"], dataTypes.string),
            (magicHash, dataTypes.string),
            (scoreData["300_count"], dataTypes.uInt16),
            (scoreData["100_count"], dataTypes.uInt16),
            (scoreData["50_count"], dataTypes.uInt16),
            (scoreData["gekis_count"], dataTypes.uInt16),
            (scoreData["katus_count"], dataTypes.uInt16),
            (scoreData["misses_count"], dataTypes.uInt16),
            (scoreData["score"], dataTypes.uInt32),
            (scoreData["max_combo"], dataTypes.uInt16),
            (scoreData["full_combo"], dataTypes.byte),
            (scoreData["mods"], dataTypes.uInt32),
            (0, dataTypes.byte),
            (DOTNET_OFFSET + (int(scoreData["time"]) * 10_000_000), dataTypes.uInt64),
            (rawReplay, dataTypes.rawReplay),
            (scoreID, dataTypes.uInt64),
        ]
    )

    # Return full replay
    return fullReplay
