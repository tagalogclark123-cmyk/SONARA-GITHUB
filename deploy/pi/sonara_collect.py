#!/usr/bin/env python3
"""
SONARA farm data collection (runs on the Raspberry Pi, with sonara_deploy_bridge on USB).

Saves EVERY clip from every node as a WAV file, with a CSV row per clip, and classifies each clip
in a separate low-priority process so the model never slows down the radio link.

Output (one folder per start):  ~/sonara_deploy/runs/<YYYYMMDD-HHMMSS>/
  clips/node<N>/node<N>_clip<ID>_<time>.wav   every clip (damaged ones too, marked in the CSV)
  clips.csv          one row per clip: node, times, packets lost, damaged, sound level, link numbers
  predictions.csv    one row per classified clip: probability, flagged, zone alert
  bridge.csv         bridge heartbeat every 5 s (alive, dropped packets)
  pi_health.csv      Pi temperature, throttling, disk, every minute
  summary.txt        rewritten every 10 min and at stop
  run_info.json      start time, clock sync state, settings
Field notes (sonara_note.py) go to ~/sonara_deploy/notes.csv for all runs.
Live view: tail -f ~/sonara_deploy/live.log

It NEVER deletes clips. If free disk space drops below MIN_FREE_GB it stops saving audio (the CSV keeps
counting) and says so in live.log.

Run by hand:   ~/sonara-env/bin/python sonara_collect.py [--port /dev/ttyUSB0] [--no-model]
Run as service: see SONARA_DEPLOY_GUIDE (sonara-collect.service).
"""
import argparse, csv, glob, json, os, queue, shutil, struct, subprocess, sys, threading, time, wave
from datetime import datetime

import numpy as np
import serial

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.expanduser("~/sonara_deploy")
BAUD = 921600
SR, CLIP_BYTES, DATA_MAX = 16000, 160000, 240
TOTAL_PKTS = (CLIP_BYTES + DATA_MAX - 1) // DATA_MAX          # 667
DAMAGED_LOST = 33                                              # > 5% of packets lost = damaged
CLIP_TIMEOUT_S = 3.0                                           # no packet for 3 s and no END -> close the clip
MIN_FREE_GB = 2.0
ALERT_K, ALERT_N = 8, 20                                       # zone alert: 8 of the last 20 usable clips flagged

HEADER = struct.Struct("<BBBHHHB")                             # audio packet header (10 bytes)
END = struct.Struct("<BBHIIBBHHHHHHHHIHH")                     # node END packet (38 bytes)
ENDB = struct.Struct("<HbbbIB")                                # bridge additions (10 bytes)
BEAT = struct.Struct("<BIIIIBBB")                              # bridge heartbeat (20 bytes)
RESET = {0: "unknown", 1: "power-on", 2: "external", 3: "software", 4: "crash", 5: "interrupt watchdog",
         6: "task watchdog", 7: "other watchdog", 8: "deep sleep", 9: "brownout (low power)", 10: "SDIO"}

ap = argparse.ArgumentParser()
ap.add_argument("--port", default=None)
ap.add_argument("--no-model", action="store_true")
args = ap.parse_args()

os.makedirs(BASE, exist_ok=True)
RUN = os.path.join(BASE, "runs", datetime.now().strftime("%Y%m%d-%H%M%S"))
os.makedirs(os.path.join(RUN, "clips"), exist_ok=True)
LIVE = open(os.path.join(BASE, "live.log"), "a", buffering=1)


def log(msg):
    line = f"{datetime.now():%m-%d %H:%M:%S} {msg}"
    print(line, flush=True)
    LIVE.write(line + "\n")


def sh(cmd):
    try:
        return subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=5).stdout.strip()
    except Exception:
        return ""


class CsvLog:
    """Append-only CSV that is flushed after every row (safe if the power is cut)."""
    def __init__(self, name, fields):
        path = os.path.join(RUN, name)
        new = not os.path.exists(path)
        self.f = open(path, "a", newline="", buffering=1)
        self.w = csv.DictWriter(self.f, fieldnames=fields, extrasaction="ignore")
        if new: self.w.writeheader()
    def row(self, r):
        self.w.writerow(r); self.f.flush()


CLIP_FIELDS = ["file", "node", "clip_id", "rec_start", "received", "got", "total", "lost", "damaged", "saved",
               "level_dbfs", "peak", "clipped", "bridge_rx", "rssi_avg", "rssi_min", "node_failed", "retries",
               "send_ms", "wait_ms", "node_uptime_s", "node_min_heap", "node_reset", "mic_ok", "batt_mv",
               "node_sent_clips", "node_dropped_clips", "bridge_drops_total", "end_received", "clock_synced"]
PRED_FIELDS = ["file", "node", "clip_id", "rec_start", "damaged", "p", "flagged", "inf_ms", "recent_flags",
               "zone_alert"]
clips_csv = CsvLog("clips.csv", CLIP_FIELDS)
pred_csv = CsvLog("predictions.csv", PRED_FIELDS)
bridge_csv = CsvLog("bridge.csv", ["time", "bridge_uptime_s", "queue_drops", "frames_out", "grants", "owner", "nodes_seen"])
health_csv = CsvLog("pi_health.csv", ["time", "temp_c", "throttled", "load_1min", "disk_free_gb", "clips_saved"])

clock_synced = sh("timedatectl show -p NTPSynchronized --value") == "yes"
json.dump(dict(started=datetime.now().isoformat(timespec="seconds"), clock_synced=clock_synced,
               boot_id=sh("cat /proc/sys/kernel/random/boot_id"), threshold_rule=f"{ALERT_K} of {ALERT_N}",
               damaged_rule=f"more than {DAMAGED_LOST} of {TOTAL_PKTS} packets lost", min_free_gb=MIN_FREE_GB),
          open(os.path.join(RUN, "run_info.json"), "w"), indent=2)


# ---------------- classifier in its own low-priority process ----------------
thr = None
cls_in = cls_out = None
if not args.no_model:
    worker = subprocess.Popen([sys.executable, "-u", os.path.join(HERE, "sonara_classify_worker.py"), HERE],
                              stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, bufsize=1)
    cls_out = queue.Queue()

    class _In:
        def put(self, job):
            try:
                worker.stdin.write(f"{job[0]}\t{job[1][0]},{job[1][1]}\n"); worker.stdin.flush()
            except Exception as e:
                log(f"!! classifier stopped ({e})")
    cls_in = _In()

    def _read_worker():
        for line in worker.stdout:
            try:
                m = json.loads(line)
            except ValueError:
                continue
            if m[0] in ("result", "fail"):
                m[1] = tuple(int(v) for v in m[1].split(","))
            cls_out.put(m)
        cls_out.put(["error", "classifier process ended"])
    threading.Thread(target=_read_worker, daemon=True).start()


# ---------------- serial reader thread (does nothing but read) ----------------
raw_q = queue.Queue()
port_state = {"open": False, "name": None}


def find_port():
    if args.port: return args.port
    c = sorted(glob.glob("/dev/serial/by-id/*")) + sorted(glob.glob("/dev/ttyUSB*")) + sorted(glob.glob("/dev/ttyACM*"))
    return c[0] if c else None


def reader():
    warned = 0; lost_warned = 0
    while True:
        name = find_port()
        if not name:
            if time.time() - warned > 60: log("!! bridge not found on USB. Is it plugged in?"); warned = time.time()
            time.sleep(2); continue
        try:
            ser = serial.Serial(name, BAUD, timeout=0.05)
            port_state.update(open=True, name=name)
            log(f"bridge connected on {name}")
            while True:
                d = ser.read(ser.in_waiting or 1)
                if d: raw_q.put(d)
        except Exception as e:
            if port_state["open"] or time.time() - lost_warned > 60:
                log(f"!! bridge connection lost or not available ({e.__class__.__name__}); retrying every 2 s")
                lost_warned = time.time()
            port_state["open"] = False
            try: ser.close()
            except Exception: pass
            time.sleep(2)


threading.Thread(target=reader, daemon=True).start()


# ---------------- framing ----------------
class Parser:
    def __init__(self): self.buf = bytearray(); self.bad = 0
    def feed(self, data):
        self.buf += data; out = []
        while True:
            i = self.buf.find(b"\xAA\x55")
            if i < 0:
                self.buf = bytearray(b"\xAA") if self.buf[-1:] == b"\xAA" else bytearray(); break
            if i: del self.buf[:i]
            if len(self.buf) < 3: break
            n = self.buf[2]
            if len(self.buf) < n + 4: break
            p = bytes(self.buf[3:3 + n])
            if (sum(p) & 0xFF) != self.buf[3 + n]:
                self.bad += 1; del self.buf[:2]; continue
            del self.buf[:n + 4]; out.append(p)
        return out


# ---------------- state ----------------
open_clips = {}           # (node, clip_id) -> dict(chunks, first, last)
closed = {}               # (node, clip_id) -> time closed (late END packets are ignored)
mic_warned = {}
pending = {}              # (node, clip_id) -> info for live line, waiting for the classifier
recent = {}               # node -> list of last flags (usable clips)
alert_on = {}
stats = dict(saved=0, damaged=0, unsaved_disk=0, flagged=0, classified=0, per_node={}, bridge_drops=0,
             bridge_last=0.0, bridge_up=0, resets=[], bad_frames=0)
last_uptime = {}
t_start = time.time()
disk_warned = 0.0


def node_stats(n):
    return stats["per_node"].setdefault(n, dict(clips=0, damaged=0, flagged=0, classified=0, last=0.0, level=[]))


def audio_metrics(raw16):
    x = raw16.astype(np.float64) / 32768.0
    X = np.fft.rfft(x - x.mean())
    f = np.fft.rfftfreq(len(x), 1 / SR)
    band = (f >= 200) & (f <= 4000)
    pw = 2 * np.sum(np.abs(X[band]) ** 2) / len(x) ** 2          # mean power in 200-4000 Hz
    lvl = 10 * np.log10(pw + 1e-14)
    a = np.abs(raw16.astype(np.int32))
    return round(float(lvl), 1), int(a.max()) if len(a) else 0, int(np.sum(a >= 32767))


def close_clip(key, end=None):
    global disk_warned
    c = open_clips.pop(key)
    node, cid = key
    closed[key] = time.time()
    audio = bytearray(CLIP_BYTES)
    for idx, d in c["chunks"].items():
        off = idx * DATA_MAX
        if off + len(d) <= CLIP_BYTES: audio[off:off + len(d)] = d
    got = len(c["chunks"]); lost = TOTAL_PKTS - got; damaged = int(lost > DAMAGED_LOST)
    received = datetime.fromtimestamp(c["last"])
    if end is not None:
        rec_start = datetime.fromtimestamp(time.time() - end["rec_age_ms"] / 1000.0)
    else:
        rec_start = datetime.fromtimestamp(c["first"] - 5.0)       # estimate: send starts right after recording
    raw16 = np.frombuffer(bytes(audio), "<i2")
    lvl, peak, clipped = audio_metrics(raw16)
    ndir = os.path.join(RUN, "clips", f"node{node}")
    os.makedirs(ndir, exist_ok=True)
    fname = f"node{node}_clip{cid:05d}_{rec_start:%Y%m%d-%H%M%S}.wav"
    path = os.path.join(ndir, fname)
    free_gb = shutil.disk_usage(RUN).free / 1e9
    saved = free_gb >= MIN_FREE_GB
    if saved:
        with wave.open(path, "wb") as w:
            w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes(bytes(audio))
        stats["saved"] += 1
    else:
        stats["unsaved_disk"] += 1
        if time.time() - disk_warned > 600:
            log(f"!! DISK NEARLY FULL ({free_gb:.1f} GB free): clips are NOT being saved. Copy data off the Pi.")
            disk_warned = time.time()
    ns = node_stats(node); ns["clips"] += 1; ns["damaged"] += damaged; ns["last"] = time.time()
    ns["level"] = (ns["level"] + [lvl])[-200:]
    stats["damaged"] += damaged
    e = end or {}
    if end is not None and node in last_uptime and e["uptime_s"] < last_uptime[node]:
        why = RESET.get(e["reset_reason"], str(e["reset_reason"]))
        stats["resets"].append(f"{datetime.now():%m-%d %H:%M} node {node}: {why}")
        log(f"!! node {node} restarted (reason: {why})")
    if end is not None: last_uptime[node] = e["uptime_s"]
    clips_csv.row(dict(file=fname if saved else "", node=node, clip_id=cid, rec_start=f"{rec_start:%Y-%m-%d %H:%M:%S}",
                       received=f"{received:%Y-%m-%d %H:%M:%S}", got=got, total=TOTAL_PKTS, lost=lost, damaged=damaged,
                       saved=int(saved), level_dbfs=lvl, peak=peak, clipped=clipped,
                       bridge_rx=e.get("bridge_rx", ""), rssi_avg=e.get("rssi_avg", ""), rssi_min=e.get("rssi_min", ""),
                       node_failed=e.get("failed", ""), retries=e.get("retries", ""), send_ms=e.get("send_ms", ""),
                       wait_ms=e.get("wait_ms", ""), node_uptime_s=e.get("uptime_s", ""), node_min_heap=e.get("min_heap", ""),
                       node_reset=RESET.get(e["reset_reason"], "") if end else "", mic_ok=e.get("i2s_ok", ""),
                       batt_mv=e.get("batt_mv", "") or "", node_sent_clips=e.get("sent_clips", ""),
                       node_dropped_clips=e.get("dropped_clips", ""), bridge_drops_total=e.get("bridge_drops", ""),
                       end_received=int(end is not None), clock_synced=int(clock_synced)))
    info = dict(file=fname, node=node, cid=cid, rec_start=rec_start, lost=lost, damaged=damaged, lvl=lvl,
                rssi=e.get("rssi_avg", "?"), wait=e.get("wait_ms", None), saved=saved)
    if saved and cls_out is not None:
        pending[key] = info
        cls_in.put((path, key))
    else:
        live_line(info, None)


def live_line(info, p, ms=None, recent_flags=None, alert=False):
    if p is None:
        pp = "p=-"
    else:
        pp = f"p={p:.2f}" + (" FLAG" if (not info["damaged"] and p >= thr) else "")
    dmg = f" DAMAGED({info['lost']} lost)" if info["damaged"] else (f" lost {info['lost']}" if info["lost"] else "")
    rf = f" | last{ALERT_N}: {recent_flags}" if recent_flags is not None else ""
    wait = f" wait {info['wait'] / 1000:.1f}s" if info.get("wait") else ""
    log(f"node {info['node']} clip {info['cid']:5d} rec {info['rec_start']:%H:%M:%S} | lvl {info['lvl']} dBFS | "
        f"RSSI {info['rssi']}{wait}{dmg} | {pp}{rf}{' | ZONE ALERT' if alert else ''}"
        f"{'' if info['saved'] else ' | NOT SAVED (disk)'}")


def handle_result(key, p, ms):
    info = pending.pop(key, None)
    if info is None: return
    node = info["node"]; ns = node_stats(node)
    flagged = int(not info["damaged"] and p >= thr)
    stats["classified"] += 1; ns["classified"] += 1
    stats["flagged"] += flagged; ns["flagged"] += flagged
    rec = recent.setdefault(node, [])
    if not info["damaged"]:
        rec.append(flagged); del rec[:-ALERT_N]
    k = sum(rec); alert = len(rec) >= ALERT_N and k >= ALERT_K
    if alert and not alert_on.get(node): log(f"*** ZONE ALERT node {node}: {k} of last {ALERT_N} clips flagged ***")
    if not alert and alert_on.get(node): log(f"zone alert cleared for node {node}")
    alert_on[node] = alert
    pred_csv.row(dict(file=info["file"], node=node, clip_id=info["cid"], rec_start=f"{info['rec_start']:%Y-%m-%d %H:%M:%S}",
                      damaged=info["damaged"], p=round(p, 5), flagged=flagged, inf_ms=round(ms, 1),
                      recent_flags=f"{k}/{len(rec)}", zone_alert=int(alert)))
    live_line(info, p, ms, f"{k}/{len(rec)}", alert)


def write_summary():
    hrs = max((time.time() - t_start) / 3600, 1e-6)
    free_gb = shutil.disk_usage(RUN).free / 1e9
    L = ["SONARA FARM DATA COLLECTION", "=" * 60,
         f"Run folder: {RUN}",
         f"Started {datetime.fromtimestamp(t_start):%Y-%m-%d %H:%M}, running {hrs:.1f} h. Pi clock synced to internet: "
         f"{'yes' if clock_synced else 'NO (times may be off; note the real time in notes)'}",
         f"Clips saved {stats['saved']} ({stats['saved'] / hrs:.0f}/h), damaged {stats['damaged']}, "
         f"not saved for lack of disk {stats['unsaved_disk']}. Disk free {free_gb:.1f} GB.",
         f"Bridge: {'alive' if time.time() - stats['bridge_last'] < 15 else 'NO HEARTBEAT'}; packets dropped in bridge "
         f"since its start {stats['bridge_drops']}; corrupted serial frames {parser.bad}.",
         ""]
    if thr is not None:
        L.append(f"Model threshold {thr}; zone alert = {ALERT_K} of last {ALERT_N} usable clips flagged.")
    else:
        L.append("Model not running (collection only).")
    L += ["", "PER NODE   clips  per hour  damaged  classified  flagged  median level  last clip"]
    for n in sorted(stats["per_node"]):
        s = stats["per_node"][n]
        med = f"{np.median(s['level']):.1f} dBFS" if s["level"] else "-"
        ago = f"{(time.time() - s['last']) / 60:.0f} min ago" if s["last"] else "-"
        fl = f"{s['flagged']} ({100 * s['flagged'] / s['classified']:.1f}%)" if s["classified"] else "-"
        L.append(f"  node {n}  {s['clips']:6d}  {s['clips'] / hrs:8.0f}  {s['damaged']:7d}  {s['classified']:10d}  "
                 f"{fl:>8}  {med:>12}  {ago}")
    if stats["resets"]:
        L += ["", "NODE RESTARTS"] + [f"  {r}" for r in stats["resets"][-20:]]
    L += ["", "Flags are model outputs on unlabelled farm audio, not diagnoses. Check flagged clips by listening",
          "and against the caretaker's / vet's observations in notes.csv."]
    txt = "\n".join(L) + "\n"
    open(os.path.join(RUN, "summary.txt"), "w").write(txt)
    return txt


def pi_health():
    t = sh("vcgencmd measure_temp").replace("temp=", "").replace("'C", "")
    health_csv.row(dict(time=f"{datetime.now():%Y-%m-%d %H:%M:%S}", temp_c=t, throttled=sh("vcgencmd get_throttled").replace("throttled=", ""),
                        load_1min=os.getloadavg()[0], disk_free_gb=round(shutil.disk_usage(RUN).free / 1e9, 2),
                        clips_saved=stats["saved"]))


# ---------------- main loop ----------------
parser = Parser()
log(f"=== SONARA collection started. Run folder {RUN}. Pi clock synced: {'yes' if clock_synced else 'NO'} ===")
if not clock_synced:
    log("!! Pi clock not synced to the internet. Check `date`; set it with: sudo date -s '2026-11-03 09:30:00'")
next_summary = time.time() + 60; next_health = time.time()
try:
    while True:
        try:
            data = raw_q.get(timeout=0.2)
            chunks = [data]
            while not raw_q.empty() and len(chunks) < 200: chunks.append(raw_q.get_nowait())
            data = b"".join(chunks)
        except queue.Empty:
            data = b""
        for p in parser.feed(data) if data else []:
            m = p[0]
            if m == 0x53 and len(p) >= HEADER.size:
                _, _, node, cid, idx, tot, dl = HEADER.unpack_from(p)
                c = open_clips.setdefault((node, cid), dict(chunks={}, first=time.time()))
                c["chunks"][idx] = p[HEADER.size:HEADER.size + dl]; c["last"] = time.time()
            elif m == 0x63 and len(p) == END.size + ENDB.size:
                v = END.unpack_from(p, 0); b = ENDB.unpack_from(p, END.size)
                (_, node, cid, upt, minheap, rr, i2s, rpeak, rrms, pk, failed, retries, send_ms, wait_ms, batt,
                 rec_age, dropped, sent) = v
                end = dict(uptime_s=upt, min_heap=minheap, reset_reason=rr, i2s_ok=i2s, failed=failed, retries=retries,
                           send_ms=send_ms, wait_ms=wait_ms, batt_mv=batt, rec_age_ms=rec_age, dropped_clips=dropped,
                           sent_clips=sent, bridge_rx=b[0], rssi_avg=b[1], rssi_min=b[2], bridge_drops=b[4])
                stats["bridge_drops"] = max(stats["bridge_drops"], b[4])
                if (node, cid) in closed and (node, cid) not in open_clips:
                    continue                                   # clip already closed by timeout
                if (node, cid) not in open_clips:
                    open_clips[(node, cid)] = dict(chunks={}, first=time.time(), last=time.time())
                if not i2s and time.time() - mic_warned.get(node, 0) > 600:
                    log(f"!! node {node}: microphone not working (check wiring)"); mic_warned[node] = time.time()
                close_clip((node, cid), end)
            elif m == 0x64 and len(p) == BEAT.size:
                _, up, drops, frames, grants, owner, seen, _ = BEAT.unpack(p)
                if up < stats["bridge_up"]: log("!! bridge restarted")
                stats.update(bridge_last=time.time(), bridge_up=up, bridge_drops=drops)
                bridge_csv.row(dict(time=f"{datetime.now():%Y-%m-%d %H:%M:%S}", bridge_uptime_s=up, queue_drops=drops,
                                    frames_out=frames, grants=grants, owner=owner,
                                    nodes_seen=",".join(str(i + 1) for i in range(8) if seen >> i & 1)))
        now = time.time()
        for k in [k for k, c in open_clips.items() if now - c["last"] > CLIP_TIMEOUT_S]:
            close_clip(k)                                          # END packet never arrived
        for k in [k for k, t in closed.items() if now - t > 120]: del closed[k]
        if cls_out is not None:
            while True:
                try: msg = cls_out.get_nowait()
                except queue.Empty: break
                if msg[0] == "ready":
                    thr = msg[1]; log(f"model loaded (threshold {thr})")
                elif msg[0] == "error":
                    log(f"!! model not loaded, collecting audio only: {msg[1]}"); cls_out = None
                    for info in list(pending.values()): live_line(info, None)
                    pending.clear(); break
                elif msg[0] == "result":
                    handle_result(msg[1], msg[2], msg[3])
                elif msg[0] == "fail":
                    info = pending.pop(msg[1], None); log(f"!! classify failed: {msg[2]}")
                    if info: live_line(info, None)
        if now >= next_health:
            pi_health(); next_health = now + 60
            if port_state["open"] and now - stats["bridge_last"] > 30 and now - t_start > 30:
                log("!! no heartbeat from the bridge for 30 s (is sonara_deploy_bridge flashed?)")
            for n, s in stats["per_node"].items():
                if s["last"] and now - s["last"] > 300:
                    log(f"!! node {n}: no clip for {(now - s['last']) / 60:.0f} min (power bank empty? out of range?)")
        if now >= next_summary:
            write_summary(); next_summary = now + 600
except KeyboardInterrupt:
    pass
finally:
    for k in list(open_clips): close_clip(k)
    deadline = time.time() + 10
    while pending and cls_out is not None and time.time() < deadline:
        try:
            msg = cls_out.get(timeout=0.5)
            if msg[0] == "result": handle_result(msg[1], msg[2], msg[3])
        except Exception:
            pass
    txt = write_summary()
    log("=== collection stopped ===")
    print("\n" + txt)
