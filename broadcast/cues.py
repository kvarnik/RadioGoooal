"""Match-effect cues. The deck plays this list and does not rescan the event file."""

from __future__ import annotations

from facts import WINDOW_END, WINDOW_START, event_second

KICK_PASSES = {"Goal Kick", "Kick Off"}


def match_cues(events: list[dict]) -> list[dict]:
    found: dict[int, list[str]] = {}

    def add(t: int, name: str) -> None:
        effects = found.setdefault(t, [])
        if name not in effects:
            effects.append(name)

    last = WINDOW_END - WINDOW_START
    for event in events:
        t = event_second(event) - WINDOW_START
        if t < 0 or t > last:
            continue
        kind = (event.get("type") or {}).get("name")
        if kind == "Shot":
            add(t, "kick")
            outcome = ((event.get("shot") or {}).get("outcome") or {}).get("name")
            if outcome == "Goal":
                add(t, "goal")
        elif kind == "Pass":
            pass_type = ((event.get("pass") or {}).get("type") or {}).get("name")
            if pass_type in KICK_PASSES:
                add(t, "kick")
        elif kind == "Foul Committed":
            add(t, "whistle")
    add(last, "whistle")
    return [{"t": t, "effects": found[t]} for t in sorted(found)]
