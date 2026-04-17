"""Theoretical upper bounds from the paper (Section 5).

Wraps :func:`main.compute_theoretical_bounds` and re-exposes the four
per-model bounds under clean names.

.. code-block:: python

    from searchfcr.bounds import bound_m1, bound_m2, bound_m3, bound_m4
    bound_m4(n=30, R=3, E=14, L=10)
"""

from __future__ import annotations

from ._main_import import main_mod


def _compute(n: int, R: int, E: float, L: float) -> dict:
    return main_mod.compute_theoretical_bounds(n, R, E, L)


# Internal keys used by main.py's bounds dict.
_KEY_M1 = "M1 Random (\u221eE)"
_KEY_M2 = "M2 Auction (\u221eE, N2N)"
_KEY_M3 = "M3 Auction Single (E)"
_KEY_M4 = "M4 Auction Multi (E)"


def bound_m1(n: int, R: int, E: float, L: float) -> float:
    """Upper bound on E[FCR_1] for the random-baseline model (infinite energy).

    ``E[FCR_1] <= (2*E[K_1] - 1) * d_avg / d_opt`` where
    ``E[K_1] = 1 / (1 - (1 - 1/n)^R)``.
    """
    return float(_compute(n, R, E, L)[_KEY_M1])


def bound_m2(n: int, R: int, E: float, L: float) -> float:
    """Upper bound on E[FCR_2] for the infinite-energy node-to-node auction.

    ``E[FCR_2] <= E[K] * d_hop / d_opt`` with ``E[K] = (n + R) / (2R)``.
    """
    return float(_compute(n, R, E, L)[_KEY_M2])


def bound_m3(n: int, R: int, E: float, L: float) -> float:
    """Upper bound on E[FCR_3] for the single-node auction under energy E."""
    return float(_compute(n, R, E, L)[_KEY_M3])


def bound_m4(n: int, R: int, E: float, L: float) -> float:
    """Upper bound on E[FCR_4] for the multi-node auction under energy E.

    ``E[FCR_4] <= E * E[K_4] / d_opt`` with ``E[K_4]`` averaging
    ``ceil(i / (R*S))`` over ``i = 1..n``.
    """
    return float(_compute(n, R, E, L)[_KEY_M4])


def constants(n: int, R: int, E: float, L: float) -> dict:
    """Return the geometric constants (d_avg, d_hop, d_opt, E[K], ...)."""
    return dict(_compute(n, R, E, L)["constants"])


__all__ = ["bound_m1", "bound_m2", "bound_m3", "bound_m4", "constants"]
