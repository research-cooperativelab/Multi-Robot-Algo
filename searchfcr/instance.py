"""Instance: a serializable search-and-rescue problem instance.

JSON format (stable, version 1):

.. code-block:: json

    {
      "schema": "searchfcr.instance/v1",
      "n_nodes": 30,
      "n_robots": 3,
      "area_scale": 10.0,
      "node_positions": {"0": [x, y], "1": [x, y], ...},
      "node_probs":     {"0": p0, "1": p1, ...},
      "bases":          {"0": [x, y], "1": [x, y], ...},
      "target": 17,
      "optimal_dist": 2.134,
      "seed": 42,
      "metadata": { ... arbitrary JSON ... }
    }

Field reference:

- ``n_nodes``: number of candidate search sites.
- ``n_robots``: fleet size.
- ``area_scale``: edge length ``L`` of the square deployment area.
- ``node_positions``: map from node id (int-as-str in JSON) to [x, y].
- ``node_probs``: normalized prior over ``node_positions`` keys (sums to 1).
- ``bases``: map from robot id (int-as-str in JSON) to [x, y].
- ``target``: node id of the ground-truth target (drawn from ``node_probs``).
- ``optimal_dist``: ``min_r d(base_r, target)`` — used as FCR denominator.
- ``seed``: seed used to generate this instance (may be None).
- ``metadata``: free-form annotations (e.g. generator version, parent sweep).

Int-as-str keys are a JSON concession: ``json.dump`` cannot emit int keys.
``Instance.from_dict`` transparently coerces both int and str keys back to int.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ._main_import import main_mod

SCHEMA_VERSION = "searchfcr.instance/v1"


def _coerce_int_keyed(d: dict) -> dict:
    """Accept both ``{0: v}`` and ``{"0": v}`` forms and normalize to int keys."""
    out = {}
    for k, v in d.items():
        if isinstance(k, str):
            try:
                k_int = int(k)
            except ValueError as exc:
                raise ValueError(f"Non-integer key in node/base map: {k!r}") from exc
            out[k_int] = v
        else:
            out[int(k)] = v
    return out


def _tuple_positions(d: dict) -> dict:
    """Positions round-trip as lists via JSON; restore as tuples for hashability."""
    return {k: tuple(v) for k, v in d.items()}


@dataclass(frozen=True)
class Instance:
    """A frozen, serializable search problem instance.

    This is a thin wrapper over the plain-dict format that ``main.py`` uses
    internally. ``to_main_dict()`` produces the dict shape expected by the
    runner functions in main.py; ``from_main_dict()`` is the reverse.
    """

    n_nodes: int
    n_robots: int
    area_scale: float
    node_positions: dict  # {int: (float, float)}
    node_probs: dict  # {int: float}
    bases: dict  # {int: (float, float)}
    target: int
    optimal_dist: float
    seed: int | None = None
    metadata: dict = field(default_factory=dict)

    # ---------------------------------------------------------------- factory

    @classmethod
    def generate(
        cls,
        n: int,
        r: int,
        L: float,
        seed: int | None = None,
        min_opt_dist: float = 1.0,
        max_opt_dist: float | None = None,
    ) -> "Instance":
        """Generate a random instance via ``main.generate_instance``.

        Parameters mirror main.py exactly. ``seed`` is recorded on the returned
        instance so experiments are reproducible.
        """
        raw = main_mod.generate_instance(
            n,
            r,
            L,
            seed=seed,
            min_opt_dist=min_opt_dist,
            max_opt_dist=max_opt_dist,
        )
        return cls(
            n_nodes=n,
            n_robots=r,
            area_scale=float(L),
            node_positions=dict(raw["node_positions"]),
            node_probs=dict(raw["node_probs"]),
            bases=dict(raw["bases"]),
            target=int(raw["target"]),
            optimal_dist=float(raw["optimal_dist"]),
            seed=seed,
            metadata={},
        )

    # --------------------------------------------------------------- bridging

    def to_main_dict(self) -> dict:
        """Return the dict shape that main.py's model_* functions expect."""
        return {
            "node_positions": dict(self.node_positions),
            "node_probs": dict(self.node_probs),
            "bases": dict(self.bases),
            "target": self.target,
            "optimal_dist": self.optimal_dist,
        }

    @classmethod
    def from_main_dict(
        cls,
        d: dict,
        *,
        n_nodes: int | None = None,
        n_robots: int | None = None,
        area_scale: float | None = None,
        seed: int | None = None,
        metadata: dict | None = None,
    ) -> "Instance":
        """Wrap a raw main.py dict. Sizes inferred from the maps if absent."""
        node_positions = dict(d["node_positions"])
        bases = dict(d["bases"])
        return cls(
            n_nodes=n_nodes if n_nodes is not None else len(node_positions),
            n_robots=n_robots if n_robots is not None else len(bases),
            area_scale=float(area_scale) if area_scale is not None else float("nan"),
            node_positions=node_positions,
            node_probs=dict(d["node_probs"]),
            bases=bases,
            target=int(d["target"]),
            optimal_dist=float(d["optimal_dist"]),
            seed=seed,
            metadata=dict(metadata) if metadata else {},
        )

    # ------------------------------------------------------------- JSON layer

    def to_dict(self) -> dict:
        """Return a JSON-ready dict (stable schema)."""
        return {
            "schema": SCHEMA_VERSION,
            "n_nodes": self.n_nodes,
            "n_robots": self.n_robots,
            "area_scale": self.area_scale,
            "node_positions": {str(k): list(v) for k, v in self.node_positions.items()},
            "node_probs": {str(k): float(v) for k, v in self.node_probs.items()},
            "bases": {str(k): list(v) for k, v in self.bases.items()},
            "target": self.target,
            "optimal_dist": self.optimal_dist,
            "seed": self.seed,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Instance":
        schema = d.get("schema")
        if schema is not None and schema != SCHEMA_VERSION:
            raise ValueError(
                f"Unknown instance schema {schema!r}; expected {SCHEMA_VERSION!r}"
            )
        return cls(
            n_nodes=int(d["n_nodes"]),
            n_robots=int(d["n_robots"]),
            area_scale=float(d["area_scale"]),
            node_positions=_tuple_positions(_coerce_int_keyed(d["node_positions"])),
            node_probs={k: float(v) for k, v in _coerce_int_keyed(d["node_probs"]).items()},
            bases=_tuple_positions(_coerce_int_keyed(d["bases"])),
            target=int(d["target"]),
            optimal_dist=float(d["optimal_dist"]),
            seed=d.get("seed"),
            metadata=dict(d.get("metadata") or {}),
        )

    def save(self, path: str | Path) -> None:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2, sort_keys=True)

    @classmethod
    def load(cls, path: str | Path) -> "Instance":
        with Path(path).open("r", encoding="utf-8") as f:
            return cls.from_dict(json.load(f))


def generate(
    n: int,
    r: int,
    L: float,
    seed: int | None = None,
    min_opt_dist: float = 1.0,
    max_opt_dist: float | None = None,
) -> Instance:
    """Functional alias for :meth:`Instance.generate`."""
    return Instance.generate(n, r, L, seed, min_opt_dist, max_opt_dist)


def save(instance: Instance, path: str | Path) -> None:
    """Functional alias for :meth:`Instance.save`."""
    instance.save(path)


def load(path: str | Path) -> Instance:
    """Functional alias for :meth:`Instance.load`."""
    return Instance.load(path)


__all__ = ["Instance", "SCHEMA_VERSION", "generate", "save", "load"]
