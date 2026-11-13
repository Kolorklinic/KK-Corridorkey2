#!/usr/bin/env python3
# ---------------------------------------------------------------------------
# CorridorKey 2 for Resolve - worker tests
#
# From Creative Video Tips (CVT)  |  https://creativevideotips.com
# Licence: CC BY-NC-SA 4.0 with the CorridorKey additional terms (see LICENSE).
#
#   python test_worker.py unit
#       Plain helper tests (no model, a second).
#   python test_worker.py shot <movie> <reference alpha.mp4> [--window N]
#       Turns the movie into EXR frames the way the plugin will hand them
#       over, runs the worker, and compares its mattes with a reference
#       matte from the 2026-11-13 Mac test.
# Run with the CorridorKey Python (e.g. ~/CorridorKey/.venv/bin/python).
# ---------------------------------------------------------------------------
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
WORKER = HERE.parent / "ck2_worker.py"
sys.path.insert(0, str(HERE.parent))
os.environ.setdefault("OPENCV_IO_ENABLE_OPENEXR", "1")

import ck2_worker as w  # noqa: E402


def unit() -> None:
    assert w.chip_generation("Apple M1 Max") == 1
    assert w.chip_generation("Apple M5 Max") == 5
    assert w.chip_generation("Intel(R) Core") == 0
    assert w.choose_precision("Apple M2 Max") == "fp16"
    assert w.choose_precision("Apple M5 Max") == "bf16"
    assert w.padded_size(1920, 1080) == (1920, 1152)
    # Measured peaks: 16 -> ~24 GB, 24 -> ~31.6 GB, 40 -> ~46 GB, 80 -> 81.5 GB at HD.
    for win, measured in ((16, 23.9), (24, 31.6), (40, 45.9), (80, 81.5)):
        est = w.estimate_peak_gb(1920, 1152, win)
        assert measured <= est + 1.0, (win, est, measured)
    # 64 GB Mac: 51.8 GB GPU * 0.85 = 44 GB -> 24 at HD. M5 Max 128 GB -> 80.
    assert w.choose_window(1920, 1080, 200, 51.8 * 0.85) == 24
    assert w.choose_window(1920, 1080, 200, 107.5 * 0.85) == 80
    assert w.choose_window(1920, 1080, 10, 107.5 * 0.85) == 10
    assert w.choose_window(3840, 2160, 200, 51.8 * 0.85) == 8   # UHD, untested: ~37 GB est.
    # Temporal chunks as CorridorKey lays them out (checked against its logs:
    # 84 frames at 80 -> 2 windows, at 40 -> 4, 23 at 23 -> 1).
    assert len(w.chunk_starts(84, 80, 40)) == 2
    assert len(w.chunk_starts(84, 40, 20)) == 4
    assert len(w.chunk_starts(23, 23, 11)) == 1
    assert len(w.chunk_starts(93, 80, 40)) == 2
    assert w.chunk_starts(84, 40, 20) == [0, 20, 40, 44]
    assert w.chunk_of_frame(1, [0, 20, 40, 44], 40) == 1
    assert w.chunk_of_frame(84, [0, 20, 40, 44], 40) == 4
    print("unit tests passed")


def read_alpha_video(path: str):
    import cv2
    import numpy as np
    cap, out = cv2.VideoCapture(path), []
    while True:
        ok, f = cap.read()
        if not ok:
            break
        out.append(f[..., 0].astype(np.float32) / 255.0)
    return np.array(out)


def shot(movie: str, reference: str, window: str) -> None:
    import cv2
    import numpy as np
    tmp = Path(tempfile.mkdtemp(prefix="ck2_test_"))
    frames = tmp / "frames"
    frames.mkdir()
    # Display-coded RGB as half-float EXR, like the plugin's staging folder.
    subprocess.run(["ffmpeg", "-loglevel", "error", "-i", movie, "-pix_fmt", "gbrpf32le",
                    "-c:v", "exr", "-format", "1", "-compression", "3",
                    str(frames / "%06d.exr")], check=True)
    n = len(list(frames.glob("*.exr")))
    job = {
        "model_dir": "~/CorridorKey/CorridorKey2.0", "frames_dir": str(frames),
        "output_dir": str(tmp / "cache"), "window": window,
        "output_names": [f"f{i:06d}.exr" for i in range(n)],
    }
    (tmp / "job.json").write_text(json.dumps(job))
    t0 = time.time()
    proc = subprocess.run([sys.executable, str(WORKER), "run", str(tmp / "job.json")],
                          capture_output=True, text=True)
    events = [json.loads(l) for l in proc.stdout.splitlines() if l.startswith("{")]
    kinds = [e["event"] for e in events]
    print(f"worker exit {proc.returncode} in {time.time() - t0:.1f} s; events: "
          f"{ {k: kinds.count(k) for k in dict.fromkeys(kinds)} }")
    for e in events:
        if e["event"] in ("plan", "done", "error", "cpu_fallbacks"):
            print("  ", e)
    if proc.returncode != 0:
        print(proc.stderr[-3000:])
        sys.exit(1)
    progress = [e for e in events if e["event"] == "progress"]
    assert progress and progress[-1]["done"] == n, "progress did not reach the last frame"

    cache = sorted((tmp / "cache").glob("f*.exr"))
    assert len(cache) == n, f"{len(cache)} cached frames, expected {n}"
    first = cv2.imread(str(cache[0]), cv2.IMREAD_UNCHANGED)
    assert first.ndim == 3 and first.shape[2] == 4, first.shape
    alphas = np.array([cv2.imread(str(p), cv2.IMREAD_UNCHANGED)[..., 3] for p in cache])
    ref = read_alpha_video(reference)
    assert len(ref) == n, f"reference has {len(ref)} frames, worker {n}"
    d = np.abs(alphas.astype(np.float32) - ref)
    bad = (d > 0.1).mean() * 100
    print(f"   cache frame {first.shape[1]}x{first.shape[0]} RGBA half; "
          f"vs reference: mean diff {d.mean():.4f}, pixels >0.1: {bad:.3f}%")
    assert bad < 0.5, "matte differs from the reference"
    print(f"shot test passed ({tmp})")


if __name__ == "__main__":
    if len(sys.argv) >= 2 and sys.argv[1] == "unit":
        unit()
    elif len(sys.argv) >= 4 and sys.argv[1] == "shot":
        win = sys.argv[sys.argv.index("--window") + 1] if "--window" in sys.argv else "auto"
        shot(sys.argv[2], sys.argv[3], win)
    else:
        print(open(__file__).read().split("# ----")[1])
        sys.exit(2)
