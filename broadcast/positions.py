"""One-hertz positions for 87:00–92:00. The picture is reconstructed."""

from __future__ import annotations

import itertools
import math
from pathlib import Path

from facts import AWAY_ID, HOME_ID, WINDOW_END, WINDOW_START, build_stints, event_second

ROOT = Path(__file__).resolve().parents[1]
POSITIONS_PATH = Path(__file__).resolve().parent / "data" / "9000001-positions.json"
REPORT_PATH = ROOT / "broadcast" / "data" / "positions-report.md"
SPEED_PATH = ROOT / "broadcast" / "data" / "speed.json"
SEED = 9000001

# Internal steps stay under 10 m/s after coordinates are rounded to 0.01 yards.
STEP_CAP = 10 / 0.9144 - 0.05
BALL_FLAG_MPS = 40.0

# Depth is the fraction of the span from a team's own goal toward the ball.
# Lane 0 is the left touchline in that team's attacking frame.
SLOTS = {
    "Goalkeeper": (0.07, 0.50),
    "Right Back": (0.24, 0.86),
    "Right Center Back": (0.20, 0.64),
    "Left Center Back": (0.20, 0.36),
    "Left Back": (0.24, 0.14),
    "Right Defensive Midfield": (0.40, 0.62),
    "Left Defensive Midfield": (0.40, 0.38),
    "Right Wing": (0.58, 0.86),
    "Center Attacking Midfield": (0.60, 0.50),
    "Left Wing": (0.58, 0.14),
    "Center Forward": (0.78, 0.50),
}


def orient(team_id: int, x: float, y: float) -> tuple[float, float]:
    """Arsesnail attack toward x = 120. Mancheater City events are mirrored."""
    if team_id == AWAY_ID:
        return 120 - x, 80 - y
    return x, y


def _duration(event: dict) -> float:
    value = event.get("duration")
    return 0.0 if value is None else float(value)


def _end_xy(event: dict) -> tuple[float, float] | None:
    for key in ("pass", "carry", "shot"):
        block = event.get(key) or {}
        loc = block.get("end_location")
        if loc:
            return float(loc[0]), float(loc[1])
    return None


def _ordered(events: list[dict]) -> list[dict]:
    return sorted(events, key=lambda event: (event_second(event), event.get("index", 0)))


def ball_frames(events: list[dict]) -> list[dict]:
    located = [
        event
        for event in _ordered(events)
        if event.get("location") and event.get("team") and event_second(event) <= WINDOW_END
    ]
    frames = []
    last = (60.0, 40.0)
    cursor = 0
    for t in range(WINDOW_START, WINDOW_END + 1):
        chosen = None
        scan = cursor
        while scan < len(located):
            event = located[scan]
            start = event_second(event)
            if start > t:
                break
            duration = _duration(event)
            covers = duration >= 0.2 and start <= t <= start + duration
            snaps = duration < 0.2 and start == t
            if covers or snaps:
                chosen = event
            if start < t:
                cursor = scan + 1
            scan += 1
        if chosen is None:
            frames.append({"xy": last, "snap": False})
            continue
        start = event_second(chosen)
        duration = _duration(chosen)
        team_id = chosen["team"]["id"]
        x0, y0 = orient(team_id, float(chosen["location"][0]), float(chosen["location"][1]))
        end = _end_xy(chosen)
        x1, y1 = orient(team_id, *end) if end else (x0, y0)
        if duration < 0.2:
            last = (x1, y1)
            frames.append({"xy": last, "snap": True})
        else:
            span = t - start
            u = min(1.0, max(0.0, span / duration))
            last = (x0 + (x1 - x0) * u, y0 + (y1 - y0) * u)
            frames.append({"xy": last, "snap": False})
    return frames


def _roster(events: list[dict]) -> dict[int, dict]:
    """Identity of each player from the last lineup at or before 87:00, plus later shifts."""
    roster: dict[int, dict] = {}
    for event in _ordered(events):
        kind = event.get("type", {}).get("name")
        if kind not in {"Starting XI", "Tactical Shift"}:
            continue
        if event_second(event) > WINDOW_END:
            continue
        team_id = event["team"]["id"]
        for row in event["tactics"]["lineup"]:
            pid = row["player"]["id"]
            roster[pid] = {
                "id": pid,
                "name": row["player"]["name"],
                "team_id": team_id,
                "position": row["position"]["name"],
            }
    return roster


def on_pitch_ids(events: list[dict]) -> list[set[int]]:
    stints = build_stints(events)
    frames = []
    for t in range(WINDOW_START, WINDOW_END + 1):
        present = {
            pid
            for pid, spans in stints.items()
            if any(start <= t < end for start, end in spans)
        }
        frames.append(present)
    return frames


def _soft(player: dict, ball: tuple[float, float]) -> tuple[float, float]:
    slot = SLOTS.get(player["position"])
    if slot is None:
        raise RuntimeError(f"{player['name']} has no slot for {player['position']}")
    depth, lane = slot
    attacking_right = player["team_id"] == HOME_ID
    own = 0.0 if attacking_right else 120.0
    sign = 1.0 if attacking_right else -1.0
    reach = max(8.0, abs(ball[0] - own) - 3.0)
    x = own + sign * depth * reach
    y = (lane if attacking_right else 1 - lane) * 80
    return (min(119.0, max(1.0, x)), min(78.0, max(2.0, y)))


def _pins(events: list[dict], present: list[set[int]]) -> list[dict[int, tuple[float, float]]]:
    pins: list[dict[int, tuple[float, float]]] = [{} for _ in present]
    freezes: list[dict[int, tuple[float, float]]] = [{} for _ in present]
    for event in _ordered(events):
        t = event_second(event)
        if t < WINDOW_START or t > WINDOW_END:
            continue
        index = t - WINDOW_START
        team_id = (event.get("team") or {}).get("id")
        player = event.get("player")
        if player and event.get("location") and player["id"] in present[index] and team_id:
            pins[index][player["id"]] = orient(
                team_id, float(event["location"][0]), float(event["location"][1])
            )
        if event.get("type", {}).get("name") == "Shot":
            for row in (event.get("shot") or {}).get("freeze_frame") or []:
                pid = row["player"]["id"]
                if pid not in present[index] or not team_id:
                    continue
                freezes[index][pid] = orient(
                    team_id, float(row["location"][0]), float(row["location"][1])
                )
    for index, frame in enumerate(freezes):
        pins[index].update(frame)
    return pins


def _step(pos: tuple[float, float], target: tuple[float, float]) -> tuple[float, float]:
    dx = target[0] - pos[0]
    dy = target[1] - pos[1]
    dist = math.hypot(dx, dy)
    if dist <= STEP_CAP or dist == 0:
        return target
    scale = STEP_CAP / dist
    return (pos[0] + dx * scale, pos[1] + dy * scale)


def build_positions(events: list[dict], seed: int = SEED) -> tuple[dict, list[dict]]:
    if seed != SEED:
        raise RuntimeError(f"This track is built with seed {SEED}")
    roster = _roster(events)
    present = on_pitch_ids(events)
    balls = ball_frames(events)
    pins = _pins(events, present)
    ids = sorted(present[0])
    for index, frame_ids in enumerate(present):
        if frame_ids != set(ids):
            missing = set(ids) - frame_ids
            extra = frame_ids - set(ids)
            raise RuntimeError(f"Frame {index} changed the elevens: off {missing} on {extra}")
    players = [roster[pid] for pid in ids]
    home = sum(player["team_id"] == HOME_ID for player in players)
    away = len(players) - home
    if home != 11 or away != 11:
        raise RuntimeError(f"Window eleven is {home} and {away}, expected 11 and 11")
    unknown = [player for player in players if player["position"] not in SLOTS]
    if unknown:
        names = ", ".join(f"{player['name']} ({player['position']})" for player in unknown)
        raise RuntimeError(f"No formation slot for {names}")

    soft = [[_soft(player, balls[index]["xy"]) for player in players] for index in range(301)]
    pos = {player["id"]: soft[0][i] for i, player in enumerate(players)}
    solved: list[dict[int, tuple[float, float]]] = []
    late: list[dict] = []
    for index in range(301):
        for slot, player in enumerate(players):
            pid = player["id"]
            nxt = None
            for ahead in range(index, 301):
                if pid in pins[ahead]:
                    nxt = (ahead, pins[ahead][pid])
                    break
            aim = soft[index][slot]
            if nxt:
                ahead, pin = nxt
                dist = math.hypot(pin[0] - pos[pid][0], pin[1] - pos[pid][1])
                left = ahead - index
                if left == 0 or dist > max(0, left - 1) * STEP_CAP:
                    aim = pin
            pos[pid] = _step(pos[pid], aim)
            if pid in pins[index]:
                miss = math.hypot(pos[pid][0] - pins[index][pid][0], pos[pid][1] - pins[index][pid][1])
                if miss > 0.5:
                    late.append(
                        {
                            "t": WINDOW_START + index,
                            "id": pid,
                            "name": player["name"],
                            "yards": round(miss, 2),
                        }
                    )
        solved.append(dict(pos))

    frames = []
    for index, t in enumerate(range(WINDOW_START, WINDOW_END + 1)):
        frames.append(
            {
                "t": t,
                "ball": [round(balls[index]["xy"][0], 2), round(balls[index]["xy"][1], 2)],
                "snap": balls[index]["snap"],
                "players": [
                    {
                        "id": player["id"],
                        "team_id": player["team_id"],
                        "x": round(solved[index][player["id"]][0], 2),
                        "y": round(solved[index][player["id"]][1], 2),
                    }
                    for player in players
                ],
            }
        )
    data = {
        "match_id": 9000001,
        "seed": seed,
        "pitch": {"length": 120, "width": 80, "units": "yards"},
        "fixed_frame": "Arsesnail attacks +x. Mancheater City locations are mirrored.",
        "t0": WINDOW_START,
        "frames": frames,
    }
    return data, late


def _player_steps(frames: list[dict]) -> list[float]:
    speeds = []
    previous = {player["id"]: (player["x"], player["y"]) for player in frames[0]["players"]}
    for frame in frames[1:]:
        for player in frame["players"]:
            before = previous[player["id"]]
            yards = math.hypot(player["x"] - before[0], player["y"] - before[1])
            speeds.append(yards * 0.9144)
            previous[player["id"]] = (player["x"], player["y"])
    return speeds


def _ball_speeds(frames: list[dict]) -> list[float]:
    speeds = []
    for before, after in itertools.pairwise(frames):
        if after["snap"]:
            continue
        yards = math.hypot(after["ball"][0] - before["ball"][0], after["ball"][1] - before["ball"][1])
        speeds.append(yards * 0.9144)
    return speeds


def _min_gap(frames: list[dict]) -> float:
    smallest = math.inf
    for frame in frames:
        points = [(player["x"], player["y"]) for player in frame["players"]]
        for i, left in enumerate(points):
            for right in points[i + 1 :]:
                smallest = min(smallest, math.hypot(left[0] - right[0], left[1] - right[1]))
    return smallest


def speed_table(frames: list[dict]) -> dict:
    ids = [player["id"] for player in frames[0]["players"]]
    previous = {player["id"]: (player["x"], player["y"]) for player in frames[0]["players"]}
    current = {str(pid): [0.0] for pid in ids}
    top = {str(pid): [0.0] for pid in ids}
    distance = {str(pid): [0.0] for pid in ids}
    for frame in frames[1:]:
        for player in frame["players"]:
            key = str(player["id"])
            before = previous[player["id"]]
            yards = math.hypot(player["x"] - before[0], player["y"] - before[1])
            mps = round(yards * 0.9144, 2)
            current[key].append(mps)
            top[key].append(round(max(top[key][-1], mps), 2))
            distance[key].append(round(distance[key][-1] + yards * 0.9144, 1))
            previous[player["id"]] = (player["x"], player["y"])
    return {"current": current, "top": top, "distance": distance}


def write_report(frames: list[dict], late: list[dict], path: Path = REPORT_PATH) -> None:
    player_speeds = _player_steps(frames)
    ball_speeds = _ball_speeds(frames)
    flags = [speed for speed in ball_speeds if speed > BALL_FLAG_MPS]
    full = sum(
        1
        for frame in frames
        if sum(player["team_id"] == HOME_ID for player in frame["players"]) == 11
        and sum(player["team_id"] == AWAY_ID for player in frame["players"]) == 11
    )
    lines = [
        "# Position check, 87:00–92:00",
        "",
        f"Seed {SEED}. {len(frames)} frames. The generator does not use a random draw;",
        "the seed is fixed so a rerun can fail if the file changes.",
        "",
        f"- Highest player speed: {max(player_speeds):.2f} m/s. Cap: 10 m/s.",
        f"- Highest drawn ball speed: {max(ball_speeds) if ball_speeds else 0:.2f} m/s.",
        f"- Ball segments over {BALL_FLAG_MPS:.0f} m/s: {len(flags)}. A snap is not a segment.",
        f"- Frames with 11 a side: {full} of {len(frames)}.",
        f"- Smallest gap between two players: {_min_gap(frames):.2f} yards.",
        f"- Late arrivals (pin missed by more than 0.5 yards): {len(late)}.",
        "",
    ]
    if late:
        lines.append("Late arrivals:")
        lines.append("")
        for row in late[:40]:
            minute, second = divmod(row["t"], 60)
            lines.append(f"- {minute}:{second:02d} {row['name']} short by {row['yards']} yards")
        if len(late) > 40:
            lines.append(f"- {len(late) - 40} more")
        lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")
