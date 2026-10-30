#!/usr/bin/env python3
"""Helper for sonara_collect.py: classifies WAV files at low priority. Reads 'path<TAB>key' lines on stdin,
answers one JSON line per file on stdout. Not meant to be run by hand."""
import json, os, sys, time, wave
import numpy as np
here = sys.argv[1]
try: os.nice(10)
except Exception: pass
def say(*a): print(json.dumps(a), flush=True)
try:
    import torch
    torch.set_num_threads(2)
    model = torch.jit.load(os.path.join(here, "sonara_system_model.pt"), map_location="cpu").eval()
    thr = json.load(open(os.path.join(here, "deployment_config.json")))["operating_points"]["0.90"]["threshold"]
    say("ready", thr)
except Exception as e:
    say("error", str(e)); sys.exit(0)
try:
  for line in sys.stdin:
    path, key = line.rstrip("\n").split("\t")
    try:
        with wave.open(path) as w:
            x = np.frombuffer(w.readframes(w.getnframes()), "<i2").astype(np.float32) / 32768.0
        t0 = time.perf_counter()
        with torch.no_grad():
            p = float(model(torch.from_numpy(np.ascontiguousarray(x)).unsqueeze(0)).reshape(-1)[0])
        say("result", key, p, (time.perf_counter() - t0) * 1000)
    except Exception as e:
        say("fail", key, str(e))
except KeyboardInterrupt:
    pass
