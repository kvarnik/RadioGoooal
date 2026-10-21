"""Rewrite API. The cached demo does not need this process to be awake."""

from __future__ import annotations

import json
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from api.vault import load_key_vault
from workflow import load_agents, rewrite_call, squad_names

CACHE_PATH = Path(__file__).resolve().parents[1] / "data" / "audio" / "cache.json"


@asynccontextmanager
async def lifespan(_app: FastAPI):
    load_key_vault()
    yield


app = FastAPI(title="RadioGoooal", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

SQUAD = squad_names()


class RewriteRequest(BaseModel):
    sec: int = Field(ge=0, le=300)
    style: str
    lang: str
    bias: str


def cache_summary() -> dict:
    if not CACHE_PATH.exists():
        return {"version": None, "speech": "missing", "lines": 0, "characters": 0, "pass_rate": None}
    data = json.loads(CACHE_PATH.read_text(encoding="utf-8"))
    return {
        "version": data["version"],
        "speech": data["speech"],
        "lines": data["lines"],
        "characters": data["characters"],
        "pass_rate": data["pass_rate"],
    }


@app.get("/healthz")
@app.get("/api/healthz")
def healthz() -> dict:
    safety_key = os.environ.get("CONTENT_SAFETY_KEY") and os.environ.get("CONTENT_SAFETY_ENDPOINT")
    safety = "azure" if safety_key else "local-word-list"
    speech_key = os.environ.get("SPEECH_KEY") and os.environ.get("SPEECH_REGION")
    speech = "azure" if speech_key else "unconfigured"
    return {
        "cache": cache_summary(),
        "agents": [agent["name"] for agent in load_agents()],
        "foundry": "unconfigured",
        "speech": speech,
        "content_safety": safety,
    }


@app.post("/rewrite")
@app.post("/api/rewrite")
def rewrite(body: RewriteRequest) -> dict:
    try:
        return rewrite_call(body.sec, body.style, body.lang, body.bias, SQUAD)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
