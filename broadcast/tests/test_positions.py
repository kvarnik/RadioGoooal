import json

from facts import EVENTS_PATH, HOME_ID
from positions import POSITIONS_PATH, SEED, STEP_CAP, build_positions

EVENTS = json.loads(EVENTS_PATH.read_text())
DATA, LATE = build_positions(EVENTS, seed=SEED)
FRAMES = DATA["frames"]


def test_track_shape_and_the_speed_cap():
    assert DATA["seed"] == 9000001
    assert len(FRAMES) == 301
    assert FRAMES[0]["t"] == 87 * 60
    assert FRAMES[-1]["t"] == 92 * 60
    for frame in FRAMES:
        home = [player for player in frame["players"] if player["team_id"] == HOME_ID]
        assert len(home) == 11
        assert len(frame["players"]) == 22
    previous = {player["id"]: (player["x"], player["y"]) for player in FRAMES[0]["players"]}
    for frame in FRAMES[1:]:
        for player in frame["players"]:
            before = previous[player["id"]]
            step = ((player["x"] - before[0]) ** 2 + (player["y"] - before[1]) ** 2) ** 0.5
            assert step <= 10 / 0.9144 + 1e-6
            previous[player["id"]] = (player["x"], player["y"])
    assert STEP_CAP < 10 / 0.9144


def test_goals_land_on_the_fixed_pitch():
    def ball(minute, second):
        return FRAMES[(minute * 60 + second) - FRAMES[0]["t"]]["ball"]

    hampstead = ball(87, 5)
    dickenson = ball(91, 30)
    assert hampstead[0] > 115
    assert dickenson[0] < 5


def test_committed_file_matches_the_generator():
    assert json.loads(POSITIONS_PATH.read_text()) == DATA
