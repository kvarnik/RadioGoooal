"""Build the 252-line speech cache. Speech is called only when a key is set."""

from __future__ import annotations

import hashlib
import json
import os
import re
import urllib.request
from pathlib import Path

from safety import screen_line
from templates import LANGS, MOMENTS, _bundle, _pair
from verify import verify_line

CHAR_LIMIT = 100_000
PLACEHOLDER_VOICE = "pending-voice-name"
LOCALES = {"en": "en-US", "es": "es-ES", "pt": "pt-BR"}
TOKEN = re.compile(r"\d{1,2}:\d{2}|\d+(?:\.\d+)?")


def variants() -> list[tuple[str, str]]:
    """Four styles once, and home-fan three times. That is the seven variants."""
    chosen = [(style, "neutral") for style in ("classic", "american", "tactical", "poetic")]
    chosen.extend(("homefan", bias) for bias in ("neutral", "arsesnail", "city"))
    return chosen


def speakable(text: str) -> str:
    escaped = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    def wrap(match: re.Match[str]) -> str:
        token = match.group(0)
        if ":" in token:
            minute, second = token.split(":")
            return (
                f'<say-as interpret-as="number_digit">{minute}</say-as>'
                ":"
                f'<say-as interpret-as="number_digit">{second}</say-as>'
            )
        kind = "cardinal" if "." in token else "number_digit"
        return f'<say-as interpret-as="{kind}">{token}</say-as>'

    return TOKEN.sub(wrap, escaped)


def ssml(text: str, lang: str, voice: str) -> str:
    locale = LOCALES[lang]
    return (
        f'<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="{locale}">'
        f'<voice name="{voice}">{speakable(text)}</voice></speak>'
    )


def enforce_budget(characters: int) -> None:
    if characters > CHAR_LIMIT:
        raise RuntimeError(f"speech cache asks for {characters} characters, above {CHAR_LIMIT}")


def _short_voice(names: list[str]) -> str:
    plain = [name for name in names if "Multilingual" not in name and "Dragon" not in name]
    return min(plain or names, key=len)


def choose_voices(catalog: list[dict]) -> dict[str, dict[str, str]]:
    chosen: dict[str, dict[str, str]] = {}
    for lang, locale in LOCALES.items():
        neural = [
            voice
            for voice in catalog
            if voice.get("Locale") == locale and voice.get("VoiceType") == "Neural"
        ]
        male = [voice["ShortName"] for voice in neural if voice.get("Gender") == "Male"]
        female = [voice["ShortName"] for voice in neural if voice.get("Gender") == "Female"]
        if not male or not female:
            raise RuntimeError(f"{locale} has no neural pair")
        chosen[lang] = {"call": _short_voice(male), "analyst": _short_voice(female)}
    return chosen


def _configured() -> tuple[str, str] | None:
    region = os.environ.get("SPEECH_REGION", "").strip()
    key = os.environ.get("SPEECH_KEY", "").strip()
    if not region and not key:
        return None
    if not region or not key:
        raise RuntimeError("SPEECH_KEY and SPEECH_REGION must both be set")
    if not re.fullmatch(r"[A-Za-z0-9]+", region):
        raise RuntimeError("SPEECH_REGION is not a region name")
    return region, key


def list_voices(region: str, key: str) -> list[dict]:
    url = f"https://{region}.tts.speech.microsoft.com/cognitiveservices/voices/list"
    request = urllib.request.Request(url, headers={"Ocp-Apim-Subscription-Key": key})
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def synthesize(document: str, region: str, key: str, dest: Path) -> None:
    url = f"https://{region}.tts.speech.microsoft.com/cognitiveservices/v1"
    request = urllib.request.Request(
        url,
        data=document.encode("utf-8"),
        method="POST",
        headers={
            "Ocp-Apim-Subscription-Key": key,
            "Content-Type": "application/ssml+xml",
            "X-Microsoft-OutputFormat": "riff-24khz-16bit-mono-pcm",
            "User-Agent": "RadioGoooal",
        },
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        dest.write_bytes(response.read())


def _fallback(moment_id: str, lang: str, role: str) -> str:
    call, analyst = _pair(moment_id, "classic", lang, "neutral")
    return call if role == "call" else analyst


def _accept(text: str, moment: dict, squad: list[str], role: str, lang: str) -> tuple[str, dict]:
    errors = verify_line(text, _bundle(moment), squad)
    verdict = {"verifier": "pass", "attempt": 1}
    if errors:
        text = _fallback(moment["id"], lang, role)
        errors = verify_line(text, _bundle(moment), squad)
        verdict = {"verifier": "template", "attempt": 2, "errors": errors}
        if errors:
            raise RuntimeError(f"{moment['id']} {role} template failed: {errors}")
    screened = screen_line(text)
    if screened["verdict"] == "blocked":
        replacement = _fallback(moment["id"], lang, role)
        if screen_line(replacement)["verdict"] == "blocked":
            raise RuntimeError(f"{moment['id']} {role} template blocked on {screened['term']}")
        text = replacement
        verdict["safety"] = "template"
        verdict["safety_term"] = screened["term"]
    else:
        verdict["safety"] = "pass"
        verdict["safety_source"] = screened["source"]
    return text, verdict


def build_speech_cache(squad: list[str], dest: Path) -> dict:
    entries = []
    spoken = 0
    for moment in MOMENTS:
        for style, bias in variants():
            for lang in LANGS:
                call, analyst = _pair(moment["id"], style, lang, bias)
                for role, raw in (("call", call), ("analyst", analyst)):
                    text, verdict = _accept(raw, moment, squad, role, lang)
                    spoken += len(text)
                    entries.append(
                        {
                            "id": f"{moment['id']}/{style}/{lang}/{bias}/{role}",
                            "moment": moment["id"],
                            "t": moment["t"],
                            "style": style,
                            "lang": lang,
                            "bias": bias,
                            "role": role,
                            "text": text,
                            "verdict": verdict,
                            "file": None,
                        }
                    )

    documents = [ssml(entry["text"], entry["lang"], PLACEHOLDER_VOICE) for entry in entries]
    characters = sum(len(document) for document in documents)
    enforce_budget(characters)
    version = hashlib.sha256("\n".join(entry["text"] for entry in entries).encode()).hexdigest()[:12]
    passed = sum(1 for entry in entries if entry["verdict"]["attempt"] == 1 and entry["verdict"]["safety"] == "pass")
    cache = {
        "version": version,
        "speech": "unconfigured",
        "lines": len(entries),
        "characters": characters,
        "spoken_characters": spoken,
        "limit": CHAR_LIMIT,
        "pass_rate": round(passed / len(entries), 4),
        "entries": entries,
    }

    dest.mkdir(parents=True, exist_ok=True)
    voices = None
    config = _configured()
    if config:
        region, key = config
        voices = choose_voices(list_voices(region, key))
        real = [
            ssml(entry["text"], entry["lang"], voices[entry["lang"]][entry["role"]])
            for entry in entries
        ]
        enforce_budget(sum(len(document) for document in real))
        clip_dir = dest / "clips"
        clip_dir.mkdir(parents=True, exist_ok=True)
        for entry, document in zip(entries, real, strict=True):
            name = entry["id"].replace("/", "-") + ".wav"
            synthesize(document, region, key, clip_dir / name)
            entry["file"] = f"clips/{name}"
        cache["speech"] = "azure"
        cache["characters"] = sum(len(document) for document in real)
        cache["voices"] = voices

    (dest / "cache.json").write_text(
        json.dumps(cache, ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    _write_voices(dest / "VOICES.md", voices, cache["characters"])
    return cache


def _write_voices(path: Path, voices: dict | None, characters: int) -> None:
    if not voices:
        path.write_text(
            "# Voices\n\n"
            "Speech is not configured. No short name has been chosen.\n\n"
            "Set `SPEECH_KEY` and `SPEECH_REGION`, then run `python tools/build_cache.py` "
            "from `broadcast/`. The build reads the neural voices on that resource and "
            "writes the six short names here.\n\n"
            f"The script cache is {characters} characters of SSML, under the 100,000 character stop. "
            "That count uses the placeholder voice name `pending-voice-name`.\n",
            encoding="utf-8",
        )
        return
    lines = ["# Voices\n", "Chosen from the neural voices on the Speech resource.\n"]
    for lang, pair in voices.items():
        lines.append(f"- {lang} play-by-play: `{pair['call']}`")
        lines.append(f"- {lang} analyst: `{pair['analyst']}`")
    lines.append(f"\nThe cache asked Speech for {characters} characters.\n")
    path.write_text("\n".join(lines), encoding="utf-8")
