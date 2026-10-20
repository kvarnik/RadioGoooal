import pytest

from safety import screen_line
from speech import (
    CHAR_LIMIT,
    build_speech_cache,
    choose_voices,
    enforce_budget,
    speakable,
    ssml,
    variants,
)
from workflow import squad_names


def test_seven_variants_cover_home_fan_biases_once_each():
    assert variants() == [
        ("classic", "neutral"),
        ("american", "neutral"),
        ("tactical", "neutral"),
        ("poetic", "neutral"),
        ("homefan", "neutral"),
        ("homefan", "arsesnail"),
        ("homefan", "city"),
    ]


def test_ssml_speaks_the_clock_as_digits():
    marked = speakable("87:05. Robert Hampstead scores.")
    assert '<say-as interpret-as="number_digit">87</say-as>' in marked
    assert '<say-as interpret-as="number_digit">05</say-as>' in marked
    assert "Robert Hampstead" in marked


def test_blocklist_is_whole_words():
    assert screen_line("The odds have shifted.")["term"] == "odds"
    assert screen_line("That looks nailed on from here.")["verdict"] == "blocked"
    assert screen_line("He plays between the posts.")["verdict"] == "pass"


def test_budget_stops_before_speech_is_asked():
    enforce_budget(CHAR_LIMIT)
    with pytest.raises(RuntimeError):
        enforce_budget(CHAR_LIMIT + 1)


def test_voice_pair_comes_from_the_catalog():
    catalog = []
    for locale, male, female in (
        ("en-US", "en-US-AndrewNeural", "en-US-JennyNeural"),
        ("es-ES", "es-ES-AlvaroNeural", "es-ES-ElviraNeural"),
        ("pt-BR", "pt-BR-AntonioNeural", "pt-BR-FranciscaNeural"),
    ):
        catalog.append(
            {
                "Locale": locale,
                "VoiceType": "Neural",
                "Gender": "Male",
                "ShortName": male + "Multilingual",
            }
        )
        catalog.append({"Locale": locale, "VoiceType": "Neural", "Gender": "Male", "ShortName": male})
        catalog.append({"Locale": locale, "VoiceType": "Neural", "Gender": "Female", "ShortName": female})
    chosen = choose_voices(catalog)
    assert chosen["en"]["call"] == "en-US-AndrewNeural"
    assert chosen["pt"]["analyst"] == "pt-BR-FranciscaNeural"


def test_cache_is_252_lines_and_does_not_call_speech(tmp_path):
    cache = build_speech_cache(squad_names(), tmp_path)
    assert cache["lines"] == 252
    assert cache["speech"] == "unconfigured"
    assert cache["pass_rate"] == 1
    assert cache["characters"] < CHAR_LIMIT
    assert all(entry["file"] is None for entry in cache["entries"])
    assert all(entry["verdict"]["safety"] == "pass" for entry in cache["entries"])
    assert "No short name has been chosen." in (tmp_path / "VOICES.md").read_text(encoding="utf-8")
    sample = ssml(cache["entries"][0]["text"], "en", "pending-voice-name")
    assert sample.startswith("<speak ")
