"""Write the speech-cache manifest. Synthesis runs only when Speech is configured."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from facts import EVENTS_PATH, _player_names
from speech import build_speech_cache

DEST = Path(__file__).resolve().parents[1] / "data" / "audio"


def main() -> None:
    events = json.loads(EVENTS_PATH.read_text(encoding="utf-8"))
    cache = build_speech_cache(sorted(_player_names(events).values()), DEST)
    print(
        f"lines {cache['lines']} characters {cache['characters']} "
        f"pass_rate {cache['pass_rate']} speech {cache['speech']}"
    )


if __name__ == "__main__":
    main()
