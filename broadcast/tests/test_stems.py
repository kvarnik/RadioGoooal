import csv
import json
from pathlib import Path

from cues import match_cues
from facts import EVENTS_PATH

AUDIO = Path(__file__).resolve().parents[1] / "data" / "audio"
EVENTS = json.loads(EVENTS_PATH.read_text())
ROLES = ["home", "away", "chant", "kick", "whistle", "goal"]


def inventory():
    with (AUDIO / "sources.csv").open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def test_window_cues_are_kicks_goals_and_the_final_whistle():
    cues = {cue["t"]: cue["effects"] for cue in match_cues(EVENTS)}
    assert cues == {
        5: ["kick", "goal"],
        9: ["kick"],
        34: ["kick"],
        65: ["kick"],
        165: ["kick"],
        195: ["kick"],
        240: ["kick"],
        267: ["kick"],
        268: ["kick", "goal"],
        270: ["kick", "goal"],
        300: ["whistle"],
    }
    assert json.loads((AUDIO / "cues.json").read_text())["cues"] == match_cues(EVENTS)


def test_sound_inventory_lists_every_stored_clip():
    rows = inventory()
    assert [row["role"] for row in rows] == ROLES
    attribution = (AUDIO / "ATTRIBUTION.md").read_text(encoding="utf-8")
    deck = (AUDIO.parents[1] / "app" / "audio.js").read_text(encoding="utf-8")
    assert "freesound.org" not in deck
    for row in rows:
        path = AUDIO / row["filename"]
        assert path.is_file()
        assert path.stat().st_size == int(row["stored_bytes"])
        assert row["license"] == "CC0 1.0"
        assert "publicdomain/zero/1.0" in row["license_url"]
        assert row["source_url"].startswith("https://freesound.org/")
        assert row["download_url"].startswith("https://cdn.freesound.org/previews/")
        assert row["download_url"].endswith("-hq.mp3")
        assert row["author"]
        assert row["freesound_id"]
        assert row["playback"] in {"loop", "oneshot"}
        assert row["filename"] in attribution
        assert row["source_url"] in attribution
