"""searchfcr: a benchmark for budgeted multi-robot search.

Wraps the primitives in ``main.py`` (the thesis simulator) under a stable,
citable API. Keep imports flat so users can write::

    import searchfcr as sf
    inst = sf.Instance.generate(n=30, r=3, L=10.0, seed=42)
    res = sf.run("M4star", inst, energy=14.0)
    print(res.fcr)

The package has one source of truth: all algorithms live in ``main.py`` at
the repo root. Nothing here duplicates that code; models.py etc. dispatch
into it.
"""

from __future__ import annotations

__version__ = "0.1.0"

from .bids import (
    Bid,
    inv_d,
    list_bids,
    p,
    p_exp_decay,
    p_over_d,
    p_over_d2,
)
from .bounds import bound_m1, bound_m2, bound_m3, bound_m4, constants
from .instance import Instance, SCHEMA_VERSION, generate, load, save
from .metrics import entropy, fcr
from .models import (
    MODELS,
    HungarianD,
    HungarianPD,
    M1,
    M2,
    M3,
    M4,
    M4star,
    RunResult,
    canonical_model_name,
    run,
)

__all__ = [
    "__version__",
    # instance
    "Instance",
    "SCHEMA_VERSION",
    "generate",
    "load",
    "save",
    # models
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
    # bids
    "Bid",
    "p",
    "inv_d",
    "p_over_d",
    "p_over_d2",
    "p_exp_decay",
    "list_bids",
    # metrics
    "fcr",
    "entropy",
    # bounds
    "bound_m1",
    "bound_m2",
    "bound_m3",
    "bound_m4",
    "constants",
]
