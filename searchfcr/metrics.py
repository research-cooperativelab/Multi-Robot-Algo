"""Metrics: FCR and entropy, thin wrappers over main.py.

``fcr(result)`` returns the Finder Competitive Ratio for a single run.
``entropy(probs)`` returns the Shannon entropy (in bits) of a probability map.
"""

from __future__ import annotations

from typing import Union

from ._main_import import main_mod
from .models import RunResult


def fcr(result: Union[RunResult, dict]) -> float | None:
    """Return ``finder_dist / optimal_dist`` for a run, or ``None`` if no find.

    Accepts either a :class:`RunResult` (preferred) or a raw dict as produced
    by main.py's ``model_*`` functions.
    """
    if isinstance(result, RunResult):
        return result.fcr
    # Fall back to main.py's extractor on raw dicts.
    extracted = main_mod.extract_fcr(result)
    if extracted is None:
        return None
    return float(extracted["finder_cr"])


def entropy(probs: dict) -> float:
    """Shannon entropy of a probability distribution (bits).

    Wraps :func:`main.entropy`. Accepts any ``{key: p}`` mapping; ``p <= 0`` is
    skipped (treated as absent).
    """
    return float(main_mod.entropy(probs))


__all__ = ["fcr", "entropy"]
