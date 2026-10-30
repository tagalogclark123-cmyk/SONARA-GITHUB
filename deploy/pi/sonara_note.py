#!/usr/bin/env python3
"""
SONARA field note. Writes a time-stamped line to ~/sonara_deploy/notes.csv.
  note "pen 2: 3 birds sneezing, caretaker says sick since yesterday"
  note "feeding time, very noisy"
  note "vet checked pen 2: suspected CRD"
  note "node 3 moved to pen 4"
(`note` is a shortcut set up by install.sh; otherwise use ~/sonara-env/bin/python sonara_note.py "...")
"""
import csv, os, subprocess, sys
from datetime import datetime
if len(sys.argv) < 2:
    print(__doc__); sys.exit(1)
text = " ".join(sys.argv[1:])
base = os.path.expanduser("~/sonara_deploy"); os.makedirs(base, exist_ok=True)
path = os.path.join(base, "notes.csv"); new = not os.path.exists(path)
try:
    synced = subprocess.run(["timedatectl", "show", "-p", "NTPSynchronized", "--value"], capture_output=True, text=True).stdout.strip()
except Exception:
    synced = "?"
with open(path, "a", newline="") as f:
    w = csv.writer(f)
    if new: w.writerow(["time", "clock_synced", "note"])
    w.writerow([f"{datetime.now():%Y-%m-%d %H:%M:%S}", synced, text])
with open(os.path.join(base, "live.log"), "a") as f:
    f.write(f"{datetime.now():%m-%d %H:%M:%S} NOTE: {text}\n")
print(f"saved: {datetime.now():%H:%M:%S}  {text}")
