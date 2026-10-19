"""Facts for synthetic match 9000001. Numbers come from the event file only."""

from __future__ import annotations

import math
from collections import Counter, defaultdict, deque
from pathlib import Path

EVENTS_PATH = Path(__file__).resolve().parent / "data" / "9000001.json"

HOME_ID = 1
AWAY_ID = 36
HOME = "Arsesnail"
AWAY = "Mancheater City"
TEAM_NAME = {HOME_ID: HOME, AWAY_ID: AWAY}
OTHER = {HOME_ID: AWAY_ID, AWAY_ID: HOME_ID}

WINDOW_START = 87 * 60
WINDOW_END = 92 * 60
WINDOW = list(range(WINDOW_START, WINDOW_END + 1))

INCOMPLETE = {"Incomplete", "Out", "Unknown", "Pass Offside"}
NOT_A_TOUCH = {"Pressure", "Dribbled Past"}
HEIGHT_POINTS = {"Ground Pass": 0, "Low Pass": 8, "High Pass": 14}


def event_second(event: dict) -> int:
    return int(event["minute"]) * 60 + int(event["second"])


def pass_complete(event: dict) -> bool:
    outcome = (event.get("pass") or {}).get("outcome")
    if outcome is None:
        return True
    return outcome.get("name") not in INCOMPLETE


def pass_difficulty(event: dict) -> int:
    """Difficulty from 0 to 100. Weights: distance 34, forward 26, height 14, pressure 14, kind 12."""
    block = event["pass"]
    start = event.get("location")
    end = block.get("end_location")
    length = block.get("length")
    if length is None and start and end:
        length = math.hypot(end[0] - start[0], end[1] - start[1])
    length = float(length or 0)
    forward = max(0.0, end[0] - start[0]) if start and end else 0.0
    height = HEIGHT_POINTS.get((block.get("height") or {}).get("name"), 0)
    pressure = 14 if event.get("under_pressure") else 0
    kind = 12 if block.get("cross") or block.get("through_ball") else 0
    score = min(length, 40) / 40 * 34 + min(forward, 30) / 30 * 26 + height + pressure + kind
    return round(max(0.0, min(100.0, score)))


def shot_speed_mps(event: dict) -> float | None:
    """Ground speed in m/s. Shots shorter than 0.2 seconds have no speed."""
    if event.get("type", {}).get("name") != "Shot":
        return None
    duration = float(event.get("duration") or 0)
    if duration < 0.2:
        return None
    start = event.get("location")
    end = (event.get("shot") or {}).get("end_location")
    if not start or not end:
        return None
    yards = math.hypot(end[0] - start[0], end[1] - start[1])
    return yards * 0.9144 / duration


def is_touch(event: dict) -> bool:
    return "player" in event and event.get("type", {}).get("name") not in NOT_A_TOUCH


def fare_count(stints: list[tuple[int, int]], touches: list[int], at_second: int) -> int:
    """Finished 10-minute spells on the pitch with no touch. A spell counts once its end is reached."""
    total = 0
    for start_min in range(0, 100, 10):
        begin = start_min * 60
        end = begin + 600
        if at_second < end:
            break
        covered = any(a <= begin and end <= b for a, b in stints)
        touched = any(begin <= t < end for t in touches)
        if covered and not touched:
            total += 1
    return total


def _close(stints: dict[int, list[tuple[int, int]]], open_from: dict[int, int], pid: int, at: int) -> None:
    if pid in open_from:
        stints.setdefault(pid, []).append((open_from.pop(pid), at))


def _open(open_from: dict[int, int], pid: int, at: int) -> None:
    if pid not in open_from:
        open_from[pid] = at


def build_stints(events: list[dict]) -> dict[int, list[tuple[int, int]]]:
    """On-pitch intervals, end exclusive. A tactical shift replaces that team's eleven."""
    xi: dict[int, list[int]] = {}
    open_from: dict[int, int] = {}
    stints: dict[int, list[tuple[int, int]]] = {}
    last = 0
    ordered = sorted(events, key=lambda event: (event_second(event), event.get("index", 0)))
    for event in ordered:
        t = event_second(event)
        last = max(last, t)
        kind = event.get("type", {}).get("name")
        team_id = (event.get("team") or {}).get("id")
        if kind in {"Starting XI", "Tactical Shift"}:
            ids = [row["player"]["id"] for row in event["tactics"]["lineup"]]
            current = xi.get(team_id, [])
            for pid in current:
                if pid not in ids:
                    _close(stints, open_from, pid, t)
            for pid in ids:
                _open(open_from, pid, t)
            xi[team_id] = list(ids)
        elif kind == "Substitution":
            off = event["player"]["id"]
            on = event["substitution"]["replacement"]["id"]
            current = list(xi.get(team_id, []))
            if off not in current:
                continue
            _close(stints, open_from, off, t)
            if on in current and on != off:
                current = [pid for pid in current if pid != off]
            else:
                current = [on if pid == off else pid for pid in current]
                _open(open_from, on, t)
            xi[team_id] = current
    for pid in list(open_from):
        _close(stints, open_from, pid, last + 1)
    return stints


def seconds_on_pitch(stints: list[tuple[int, int]], t: int) -> int:
    total = 0
    for start, end in stints:
        hi = min(end, t + 1)
        if hi > start:
            total += hi - start
    return total


def _trim(times: deque[int], t: int) -> None:
    while times and times[0] <= t - 60:
        times.popleft()


def _player_names(events: list[dict]) -> dict[int, str]:
    names: dict[int, str] = {}
    for event in events:
        player = event.get("player")
        if player:
            names[player["id"]] = player["name"]
        for row in (event.get("tactics") or {}).get("lineup") or []:
            names[row["player"]["id"]] = row["player"]["name"]
        replacement = (event.get("substitution") or {}).get("replacement")
        if replacement:
            names[replacement["id"]] = replacement["name"]
    return names


def _teams_and_positions(events: list[dict]) -> tuple[dict[int, int], dict[int, str]]:
    team_of: dict[int, int] = {}
    position_of: dict[int, str] = {}
    ordered = sorted(events, key=lambda event: (event_second(event), event.get("index", 0)))
    for event in ordered:
        if event_second(event) > WINDOW_START:
            break
        kind = event.get("type", {}).get("name")
        team_id = (event.get("team") or {}).get("id")
        if kind in {"Starting XI", "Tactical Shift"}:
            for row in event["tactics"]["lineup"]:
                pid = row["player"]["id"]
                team_of[pid] = team_id
                position_of[pid] = row["position"]["name"]
        elif kind == "Substitution":
            off = event["player"]["id"]
            on = event["substitution"]["replacement"]["id"]
            team_of[on] = team_id
            if off in position_of and on not in position_of:
                position_of[on] = position_of[off]
    return team_of, position_of


def lineup_ids(events: list[dict], t: int) -> dict[int, list[int]]:
    stints = build_stints(events)
    team_of, _ = _teams_and_positions(events)
    out: dict[int, list[int]] = {HOME_ID: [], AWAY_ID: []}
    for pid, spans in stints.items():
        if any(start <= t < end for start, end in spans):
            team_id = team_of.get(pid)
            if team_id in out:
                out[team_id].append(pid)
    return out


def build_facts(events: list[dict]) -> dict:
    ordered = sorted(events, key=lambda event: (event_second(event), event.get("index", 0)))
    names = _player_names(events)
    team_of, position_of = _teams_and_positions(events)
    stints = build_stints(events)
    passer_of = {
        event["id"]: event["player"]["id"]
        for event in ordered
        if event.get("type", {}).get("name") == "Pass" and event.get("player")
    }

    score: Counter[int] = Counter()
    shots: Counter[int] = Counter()
    xg: dict[int, float] = defaultdict(float)
    pass_n: Counter[int] = Counter()
    pass_ok: Counter[int] = Counter()
    control_times: dict[int, deque[int]] = {HOME_ID: deque(), AWAY_ID: deque()}
    pressure_times: dict[int, deque[int]] = {HOME_ID: deque(), AWAY_ID: deque()}
    lose_times: dict[int, deque[int]] = {HOME_ID: deque(), AWAY_ID: deque()}

    p_touch: Counter[int] = Counter()
    p_pass: Counter[int] = Counter()
    p_pass_ok: Counter[int] = Counter()
    p_shot: Counter[int] = Counter()
    p_xg: dict[int, float] = defaultdict(float)
    p_goal: Counter[int] = Counter()
    p_assist: Counter[int] = Counter()
    p_dribble: Counter[int] = Counter()
    p_duel: Counter[int] = Counter()
    p_interception: Counter[int] = Counter()
    p_foul: Counter[int] = Counter()
    p_card: Counter[int] = Counter()
    p_diff_sum: dict[int, float] = defaultdict(float)
    p_goal_clock: dict[int, str] = {}
    p_goal_xg: dict[int, float] = {}
    touch_times: dict[int, list[int]] = defaultdict(list)
    touch_path: dict[int, float] = defaultdict(float)
    last_touch: dict[int, tuple[float, float]] = {}
    # (difficulty, length, -second) so the harder, then longer, then earlier pass wins.
    hardest: dict[int, tuple[int, float, int]] = {}
    hardest_label: dict[int, str] = {}

    def snapshot(t: int) -> dict:
        for bucket in (control_times, pressure_times, lose_times):
            for times in bucket.values():
                _trim(times, t)
        control = {}
        control_index = {}
        for team_id in (HOME_ID, AWAY_ID):
            chaos = (
                len(pressure_times[OTHER[team_id]])
                + len(lose_times[team_id])
            )
            index = len(control_times[team_id]) - chaos
            control[str(team_id)] = "control" if index >= 0 else "chaos"
            control_index[str(team_id)] = index
        pass_pct = {}
        for team_id in (HOME_ID, AWAY_ID):
            total = pass_n[team_id]
            pass_pct[str(team_id)] = round(100 * pass_ok[team_id] / total) if total else None
        players = []
        for pid, name in sorted(names.items(), key=lambda item: item[0]):
            taken = p_pass[pid]
            players.append(
                {
                    "id": pid,
                    "name": name,
                    "team_id": team_of.get(pid),
                    "team": TEAM_NAME.get(team_of.get(pid), ""),
                    "position": position_of.get(pid, ""),
                    "minutes": seconds_on_pitch(stints.get(pid, []), t) // 60,
                    "touches": p_touch[pid],
                    "passes": taken,
                    "pass_pct": round(100 * p_pass_ok[pid] / taken) if taken else None,
                    "shots": p_shot[pid],
                    "xg": round(p_xg[pid], 4),
                    "goals": p_goal[pid],
                    "assists": p_assist[pid],
                    "dribbles": p_dribble[pid],
                    "duels": p_duel[pid],
                    "interceptions": p_interception[pid],
                    "fouls": p_foul[pid],
                    "cards": p_card[pid],
                    "avg_difficulty": round(p_diff_sum[pid] / taken, 1) if taken else None,
                    "hardest_pass": hardest_label.get(pid, ""),
                    "passenger_fare": fare_count(stints.get(pid, []), touch_times[pid], t),
                    "touch_path": round(touch_path[pid], 1),
                    "goal_clock": p_goal_clock.get(pid, ""),
                    "goal_xg": p_goal_xg.get(pid),
                }
            )
        return {
            "t": t,
            "score": {str(HOME_ID): score[HOME_ID], str(AWAY_ID): score[AWAY_ID]},
            "shots": {str(HOME_ID): shots[HOME_ID], str(AWAY_ID): shots[AWAY_ID]},
            "xg": {str(HOME_ID): round(xg[HOME_ID], 6), str(AWAY_ID): round(xg[AWAY_ID], 6)},
            "pass_pct": pass_pct,
            "control": control,
            "control_index": control_index,
            "players": players,
        }

    rows = []
    cursor = 0
    for t in WINDOW:
        while cursor < len(ordered) and event_second(ordered[cursor]) <= t:
            event = ordered[cursor]
            cursor += 1
            when = event_second(event)
            kind = event.get("type", {}).get("name")
            team_id = (event.get("team") or {}).get("id")
            player = event.get("player") or {}
            pid = player.get("id")
            if kind == "Pass" and team_id in TEAM_NAME:
                pass_n[team_id] += 1
                if pass_complete(event):
                    pass_ok[team_id] += 1
                    control_times[team_id].append(when)
                if pid is not None:
                    p_pass[pid] += 1
                    difficulty = pass_difficulty(event)
                    p_diff_sum[pid] += difficulty
                    if pass_complete(event):
                        p_pass_ok[pid] += 1
                        length = float(event["pass"].get("length") or 0)
                        rank = (difficulty, length, -when)
                        if pid not in hardest or rank > hardest[pid]:
                            hardest[pid] = rank
                            clock = f"{event['minute']}:{int(event['second']):02d}"
                            hardest_label[pid] = f"{difficulty} at {clock}"
            elif kind == "Shot" and team_id in TEAM_NAME:
                shots[team_id] += 1
                value = float((event.get("shot") or {}).get("statsbomb_xg") or 0)
                xg[team_id] += value
                if pid is not None:
                    p_shot[pid] += 1
                    p_xg[pid] += value
                outcome = ((event.get("shot") or {}).get("outcome") or {}).get("name")
                if outcome == "Goal":
                    score[team_id] += 1
                    if pid is not None:
                        p_goal[pid] += 1
                        p_goal_clock[pid] = f"{event['minute']}:{int(event['second']):02d}"
                        p_goal_xg[pid] = round(value, 2)
                    key = (event.get("shot") or {}).get("key_pass_id")
                    if key in passer_of:
                        p_assist[passer_of[key]] += 1
            elif kind == "Pressure" and team_id in TEAM_NAME:
                pressure_times[team_id].append(when)
            elif kind in {"Dispossessed", "Miscontrol"} and team_id in TEAM_NAME:
                lose_times[team_id].append(when)
            elif kind == "Dribble" and pid is not None:
                p_dribble[pid] += 1
            elif kind == "Duel" and pid is not None:
                p_duel[pid] += 1
            elif kind == "Interception" and pid is not None:
                p_interception[pid] += 1
            elif kind == "Foul Committed" and pid is not None:
                p_foul[pid] += 1
                if (event.get("foul_committed") or {}).get("card"):
                    p_card[pid] += 1
            if (event.get("bad_behaviour") or {}).get("card") and pid is not None:
                p_card[pid] += 1
            if pid is not None and is_touch(event):
                p_touch[pid] += 1
                touch_times[pid].append(when)
                loc = event.get("location")
                if loc:
                    point = (float(loc[0]), float(loc[1]))
                    previous = last_touch.get(pid)
                    if previous is not None:
                        touch_path[pid] += math.hypot(point[0] - previous[0], point[1] - previous[1])
                    last_touch[pid] = point
        rows.append(snapshot(t))

    return {
        "match_id": 9000001,
        "t0": WINDOW_START,
        "count": len(rows),
        "teams": [
            {"id": HOME_ID, "name": HOME, "side": "home"},
            {"id": AWAY_ID, "name": AWAY, "side": "away"},
        ],
        "rows": rows,
    }


def row_at(facts: dict, minute: int, second: int) -> dict:
    return facts["rows"][(minute * 60 + second) - facts["t0"]]


def player_row(facts_row: dict, name: str) -> dict:
    for player in facts_row["players"]:
        if player["name"] == name:
            return player
    raise KeyError(name)
