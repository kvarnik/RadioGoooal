"""Write the fact file, the template lines, the position track, and the check report."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from facts import EVENTS_PATH, _player_names, build_facts
from positions import (
    POSITIONS_PATH,
    REPORT_PATH,
    SEED,
    SPEED_PATH,
    build_positions,
    speed_table,
    write_report,
)
from templates import build_templates

FACTS_PATH = Path(__file__).resolve().parents[1] / "data" / "facts.json"
TEMPLATES_PATH = Path(__file__).resolve().parents[1] / "data" / "templates.json"


def dump(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")


def main() -> None:
    events = json.loads(EVENTS_PATH.read_text())
    dump(FACTS_PATH, build_facts(events))
    dump(TEMPLATES_PATH, build_templates(sorted(_player_names(events).values())))
    positions, late = build_positions(events, seed=SEED)
    dump(POSITIONS_PATH, positions)
    dump(SPEED_PATH, speed_table(positions["frames"]))
    write_report(positions["frames"], late, REPORT_PATH)
    print(f"facts {FACTS_PATH}")
    print(f"templates {TEMPLATES_PATH}")
    print(f"positions {POSITIONS_PATH}")
    print(f"report {REPORT_PATH}")


if __name__ == "__main__":
    main()
