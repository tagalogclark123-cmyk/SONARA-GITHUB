#!/usr/bin/env python3
"""
SONARA - field session report (runs on the Raspberry Pi).

Classifies every node clip recorded during a field session and writes a report you can share.

What it does
  1. Classifies each clip with the system model (same model, threshold and zone rule as sonara_classify.py).
  2. Checks audio quality of each clip (too quiet, clipped, lost packets, how the sound energy is spread
     over low/mid/high frequencies compared with the SmartEars training clips).
  3. Writes a report folder:
       summary.txt          the summary (also printed on screen)
       report.html          the same summary with a timeline chart; open it in any browser
       clips.csv            one row per clip: time, node, probability, flag, audio-quality numbers
       review/              a BLIND listening set: the most strongly flagged clips plus a random sample of
                            not-flagged clips, renamed review_001.wav, ... in shuffled order
       review/review_sheet.csv   for the listener(s): write what you hear, without seeing the model's answer
       review_key.csv       which review file is which clip and what the model said (keep it closed until
                            the listening is done; it is deliberately outside the review folder)
       field_notes.csv      template for what you SEE in each zone during the session (fill it in on site)

Usage (on the Pi)
  ~/sonara-env/bin/python sonara_field_report.py                       clips in ~/sonara_clips, report named by date
  ~/sonara-env/bin/python sonara_field_report.py ~/field_day1 --name claveria_day1 --site "USTP Claveria, house 2"
  options:
    --zones "1=House 2 north,2=House 2 south"   names for the nodes' zones
    --since "2026-10-22 13:00"  --until "2026-10-22 15:30"   only clips in this time range
    --target 0.95               use the 95%-recall operating point instead of 0.90
    --review 15                 how many flagged and how many not-flagged clips go in the listening set

Needs in the same folder as this script: sonara_system_model.pt, deployment_config.json (already on the Pi).
Running it again on the same folder is fast: clips already classified are taken from clips.csv.

Important: there is no ground truth for field clips, so this report CANNOT give accuracy or recall.
"Flagged" means the model found acoustic patterns similar to the respiratory-distress clips it was
trained on. It is a screening signal for closer observation, not a diagnosis, and the share of flagged
clips is not the share of sick birds. The replay test (19 Oct) showed the model can miss distress sounds
when the recording chain changes the sound's frequency balance, so a low flag rate does not prove the
flock is healthy either.
"""
import argparse
import csv
import glob
import html
import json
import math
import os
import random
import re
import shutil
import sys
import time
import wave
from collections import defaultdict, deque
from datetime import datetime

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
SR, N = 16000, 80000
CYCLE_S = 30                   # the node sends one 5-s clip every 30 s
PACKET_SAMPLES = 120           # 240 bytes of audio per ESP-NOW packet; a lost packet becomes 120 zeros
BANDS = [(20, 250), (250, 1000), (1000, 4000), (4000, 8000)]
BAND_NAMES = ["<250 Hz", "250-1k", "1k-4k", "4k-8k"]
# Share of sound energy per band (median over 40 random clips per class from the SmartEars locked test set,
# resampled to 16 kHz exactly like the model input). Measured by Claude, 22 Oct 2026. Reference only.
SMARTEARS_REF = {"Healthy": [73.6, 12.1, 11.5, 0.9], "Sick": [94.9, 3.3, 1.8, 0.3], "None": [82.8, 11.5, 3.0, 0.6]}
MAX_LOST_PACKETS = 33          # a clip missing more than 5% of its 667 packets is "damaged": left out of all statistics
QUIET_DB = -60.0               # in-band (200-4000 Hz) level below this: probably nothing audible near the mic
CLIP_LEVEL = 32700


# ----------------------------------------------------------------------------- audio helpers
def read_clip(path):
    with wave.open(path, "rb") as w:
        if w.getframerate() != SR or w.getsampwidth() != 2:
            raise ValueError(f"expected 16 kHz 16-bit, got {w.getframerate()} Hz {8 * w.getsampwidth()}-bit")
        raw = np.frombuffer(w.readframes(w.getnframes()), "<i2")
        if w.getnchannels() > 1:
            raw = raw.reshape(-1, w.getnchannels()).mean(1).astype(np.int16)
    return raw


def band_filter(x, lo, hi):
    """Simple FFT band-pass (no scipy needed)."""
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / SR)
    X[(f < lo) | (f >= hi)] = 0
    return np.fft.irfft(X, len(x))


def quality(raw):
    x = raw.astype(np.float64) / 32768.0
    x = x - x.mean()
    q = {}
    q["peak"] = int(np.abs(raw.astype(np.int32)).max()) if len(raw) else 0
    q["clipped_pct"] = round(100.0 * float(np.mean(np.abs(raw.astype(np.int32)) >= CLIP_LEVEL)), 3)
    inband = band_filter(x, 200, 4000)
    q["level_db"] = round(20 * math.log10(math.sqrt(float(np.mean(inband ** 2))) + 1e-12), 1)
    # lost packets: runs of exact zeros at least one packet long
    z = np.flatnonzero(np.diff(np.r_[0, (raw == 0).astype(np.int8), 0]))
    runs = z[1::2] - z[0::2]
    q["lost_packets_est"] = int(np.sum(runs[runs >= PACKET_SAMPLES] // PACKET_SAMPLES))
    q["short_clip"] = int(len(raw) < N)
    P = np.abs(np.fft.rfft(x)) ** 2
    f = np.fft.rfftfreq(len(x), 1 / SR)
    e = np.array([P[(f >= a) & (f < b)].sum() for a, b in BANDS])
    share = 100 * e / max(e.sum(), 1e-20)
    for name, s in zip(["band_low_pct", "band_lowmid_pct", "band_mid_pct", "band_high_pct"], share):
        q[name] = round(float(s), 1)
    return q


def file_time(path):
    m = re.search(r"_(\d{8}-\d{6})\.wav$", path)
    if m:
        return datetime.strptime(m.group(1), "%Y%m%d-%H%M%S")
    return datetime.fromtimestamp(os.path.getmtime(path))


def node_of(path):
    m = re.match(r"node(\d+)_clip(\d+)", os.path.basename(path))
    return (int(m.group(1)), int(m.group(2))) if m else (0, -1)


# ----------------------------------------------------------------------------- model
class Model:
    def __init__(self, target):
        import torch
        self.torch = torch
        for p in ("sonara_system_model.pt", "deployment_config.json"):
            if not os.path.exists(os.path.join(HERE, p)):
                sys.exit(f"Missing {p}. Put it in the same folder as this script: {HERE}")
        cfg = json.load(open(os.path.join(HERE, "deployment_config.json")))
        key = f"{target:.2f}"
        if key not in cfg["operating_points"]:
            sys.exit(f"No operating point {key} in deployment_config.json ({list(cfg['operating_points'])})")
        op = cfg["operating_points"][key]
        self.key, self.threshold = key, float(op["threshold"])
        self.window = int(op["alert_rule"]["window_clips"])
        self.needed = math.ceil(float(op["alert_rule"]["share_flagged"]) * self.window)
        self.desc = f"{cfg.get('setup', 'system model')}, seed {cfg.get('seed', '?')}"
        torch.set_num_threads(4)
        import warnings
        warnings.filterwarnings("ignore")
        self.net = torch.jit.load(os.path.join(HERE, "sonara_system_model.pt"), map_location="cpu").eval()

    def prob(self, raw):
        x = raw.astype(np.float32) / 32768.0
        x = np.pad(x, (0, max(0, N - len(x))))[:N]
        with self.torch.no_grad():
            t0 = time.perf_counter()
            p = float(self.net(self.torch.from_numpy(np.ascontiguousarray(x)).unsqueeze(0)).reshape(-1)[0])
            return p, (time.perf_counter() - t0) * 1000


# ----------------------------------------------------------------------------- report helpers
def pct(a, b):
    return f"{100.0 * a / b:.1f}%" if b else "n/a"


def text_hist(values, edges, width=40):
    counts = np.histogram(values, bins=edges)[0]
    top = max(counts.max(), 1)
    lines = []
    for lo, hi, c in zip(edges[:-1], edges[1:], counts):
        lines.append(f"   {lo:4.2f}-{hi:4.2f} | {'#' * int(round(width * c / top)):<{width}} {c}")
    return lines


def alert_episodes(rows, window, needed):
    """Applies the zone rule clip by clip per node; returns list of (node, start_time, end_time, peak_count)."""
    eps = []
    by_node = defaultdict(list)
    for r in rows:
        by_node[r["node"]].append(r)
    for node, rs in by_node.items():
        h = deque(maxlen=window)
        cur = None
        for r in rs:
            h.append(r["flagged"])
            c = sum(h)
            if c >= needed:
                if cur is None:
                    cur = [node, r["time"], r["time"], c]
                cur[2], cur[3] = r["time"], max(cur[3], c)
            elif cur is not None:
                eps.append(tuple(cur))
                cur = None
        if cur is not None:
            eps.append(tuple(cur))
    return sorted(eps, key=lambda e: e[1])


def svg_timeline(rows, thr, zone_name):
    """Probability of every clip over time, one colour per node, with the threshold line."""
    if not rows:
        return ""
    W, H, L, R, T, B = 900, 300, 50, 20, 20, 40
    t0 = min(r["time"] for r in rows).timestamp()
    t1 = max(r["time"] for r in rows).timestamp()
    span = max(t1 - t0, 60)
    colors = ["#2a6fdb", "#d9822b", "#1f9e6e", "#a347ba", "#c23b3b", "#6b7280"]
    nodes = sorted({r["node"] for r in rows})
    X = lambda t: L + (W - L - R) * (t - t0) / span
    Y = lambda p: T + (H - T - B) * (1 - p)
    s = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="Model probability per clip over time">']
    for p in (0, 0.25, 0.5, 0.75, 1.0):
        s.append(f'<line x1="{L}" x2="{W - R}" y1="{Y(p):.1f}" y2="{Y(p):.1f}" class="grid"/>'
                 f'<text x="{L - 6}" y="{Y(p) + 4:.1f}" text-anchor="end" class="ax">{p:.2f}</text>')
    s.append(f'<line x1="{L}" x2="{W - R}" y1="{Y(thr):.1f}" y2="{Y(thr):.1f}" class="thr"/>'
             f'<text x="{W - R}" y="{Y(thr) - 5:.1f}" text-anchor="end" class="thrt">threshold {thr}</text>')
    for k in range(5):
        t = t0 + span * k / 4
        s.append(f'<text x="{X(t):.1f}" y="{H - 15}" text-anchor="middle" class="ax">'
                 f'{datetime.fromtimestamp(t).strftime("%H:%M")}</text>')
    for i, n in enumerate(nodes):
        c = colors[i % len(colors)]
        for r in rows:
            if r["node"] == n:
                s.append(f'<circle cx="{X(r["time"].timestamp()):.1f}" cy="{Y(r["p"]):.1f}" r="2.6" fill="{c}">'
                         f'<title>{html.escape(r["file"])}  p={r["p"]:.3f}</title></circle>')
        s.append(f'<rect x="{L + 10 + 160 * i}" y="{H - 10}" width="10" height="10" fill="{c}"/>'
                 f'<text x="{L + 25 + 160 * i}" y="{H - 1}" class="ax">{html.escape(zone_name(n))}</text>')
    s.append("</svg>")
    return "\n".join(s)


# ----------------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser(description="SONARA field session report")
    ap.add_argument("folder", nargs="?", default="~/sonara_clips")
    ap.add_argument("--name", default=None, help="report name (default: date of the first clip)")
    ap.add_argument("--site", default="", help="where the session was recorded")
    ap.add_argument("--zones", default="", help='e.g. "1=House 2 north,2=House 2 south"')
    ap.add_argument("--since", default=None, help='"YYYY-mm-dd HH:MM"')
    ap.add_argument("--until", default=None, help='"YYYY-mm-dd HH:MM"')
    ap.add_argument("--target", type=float, default=0.90)
    ap.add_argument("--review", type=int, default=15)
    ap.add_argument("--out", default="~/sonara_reports")
    a = ap.parse_args()

    folder = os.path.expanduser(a.folder)
    files = sorted(glob.glob(os.path.join(folder, "node*_clip*.wav")), key=lambda p: (file_time(p), p))
    if a.since:
        files = [f for f in files if file_time(f) >= datetime.strptime(a.since, "%Y-%m-%d %H:%M")]
    if a.until:
        files = [f for f in files if file_time(f) <= datetime.strptime(a.until, "%Y-%m-%d %H:%M")]
    if not files:
        sys.exit(f"No node clips found in {folder} (for the chosen time range).")

    zones = {}
    for part in filter(None, a.zones.split(",")):
        k, v = part.split("=", 1)
        zones[int(k.strip())] = v.strip()
    zone_name = lambda n: zones.get(n, f"node {n}")

    name = a.name or file_time(files[0]).strftime("field_%Y%m%d")
    out = os.path.join(os.path.expanduser(a.out), name)
    os.makedirs(out, exist_ok=True)
    csv_path = os.path.join(out, "clips.csv")

    model = Model(a.target)
    cache = {}
    if os.path.exists(csv_path):
        for r in csv.DictReader(open(csv_path)):
            if r.get("threshold") == str(model.threshold):
                cache[(r["file"], r["bytes"])] = r

    print(f"{len(files)} clips in {folder}. Model: {model.desc}; operating point {model.key} recall, "
          f"threshold {model.threshold}; zone alert at {model.needed} of {model.window} clips.\n", flush=True)

    fields = ["time", "file", "node", "zone", "clip_id", "bytes", "probability", "threshold", "flagged", "inference_ms",
              "level_db", "peak", "clipped_pct", "lost_packets_est", "short_clip",
              "band_low_pct", "band_lowmid_pct", "band_mid_pct", "band_high_pct", "usable", "error"]
    rows, errors = [], []
    t_start = time.time()
    for k, path in enumerate(files, 1):
        base, size = os.path.basename(path), str(os.path.getsize(path))
        node, cid = node_of(path)
        c = cache.get((base, size))
        if c and not c.get("error"):
            r = dict(c)
        else:
            r = {"time": file_time(path).isoformat(sep=" "), "file": base, "node": node, "zone": zone_name(node),
                 "clip_id": cid, "bytes": size, "threshold": model.threshold, "error": ""}
            try:
                raw = read_clip(path)
                r.update(quality(raw))
                p, ms = model.prob(raw)
                r.update(probability=round(p, 5), flagged=int(p >= model.threshold), inference_ms=round(ms, 1))
            except Exception as e:  # damaged file: keep a row so it shows up in the report
                r["error"] = str(e)[:120]
        r["zone"] = zone_name(node)
        if not r.get("error"):
            r["usable"] = int(int(float(r["lost_packets_est"])) <= MAX_LOST_PACKETS)
        rows.append(r)
        if k % 50 == 0 or k == len(files):
            print(f"  {k}/{len(files)} clips ({time.time() - t_start:.0f} s)", flush=True)

    with open(csv_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)

    good = []
    for r in rows:
        if r.get("error"):
            errors.append(r)
            continue
        good.append({"time": datetime.fromisoformat(str(r["time"])), "file": r["file"], "node": int(r["node"]),
                     "p": float(r["probability"]), "flagged": int(r["flagged"]), "ms": float(r["inference_ms"]),
                     "level": float(r["level_db"]), "peak": int(float(r["peak"])), "clip": float(r["clipped_pct"]),
                     "lost": int(float(r["lost_packets_est"])),
                     "bands": [float(r[b]) for b in ["band_low_pct", "band_lowmid_pct", "band_mid_pct", "band_high_pct"]]})
    if not good:
        sys.exit("No clip could be read.")
    good.sort(key=lambda r: r["time"])
    thr = model.threshold
    t_first, t_last = good[0]["time"], good[-1]["time"]
    dur_s = (t_last - t_first).total_seconds() + CYCLE_S
    nodes = sorted({r["node"] for r in good})

    L = []  # summary lines
    L.append("SONARA FIELD SESSION REPORT")
    L.append("=" * 60)
    L.append(f"Report:   {name}" + (f"   Site: {a.site}" if a.site else ""))
    allr = good
    usable = [r for r in allr if r["lost"] <= MAX_LOST_PACKETS]
    L.append(f"Session:  {t_first:%Y-%m-%d %H:%M} to {t_last:%H:%M} ({dur_s / 3600:.1f} h), {len(allr)} clips, "
             f"{len(usable)} usable (damaged = more than {MAX_LOST_PACKETS} of 667 radio packets lost)"
             + (f", {len(errors)} unreadable" if errors else ""))
    L.append(f"Model:    {model.desc}; {model.key}-recall operating point, threshold {thr}; "
             f"zone alert when {model.needed} of the last {model.window} clips are flagged")
    L.append("")
    L.append("1. RECORDING COVERAGE AND AUDIO QUALITY")
    for n in nodes:
        R = [r for r in allr if r["node"] == n]
        span = (R[-1]["time"] - R[0]["time"]).total_seconds() + CYCLE_S
        exp = max(int(round(span / CYCLE_S)), 1)
        Ru = [r for r in R if r["lost"] <= MAX_LOST_PACKETS] or R   # levels only from undamaged clips
        quiet = sum(r["level"] < QUIET_DB for r in Ru)
        clipped = sum(r["clip"] > 0.1 for r in R)
        lost = sum(r["lost"] > 0 for r in R)
        L.append(f"   {zone_name(n)}: {len(R)} clip(s) of about {exp} expected ({pct(len(R), exp)}), "
                 f"{R[0]['time']:%H:%M}-{R[-1]['time']:%H:%M}")
        L.append(f"      level of undamaged clips (200-4000 Hz): median {np.median([r['level'] for r in Ru]):.1f} dBFS "
                 f"(10th-90th pct {np.percentile([r['level'] for r in Ru], 10):.1f} to "
                 f"{np.percentile([r['level'] for r in Ru], 90):.1f}); median peak {int(np.median([r['peak'] for r in Ru]))}")
        L.append(f"      very quiet undamaged clips (< {QUIET_DB:.0f} dBFS): {quiet}   clipped (>0.1% of samples): {clipped}   "
                 f"with lost packets: {lost}")
        dmg = [r for r in R if r["lost"] > MAX_LOST_PACKETS]
        if dmg:
            empty = sum(r["lost"] >= 660 for r in dmg)
            L.append(f"      ! DAMAGED clips (> {MAX_LOST_PACKETS} packets lost): {len(dmg)} of {len(R)}, of which {empty} almost "
                     f"empty; first {dmg[0]['time']:%H:%M}, last {dmg[-1]['time']:%H:%M}. Left out of everything below.")
    good = usable
    if not good:
        sys.exit("No usable clips (all damaged by lost packets).")
    L.append(f"   Everything below uses the {len(good)} usable clips only.")
    bands = np.array([r["bands"] for r in good])
    L.append("   Where the sound energy is (median share per band, all clips) vs SmartEars training clips:")
    L.append("      " + "".join(f"{b:>10}" for b in BAND_NAMES))
    L.append("      " + "".join(f"{v:>9.1f}%" for v in np.median(bands, 0)) + "   this session")
    for cls, ref in SMARTEARS_REF.items():
        L.append("      " + "".join(f"{v:>9.1f}%" for v in ref) + f"   SmartEars {cls}")
    low = float(np.median(bands[:, 0]))
    if low < 50:
        L.append(f"   ! Only {low:.0f}% of the energy is below 250 Hz (SmartEars clips: 74-95%). The frequency balance")
        L.append("     differs strongly from the training data; the replay test showed this alone can make the model")
        L.append("     miss distress sounds. Treat the flag counts below with extra caution.")
    if errors:
        L.append(f"   Unreadable files: {', '.join(r['file'] for r in errors[:5])}{' ...' if len(errors) > 5 else ''}")
    L.append("")

    L.append("2. MODEL OUTPUT")
    ps = np.array([r["p"] for r in good])
    fl = np.array([r["flagged"] for r in good])
    L.append(f"   Flagged clips: {fl.sum()} of {len(good)} ({pct(fl.sum(), len(good))})")
    for n in nodes:
        m = np.array([r["node"] == n for r in good])
        L.append(f"      {zone_name(n)}: {fl[m].sum()} of {m.sum()} ({pct(fl[m].sum(), m.sum())}), "
                 f"median probability {np.median(ps[m]):.3f}")
    L.append("   Probability distribution (all clips):")
    L += text_hist(ps, np.array([0, .1, .2, .3, .4, .5, thr, .6, .7, .8, .9, 1.0001]))
    near = int(((ps >= thr - 0.1) & (ps < thr + 0.1)).sum())
    L.append(f"   Clips within 0.10 of the threshold (borderline): {near}")
    L.append("")
    L.append("   By 30-minute block:")
    L.append("      time    " + "".join(f"{zone_name(n)[:14]:>16}" for n in nodes))
    blocks = defaultdict(lambda: defaultdict(list))
    for r in good:
        b = r["time"].replace(minute=(r["time"].minute // 30) * 30, second=0, microsecond=0)
        blocks[b][r["node"]].append(r["flagged"])
    for b in sorted(blocks):
        cells = []
        for n in nodes:
            v = blocks[b][n]
            cells.append(f"{sum(v):>5}/{len(v):<3} {('(' + pct(sum(v), len(v)) + ')') if v else '':>7}")
        L.append(f"      {b:%H:%M}   " + " ".join(f"{c:>15}" for c in cells))
    L.append("")
    eps = alert_episodes(good, model.window, model.needed)
    L.append(f"3. ZONE ALERTS (rule: {model.needed} of the last {model.window} clips flagged, per node)")
    if not eps:
        L.append("   No zone alert during this session.")
    for node, s0, s1, c in eps:
        L.append(f"   {zone_name(node)}: alert from {s0:%H:%M:%S} to {s1:%H:%M:%S} (up to {c} of {model.window} flagged)")
    L.append("")
    L.append("4. MOST STRONGLY FLAGGED CLIPS (listen to these first)")
    for r in sorted(good, key=lambda r: -r["p"])[:10]:
        if r["p"] < thr:
            break
        L.append(f"   {r['time']:%H:%M:%S}  {zone_name(r['node']):<16} p={r['p']:.3f}  level {r['level']:.0f} dBFS  {r['file']}")
    if fl.sum() == 0:
        L.append("   (no flagged clips)")
    ms = np.array([r["ms"] for r in good])
    L.append("")
    L.append(f"5. SPEED: inference per clip on the machine that ran this report: median {np.median(ms):.0f} ms, 95th percentile {np.percentile(ms, 95):.0f} ms")
    L.append("")

    # ---- blind review set
    rv_dir = os.path.join(out, "review")
    if os.path.isdir(rv_dir):
        shutil.rmtree(rv_dir)
    os.makedirs(rv_dir)
    rng = random.Random(2026)
    flagged_top = sorted([r for r in good if r["flagged"]], key=lambda r: -r["p"])[:a.review]
    pool = [r for r in good if not r["flagged"] and r["level"] >= QUIET_DB] or [r for r in good if not r["flagged"]]
    calm = rng.sample(pool, min(a.review, len(pool)))
    picks = [(r, "flagged") for r in flagged_top] + [(r, "not flagged") for r in calm]
    rng.shuffle(picks)
    with open(os.path.join(rv_dir, "review_sheet.csv"), "w", newline="") as f1, \
            open(os.path.join(out, "review_key.csv"), "w", newline="") as f2:
        w1, w2 = csv.writer(f1), csv.writer(f2)
        w1.writerow(["review_file", "what_you_hear (normal / possible_distress / noise_only / unsure)",
                     "what sound (e.g. gasp, rale, cough, sneeze, fan, people)", "confidence (1-3)", "listener", "notes"])
        w2.writerow(["review_file", "original_file", "time", "zone", "probability", "model_said"])
        for i, (r, said) in enumerate(picks, 1):
            nm = f"review_{i:03d}.wav"
            shutil.copy2(os.path.join(folder, r["file"]), os.path.join(rv_dir, nm))
            w1.writerow([nm, "", "", "", "", ""])
            w2.writerow([nm, r["file"], r["time"].isoformat(sep=" "), zone_name(r["node"]), round(r["p"], 4), said])
    L.append(f"6. BLIND LISTENING SET: {len(picks)} clips in review/ ({len(flagged_top)} flagged, {len(calm)} not flagged, shuffled).")
    L.append("   Listen and fill in review/review_sheet.csv WITHOUT opening review_key.csv. Ideally have a veterinarian")
    L.append("   or experienced poultry worker listen too. Then compare with review_key.csv.")
    L.append("")

    notes_path = os.path.join(out, "field_notes.csv")
    if not os.path.exists(notes_path):
        with open(notes_path, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["time (HH:MM)", "zone / node", "birds in zone (approx)", "age / breed",
                        "signs seen (none / sneezing / coughing / gasping / open-mouth breathing / nasal discharge / "
                        "swollen face / watery eyes / lethargy / other)", "how many birds show signs",
                        "noise sources (fans, people, feeding, rain, machines)", "mic distance to nearest birds (m)",
                        "observer", "notes"])
            for n in nodes:
                w.writerow(["", zone_name(n), "", "", "", "", "", "", "", ""])

    L.append("HOW TO READ THIS REPORT")
    L.append("   - There is no ground truth for these clips, so this report gives no accuracy or recall.")
    L.append("   - 'Flagged' = acoustic patterns similar to the distress clips in the training data. It is a cue for")
    L.append("     closer observation, not a diagnosis, and the flagged share is not the share of sick birds.")
    L.append("   - A low flag rate does not prove the flock is healthy: the replay test showed the model can miss")
    L.append("     distress sounds when the microphone path changes the sound's frequency balance (see section 1).")
    L.append("   - Compare the flags with field_notes.csv (what people saw) and the blind listening results before")
    L.append("     drawing any conclusion.")
    summary = "\n".join(L)
    open(os.path.join(out, "summary.txt"), "w").write(summary + "\n")
    print("\n" + summary)

    # ---- HTML version
    page = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>SONARA field report</title>
<style>
:root{{--bg:#fbfaf7;--fg:#1d2430;--mut:#5b6472;--line:#d9dde3;--thr:#c23b3b;--card:#ffffff}}
@media (prefers-color-scheme:dark){{:root{{--bg:#14171c;--fg:#e6e8eb;--mut:#9aa3ae;--line:#323844;--thr:#ff6b6b;--card:#1b1f26}}}}
body{{background:var(--bg);color:var(--fg);font:15px/1.5 system-ui,sans-serif;margin:0;padding:24px 16px}}
main{{max-width:960px;margin:auto}} h1{{font-size:22px;margin:0 0 4px}} .mut{{color:var(--mut)}}
.card{{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:16px;margin:16px 0;overflow-x:auto}}
svg{{width:100%;height:auto}} .grid{{stroke:var(--line)}} .thr{{stroke:var(--thr);stroke-dasharray:5 4}}
.thrt{{fill:var(--thr);font-size:12px}} .ax{{fill:var(--mut);font-size:12px}}
pre{{font:12.5px/1.45 ui-monospace,Menlo,Consolas,monospace;white-space:pre;margin:0}}
</style></head><body><main>
<h1>SONARA field session: {html.escape(name)}</h1>
<div class="mut">{html.escape(a.site)} {t_first:%Y-%m-%d %H:%M} to {t_last:%H:%M} &middot; {len(good)} clips &middot;
screening signal only, not a diagnosis</div>
<div class="card"><b>Model probability for every clip</b> <span class="mut">(hover a dot for the file name)</span>
{svg_timeline(good, thr, zone_name)}</div>
<div class="card"><pre>{html.escape(summary)}</pre></div>
</main></body></html>"""
    open(os.path.join(out, "report.html"), "w").write(page)
    print(f"\nReport folder: {out}\n  summary.txt, report.html, clips.csv, field_notes.csv, review/ (+ review_key.csv)")


if __name__ == "__main__":
    main()
