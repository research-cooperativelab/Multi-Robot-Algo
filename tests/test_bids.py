"""Bid function tests: every bid returns a finite, non-negative float."""

from __future__ import annotations

import math

import pytest

from searchfcr import Bid, list_bids
from searchfcr.bids import inv_d, p, p_exp_decay, p_over_d, p_over_d2, resolve


@pytest.mark.parametrize("bid_name", list_bids())
def test_bid_positive_on_valid_inputs(bid_name: str):
    fn = resolve(bid_name)
    value = fn(0.5, 2.0, 14.0)
    assert isinstance(value, float)
    assert math.isfinite(value)
    assert value >= 0.0


def test_bid_p_returns_probability():
    assert p(0.7, 1.0, 14.0) == pytest.approx(0.7)


def test_bid_inv_d_handles_zero_distance():
    # zero distance -> bid function returns 0 (guard in main.py)
    assert inv_d(0.5, 0.0, 14.0) == 0


def test_bid_p_over_d_sensible():
    assert p_over_d(0.6, 2.0, 14.0) == pytest.approx(0.3)


def test_bid_p_over_d2_sensible():
    assert p_over_d2(0.8, 2.0, 14.0) == pytest.approx(0.2)


def test_bid_exp_decay_decreases_with_distance():
    v_near = p_exp_decay(0.5, 1.0, 14.0)
    v_far = p_exp_decay(0.5, 10.0, 14.0)
    assert v_near > v_far > 0


def test_bid_enum_and_string_interchangeable():
    assert resolve(Bid.P_OVER_D) is resolve("p_over_d")


def test_resolve_unknown_raises():
    with pytest.raises(ValueError):
        resolve("not_a_bid")
