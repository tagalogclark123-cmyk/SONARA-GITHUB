"""Measure SONARA inference time on the Raspberry Pi 4 gateway (matrix row 16).

Copy this file and sonara_models.py into the same folder on the Pi, then run:

    python3 pi_latency_benchmark.py                 # all models, random weights
    python3 pi_latency_benchmark.py --weights_dir results_v6 --seed 42

Latency does not depend on the trained weights, so random weights give the same timing.
Pass --weights_dir to also check that the trained .pt files load on the Pi.

Requires: torch, torchvision (for MobileNetV3), numpy. torchaudio is optional; if present,
feature extraction (log-mel + deltas) for one 5-s clip is timed as well.
"""
import argparse, os, platform, time
import numpy as np
import torch
from sonara_models import MODEL_BUILDERS, MODEL_LABELS, count_params

p = argparse.ArgumentParser()
p.add_argument("--models", nargs="*", default=["cnn_bilstm", "cnn_frontend_only", "dscnn", "mobilenetv3_small"])
p.add_argument("--threads", type=int, default=4)
p.add_argument("--warmup", type=int, default=10)
p.add_argument("--runs", type=int, default=100)
p.add_argument("--weights_dir", default=None)
p.add_argument("--seed", type=int, default=42)
p.add_argument("--out", default="pi_latency_results.csv")
a = p.parse_args()

torch.set_num_threads(a.threads)
print(f"Machine: {platform.machine()} | {platform.platform()} | torch {torch.__version__} | threads {a.threads}")
try:
    with open("/proc/device-tree/model") as f:
        print("Board:", f.read().strip("\x00\n"))
except OSError:
    pass


def time_fn(fn):
    for _ in range(a.warmup):
        fn()
    ts = []
    for _ in range(a.runs):
        t = time.perf_counter(); fn(); ts.append((time.perf_counter() - t) * 1000)
    return float(np.median(ts)), float(np.percentile(ts, 95))


rows = []
try:
    import torchaudio
    mel = torchaudio.transforms.MelSpectrogram(sample_rate=16000, n_fft=400, hop_length=160, n_mels=64, power=2.0)
    to_db = torchaudio.transforms.AmplitudeToDB(stype="power")
    dl = torchaudio.transforms.ComputeDeltas()
    wav = torch.randn(1, 5 * 16000) * 0.1

    @torch.no_grad()
    def feats():
        db = to_db(mel(wav)); d1 = dl(db); return torch.cat([db, d1, dl(d1)], 0)

    med, p95 = time_fn(feats)
    rows.append(dict(step="feature extraction (5-s clip)", params="", size_mb="", median_ms=round(med, 1), p95_ms=round(p95, 1)))
except ImportError:
    print("torchaudio not installed: skipping feature-extraction timing")

x = torch.randn(1, 3, 64, 500)   # one 5-s clip
for name in a.models:
    model = MODEL_BUILDERS[name]().eval()
    if a.weights_dir:
        path = os.path.join(a.weights_dir, f"{name}_seed{a.seed}.pt")
        model.load_state_dict(torch.load(path, map_location="cpu"))
        print("loaded", path)
    with torch.no_grad():
        med, p95 = time_fn(lambda: model(x))
    n = count_params(model)
    rows.append(dict(step=MODEL_LABELS[name], params=n, size_mb=round(n * 4 / 1e6, 2), median_ms=round(med, 1), p95_ms=round(p95, 1)))
    print(f"{MODEL_LABELS[name]:36s} median {med:8.1f} ms   p95 {p95:8.1f} ms")

import csv
with open(a.out, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
    w.writeheader(); w.writerows(rows)
print("\n" + "\n".join(f"{r['step']:36s} {r['median_ms']:>8} ms (p95 {r['p95_ms']})" for r in rows))
print("Saved", a.out, f"| {a.runs} runs after {a.warmup} warm-up runs, batch size 1")
