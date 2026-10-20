"""Screen a line before it is cached or spoken.

The local list is the custom blocklist: whole words only. Azure Content Safety
runs as well when CONTENT_SAFETY_ENDPOINT and CONTENT_SAFETY_KEY are set.
"""

from __future__ import annotations

import json
import os
import re
import urllib.request

BLOCK = re.compile(r"\b(odds|bet|accumulator|nailed on)\b", re.IGNORECASE)
SEVERITY_LIMIT = 2


def screen_line(line: str) -> dict:
    match = BLOCK.search(line)
    if match:
        return {"verdict": "blocked", "term": match.group(0).lower(), "source": "local-word-list"}
    endpoint = os.environ.get("CONTENT_SAFETY_ENDPOINT", "").strip().rstrip("/")
    key = os.environ.get("CONTENT_SAFETY_KEY", "").strip()
    if not endpoint or not key:
        return {"verdict": "pass", "source": "local-word-list"}
    return _azure(line, endpoint, key)


def _azure(line: str, endpoint: str, key: str) -> dict:
    if not endpoint.startswith("https://"):
        raise RuntimeError("CONTENT_SAFETY_ENDPOINT must be an https URL")
    url = f"{endpoint}/contentsafety/text:analyze?api-version=2024-09-01"
    body = json.dumps(
        {
            "text": line,
            "categories": ["Hate", "SelfHarm", "Sexual", "Violence"],
            "outputType": "FourSeverityLevels",
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={"Ocp-Apim-Subscription-Key": key, "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        payload = json.loads(response.read().decode("utf-8"))
    for category in payload.get("categoriesAnalysis", []):
        if int(category.get("severity", 0)) >= SEVERITY_LIMIT:
            return {"verdict": "blocked", "term": category["category"], "source": "azure"}
    return {"verdict": "pass", "source": "azure"}
