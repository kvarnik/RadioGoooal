"""Offline agent workflow. Foundry replaces the template writer when it is configured."""

from __future__ import annotations

import json
from pathlib import Path

import yaml

from facts import EVENTS_PATH, _player_names
from safety import screen_line
from templates import BIASES, LANGS, MOMENTS, STYLES, _bundle, _pair
from verify import verify_line

AGENTS = Path(__file__).resolve().parent / "agents"


def load_agents() -> list[dict]:
    loaded = []
    for path in sorted(AGENTS.glob("*.yaml")):
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        data["file"] = path.name
        loaded.append(data)
    return sorted(loaded, key=lambda agent: (agent["order"], agent["name"]))


def _moment(sec: int) -> dict:
    current = MOMENTS[0]
    for moment in MOMENTS:
        if moment["t"] <= sec:
            current = moment
    return current


def squad_names() -> list[str]:
    events = json.loads(EVENTS_PATH.read_text(encoding="utf-8"))
    return sorted(_player_names(events).values())


def rewrite_call(sec: int, style: str, lang: str, bias: str, squad: list[str]) -> dict:
    if style not in STYLES or lang not in LANGS or bias not in BIASES:
        raise ValueError("style, language, or bias is not one of the cached choices")
    if not 0 <= sec <= 300:
        raise ValueError("clock is outside 87:00–92:00")

    moment = _moment(sec)
    bundle = _bundle(moment)
    call, _analyst = _pair(moment["id"], style, lang, bias)
    proposed, _ = _pair(moment["id"], "tactical" if style != "tactical" else "classic", lang, bias)
    steps = [
        {"agent": "interpreter", "action": "Copied the fact bundle. No model figure was added."},
        {"agent": "moment_editor", "action": f"Kept {moment['id']}."},
        {"agent": "play_by_play", "action": "Wrote from the bundle, concurrently with the analyst."},
        {"agent": "analyst", "action": "Wrote from the bundle, concurrently with play-by-play."},
    ]

    errors = verify_line(proposed, bundle, squad)
    if errors:
        line = call
        verdict = "template"
        steps.append({"agent": "verifier", "action": f"Rejected the line: {', '.join(errors)}."})
    else:
        line = proposed
        verdict = "pass"
        steps.append({"agent": "verifier", "action": "Passed."})

    screened = screen_line(line)
    if screened["verdict"] == "blocked":
        line = call
        verdict = "safety"
        if screen_line(line)["verdict"] == "blocked":
            raise RuntimeError("template line blocked")
        steps.append(
            {"agent": "content_safety", "action": f"Blocked {screened['term']}. Used the template."}
        )
    elif screened["source"] == "azure":
        steps.append({"agent": "content_safety", "action": "Azure Content Safety passed."})
    else:
        steps.append({
            "agent": "content_safety",
            "action": "Local word list passed. Azure Content Safety is not configured.",
        })

    return {
        "line": line,
        "verdict": verdict,
        "moment": moment["id"],
        "steps": steps,
        "note": "Verifier finished. Foundry and Speech are not configured, so this is the cached template.",
    }
