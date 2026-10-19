"""Template lines. Digits and names stay inside the verifier's bundle."""

from __future__ import annotations

from verify import verify_line

HOME = "Arsesnail"
AWAY = "Mancheater City"
STYLES = ["classic", "american", "tactical", "homefan", "poetic"]
LANGS = ["en", "es", "pt"]
BIASES = ["neutral", "arsesnail", "city"]

MOMENTS = [
    {
        "id": "open",
        "t": 0,
        "who": {"en": "ANALYST", "es": "ANALISTA", "pt": "ANALISTA"},
        "tag": {
            "en": "87:00 · OPENING",
            "es": "87:00 · APERTURA",
            "pt": "87:00 · ABERTURA",
        },
        "clocks": ["87:00"],
        "scores": ["4-1"],
        "names": [HOME, AWAY],
        "numbers": ["87:00", "4", "1", "1.15", "1.21", "23", "12"],
    },
    {
        "id": "hampstead",
        "t": 5,
        "who": {"en": "PLAY-BY-PLAY", "es": "RELATO", "pt": "NARRACAO"},
        "tag": {
            "en": "87:05 · GOAL · HAMPSTEAD · xG 0.43",
            "es": "87:05 · GOL · HAMPSTEAD · xG 0.43",
            "pt": "87:05 · GOL · HAMPSTEAD · xG 0.43",
        },
        "clocks": ["87:05"],
        "scores": ["5-1"],
        "names": ["Robert Hampstead", HOME, AWAY],
        "numbers": ["87:05", "5", "1", "0.43", "1.58", "24"],
    },
    {
        "id": "push",
        "t": 65,
        "who": {"en": "ANALYST", "es": "ANALISTA", "pt": "ANALISTA"},
        "tag": {
            "en": "88:05 · MANCHEATER CITY · 4 SHOTS",
            "es": "88:05 · MANCHEATER CITY · 4 REMATES",
            "pt": "88:05 · MANCHEATER CITY · 4 CHUTES",
        },
        "clocks": ["88:05"],
        "scores": ["5-1"],
        "names": [HOME, AWAY],
        "numbers": ["88:05", "5", "1", "4"],
    },
    {
        "id": "rochdale",
        "t": 268,
        "who": {"en": "PLAY-BY-PLAY", "es": "RELATO", "pt": "NARRACAO"},
        "tag": {
            "en": "91:28 · GOAL · ROCHDALE · xG 0.30",
            "es": "91:28 · GOL · ROCHDALE · xG 0.30",
            "pt": "91:28 · GOL · ROCHDALE · xG 0.30",
        },
        "clocks": ["91:28"],
        "scores": ["5-2"],
        "names": ["David Rochdale", HOME, AWAY],
        "numbers": ["91:28", "5", "2", "0.30"],
    },
    {
        "id": "dickenson",
        "t": 270,
        "who": {"en": "PLAY-BY-PLAY", "es": "RELATO", "pt": "NARRACAO"},
        "tag": {
            "en": "91:30 · GOAL · DICKENSON · xG 0.51",
            "es": "91:30 · GOL · DICKENSON · xG 0.51",
            "pt": "91:30 · GOL · DICKENSON · xG 0.51",
        },
        "clocks": ["91:30"],
        "scores": ["5-3"],
        "names": ["James Dickenson", "David Rochdale", HOME, AWAY],
        "numbers": ["91:30", "5", "3", "0.51", "2.34", "18"],
    },
    {
        "id": "recap",
        "t": 300,
        "who": {"en": "ANALYST", "es": "ANALISTA", "pt": "ANALISTA"},
        "tag": {
            "en": "92:00 · RECAP",
            "es": "92:00 · RESUMEN",
            "pt": "92:00 · RESUMO",
        },
        "clocks": ["92:00"],
        "scores": ["5-3"],
        "names": [HOME, AWAY],
        "numbers": ["92:00", "5", "3", "2.34", "18", "1.60", "25"],
    },
]


def _bundle(moment: dict) -> dict:
    return {
        "clocks": moment["clocks"],
        "scores": moment["scores"],
        "names": moment["names"],
        "numbers": moment["numbers"],
    }


def _pair(moment_id: str, style: str, lang: str, bias: str) -> tuple[str, str]:
    home, away = HOME, AWAY
    if moment_id == "open":
        score = f"{home} 4–1 {away}"
        call = {
            "en": f"87:00. {score}. The score is comfortable. The chances are not.",
            "es": f"87:00. {score}. El marcador es comodo. Las ocasiones, no.",
            "pt": f"87:00. {score}. O placar e folgado. As chances, nao.",
        }[lang]
        analyst = {
            "en": f"{home} 1.15 expected goals from 23 shots. {away} 1.21 from 12.",
            "es": f"{home} 1.15 goles esperados en 23 remates. {away} 1.21 en 12.",
            "pt": f"{home} 1.15 gols esperados em 23 chutes. {away} 1.21 em 12.",
        }[lang]
        if style == "homefan" and bias == "arsesnail":
            call = f"87:00. {score}. " + {"en": "Keep it tight.", "es": "Hay que cerrarlo.", "pt": "E segurar."}[lang]
        elif style == "homefan" and bias == "city":
            call = f"87:00. {score}. " + {"en": "The chances say this stays open.", "es": "Las ocasiones dicen que sigue abierto.", "pt": "As chances dizem que segue aberto."}[lang]
        elif style == "american":
            call = f"87:00. {score}. " + {"en": "Under four minutes, and the chances disagree.", "es": "Menos de cuatro minutos, y las ocasiones no coinciden.", "pt": "Menos de quatro minutos, e as chances nao batem."}[lang]
        elif style == "tactical":
            call = f"87:00. {score}. " + {"en": "The scoreline is running ahead of the chances.", "es": "El marcador va por delante de las ocasiones.", "pt": "O placar vai na frente das chances."}[lang]
        elif style == "poetic":
            call = f"87:00. {score}. " + {"en": "The evening is not sure of itself.", "es": "La tarde aun no esta segura.", "pt": "A tarde ainda nao tem certeza."}[lang]
        return call, analyst

    if moment_id == "hampstead":
        base = {
            "en": f"87:05. Robert Hampstead scores. {home} 5–1 {away}.",
            "es": f"87:05. Robert Hampstead marca. {home} 5–1 {away}.",
            "pt": f"87:05. Robert Hampstead marca. {home} 5–1 {away}.",
        }[lang]
        analyst = {
            "en": f"A 0.43 chance from close range. {home} move to 1.58 expected goals, 24 shots.",
            "es": f"Una ocasion de 0.43 desde muy cerca. {home} llega a 1.58 goles esperados, 24 remates.",
            "pt": f"Uma chance de 0.43 de muito perto. {home} vai a 1.58 gols esperados, 24 chutes.",
        }[lang]
        if style == "homefan" and bias == "arsesnail":
            base += {"en": " That one is in.", "es": " Esa entro.", "pt": " Essa entrou."}[lang]
        elif style == "tactical":
            base = {
                "en": f"87:05. Robert Hampstead finishes a 0.43 chance from close range. {home} 5–1 {away}.",
                "es": f"87:05. Robert Hampstead define una ocasion de 0.43 desde muy cerca. {home} 5–1 {away}.",
                "pt": f"87:05. Robert Hampstead conclui uma chance de 0.43 de muito perto. {home} 5–1 {away}.",
            }[lang]
        elif style == "poetic":
            base = {
                "en": f"87:05. Robert Hampstead scores, close range. {home} 5–1 {away}.",
                "es": f"87:05. Robert Hampstead marca, muy cerca. {home} 5–1 {away}.",
                "pt": f"87:05. Robert Hampstead marca, muito perto. {home} 5–1 {away}.",
            }[lang]
        return base, analyst

    if moment_id == "push":
        call = {
            "en": f"88:05. {away} have 4 shots, and none has gone in. {home} 5–1 {away}.",
            "es": f"88:05. {away} lleva 4 remates, y ninguno entro. {home} 5–1 {away}.",
            "pt": f"88:05. {away} tem 4 chutes, e nenhum entrou. {home} 5–1 {away}.",
        }[lang]
        analyst = {
            "en": f"4 shots from {away} since 88:05. The score stays 5–1.",
            "es": f"4 remates de {away} desde 88:05. El marcador sigue 5–1.",
            "pt": f"4 chutes de {away} desde 88:05. O placar segue 5–1.",
        }[lang]
        if style == "homefan" and bias == "city":
            call = {
                "en": f"88:05. {away} keep coming. 4 shots. {home} 5–1 {away}.",
                "es": f"88:05. {away} sigue llegando. 4 remates. {home} 5–1 {away}.",
                "pt": f"88:05. {away} segue chegando. 4 chutes. {home} 5–1 {away}.",
            }[lang]
        elif style == "homefan" and bias == "arsesnail":
            call = {
                "en": f"88:05. {away} have 4 shots. Clear it. {home} 5–1 {away}.",
                "es": f"88:05. {away} lleva 4 remates. A despejar. {home} 5–1 {away}.",
                "pt": f"88:05. {away} tem 4 chutes. E afastar. {home} 5–1 {away}.",
            }[lang]
        return call, analyst

    if moment_id == "rochdale":
        call = {
            "en": f"91:28. David Rochdale scores. {home} 5–2 {away}.",
            "es": f"91:28. David Rochdale marca. {home} 5–2 {away}.",
            "pt": f"91:28. David Rochdale marca. {home} 5–2 {away}.",
        }[lang]
        analyst = {
            "en": "A 0.30 chance. The pressure finally tells.",
            "es": "Una ocasion de 0.30. La presion al fin pesa.",
            "pt": "Uma chance de 0.30. A pressao enfim pesa.",
        }[lang]
        if style == "tactical":
            call = {
                "en": f"91:28. David Rochdale converts a 0.30 chance. {home} 5–2 {away}.",
                "es": f"91:28. David Rochdale convierte una ocasion de 0.30. {home} 5–2 {away}.",
                "pt": f"91:28. David Rochdale converte uma chance de 0.30. {home} 5–2 {away}.",
            }[lang]
        return call, analyst

    if moment_id == "dickenson":
        call = {
            "en": f"91:30. James Dickenson scores. {home} 5–3 {away}.",
            "es": f"91:30. James Dickenson marca. {home} 5–3 {away}.",
            "pt": f"91:30. James Dickenson marca. {home} 5–3 {away}.",
        }[lang]
        analyst = {
            "en": f"A 0.51 chance, two seconds after David Rochdale. {away} finish on 2.34 expected goals from 18 shots.",
            "es": f"Una ocasion de 0.51, dos segundos despues de David Rochdale. {away} cierra con 2.34 goles esperados en 18 remates.",
            "pt": f"Uma chance de 0.51, dois segundos depois de David Rochdale. {away} fecha com 2.34 gols esperados em 18 chutes.",
        }[lang]
        if style == "homefan" and bias == "arsesnail":
            call += {"en": " Still 5–3.", "es": " Sigue 5–3.", "pt": " Segue 5–3."}[lang]
        return call, analyst

    call = {
        "en": f"92:00. {home} 5–3 {away}. {home} 1.60 expected goals from 25 shots. {away} 2.34 from 18.",
        "es": f"92:00. {home} 5–3 {away}. {home} 1.60 goles esperados en 25 remates. {away} 2.34 en 18.",
        "pt": f"92:00. {home} 5–3 {away}. {home} 1.60 gols esperados em 25 chutes. {away} 2.34 em 18.",
    }[lang]
    analyst = {
        "en": f"No further shots. {away} made more of the chances: 2.34 to 1.60.",
        "es": f"No hay mas remates. {away} tuvo mas ocasiones: 2.34 contra 1.60.",
        "pt": f"Nao ha mais chutes. {away} criou mais: 2.34 a 1.60.",
    }[lang]
    return call, analyst


def build_templates(squad: list[str]) -> dict:
    moments = []
    for moment in MOMENTS:
        bundle = _bundle(moment)
        lines: dict = {}
        for style in STYLES:
            lines[style] = {}
            for lang in LANGS:
                lines[style][lang] = {}
                for bias in BIASES:
                    call, analyst = _pair(moment["id"], style, lang, bias)
                    rewrite = _pair(moment["id"], "tactical" if style != "tactical" else "classic", lang, bias)[0]
                    for text in (call, analyst, rewrite):
                        errors = verify_line(text, bundle, squad)
                        if errors:
                            raise RuntimeError(f"{moment['id']} {style} {lang} {bias}: {errors} :: {text}")
                    lines[style][lang][bias] = {"call": call, "analyst": analyst, "rewrite": rewrite}
        moments.append(
            {
                "id": moment["id"],
                "t": moment["t"],
                "who": moment["who"],
                "tag": moment["tag"],
                "lines": lines,
            }
        )
    return {"moments": moments}
