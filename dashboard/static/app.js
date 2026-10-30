// SONARA dashboard (farmer view). All numbers come from /api/data, served by server.py
// from the field_data folder. Nothing on this page is made up.

const state = { data: null, session: null, idx: 0, timer: null, view: 'dashboard', showAllActivity: false, pictures: false };

const $ = (id) => document.getElementById(id);
const toDate = (s) => new Date(String(s).replace(' ', 'T'));
const fmt = {
  int: d3.format(','),
  pct: d3.format('.0%'),
  time: d3.timeFormat('%-I:%M %p'),
  timeSec: d3.timeFormat('%-I:%M:%S %p'),
  day: d3.timeFormat('%b %-d'),
  longDay: d3.timeFormat('%A, %B %-d, %Y'),
  axis: d3.timeFormat('%-I:%M'),
};

// Small line icons (stroke paths in a 24x24 box). Fixed strings, never data.
const ICONS = {
  bird: '<path d="M16 7h.01"/><path d="M3.4 18H12a8 8 0 0 0 8-8V7a4 4 0 0 0-7.28-2.3L2 20"/><path d="m20 7 2 .5-2 .5"/><path d="M10 18v3"/><path d="M14 17.75V21"/><path d="M7 18a6 6 0 0 0 3.84-10.61"/>',
  sound: '<path d="M11 5 6 9H2v6h4l5 4V5z"/><path d="M15.54 8.46a5 5 0 0 1 0 7.07"/><path d="M19.07 4.93a10 10 0 0 1 0 14.14"/>',
  wifi: '<path d="M5 12.55a11 11 0 0 1 14.08 0"/><path d="M1.42 9a16 16 0 0 1 21.16 0"/><path d="M8.53 16.11a6 6 0 0 1 6.95 0"/><path d="M12 20h.01"/>',
  wifiOff: '<path d="M12 20h.01"/><path d="M8.5 16.43a5 5 0 0 1 7 0"/><path d="M5 12.86a10 10 0 0 1 5.17-2.69"/><path d="M19 12.86a10 10 0 0 0-2-1.39"/><path d="M2 8.82a15 15 0 0 1 4.18-2.65"/><path d="M22 8.82a15 15 0 0 0-11.29-3.76"/><path d="m2 2 20 20"/>',
  alert: '<path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><path d="M12 9v4"/><path d="M12 17h.01"/>',
  check: '<path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><path d="m9 11 3 3L22 4"/>',
  play: '<polygon points="6 3 20 12 6 21 6 3"/>',
  pause: '<rect x="6" y="4" width="4" height="16" rx="1"/><rect x="14" y="4" width="4" height="16" rx="1"/>',
  stop: '<rect x="5" y="5" width="14" height="14" rx="2"/>',
};
function icon(name) {
  const ns = 'http://www.w3.org/2000/svg';
  const svg = document.createElementNS(ns, 'svg');
  svg.setAttribute('class', 'ic');
  svg.setAttribute('viewBox', '0 0 24 24');
  svg.innerHTML = ICONS[name];
  return svg;
}
function el(tag, cls, text) {
  const e = document.createElement(tag);
  if (cls) e.className = cls;
  if (text != null) e.textContent = text;
  return e;
}
function iconBox(name, tone) {
  const s = el('span', 'kpi-ic ic-' + tone);
  s.appendChild(icon(name));
  return s;
}

const settings = () => state.data.settings;
const sessionById = (id) => state.data.sessions.find((s) => s.session_id === id);
const currentSession = () => sessionById(state.session);
const clipsOf = (id) => state.data.clips.filter((c) => c.session_id === id);
const sessionClips = () => clipsOf(state.session);
const audioUrl = (c) => `/audio/${encodeURIComponent(c.session_id)}/${encodeURIComponent(c.file)}`;
const kind = (c) => (!c.usable ? 'lost' : c.flagged ? 'bad' : 'ok');
const STATUS_LABEL = { normal: 'Normal', watch: 'Watch', alert: 'Check birds', none: 'No data' };

// Everything the page needs to know about one recording, worked out from its clips.
function summarize(s) {
  const rows = clipsOf(s.session_id);
  const usable = rows.filter((c) => c.usable);
  const flagged = usable.filter((c) => c.flagged);
  const share = rows.length ? usable.length / rows.length : 0;
  const connection = share >= 0.95 ? 'good' : share >= 0.75 ? 'weak' : 'poor';
  const alertStarts = [];
  let prev = 0;
  usable.forEach((c) => { if (c.alert && !prev) alertStarts.push(c); prev = c.alert; });
  let status = 'normal';
  if (!usable.length) status = 'none';
  else if (alertStarts.length) status = 'alert';
  else if (flagged.length) status = 'watch';
  return {
    s, rows, usable, flagged, share, connection, alertStarts, status,
    first: rows.length ? toDate(rows[0].time) : null,
    last: rows.length ? toDate(rows[rows.length - 1].time) : null,
  };
}
const connLabel = { good: 'Good', weak: 'Weak', poor: 'Poor' };
const recLabel = (info) => `${info.s.pen} · ${info.first ? `${fmt.day(info.first)}, ${fmt.time(info.first)}` : info.s.date}`;
const timeRange = (info) => (info.first ? `${fmt.longDay(info.first)} · ${fmt.time(info.first)} to ${fmt.time(info.last)}` : '');

// ---------------------------------------------------------------- loading

async function load() {
  $('error').hidden = true;
  try {
    const res = await fetch('/api/data', { cache: 'no-store' });
    const body = await res.json();
    if (!res.ok || body.error) throw new Error(body.error || res.statusText);
    state.data = body;
  } catch (e) {
    $('error').textContent = 'Could not load the recordings: ' + e.message;
    $('error').hidden = false;
    return;
  }
  if (state.data.has_logo) {
    const img = el('img');
    img.src = '/static/logo.png';
    img.alt = 'SONARA logo';
    $('logo').replaceChildren(img);
  }
  const ids = state.data.sessions.map((s) => s.session_id);
  if (!ids.includes(state.session)) state.session = ids[0] || null;
  if (!state.session) {
    $('error').textContent = 'No recordings found in the data folder.';
    $('error').hidden = false;
    return;
  }
  resetReplay();
  drawAll();
}

function selectSession(id) {
  if (id === state.session) return;
  state.session = id;
  state.showAllActivity = false;
  resetReplay();
  drawAll();
}

function resetReplay() {
  stopReplay();
  state.idx = Math.max(0, sessionClips().length - 1);
}

// ---------------------------------------------------------------- views

function showView(name) {
  const known = ['dashboard', 'replay', 'sounds', 'help'];
  state.view = known.includes(name) ? name : 'dashboard';
  document.querySelectorAll('.view').forEach((v) => { v.hidden = v.dataset.view !== state.view; });
  document.querySelectorAll('.nav-item').forEach((a) => a.classList.toggle('active', a.dataset.view === state.view));
  if (state.view !== 'replay') stopReplay();
  if (state.view !== 'replay' && state.view !== 'sounds') stopAllSounds();
  if (state.data && state.view === 'replay') { drawStrip(); replayCard.drawPicture(); }
  if (state.data && state.view === 'sounds') soundCards.forEach((c) => c.drawPicture());
  window.scrollTo(0, 0);
}
window.addEventListener('hashchange', () => showView(location.hash.slice(1)));

// ---------------------------------------------------------------- drawing

function drawAll() {
  const info = summarize(currentSession());
  drawTop(info);
  drawKpis(info);
  drawZones();
  drawNodes(info);
  drawActivity(info);
  drawAlertPanel(info);
  drawDonut(info);
  drawReplay();
  drawStrip();
  drawSounds(info);
  const n = info.flagged.length;
  $('nav-sounds-count').hidden = n === 0;
  $('nav-sounds-count').textContent = fmt.int(n);
  $('foot').textContent = 'SONARA · research prototype, USTP BS Data Science. It does not diagnose disease.';
}

function drawTop(info) {
  $('top-date').textContent = timeRange(info);
  const sel = $('recording');
  sel.replaceChildren(...state.data.sessions.map((s) => {
    const o = new Option(recLabel(summarize(s)), s.session_id);
    return o;
  }));
  sel.value = state.session;
  const sub = `${info.s.pen} · ${timeRange(info)}`;
  $('replay-sub').textContent = sub;
  $('sounds-sub').textContent = sub;
}

function drawKpis(info) {
  const s = info.s;
  $('k-birds').textContent = s.birds ? fmt.int(Number(s.birds)) : '—';
  $('k-birds-sub').textContent = s.birds ? `${s.pen}${s.age ? ', ' + s.age : ''}` : 'Not recorded';

  const n = info.flagged.length;
  $('k-unusual').textContent = fmt.int(n);
  const us = $('k-unusual-sub');
  us.textContent = n ? `Last heard at ${fmt.time(toDate(info.flagged[n - 1].time))}` : 'None in this recording';
  us.className = 'kpi-sub' + (n ? ' warn' : '');

  const link = $('k-link');
  link.textContent = connLabel[info.connection];
  link.className = 'kpi-value val-' + info.connection;
  const ls = $('k-link-sub');
  ls.textContent = `${fmt.int(info.usable.length)} of ${fmt.int(info.rows.length)} recordings received`;
  ls.className = 'kpi-sub' + (info.connection === 'poor' ? ' bad' : info.connection === 'weak' ? ' warn' : '');

  const a = info.alertStarts.length;
  $('k-alerts').textContent = fmt.int(a);
  const as = $('k-alerts-sub');
  as.textContent = a ? `First at ${fmt.time(toDate(info.alertStarts[0].time))}` : 'None during this recording';
  as.className = 'kpi-sub' + (a ? ' bad' : '');
}

function drawZones() {
  const box = $('zones');
  box.replaceChildren();
  const summaryText = { alert: 'Many unusual sounds', watch: 'Some unusual sounds', normal: 'No unusual sounds', none: 'No sound received' };
  state.data.sessions.forEach((s) => {
    const info = summarize(s);
    const card = el('button', `zone z-${info.status}` + (s.session_id === state.session ? ' selected' : ''));
    card.type = 'button';
    card.setAttribute('aria-pressed', String(s.session_id === state.session));

    const head = el('div', 'zone-head');
    const names = el('div');
    names.append(el('span', 'zone-name', s.pen), el('span', 'zone-when', info.first ? `${fmt.day(info.first)}, ${fmt.time(info.first)} to ${fmt.time(info.last)}` : s.date));
    const badge = el('span', 'badge b-' + info.status);
    badge.append(el('span', 'dot'), document.createTextNode(STATUS_LABEL[info.status]));
    head.append(names, badge);

    const stats = el('div', 'zone-stats');
    const mini = (ic, tone, label, value) => {
      const m = el('div', 'mini');
      const t = el('div', 'mini-text');
      t.append(el('span', 'mini-label', label), el('span', 'mini-value', value));
      m.append(iconBox(ic, tone), t);
      return m;
    };
    stats.append(
      mini('bird', 'green', 'Birds', s.birds ? fmt.int(Number(s.birds)) : '—'),
      mini('sound', info.flagged.length ? 'red' : 'green', 'Unusual sounds', fmt.int(info.flagged.length)),
    );

    const foot = el('div', 'zone-foot');
    const conn = el('span', 'conn val-' + info.connection);
    conn.append(icon(info.connection === 'poor' ? 'wifiOff' : 'wifi'), document.createTextNode('Sensor: ' + connLabel[info.connection]));
    foot.append(el('span', '', summaryText[info.status]), conn);

    card.append(head, stats, foot);
    card.addEventListener('click', () => selectSession(s.session_id));
    box.appendChild(card);
  });
}

function drawNodes(info) {
  const box = $('nodes');
  box.replaceChildren();
  const nodes = d3.groups(info.rows, (c) => c.node);
  $('node-count').textContent = `${nodes.length} ${nodes.length === 1 ? 'node' : 'nodes'} in this pen`;
  nodes.forEach(([node, rows]) => {
    const ok = rows.filter((c) => c.usable).length;
    const share = rows.length ? ok / rows.length : 0;
    const conn = share >= 0.95 ? 'good' : share >= 0.75 ? 'weak' : 'poor';
    const row = el('div', 'node n-' + conn);
    const text = el('div', 'node-text');
    const place = info.s.mic_position && info.s.mic_position !== 'not recorded' ? info.s.mic_position : 'placement not recorded';
    text.append(el('span', 'node-name', `Node ${node}`), el('span', 'node-sub', `Last recording ${fmt.time(toDate(rows[rows.length - 1].time))} · ${place}`));
    const pct = el('div', 'node-pct val-' + conn, fmt.pct(share));
    pct.appendChild(el('small', '', 'received'));
    row.append(iconBox(conn === 'poor' ? 'wifiOff' : 'wifi', conn === 'good' ? 'green' : conn === 'weak' ? 'amber' : 'red'), text, pct);
    box.appendChild(row);
  });
}

// Events in the recording, built from the clips: start, unusual sounds, connection lost/back, alerts, end.
function events(info) {
  const ev = [];
  const rows = info.rows;
  if (!rows.length) return ev;
  ev.push({ t: toDate(rows[0].time), title: 'Recording started', ic: 'play', tone: 'grey' });
  let lostRun = 0;
  let lostStart = null;
  let isLost = false;
  let prevAlert = 0;
  rows.forEach((c) => {
    if (!c.usable) {
      if (lostRun === 0) lostStart = c;
      lostRun += 1;
      if (lostRun === 3) { ev.push({ t: toDate(lostStart.time), title: 'Sensor connection lost', ic: 'wifiOff', tone: 'amber' }); isLost = true; }
      return;
    }
    if (isLost) ev.push({ t: toDate(c.time), title: 'Sensor connection back', ic: 'wifi', tone: 'blue' });
    lostRun = 0; isLost = false;
    if (c.flagged) ev.push({ t: toDate(c.time), title: 'Unusual sound heard', ic: 'sound', tone: 'red' });
    if (c.alert && !prevAlert) ev.push({ t: toDate(c.time), title: '"Check birds" alert started', ic: 'alert', tone: 'red' });
    if (!c.alert && prevAlert) ev.push({ t: toDate(c.time), title: 'Alert ended', ic: 'check', tone: 'green' });
    prevAlert = c.alert;
  });
  ev.push({ t: toDate(rows[rows.length - 1].time), title: 'Recording ended', ic: 'stop', tone: 'grey' });
  return ev.reverse();
}

function drawActivity(info) {
  const ev = events(info);
  const shown = state.showAllActivity ? ev : ev.slice(0, 5);
  const ul = $('activity');
  ul.replaceChildren(...shown.map((e) => {
    const li = el('li', 'act');
    const t = el('div');
    t.append(el('div', 'act-title', e.title), el('div', 'act-time', fmt.timeSec(e.t)));
    li.append(iconBox(e.ic, e.tone), t);
    return li;
  }));
  const btn = $('activity-toggle');
  btn.hidden = ev.length <= 5;
  btn.textContent = state.showAllActivity ? 'Show less' : `View all (${ev.length})`;
}

function drawAlertPanel(info) {
  const s = info.s;
  const n = info.flagged.length;
  const panel = $('alert-panel');
  panel.className = 'alert-panel p-' + info.status;
  const C = {
    alert: {
      ic: 'alert', title: 'Active alert', sub: 'Many unusual sounds close together', badge: 'Check birds',
      heading: 'Breathing-related sounds heard',
      text: `Many coughing or breathing-related sounds were heard in this pen within a short time.`,
      timeLabel: 'First alert', time: info.alertStarts.length ? fmt.time(toDate(info.alertStarts[0].time)) : '—',
      action: 'Check the birds in this pen. Listen to the sounds first. If the birds look sick, contact a veterinarian.',
    },
    watch: {
      ic: 'alert', title: 'Keep watch', sub: 'Not enough for an alert yet', badge: 'Watch',
      heading: 'Unusual sounds heard',
      text: `${fmt.int(n)} unusual ${n === 1 ? 'sound was' : 'sounds were'} heard in this pen. Not enough for a "Check birds" alert.`,
      timeLabel: 'Last heard', time: n ? fmt.time(toDate(info.flagged[n - 1].time)) : '—',
      action: 'Listen to the sounds and look at the birds when you can. If they look sick, contact a veterinarian.',
    },
    normal: {
      ic: 'check', title: 'No alerts', sub: 'Nothing unusual heard', badge: 'Normal',
      heading: 'All quiet',
      text: `No unusual sounds were heard in this pen during this recording.`,
      timeLabel: 'Recorded until', time: info.last ? fmt.time(info.last) : '—',
      action: 'Keep watching your birds as usual.',
    },
    none: {
      ic: 'wifiOff', title: 'No data', sub: 'No sound received', badge: 'No data',
      heading: 'The sensor sent no usable sound',
      text: 'SONARA cannot tell anything about the birds in this pen for this recording.',
      timeLabel: 'Recorded until', time: info.last ? fmt.time(info.last) : '—',
      action: "Check the sensor's power and move it closer to the receiver.",
    },
  }[info.status];
  $('alert-ic').replaceChildren(icon(C.ic));
  $('alert-title').textContent = C.title;
  $('alert-sub').textContent = C.sub;
  $('alert-badge').textContent = C.badge;
  $('alert-heading').textContent = C.heading;
  $('alert-text').textContent = C.text;
  $('alert-pen').textContent = s.pen;
  $('alert-time-label').textContent = C.timeLabel;
  $('alert-time').textContent = C.time;
  $('action-text').textContent = C.action;
  const warn = $('link-warning');
  const missing = info.rows.length - info.usable.length;
  warn.hidden = info.connection === 'good' || info.status === 'none';
  warn.textContent = `${fmt.int(missing)} of ${fmt.int(info.rows.length)} recordings (${fmt.pct(1 - info.share)}) did not arrive clearly. Sounds may have been missed. Check the sensor's position and power.`;
  $('btn-listen').hidden = n === 0;
}

function drawDonut(info) {
  const box = $('donut');
  box.replaceChildren();
  const parts = [
    { key: 'Normal', n: info.usable.length - info.flagged.length, color: 'var(--green)' },
    { key: 'Unusual sound', n: info.flagged.length, color: 'var(--red)' },
    { key: 'Not received', n: info.rows.length - info.usable.length, color: 'var(--lost)' },
  ];
  const total = d3.sum(parts, (p) => p.n);
  const svg = d3.select(box).append('svg').attr('viewBox', '-75 -75 150 150');
  const pie = d3.pie().value((p) => p.n).sort(null).padAngle(total ? 0.015 : 0);
  const arc = d3.arc().innerRadius(52).outerRadius(72).cornerRadius(2);
  svg.selectAll('path').data(pie(parts.filter((p) => p.n > 0))).join('path')
    .attr('d', arc).style('fill', (d) => d.data.color);
  svg.append('text').attr('class', 'donut-center').attr('text-anchor', 'middle').attr('y', 6).text(fmt.int(total));
  svg.append('text').attr('class', 'donut-center-sub').attr('text-anchor', 'middle').attr('y', 24).text('recordings');
  $('donut-legend').replaceChildren(...parts.map((p) => {
    const li = el('li');
    const dot = el('span', 'dot');
    dot.style.background = p.color;
    const val = el('span', 'val', fmt.int(p.n) + ' ');
    val.appendChild(el('small', '', total ? fmt.pct(p.n / total) : ''));
    li.append(dot, el('span', 'lab', p.key), val);
    return li;
  }));
}

// ---------------------------------------------------------------- replay

// Zone status for clip i, following the gateway's rule.
function statusAt(rows, i) {
  const r = rows[i];
  let last = null;
  for (let j = i; j >= 0; j -= 1) { if (rows[j].usable) { last = rows[j]; break; } }
  const gapMin = last ? (toDate(r.time) - toDate(last.time)) / 60000 : Infinity;
  if (!last || gapMin > settings().no_data_minutes) {
    return ['none', 'No data', 'The sensor in this pen is not sending sound. Check the sensor and its power.'];
  }
  if (r.alert) return ['alert', 'Check birds', 'Many coughing or breathing-related sounds. Please check the birds in this pen. If they look sick, contact a veterinarian.'];
  if (r.window_flags > 0) return ['watch', 'Watch', 'Some unusual sounds were heard. Keep an eye on this pen.'];
  return ['normal', 'Normal', 'No unusual sounds heard in this pen.'];
}

function drawReplay() {
  const rows = sessionClips();
  $('play').textContent = state.timer ? 'Pause' : 'Play';
  if (!rows.length) return;
  state.idx = Math.min(state.idx, rows.length - 1);
  const slider = $('slider');
  slider.max = String(rows.length - 1);
  slider.value = String(state.idx);
  const r = rows[state.idx];
  const [cls, label, text] = statusAt(rows, state.idx);
  $('pill').className = 'status-pill st-' + cls;
  $('pill').textContent = label;
  $('msg').textContent = text;
  const now = !r.usable ? 'not received clearly' : r.flagged ? 'unusual sound' : 'normal';
  $('sub').textContent = `Recent sounds: ${fmt.int(r.window_flags)} unusual out of the last ${fmt.int(settings().alert_window_clips)}. This sound: ${now}.`;
  $('clock').textContent = fmt.timeSec(toDate(r.time));
  $('listen').disabled = !r.has_audio;
  updateReplaySound();
}

function drawStrip() {
  const rows = sessionClips();
  const box = $('strip');
  box.replaceChildren();
  if (!rows.length || state.view !== 'replay') return;
  const W = Math.max(280, Math.floor(box.clientWidth || 600));
  const H = 86, top = 6, barH = 46, left = 8, right = 8;
  const svg = d3.select(box).append('svg').attr('viewBox', `0 0 ${W} ${H}`);
  // One bar per recording, evenly spaced, in time order.
  const x = d3.scaleBand(d3.range(rows.length), [left, W - right]).paddingInner(rows.length > 150 ? 0 : 0.15);
  const bw = Math.max(1, x.bandwidth());
  const mid = (i) => x(i) + x.bandwidth() / 2;
  const color = { ok: 'var(--green)', bad: 'var(--red)', lost: 'var(--lost)' };
  svg.append('g').selectAll('rect').data(rows).join('rect')
    .attr('x', (r, i) => x(i)).attr('width', bw)
    .attr('y', top).attr('height', barH).attr('rx', Math.min(2, bw / 2))
    .style('fill', (r) => color[kind(r)]).style('opacity', (r) => (kind(r) === 'ok' ? 0.4 : 1));
  const nTicks = Math.max(2, Math.min(rows.length, Math.floor(W / 110)));
  const tickIdx = [...new Set(d3.range(nTicks).map((k) => Math.round((k * (rows.length - 1)) / Math.max(1, nTicks - 1))))];
  svg.append('g').attr('class', 'axis').selectAll('text').data(tickIdx).join('text')
    .attr('x', (i) => mid(i)).attr('y', top + barH + 20)
    .attr('text-anchor', (i, k) => (k === 0 ? 'start' : k === tickIdx.length - 1 ? 'end' : 'middle'))
    .text((i) => fmt.axis(toDate(rows[i].time)));
  const cx = mid(state.idx);
  svg.append('line').attr('class', 'cursor').attr('x1', cx).attr('x2', cx).attr('y1', top - 4).attr('y2', top + barH + 4);

  const tip = $('tip');
  const nearest = (event) => {
    const [mx] = d3.pointer(event, svg.node());
    return Math.max(0, Math.min(rows.length - 1, Math.floor((mx - left) / x.step())));
  };
  svg.style('cursor', 'pointer')
    .on('pointermove', (event) => {
      const r = rows[nearest(event)];
      tip.replaceChildren(el('div', 'h', fmt.timeSec(toDate(r.time))), el('div', '', { ok: 'Normal', bad: 'Unusual sound', lost: 'Not received clearly' }[kind(r)]));
      tip.hidden = false;
      const w = tip.offsetWidth;
      let l = event.clientX + 14;
      if (l + w > window.innerWidth - 8) l = event.clientX - w - 14;
      tip.style.left = Math.max(8, l) + 'px';
      tip.style.top = (event.clientY - 44) + 'px';
    })
    .on('pointerleave', () => { tip.hidden = true; })
    .on('click', (event) => { stopReplay(); moveReplay(nearest(event)); });
}

// ---------------------------------------------------------------- sounds

// Every sound card on the page. Only one sound plays at a time.
const soundCards = new Set();
function stopAllSounds(except) {
  soundCards.forEach((c) => { if (c !== except && !c.audio.paused) c.audio.pause(); });
}

// A sound card: label, time, Play button and (when sound pictures are on) the picture
// with a white line that moves while the sound plays.
function soundCard() {
  const card = el('div', 'snd');
  const head = el('div', 'snd-head');
  const tag = el('span', 'tag');
  const time = el('span', 'muted');
  const btn = el('button', 'btn btn-small btn-play');
  btn.type = 'button';
  head.append(tag, time, btn);
  const pic = SonaraSpectro.frame();
  pic.box.classList.add('pic-only');
  card.append(head, pic.box);
  const audio = new Audio();
  audio.preload = 'none';
  const c = { el: card, audio, url: null, drawn: null, busy: false, pending: false, raf: 0 };

  const setBtn = () => {
    btn.replaceChildren(icon(audio.paused ? 'play' : 'pause'), document.createTextNode(audio.paused ? 'Play' : 'Pause'));
    btn.disabled = !c.url;
  };
  const tick = () => {
    const f = audio.duration ? audio.currentTime / audio.duration : 0;
    SonaraSpectro.setLine(pic, f);
    if (!audio.paused) c.raf = requestAnimationFrame(tick);
  };
  audio.addEventListener('play', () => { setBtn(); cancelAnimationFrame(c.raf); c.raf = requestAnimationFrame(tick); });
  audio.addEventListener('pause', () => { setBtn(); cancelAnimationFrame(c.raf); });
  audio.addEventListener('ended', () => { audio.currentTime = 0; setBtn(); SonaraSpectro.setLine(pic, null); });
  c.play = () => {
    if (!c.url) return;
    if (audio.paused) { stopAllSounds(c); audio.play().catch(() => {}); } else audio.pause();
  };
  btn.addEventListener('click', c.play);

  // Draws the picture if pictures are on. While one is being drawn, newer requests wait
  // and only the latest is drawn after it (keeps the replay smooth while it plays).
  c.drawPicture = async () => {
    if (!state.pictures || !c.url || c.url === c.drawn || !card.isConnected) return;
    if (c.busy) { c.pending = true; return; }
    c.busy = true;
    const url = c.url;
    await SonaraSpectro.render(pic, url);
    c.drawn = url;
    c.busy = false;
    if (c.pending) { c.pending = false; c.drawPicture(); }
  };

  // Shows one clip in this card.
  c.show = (clip, label, tone) => {
    tag.textContent = label;
    tag.className = 'tag st-' + tone;
    time.textContent = clip ? fmt.timeSec(toDate(clip.time)) : '';
    const url = clip && clip.has_audio ? audioUrl(clip) : null;
    if (url !== c.url) {
      if (!audio.paused) audio.pause();
      SonaraSpectro.setLine(pic, null);
      c.url = url;
      if (url) audio.src = url; else audio.removeAttribute('src');
      if (!url) { c.drawn = null; pic.msg.hidden = false; pic.msg.textContent = 'Recording not available'; }
    }
    setBtn();
    c.drawPicture();
  };
  soundCards.add(c);
  return c;
}

// Sound pictures on or off (off at first, so the page stays simple).
function setPictures(on) {
  state.pictures = on;
  document.body.classList.toggle('pics-off', !on);
  document.querySelectorAll('.pics-toggle').forEach((b) => {
    const plural = b.closest('[data-view="sounds"]') ? 's' : '';
    b.textContent = (on ? 'Hide' : 'Show') + ' sound picture' + plural;
  });
  try { localStorage.setItem('sonara-pictures', on ? '1' : '0'); } catch (e) { /* storage blocked */ }
  soundCards.forEach((c) => { if (!c.el.isConnected) soundCards.delete(c); else c.drawPicture(); });
}

// A normal sound from the same recording to compare with: not flagged, a low score, and
// about as loud as the unusual sound. Prefers one not used yet.
function normalFor(clip, rows, used) {
  let pool = rows.filter((c) => c.usable && !c.flagged && c.has_audio && c.probability < 0.2);
  if (!pool.length) pool = rows.filter((c) => c.usable && !c.flagged && c.has_audio);
  if (!pool.length) return null;
  const fresh = pool.filter((c) => !used.has(c.file));
  if (fresh.length) pool = fresh;
  return pool.reduce((best, c) => {
    const d = Math.abs((c.level_db ?? 0) - (clip.level_db ?? 0));
    return !best || d < best.d ? { c, d } : best;
  }, null).c;
}

function drawSounds(info) {
  stopAllSounds();
  soundCards.forEach((c) => { if (c !== replayCard) soundCards.delete(c); });
  const rows = info.flagged;
  $('flag-empty').hidden = rows.length > 0;
  const ul = $('sounds');
  ul.hidden = rows.length === 0;
  const used = new Set();
  ul.replaceChildren(...rows.map((r) => {
    const li = el('li', 'pair');
    const grid = el('div', 'pair-grid');
    const odd = soundCard();
    grid.appendChild(odd.el);
    odd.show(r, 'Unusual sound', 'alert');
    const n = normalFor(r, info.rows, used);
    if (n) {
      used.add(n.file);
      const ok = soundCard();
      grid.appendChild(ok.el);
      ok.show(n, 'Normal sound, same pen', 'normal');
    }
    li.appendChild(grid);
    return li;
  }));
  if (state.view === 'sounds') soundCards.forEach((c) => c.drawPicture());
}

// The sound card on the Zone Replay page follows the slider.
const replayCard = soundCard();
$('replay-sound').appendChild(replayCard.el);
function updateReplaySound() {
  const r = sessionClips()[state.idx];
  if (!r) return;
  if (!r.usable) replayCard.show(r, 'Not received clearly', 'none');
  else if (r.flagged) replayCard.show(r, 'Unusual sound', 'alert');
  else replayCard.show(r, 'Normal sound', 'normal');
}

// ---------------------------------------------------------------- controls

function stopReplay() {
  if (state.timer) { clearInterval(state.timer); state.timer = null; }
  $('play').textContent = 'Play';
}

function moveReplay(i) {
  state.idx = i;
  drawReplay();
  drawStrip();
}

$('slider').addEventListener('input', (e) => { stopReplay(); moveReplay(Number(e.target.value)); });

$('play').addEventListener('click', () => {
  if (state.timer) { stopReplay(); return; }
  if (!sessionClips().length) return;
  if (state.idx >= sessionClips().length - 1) state.idx = 0;
  $('play').textContent = 'Pause';
  state.timer = setInterval(() => {
    if (state.idx >= sessionClips().length - 1) { stopReplay(); return; }
    moveReplay(state.idx + 1);
  }, 220);
});

$('listen').addEventListener('click', () => { stopReplay(); replayCard.play(); });
document.querySelectorAll('.pics-toggle').forEach((b) => b.addEventListener('click', () => setPictures(!state.pictures)));
let savedPictures = null;
try { savedPictures = localStorage.getItem('sonara-pictures'); } catch (e) { /* ignore */ }
setPictures(savedPictures === '1');

$('recording').addEventListener('change', (e) => selectSession(e.target.value));
$('refresh').addEventListener('click', load);
$('activity-toggle').addEventListener('click', () => {
  state.showAllActivity = !state.showAllActivity;
  drawActivity(summarize(currentSession()));
});

function applyTheme(t) {
  document.documentElement.dataset.theme = t;
}
$('theme').addEventListener('click', () => {
  const next = document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark';
  applyTheme(next);
  try { localStorage.setItem('sonara-theme', next); } catch (e) { /* storage blocked */ }
  if (state.data) drawAll();
});
let savedTheme = null;
try { savedTheme = localStorage.getItem('sonara-theme'); } catch (e) { /* ignore */ }
applyTheme(savedTheme || (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'));

let resizeTimer = null;
window.addEventListener('resize', () => {
  clearTimeout(resizeTimer);
  resizeTimer = setTimeout(() => { if (state.data) drawStrip(); }, 150);
});

showView(location.hash.slice(1));
load();
