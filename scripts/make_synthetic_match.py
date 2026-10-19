#!/usr/bin/env python3
"""Build one synthetic match by stitching three Premier League event files.

Each segment keeps the events whose match clock falls in that window.
Players are renamed onto one made-up squad per club so the names stay
stable when the source file changes. Shot outcomes are then rewritten
so Arsesnail has 5 goals and Mancheater City has 3. Pitch locations are
shifted by 0.01–3 meters, and each timestamp is moved by 0–0.1 seconds.
"""

from __future__ import annotations

import json
import math
import random
import uuid
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = ROOT / "open-data" / "data" / "events" / "premier"
OUTPUT = ROOT / "broadcast" / "data" / "9000001.json"

# Swap a file, or move the minute boundaries, to change which passage is used.
SEGMENTS = [
    {"file": "3754216.json", "start_min": 0, "end_min": 30},
    {"file": "3754229.json", "start_min": 30, "end_min": 60},
    {"file": "3754340.json", "start_min": 60, "end_min": None},
]

SCORE = {"Arsesnail": 5, "Mancheater City": 3}
TEAMS = {
    "Arsesnail": {"id": 1, "name": "Arsesnail"},
    "Mancheater City": {"id": 36, "name": "Mancheater City"},
}
GOAL = {"id": 97, "name": "Goal"}
SAVED = {"id": 100, "name": "Saved"}

MANCHESTER_SURNAMES = [
    "Oxford", "Deansgate", "Portland", "Piccadilly", "Princess",
    "Whitworth", "Wilmslow", "Withington", "Burton", "Barlow",
    "Dickenson", "Cheetham", "Rochdale", "Chester", "Stretford",
    "Moss", "Albert", "Mosley", "Peter", "Ancoats",
]
NORTH_LONDON_SURNAMES = [
    "Holloway", "Finchley", "Archway", "Stroud", "Crouch",
    "Muswell", "Hornsey", "Kentish", "Haverstock", "Camden",
    "Essex", "Pentonville", "Tollington", "Blackstock", "Highbury",
    "Barnsbury", "Hampstead", "Wightman", "Burghley", "Whetstone",
]
FIRST_NAMES = [
    "David", "John", "Michael", "Paul", "Peter",
    "Andrew", "Mark", "James", "Robert", "Stephen",
    "Richard", "Christopher", "Ian", "Thomas", "Daniel",
    "Alan", "Anthony", "Simon", "Steven", "Matthew",
    "Kevin", "Brian", "Gary", "Philip", "Martin",
    "William", "George", "Jonathan", "Neil", "Nigel",
]
SURNAMES = {
    "Arsesnail": NORTH_LONDON_SURNAMES,
    "Mancheater City": MANCHESTER_SURNAMES,
}
PLAYER_KEYS = {"player", "recipient", "replacement"}
TEAM_KEYS = {"team", "possession_team"}
WEAK_POSITIONS = {"", "Unknown", "Substitute"}
LOCATION_KEYS = {"location", "end_location"}
# StatsBomb x/y are yards on a 120 by 80 pitch.
METERS_PER_YARD = 0.9144


def clock_seconds(event: dict) -> float:
    hours, minutes, seconds = event["timestamp"].split(":")
    elapsed = int(hours) * 3600 + int(minutes) * 60 + float(seconds)
    if event["period"] > 1:
        elapsed += (event["period"] - 1) * 45 * 60
    return elapsed


def in_window(event: dict, start_min: int, end_min: int | None) -> bool:
    elapsed = clock_seconds(event)
    if elapsed < start_min * 60:
        return False
    if end_min is not None and elapsed >= end_min * 60:
        return False
    return True


class Squad:
    def __init__(self, team_name: str, rng: random.Random) -> None:
        self.team_name = team_name
        self.team = TEAMS[team_name]
        self.surnames = list(SURNAMES[team_name])
        self.rng = rng
        self.by_source: dict[int, dict] = {}
        self.by_position: dict[str, list[dict]] = defaultdict(list)
        self.players: list[dict] = []
        self.next_id = 910001 if team_name == "Arsesnail" else 920001

    def assign(self, source_id: int, position: str, segment_index: int) -> dict:
        if source_id in self.by_source:
            player = self.by_source[source_id]
            if player["position"] in WEAK_POSITIONS and position not in WEAK_POSITIONS:
                player["position"] = position
            return player

        position = position or "Unknown"
        reusable = [
            player
            for player in self.by_position.get(position, [])
            if player["last_segment"] != segment_index
        ]
        if reusable:
            player = reusable[0]
        else:
            player = self._create(position)
            self.by_position[position].append(player)
        player["last_segment"] = segment_index
        self.by_source[source_id] = player
        return player

    def _create(self, position: str) -> dict:
        if not self.surnames:
            raise RuntimeError(f"{self.team_name} ran out of unique surnames")
        surname = self.surnames.pop(0)
        first_choices = [name for name in FIRST_NAMES if name != surname]
        player = {
            "id": self.next_id,
            "name": f"{self.rng.choice(first_choices)} {surname}",
            "position": position,
            "last_segment": None,
        }
        self.next_id += 1
        self.players.append(player)
        return player


def load_segment(spec: dict) -> list[dict]:
    path = SOURCE_DIR / spec["file"]
    events = json.loads(path.read_text())
    kept = [
        event
        for event in events
        if in_window(event, spec["start_min"], spec["end_min"])
        and not event.get("type", {}).get("name", "").startswith("Own Goal")
    ]
    if not kept:
        raise RuntimeError(f"No events in {spec['file']} for {spec}")
    return kept


def map_teams(events: list[dict]) -> dict[int, dict]:
    shot_counts = Counter()
    seen: list[int] = []
    for event in events:
        team = event.get("team") or {}
        team_id = team.get("id")
        if team_id is None:
            continue
        if team_id not in seen:
            seen.append(team_id)
        if event.get("type", {}).get("name") == "Shot":
            shot_counts[team_id] += 1
    if len(seen) != 2:
        raise RuntimeError(f"Expected two teams in the window, found {len(seen)}")
    ranked = sorted(seen, key=lambda team_id: (shot_counts[team_id], -team_id), reverse=True)
    return {
        ranked[0]: dict(TEAMS["Arsesnail"]),
        ranked[1]: dict(TEAMS["Mancheater City"]),
    }


def other_team_id(team_ids: list[int], team_id: int) -> int:
    return next(candidate for candidate in team_ids if candidate != team_id)


def harvest(events: list[dict]) -> list[tuple[int, int, str]]:
    """Return source players in first-seen order with their best position."""
    team_ids = []
    for event in events:
        team_id = (event.get("team") or {}).get("id")
        if team_id is not None and team_id not in team_ids:
            team_ids.append(team_id)

    best: dict[int, dict] = {}
    order: list[int] = []

    def add(source_id: int, team_id: int, position: str) -> None:
        position = position or "Unknown"
        current = best.get(source_id)
        if current is None:
            best[source_id] = {"team_id": team_id, "position": position}
            order.append(source_id)
            return
        if current["position"] in WEAK_POSITIONS and position not in WEAK_POSITIONS:
            current["position"] = position

    for event in events:
        team = event.get("team") or {}
        team_id = team.get("id")
        if team_id is None:
            continue
        for item in (event.get("tactics") or {}).get("lineup") or []:
            add(item["player"]["id"], team_id, item.get("position", {}).get("name", "Unknown"))
        if "player" in event:
            add(event["player"]["id"], team_id, (event.get("position") or {}).get("name", "Unknown"))
        replacement = (event.get("substitution") or {}).get("replacement")
        if replacement:
            add(replacement["id"], team_id, "Substitute")
        recipient = (event.get("pass") or {}).get("recipient")
        if recipient:
            add(recipient["id"], team_id, "Unknown")
        for frame in (event.get("shot") or {}).get("freeze_frame") or []:
            frame_team = team_id if frame.get("teammate", True) else other_team_id(team_ids, team_id)
            add(frame["player"]["id"], frame_team, (frame.get("position") or {}).get("name", "Unknown"))

    return [(source_id, best[source_id]["team_id"], best[source_id]["position"]) for source_id in order]


def remap(obj, player_map: dict[int, dict], team_map: dict[int, dict], parent_key: str | None = None):
    if isinstance(obj, list):
        return [remap(item, player_map, team_map, parent_key) for item in obj]
    if isinstance(obj, dict):
        if parent_key in PLAYER_KEYS and "id" in obj and "name" in obj:
            player = player_map[obj["id"]]
            return {"id": player["id"], "name": player["name"]}
        if parent_key in TEAM_KEYS and "id" in obj and "name" in obj:
            team = team_map[obj["id"]]
            return {"id": team["id"], "name": team["name"]}
        return {key: remap(value, player_map, team_map, key) for key, value in obj.items()}
    return obj


def remember_names(events: list[dict], names: set[str]) -> None:
    """Record source team and player names so the rewrite can be checked for leftovers."""
    for event in events:
        for key in TEAM_KEYS:
            team = event.get(key) or {}
            if team.get("name"):
                names.add(team["name"])
        if event.get("player", {}).get("name"):
            names.add(event["player"]["name"])
        recipient = (event.get("pass") or {}).get("recipient") or {}
        if recipient.get("name"):
            names.add(recipient["name"])
        replacement = (event.get("substitution") or {}).get("replacement") or {}
        if replacement.get("name"):
            names.add(replacement["name"])
        for item in (event.get("tactics") or {}).get("lineup") or []:
            if item.get("player", {}).get("name"):
                names.add(item["player"]["name"])
        for frame in (event.get("shot") or {}).get("freeze_frame") or []:
            if frame.get("player", {}).get("name"):
                names.add(frame["player"]["name"])


def goal_location(index: int) -> list[float]:
    y = 36.6 + (index * 1.1) % 6.6
    z = 0.3 + (index * 0.37) % 2.0
    return [120.0, round(y, 1), round(z, 1)]


def shift_timestamp(event: dict, delta: float) -> None:
    hours, minutes, seconds = event["timestamp"].split(":")
    total = int(hours) * 3600 + int(minutes) * 60 + float(seconds) + delta
    total = max(total, 0.0)
    whole = int(total)
    fraction = total - whole
    next_hours, remainder = divmod(whole, 3600)
    next_minutes, next_seconds = divmod(remainder, 60)
    event["timestamp"] = f"{next_hours:02d}:{next_minutes:02d}:{next_seconds + fraction:06.3f}"
    event["second"] = next_seconds
    if next_seconds < int(float(seconds)) and delta > 0:
        event["minute"] = event["minute"] + 1


def jitter_locations(event: dict, rng: random.Random) -> list[float]:
    """Move every x/y point by a random distance from 0.01 to 3 meters."""
    drawn: list[float] = []

    def walk(obj) -> None:
        if isinstance(obj, dict):
            for key, value in obj.items():
                if (
                    key in LOCATION_KEYS
                    and isinstance(value, list)
                    and len(value) >= 2
                    and all(isinstance(item, (int, float)) for item in value[:2])
                ):
                    meters = rng.uniform(0.01, 3.0)
                    yards = meters / METERS_PER_YARD
                    theta = rng.uniform(0, math.tau)
                    value[0] = round(min(120.0, max(0.0, value[0] + yards * math.cos(theta))), 4)
                    value[1] = round(min(80.0, max(0.0, value[1] + yards * math.sin(theta))), 4)
                    drawn.append(meters)
                else:
                    walk(value)
        elif isinstance(obj, list):
            for item in obj:
                walk(item)

    walk(event)
    shot = event.get("shot") or {}
    end = shot.get("end_location")
    if shot.get("outcome", {}).get("name") == "Goal" and isinstance(end, list) and len(end) >= 2:
        end[0] = 120.0
        end[1] = round(min(44.0, max(36.0, end[1])), 4)
    return drawn


def nudge_timestamp(event: dict, rng: random.Random) -> float:
    delta = rng.uniform(0.0, 0.1)
    shift_timestamp(event, delta)
    return delta


def refresh_pass_geometry(event: dict) -> None:
    pass_event = event.get("pass")
    start = event.get("location")
    if not pass_event or not start or "end_location" not in pass_event:
        return
    end = pass_event["end_location"]
    dx = end[0] - start[0]
    dy = end[1] - start[1]
    if "length" in pass_event:
        pass_event["length"] = round(math.hypot(dx, dy), 5)
    if "angle" in pass_event:
        pass_event["angle"] = round(math.atan2(dy, dx), 6)


def perturb(events: list[dict], rng: random.Random) -> dict:
    distances: list[float] = []
    deltas: list[float] = []
    for event in events:
        distances.extend(jitter_locations(event, rng))
        deltas.append(nudge_timestamp(event, rng))
        refresh_pass_geometry(event)
    if not distances or not deltas:
        raise RuntimeError("No locations or timestamps were perturbed")
    if min(distances) < 0.01 or max(distances) > 3:
        raise RuntimeError(f"Location noise out of range: {min(distances)}–{max(distances)} m")
    if min(deltas) < 0 or max(deltas) > 0.1:
        raise RuntimeError(f"Timestamp noise out of range: {min(deltas)}–{max(deltas)} s")
    return {
        "locations": len(distances),
        "min_m": min(distances),
        "max_m": max(distances),
        "min_s": min(deltas),
        "max_s": max(deltas),
    }


def set_score(events: list[dict]) -> dict[str, int]:
    """Turn the highest-xG shots into the required goals. Insert a shot if a team is short."""
    shots: dict[str, list[dict]] = defaultdict(list)
    for event in events:
        if event.get("type", {}).get("name") == "Shot":
            shots[event["team"]["name"]].append(event)

    inserted = Counter()
    for team_name, needed in SCORE.items():
        team_shots = shots[team_name]
        while len(team_shots) < needed:
            template = team_shots[-1] if team_shots else next(
                event for event in events if event.get("type", {}).get("name") == "Shot"
            )
            clone = json.loads(json.dumps(template))
            clone["id"] = str(uuid.uuid4())
            clone["team"] = dict(TEAMS[team_name])
            clone["possession_team"] = dict(TEAMS[team_name])
            clone["related_events"] = []
            clone["shot"].pop("key_pass_id", None)
            shift_timestamp(clone, 2 + inserted[team_name])
            events.append(clone)
            team_shots.append(clone)
            inserted[team_name] += 1

        ranked = sorted(
            team_shots,
            key=lambda event: (
                -(event["shot"].get("statsbomb_xg") or 0),
                event.get("index", 0),
            ),
        )
        for index, event in enumerate(ranked):
            outcome = event["shot"].get("outcome", {}).get("name")
            if index < needed:
                event["shot"]["outcome"] = dict(GOAL)
                event["shot"]["end_location"] = goal_location(index)
            elif outcome == "Goal":
                event["shot"]["outcome"] = dict(SAVED)
    return dict(inserted)


def retie_ids(events: list[dict]) -> None:
    mapping = {event["id"]: str(uuid.uuid4()) for event in events}

    def walk(obj, parent_key: str | None = None):
        if isinstance(obj, list):
            return [walk(item, parent_key) for item in obj]
        if isinstance(obj, dict):
            rebuilt = {}
            for key, value in obj.items():
                if key in {"assisted_shot_id", "key_pass_id"}:
                    if value in mapping:
                        rebuilt[key] = mapping[value]
                    continue
                if key == "related_events" and isinstance(value, list):
                    linked = [mapping[item] for item in value if item in mapping]
                    if linked:
                        rebuilt[key] = linked
                    continue
                if key == "id" and isinstance(value, str) and parent_key is None:
                    rebuilt[key] = mapping[value]
                    continue
                rebuilt[key] = walk(value, key)
            return rebuilt
        return obj

    rewritten = [walk(event) for event in events]
    events[:] = rewritten


def most_interesting(events: list[dict], width: int = 5) -> dict:
    last_minute = max(int(clock_seconds(event) // 60) for event in events)
    best = None
    for start in range(0, max(last_minute - width + 2, 1)):
        window = [
            event
            for event in events
            if start <= clock_seconds(event) / 60 < start + width
        ]
        shots = [event for event in window if event.get("type", {}).get("name") == "Shot"]
        goals = [event for event in shots if event["shot"]["outcome"]["name"] == "Goal"]
        xg = sum(event["shot"].get("statsbomb_xg") or 0 for event in shots)
        score = len(goals) * 15 + len(shots) * 2 + xg
        row = {
            "start": start,
            "end": start + width,
            "score": score,
            "goals": goals,
            "shots": shots,
            "xg": xg,
        }
        if best is None or (score, len(goals), xg) > (best["score"], len(best["goals"]), best["xg"]):
            best = row
    return best


def source_for_minute(minute: float) -> str:
    for spec in SEGMENTS:
        end = spec["end_min"]
        if minute >= spec["start_min"] and (end is None or minute < end):
            return spec["file"]
    return SEGMENTS[-1]["file"]


def verify(events: list[dict], original_names: set[str]) -> None:
    encoded = json.dumps(events)
    for name in original_names:
        if f'"{name}"' in encoded:
            raise AssertionError(f"Original name leaked into the synthetic file: {name}")

    teams = Counter()
    ids_to_names: dict[int, str] = {}
    names_to_ids: dict[str, int] = {}
    goals = Counter()
    indexes = []
    linked_ids = {event["id"] for event in events}

    for event in events:
        indexes.append(event["index"])
        team_name = (event.get("team") or {}).get("name")
        if team_name:
            teams[team_name] += 1
            if team_name not in TEAMS:
                raise AssertionError(f"Unexpected team {team_name}")
        for key in ("related_events",):
            for linked in event.get(key) or []:
                if linked not in linked_ids:
                    raise AssertionError(f"Dangling {key} {linked}")
        for nested_key in ("pass", "shot"):
            nested = event.get(nested_key) or {}
            for pointer in ("assisted_shot_id", "key_pass_id"):
                if pointer in nested and nested[pointer] not in linked_ids:
                    raise AssertionError(f"Dangling {pointer}")
        if event.get("type", {}).get("name") == "Shot" and event["shot"]["outcome"]["name"] == "Goal":
            goals[team_name] += 1
            end = event["shot"]["end_location"]
            if not (len(end) == 3 and end[0] == 120 and 36 <= end[1] <= 44 and 0 <= end[2] <= 2.67):
                raise AssertionError(f"Goal end_location is off the goal frame: {end}")
        player = event.get("player")
        if player:
            _check_player(player, team_name, ids_to_names, names_to_ids)

    if dict(goals) != SCORE:
        raise AssertionError(f"Score is {dict(goals)}, expected {SCORE}")
    if indexes != list(range(1, len(events) + 1)):
        raise AssertionError("Event indexes are not contiguous")
    surnames = [name.split(" ", 1)[1] for name in ids_to_names.values()]
    if len(surnames) != len(set(surnames)):
        raise AssertionError("Surnames are not unique")
    periods = {event["period"] for event in events}
    if periods != {1, 2}:
        raise AssertionError(f"Expected both halves, found periods {periods}")
    type_counts = Counter(event["type"]["name"] for event in events)
    if type_counts["Starting XI"] != 2:
        raise AssertionError("Expected one Starting XI event per team")
    print(f"verified {len(events)} events, score Arsesnail {goals['Arsesnail']}-Mancheater City {goals['Mancheater City']}")
    print(f"unique players {len(ids_to_names)}")


def _check_player(player: dict, team_name: str, ids_to_names, names_to_ids) -> None:
    first, last = player["name"].split(" ", 1)
    if first not in FIRST_NAMES:
        raise AssertionError(f"Unexpected first name {first}")
    if last not in SURNAMES[team_name]:
        raise AssertionError(f"{last} is not a {team_name} surname")
    previous = ids_to_names.get(player["id"])
    if previous not in (None, player["name"]):
        raise AssertionError(f"Player id {player['id']} changed name")
    ids_to_names[player["id"]] = player["name"]
    previous_id = names_to_ids.get(player["name"])
    if previous_id not in (None, player["id"]):
        raise AssertionError(f"{player['name']} has two ids")
    names_to_ids[player["name"]] = player["id"]


def describe(events: list[dict], inserted: dict[str, int], highlight: dict) -> None:
    print("segments")
    for spec in SEGMENTS:
        end = spec["end_min"] if spec["end_min"] is not None else "end"
        print(f"  {spec['start_min']}-{end} min  {spec['file']}")
    print(f"inserted shots {inserted or '{}'}")
    print("goals")
    for event in events:
        if event.get("type", {}).get("name") != "Shot":
            continue
        if event["shot"]["outcome"]["name"] != "Goal":
            continue
        print(
            f"  {event['minute']}:{event['second']:02d}  {event['team']['name']}"
            f"  {event['player']['name']}  xG {event['shot'].get('statsbomb_xg')}"
        )
    start, end = highlight["start"], highlight["end"]
    print(
        f"most interesting {start}-{end} min"
        f"  goals {len(highlight['goals'])}"
        f"  shots {len(highlight['shots'])}"
        f"  xG {highlight['xg']:.2f}"
        f"  source {source_for_minute(start)}"
    )
    for event in highlight["shots"]:
        outcome = event["shot"]["outcome"]["name"]
        print(
            f"  shot {event['minute']}:{event['second']:02d}  {event['team']['name']}"
            f"  {event['player']['name']}  {outcome}  xG {event['shot'].get('statsbomb_xg')}"
        )


def build() -> list[dict]:
    rng = random.Random(13)
    squads = {name: Squad(name, rng) for name in TEAMS}
    player_map: dict[int, dict] = {}
    original_names: set[str] = set()
    combined: list[dict] = []

    for segment_index, spec in enumerate(SEGMENTS):
        events = load_segment(spec)
        remember_names(events, original_names)
        team_map = map_teams(events)
        for source_id, source_team_id, position in harvest(events):
            squad = squads[team_map[source_team_id]["name"]]
            player_map[source_id] = squad.assign(source_id, position, segment_index)
        combined.extend(remap(event, player_map, team_map) for event in events)

    combined.sort(key=lambda event: (event["period"], event["timestamp"], event.get("index", 0)))
    inserted = set_score(combined)
    combined.sort(key=lambda event: (event["period"], event["timestamp"], event.get("index", 0)))
    for index, event in enumerate(combined, start=1):
        event["index"] = index
    noise = perturb(combined, rng)
    combined.sort(key=lambda event: (event["period"], event["timestamp"], event.get("index", 0)))
    for index, event in enumerate(combined, start=1):
        event["index"] = index
    retie_ids(combined)
    verify(combined, original_names)

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(combined, indent=2, ensure_ascii=False) + "\n")
    reloaded = json.loads(OUTPUT.read_text())
    verify(reloaded, original_names)
    describe(reloaded, inserted, most_interesting(reloaded))
    print(
        f"noise  locations {noise['locations']}"
        f"  {noise['min_m']:.4f}–{noise['max_m']:.4f} m"
        f"  timestamps {noise['min_s']:.4f}–{noise['max_s']:.4f} s"
    )
    print(f"wrote {OUTPUT} ({OUTPUT.stat().st_size} bytes)")
    return reloaded


if __name__ == "__main__":
    build()
