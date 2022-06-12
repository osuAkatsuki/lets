from typing import Any, Dict, Optional, Tuple, Union

from objects.score import score
from secret.achievements.utils import achievements_response


class Chart:
    """
    Chart base class
    """

    def __init__(self, id_: int, url: str, name: str) -> None:
        """
        Initializes a new chart.

        :param id_: chart id. Currently known values are 'beatmap' and 'overall'
        :param url: URL to open when clicking on the chart title.
        :param name: chart name displayed in the game client
        """

        self.id_ = id_
        self.url = url
        self.name = name

    def items(self):
        """
        `items()` method that allows this class to be used as a iterable dict

        :return:
        """

        return self.output_attrs.items()

    @property
    def output_attrs(self) -> Dict[str, Union[str, int]]:
        """
        An unzingonified dict containing the stuff that will be sent to the game client

        :return: dict
        """

        return {
            "chartId": self.id_,
            "chartUrl": self.url,
            "chartName": self.name
        }

    @staticmethod
    def before_after_dict(name, values: Tuple[Optional[Union[int, float]]], none_value: str = '0') -> Dict[str, Optional[Union[str, int, float]]]:
        """
        Turns a tuple with two elements in a dict with two elements.

        :param name: prefix of the keys
        :param values: (value_before, value_after). value_before and value_after can be None.
        :param none_value: value to use instead of None (None, when zingonified, is not recognized by the game client)
        :return: { XXXBefore -> first element, XXXAfter -> second element }, where XXX is `name`
        """

        return {
            f'{name}{"Before" if i == 0 else "After"}': x if x else none_value for i, x in enumerate(values)
        }


class BeatmapChart(Chart):
    """
    Beatmap ranking chart
    """
    def __init__(self, old_score: Optional[score], new_score: score, beatmap_id: int) -> None:
        """
        Initializes a new BeatmapChart object.

        :param old_score: score object of the old score
        :param new_score: score object of the currently submitted score
        :param beatmap_id: beatmap id, for the clickable link
        """

        super(BeatmapChart, self).__init__("beatmap", f"https://akatsuki.pw/b/{beatmap_id}", "Beatmap Ranking")
        self.rank: tuple[Optional[int]] = (old_score.rank if old_score else None, new_score.rank)
        self.max_combo: tuple[Optional[int]] = (old_score.maxCombo if old_score else None, new_score.maxCombo)
        self.accuracy: tuple[Optional[float]] = (old_score.accuracy * 100 if old_score else None, new_score.accuracy * 100)
        self.ranked_score: tuple[Optional[int]] = (old_score.score if old_score else None, new_score.score)
        self.pp: tuple[Optional[float]] = (old_score.pp if old_score else None, new_score.pp)
        self.score_id: tuple[Optional[int]] = new_score.scoreID

    @property
    def output_attrs(self):
        return {
            **super(BeatmapChart, self).output_attrs,
            **self.before_after_dict("rank", self.rank, none_value=""),
            **self.before_after_dict("maxCombo", self.max_combo),
            **self.before_after_dict("accuracy", self.accuracy),
            **self.before_after_dict("rankedScore", self.ranked_score),
            **self.before_after_dict("totalScore", self.ranked_score),
            **self.before_after_dict("pp", self.pp),
            "onlineScoreId": self.score_id
        }


class OverallChart(Chart):
    """
    Overall ranking chart  achievements
    """

    def __init__(self, user_id: int, old_user_stats: Any, new_user_stats: Any, maxCombo: int, score: int, new_achievements, old_rank: int, new_rank: int) -> None:
        """
        Initializes a new OverallChart object.
        This constructor sucks because LETS itself sucks.

        :param user_id: id of the user
        :param old_user_stats: user stats dict before submitting the score
        :param new_user_stats: user stats dict after submitting the score
        :param maxCombo: users max combo before submitting the score
        :param score: score object of the scores that has just been submitted
        :param new_achievements: achievements unlocked list
        :param old_rank: global rank before submitting the score
        :param new_rank: global rank after submitting the score
        """

        super(OverallChart, self).__init__("overall", f"https://akatsuki.pw/u/{user_id}", "Overall Ranking")
        self.rank: tuple[int] = (old_rank, new_rank)
        self.ranked_score: tuple[int] = (old_user_stats["rankedScore"], new_user_stats["rankedScore"])
        self.total_score: tuple[int] = (old_user_stats["totalScore"], new_user_stats["totalScore"])
        self.max_combo: tuple[int] = (maxCombo, maxCombo)
        self.accuracy: tuple[float] = (old_user_stats["accuracy"], new_user_stats["accuracy"])
        self.pp: tuple[float] = (old_user_stats["pp"], new_user_stats["pp"])
        self.new_achievements = new_achievements
        self.score_id: int = score.scoreID

    @property
    def output_attrs(self):
        return {
            **super(OverallChart, self).output_attrs,
            **self.before_after_dict("rank", self.rank),
            **self.before_after_dict("rankedScore", self.ranked_score),
            **self.before_after_dict("totalScore", self.total_score),
            **self.before_after_dict("maxCombo", self.max_combo),
            **self.before_after_dict("accuracy", self.accuracy),
            **self.before_after_dict("pp", self.pp),
            "achievements-new": achievements_response(self.new_achievements),
            "onlineScoreId": self.score_id
        }
