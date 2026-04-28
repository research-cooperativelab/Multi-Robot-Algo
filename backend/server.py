"""
FastAPI backend for Multi-Robot SAR Simulation.
Wraps simulation logic from main.py, exposes REST API for visualization.

Endpoints:
  POST /api/simulate  — run full simulation, return all rounds
  POST /api/step      — session-based step-through replay
"""

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from pathlib import Path
import asyncio
import io
import shutil
import tempfile
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


# ── PyBullet 3-D demo endpoint ─────────────────────────────────────────────────

_REPO_ROOT   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DEMO_SCRIPT = os.path.join(_REPO_ROOT, "pybullet_demo", "run_demo.py")
_VID_SCRIPT  = os.path.join(_REPO_ROOT, "pybullet_demo", "make_video.py")
_PYBULLET_SEM = asyncio.Semaphore(2)   # max 2 concurrent renders

_ALLOWED_MODELS = {"M1", "M4", "M4star"}


class PyBulletRequest(BaseModel):
    model:   str   = Field(default="M4star")
    seed:    int   = Field(default=42)
    n:       int   = Field(default=20, ge=5,  le=50)
    r:       int   = Field(default=3,  ge=1,  le=5)
    e:       float = Field(default=14.0, ge=5.0, le=30.0)
    compare: bool  = Field(default=False)


async def _run_proc(args: list[str], timeout: int = 90) -> tuple[int, str]:
    proc = await asyncio.create_subprocess_exec(
        *args,
        cwd=_REPO_ROOT,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    except asyncio.TimeoutError:
        proc.kill()
        raise HTTPException(504, "Demo render timed out — try fewer sites or lower energy")
    return proc.returncode, (stderr or b"").decode()


@app.post("/api/pybullet")
async def run_pybullet_demo(req: PyBulletRequest):
    model = req.model.replace("M4*", "M4star")
    if model not in _ALLOWED_MODELS:
        raise HTTPException(400, f"Invalid model '{req.model}'. Choose M1, M4, or M4star.")

    common = [
        "--seed", str(req.seed),
        "--n",    str(req.n),
        "--r",    str(req.r),
        "--e",    str(req.e),
        "--headless", "--record", "--force-matplotlib",
    ]

    async with _PYBULLET_SEM:
        tmp = tempfile.mkdtemp(prefix="searchfcr_demo_")
        try:
            if req.compare:
                left_dir  = os.path.join(tmp, "M1")
                right_dir = os.path.join(tmp, model)
                for m, d in [("M1", left_dir), (model, right_dir)]:
                    rc, err = await _run_proc(
                        [sys.executable, _DEMO_SCRIPT, "--model", m,
                         "--frames-dir", d, *common]
                    )
                    if rc != 0:
                        raise HTTPException(500, f"Demo render failed for {m}: {err[-300:]}")

                gif_path = os.path.join(tmp, "compare.gif")
                rc, err = await _run_proc([
                    sys.executable, _VID_SCRIPT,
                    "--dir", left_dir, right_dir,
                    "--out", gif_path,
                    "--side-by-side",
                    "--left-label",  "M1 (random)",
                    "--right-label", f"{req.model} (auction+chain)",
                ], timeout=30)
                if rc != 0:
                    raise HTTPException(500, f"GIF stitch failed: {err[-300:]}")
            else:
                frames_dir = os.path.join(tmp, "frames")
                rc, err = await _run_proc(
                    [sys.executable, _DEMO_SCRIPT, "--model", model,
                     "--frames-dir", frames_dir, *common]
                )
                if rc != 0:
                    raise HTTPException(500, f"Demo render failed: {err[-300:]}")

                gif_path = os.path.join(tmp, "demo.gif")
                rc, err = await _run_proc([
                    sys.executable, _VID_SCRIPT,
                    "--dir", frames_dir,
                    "--out", gif_path,
                ], timeout=30)
                if rc != 0:
                    raise HTTPException(500, f"GIF stitch failed: {err[-300:]}")

            with open(gif_path, "rb") as f:
                gif_bytes = f.read()

            return Response(content=gif_bytes, media_type="image/gif")

        finally:
            shutil.rmtree(tmp, ignore_errors=True)


# ── Frame helpers ──────────────────────────────────────────────────────────────

def _to_jpeg(path: str, scale: float = 0.5, quality: int = 80) -> bytes:
    from PIL import Image
    img = Image.open(path).convert("RGB")
    if scale != 1.0:
        w, h = img.size
        img = img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=quality)
    return buf.getvalue()


def _stitch_jpeg(left: str, right: str, right_label: str,
                 scale: float = 0.5, quality: int = 80) -> bytes:
    from PIL import Image, ImageDraw
    L = Image.open(left).convert("RGB")
    R = Image.open(right).convert("RGB")
    if scale != 1.0:
        w, h = L.size; L = L.resize((int(w*scale), int(h*scale)), Image.LANCZOS)
        w, h = R.size; R = R.resize((int(w*scale), int(h*scale)), Image.LANCZOS)
    combo = Image.new("RGB", (L.width + R.width + 4, max(L.height, R.height)), (20, 20, 20))
    combo.paste(L, (0, 0))
    combo.paste(R, (L.width + 4, 0))
    draw = ImageDraw.Draw(combo)
    draw.text((8, 8), "M1  (random)", fill=(255, 100, 100))
    draw.text((L.width + 12, 8), f"{right_label}  (auction+chain)", fill=(100, 200, 255))
    buf = io.BytesIO()
    combo.save(buf, format="JPEG", quality=quality)
    return buf.getvalue()


# ── WebSocket live-stream endpoint ─────────────────────────────────────────────

@app.websocket("/api/pybullet/ws")
async def pybullet_stream(ws: WebSocket):
    await ws.accept()

    try:
        raw = await asyncio.wait_for(ws.receive_json(), timeout=10)
    except (asyncio.TimeoutError, Exception):
        await ws.close(1008)
        return

    model   = raw.get("model", "M4star").replace("M4*", "M4star")
    seed    = int(raw.get("seed", 42))
    n       = max(5, min(int(raw.get("n", 20)), 30))
    r       = max(1, min(int(raw.get("r", 3)), 5))
    e       = max(5.0, min(float(raw.get("e", 14.0)), 30.0))
    compare = bool(raw.get("compare", False))

    if model not in _ALLOWED_MODELS:
        await ws.send_json({"status": "error", "message": f"Invalid model: {model}"})
        await ws.close(); return

    common = ["--seed", str(seed), "--n", str(n), "--r", str(r),
              "--e", str(e), "--headless", "--record", "--force-matplotlib"]

    async with _PYBULLET_SEM:
        tmp = tempfile.mkdtemp(prefix="searchfcr_ws_")
        try:
            await ws.send_json({"status": "starting"})

            if compare:
                # Run both models in parallel, wait, then stream stitched pairs
                left_dir  = os.path.join(tmp, "M1")
                right_dir = os.path.join(tmp, model)

                async def _spawn(m: str, d: str):
                    return await asyncio.create_subprocess_exec(
                        sys.executable, _DEMO_SCRIPT,
                        "--model", m, "--frames-dir", d, *common,
                        cwd=_REPO_ROOT,
                        stdout=asyncio.subprocess.DEVNULL,
                        stderr=asyncio.subprocess.DEVNULL,
                    )

                lp, rp = await asyncio.gather(_spawn("M1", left_dir), _spawn(model, right_dir))
                await asyncio.wait_for(asyncio.gather(lp.wait(), rp.wait()), timeout=120)

                left_frames  = sorted(Path(left_dir).glob("frame_*.png"))
                right_frames = sorted(Path(right_dir).glob("frame_*.png"))
                n_pairs = min(len(left_frames), len(right_frames))
                await ws.send_json({"status": "streaming", "total": n_pairs})

                for lf, rf in zip(left_frames, right_frames):
                    frame = await asyncio.get_event_loop().run_in_executor(
                        None, _stitch_jpeg, str(lf), str(rf), model)
                    await ws.send_bytes(frame)
                    await asyncio.sleep(0.04)   # ~25 fps playback

            else:
                frames_dir = os.path.join(tmp, "frames")
                os.makedirs(frames_dir, exist_ok=True)
                proc = await asyncio.create_subprocess_exec(
                    sys.executable, _DEMO_SCRIPT,
                    "--model", model, "--frames-dir", frames_dir, *common,
                    cwd=_REPO_ROOT,
                    stdout=asyncio.subprocess.DEVNULL,
                    stderr=asyncio.subprocess.DEVNULL,
                )
                await ws.send_json({"status": "streaming"})

                sent: set[str] = set()
                deadline = asyncio.get_event_loop().time() + 120

                while True:
                    if asyncio.get_event_loop().time() > deadline:
                        proc.kill(); break

                    for fname in sorted(os.listdir(frames_dir)):
                        if fname.startswith("frame_") and fname.endswith(".png") and fname not in sent:
                            fpath = os.path.join(frames_dir, fname)
                            try:
                                frame = await asyncio.get_event_loop().run_in_executor(
                                    None, _to_jpeg, fpath)
                                await ws.send_bytes(frame)
                                sent.add(fname)
                            except Exception:
                                pass

                    if proc.returncode is not None:
                        break
                    await asyncio.sleep(0.1)

                # flush remaining frames
                for fname in sorted(os.listdir(frames_dir)):
                    if fname.startswith("frame_") and fname.endswith(".png") and fname not in sent:
                        try:
                            frame = await asyncio.get_event_loop().run_in_executor(
                                None, _to_jpeg, os.path.join(frames_dir, fname))
                            await ws.send_bytes(frame)
                            sent.add(fname)
                        except Exception:
                            pass

            await ws.send_json({"status": "done"})

        except WebSocketDisconnect:
            pass
        except asyncio.TimeoutError:
            try: await ws.send_json({"status": "error", "message": "Render timed out"})
            except Exception: pass
        except Exception as ex:
            try: await ws.send_json({"status": "error", "message": str(ex)[:300]})
            except Exception: pass
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
            try: await ws.close()
            except Exception: pass
