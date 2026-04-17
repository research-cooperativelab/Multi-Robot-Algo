# PyBullet Drone Demo

A visual, physics-inspired replay of the multi-robot search algorithms
described in the CSULB honors thesis.  Three drones fly over a 10 m x 10 m
search arena populated with 30 candidate sites; one of the sites holds
the target.  The drones execute the tours produced by
`model_1_random_infinite` (M1) or `model_4_auction_multi` with p/d or
p/d^2 bids (M4 / M4*) as defined in `main.py`.

This is a **kinematic replay**, not a flight simulator.  There is no PID
loop, no quaternion dynamics, no propeller wash.  Drones are rigid
bodies at fixed altitude 1.0 m that slide along straight lines at a
constant ground speed (default 2 m/s).  The goal is a clear, convincing
visual — suitable for a thesis defense — of *what the algorithms
actually do*.

## Contents

| File                   | Purpose                                                 |
| ---------------------- | ------------------------------------------------------- |
| `run_demo.py`          | Entry point (CLI).                                      |
| `scene.py`             | PyBullet scene construction + runtime mutators.         |
| `replay.py`            | Tour reconstruction + animation loop + matplotlib fallback. |
| `frames/`              | PNG output when `--record` is used.                     |
| `screenshots/`         | Hand-picked stills from a real run.                     |
| `example_instance.json`| Reproducible example instance (saved with `--save-instance`). |

## Installation

```bash
pip install pybullet
```

Also used: `numpy` and `matplotlib` (already transitive deps of the
thesis repo).  Frame PNGs are written through Pillow if available,
otherwise matplotlib's `imsave`.

> **Windows / Python 3.13 note.**  Upstream PyBullet does not yet ship a
> `cp313` wheel for Windows and building from source requires MSVC.  If
> `import pybullet` fails on your machine, `run_demo.py` automatically
> falls back to a pure-matplotlib top-down renderer that produces the
> same kind of PNG frames (see `--force-matplotlib`).  Every stills in
> `screenshots/` was generated via this fallback so the demo works on
> the thesis author's laptop today.

## Usage

### Basic (default = M4*, seed 42, 30 sites, 3 robots, E=14)

```bash
python pybullet_demo/run_demo.py
```

Opens a PyBullet GUI window and animates the drones completing the
Model 4* replay in real time.

### Head-less capture — a PNG per frame

```bash
python pybullet_demo/run_demo.py --headless --record
```

Writes `frame_00000.png`, `frame_00001.png`, … to `pybullet_demo/frames/`.
No display server required; works over SSH.

### Side-by-side: "watch M1 flail vs. M4* succeed"

```bash
python pybullet_demo/run_demo.py --compare M1,M4* --headless --record
```

This is the money demo for the thesis defense.  The two models run on
the **same instance** (same sites, same target, same priors); PyBullet
can only host one live world at a time, so the frames for each model go
to `frames/M1/` and `frames/M4star/` respectively.  Concatenate them
side-by-side with ffmpeg (see below) or splice them into a 2-pane video
in iMovie / DaVinci.

### Other useful flags

```bash
--seed N              # RNG seed (default 42)
--n 30 --r 3 --e 14   # sites / robots / energy budget
--model M4            # run M4 instead of M4*
--speed 2.0           # drone ground speed in m/s
--hz 240              # simulation step rate
--frame-every 8       # write 1 PNG every N sim steps
--save-instance FILE  # persist the generated instance to JSON
--load-instance FILE  # replay a previously saved instance
--force-matplotlib    # skip PyBullet entirely (fallback renderer)
```

## Stitching frames into a video

There is **no ffmpeg dependency in the demo itself**.  To turn the
PNGs into a video after the fact, run:

```bash
# single-model run
ffmpeg -framerate 60 -i pybullet_demo/frames/frame_%05d.png demo.mp4

# side-by-side after --compare
ffmpeg -framerate 60 -i pybullet_demo/frames/M1/frame_%05d.png m1.mp4
ffmpeg -framerate 60 -i pybullet_demo/frames/M4star/frame_%05d.png m4s.mp4
ffmpeg -i m1.mp4 -i m4s.mp4 -filter_complex hstack compare.mp4
```

## What you are looking at

- **Yellow cylinders**: candidate sites.  Height ∝ prior probability
  `node_probs[i]`.
- **Grey cylinder**: site that has been visited (belief set to zero by
  Bayesian update).
- **Bright yellow + gold sphere**: the target site, once the finder
  reaches it.
- **Red / blue / green squares**: the three robot bases.
- **Red / blue / green drones**: one quadcopter per robot, colour-
  matched to its base.
- **Overlay text** (via `pybullet.addUserDebugText`): current round and
  running fleet competitive ratio (FCR = total distance walked / d_opt).

## Sample stills

`screenshots/01_initial_scene.png` through
`screenshots/04_replay_finished.png` show the full arc of the default
M4* run (seed 42).  They cover:

1. **01_initial_scene** — all 30 sites visible, 3 drones parked at
   their bases, target highlighted in gold.
2. **02_drones_in_flight** — drones partway through their greedy
   chains; a couple of sites already visited (grey).
3. **03_target_found** — green drone has reached the target; overlay
   reads "target found by robot 2".
4. **04_replay_finished** — end-of-sortie, final FCR printed.

## Design notes

- **Why matplotlib fallback?**  The thesis author's machine cannot
  currently install PyBullet (CPython 3.13 + no MSVC).  Rather than
  produce a demo that is unrunnable on the very laptop used for the
  defense, the code path probes for pybullet at import time and quietly
  switches renderers.  The two renderers consume the same `Replay`
  object, so switching does not change the animation semantics.
- **Why a thin re-implementation of M1 / M4 in `replay.py`?**  `main.py`
  records only aggregate round statistics; it does not keep the full
  (robot → tour) mapping.  `replay.py` replays the algorithms with
  identical logic and records waypoints.  Re-seeding with `random.seed`
  before each call keeps the two worlds lock-step.
- **Why no real drone dynamics?**  The thesis is about search-strategy
  competitive ratios, not low-level flight control.  A rigid-body
  translation animation communicates the algorithmic behaviour just as
  well as a full PID quadrotor and costs orders of magnitude less code.
