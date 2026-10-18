"""Measure SONARA inference time and memory on the Raspberry Pi 4 gateway (matrix rows 15 and 16).

Copy this file and sonara_models.py into the same folder on the Pi, then run:

    python3 pi_latency_benchmark.py
    python3 pi_latency_benchmark.py --torchscript sonara_system_model.pt
    python3 pi_latency_benchmark.py --weights_dir export --seed 42

The default compares the three models from the final evaluation: MobileNetV3-Small (B8, system
model), EfficientNet-B0 (C2/C3, runner-up) and the CNN-BiLSTM (A0, baseline). Each model is timed
in its own process so its memory use can be measured separately.

Latency does not depend on the trained weights, so random weights give the same timing.
--torchscript times the exported gateway file end to end (raw 5-s waveform in, Distress
probability out, feature extraction included): this is the number the gateway actually pays.
--weights_dir also checks that the trained .pt files load on the Pi.

Requires: torch, torchvision, numpy. torchaudio is optional; if present, feature extraction
(log-mel + deltas) for one 5-s clip is timed as well.
Run with the Pi idle, on its normal power supply, with a heatsink or fan if one will be used in
the farm. The script prints the CPU temperature and throttling state before and after.
"""
import argparse, csv, json, os, platform, resource, subprocess, sys, time
import numpy as np

DEFAULT_MODELS = ["mobilenetv3_small", "efficientnet_b0", "cnn_bilstm"]

p = argparse.ArgumentParser()
p.add_argument("--models", nargs="*", default=DEFAULT_MODELS)
p.add_argument("--threads", type=int, default=4)
p.add_argument("--warmup", type=int, default=10)
p.add_argument("--runs", type=int, default=100)
p.add_argument("--weights_dir", default=None)
p.add_argument("--seed", type=int, default=42)
p.add_argument("--torchscript", default=None, help="path to sonara_system_model.pt (end-to-end timing)")
p.add_argument("--out", default="pi_latency_results.csv")
p.add_argument("--_child", default=None, help=argparse.SUPPRESS)   # internal: time one item in a subprocess
a = p.parse_args()


def peak_rss_mb():
    r = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss          # kB on Linux
    return r / 1024 if sys.platform != "darwin" else r / 1e6


def time_fn(fn):
    for _ in range(a.warmup):
        fn()
    ts = []
    for _ in range(a.runs):
        t = time.perf_counter(); fn(); ts.append((time.perf_counter() - t) * 1000)
    return float(np.median(ts)), float(np.percentile(ts, 95)), float(np.mean(ts))


def child(item):
    """Time one item in this (fresh) process and print one JSON line."""
    import torch
    torch.set_num_threads(a.threads)
    base_rss = peak_rss_mb()
    if item == "features":
        import torchaudio
        mel = torchaudio.transforms.MelSpectrogram(sample_rate=16000, n_fft=400, hop_length=160, n_mels=64, power=2.0)
        to_db = torchaudio.transforms.AmplitudeToDB(stype="power")
        dl = torchaudio.transforms.ComputeDeltas()
        wav = torch.randn(1, 5 * 16000) * 0.1

        @torch.no_grad()
        def fn():
            db = to_db(mel(wav)); d1 = dl(db); return torch.cat([db, d1, dl(d1)], 0)
        label, n, size_mb = "feature extraction (5-s clip)", "", ""
    elif item == "torchscript":
        model = torch.jit.load(a.torchscript, map_location="cpu").eval()
        wav = (torch.rand(1, 5 * 16000) * 2 - 1) * 0.1                  # 1 x 80000, values in -1..1
        with torch.no_grad():
            out = model(wav)
        fn = lambda: model(wav)
        label = "TorchScript gateway model, end to end (waveform -> probability)"
        n = sum(p.numel() for p in model.parameters())
        size_mb = round(os.path.getsize(a.torchscript) / 1e6, 2)
        print(f"# torchscript output on a random clip: {float(out.flatten()[-1]):.4f}", file=sys.stderr)
    else:
        from sonara_models import MODEL_BUILDERS, MODEL_LABELS, count_params
        model = MODEL_BUILDERS[item]().eval()
        if a.weights_dir:
            path = os.path.join(a.weights_dir, f"{item}_seed{a.seed}.pt")
            if os.path.exists(path):
                model.load_state_dict(torch.load(path, map_location="cpu"))
                print(f"# loaded {path}", file=sys.stderr)
            else:
                print(f"# no weights at {path}: timing with random weights", file=sys.stderr)
        x = torch.randn(1, 3, 64, 500)                                  # one 5-s clip of features
        fn = lambda: model(x)
        label, n = MODEL_LABELS[item], count_params(model)
        size_mb = round(n * 4 / 1e6, 2)
    with torch.no_grad():
        med, p95, mean = time_fn(fn)
    print(json.dumps(dict(step=label, key=item, params=n, size_mb=size_mb, median_ms=round(med, 1),
                          p95_ms=round(p95, 1), mean_ms=round(mean, 1),
                          peak_ram_mb=round(peak_rss_mb(), 1), ram_before_mb=round(base_rss, 1),
                          model_ram_mb=round(peak_rss_mb() - base_rss, 1))))


def pi_state():
    out = {}
    for key, cmd in [("temp", ["vcgencmd", "measure_temp"]), ("throttled", ["vcgencmd", "get_throttled"])]:
        try:
            out[key] = subprocess.run(cmd, capture_output=True, text=True, timeout=5).stdout.strip()
        except (OSError, subprocess.TimeoutExpired):
            out[key] = "n/a"
    return out


if a._child:
    child(a._child)
    sys.exit(0)

import torch
print(f"Machine: {platform.machine()} | {platform.platform()} | Python {platform.python_version()} | "
      f"torch {torch.__version__} | threads {a.threads}")
try:
    with open("/proc/device-tree/model") as f:
        print("Board:", f.read().strip("\x00\n"))
except OSError:
    print("Board: not a Raspberry Pi (no /proc/device-tree/model)")
try:
    with open("/proc/meminfo") as f:
        print("RAM:", f.readline().split(":")[1].strip())
except OSError:
    pass
before = pi_state()
print("Before:", before)

items = []
try:
    import torchaudio  # noqa: F401
    items.append("features")
except ImportError:
    print("torchaudio not installed: skipping feature-extraction timing")
items += a.models
if a.torchscript:
    items.append("torchscript")

passthrough = [f"--threads={a.threads}", f"--warmup={a.warmup}", f"--runs={a.runs}", f"--seed={a.seed}"]
if a.weights_dir:
    passthrough.append(f"--weights_dir={a.weights_dir}")
if a.torchscript:
    passthrough.append(f"--torchscript={a.torchscript}")

rows = []
for item in items:
    r = subprocess.run([sys.executable, os.path.abspath(__file__), f"--_child={item}", *passthrough],
                       capture_output=True, text=True, cwd=os.path.dirname(os.path.abspath(__file__)))
    if r.stderr.strip():
        print(r.stderr.strip())
    if r.returncode != 0:
        print(f"FAILED: {item}")
        continue
    row = json.loads(r.stdout.strip().splitlines()[-1])
    rows.append(row)
    print(f"{row['step'][:44]:44s} median {row['median_ms']:8.1f} ms   p95 {row['p95_ms']:8.1f} ms   "
          f"peak RAM {row['peak_ram_mb']:7.1f} MB (+{row['model_ram_mb']:.1f} MB over PyTorch alone)")

after = pi_state()
print("After:", after)
for r in rows:
    r.update(threads=a.threads, runs=a.runs, warmup=a.warmup, temp_before=before["temp"], temp_after=after["temp"],
             throttled_after=after["throttled"])
with open(a.out, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
    w.writeheader(); w.writerows(rows)

by_key = {r["key"]: r for r in rows}
print("\nSummary (batch size 1, one 5-s clip):")
for r in rows:
    print(f"  {r['step'][:60]:60s} {r['median_ms']:>8} ms (p95 {r['p95_ms']})")
if "mobilenetv3_small" in by_key and "efficientnet_b0" in by_key:
    m, e = by_key["mobilenetv3_small"], by_key["efficientnet_b0"]
    print(f"\nEfficientNet-B0 / MobileNetV3-Small: {e['median_ms'] / m['median_ms']:.2f}x the time, "
          f"{e['params'] / m['params']:.2f}x the parameters, {e['model_ram_mb'] / max(m['model_ram_mb'], 0.1):.2f}x the extra RAM")
if "features" in by_key and "mobilenetv3_small" in by_key:
    total = by_key["features"]["median_ms"] + by_key["mobilenetv3_small"]["median_ms"]
    print(f"Features + MobileNetV3-Small: {total:.1f} ms per clip (target < 200 ms)")
if after["throttled"] not in ("n/a", "throttled=0x0"):
    print("WARNING: the Pi reports throttling (" + after["throttled"] + "). Improve cooling or power and run again.")
print("Saved", a.out, f"| {a.runs} runs after {a.warmup} warm-up runs, batch size 1, {a.threads} threads")
