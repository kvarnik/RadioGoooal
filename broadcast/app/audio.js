const BUSES = ["home", "away", "chant", "match", "call", "notes"];

let ctx = null;
const gains = {};
const pending = {};
const buffers = new Map();
let generation = 0;
let callSource = null;
let analystSource = null;
let analystTrim = null;
let loops = [];
let effects = new Map();
let loopSources = [];
let loopRun = 0;
let starting = false;
let effectGeneration = 0;
const liveEffects = new Set();

function graph() {
  if (ctx) return ctx;
  ctx = new AudioContext();
  const limiter = ctx.createDynamicsCompressor();
  limiter.threshold.value = -1;
  limiter.knee.value = 0;
  limiter.ratio.value = 20;
  limiter.attack.value = 0.003;
  limiter.release.value = 0.25;
  const sum = ctx.createGain();
  sum.channelCount = 1;
  sum.channelCountMode = "explicit";
  sum.connect(limiter);
  limiter.connect(ctx.destination);
  for (const id of BUSES) {
    const gain = ctx.createGain();
    gain.gain.value = pending[id] ?? 0;
    gain.connect(sum);
    gains[id] = gain;
  }
  return ctx;
}

export function setFader(id, level) {
  pending[id] = level;
  if (gains[id]) gains[id].gain.value = level;
}

function parseCsv(text) {
  const rows = [];
  let row = [];
  let cell = "";
  let quoted = false;
  const pushRow = () => {
    row.push(cell);
    if (row.some((value) => value !== "")) rows.push(row);
    row = [];
    cell = "";
  };
  for (let i = 0; i < text.length; i += 1) {
    const char = text[i];
    if (quoted) {
      if (char === '"') {
        if (text[i + 1] === '"') {
          cell += '"';
          i += 1;
        } else {
          quoted = false;
        }
      } else {
        cell += char;
      }
    } else if (char === '"') {
      quoted = true;
    } else if (char === ",") {
      row.push(cell);
      cell = "";
    } else if (char === "\n") {
      pushRow();
    } else if (char !== "\r") {
      cell += char;
    }
  }
  if (cell.length || row.length) pushRow();
  const [header, ...body] = rows;
  return body.map((cols) => Object.fromEntries(header.map((key, index) => [key, cols[index] ?? ""])));
}

export function loadInventory(text) {
  const rows = parseCsv(text);
  loops = rows.filter((row) => row.playback === "loop" && row.filename && row.bus);
  effects = new Map(rows.filter((row) => row.playback === "oneshot" && row.role).map((row) => [row.role, row]));
  for (const row of rows) bufferFor(row.filename);
  return rows;
}

export function startLoops() {
  if (loopSources.length || starting) {
    graph().resume();
    return;
  }
  starting = true;
  const run = loopRun;
  const context = graph();
  context.resume();
  Promise.all(loops.map(async (row) => {
    const buffer = await bufferFor(row.filename);
    if (run !== loopRun || !buffer) return null;
    const source = context.createBufferSource();
    source.buffer = buffer;
    source.loop = true;
    source.connect(gains[row.bus]);
    source.start();
    return source;
  })).then((sources) => {
    starting = false;
    const live = sources.filter(Boolean);
    if (run !== loopRun) {
      for (const source of live) stopSource(source);
      return;
    }
    loopSources = live;
  });
}

export function stopLoops() {
  loopRun += 1;
  starting = false;
  for (const source of loopSources) stopSource(source);
  loopSources = [];
}

export async function playEffect(role) {
  const row = effects.get(role);
  if (!row?.filename) return;
  const token = effectGeneration;
  const context = graph();
  const resume = context.resume();
  const buffer = await bufferFor(row.filename);
  await resume;
  if (token !== effectGeneration || !buffer) return;
  const started = connect(buffer, row.bus || "match", 1);
  liveEffects.add(started.source);
  started.source.onended = () => {
    liveEffects.delete(started.source);
  };
}

export function stopEffects() {
  effectGeneration += 1;
  for (const source of liveEffects) stopSource(source);
  liveEffects.clear();
}

function stopSource(source) {
  if (!source) return;
  source.onended = null;
  try {
    source.stop();
  } catch {
    // The buffer already finished.
  }
}

export function stopVoices() {
  generation += 1;
  stopSource(callSource);
  stopSource(analystSource);
  callSource = null;
  analystSource = null;
  analystTrim = null;
}

async function bufferFor(file) {
  const url = `../data/audio/${file}`;
  if (buffers.has(url)) return buffers.get(url);
  const response = await fetch(url, { cache: "no-store" });
  if (!response.ok) return null;
  const audio = await graph().decodeAudioData(await response.arrayBuffer());
  buffers.set(url, audio);
  return audio;
}

function connect(buffer, bus, scale) {
  const source = graph().createBufferSource();
  source.buffer = buffer;
  const trim = graph().createGain();
  trim.gain.value = scale;
  source.connect(trim);
  trim.connect(gains[bus]);
  source.start();
  return { source, trim };
}

export async function startVoices(callEntry, analystEntry) {
  if (!callEntry?.file) return;
  const token = ++generation;
  const context = graph();
  await context.resume();
  const callBuffer = await bufferFor(callEntry.file);
  if (!callBuffer || token !== generation) return;
  stopSource(callSource);
  if (analystSource && analystTrim) analystTrim.gain.value = 0.25;
  const started = connect(callBuffer, "call", 1);
  callSource = started.source;
  callSource.onended = () => {
    if (token !== generation) return;
    callSource = null;
    stopSource(analystSource);
    analystSource = null;
    analystTrim = null;
    if (!analystEntry?.file) return;
    bufferFor(analystEntry.file).then((analystBuffer) => {
      if (!analystBuffer || token !== generation) return;
      const analyst = connect(analystBuffer, "notes", 1);
      analystSource = analyst.source;
      analystTrim = analyst.trim;
      analystSource.onended = () => {
        if (analystSource !== analyst.source) return;
        analystSource = null;
        analystTrim = null;
      };
    });
  };
}
