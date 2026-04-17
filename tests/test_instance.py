"""Instance round-trip and schema tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from searchfcr import Instance, SCHEMA_VERSION


def test_generate_basic():
    inst = Instance.generate(n=10, r=2, L=10.0, seed=42)
    assert inst.n_nodes == 10
    assert inst.n_robots == 2
    assert inst.area_scale == 10.0
    assert len(inst.node_positions) == 10
    assert len(inst.node_probs) == 10
    assert len(inst.bases) == 2
    # node_probs sums to 1
    assert abs(sum(inst.node_probs.values()) - 1.0) < 1e-9
    # target is a valid node id
    assert inst.target in inst.node_positions
    # optimal_dist is non-negative
    assert inst.optimal_dist >= 0.0
    # seed is recorded
    assert inst.seed == 42


def test_deterministic_with_seed():
    a = Instance.generate(n=15, r=3, L=10.0, seed=7)
    b = Instance.generate(n=15, r=3, L=10.0, seed=7)
    assert a.target == b.target
    assert a.optimal_dist == pytest.approx(b.optimal_dist)
    assert a.node_positions == b.node_positions


def test_roundtrip_json_tmp_file(tmp_path: Path):
    inst = Instance.generate(n=12, r=2, L=5.0, seed=123)
    out = tmp_path / "inst.json"
    inst.save(out)
    assert out.is_file()
    loaded = Instance.load(out)

    assert loaded.n_nodes == inst.n_nodes
    assert loaded.n_robots == inst.n_robots
    assert loaded.area_scale == inst.area_scale
    assert loaded.target == inst.target
    assert loaded.optimal_dist == pytest.approx(inst.optimal_dist)
    assert loaded.seed == inst.seed
    # Positions / probs / bases all match
    for k, v in inst.node_positions.items():
        assert tuple(loaded.node_positions[k]) == tuple(v)
    for k, v in inst.node_probs.items():
        assert loaded.node_probs[k] == pytest.approx(v)
    for k, v in inst.bases.items():
        assert tuple(loaded.bases[k]) == tuple(v)


def test_to_dict_from_dict_symmetric():
    inst = Instance.generate(n=8, r=2, L=10.0, seed=1)
    d = inst.to_dict()
    assert d["schema"] == SCHEMA_VERSION
    # Keys are strings per JSON convention
    assert all(isinstance(k, str) for k in d["node_positions"].keys())
    inst2 = Instance.from_dict(d)
    assert inst2.node_positions == inst.node_positions
    assert inst2.node_probs == inst.node_probs
    assert inst2.bases == inst.bases


def test_from_dict_rejects_unknown_schema():
    bad = {"schema": "unknown/v999", "n_nodes": 1, "n_robots": 1,
           "area_scale": 1.0, "node_positions": {"0": [0, 0]},
           "node_probs": {"0": 1.0}, "bases": {"0": [0, 0]},
           "target": 0, "optimal_dist": 0.0, "seed": 0, "metadata": {}}
    with pytest.raises(ValueError):
        Instance.from_dict(bad)


def test_to_main_dict_has_expected_keys():
    inst = Instance.generate(n=6, r=2, L=10.0, seed=5)
    d = inst.to_main_dict()
    for k in ("node_positions", "node_probs", "bases", "target", "optimal_dist"):
        assert k in d
