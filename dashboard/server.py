"""
SONARA Field Monitor: local dashboard server.

Reads the field sessions in ../field_data (one folder per session, each with
report/clips.csv) and shows them as a dashboard at http://localhost:8000

Uses only the Python standard library, so there is nothing to install.

Run from VS Code's terminal, inside the SONARA-GITHUB folder:
    python dashboard/server.py
Then open http://localhost:8000 in your browser. Stop it with Ctrl+C.

Options:
    --port 8000              use another port if 8000 is busy
    --data PATH              read sessions from another folder (default: ../field_data)
"""

import argparse
import csv
import json
import math
import mimetypes
import os
import re
import sys
from collections import deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import unquote, urlparse

HERE = os.path.dirname(os.path.abspath(__file__))
STATIC = os.path.join(HERE, "static")
SETTINGS_FILE = os.path.join(HERE, "settings.json")
DEFAULT_DATA = os.path.normpath(os.path.join(HERE, "..", "field_data"))

SAFE_NAME = re.compile(r"^[A-Za-z0-9._-]+$")
CONTENT_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".wav": "audio/wav",
}


# ---------------------------------------------------------------------------
# Reading the data
# ---------------------------------------------------------------------------

def load_settings():
    with open(SETTINGS_FILE, encoding="utf-8") as f:
        return json.load(f)


def to_float(value, default=None):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def quantile(values, p):
    """Linear-interpolated quantile (same method as numpy.percentile's default)."""
    v = sorted(x for x in values if x is not None and not math.isnan(x))
    if not v:
        return None
    i = (len(v) - 1) * p
    lo, hi = math.floor(i), math.ceil(i)
    return v[lo] + (v[hi] - v[lo]) * (i - lo)


def read_session_log(data_dir):
    """field_data/sessions.csv: one row per session, written by the team."""
    path = os.path.join(data_dir, "sessions.csv")
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8-sig", newline="") as f:
        return {r["session_id"]: r for r in csv.DictReader(f)}


def timing_machine(session_dir):
    """The session report says where it measured inference time."""
    path = os.path.join(session_dir, "report", "summary.txt")
    if not os.path.exists(path):
        return "unknown"
    with open(path, encoding="utf-8", errors="replace") as f:
        text = f.read()
    if "on this Pi" in text:
        return "Raspberry Pi"
    if "machine that ran this report" in text:
        return "report computer (not the Pi)"
    return "unknown"


def load_all(data_dir, settings):
    log = read_session_log(data_dir)
    max_lost = int(settings["max_lost_packets"])
    window = int(settings["alert_window_clips"])
    trigger = int(settings["alert_trigger_clips"])

    folders = sorted(
        d for d in os.listdir(data_dir)
        if os.path.isfile(os.path.join(data_dir, d, "report", "clips.csv"))
    )

    sessions, clips, problems = [], [], []
    for n, sid in enumerate(folders, start=1):
        sdir = os.path.join(data_dir, sid)
        meta = log.get(sid, {})
        if not meta:
            problems.append(f"{sid}: not listed in sessions.csv, so site and bird details are missing")
        audio_dir = os.path.join(sdir, "audio")

        rows = []
        with open(os.path.join(sdir, "report", "clips.csv"), encoding="utf-8-sig", newline="") as f:
            for r in csv.DictReader(f):
                if r.get("error"):
                    problems.append(f"{sid}/{r.get('file')}: {r['error']}")
                    continue
                lost = int(to_float(r.get("lost_packets_est"), 0))
                # Older reports (sessions 1 and 2) have no 'usable' column: apply the same rule.
                usable_col = (r.get("usable") or "").strip()
                usable = int(usable_col) if usable_col in ("0", "1") else int(lost <= max_lost)
                prob = to_float(r.get("probability"))
                flag_col = (r.get("flagged") or "").strip()
                if flag_col in ("0", "1"):
                    flagged = int(flag_col)  # what the gateway decided at the time
                else:
                    flagged = int(prob is not None and prob >= to_float(r.get("threshold"), settings["threshold"]))
                rows.append({
                    "session_id": sid,
                    "time": r["time"],
                    "file": r["file"],
                    "node": r.get("node", ""),
                    "zone": r.get("zone") or meta.get("pen_label") or f"node {r.get('node', '')}",
                    "probability": prob,
                    "flagged": flagged,
                    "usable": usable,
                    "lost_packets": lost,
                    "level_db": to_float(r.get("level_db")),
                    "inference_ms": to_float(r.get("inference_ms")),
                    "has_audio": os.path.isfile(os.path.join(audio_dir, r["file"])),
                })
        rows.sort(key=lambda c: c["time"])

        # Zone alert rule, clip by clip, per node: flagged usable clips among the last N usable clips.
        history = {}
        for c in rows:
            h = history.setdefault(c["node"], deque(maxlen=window))
            if c["usable"]:
                h.append(1 if c["flagged"] else 0)
            c["window_clips"] = len(h)
            c["window_flags"] = sum(h)
            c["alert"] = int(c["window_flags"] >= trigger)

        usable_rows = [c for c in rows if c["usable"]]
        scores = [c["probability"] for c in usable_rows if c["probability"] is not None]
        flagged = sum(c["flagged"] for c in usable_rows)
        alerts, prev = 0, {}
        for c in usable_rows:
            if c["alert"] and not prev.get(c["node"]):
                alerts += 1
            prev[c["node"]] = c["alert"]
        ms = [c["inference_ms"] for c in rows]

        sessions.append({
            "session_id": sid,
            "label": f"S{n}",
            "date": meta.get("date", rows[0]["time"][:10] if rows else ""),
            "start": meta.get("start", rows[0]["time"][11:19] if rows else ""),
            "end": meta.get("end", rows[-1]["time"][11:19] if rows else ""),
            "site": meta.get("site", ""),
            "pen": meta.get("pen_label") or (rows[0]["zone"] if rows else ""),
            "birds": meta.get("birds", ""),
            "age": meta.get("age", ""),
            "reported_health": meta.get("health_status", "not recorded"),
            "health_source": meta.get("health_source", ""),
            "mic_position": meta.get("mic_position", ""),
            "notes": meta.get("notes", ""),
            "total_clips": len(rows),
            "usable_clips": len(usable_rows),
            "damaged_clips": len(rows) - len(usable_rows),
            "flagged_clips": flagged,
            "flagged_share": flagged / len(usable_rows) if usable_rows else None,
            "median_score": quantile(scores, 0.5),
            "max_score": max(scores) if scores else None,
            "alert_episodes": alerts,
            "median_inference_ms": quantile(ms, 0.5),
            "p95_inference_ms": quantile(ms, 0.95),
            "timing_machine": timing_machine(sdir),
        })
        clips.extend(rows)

    return {
        "data_folder": data_dir,
        "has_logo": os.path.isfile(os.path.join(STATIC, "logo.png")),
        "settings": settings,
        "sessions": sessions,
        "clips": clips,
        "problems": problems,
    }


# ---------------------------------------------------------------------------
# Web server
# ---------------------------------------------------------------------------

class Handler(BaseHTTPRequestHandler):
    data_dir = DEFAULT_DATA

    def log_message(self, fmt, *args):  # keep the terminal quiet except for errors
        pass

    def send_bytes(self, body, ctype, status=200):
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def send_file(self, path):
        if not os.path.isfile(path):
            return self.send_bytes(b"Not found", "text/plain", 404)
        # Fixed types: on Windows, mimetypes can read wrong values from the registry.
        ext = os.path.splitext(path)[1].lower()
        ctype = CONTENT_TYPES.get(ext) or mimetypes.guess_type(path)[0] or "application/octet-stream"
        with open(path, "rb") as f:
            self.send_bytes(f.read(), ctype)

    def do_GET(self):
        path = unquote(urlparse(self.path).path)

        if path in ("/", "/index.html"):
            return self.send_file(os.path.join(STATIC, "index.html"))

        if path.startswith("/static/"):
            name = path[len("/static/"):]
            if not SAFE_NAME.match(name):
                return self.send_bytes(b"Not found", "text/plain", 404)
            return self.send_file(os.path.join(STATIC, name))

        if path == "/api/data":
            try:
                payload = load_all(self.data_dir, load_settings())
                body = json.dumps(payload).encode("utf-8")
                return self.send_bytes(body, "application/json")
            except Exception as e:  # show the reason on the page instead of a blank screen
                body = json.dumps({"error": f"{type(e).__name__}: {e}"}).encode("utf-8")
                return self.send_bytes(body, "application/json", 500)

        # /audio/<session_id>/<file>.wav  (only files inside field_data/<session>/audio/)
        m = re.match(r"^/audio/([^/]+)/([^/]+)$", path)
        if m and SAFE_NAME.match(m.group(1)) and SAFE_NAME.match(m.group(2)) and m.group(2).lower().endswith(".wav"):
            return self.send_file(os.path.join(self.data_dir, m.group(1), "audio", m.group(2)))

        self.send_bytes(b"Not found", "text/plain", 404)


def main():
    ap = argparse.ArgumentParser(description="SONARA Field Monitor (local dashboard)")
    ap.add_argument("--port", type=int, default=8000)
    ap.add_argument("--data", default=DEFAULT_DATA, help="folder with the session folders and sessions.csv")
    a = ap.parse_args()

    data_dir = os.path.abspath(a.data)
    if not os.path.isdir(data_dir):
        sys.exit(f"Cannot find the data folder: {data_dir}\n"
                 f"Put this 'dashboard' folder inside SONARA-GITHUB (next to 'field_data'), "
                 f"or pass --data with the folder's path.")
    try:
        summary = load_all(data_dir, load_settings())
    except Exception as e:
        sys.exit(f"Could not read the field data: {type(e).__name__}: {e}")

    Handler.data_dir = data_dir
    try:
        server = ThreadingHTTPServer(("127.0.0.1", a.port), Handler)
    except OSError:
        sys.exit(f"Port {a.port} is already in use. Try: python dashboard/server.py --port 8001")

    print("SONARA Field Monitor")
    print(f"  Data folder: {data_dir}")
    print(f"  Found {len(summary['sessions'])} sessions, {len(summary['clips'])} clips")
    for p in summary["problems"]:
        print(f"  Note: {p}")
    print(f"\n  Open this in your browser:  http://localhost:{a.port}")
    print("  Press Ctrl+C here to stop.\n")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("Stopped.")


if __name__ == "__main__":
    main()
