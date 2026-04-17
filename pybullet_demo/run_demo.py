"""
PyBullet drone demonstration for the multi-robot SAR thesis.

Example invocations:
    # Basic interactive GUI (default M4*, seed 42, 30 sites, 3 robots)
    python pybullet_demo/run_demo.py

    # Head-less capture -> pybullet_demo/frames/frame_*.png
    python pybullet_demo/run_demo.py --headless --record

    # Side-by-side "watch M1 flail vs. M4* succeed"
    python pybullet_demo/run_demo.py --compare M1,M4* --headless --record

    # Save/load a fixed instance for reproducibility
    python pybullet_demo/run_demo.py --save-instance inst.json
    python pybullet_demo/run_demo.py --load-instance inst.json

Frame stitching (outside this script -- NO ffmpeg runtime dependency):
    ffmpeg -framerate 60 -i pybullet_demo/frames/frame_%05d.png demo.mp4
"""

from __future__ import annotations

import argparse
import json
import os
import random
import shutil
import sys
import time
from typing import List, Optional

# Make sure both this dir and the repo root are on sys.path so that
# "import main" and "import scene"/"import replay" both resolve cleanly.
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.dirname(_THIS_DIR)
for _p in (_REPO_ROOT, _THIS_DIR):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import numpy as np

import main as mr
from scene import PYBULLET_AVAILABLE
from replay import (
    build_replay, run_replay, run_replay_matplotlib,
)


# ---------------------------------------------------------------------------
# Instance I/O helpers
# ---------------------------------------------------------------------------

def _instance_to_json(inst: dict) -> dict:
    """Convert numpy-produced tuples/keys into JSON-safe structures."""
    return {
        "node_positions": {str(k): [float(v[0]), float(v[1])]
                            for k, v in inst["node_positions"].items()},
        "node_probs": {str(k): float(v)
                       for k, v in inst["node_probs"].items()},
        "bases": {str(k): [float(v[0]), float(v[1])]
                   for k, v in inst["bases"].items()},
        "target": int(inst["target"]),
        "optimal_dist": float(inst["optimal_dist"]),
    }


def _instance_from_json(data: dict) -> dict:
    return {
        "node_positions": {int(k): tuple(v)
                           for k, v in data["node_positions"].items()},
        "node_probs": {int(k): float(v)
                       for k, v in data["node_probs"].items()},
        "bases": {int(k): tuple(v)
                   for k, v in data["bases"].items()},
        "target": int(data["target"]),
        "optimal_dist": float(data["optimal_dist"]),
    }


def load_or_generate_instance(
    args: argparse.Namespace,
) -> dict:
    if args.load_instance and os.path.exists(args.load_instance):
        with open(args.load_instance) as f:
            return _instance_from_json(json.load(f))
    # Fixed seed → reproducible demo
    inst = mr.generate_instance(
        n_nodes=args.n, n_robots=args.r,
        area_scale=10.0, seed=args.seed,
        min_opt_dist=1.0, max_opt_dist=args.e / 2.0,
    )
    if args.save_instance:
        with open(args.save_instance, "w") as f:
            json.dump(_instance_to_json(inst), f, indent=2)
    return inst


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(
        description="PyBullet drone demo for multi-robot search & rescue.",
    )
    ap.add_argument("--model", default="M4*",
                    help="Model to replay (M1, M4, or M4*). Default: M4*.")
    ap.add_argument("--seed", type=int, default=42,
                    help="RNG seed for instance generation. Default: 42.")
    ap.add_argument("--n", type=int, default=30,
                    help="Number of candidate sites. Default: 30.")
    ap.add_argument("--r", type=int, default=3,
                    help="Number of robots / bases. Default: 3.")
    ap.add_argument("--e", type=float, default=14.0,
                    help="Energy budget E (metres). Default: 14.")
    ap.add_argument("--speed", type=float, default=2.0,
                    help="Drone ground speed (m/s). Default: 2.")
    ap.add_argument("--hz", type=int, default=240,
                    help="Sim-step rate. Default: 240.")
    ap.add_argument("--record", action="store_true",
                    help="Save a PNG per frame to pybullet_demo/frames/.")
    ap.add_argument("--frame-every", type=int, default=8,
                    help="Capture one frame per N sim steps. Default: 8.")
    ap.add_argument("--frames-dir", default=None,
                    help="Destination directory for --record PNGs.")
    ap.add_argument("--headless", action="store_true",
                    help="Use pybullet.DIRECT (no GUI window).")
    ap.add_argument("--force-matplotlib", action="store_true",
                    help="Bypass PyBullet entirely; use matplotlib renderer.")
    ap.add_argument("--compare", default=None,
                    help="Comma-separated pair of models, e.g. 'M1,M4*'. "
                         "Runs both on the *same* instance. In headless mode "
                         "the two streams go to separate frame subdirs.")
    ap.add_argument("--save-instance", default=None,
                    help="Write the generated instance to this JSON path.")
    ap.add_argument("--load-instance", default=None,
                    help="Read the instance from this JSON path instead of "
                         "generating one.")
    ap.add_argument("--max-frames", type=int, default=600,
                    help="Hard cap on frames written per run (prevents "
                         "runaway disk usage). Default: 600.")
    return ap.parse_args(argv)


# ---------------------------------------------------------------------------
# Run helpers
# ---------------------------------------------------------------------------

def _run_one(
    model: str, instance: dict, args: argparse.Namespace,
    frames_dir: str, title_prefix: str = "",
) -> int:
    # Re-seed so M1's random picks are deterministic across paired runs
    random.seed(args.seed)
    np.random.seed(args.seed)

    replay = build_replay(model, instance, energy=args.e)
    print(f"[{model}] rounds={len(replay.rounds)} "
          f"final FCR={replay.final_fcr:.3f} d_opt={replay.optimal_dist:.3f}")

    t0 = time.time()
    used_matplotlib = False

    if PYBULLET_AVAILABLE and not args.force_matplotlib:
        mode = "DIRECT" if args.headless else "GUI"
        try:
            n_frames = run_replay(
                replay, instance, mode=mode,
                speed_mps=args.speed, hz=args.hz,
                record=args.record, frames_dir=frames_dir,
                frame_every=args.frame_every,
                title_prefix=title_prefix,
            )
        except Exception as exc:
            print(f"[{model}] PyBullet path failed ({exc!r}); "
                  f"falling back to matplotlib renderer.")
            n_frames = run_replay_matplotlib(
                replay, instance, frames_dir=frames_dir,
                speed_mps=args.speed, hz=max(30, args.hz // 4),
                frame_every=max(2, args.frame_every // 2),
                title_prefix=title_prefix,
            )
            used_matplotlib = True
    else:
        if not PYBULLET_AVAILABLE:
            print(f"[{model}] pybullet not installed; using matplotlib path.")
        else:
            print(f"[{model}] --force-matplotlib: using matplotlib path.")
        n_frames = run_replay_matplotlib(
            replay, instance, frames_dir=frames_dir,
            speed_mps=args.speed, hz=max(30, args.hz // 4),
            frame_every=max(2, args.frame_every // 2),
            title_prefix=title_prefix,
        )
        used_matplotlib = True

    dt = time.time() - t0
    tag = "matplotlib" if used_matplotlib else "pybullet"
    print(f"[{model}] replay done in {dt:.1f}s ({n_frames} frames via {tag})")
    return n_frames


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main(argv: Optional[List[str]] = None) -> int:
    args = parse_args(argv)
    default_dir = os.path.join(_THIS_DIR, "frames")
    frames_dir = args.frames_dir or default_dir

    instance = load_or_generate_instance(args)
    print(f"instance: n={len(instance['node_positions'])} "
          f"R={len(instance['bases'])} target={instance['target']} "
          f"d_opt={instance['optimal_dist']:.3f}")

    # Clean the output dir so successive runs don't interleave frames.
    if args.record and os.path.isdir(frames_dir):
        for f in os.listdir(frames_dir):
            if f.startswith("frame_") and f.endswith(".png"):
                try:
                    os.remove(os.path.join(frames_dir, f))
                except Exception:
                    pass

    if args.compare:
        models = [m.strip() for m in args.compare.split(",") if m.strip()]
        if len(models) != 2:
            raise SystemExit("--compare takes exactly two models: e.g. M1,M4*")
        total = 0
        for m in models:
            sub = os.path.join(frames_dir, m.replace("*", "star"))
            if args.record and os.path.isdir(sub):
                shutil.rmtree(sub, ignore_errors=True)
            os.makedirs(sub, exist_ok=True)
            total += _run_one(m, instance, args, sub, title_prefix=f"[{m}] ")
        print(f"compare: wrote {total} total frames to {frames_dir}/<model>/")
        if total:
            print(f"Open e.g. {os.path.join(frames_dir, models[0].replace('*', 'star'), 'frame_00000.png')}")
        return 0

    n_frames = _run_one(args.model, instance, args, frames_dir)
    if args.record and n_frames:
        first = os.path.join(frames_dir, "frame_00000.png")
        print(f"Open {first} to preview the demo.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
