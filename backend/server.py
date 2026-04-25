"""
FastAPI backend for Multi-Robot SAR Simulation.
Wraps simulation logic from main.py, exposes REST API for visualization.

Endpoints:
  POST /api/simulate  — run full simulation, return all rounds
  POST /api/step      — session-based step-through replay
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
import sys
import os
import uuid
import math
import random
import numpy as np

# ── Import simulation primitives from main.py ──────────────────────────────────
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import (
    euclidean_distance,
    generate_instance,
    bayesian_update,
    run_auction,
    bid_p_over_d,
    bid_p_over_d2,
    entropy,
)

# ── App setup ──────────────────────────────────────────────────────────────────
app = FastAPI(title="SAR Simulation API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request / Response schemas ─────────────────────────────────────────────────
class SimParams(BaseModel):
    n_nodes:    int   = Field(default=20,  ge=5,  le=100)
    n_robots:   int   = Field(default=3,   ge=1,  le=10)
    energy:     float = Field(default=15.0, ge=1.0, le=200.0)
    area_scale: float = Field(default=10.0, ge=1.0, le=50.0)
    seed:       int   = Field(default=42)
    model:      str   = Field(default="M4*")


class StepRequest(BaseModel):
    session_id: Optional[str] = None
    params:     Optional[SimParams] = None   # required for first call
    direction:  str = "next"                 # "next" | "prev"


# ── In-memory session store ────────────────────────────────────────────────────
# { session_id: { "data": SimResult, "cursor": int } }
sessions: Dict[str, Dict[str, Any]] = {}


# ── Helpers ────────────────────────────────────────────────────────────────────
def _serialize_instance(instance: dict, area_scale: float) -> dict:
    return {
        "nodes": [
            {
                "id": i,
                "x": instance["node_positions"][i][0],
                "y": instance["node_positions"][i][1],
                "prob": instance["node_probs"][i],
            }
            for i in sorted(instance["node_positions"])
        ],
        "bases": [
            {"id": r, "x": instance["bases"][r][0], "y": instance["bases"][r][1]}
            for r in sorted(instance["bases"])
        ],
        "target":       instance["target"],
        "area_scale":   area_scale,
        "optimal_dist": instance["optimal_dist"],
    }


def _build_round(
    iteration: int,
    probs_before: dict,
    robot_tours_ids: dict,      # {robot_id (int): [node_id, ...]}
    visited_this_round: list,
    all_visited: list,
    target_found: bool,
    finder: Optional[int],
    robot_dists: dict,
    optimal_dist: float,
    robot_positions: Optional[dict] = None,  # M2 only
) -> dict:
    fcr = None
    if target_found and finder is not None:
        fd = robot_dists[finder]
        fcr = fd / optimal_dist if optimal_dist > 1e-9 else None

    ent = entropy(probs_before)

    return {
        "round":              iteration,
        "probs_before":       {str(k): v for k, v in probs_before.items()},
        "entropy_before":     ent,
        "robot_tours":        {str(r): robot_tours_ids[r] for r in robot_tours_ids},
        "visited_this_round": visited_this_round,
        "all_visited":        all_visited,
        "target_found":       target_found,
        "finder":             finder,
        "fcr":                fcr,
        "robot_total_dist":   {str(r): robot_dists[r] for r in robot_dists},
        **({"robot_positions": {str(r): list(pos) for r, pos in robot_positions.items()}}
           if robot_positions else {}),
    }


# ── Rich simulation functions ──────────────────────────────────────────────────

def _run_m1_rich(instance: dict) -> dict:
    """M1: Infinite energy, no coordination (random baseline)."""
    np_  = instance["node_positions"]
    probs = dict(instance["node_probs"])
    bases = instance["bases"]
    target = instance["target"]
    opt  = instance["optimal_dist"]
    n_robots = len(bases)

    available     = set(np_.keys())
    robot_dists   = {r: 0.0 for r in range(n_robots)}
    all_visited_set: set  = set()
    all_visited_lst: list = []
    rounds: list = []
    iteration = 0

    while available:
        iteration += 1
        if iteration > 500:
            break

        probs_before = dict(probs)
        avail_list   = list(available)
        weights      = [probs.get(n, 0) for n in avail_list]
        total_w      = sum(weights)
        if total_w < 1e-12:
            break
        weights = [w / total_w for w in weights]

        found, finder        = False, None
        visited_this_round   = []
        robot_tours_ids      = {r: [] for r in range(n_robots)}

        for r in range(n_robots):
            choice = random.choices(avail_list, weights=weights, k=1)[0]
            d      = euclidean_distance(bases[r], np_[choice])
            robot_tours_ids[r] = [choice]

            if choice == target:
                robot_dists[r] += d
                found, finder = True, r
                if choice not in visited_this_round:
                    visited_this_round.append(choice)
                break
            else:
                robot_dists[r] += 2 * d
                if choice not in visited_this_round:
                    visited_this_round.append(choice)

        for n in visited_this_round:
            if n not in all_visited_set:
                all_visited_set.add(n)
                all_visited_lst.append(n)

        probs     = bayesian_update(probs, set(visited_this_round))
        available -= set(visited_this_round)

        rounds.append(_build_round(
            iteration, probs_before, robot_tours_ids,
            visited_this_round, list(all_visited_lst),
            found, finder, robot_dists, opt,
        ))
        if found:
            break

    return {
        "model":            "M1",
        "rounds":           rounds,
        "found":            any(r["target_found"] for r in rounds),
        "final_fcr":        rounds[-1]["fcr"] if rounds and rounds[-1]["target_found"] else None,
        "total_iterations": iteration,
    }


def _run_m2_rich(instance: dict) -> dict:
    """M2: Infinite energy, SSI auction, node-to-node movement."""
    np_  = instance["node_positions"]
    probs = dict(instance["node_probs"])
    bases = instance["bases"]
    target = instance["target"]
    opt  = instance["optimal_dist"]
    n_robots = len(bases)

    available     = set(np_.keys())
    robot_pos     = {r: bases[r] for r in range(n_robots)}
    robot_dists   = {r: 0.0 for r in range(n_robots)}
    all_visited_set: set  = set()
    all_visited_lst: list = []
    rounds: list = []
    iteration = 0

    while available:
        iteration += 1
        probs_before = dict(probs)

        robot_bids = {}
        for r in range(n_robots):
            bids = []
            for n in available:
                d  = euclidean_distance(robot_pos[r], np_[n])
                if d > 0 and probs.get(n, 0) > 0:
                    bv = bid_p_over_d(probs[n], d)
                    bids.append((n, bv, d))
            bids.sort(key=lambda x: x[1], reverse=True)
            robot_bids[r] = bids

        if all(len(b) == 0 for b in robot_bids.values()):
            break
        assigned = run_auction(robot_bids)
        if not assigned:
            break

        found, finder      = False, None
        visited_this_round = []
        robot_tours_ids    = {r: [] for r in range(n_robots)}

        for r, (n, d) in assigned.items():
            robot_dists[r]      += d
            robot_pos[r]         = np_[n]
            robot_tours_ids[r]   = [n]
            if n not in visited_this_round:
                visited_this_round.append(n)
            if n == target:
                found, finder = True, r

        for n in visited_this_round:
            if n not in all_visited_set:
                all_visited_set.add(n)
                all_visited_lst.append(n)

        probs     = bayesian_update(probs, set(visited_this_round))
        available -= set(visited_this_round)

        rounds.append(_build_round(
            iteration, probs_before, robot_tours_ids,
            visited_this_round, list(all_visited_lst),
            found, finder, robot_dists, opt,
            robot_positions={r: robot_pos[r] for r in range(n_robots)},
        ))
        if found:
            break

    return {
        "model":            "M2",
        "rounds":           rounds,
        "found":            any(r["target_found"] for r in rounds),
        "final_fcr":        rounds[-1]["fcr"] if rounds and rounds[-1]["target_found"] else None,
        "total_iterations": iteration,
    }


def _run_m3_rich(instance: dict, energy: float,
                 bid_func=bid_p_over_d, model_name: str = "M3") -> dict:
    """M3: Finite energy, SSI auction, single-node sorties."""
    np_  = instance["node_positions"]
    probs = dict(instance["node_probs"])
    bases = instance["bases"]
    target = instance["target"]
    opt  = instance["optimal_dist"]
    n_robots = len(bases)

    available     = set(np_.keys())
    robot_dists   = {r: 0.0 for r in range(n_robots)}
    all_visited_set: set  = set()
    all_visited_lst: list = []
    rounds: list = []
    iteration = 0

    while available:
        iteration += 1
        probs_before = dict(probs)

        robot_bids = {}
        for r in range(n_robots):
            bids = []
            for n in available:
                d  = euclidean_distance(bases[r], np_[n])
                if 2 * d <= energy and d > 0 and probs.get(n, 0) > 0:
                    bv = bid_func(probs[n], d, energy)
                    bids.append((n, bv, d))
            bids.sort(key=lambda x: x[1], reverse=True)
            robot_bids[r] = bids

        if all(len(b) == 0 for b in robot_bids.values()):
            break
        assigned = run_auction(robot_bids)
        if not assigned:
            break

        found, finder      = False, None
        visited_this_round = []
        robot_tours_ids    = {r: [] for r in range(n_robots)}

        for r, (n, d) in assigned.items():
            robot_tours_ids[r] = [n]
            if n not in visited_this_round:
                visited_this_round.append(n)
            if n == target:
                robot_dists[r] += d
                found, finder = True, r
            else:
                robot_dists[r] += 2 * d

        for n in visited_this_round:
            if n not in all_visited_set:
                all_visited_set.add(n)
                all_visited_lst.append(n)

        probs     = bayesian_update(probs, set(visited_this_round))
        available -= set(visited_this_round)

        rounds.append(_build_round(
            iteration, probs_before, robot_tours_ids,
            visited_this_round, list(all_visited_lst),
            found, finder, robot_dists, opt,
        ))
        if found:
            break

    return {
        "model":            model_name,
        "rounds":           rounds,
        "found":            any(r["target_found"] for r in rounds),
        "final_fcr":        rounds[-1]["fcr"] if rounds and rounds[-1]["target_found"] else None,
        "total_iterations": iteration,
    }


def _run_m4_rich(instance: dict, energy: float,
                 bid_func=bid_p_over_d, model_name: str = "M4") -> dict:
    """M4 / M4*: Finite energy, SSI auction + greedy chain, multi-node sorties."""
    np_  = instance["node_positions"]
    probs = dict(instance["node_probs"])
    bases = instance["bases"]
    target = instance["target"]
    opt  = instance["optimal_dist"]
    n_robots = len(bases)

    available     = set(np_.keys())
    robot_dists   = {r: 0.0 for r in range(n_robots)}
    all_visited_set: set  = set()
    all_visited_lst: list = []
    rounds: list = []
    iteration = 0

    while available:
        iteration += 1
        probs_before = dict(probs)

        # Phase 1 — SSI auction for first node
        robot_bids = {}
        for r in range(n_robots):
            bids = []
            for n in available:
                d  = euclidean_distance(bases[r], np_[n])
                if 2 * d <= energy and d > 0 and probs.get(n, 0) > 0:
                    bv = bid_func(probs[n], d, energy)
                    bids.append((n, bv, d))
            bids.sort(key=lambda x: x[1], reverse=True)
            robot_bids[r] = bids

        if all(len(b) == 0 for b in robot_bids.values()):
            break
        first_assigned = run_auction(robot_bids)
        if not first_assigned:
            break

        # Phase 2 — Greedy chain extension
        # internal_tours: {r: [(node_id, dist_from_prev), ...]}
        all_claimed   = set(n for n, _ in first_assigned.values())
        internal_tours: Dict[int, list] = {}
        robot_rem:      Dict[int, float] = {}
        robot_pos_cur:  Dict[int, tuple] = {}

        for r, (node, dist) in first_assigned.items():
            internal_tours[r]  = [(node, dist)]
            robot_pos_cur[r]   = np_[node]
            robot_rem[r]       = energy - dist

        active = set(first_assigned.keys())
        while active:
            progress = False
            for r in list(active):
                best_node, best_bid, best_d = None, -1.0, 0.0
                for n in available - all_claimed:
                    d_to   = euclidean_distance(robot_pos_cur[r], np_[n])
                    d_back = euclidean_distance(np_[n], bases[r])
                    if d_to + d_back <= robot_rem[r] and d_to > 0 and probs.get(n, 0) > 0:
                        bv = bid_func(probs[n], d_to, energy)
                        if bv > best_bid:
                            best_bid, best_d, best_node = bv, d_to, n
                if best_node is None:
                    active.discard(r)
                else:
                    internal_tours[r].append((best_node, best_d))
                    all_claimed.add(best_node)
                    robot_rem[r]      -= best_d
                    robot_pos_cur[r]   = np_[best_node]
                    progress = True
            if not progress:
                break

        # API-facing: just node IDs per robot
        robot_tours_ids = {
            r: [n for n, _ in internal_tours.get(r, [])]
            for r in range(n_robots)
        }

        # Phase 3 — Execute tours
        found, finder      = False, None
        visited_this_round = []

        for r, tour_wd in internal_tours.items():
            found_in_this = False
            for node, d in tour_wd:
                robot_dists[r] += d
                if node not in visited_this_round:
                    visited_this_round.append(node)
                if node == target:
                    found, finder, found_in_this = True, r, True
                    break
            if not found_in_this and tour_wd:
                last_node = tour_wd[-1][0]
                robot_dists[r] += euclidean_distance(np_[last_node], bases[r])

        for n in visited_this_round:
            if n not in all_visited_set:
                all_visited_set.add(n)
                all_visited_lst.append(n)

        probs     = bayesian_update(probs, set(visited_this_round))
        available -= set(visited_this_round)

        rounds.append(_build_round(
            iteration, probs_before, robot_tours_ids,
            visited_this_round, list(all_visited_lst),
            found, finder, robot_dists, opt,
        ))
        if found:
            break

    return {
        "model":            model_name,
        "rounds":           rounds,
        "found":            any(r["target_found"] for r in rounds),
        "final_fcr":        rounds[-1]["fcr"] if rounds and rounds[-1]["target_found"] else None,
        "total_iterations": iteration,
    }


# ── Core dispatcher ────────────────────────────────────────────────────────────

def _dispatch(params: SimParams) -> dict:
    """Generate instance + run selected model, return full result."""
    instance = generate_instance(
        params.n_nodes,
        params.n_robots,
        params.area_scale,
        seed=params.seed,
        max_opt_dist=params.energy / 2,
    )
    model = params.model
    E     = params.energy

    if model == "M1":
        sim = _run_m1_rich(instance)
    elif model == "M2":
        sim = _run_m2_rich(instance)
    elif model == "M3":
        sim = _run_m3_rich(instance, E, bid_p_over_d, "M3")
    elif model == "M4":
        sim = _run_m4_rich(instance, E, bid_p_over_d, "M4")
    elif model == "M4*":
        sim = _run_m4_rich(instance, E, bid_p_over_d2, "M4*")
    else:
        raise ValueError(f"Unknown model: {model}")

    sim["instance"] = _serialize_instance(instance, params.area_scale)
    return sim


# ── API endpoints ──────────────────────────────────────────────────────────────

@app.post("/api/simulate")
async def simulate(params: SimParams):
    """
    Run a full simulation and return all rounds.
    The frontend stores all rounds and steps through them locally.
    """
    try:
        result = _dispatch(params)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/step")
async def step(req: StepRequest):
    """
    Session-based step-through.
    - First call: send params (no session_id) → creates session, returns step 0
    - Subsequent calls: send session_id + direction ("next" | "prev")
    """
    if req.session_id is None:
        # New session
        if req.params is None:
            raise HTTPException(400, "params required for first call")
        result = _dispatch(req.params)
        sid    = str(uuid.uuid4())
        sessions[sid] = {"data": result, "cursor": 0}
        return {
            "session_id":   sid,
            "cursor":       0,
            "total_rounds": len(result["rounds"]),
            "step":         result["rounds"][0] if result["rounds"] else None,
            "instance":     result["instance"],
            "model":        result["model"],
            "found":        result["found"],
            "final_fcr":    result["final_fcr"],
        }
    else:
        if req.session_id not in sessions:
            raise HTTPException(404, "Session not found")
        sess   = sessions[req.session_id]
        rounds = sess["data"]["rounds"]
        cursor = sess["cursor"]

        if req.direction == "next":
            cursor = min(cursor + 1, len(rounds) - 1)
        elif req.direction == "prev":
            cursor = max(cursor - 1, 0)

        sess["cursor"] = cursor
        return {
            "session_id":   req.session_id,
            "cursor":       cursor,
            "total_rounds": len(rounds),
            "step":         rounds[cursor] if rounds else None,
            "instance":     sess["data"]["instance"],
            "model":        sess["data"]["model"],
            "found":        sess["data"]["found"],
            "final_fcr":    sess["data"]["final_fcr"],
        }


@app.get("/api/health")
async def health():
    return {"status": "ok"}
