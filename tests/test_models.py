"""Model dispatch tests: every clean-name model runs end-to-end."""

from __future__ import annotations

import math

import pytest

from searchfcr import MODELS, Instance, RunResult, run
from searchfcr.bounds import bound_m1, bound_m2, bound_m3, bound_m4


@pytest.fixture(scope="module")
def small_instance() -> Instance:
    return Instance.generate(n=10, r=2, L=10.0, seed=42, max_opt_dist=5.0)


@pytest.mark.parametrize("model", MODELS)
def test_every_model_runs(model: str, small_instance: Instance):
    res = run(model, small_instance, energy=10.0)
    assert isinstance(res, RunResult)
    assert isinstance(res.found, bool)
    assert isinstance(res.iterations, int) and res.iterations >= 0

    # FCR should be a finite number when found; None otherwise.
    if res.found:
        assert res.fcr is not None
        assert math.isfinite(res.fcr)
        assert res.fcr > 0
        assert res.finder in res.robot_dists
    else:
        assert res.fcr is None


def test_run_rejects_unknown_model(small_instance: Instance):
    with pytest.raises(ValueError):
        run("NotAModel", small_instance)


def test_run_accepts_aliases(small_instance: Instance):
    # "Hungarian" alias -> HungarianD
    res = run("Hungarian", small_instance, energy=10.0)
    assert res.model == "HungarianD"

    res2 = run("M4*", small_instance, energy=10.0)
    assert res2.model == "M4star"


def test_run_non_euclidean_raises(small_instance: Instance):
    with pytest.raises(NotImplementedError):
        run("M3", small_instance, dist="manhattan")


def test_bounds_are_positive():
    vals = [
        bound_m1(30, 3, 14, 10),
        bound_m2(30, 3, 14, 10),
        bound_m3(30, 3, 14, 10),
        bound_m4(30, 3, 14, 10),
    ]
    for v in vals:
        assert math.isfinite(v)
        assert v > 0
