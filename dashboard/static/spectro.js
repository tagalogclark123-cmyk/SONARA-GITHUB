// Log-mel spectrogram, computed in the browser with the same settings as the SONARA model input:
// 16 kHz audio, 400-sample Hann window, 160-sample hop, 64 mel bands (HTK scale, 0 to 8 kHz),
// power spectrum, 10*log10 in dB, centered frames with reflect padding (as torchaudio does).
(function () {
  const SR = 16000, NFFT = 400, HOP = 160, NMELS = 64;
  const NBINS = NFFT / 2 + 1;
  const DB_MIN = -55, DB_MAX = 20; // fixed colour range, the same for every clip

  // ---- tables, built once
  const win = new Float64Array(NFFT);
  for (let n = 0; n < NFFT; n += 1) win[n] = 0.5 - 0.5 * Math.cos((2 * Math.PI * n) / NFFT);
  const cosT = new Float64Array(NFFT), sinT = new Float64Array(NFFT);
  for (let n = 0; n < NFFT; n += 1) { cosT[n] = Math.cos((2 * Math.PI * n) / NFFT); sinT[n] = Math.sin((2 * Math.PI * n) / NFFT); }
  const hz2mel = (f) => 2595 * Math.log10(1 + f / 700);
  const mel2hz = (m) => 700 * (10 ** (m / 2595) - 1);
  const fb = []; // fb[m] = [{k, w}, ...]
  (function buildFilterbank() {
    const allf = Array.from({ length: NBINS }, (_, k) => (k * (SR / 2)) / (NBINS - 1));
    const mmax = hz2mel(SR / 2);
    const fp = Array.from({ length: NMELS + 2 }, (_, i) => mel2hz((i * mmax) / (NMELS + 1)));
    for (let m = 0; m < NMELS; m += 1) {
      const row = [];
      for (let k = 0; k < NBINS; k += 1) {
        const down = (allf[k] - fp[m]) / (fp[m + 1] - fp[m]);
        const up = (fp[m + 2] - allf[k]) / (fp[m + 2] - fp[m + 1]);
        const w = Math.max(0, Math.min(down, up));
        if (w > 0) row.push({ k, w });
      }
      fb.push(row);
    }
  }());

  // ---- WAV (16-bit PCM) to samples in -1..1, first channel
  function parseWav(buf) {
    const v = new DataView(buf);
    const tag = (o) => String.fromCharCode(v.getUint8(o), v.getUint8(o + 1), v.getUint8(o + 2), v.getUint8(o + 3));
    if (tag(0) !== 'RIFF' || tag(8) !== 'WAVE') throw new Error('not a WAV file');
    let o = 12, fmt = null, data = null;
    while (o + 8 <= v.byteLength) {
      const id = tag(o), size = v.getUint32(o + 4, true);
      if (id === 'fmt ') fmt = { format: v.getUint16(o + 8, true), channels: v.getUint16(o + 10, true), rate: v.getUint32(o + 12, true), bits: v.getUint16(o + 22, true) };
      if (id === 'data') { data = { start: o + 8, size: Math.min(size, v.byteLength - o - 8) }; break; }
      o += 8 + size + (size % 2);
    }
    if (!fmt || !data) throw new Error('WAV file has no audio');
    if (fmt.format !== 1 || fmt.bits !== 16) throw new Error('only 16-bit PCM WAV is supported');
    if (fmt.rate !== SR) throw new Error(`audio is ${fmt.rate} Hz, expected ${SR} Hz`);
    const n = Math.floor(data.size / (2 * fmt.channels));
    const x = new Float64Array(n);
    for (let i = 0; i < n; i += 1) x[i] = v.getInt16(data.start + i * 2 * fmt.channels, true) / 32768;
    return x;
  }

  // ---- log-mel: returns {db: Float32Array(NMELS * frames), frames}, db[m * frames + t]
  function logMel(x) {
    const pad = NFFT / 2, N = x.length;
    const xp = new Float64Array(N + 2 * pad);
    for (let i = 0; i < N; i += 1) xp[pad + i] = x[i];
    for (let i = 0; i < pad; i += 1) {
      xp[pad - 1 - i] = x[Math.min(i + 1, N - 1)];          // reflect at the start
      xp[pad + N + i] = x[Math.max(N - 2 - i, 0)];          // reflect at the end
    }
    const frames = 1 + Math.floor((xp.length - NFFT) / HOP);
    const db = new Float32Array(NMELS * frames);
    const fr = new Float64Array(NFFT), pw = new Float64Array(NBINS);
    for (let t = 0; t < frames; t += 1) {
      const off = t * HOP;
      for (let n = 0; n < NFFT; n += 1) fr[n] = xp[off + n] * win[n];
      for (let k = 0; k < NBINS; k += 1) {
        let re = 0, im = 0, idx = 0;
        for (let n = 0; n < NFFT; n += 1) {
          re += fr[n] * cosT[idx];
          im -= fr[n] * sinT[idx];
          idx += k; if (idx >= NFFT) idx -= NFFT;
        }
        pw[k] = re * re + im * im;
      }
      for (let m = 0; m < NMELS; m += 1) {
        let s = 0;
        const row = fb[m];
        for (let j = 0; j < row.length; j += 1) s += pw[row[j].k] * row[j].w;
        db[m * frames + t] = 10 * Math.log10(Math.max(s, 1e-10));
      }
    }
    return { db, frames };
  }

  // ---- drawing
  let lut = null;
  function colors() {
    if (lut) return lut;
    lut = [];
    for (let i = 0; i < 256; i += 1) {
      const c = d3.rgb(d3.interpolateMagma(i / 255));
      lut.push([c.r, c.g, c.b]);
    }
    return lut;
  }
  function paint(canvas, spec) {
    const { db, frames } = spec;
    canvas.width = frames;
    canvas.height = NMELS;
    const ctx = canvas.getContext('2d');
    const img = ctx.createImageData(frames, NMELS);
    const L = colors();
    for (let m = 0; m < NMELS; m += 1) {
      const y = NMELS - 1 - m; // low pitch at the bottom
      for (let t = 0; t < frames; t += 1) {
        const v = (db[m * frames + t] - DB_MIN) / (DB_MAX - DB_MIN);
        const c = L[Math.max(0, Math.min(255, Math.round(v * 255)))];
        const p = (y * frames + t) * 4;
        img.data[p] = c[0]; img.data[p + 1] = c[1]; img.data[p + 2] = c[2]; img.data[p + 3] = 255;
      }
    }
    ctx.putImageData(img, 0, 0);
  }

  // Builds the box: canvas + axis labels. Returns the element and its canvas.
  function frame() {
    const box = document.createElement('div');
    box.className = 'spec';
    const plot = document.createElement('div');
    plot.className = 'spec-plot';
    const canvas = document.createElement('canvas');
    canvas.className = 'spec-canvas';
    plot.appendChild(canvas);
    const msg = document.createElement('div');
    msg.className = 'spec-msg';
    msg.textContent = 'Loading…';
    plot.appendChild(msg);
    const line = document.createElement('div');
    line.className = 'spec-line';
    line.hidden = true;
    plot.appendChild(line);
    [['High', 'spec-y spec-y-top'], ['Low', 'spec-y spec-y-bottom']].forEach(([label, cls]) => {
      const s = document.createElement('span');
      s.className = cls;
      s.textContent = label;
      plot.appendChild(s);
    });
    const xs = document.createElement('div');
    xs.className = 'spec-x';
    ['Start', 'End'].forEach((t) => { const s = document.createElement('span'); s.textContent = t; xs.appendChild(s); });
    box.append(plot, xs);
    return { box, canvas, msg, line };
  }

  const cache = new Map();
  function get(url) {
    if (!cache.has(url)) {
      cache.set(url, fetch(url)
        .then((r) => { if (!r.ok) throw new Error('audio file not found'); return r.arrayBuffer(); })
        .then((buf) => logMel(parseWav(buf))));
      if (cache.size > 300) cache.delete(cache.keys().next().value);
    }
    return cache.get(url);
  }

  // Draws the spectrogram of `url` into a frame() made earlier.
  async function render(parts, url) {
    parts.msg.hidden = false;
    parts.msg.textContent = 'Loading…';
    try {
      const spec = await get(url);
      paint(parts.canvas, spec);
      parts.msg.hidden = true;
    } catch (e) {
      cache.delete(url);
      parts.msg.textContent = 'Cannot show this sound: ' + e.message;
    }
  }

  // Moves the white line to `frac` (0 = start, 1 = end); null hides it.
  function setLine(parts, frac) {
    if (frac == null) { parts.line.hidden = true; return; }
    parts.line.hidden = false;
    parts.line.style.left = `${Math.max(0, Math.min(1, frac)) * 100}%`;
  }

  window.SonaraSpectro = { parseWav, logMel, frame, render, setLine, SR, NFFT, HOP, NMELS };
}());
