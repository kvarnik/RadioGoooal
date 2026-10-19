import json
from pathlib import Path

from facts import (
    AWAY,
    AWAY_ID,
    EVENTS_PATH,
    HOME,
    HOME_ID,
    build_facts,
    fare_count,
    pass_complete,
    pass_difficulty,
    player_row,
    row_at,
    shot_speed_mps,
)

EVENTS = json.loads(EVENTS_PATH.read_text())
FACTS = build_facts(EVENTS)


def test_score_and_xg_at_the_window_marks():
    opening = row_at(FACTS, 87, 0)
    assert opening["score"][str(HOME_ID)] == 4
    assert opening["score"][str(AWAY_ID)] == 1
    assert opening["shots"][str(HOME_ID)] == 23
    assert opening["shots"][str(AWAY_ID)] == 12
    assert round(opening["xg"][str(HOME_ID)], 3) == 1.149
    assert round(opening["xg"][str(AWAY_ID)], 3) == 1.214

    full_time = row_at(FACTS, 91, 30)
    assert full_time["score"][str(HOME_ID)] == 5
    assert full_time["score"][str(AWAY_ID)] == 3
    assert full_time["shots"][str(HOME_ID)] == 25
    assert full_time["shots"][str(AWAY_ID)] == 18
    assert round(full_time["xg"][str(AWAY_ID)], 3) == 2.337
    assert round(row_at(FACTS, 92, 0)["xg"][str(HOME_ID)], 3) == 1.604


def test_hampstead_is_close_range_and_the_other_goals_have_a_speed():
    shots = [event for event in EVENTS if event["type"]["name"] == "Shot" and event["minute"] >= 87]
    by_name = {event["player"]["name"]: event for event in shots if event["shot"]["outcome"]["name"] == "Goal"}
    assert shot_speed_mps(by_name["Robert Hampstead"]) is None
    assert shot_speed_mps(by_name["David Rochdale"]) > 0
    assert shot_speed_mps(by_name["James Dickenson"]) > 0


def test_pass_difficulty_weights_and_a_missing_outcome_is_complete():
    hardest = {
        "location": [0, 40],
        "under_pressure": True,
        "pass": {
            "length": 40,
            "end_location": [30, 40],
            "height": {"name": "High Pass"},
            "cross": True,
        },
    }
    assert pass_difficulty(hardest) == 100
    easiest = {"location": [0, 0], "pass": {"length": 0, "end_location": [0, 0], "height": {"name": "Ground Pass"}}}
    assert pass_difficulty(easiest) == 0
    assert pass_complete({"pass": {}})
    assert not pass_complete({"pass": {"outcome": {"name": "Incomplete"}}})
    real = next(event for event in EVENTS if event["type"]["name"] == "Pass" and "outcome" not in event["pass"])
    assert pass_complete(real)
    assert 0 <= pass_difficulty(real) <= 100


def test_a_spell_counts_only_after_it_finishes():
    stints = [(0, 6000)]
    assert fare_count(stints, [], 599) == 0
    assert fare_count(stints, [], 600) == 1
    assert fare_count(stints, [100], 600) == 0
    assert fare_count(stints, [100], 1200) == 1
    for player in row_at(FACTS, 92, 0)["players"]:
        earlier = player_row(row_at(FACTS, 90, 0), player["name"])
        assert player["passenger_fare"] == earlier["passenger_fare"]
        assert player["cards"] == 0


def test_clubs_keep_the_file_names():
    assert HOME == "Arsesnail"
    assert AWAY == "Mancheater City"
    text = Path(EVENTS_PATH).read_text()
    assert "Arsenal" not in text
    assert "Manchester" not in text
