const BUSES = ["home", "away", "chant", "match", "call", "notes"];

let ctx = null;
const gains = {};
const pending = {};
const buffers = new Map();
let generation = 0;
let callSource = null;
let analystSource = null;
let analystTrim = null;

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
  const response = await fetch(url);
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
