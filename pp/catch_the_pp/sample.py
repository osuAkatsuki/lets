from os import path
from sys import argv

from .osu.ctb.difficulty import Difficulty
from .osu_parser.beatmap import Beatmap
from .ppCalc import calculate_pp

if len(argv) <= 1:
    beatmap = Beatmap(path.dirname(path.realpath(__file__)) + "/test.osu")  # Yes... this be my test file (Will remove when project is done)
else:
    beatmap = Beatmap(argv[1])

if len(argv) >= 3:
    mods = int(argv[2])
else:
    mods = 0

difficulty = Difficulty(beatmap, mods)
print("Calculation:")
print("Stars: {}, PP: {}, MaxCombo: {}\n".format(
    difficulty.star_rating, calculate_pp(difficulty, 1, beatmap.max_combo, 0), beatmap.max_combo
))

"""
m = {"NOMOD": 0, "EASY": 2, "HIDDEN": 8, "HARDROCK": 16, "DOUBLETIME": 64, "HALFTIME": 256, "FLASHLIGHT": 1024}
for key in m.keys():
    difficulty = Difficulty(beatmap, m[key])
    print(f"Mods: {key}")
    print(f"Stars: {difficulty.star_rating}")
    print(f"PP: {calculate_pp(difficulty, 1, beatmap.max_combo, 0)}\n")
"""
