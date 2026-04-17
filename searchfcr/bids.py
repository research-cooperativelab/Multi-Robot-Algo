"""Bid functions: clean names + enum mapped to main.py implementations.

Each bid ``b(p, d, E)`` returns a scalar score a robot uses to rank candidate
sites. Higher is better. ``E`` is the per-sortie energy budget; bids that do
not use it should ignore the argument.
"""

from __future__ import annotations

from enum import Enum
from typing import Callable

from ._main_import import main_mod

# Functional re-exports. Names follow the enum values below (lowercase).
p: Callable = main_mod.bid_p_only
inv_d: Callable = main_mod.bid_d_only
p_over_d: Callable = main_mod.bid_p_over_d
p_over_d2: Callable = main_mod.bid_p_over_d2
p_exp_decay: Callable = main_mod.bid_exp_decay


class Bid(str, Enum):
    """Enumeration of supported bid functions.

    Inheriting from ``str`` lets users pass either the enum member or the raw
    string (``Bid.P_OVER_D`` or ``"p_over_d"``) to :func:`searchfcr.run`.
    """

    P = "p"
    INV_D = "inv_d"
    P_OVER_D = "p_over_d"
    P_OVER_D2 = "p_over_d2"
    P_EXP_DECAY = "p_exp_decay"


_BID_FUNCS: dict[str, Callable] = {
    Bid.P.value: p,
    Bid.INV_D.value: inv_d,
    Bid.P_OVER_D.value: p_over_d,
    Bid.P_OVER_D2.value: p_over_d2,
    Bid.P_EXP_DECAY.value: p_exp_decay,
}


def resolve(bid: str | Bid) -> Callable:
    """Return the callable for a bid name or enum member."""
    key = bid.value if isinstance(bid, Bid) else str(bid)
    try:
        return _BID_FUNCS[key]
    except KeyError as exc:
        valid = ", ".join(sorted(_BID_FUNCS))
        raise ValueError(f"Unknown bid {key!r}. Valid: {valid}") from exc


def list_bids() -> list[str]:
    """Sorted list of valid bid names."""
    return sorted(_BID_FUNCS.keys())


__all__ = [
    "Bid",
    "p",
    "inv_d",
    "p_over_d",
    "p_over_d2",
    "p_exp_decay",
    "resolve",
    "list_bids",
]
