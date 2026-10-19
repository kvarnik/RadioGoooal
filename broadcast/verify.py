"""Deterministic check that a spoken line stays inside the fact bundle."""

from __future__ import annotations

import re

BANNED = re.compile(r"\b(arsenal|manchester|man\s+city|premier\s+league)\b", re.IGNORECASE)
PREDICTION = re.compile(
    r"\b(will win|going to win|certain to|nailed on|odds|bet|accumulator)\b",
    re.IGNORECASE,
)
CLOCK = re.compile(r"\b(\d{1,2}:\d{2})\b")
SCORE = re.compile(r"\b(\d+)\s*[–-]\s*(\d+)\b")
NUMBER = re.compile(r"\d+(?:\.\d+)?")


def verify_line(line: str, bundle: dict, squad: list[str]) -> list[str]:
    """Return the mismatches. An empty list means the line may be cached."""
    errors: list[str] = []
    if BANNED.search(line):
        errors.append("real club name")
    if PREDICTION.search(line):
        errors.append("prediction")

    allowed_clocks = set(bundle["clocks"])
    for clock in CLOCK.findall(line):
        if clock not in allowed_clocks:
            errors.append(f"clock {clock}")

    stripped = SCORE.sub(" ", CLOCK.sub(" ", line))
    allowed_scores = set(bundle["scores"])
    for left, right in SCORE.findall(line):
        key = f"{int(left)}-{int(right)}"
        if key not in allowed_scores:
            errors.append(f"score {key}")

    allowed_numbers = {str(number) for number in bundle["numbers"]}
    for number in NUMBER.findall(stripped):
        normal = str(int(number)) if number.isdigit() else number
        if number not in allowed_numbers and normal not in allowed_numbers:
            errors.append(f"number {number}")

    allowed_names = set(bundle["names"])
    for name in squad:
        parts = name.split(" ", 1)
        surname = parts[1] if len(parts) == 2 else name
        mentioned = name in line or re.search(rf"\b{re.escape(surname)}\b", line)
        allowed = name in allowed_names or surname in allowed_names
        if mentioned and not allowed:
            errors.append(f"name {name}")
    return errors
