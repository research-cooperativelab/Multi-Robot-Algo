"""
Scene setup for the PyBullet drone demo.

This module builds a visual arena containing:
  - a 10m x 10m ground plane
  - 30 cylindrical site markers (heights proportional to prior probability)
  - 3 small colored base boxes (red, blue, green)
  - 3 drones (small coloured boxes) — one per base, matching the base colour
  - a gold highlight marker hovering over the target site

The module is written to run against real PyBullet when available.  If
PyBullet is not installed (e.g. no MSVC toolchain on Windows), the
module provides a light-weight stand-in that records every call, so
``run_demo.py`` can fall back to a pure-matplotlib rendering path and
still produce the deliverable PNG frames.
"""

from __future__ import annotations

import math
import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np

# ---------------------------------------------------------------------------
# PyBullet import guard
# ---------------------------------------------------------------------------

try:
    import pybullet as p  # type: ignore
    import pybullet_data  # type: ignore
    PYBULLET_AVAILABLE = True
except Exception as _exc:  # pragma: no cover - exercised only without pybullet
    p = None
    pybullet_data = None
    PYBULLET_AVAILABLE = False
    _PYBULLET_IMPORT_ERROR: Optional[Exception] = _exc
else:
    _PYBULLET_IMPORT_ERROR = None


# ---------------------------------------------------------------------------
# Colours shared across the simulated robots
# ---------------------------------------------------------------------------

ROBOT_COLORS: List[Tuple[float, float, float, float]] = [
    (0.90, 0.15, 0.15, 1.0),  # red
    (0.15, 0.35, 0.90, 1.0),  # blue
    (0.15, 0.80, 0.25, 1.0),  # green
]

SITE_COLOR_UNVISITED = (0.85, 0.85, 0.30, 1.0)   # pale yellow
SITE_COLOR_VISITED   = (0.45, 0.45, 0.45, 1.0)   # grey
SITE_COLOR_TARGET    = (0.95, 0.80, 0.15, 1.0)   # gold
SITE_COLOR_FOUND     = (1.00, 0.95, 0.25, 1.0)   # bright yellow (flash)

ARENA_SIZE = 10.0
DRONE_ALT  = 1.0     # fixed flight altitude (m)
DRONE_HALF = 0.12    # half-extent of the drone cube


# ---------------------------------------------------------------------------
# Scene data container
# ---------------------------------------------------------------------------

@dataclass
class SceneHandles:
    """Everything the replay loop needs to mutate at run time."""

    client: int = 0
    site_bodies: Dict[int, int] = field(default_factory=dict)
    site_visuals: Dict[int, int] = field(default_factory=dict)
    site_positions: Dict[int, Tuple[float, float]] = field(default_factory=dict)
    site_heights: Dict[int, float] = field(default_factory=dict)
    base_bodies: Dict[int, int] = field(default_factory=dict)
    drone_bodies: Dict[int, int] = field(default_factory=dict)
    drone_visuals: Dict[int, int] = field(default_factory=dict)
    target_marker: int = -1
    target_node: int = -1
    text_ids: List[int] = field(default_factory=list)
    arena_size: float = ARENA_SIZE


# ---------------------------------------------------------------------------
# Setup helpers
# ---------------------------------------------------------------------------

def connect(mode: str = "GUI") -> int:
    """Connect to PyBullet in GUI or DIRECT (headless) mode."""
    if not PYBULLET_AVAILABLE:
        raise RuntimeError(
            "pybullet is not available in this environment "
            f"(import error: {_PYBULLET_IMPORT_ERROR}). "
            "Use the matplotlib fallback path in run_demo.py."
        )
    flag = p.GUI if mode.upper() == "GUI" else p.DIRECT
    client = p.connect(flag)
    p.setAdditionalSearchPath(pybullet_data.getDataPath())
    p.setGravity(0, 0, -9.81)
    p.configureDebugVisualizer(p.COV_ENABLE_GUI, 0)
    p.configureDebugVisualizer(p.COV_ENABLE_SHADOWS, 1)
    p.resetDebugVisualizerCamera(
        cameraDistance=14.0,
        cameraYaw=35.0,
        cameraPitch=-45.0,
        cameraTargetPosition=[ARENA_SIZE / 2, ARENA_SIZE / 2, 0.0],
    )
    return client


def disconnect() -> None:
    if PYBULLET_AVAILABLE:
        try:
            p.disconnect()
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Primitive builders
# ---------------------------------------------------------------------------

def _spawn_cylinder(
    x: float, y: float, radius: float, height: float,
    rgba: Tuple[float, float, float, float],
) -> Tuple[int, int]:
    vis = p.createVisualShape(
        shapeType=p.GEOM_CYLINDER,
        radius=radius,
        length=height,
        rgbaColor=rgba,
    )
    col = p.createCollisionShape(
        shapeType=p.GEOM_CYLINDER,
        radius=radius,
        height=height,
    )
    body = p.createMultiBody(
        baseMass=0.0,
        baseCollisionShapeIndex=col,
        baseVisualShapeIndex=vis,
        basePosition=[x, y, height / 2.0],
    )
    return body, vis


def _spawn_box(
    x: float, y: float, z: float,
    half_extents: Tuple[float, float, float],
    rgba: Tuple[float, float, float, float],
) -> Tuple[int, int]:
    vis = p.createVisualShape(
        shapeType=p.GEOM_BOX,
        halfExtents=list(half_extents),
        rgbaColor=rgba,
    )
    col = p.createCollisionShape(
        shapeType=p.GEOM_BOX,
        halfExtents=list(half_extents),
    )
    body = p.createMultiBody(
        baseMass=0.0,
        baseCollisionShapeIndex=col,
        baseVisualShapeIndex=vis,
        basePosition=[x, y, z],
    )
    return body, vis


def _spawn_sphere(
    x: float, y: float, z: float, radius: float,
    rgba: Tuple[float, float, float, float],
) -> int:
    vis = p.createVisualShape(
        shapeType=p.GEOM_SPHERE,
        radius=radius,
        rgbaColor=rgba,
    )
    body = p.createMultiBody(
        baseMass=0.0,
        baseVisualShapeIndex=vis,
        basePosition=[x, y, z],
    )
    return body


# ---------------------------------------------------------------------------
# Scene construction from a main.py-compatible instance dict
# ---------------------------------------------------------------------------

def build_scene(instance: dict, *, mode: str = "GUI") -> SceneHandles:
    """Create the whole scene from an instance dict as returned by
    ``main.generate_instance``.

    The scene is anchored at (0, 0, 0); the arena is ``ARENA_SIZE`` metres
    on a side.  Every object is added through the PyBullet primitive APIs
    requested in the task description.
    """

    if not PYBULLET_AVAILABLE:
        raise RuntimeError("pybullet is not available; use the fallback path.")

    client = connect(mode=mode)
    handles = SceneHandles(client=client)

    # Ground plane ---------------------------------------------------------
    try:
        p.loadURDF("plane.urdf")
    except Exception:
        # Fallback: a flat box that looks like a plane
        _spawn_box(
            ARENA_SIZE / 2, ARENA_SIZE / 2, -0.05,
            (ARENA_SIZE / 2 + 1, ARENA_SIZE / 2 + 1, 0.05),
            (0.82, 0.82, 0.88, 1.0),
        )

    # Candidate sites ------------------------------------------------------
    probs = instance["node_probs"]
    positions = instance["node_positions"]
    max_p = max(probs.values()) if probs else 1.0

    for node_id, (x, y) in positions.items():
        prob = probs.get(node_id, 0.0)
        height = 0.15 + 1.5 * (prob / max_p)  # taller = higher prior
        radius = 0.12 + 0.10 * (prob / max_p)
        body, vis = _spawn_cylinder(x, y, radius, height, SITE_COLOR_UNVISITED)
        handles.site_bodies[node_id] = body
        handles.site_visuals[node_id] = vis
        handles.site_positions[node_id] = (x, y)
        handles.site_heights[node_id] = height

    # Bases + drones -------------------------------------------------------
    for r, (bx, by) in instance["bases"].items():
        col = ROBOT_COLORS[r % len(ROBOT_COLORS)]
        base_body, _ = _spawn_box(bx, by, 0.1, (0.35, 0.35, 0.1), col)
        handles.base_bodies[r] = base_body

        drone_vis = p.createVisualShape(
            shapeType=p.GEOM_BOX,
            halfExtents=[DRONE_HALF, DRONE_HALF, DRONE_HALF * 0.5],
            rgbaColor=col,
        )
        drone_col = p.createCollisionShape(
            shapeType=p.GEOM_BOX,
            halfExtents=[DRONE_HALF, DRONE_HALF, DRONE_HALF * 0.5],
        )
        drone = p.createMultiBody(
            baseMass=0.0,
            baseCollisionShapeIndex=drone_col,
            baseVisualShapeIndex=drone_vis,
            basePosition=[bx, by, DRONE_ALT],
        )
        handles.drone_bodies[r] = drone
        handles.drone_visuals[r] = drone_vis

    # Target marker --------------------------------------------------------
    target = instance["target"]
    tx, ty = positions[target]
    tz = handles.site_heights[target] + 0.6
    handles.target_marker = _spawn_sphere(tx, ty, tz, 0.18, SITE_COLOR_TARGET)
    handles.target_node = target

    return handles


# ---------------------------------------------------------------------------
# Runtime mutation helpers used by replay.py
# ---------------------------------------------------------------------------

def set_drone_pose(handles: SceneHandles, robot_id: int,
                   x: float, y: float, yaw: float = 0.0) -> None:
    if not PYBULLET_AVAILABLE:
        return
    quat = p.getQuaternionFromEuler([0.0, 0.0, yaw])
    p.resetBasePositionAndOrientation(
        handles.drone_bodies[robot_id], [x, y, DRONE_ALT], quat,
    )


def mark_site_visited(handles: SceneHandles, node_id: int,
                      is_target: bool = False) -> None:
    if not PYBULLET_AVAILABLE:
        return
    color = SITE_COLOR_FOUND if is_target else SITE_COLOR_VISITED
    p.changeVisualShape(
        handles.site_bodies[node_id], -1, rgbaColor=color,
    )


def update_overlay(handles: SceneHandles, lines: List[str]) -> None:
    """Replace every overlay line in a single pass."""
    if not PYBULLET_AVAILABLE:
        return
    for tid in handles.text_ids:
        try:
            p.removeUserDebugItem(tid)
        except Exception:
            pass
    handles.text_ids.clear()
    for i, line in enumerate(lines):
        tid = p.addUserDebugText(
            line,
            textPosition=[0.3, 0.3, 3.0 - 0.45 * i],
            textColorRGB=[1, 1, 1],
            textSize=1.4,
        )
        handles.text_ids.append(tid)


def yaw_towards(src: Tuple[float, float], dst: Tuple[float, float]) -> float:
    dx = dst[0] - src[0]
    dy = dst[1] - src[1]
    return math.atan2(dy, dx)


# ---------------------------------------------------------------------------
# Frame capture
# ---------------------------------------------------------------------------

def capture_frame(
    handles: SceneHandles, path: str, width: int = 960, height: int = 540,
) -> None:
    """Save a PNG of the current scene via ``pybullet.getCameraImage``."""
    if not PYBULLET_AVAILABLE:
        return
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    view = p.computeViewMatrix(
        cameraEyePosition=[ARENA_SIZE / 2 + 8, -6.0, 9.0],
        cameraTargetPosition=[ARENA_SIZE / 2, ARENA_SIZE / 2, 0.5],
        cameraUpVector=[0, 0, 1],
    )
    proj = p.computeProjectionMatrixFOV(
        fov=55.0, aspect=width / height, nearVal=0.1, farVal=60.0,
    )
    w, h, rgb, _, _ = p.getCameraImage(
        width=width, height=height, viewMatrix=view, projectionMatrix=proj,
        renderer=p.ER_TINY_RENDERER,
    )
    rgb = np.array(rgb, dtype=np.uint8).reshape(h, w, 4)[:, :, :3]
    try:
        from PIL import Image
        Image.fromarray(rgb).save(path)
    except Exception:
        # Last-resort PNG via matplotlib (always available in this repo)
        import matplotlib.pyplot as plt
        plt.imsave(path, rgb)
