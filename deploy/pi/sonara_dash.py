#!/usr/bin/env python3
"""
SONARA terminal dashboard. Run on the Pi over SSH:   monitor
(or ~/sonara-env/bin/python ~/sonara_deploy_app/sonara_dash.py)
Refreshes every 3 s. Ctrl+C closes the dashboard; collection keeps running.
Only READS the files written by sonara_collect.py.
"""
import csv, glob, os, shutil, subprocess, sys, time
from datetime import datetime

BASE = os.path.expanduser("~/sonara_deploy")
G, Y, R, B, D, X = "\033[32m", "\033[33m", "\033[31m", "\033[1m", "\033[2m", "\033[0m"


def sh(cmd):
    try:
        return subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=3).stdout.strip()
    except Exception:
        return ""


def rows(path):
    try:
        with open(path, newline="") as f:
            return list(csv.DictReader(f))
    except Exception:
        return []


def tail(path, n):
    try:
        with open(path, "rb") as f:
            f.seek(0, 2); size = f.tell(); f.seek(max(0, size - 8000))
            return f.read().decode(errors="replace").splitlines()[-n:]
    except Exception:
        return []


def ago(ts):
    s = time.time() - ts
    return f"{s:.0f}s" if s < 120 else f"{s / 60:.0f}m"


def ts(s):
    try:
        return datetime.strptime(s, "%Y-%m-%d %H:%M:%S").timestamp()
    except Exception:
        return 0


def dot(c): return f"{c}●{X}"


def bars(rssi):
    try: r = int(rssi)
    except (TypeError, ValueError): return f"{D}-{X}"
    n, c = (4, G) if r >= -65 else (3, G) if r >= -75 else (2, Y) if r >= -85 else (1, R)
    return f"{c}{'█' * n}{D}{'░' * (4 - n)}{X} {r}"


def frame(height):
    runs = sorted(glob.glob(os.path.join(BASE, "runs", "*")))
    W = min(shutil.get_terminal_size((100, 30)).columns, 96)
    line = f"{D}{'─' * W}{X}"
    out = []
    if not runs:
        return [f"{B}SONARA{X}  no run folder yet. Is collection running?  (sudo systemctl start sonara-collect)"]
    run = runs[-1]
    clips = rows(os.path.join(run, "clips.csv"))
    preds = {(p["node"], p["clip_id"], p["rec_start"]): p for p in rows(os.path.join(run, "predictions.csv"))}
    bridge = rows(os.path.join(run, "bridge.csv"))
    active = sh("systemctl is-active sonara-collect") == "active"
    synced = sh("timedatectl show -p NTPSynchronized --value") == "yes"
    free = shutil.disk_usage(BASE).free / 1e9
    temp = sh("vcgencmd measure_temp").replace("temp=", "").replace("'C", "")
    now = time.time()

    out.append(f"{B}SONARA  farm monitor{X}{' ' * max(1, W - 39)}{datetime.now():%Y-%m-%d %H:%M:%S}")
    out.append(line)
    dcol = G if free > 5 else (Y if free > 2.5 else R)
    out.append(f" Collection {dot(G if active else R)} {'running' if active else 'STOPPED'}    "
               f"Clock {dot(G if synced else Y)} {'synced' if synced else 'NOT synced (check date)'}    "
               f"Disk {dcol}{free:.1f} GB{X} free    Pi {temp} C")
    if bridge:
        b = bridge[-1]; bage = now - ts(b["time"]); drops = int(b.get("queue_drops") or 0)
        out.append(f" Bridge     {dot(G if bage < 15 else R)} {'alive' if bage < 15 else 'no heartbeat for ' + ago(ts(b['time']))}"
                   f"    nodes heard: {b.get('nodes_seen') or '-'}    dropped packets: {(Y if drops else G)}{drops}{X}")
    else:
        out.append(f" Bridge     {dot(Y)} waiting for first heartbeat")
    out.append(f" Run {os.path.basename(run)}")
    out.append("")

    nodes = sorted({c["node"] for c in clips}, key=int)
    out.append(f"{B} {'NODE':<6}{'STATUS':<22}{'CLIPS':>6}{'LAST 10 MIN':>13}{'LAST CLIP':>11}   {'SIGNAL':<12}{'LEVEL':>8}{'FLAGS':>9}{X}")
    out.append(line)
    for n in nodes:
        cn = [c for c in clips if c["node"] == n]
        last = cn[-1]; lt = ts(last["received"]); age = now - lt
        recent10 = sum(1 for c in cn if now - ts(c["received"]) <= 600)
        pn = [preds.get((c["node"], c["clip_id"], c["rec_start"])) for c in cn]
        pn = [p for p in pn if p]
        rf = pn[-1]["recent_flags"] if pn else "-"
        alert = bool(pn) and pn[-1]["zone_alert"] == "1"
        if alert: st = f"{dot(R)} {R}{B}ZONE ALERT{X}"; w = 12
        elif age > 300: st = f"{dot(R)} {R}silent{X}"; w = 8
        elif age > 60: st = f"{dot(Y)} {Y}slow{X}"; w = 6
        elif last["damaged"] == "1": st = f"{dot(Y)} {Y}last clip damaged{X}"; w = 19
        else: st = f"{dot(G)} OK"; w = 4
        out.append(f" {n:<6}{st}{' ' * (22 - w)}{len(cn):>6}{recent10:>13}{ago(lt) + ' ago':>11}   "
                   f"{bars(last.get('rssi_avg'))}{' ' * max(1, 8 - len(str(last.get('rssi_avg') or '-')))}"
                   f"{last['level_dbfs']:>6} dB{rf:>8}")
    if not nodes:
        out.append(f" {Y}no clips yet: are the nodes on and the bridge plugged in?{X}")
    out.append("")

    warn = []
    for l in tail(os.path.join(BASE, "live.log"), 400):
        if ("!!" in l or "ALERT" in l) and len(l) > 14:
            try:
                t = datetime.strptime(f"{datetime.now():%Y}-{l[:14]}", "%Y-%m-%d %H:%M:%S").timestamp()
            except ValueError:
                continue
            if now - t <= 600: warn.append(l)
    notes = rows(os.path.join(BASE, "notes.csv"))
    fixed = len(out) + 2 + 2 + min(len(notes), 3) + (1 + min(len(warn), 3) if warn else 0) + 1
    nclips = max(2, min(8, height - fixed))

    out.append(f"{B} Recent clips{X}")
    for c in clips[-nclips:][::-1]:
        p = preds.get((c["node"], c["clip_id"], c["rec_start"]))
        pp = (f"p {float(p['p']):.2f}" + (f"  {R}FLAG{X}" if p["flagged"] == "1" else "")) if p else f"{D}p ...{X}"
        dm = f"  {Y}damaged{X}" if c["damaged"] == "1" else ""
        out.append(f"   {c['rec_start'][11:]}   node {c['node']}   {c['level_dbfs']:>6} dB   {pp}{dm}")
    out.append("")
    out.append(f"{B} Notes{X}" + ("" if notes else f"   {D}none yet: note \"what you see\"{X}"))
    for nt in notes[-3:][::-1]:
        out.append(f"   {nt['time'][11:16]}  {nt['note'][:W - 12]}")
    if warn:
        out.append(f"{B} Warnings (last 10 min){X}")
        out += [f"   {Y}{w[6:][:W - 5]}{X}" for w in warn[-3:]]
    out.append(f"{D} Ctrl+C closes this view; collection keeps running. Flags are model outputs, not diagnoses.{X}")
    return out


try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")   # Pi over SSH may default to latin-1
except Exception:
    pass
ALT_ON, ALT_OFF, HIDE, SHOW = "\033[?1049h", "\033[?1049l", "\033[?25l", "\033[?25h"
sys.stdout.write(ALT_ON + HIDE)
try:
    while True:
        h = shutil.get_terminal_size((100, 30)).lines
        lines = frame(h)[:h - 1]
        sys.stdout.write("\033[H" + "".join(l + "\033[K\n" for l in lines) + "\033[J")
        sys.stdout.flush()
        time.sleep(3)
except KeyboardInterrupt:
    pass
finally:
    sys.stdout.write(SHOW + ALT_OFF); sys.stdout.flush()
