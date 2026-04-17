"""Model registry: clean names mapped to main.py's implementations.

Clean names (as used by :func:`searchfcr.run` and the CLI):

=============  ========================================================
Name           Underlying main.py function
=============  ========================================================
``M1``         ``model_1_random_infinite``   (infinite energy, random)
``M2``         ``model_2_auction_infinite``  (infinite energy, N2N auction)
``M3``         ``model_3_auction_single``    (auction, single-node sortie)
``M4``         ``model_4_auction_multi``     (auction + greedy chain)
``M4star``     ``model_4_auction_multi``     (same, but with p/d\u00b2 bid)
``HungarianD`` ``model_hungarian_single``    (Hungarian, min-distance)
``HungarianPD``(this package) Hungarian with p/d reward
=============  ========================================================

For M3, M4, and M4star the caller controls the bid function via ``bid=``.
The M4star default is ``p_over_d2`` (the paper's recommended bid); callers may
override it but the "star" branding is conventionally tied to p/d\u00b2.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

import numpy as np
from scipy.optimize import linear_sum_assignment

from ._main_import import main_mod
from .bids import Bid, resolve as resolve_bid
from .instance import Instance

# -----------------------------------------------------------------------------
# Clean-name -> main.py function map.
#
# Values are *dispatchers*: callables ``(instance_dict, energy, bid_func) ->
# result_dict`` that ignore arguments they don't need. This keeps ``run()``
# uniform.
# -----------------------------------------------------------------------------


def _dispatch_m1(inst_d, energy, bid_func):
    del energy, bid_func
    return main_mod.model_1_random_infinite(inst_d)


def _dispatch_m2(inst_d, energy, bid_func):
    del energy, bid_func
    return main_mod.model_2_auction_infinite(inst_d)


def _dispatch_m3(inst_d, energy, bid_func):
    return main_mod.model_3_auction_single(inst_d, energy, bid_func)


def _dispatch_m4(inst_d, energy, bid_func):
    return main_mod.model_4_auction_multi(inst_d, energy, bid_func)


def _dispatch_hungarian_d(inst_d, energy, bid_func):
    del bid_func
    return main_mod.model_hungarian_single(inst_d, energy)


def _dispatch_hungarian_pd(inst_d, energy, bid_func):
    """Hungarian assignment with p/d reward (negated as cost).

    Note: main.py does not ship a Hungarian variant that uses probabilities;
    we implement it here so the package can offer the full pairing of
    "centralized vs distributed" x "distance-only vs probability-aware".
    Same sortie structure as :func:`model_hungarian_single`.
    """
    del bid_func  # Hungarian uses a fixed cost derived from p and d
    return _hungarian_pd(inst_d, energy)


# Public clean-name -> dispatcher table
_MODEL_NAME_MAP: dict[str, Callable[[dict, float, Callable], dict]] = {
    "M1": _dispatch_m1,
    "M2": _dispatch_m2,
    "M3": _dispatch_m3,
    "M4": _dispatch_m4,
    "M4star": _dispatch_m4,  # same underlying model; bid default differs
    "HungarianD": _dispatch_hungarian_d,
    "HungarianPD": _dispatch_hungarian_pd,
}

# Aliases (CLI-friendly / alternate spellings)
_MODEL_ALIASES: dict[str, str] = {
    "M4*": "M4star",
    "M4_star": "M4star",
    "Hungarian_d": "HungarianD",
    "Hungarian": "HungarianD",
    "Hungarian_pd": "HungarianPD",
    "HungarianPd": "HungarianPD",
}

#: Canonical ordered list of model names for CLI ``list-models`` and benches.
MODELS: list[str] = ["M1", "M2", "M3", "M4", "M4star", "HungarianD", "HungarianPD"]

#: Default bid for each model. Models that ignore bids have ``None``.
_DEFAULT_BIDS: dict[str, str | None] = {
    "M1": None,
    "M2": None,
    "M3": Bid.P_OVER_D.value,
    "M4": Bid.P_OVER_D.value,
    "M4star": Bid.P_OVER_D2.value,
    "HungarianD": None,
    "HungarianPD": None,
}


def canonical_model_name(name: str) -> str:
    """Return the canonical model key for a user-supplied name."""
    if name in _MODEL_NAME_MAP:
        return name
    if name in _MODEL_ALIASES:
        return _MODEL_ALIASES[name]
    valid = ", ".join(MODELS)
    raise ValueError(f"Unknown model {name!r}. Valid: {valid}")


# -----------------------------------------------------------------------------
# Result type
# -----------------------------------------------------------------------------


@dataclass
class RunResult:
    """Outcome of a single model run on a single instance.

    Attributes:
        model: canonical model name that produced this result.
        finder: robot id that found the target, or ``None`` if the run
            terminated without finding it.
        fcr: finder competitive ratio = ``robot_dists[finder] / optimal_dist``.
            ``None`` when the target was not found.
        iterations: number of rounds (sorties / auction rounds) executed.
        robot_dists: total distance travelled per robot.
        found: whether the target was found.
        optimal_dist: ``min_r d(base_r, target)``; the FCR denominator.
        raw: the untouched dict returned by the underlying main.py model, for
            callers that want per-round entropy diagnostics.
    """

    model: str
    finder: int | None
    fcr: float | None
    iterations: int
    robot_dists: dict[int, float]
    found: bool
    optimal_dist: float
    raw: dict[str, Any] = field(default_factory=dict, repr=False)


# -----------------------------------------------------------------------------
# Unified runner
# -----------------------------------------------------------------------------


def run(
    model: str,
    instance: Instance,
    energy: float = 14.0,
    bid: str | Bid | None = None,
    dist: str = "euclidean",
) -> RunResult:
    """Run one model on one instance.

    Args:
        model: one of :data:`MODELS` (or an alias).
        instance: :class:`Instance` to run on.
        energy: per-sortie energy budget E. Ignored for M1/M2 (infinite energy).
        bid: bid function name (see :class:`searchfcr.Bid`). Ignored for M1,
            M2, and both Hungarian variants. When ``None``, the model's
            default bid is used (``p_over_d`` for M3/M4, ``p_over_d2`` for M4*).
        dist: distance metric. Only ``"euclidean"`` is supported today; other
            values raise ``NotImplementedError`` for forward compatibility.
    """
    if dist != "euclidean":
        raise NotImplementedError(
            f"Distance metric {dist!r} not supported yet; use 'euclidean'."
        )

    name = canonical_model_name(model)
    dispatch = _MODEL_NAME_MAP[name]

    # Resolve bid: fall back to model default if not given.
    bid_key = bid if bid is not None else _DEFAULT_BIDS[name]
    bid_func = resolve_bid(bid_key) if bid_key is not None else None

    raw = dispatch(instance.to_main_dict(), energy, bid_func)

    finder = raw.get("found_by")
    robot_dists = {int(k): float(v) for k, v in raw.get("robot_dists", {}).items()}
    opt = float(raw.get("optimal_dist", instance.optimal_dist))
    found = finder is not None
    fcr_val: float | None = None
    if found and opt > 1e-9:
        fcr_val = robot_dists[finder] / opt

    return RunResult(
        model=name,
        finder=finder if finder is None else int(finder),
        fcr=fcr_val,
        iterations=int(raw.get("iterations", 0)),
        robot_dists=robot_dists,
        found=found,
        optimal_dist=opt,
        raw=raw,
    )


# -----------------------------------------------------------------------------
# HungarianPD implementation (not in main.py)
# -----------------------------------------------------------------------------


def _hungarian_pd(instance_d: dict, energy: float) -> dict:
    """Hungarian assignment maximizing sum of p/d rewards.

    Mirrors the sortie structure of :func:`main.model_hungarian_single` exactly
    (single-node round trips, Bayesian updates, same termination condition);
    only the assignment objective changes from "minimize distance" to
    "maximize ``p_i / d_{r,i}``".
    """
    np_positions = instance_d["node_positions"]
    probs = dict(instance_d["node_probs"])
    bases = instance_d["bases"]
    target = instance_d["target"]
    opt = instance_d["optimal_dist"]
    n_robots = len(bases)

    available = set(np_positions.keys())
    robot_dists = {r: 0.0 for r in range(n_robots)}
    iteration = 0
    round_data: list[dict] = []

    while available:
        iteration += 1
        H_before = main_mod.entropy(probs)

        robot_list = list(range(n_robots))
        avail_list = [
            n
            for n in available
            if any(
                2 * main_mod.euclidean_distance(bases[r], np_positions[n]) <= energy
                for r in robot_list
            )
        ]
        if not avail_list:
            break

        nr, nn = len(robot_list), len(avail_list)
        # Cost = -reward; reward = p / d for energy-feasible, else very bad.
        BAD = 1e9
        cost = np.full((nr, nn), BAD)
        dists = np.zeros((nr, nn))
        for i, r in enumerate(robot_list):
            for j, node in enumerate(avail_list):
                d = main_mod.euclidean_distance(bases[r], np_positions[node])
                dists[i, j] = d
                if 2 * d <= energy and d > 0 and probs.get(node, 0) > 0:
                    cost[i, j] = -(probs[node] / d)

        if nn < nr:
            cost = np.hstack([cost, np.full((nr, nr - nn), BAD)])
            dists = np.hstack([dists, np.zeros((nr, nr - nn))])

        row_ind, col_ind = linear_sum_assignment(cost)
        assigned: dict[int, tuple[int, float]] = {}
        for i, j in zip(row_ind, col_ind):
            if j < nn and cost[i, j] < BAD / 2:
                assigned[robot_list[i]] = (avail_list[j], float(dists[i, j]))

        if not assigned:
            break

        found, finder = False, None
        visited: set = set()
        prob_cap = 0.0

        for r, (n, d) in assigned.items():
            visited.add(n)
            prob_cap += probs.get(n, 0)
            if n == target:
                robot_dists[r] += d
                found, finder = True, r
            else:
                robot_dists[r] += 2 * d

        probs = main_mod.bayesian_update(probs, visited)
        available -= visited
        H_after = main_mod.entropy(probs) if available else 0

        round_data.append(
            {
                "round": iteration,
                "entropy_before": H_before,
                "entropy_after": H_after,
                "prob_captured": prob_cap,
                "sites_visited": len(visited),
                "found_target": found,
            }
        )

        if found:
            return {
                "model": "HungarianPD",
                "found_by": finder,
                "robot_dists": dict(robot_dists),
                "optimal_dist": opt,
                "iterations": iteration,
                "round_data": round_data,
            }

    return {
        "model": "HungarianPD",
        "found_by": None,
        "robot_dists": dict(robot_dists),
        "optimal_dist": opt,
        "iterations": iteration,
        "round_data": round_data,
    }


# -----------------------------------------------------------------------------
# Typed aliases for importing "the model" directly.
# -----------------------------------------------------------------------------

M1 = _dispatch_m1
M2 = _dispatch_m2
M3 = _dispatch_m3
M4 = _dispatch_m4
M4star = _dispatch_m4  # same callable; distinction is bid choice
HungarianD = _dispatch_hungarian_d
HungarianPD = _dispatch_hungarian_pd


__all__ = [
    "MODELS",
    "M1",
    "M2",
    "M3",
    "M4",
    "M4star",
    "HungarianD",
    "HungarianPD",
    "RunResult",
    "run",
    "canonical_model_name",
]
