from typing import Optional, Any

from time import time

from objects import beatmap
from common.constants import gameModes
from common.constants import mods
from common.log import logUtils as log
from common.ripple import userUtils
from constants import rankedStatuses
from common.ripple import scoreUtils
from objects import glob
from pp import rippoppai
from pp import wifipiano2
from pp import cicciobello

import requests

PP_CALCULATORS = (
    rippoppai.oppai,         # std
    rippoppai.oppai,         # taiko
    cicciobello.Cicciobello, # ctb
    wifipiano2.piano     # mania
)
class score:
    __slots__ = ["scoreID", "playerName", "score", "maxCombo", "c50", "c100", "c300", "cMiss", "cKatu", "cGeki",
                 "fullCombo", "mods", "playerUserID", "rank", "date", "hasReplay", "fileMd5", "passed", "playDateTime",
                 "gameMode", "completed", "accuracy", "pp", "oldPersonalBest", "rankedScoreIncrease", "scores_table", "checksum"]
    def __init__(self, scoreID: Optional[int] = None, rank: Optional[Any] = None, setData: bool = True, relax = False):
        """
        Initialize a (empty) score object.

        scoreID -- score ID, used to get score data from db. Optional.
        rank -- score rank. Optional
        setData -- if True, set score data from db using scoreID. Optional.
        """

        self.scoreID = 0
        self.playerName = "nospe"
        self.score = 0
        self.maxCombo = 0
        self.c50 = 0
        self.c100 = 0
        self.c300 = 0
        self.cMiss = 0
        self.cKatu = 0
        self.cGeki = 0
        self.fullCombo = False
        self.mods = 0
        self.playerUserID = 0
        self.rank = rank
        self.date = 0
        self.hasReplay = 0

        self.fileMd5 = None
        self.passed = False
        self.playDateTime = 0
        self.gameMode = 0
        self.completed = 0
        self.accuracy = 0.00
        self.pp = 0.00

        self.oldPersonalBest = 0
        self.rankedScoreIncrease = 0

        self.scores_table = 'scores_relax' if relax else 'scores'

        if scoreID and setData:
            self.setDataFromDB(scoreID, rank)

        self.checksum: str = ""

    def calculateAccuracy(self) -> None:
        """
        Calculate and set accuracy for that score.
        """

        if self.gameMode == gameModes.STD:
            totalPoints = self.c50 * 50 + self.c100 * 100 + self.c300 * 300
            totalHits = self.c300 + self.c100 + self.c50 + self.cMiss
            self.accuracy = totalPoints / (totalHits * 300) if totalHits else 1

        elif self.gameMode == gameModes.TAIKO:
            totalPoints = (self.c100 * 50) + (self.c300 * 100)
            totalHits = self.cMiss + self.c100 + self.c300
            self.accuracy = totalPoints / (totalHits * 100) if totalHits else 1

        elif self.gameMode == gameModes.CTB:
            fruits = self.c300 + self.c100 + self.c50
            totalFruits = fruits + self.cMiss + self.cKatu
            self.accuracy = fruits / totalFruits if totalFruits else 1

        elif self.gameMode == gameModes.MANIA:
            totalPoints = self.c50 * 50 + self.c100 * 100 + self.cKatu * 200 + self.c300 * 300 + self.cGeki * 300
            totalHits = self.cMiss + self.c50 + self.c100 + self.c300 + self.cGeki + self.cKatu
            self.accuracy = totalPoints / (totalHits * 300)

        else: # unknown gamemode
            self.accuracy = 0

    def setRank(self, rank: Optional[Any]) -> None:
        """
        Force a score rank.

        rank -- new score rank
        """

        self.rank = rank

    def setDataFromDB(self, scoreID: int, rank: Optional[Any] = None) -> None:
        """
        Set this object's score data from db.
        Sets playerUserID too

        scoreID -- score ID
        rank -- rank in scoreboard. Optional.
        """

        data = glob.db.fetch(
            "SELECT {0}.*, users.username FROM {0} "
            "LEFT JOIN users ON users.id = {0}.userid "
            "WHERE {0}.id = %s LIMIT 1".format(self.scores_table), [scoreID])

        if data:
            self.setDataFromDict(data, rank)

    def setDataFromDict(self, data, rank: Optional[Any] = None) -> None:
        """
        Set this object's score data from dictionary.
        Doesn't set playerUserID

        data -- score dictionarty
        rank -- rank in scoreboard. Optional.
        """

        self.scoreID = data["id"]
        self.playerName = userUtils.getUsername(data["userid"]) # note: it passes username but no need to use.
        self.playerUserID = data["userid"]
        self.score = data["score"]
        self.maxCombo = data["max_combo"]
        self.gameMode = data["play_mode"]
        self.c50 = data["50_count"]
        self.c100 = data["100_count"]
        self.c300 = data["300_count"]
        self.cMiss = data["misses_count"]
        self.cKatu = data["katus_count"]
        self.cGeki = data["gekis_count"]
        self.fullCombo = data["full_combo"] == 1
        self.mods = data["mods"]

        if self.mods & mods.RELAX:
            self.scores_table = 'scores_relax'

        self.rank: Optional[Any] = rank if rank else ""
        self.date = data["time"]
        self.fileMd5: str = data["beatmap_md5"]
        self.completed = data["completed"]
        #if "pp" in data:
        self.pp: float = data["pp"]
        self.calculateAccuracy()

    def setDataFromScoreData(self, scoreData) -> None:
        """
        Set this object's score data from scoreData list (submit modular).

        scoreData -- scoreData list
        """

        # Note: len(scoreData) >= 16 must be ensured before calling

        self.fileMd5 = scoreData[0]
        self.playerName = scoreData[1].strip()
        self.checksum = scoreData[2]
        self.c300 = int(scoreData[3])
        self.c100 = int(scoreData[4])
        self.c50 = int(scoreData[5])
        self.cGeki = int(scoreData[6])
        self.cKatu = int(scoreData[7])
        self.cMiss = int(scoreData[8])
        self.score = int(scoreData[9])
        self.maxCombo = int(scoreData[10])
        self.fullCombo = scoreData[11] == 'True'
        #self.rank: Optional[Any] = scoreData[12]
        self.mods = int(scoreData[13])

        if self.mods & mods.RELAX:
            self.scores_table = 'scores_relax'

        self.passed = scoreData[14] == 'True'
        self.gameMode = int(scoreData[15])
        #self.playDateTime = int(scoreData[16])
        self.playDateTime = int(time())
        self.calculateAccuracy()
        #osuVersion: str = scoreData[17]

        self.calculatePP()
        # Set completed status
        self.setCompletedStatus()

    def getScoreData(self) -> None:
        api_request = requests.get(f"http://localhost:4242/score_sub?id={self.scoreID}&pass={int(self.passed)}&table={self.scores_table}&checksum={self.checksum}")
        resp = api_request.json()
        print("sub handler req")

        self.completed = int(resp[0])

        # b = beatmap.beatmap(self.fileMd5, 0)
        self.pp = float(resp[1])

        glob.db.execute(
            f'UPDATE {self.scores_table} SET completed = %s, pp = %s, score = %s WHERE id = %s',
            (self.completed, self.pp, self.score, self.scoreID,)
        )

    def getData(self, pp: bool = False) -> str:
        # Return score row relative to this score for getscores
        return "{}|{}|{}|{}|{}|{}|{}|{}|{}|{}|{}|{}|{}|{}|{}|1\n".format(
            self.scoreID,
            userUtils.getClan(self.playerUserID), # username
            int(self.pp) if pp else self.score,
            self.maxCombo,
            self.c50,
            self.c100,
            self.c300,
            self.cMiss,
            self.cKatu,
            self.cGeki,
            self.fullCombo,
            self.mods,
            self.playerUserID,
            self.rank,
            self.date
        )

    def setCompletedStatus(self, b = None) -> None:
        """
        Set this score completed status and rankedScoreIncrease.
        """

        self.completed = 0

        # Create beatmap object
        if b is None:
            b = beatmap.beatmap(self.fileMd5, 0)

        if not scoreUtils.isRankable(self.mods, b.maxCombo) or not self.passed:
            return

        userID = userUtils.getID(self.playerName)

        # Make sure we don't have another score identical to this one
        duplicate = glob.db.fetch(
            f'SELECT 1 FROM {self.scores_table} '
            'WHERE checksum = %s',
            [self.checksum])

        if duplicate is not None:
            # Found same score in db. Don't save this score.
            self.completed = -1
            return

        # No duplicates found.
        # Get right "completed" value
        personalBest = glob.db.fetch(
            f"SELECT id, pp, score FROM {self.scores_table} "
            "WHERE userid = %s AND beatmap_md5 = %s AND play_mode = %s "
            f"AND completed = 3 LIMIT 1",
            [userID, self.fileMd5, self.gameMode])

        if personalBest is None:
            # This is our first score on this map, so it's our best score
            self.completed = 3
            self.rankedScoreIncrease = self.score
            self.oldPersonalBest = 0
        else:
            # Compare personal best's score with current score
            if b.rankedStatus in {rankedStatuses.RANKED, rankedStatuses.APPROVED, rankedStatuses.QUALIFIED}:
                if self.pp > personalBest["pp"] or (self.pp == personalBest["pp"] and self.score >= personalBest["score"]):
                    # New best score
                    self.completed = 3
                    self.rankedScoreIncrease = self.score - personalBest["score"]
                    self.oldPersonalBest = personalBest["id"]
                else:
                    self.completed = 2
                    self.rankedScoreIncrease = 0
                    self.oldPersonalBest = 0

            elif b.rankedStatus == rankedStatuses.LOVED:
                if self.score > personalBest["score"]:
                    # New best score
                    self.completed = 3
                    self.rankedScoreIncrease = self.score - personalBest["score"]
                    self.oldPersonalBest = personalBest["id"]
                else:
                    self.completed = 2
                    self.rankedScoreIncrease = 0
                    self.oldPersonalBest = 0

    def saveScoreInDB(self) -> None:
        """
        Save this score in DB (if passed and mods are valid).
        """

        # Add this score
        if self.completed != -1:
            self.scoreID = int(glob.db.execute(
                f"INSERT INTO {self.scores_table} "
                "(id, beatmap_md5, userid, score, max_combo, full_combo, mods, "
                "300_count, 100_count, 50_count, katus_count, gekis_count, "
                "misses_count, time, play_mode, completed, accuracy, pp, checksum) "
                "VALUES (NULL, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)", [
                    self.fileMd5, userUtils.getID(self.playerName), self.score, self.maxCombo,
                    int(self.fullCombo), self.mods, self.c300, self.c100, self.c50, self.cKatu,
                    self.cGeki, self.cMiss, self.playDateTime, self.gameMode, self.completed,
                    self.accuracy * 100, self.pp, self.checksum]))

    def calculatePP(self, b = None) -> None:
        # Create beatmap object
        if b is None:
            b = beatmap.beatmap(self.fileMd5, 0)

        pp_statuses = {
            rankedStatuses.RANKED,
            rankedStatuses.APPROVED,
            rankedStatuses.QUALIFIED
        }

        if self.mods & mods.RELAX:
            pp_statuses.add(rankedStatuses.LOVED)

        if (
            self.passed and
            b.rankedStatus in pp_statuses and
            scoreUtils.isRankable(self.mods, b.maxCombo)
        ):
            calculator = PP_CALCULATORS[self.gameMode](b, self)
            self.pp = calculator.pp
        else:
            self.pp = 0
