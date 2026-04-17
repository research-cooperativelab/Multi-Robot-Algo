"""
Round-by-round replay of a multi-robot search run.

This module performs two jobs:

1. **Tour reconstruction.**  ``main.py`` stores only aggregate per-round
   statistics; it does not retain the actual (robot, site-sequence) tours
   that the algorithms walked.  To animate the drones we re-run a thin
   transparent copy of each model and record the tour as a list of
   waypoints per robot per round.

2. **Replay loop.**  ``run_replay`` walks a tour structure at a fixed
   ground-speed (metres / second) and, at every simulation step, updates
   drone poses + site colours + overlay text.  Optionally dumps a PNG per
   frame (``record=True``).  If PyBullet is unavailable on the host
   machine, falls back to a matplotlib top-down renderer that produces
   structurally identical frames so the demo remains usable.

The reconstruction functions mirror the logic of the originals byte-for-
byte (same RNG seed, same auction, same greedy chain) so that what the
viewer sees is *exactly* the sequence the simulation computed.
"""

from __future__ import annotations

import math
import os
import random
import time
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Tuple

import numpy as np

# Import main.py's helpers (distance function, bid functions, auction,
# Bayesian update).  We only use the *primitives* -- the tour-building
# loops are reimplemented here so we can record waypoints.
import main as mr

from scene import (
    PYBULLET_AVAILABLE, SceneHandles, ROBOT_COLORS,
    ARENA_SIZE, DRONE_ALT,
    build_scene, capture_frame, mark_site_visited, set_drone_pose,
    update_overlay, yaw_towards, disconnect,
)


# ---------------------------------------------------------------------------
# Tour record types
# ---------------------------------------------------------------------------

@dataclass
class RobotTour:
    robot: int
    waypoints: List[Tuple[float, float]]   # xy waypoints, starting at base
    sites: List[int]                       # site id for each non-base waypoint
    returns_to_base: bool                  # False if this robot found target


@dataclass
class RoundReplay:
    round_idx: int
    tours: List[RobotTour]
    found_target: bool
    finder: Optional[int]
    finder_site: Optional[int]


@dataclass
class Replay:
    model: str
    rounds: List[RoundReplay]
    final_fcr: float
    optimal_dist: float


# ---------------------------------------------------------------------------
# Model 1 reconstruction (random, independent)
# ---------------------------------------------------------------------------

def build_replay_m1(instance: dict) -> Replay:
    # Re-seed matches main.py's expectation: callers seed once before the
    # first model call.  We assume the caller already did `random.seed`.
    np_ = instance["node_positions"]
    probs = dict(instance["node_probs"])
    bases = instance["bases"]
    target = instance["target"]
    opt = instance["optimal_dist"]
    n_robots = len(bases)

    available = set(np_.keys())
    robot_dists = {r: 0.0 for r in range(n_robots)}
    rounds: List[RoundReplay] = []
    iteration = 0

    while available:
        iteration += 1
        if iteration > 1000:
            break

        avail_list = list(available)
        avail_weights = [probs.get(n, 0) for n in avail_list]
        total_w = sum(avail_weights)
        if total_w < 1e-12:
            break
        avail_weights = [w / total_w for w in avail_weights]

        found, finder, finder_site = False, None, None
        tours: List[RobotTour] = []
        visited_this_round = set()

        for r in range(n_robots):
            choice = random.choices(avail_list, weights=avail_weights, k=1)[0]
            d = mr.euclidean_distance(bases[r], np_[choice])
            base_xy = (float(bases[r][0]), float(bases[r][1]))
            site_xy = (float(np_[choice][0]), float(np_[choice][1]))

            if choice == target and not found:
                robot_dists[r] += d
                tours.append(RobotTour(
                    robot=r, waypoints=[base_xy, site_xy],
                    sites=[choice], returns_to_base=False,
                ))
                found, finder, finder_site = True, r, choice
                visited_this_round.add(choice)
                # Other robots still flew this round too, but M1 stops at
                # the first finder in main.py.  We omit un-executed robots.
                break
            else:
                robot_dists[r] += 2 * d
                tours.append(RobotTour(
                    robot=r, waypoints=[base_xy, site_xy, base_xy],
                    sites=[choice], returns_to_base=True,
                ))
                visited_this_round.add(choice)

        probs = mr.bayesian_update(probs, visited_this_round)
        available -= visited_this_round

        rounds.append(RoundReplay(
            round_idx=iteration, tours=tours,
            found_target=found, finder=finder, finder_site=finder_site,
        ))

        if found:
            break

    total = sum(robot_dists.values())
    fcr = total / opt if opt > 0 else float("inf")
    return Replay(model="M1", rounds=rounds, final_fcr=fcr, optimal_dist=opt)


# ---------------------------------------------------------------------------
# Model 4 / 4* reconstruction (auction + greedy chain)
# ---------------------------------------------------------------------------

def build_replay_m4(
    instance: dict, energy: float,
    bid_func: Callable = mr.bid_p_over_d2,
    label: str = "M4*",
) -> Replay:
    np_ = instance["node_positions"]
    probs = dict(instance["node_probs"])
    bases = instance["bases"]
    target = instance["target"]
    opt = instance["optimal_dist"]
    n_robots = len(bases)

    available = set(np_.keys())
    robot_dists = {r: 0.0 for r in range(n_robots)}
    rounds: List[RoundReplay] = []
    iteration = 0

    while available:
        iteration += 1

        # Phase 1: SSI Auction --------------------------------------------
        robot_bids = {}
        for r in range(n_robots):
            bids = []
            for n in available:
                d = mr.euclidean_distance(bases[r], np_[n])
                if 2 * d <= energy and d > 0 and probs.get(n, 0) > 0:
                    bv = bid_func(probs[n], d, energy)
                    bids.append((n, bv, d))
            bids.sort(key=lambda x: x[1], reverse=True)
            robot_bids[r] = bids

        if all(len(b) == 0 for b in robot_bids.values()):
            break
        first_assigned = mr.run_auction(robot_bids)
        if not first_assigned:
            break

        # Phase 2: Greedy chain -------------------------------------------
        all_claimed = set(n for n, _ in first_assigned.values())
        robot_tour_nodes: Dict[int, List[Tuple[int, float]]] = {}
        robot_rem: Dict[int, float] = {}
        robot_pos: Dict[int, Tuple[float, float]] = {}

        for r, (node, dist) in first_assigned.items():
            robot_tour_nodes[r] = [(node, dist)]
            robot_pos[r] = np_[node]
            robot_rem[r] = energy - dist

        active = set(first_assigned.keys())
        while active:
            progress = False
            for r in list(active):
                best_node, best_bid, best_d = None, -1, 0
                for n in available - all_claimed:
                    d_to = mr.euclidean_distance(robot_pos[r], np_[n])
                    d_back = mr.euclidean_distance(np_[n], bases[r])
                    if (d_to + d_back <= robot_rem[r]
                            and d_to > 0 and probs.get(n, 0) > 0):
                        bv = bid_func(probs[n], d_to, energy)
                        if bv > best_bid:
                            best_bid, best_d, best_node = bv, d_to, n
                if best_node is None:
                    active.discard(r)
                else:
                    robot_tour_nodes[r].append((best_node, best_d))
                    all_claimed.add(best_node)
                    robot_rem[r] -= best_d
                    robot_pos[r] = np_[best_node]
                    progress = True
            if not progress:
                break

        # Phase 3: Execute tours ------------------------------------------
        found, finder, finder_site = False, None, None
        visited: set = set()
        tours: List[RobotTour] = []

        for r, tour_nodes in robot_tour_nodes.items():
            base_xy = (float(bases[r][0]), float(bases[r][1]))
            waypoints = [base_xy]
            sites = []
            returns = True
            hit_target = False
            for node, d in tour_nodes:
                waypoints.append((float(np_[node][0]), float(np_[node][1])))
                sites.append(node)
                robot_dists[r] += d
                visited.add(node)
                if node == target and not found:
                    found, finder, finder_site = True, r, node
                    hit_target = True
                    break
            if hit_target:
                returns = False  # finder stops mid-tour
            else:
                if tour_nodes:
                    last_node = tour_nodes[-1][0]
                    robot_dists[r] += mr.euclidean_distance(np_[last_node], bases[r])
                    waypoints.append(base_xy)

            tours.append(RobotTour(
                robot=r, waypoints=waypoints,
                sites=sites, returns_to_base=returns,
            ))

        probs = mr.bayesian_update(probs, visited)
        available -= visited

        rounds.append(RoundReplay(
            round_idx=iteration, tours=tours,
            found_target=found, finder=finder, finder_site=finder_site,
        ))

        if found:
            break

    total = sum(robot_dists.values())
    fcr = total / opt if opt > 0 else float("inf")
    return Replay(model=label, rounds=rounds, final_fcr=fcr, optimal_dist=opt)


# ---------------------------------------------------------------------------
# Dispatch
# ---------------------------------------------------------------------------

def build_replay(model: str, instance: dict, energy: float) -> Replay:
    m = model.upper()
    if m == "M1":
        return build_replay_m1(instance)
    if m == "M4":
        return build_replay_m4(instance, energy,
                               bid_func=mr.bid_p_over_d, label="M4")
    if m in ("M4*", "M4STAR"):
        return build_replay_m4(instance, energy,
                               bid_func=mr.bid_p_over_d2, label="M4*")
    raise ValueError(f"Unsupported model {model!r}; choose M1, M4, or M4*.")


# ---------------------------------------------------------------------------
# Main replay loop (PyBullet path)
# ---------------------------------------------------------------------------

def _accumulate_running_fcr(replay: Replay, upto_round: int,
                            upto_dist: float) -> float:
    """FCR so far = total distance walked / optimal."""
    if replay.optimal_dist <= 0:
        return float("inf")
    return upto_dist / replay.optimal_dist


def run_replay(
    replay: Replay,
    instance: dict,
    *,
    mode: str = "GUI",
    speed_mps: float = 2.0,
    hz: int = 240,
    record: bool = False,
    frames_dir: str = "pybullet_demo/frames",
    frame_every: int = 8,
    capture_width: int = 960,
    capture_height: int = 540,
    title_prefix: str = "",
) -> int:
    """Animate a pre-built Replay.  Returns the number of PNG frames
    written to disk (0 if ``record`` is False)."""

    if not PYBULLET_AVAILABLE:
        raise RuntimeError("pybullet not available in this interpreter.")

    handles = build_scene(instance, mode=mode)
    dt = 1.0 / hz
    step_dist = speed_mps * dt  # metres per sim-step
    total_dist = 0.0
    frames_written = 0

    if record:
        os.makedirs(frames_dir, exist_ok=True)

    try:
        for rnd in replay.rounds:
            # Active trackers for the concurrent robots this round
            state = {}
            for tour in rnd.tours:
                state[tour.robot] = {
                    "tour": tour,
                    "seg": 0,              # current waypoint index
                    "progress": 0.0,       # metres walked along current seg
                    "done": len(tour.waypoints) <= 1,
                }
            step = 0
            while any(not s["done"] for s in state.values()):
                for r, s in state.items():
                    if s["done"]:
                        continue
                    tour: RobotTour = s["tour"]
                    a = tour.waypoints[s["seg"]]
                    b = tour.waypoints[s["seg"] + 1]
                    seg_len = math.hypot(b[0] - a[0], b[1] - a[1])
                    s["progress"] += step_dist
                    if seg_len <= 1e-6 or s["progress"] >= seg_len:
                        total_dist += max(0.0, seg_len - (s["progress"] - step_dist))
                        # Snap to b, mark visited if this was a site stop
                        set_drone_pose(handles, r, b[0], b[1],
                                       yaw_towards(a, b))
                        site_idx = s["seg"]  # seg i means arriving at wp i+1
                        if site_idx < len(tour.sites):
                            node = tour.sites[site_idx]
                            is_tgt = (rnd.finder == r and rnd.finder_site == node)
                            mark_site_visited(handles, node, is_target=is_tgt)
                        s["seg"] += 1
                        s["progress"] = 0.0
                        if s["seg"] >= len(tour.waypoints) - 1:
                            s["done"] = True
                    else:
                        # Interpolate
                        t = s["progress"] / seg_len
                        x = a[0] + t * (b[0] - a[0])
                        y = a[1] + t * (b[1] - a[1])
                        set_drone_pose(handles, r, x, y, yaw_towards(a, b))
                        total_dist += step_dist

                # Overlay
                fcr = _accumulate_running_fcr(replay, rnd.round_idx, total_dist)
                lines = [
                    f"{title_prefix}{replay.model}   round {rnd.round_idx}",
                    f"running FCR = {fcr:5.2f}  (target d_opt={replay.optimal_dist:.2f})",
                ]
                if rnd.found_target:
                    lines.append(f"target found by robot {rnd.finder}")
                update_overlay(handles, lines)

                # Step the physics (even though nothing is dynamic -- keeps
                # the GUI responsive)
                import pybullet as p
                p.stepSimulation()

                if record and (step % frame_every == 0):
                    path = os.path.join(
                        frames_dir, f"frame_{frames_written:05d}.png",
                    )
                    capture_frame(handles, path, capture_width, capture_height)
                    frames_written += 1
                step += 1
                if mode.upper() == "GUI":
                    time.sleep(dt)
    finally:
        disconnect()

    return frames_written


# ---------------------------------------------------------------------------
# Matplotlib fallback (used only when PyBullet is not installable)
# ---------------------------------------------------------------------------

def run_replay_matplotlib(
    replay: Replay,
    instance: dict,
    *,
    frames_dir: str,
    speed_mps: float = 2.0,
    hz: int = 60,
    frame_every: int = 4,
    capture_width: int = 960,
    capture_height: int = 540,
    title_prefix: str = "",
) -> int:
    """Top-down PNG renderer that mimics the PyBullet frames.

    Used only when ``pybullet`` is not importable on the host (the CPython
    3.13 / no-MSVC case on Windows).  It consumes the exact same ``Replay``
    object as the PyBullet path so switching renderers does not change the
    animation semantics.
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Circle, Rectangle

    os.makedirs(frames_dir, exist_ok=True)
    np_positions = instance["node_positions"]
    bases = instance["bases"]
    probs = instance["node_probs"]
    target = instance["target"]
    max_p = max(probs.values()) if probs else 1.0

    # Per-site state that evolves during the replay
    site_state: Dict[int, str] = {n: "unvisited" for n in np_positions}

    dt = 1.0 / hz
    step_dist = speed_mps * dt
    total_dist = 0.0
    frames_written = 0

    dpi = 100
    figw = capture_width / dpi
    figh = capture_height / dpi

    drone_xy: Dict[int, Tuple[float, float]] = {
        r: (float(b[0]), float(b[1])) for r, b in bases.items()
    }

    def _render_frame(round_idx, running_fcr, finder_text, path):
        fig, ax = plt.subplots(figsize=(figw, figh), dpi=dpi)
        ax.set_facecolor("#16181d")
        fig.patch.set_facecolor("#0c0d10")
        ax.set_xlim(-0.5, ARENA_SIZE + 0.5)
        ax.set_ylim(-0.5, ARENA_SIZE + 0.5)
        ax.set_aspect("equal")
        ax.grid(color="#2a2c33", linewidth=0.5, zorder=0)
        ax.tick_params(colors="#d0d2d7", labelsize=7)
        for spine in ax.spines.values():
            spine.set_color("#2a2c33")

        # Sites
        for n, (x, y) in np_positions.items():
            state = site_state[n]
            if n == target and state != "found":
                color = "#f0c924"  # gold target
                edge = "#ffd743"
            elif state == "found":
                color = "#fff352"
                edge = "#ffff99"
            elif state == "visited":
                color = "#707075"
                edge = "#55555a"
            else:
                color = "#d4c648"
                edge = "#a89a20"
            r_vis = 0.12 + 0.40 * (probs[n] / max_p)
            ax.add_patch(Circle((x, y), r_vis, color=color,
                                ec=edge, lw=1.0, zorder=2))

        # Bases
        for r, (bx, by) in bases.items():
            col = ROBOT_COLORS[r % len(ROBOT_COLORS)]
            mpl_col = (col[0], col[1], col[2])
            ax.add_patch(Rectangle(
                (bx - 0.25, by - 0.25), 0.5, 0.5, color=mpl_col,
                alpha=0.55, ec="white", lw=0.8, zorder=3,
            ))

        # Drones
        for r, (dx, dy) in drone_xy.items():
            col = ROBOT_COLORS[r % len(ROBOT_COLORS)]
            mpl_col = (col[0], col[1], col[2])
            ax.scatter([dx], [dy], s=170, c=[mpl_col], marker="o",
                       edgecolors="white", linewidths=1.3, zorder=5)
            ax.scatter([dx], [dy], s=30, c="white", marker="x",
                       linewidths=1.0, zorder=6)

        # Overlay text (offset slightly to avoid axis tick labels)
        ax.text(0.05, 0.96,
                f"{title_prefix}{replay.model}   round {round_idx}",
                transform=ax.transAxes, color="white",
                fontsize=12, fontweight="bold", va="top",
                bbox=dict(facecolor="#1d1f25", edgecolor="none",
                          alpha=0.85, pad=3))
        ax.text(0.05, 0.90,
                f"running FCR = {running_fcr:5.2f}   d_opt = {replay.optimal_dist:.2f}",
                transform=ax.transAxes, color="#d0d2d7",
                fontsize=10, va="top",
                bbox=dict(facecolor="#1d1f25", edgecolor="none",
                          alpha=0.85, pad=3))
        if finder_text:
            ax.text(0.05, 0.84, finder_text, transform=ax.transAxes,
                    color="#ffe466", fontsize=10, va="top",
                    fontweight="bold",
                    bbox=dict(facecolor="#1d1f25", edgecolor="none",
                              alpha=0.85, pad=3))

        ax.set_title(
            f"Multi-robot search  |  {replay.model}  |  arena {ARENA_SIZE:.0f}x{ARENA_SIZE:.0f} m",
            color="white", fontsize=10,
        )
        fig.tight_layout()
        fig.savefig(path, dpi=dpi, facecolor=fig.get_facecolor())
        plt.close(fig)

    for rnd in replay.rounds:
        state = {}
        for tour in rnd.tours:
            state[tour.robot] = {
                "tour": tour, "seg": 0, "progress": 0.0,
                "done": len(tour.waypoints) <= 1,
            }
        step = 0
        finder_text = ""
        while any(not s["done"] for s in state.values()):
            for r, s in state.items():
                if s["done"]:
                    continue
                tour = s["tour"]
                a = tour.waypoints[s["seg"]]
                b = tour.waypoints[s["seg"] + 1]
                seg_len = math.hypot(b[0] - a[0], b[1] - a[1])
                s["progress"] += step_dist
                if seg_len <= 1e-6 or s["progress"] >= seg_len:
                    total_dist += max(0.0, seg_len - (s["progress"] - step_dist))
                    drone_xy[r] = (b[0], b[1])
                    site_idx = s["seg"]
                    if site_idx < len(tour.sites):
                        node = tour.sites[site_idx]
                        if rnd.finder == r and rnd.finder_site == node:
                            site_state[node] = "found"
                            finder_text = f"target found by robot {r}"
                        else:
                            site_state[node] = "visited"
                    s["seg"] += 1
                    s["progress"] = 0.0
                    if s["seg"] >= len(tour.waypoints) - 1:
                        s["done"] = True
                else:
                    t = s["progress"] / seg_len
                    drone_xy[r] = (a[0] + t * (b[0] - a[0]),
                                   a[1] + t * (b[1] - a[1]))
                    total_dist += step_dist

            if step % frame_every == 0:
                running_fcr = _accumulate_running_fcr(
                    replay, rnd.round_idx, total_dist,
                )
                path = os.path.join(
                    frames_dir, f"frame_{frames_written:05d}.png",
                )
                _render_frame(rnd.round_idx, running_fcr, finder_text, path)
                frames_written += 1
            step += 1

    # Final still so the last moment isn't mid-motion
    running_fcr = total_dist / replay.optimal_dist if replay.optimal_dist > 0 else 0.0
    path = os.path.join(frames_dir, f"frame_{frames_written:05d}.png")
    _render_frame(
        replay.rounds[-1].round_idx if replay.rounds else 0,
        running_fcr,
        f"FCR = {replay.final_fcr:.2f}   FIN",
        path,
    )
    frames_written += 1

    return frames_written
