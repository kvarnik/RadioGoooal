"""Template lines. Digits and names stay inside the verifier's bundle."""

from __future__ import annotations

from verify import verify_line

HOME = "Arsesnail"
AWAY = "Mancheater City"
SAY_HOME = "Arse Snail"
SAY_AWAY = "Man Cheater City"
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
        "numbers": ["87:00", "87", "4", "1", "1.15", "1.21", "23", "12"],
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
        "numbers": ["87:05", "87", "5", "1", "0.43", "1.58", "24"],
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
        "numbers": ["88:05", "88", "5", "1", "4"],
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
        "numbers": ["91:28", "91", "5", "2", "0.30"],
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
        "numbers": ["91:30", "91", "5", "3", "0.51", "2.34", "18"],
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
        "numbers": ["92:00", "92", "5", "3", "2.34", "18", "1.60", "25"],
    },
]


def _bundle(moment: dict) -> dict:
    return {
        "clocks": moment["clocks"],
        "scores": moment["scores"],
        "names": moment["names"],
        "numbers": moment["numbers"],
    }


def _line(lang: str, text: dict[str, str]) -> str:
    return text[lang]


def _pair(moment_id: str, style: str, lang: str, bias: str) -> tuple[str, str]:
    home, away = SAY_HOME, SAY_AWAY
    if moment_id == "open":
        call = _line(lang, {
            "en": f"It's the 87th minute, and {home} lead {away} 4 to 1. Comfortable, if you can ignore the chances.",
            "es": f"Es el minuto 87, y {home} le gana 4 a 1 a {away}. Cómodo, si ignoras las ocasiones.",
            "pt": f"É o minuto 87, e {home} vence {away} por 4 a 1. Confortável, se você fingir que as chances não existem.",
        })
        analyst = _line(lang, {
            "en": f"{home} have 1.15 expected goals from 23 shots. {away} have 1.21 from 12. The scoreboard is doing charity work.",
            "es": f"{home} tiene 1.15 goles esperados en 23 remates. {away} tiene 1.21 en 12. El marcador está haciendo caridad.",
            "pt": f"{home} tem 1.15 gols esperados em 23 chutes. {away} tem 1.21 em 12. O placar está fazendo caridade.",
        })
        if style == "homefan" and bias == "arsesnail":
            call = _line(lang, {
                "en": f"It's the 87th minute. {home} 4, {away} 1. Sit on it. Let them keep the pretty chances.",
                "es": f"Es el minuto 87. {home} 4, {away} 1. Siéntate encima. Que se queden con las ocasiones bonitas.",
                "pt": f"É o minuto 87. {home} 4, {away} 1. Sentem em cima. Que fiquem com as chances bonitas.",
            })
        elif style == "homefan" and bias == "city":
            call = _line(lang, {
                "en": f"It's the 87th minute. {home} 4, {away} 1. Don't applaud that scoreboard. {away} have had the game.",
                "es": f"Es el minuto 87. {home} 4, {away} 1. No aplaudas ese marcador. El partido lo ha tenido {away}.",
                "pt": f"É o minuto 87. {home} 4, {away} 1. Não aplaude esse placar. Quem jogou foi {away}.",
            })
        elif style == "american":
            call = _line(lang, {
                "en": f"It's the 87th minute. {home} 4, {away} 1. The score is grinning. The chances are not in on the joke.",
                "es": f"Es el minuto 87. {home} 4, {away} 1. El marcador se ríe. Las ocasiones no entendieron el chiste.",
                "pt": f"É o minuto 87. {home} 4, {away} 1. O placar está rindo. As chances não entraram na piada.",
            })
        elif style == "tactical":
            call = _line(lang, {
                "en": f"It's the 87th minute. {home} 4, {away} 1. The scoreline is showing off. The chances refuse to clap.",
                "es": f"Es el minuto 87. {home} 4, {away} 1. El marcador se luce. Las ocasiones se niegan a aplaudir.",
                "pt": f"É o minuto 87. {home} 4, {away} 1. O placar se exibe. As chances se recusam a aplaudir.",
            })
        elif style == "poetic":
            call = _line(lang, {
                "en": f"It's the 87th minute. {home} 4, {away} 1. The evening is smirking at its own scoreboard.",
                "es": f"Es el minuto 87. {home} 4, {away} 1. La tarde se burla de su propio marcador.",
                "pt": f"É o minuto 87. {home} 4, {away} 1. A tarde zomba do próprio placar.",
            })
        return call, analyst

    if moment_id == "hampstead":
        base = _line(lang, {
            "en": f"It's the 87th minute. Robert Hampstead scores. {home} 5, {away} 1. Close range, and a little rude.",
            "es": f"Es el minuto 87. Robert Hampstead marca. {home} 5, {away} 1. Muy cerca, y un poco grosero.",
            "pt": f"É o minuto 87. Robert Hampstead marca. {home} 5, {away} 1. De muito perto, e um tanto grosseiro.",
        })
        analyst = _line(lang, {
            "en": f"A 0.43 chance from close range. {home} stroll to 1.58 expected goals and 24 shots.",
            "es": f"Una ocasión de 0.43 desde muy cerca. {home} llega a 1.58 goles esperados y 24 remates.",
            "pt": f"Uma chance de 0.43 de muito perto. {home} vai a 1.58 gols esperados e 24 chutes.",
        })
        if style == "homefan" and bias == "arsesnail":
            base = _line(lang, {
                "en": f"It's the 87th minute. Robert Hampstead scores. {home} 5, {away} 1. Frame that one. {away} can watch the replay.",
                "es": f"Es el minuto 87. Robert Hampstead marca. {home} 5, {away} 1. Enmárcalo. {away} puede ver la repetición.",
                "pt": f"É o minuto 87. Robert Hampstead marca. {home} 5, {away} 1. Emoldura essa. {away} pode ver o replay.",
            })
        elif style == "homefan" and bias == "city":
            base = _line(lang, {
                "en": f"It's the 87th minute. Robert Hampstead scores. {home} 5, {away} 1. Of course he does.",
                "es": f"Es el minuto 87. Robert Hampstead marca. {home} 5, {away} 1. Claro que sí.",
                "pt": f"É o minuto 87. Robert Hampstead marca. {home} 5, {away} 1. Claro que marca.",
            })
        elif style == "tactical":
            base = _line(lang, {
                "en": f"It's the 87th minute. Robert Hampstead finishes a 0.43 chance from close range. {home} 5, {away} 1.",
                "es": f"Es el minuto 87. Robert Hampstead define una ocasión de 0.43 desde muy cerca. {home} 5, {away} 1.",
                "pt": f"É o minuto 87. Robert Hampstead conclui uma chance de 0.43 de muito perto. {home} 5, {away} 1.",
            })
        elif style == "poetic":
            base = _line(lang, {
                "en": f"It's the 87th minute. Robert Hampstead scores from close range. {home} 5, {away} 1. A small cruelty, neatly done.",
                "es": f"Es el minuto 87. Robert Hampstead marca desde muy cerca. {home} 5, {away} 1. Una crueldad pequeña, bien hecha.",
                "pt": f"É o minuto 87. Robert Hampstead marca de muito perto. {home} 5, {away} 1. Uma crueldade pequena, bem feita.",
            })
        return base, analyst

    if moment_id == "push":
        call = _line(lang, {
            "en": f"It's the 88th minute. {away} have had 4 shots, and none of them remembered to go in. {home} 5, {away} 1.",
            "es": f"Es el minuto 88. {away} lleva 4 remates, y ninguno se acordó de entrar. {home} 5, {away} 1.",
            "pt": f"É o minuto 88. {away} teve 4 chutes, e nenhum lembrou de entrar. {home} 5, {away} 1.",
        })
        analyst = _line(lang, {
            "en": f"4 shots from {away}. The score stays 5 to 1. Plenty of effort. No punchline.",
            "es": f"4 remates de {away}. El marcador sigue 5 a 1. Mucho esfuerzo. Ningún remate.",
            "pt": f"4 chutes de {away}. O placar segue 5 a 1. Muito esforço. Nenhuma piada final.",
        })
        if style == "homefan" and bias == "city":
            call = _line(lang, {
                "en": f"It's the 88th minute. {away} keep coming. 4 shots. {home} 5, {away} 1. The score is a rumor. The chances are the match.",
                "es": f"Es el minuto 88. {away} sigue llegando. 4 remates. {home} 5, {away} 1. El marcador es un rumor. Las ocasiones son el partido.",
                "pt": f"É o minuto 88. {away} continua chegando. 4 chutes. {home} 5, {away} 1. O placar é um boato. As chances são o jogo.",
            })
        elif style == "homefan" and bias == "arsesnail":
            call = _line(lang, {
                "en": f"It's the 88th minute. {away} have 4 shots. Clear it, and try not to laugh. {home} 5, {away} 1.",
                "es": f"Es el minuto 88. {away} lleva 4 remates. Despeja, y procura no reírte. {home} 5, {away} 1.",
                "pt": f"É o minuto 88. {away} tem 4 chutes. Afasta, e tenta não rir. {home} 5, {away} 1.",
            })
        return call, analyst

    if moment_id == "rochdale":
        call = _line(lang, {
            "en": f"It's the 91st minute. David Rochdale scores. {home} 5, {away} 2. They found the net. Only a few minutes late.",
            "es": f"Es el minuto 91. David Rochdale marca. {home} 5, {away} 2. Encontraron la red. Solo unos minutos tarde.",
            "pt": f"É o minuto 91. David Rochdale marca. {home} 5, {away} 2. Acharam a rede. Só uns minutos atrasados.",
        })
        analyst = _line(lang, {
            "en": "A 0.30 chance. The pressure finally did something useful.",
            "es": "Una ocasión de 0.30. La presión por fin sirvió para algo.",
            "pt": "Uma chance de 0.30. A pressão finalmente serviu para alguma coisa.",
        })
        if style == "homefan" and bias == "city":
            call = _line(lang, {
                "en": f"It's the 91st minute. David Rochdale scores. {home} 5, {away} 2. About time. {away} have been the better side and the score knew it.",
                "es": f"Es el minuto 91. David Rochdale marca. {home} 5, {away} 2. Ya era hora. {away} fue mejor, y el marcador lo sabía.",
                "pt": f"É o minuto 91. David Rochdale marca. {home} 5, {away} 2. Já era hora. {away} foi melhor, e o placar sabia.",
            })
        elif style == "tactical":
            call = _line(lang, {
                "en": f"It's the 91st minute. David Rochdale converts a 0.30 chance. {home} 5, {away} 2.",
                "es": f"Es el minuto 91. David Rochdale convierte una ocasión de 0.30. {home} 5, {away} 2.",
                "pt": f"É o minuto 91. David Rochdale converte uma chance de 0.30. {home} 5, {away} 2.",
            })
        elif style == "poetic":
            call = _line(lang, {
                "en": f"It's the 91st minute. David Rochdale scores. {home} 5, {away} 2. A late apology from the goal.",
                "es": f"Es el minuto 91. David Rochdale marca. {home} 5, {away} 2. Una disculpa tardía del arco.",
                "pt": f"É o minuto 91. David Rochdale marca. {home} 5, {away} 2. Um pedido de desculpas atrasado do gol.",
            })
        return call, analyst

    if moment_id == "dickenson":
        call = _line(lang, {
            "en": f"It's the 91st minute. James Dickenson scores. {home} 5, {away} 3. Two bites, back to back.",
            "es": f"Es el minuto 91. James Dickenson marca. {home} 5, {away} 3. Dos mordiscos, uno detrás del otro.",
            "pt": f"É o minuto 91. James Dickenson marca. {home} 5, {away} 3. Duas mordidas, uma atrás da outra.",
        })
        analyst = _line(lang, {
            "en": f"A 0.51 chance, right after David Rochdale. {away} finish on 2.34 expected goals from 18 shots. Lively. Still not enough.",
            "es": f"Una ocasión de 0.51, justo después de David Rochdale. {away} cierra con 2.34 goles esperados en 18 remates. Animado. Y no alcanza.",
            "pt": f"Uma chance de 0.51, logo depois de David Rochdale. {away} fecha com 2.34 gols esperados em 18 chutes. Animado. E não chega.",
        })
        if style == "homefan" and bias == "arsesnail":
            call = _line(lang, {
                "en": f"It's the 91st minute. James Dickenson scores. {home} 5, {away} 3. How generous. Still 5 to 3.",
                "es": f"Es el minuto 91. James Dickenson marca. {home} 5, {away} 3. Qué generoso. Sigue 5 a 3.",
                "pt": f"É o minuto 91. James Dickenson marca. {home} 5, {away} 3. Que generoso. Continua 5 a 3.",
            })
        elif style == "homefan" and bias == "city":
            call = _line(lang, {
                "en": f"It's the 91st minute. James Dickenson scores. {home} 5, {away} 3. That's the real team, arriving late and still sharper.",
                "es": f"Es el minuto 91. James Dickenson marca. {home} 5, {away} 3. Ese es el equipo de verdad, tarde y todavía más fino.",
                "pt": f"É o minuto 91. James Dickenson marca. {home} 5, {away} 3. Esse é o time de verdade, atrasado e ainda mais afiado.",
            })
        return call, analyst

    call = _line(lang, {
        "en": f"It's the 92nd minute. {home} 5, {away} 3. {home}, 1.60 expected goals from 25 shots. {away}, 2.34 from 18.",
        "es": f"Es el minuto 92. {home} 5, {away} 3. {home}, 1.60 goles esperados en 25 remates. {away}, 2.34 en 18.",
        "pt": f"É o minuto 92. {home} 5, {away} 3. {home}, 1.60 gols esperados em 25 chutes. {away}, 2.34 em 18.",
    })
    analyst = _line(lang, {
        "en": f"No further shots. {away} made more of the chances, 2.34 to 1.60, and still walk off behind. The scoreboard doesn't do sarcasm. I do.",
        "es": f"No hay más remates. {away} creó más, 2.34 contra 1.60, y se va por detrás. El marcador no sabe de sarcasmo. Yo sí.",
        "pt": f"Não há mais chutes. {away} criou mais, 2.34 a 1.60, e sai atrás. O placar não sabe sarcasmo. Eu sei.",
    })
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
