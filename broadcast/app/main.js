import { setFader, startVoices, stopVoices } from "./audio.js";

const HOME = "1";
const AWAY = "36";
const STYLES = [
  { id: "classic", short: "Classic", angle: 162, voice: "Two-voice booth, measured" },
  { id: "american", short: "American", angle: 126, voice: "Fast play-by-play, colour analyst" },
  { id: "tactical", short: "Tactical", angle: 90, voice: "Coach-style, unhurried" },
  { id: "homefan", short: "Home fan", angle: 54, voice: "" },
  { id: "poetic", short: "Poetic", angle: 18, voice: "Spare, slow" },
];
const FAN_VOICE = {
  neutral: "Partisan, neutral",
  arsesnail: "Partisan, Arsesnail end",
  city: "Partisan, Mancheater City end",
};
const FADERS = [
  { id: "home", label: "Home", group: "crowd", value: 72 },
  { id: "away", label: "Away", group: "crowd", value: 40 },
  { id: "chant", label: "Chant", group: "crowd", value: 58 },
  { id: "match", label: "Match", group: "broadcast", value: 80 },
  { id: "call", label: "Call", group: "broadcast", value: 92 },
  { id: "notes", label: "Notes", group: "broadcast", value: 60 },
];
const ANALYST = { en: "ANALYST", es: "ANALISTA", pt: "ANALISTA" };

const state = {
  sec: 0,
  playing: false,
  rate: 1,
  scan: 0,
  style: "classic",
  lang: "en",
  bias: "neutral",
  focus: null,
  rewritten: false,
  rewriteNote: "",
  ready: false,
};

let facts;
let templates;
let positions;
let speed;
let cache = null;
let acc = 0;
let resume = false;
let scanning = 0;
let downAt = 0;
let held = null;
let timer = 0;

const $ = (id) => document.getElementById(id);

function clockOf(sec) {
  const minute = 87 + Math.floor(sec / 60);
  return `${minute}:${String(sec % 60).padStart(2, "0")}`;
}

function xg(value) {
  return Number(value).toFixed(2);
}

function momentAt(sec) {
  let current = templates.moments[0];
  for (const moment of templates.moments) {
    if (moment.t <= sec) current = moment;
  }
  return current;
}

function clipFor(moment, role) {
  if (!cache || !moment) return null;
  const bias = state.style === "homefan" ? state.bias : "neutral";
  return cache.entries.find((entry) =>
    entry.moment === moment.id &&
    entry.style === state.style &&
    entry.lang === state.lang &&
    entry.bias === bias &&
    entry.role === role
  );
}

function speakMoment(moment) {
  if (!moment || state.rewritten || state.scan) return;
  startVoices(clipFor(moment, "call"), clipFor(moment, "analyst"));
}

function seek(next) {
  const previous = state.sec;
  acc = 0;
  state.sec = Math.max(0, Math.min(300, Math.round(Number(next))));
  state.rewritten = false;
  state.rewriteNote = "";
  stopVoices();
  if (state.sec !== previous) speakMoment(templates?.moments.find((item) => item.t === state.sec));
  render();
}

function scanStart(dir) {
  downAt = performance.now();
  held = null;
  resume = state.playing;
  scanning = dir;
  acc = 0;
  state.playing = true;
  state.rate = dir * 6;
  state.scan = dir;
  render();
}

function scanEnd() {
  if (!scanning) return;
  held = performance.now() - downAt;
  scanning = 0;
  acc = 0;
  state.playing = resume;
  state.rate = 1;
  state.scan = 0;
  render();
}

function skip(dir) {
  const elapsed = held;
  held = null;
  if (elapsed !== null && elapsed > 250) return;
  seek(state.sec + dir * 5);
}

function play() {
  if (state.sec >= 300) {
    state.sec = 0;
    state.rewritten = false;
    state.rewriteNote = "";
  }
  acc = 0;
  state.playing = true;
  state.rate = 1;
  state.scan = 0;
  speakMoment(templates?.moments.find((item) => item.t === state.sec));
  render();
}

function pause() {
  state.playing = false;
  state.rate = 1;
  state.scan = 0;
  stopVoices();
  render();
}

function tick() {
  if (!state.playing || !state.ready) return;
  acc += 0.1 * state.rate;
  let step = 0;
  while (acc >= 1) {
    acc -= 1;
    step += 1;
  }
  while (acc <= -1) {
    acc += 1;
    step -= 1;
  }
  if (!step) return;
  const previous = state.sec;
  const next = Math.max(0, Math.min(300, state.sec + step));
  const stop = (next === 300 && step > 0) || (next === 0 && step < 0);
  state.sec = next;
  if (step > 0 && !state.scan) {
    let crossed = null;
    for (const moment of templates.moments) {
      if (previous < moment.t && moment.t <= next) crossed = moment;
    }
    if (crossed) speakMoment(crossed);
  }
  state.rewritten = false;
  if (stop) {
    state.playing = false;
    state.rate = 1;
  }
  render();
}

function surname(name) {
  return name.split(" ").slice(-1)[0];
}

function renderPitch(sec) {
  const frame = positions.frames[sec];
  const previous = sec > 0 ? positions.frames[sec - 1] : null;
  const row = facts.rows[sec];
  const names = new Map(row.players.map((player) => [player.id, player.name]));
  const root = $("players");
  root.replaceChildren();
  for (const player of frame.players) {
    const before = previous?.players.find((item) => item.id === player.id);
    const button = document.createElement("button");
    button.type = "button";
    button.className = "player";
    button.style.left = `${(player.x / 120) * 100}%`;
    button.style.top = `${(player.y / 80) * 100}%`;
    const name = names.get(player.id) || "Player";
    button.setAttribute("aria-label", name);
    button.addEventListener("click", () => {
      state.focus = player.id;
      render();
    });
    const color = String(player.team_id) === HOME ? "#d0402f" : "#a6d6f2";
    if (before) {
      const dx = player.x - before.x;
      const dy = player.y - before.y;
      if (Math.hypot(dx, dy) > 0.2) {
        const arrow = document.createElement("span");
        arrow.className = "arrow";
        arrow.style.background = color;
        arrow.style.transform = `rotate(${Math.atan2(dy, dx) * 180 / Math.PI}deg)`;
        button.append(arrow);
      }
    }
    const dot = document.createElement("span");
    dot.className = "dot";
    dot.style.background = color;
    dot.style.borderColor = color;
    button.append(dot);
    if (player.id === state.focus) {
      const ring = document.createElement("span");
      ring.className = "ring";
      button.append(ring);
    }
    const showTag = player.id === state.focus
      || (name === "David Rochdale" && sec >= 268)
      || (name === "James Dickenson" && sec >= 270);
    if (showTag) {
      const tag = document.createElement("span");
      tag.className = "tag";
      tag.textContent = surname(name);
      button.append(tag);
    }
    root.append(button);
  }
  const ball = $("ball");
  ball.style.left = `${(frame.ball[0] / 120) * 100}%`;
  ball.style.top = `${(frame.ball[1] / 80) * 100}%`;
}

function renderCard(sec) {
  const row = facts.rows[sec];
  const player = row.players.find((item) => item.id === state.focus) || row.players.find((item) => item.name === "Robert Hampstead");
  if (!player) return;
  state.focus = player.id;
  $("player-name").textContent = player.name;
  const scored = player.goals > 0 && player.goal_clock
    ? `scored ${player.goal_clock} · xG ${Number(player.goal_xg).toFixed(2)}`
    : player.position;
  $("player-sub").textContent = `${player.team} · ${scored}`;
  const pct = player.pass_pct === null ? "—" : `${player.pass_pct}%`;
  $("player-line").textContent = `Minutes ${player.minutes} · Touches ${player.touches} · Passes ${player.passes} (${pct}) · Passenger fare ${player.passenger_fare}`;
  $("player-extra").textContent = `Shots ${player.shots} · xG ${xg(player.xg)} · Goals ${player.goals} · Assists ${player.assists} · Dribbles ${player.dribbles} · Duels ${player.duels} · Interceptions ${player.interceptions} · Fouls ${player.fouls} · Cards ${player.cards}`;
  const hardest = player.hardest_pass || "—";
  const average = player.avg_difficulty === null ? "—" : player.avg_difficulty;
  $("player-pass").textContent = `Pass difficulty ${average} avg · hardest ${hardest} · touch path ${player.touch_path} yd`;
  const key = String(player.id);
  const current = speed.current[key]?.[sec];
  const top = speed.top[key]?.[sec];
  const distance = speed.distance[key]?.[sec];
  $("player-speed").textContent = current === undefined
    ? "Speed, top speed, and distance are reconstructed. This player is off the pitch in the window."
    : `Speed ${current.toFixed(1)} m/s · top ${top.toFixed(1)} m/s · ${distance.toFixed(0)} m · reconstructed`;
}

function renderCall(sec) {
  const moment = momentAt(sec);
  const pack = moment.lines[state.style][state.lang][state.bias];
  $("who").textContent = `${moment.who[state.lang]} · ${STYLES.find((style) => style.id === state.style).short.toUpperCase()}`;
  $("moment-tag").textContent = moment.tag[state.lang];
  $("call").textContent = state.rewritten ? pack.rewrite : pack.call;
  $("analyst-label").textContent = ANALYST[state.lang];
  $("analyst").textContent = pack.analyst;
  $("rewrite-note").hidden = !state.rewritten;
  if (state.rewritten) $("rewrite-note").textContent = state.rewriteNote;
}

function render() {
  if (!state.ready) return;
  const sec = state.sec;
  const row = facts.rows[sec];
  const clock = clockOf(sec);
  $("counter").setAttribute("aria-label", `Match clock ${clock}`);
  $("counter").replaceChildren(...clock.split("").map((glyph) => {
    const span = document.createElement("span");
    span.className = glyph === ":" ? "colon" : "digit";
    span.textContent = glyph;
    return span;
  }));
  $("glass-clock").textContent = clock;
  $("score-home").textContent = row.score[HOME];
  $("score-away").textContent = row.score[AWAY];
  $("stats-at").textContent = `AT ${clock}`;
  $("shots-home").textContent = row.shots[HOME];
  $("shots-away").textContent = row.shots[AWAY];
  $("xg-home").textContent = xg(row.xg[HOME]);
  $("xg-away").textContent = xg(row.xg[AWAY]);
  if (!state.focus) {
    const hampstead = facts.rows[0].players.find((player) => player.name === "Robert Hampstead");
    state.focus = hampstead ? hampstead.id : null;
  }
  $("pass-home").textContent = `${row.pass_pct[HOME]}%`;
  $("pass-away").textContent = `${row.pass_pct[AWAY]}%`;
  $("control").textContent = `Arsesnail · ${row.control[HOME]} · Mancheater City · ${row.control[AWAY]}`;
  const scrub = $("scrub");
  if (document.activeElement !== scrub) scrub.value = String(sec);
  $("scan-label").textContent = state.scan < 0 ? "◀◀ SCAN 6×" : state.scan > 0 ? "SCAN 6× ▶▶" : state.playing ? "▶ 1×" : "❚❚";
  $("lamp").classList.toggle("on", state.playing);
  $("air-label").textContent = state.scan ? "SCANNING" : state.playing ? "ON AIR" : "PAUSED";
  $("play").setAttribute("aria-pressed", String(state.playing && !state.scan));
  $("pause").setAttribute("aria-pressed", String(!state.playing));
  $("rewind").setAttribute("aria-pressed", String(state.scan < 0));
  $("forward").setAttribute("aria-pressed", String(state.scan > 0));
  const style = STYLES.find((item) => item.id === state.style);
  $("voices").textContent = state.style === "homefan" ? FAN_VOICE[state.bias] : style.voice;
  $("needle").style.transform = `rotate(${90 - style.angle}deg)`;
  for (const button of document.querySelectorAll(".style-stop")) {
    button.setAttribute("aria-pressed", String(button.dataset.style === state.style));
  }
  for (const button of document.querySelectorAll("[data-lang]")) {
    button.setAttribute("aria-pressed", String(button.dataset.lang === state.lang));
  }
  for (const button of document.querySelectorAll("[data-bias]")) {
    button.setAttribute("aria-pressed", String(button.dataset.bias === state.bias));
  }
  renderPitch(sec);
  renderCard(sec);
  renderCall(sec);
}

function bindTransport() {
  const hold = (button, dir) => {
    button.addEventListener("pointerdown", (event) => {
      event.preventDefault();
      scanStart(dir);
    });
    button.addEventListener("pointerup", scanEnd);
    button.addEventListener("pointerleave", scanEnd);
    button.addEventListener("click", () => skip(dir));
  };
  hold($("rewind"), -1);
  hold($("forward"), 1);
  $("play").addEventListener("click", play);
  $("pause").addEventListener("click", pause);
  $("scrub").addEventListener("input", (event) => seek(event.target.value));
  $("rewrite").addEventListener("click", () => {
    const moment = momentAt(state.sec);
    const pack = moment.lines[state.style][state.lang][state.bias];
    state.rewritten = true;
    state.rewriteNote = "Local template. The live rewrite waits on the API.";
    render();
    fetch("http://127.0.0.1:8787/rewrite", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ sec: state.sec, style: state.style, lang: state.lang, bias: state.bias }),
    }).then(async (response) => {
      if (!response.ok) return;
      const data = await response.json();
      pack.rewrite = data.line;
      state.rewriteNote = data.note;
      state.rewritten = true;
      render();
    }).catch(() => {});
  });
  window.addEventListener("keydown", (event) => {
    if (event.target instanceof HTMLInputElement || event.repeat) return;
    if (event.code === "Space") {
      event.preventDefault();
      if (state.playing) pause();
      else play();
    } else if (event.code === "ArrowRight" || event.code === "ArrowLeft") {
      event.preventDefault();
      scanStart(event.code === "ArrowRight" ? 1 : -1);
    }
  });
  window.addEventListener("keyup", (event) => {
    if (event.code !== "ArrowRight" && event.code !== "ArrowLeft") return;
    const dir = event.code === "ArrowRight" ? 1 : -1;
    scanEnd();
    if (performance.now() - downAt <= 250) seek(state.sec + dir * 5);
  });
}

function bindChoices() {
  const root = $("styles");
  for (const style of STYLES) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "style-stop";
    button.dataset.style = style.id;
    button.textContent = style.short;
    button.setAttribute("aria-pressed", String(style.id === state.style));
    const rad = style.angle * Math.PI / 180;
    button.style.left = `${(50 + 40 * Math.cos(rad)).toFixed(1)}%`;
    button.style.top = `${(100 - 80 * Math.sin(rad)).toFixed(1)}%`;
    button.addEventListener("click", () => {
      state.style = style.id;
      state.rewritten = false;
      stopVoices();
      render();
    });
    root.append(button);
  }
  for (const button of document.querySelectorAll("[data-lang]")) {
    button.addEventListener("click", () => {
      state.lang = button.dataset.lang;
      state.rewritten = false;
      stopVoices();
      render();
    });
  }
  for (const button of document.querySelectorAll("[data-bias]")) {
    button.addEventListener("click", () => {
      state.bias = button.dataset.bias;
      state.rewritten = false;
      stopVoices();
      render();
    });
  }
  for (const spec of FADERS) {
    const column = document.createElement("div");
    column.className = "fader-col";
    const value = document.createElement("span");
    value.className = "fader-value";
    value.textContent = String(spec.value);
    const input = document.createElement("input");
    input.className = "fader";
    input.type = "range";
    input.min = "0";
    input.max = "100";
    input.value = String(spec.value);
    input.setAttribute("aria-label", `${spec.label} level`);
    input.id = `fader-${spec.id}`;
    input.addEventListener("input", () => {
      value.textContent = input.value;
      setFader(spec.id, Number(input.value) / 100);
    });
    setFader(spec.id, spec.value / 100);
    const name = document.createElement("span");
    name.className = "fader-name";
    name.textContent = spec.label;
    column.append(value, input, name);
    $(spec.group).append(column);
  }
}

async function load() {
  const [factFile, templateFile, positionFile, speedFile, cacheFile] = await Promise.all([
    fetch("../data/facts.json"),
    fetch("../data/templates.json"),
    fetch("../data/9000001-positions.json"),
    fetch("../data/speed.json"),
    fetch("../data/audio/cache.json"),
  ]);
  if (![factFile, templateFile, positionFile, speedFile].every((response) => response.ok)) {
    $("call").textContent = "The cached files did not load. Serve the repo root and open broadcast/app/.";
    return;
  }
  facts = await factFile.json();
  templates = await templateFile.json();
  positions = await positionFile.json();
  speed = await speedFile.json();
  cache = cacheFile.ok ? await cacheFile.json() : null;
  state.ready = true;
  render();
}

bindTransport();
bindChoices();
timer = window.setInterval(tick, 100);
load().catch(() => {
  $("call").textContent = "The cached files did not load. Serve the repo root and open broadcast/app/.";
});
