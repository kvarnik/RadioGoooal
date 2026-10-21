import json

from fastapi.testclient import TestClient

from api.app import CACHE_PATH, app
from api.vault import load_key_vault
from workflow import load_agents

client = TestClient(app)


def test_health_names_the_five_agents(monkeypatch):
    monkeypatch.delenv("SPEECH_KEY", raising=False)
    monkeypatch.delenv("SPEECH_REGION", raising=False)
    response = client.get("/healthz")
    assert response.status_code == 200
    body = response.json()
    assert body["foundry"] == "unconfigured"
    assert body["speech"] == "unconfigured"
    assert body["content_safety"] == "local-word-list"
    cache = json.loads(CACHE_PATH.read_text(encoding="utf-8"))
    assert body["cache"]["speech"] == cache["speech"]
    assert body["cache"]["lines"] == 252
    assert body["cache"]["pass_rate"] == 1
    assert body["agents"] == ["interpreter", "moment_editor", "analyst", "play_by_play", "verifier"]
    assert len(load_agents()) == 5


def test_rewrite_stays_inside_the_window_and_passes_the_verifier():
    response = client.post("/rewrite", json={"sec": 5, "style": "classic", "lang": "en", "bias": "neutral"})
    assert response.status_code == 200
    body = response.json()
    assert body["moment"] == "hampstead"
    assert body["verdict"] == "pass"
    assert "Robert Hampstead" in body["line"]
    assert "Arsenal" not in body["line"]
    assert [step["agent"] for step in body["steps"]][:4] == [
        "interpreter",
        "moment_editor",
        "play_by_play",
        "analyst",
    ]


def test_key_vault_stays_quiet_without_a_uri(monkeypatch):
    monkeypatch.delenv("KEY_VAULT_URI", raising=False)
    load_key_vault()


def test_linked_backend_routes_match_the_local_ones():
    direct = client.post("/rewrite", json={"sec": 5, "style": "classic", "lang": "en", "bias": "neutral"})
    linked = client.post("/api/rewrite", json={"sec": 5, "style": "classic", "lang": "en", "bias": "neutral"})
    assert direct.status_code == 200
    assert linked.json()["line"] == direct.json()["line"]
    assert client.get("/api/healthz").status_code == 200


def test_rewrite_rejects_a_clock_outside_the_window():
    response = client.post("/rewrite", json={"sec": 301, "style": "classic", "lang": "en", "bias": "neutral"})
    assert response.status_code == 422
