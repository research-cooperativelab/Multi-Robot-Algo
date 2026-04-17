"""Experiment 3 — Cost Sensitivity.

Hypothesis: The p/d^2 finding (Model 4*) generalises beyond Euclidean cost.
The cost-foreclosure argument says a quadratic distance penalty protects
the robot's budget by preventing over-commitment to distant high-prior
sites. That argument does not invoke any particular metric — only the
ordering of cheap vs expensive moves. If it is sound, p/d^2 should still
beat p/d under Manhattan distance, heterogeneous robot speeds, and a
simple obstacle penalty.

Protocol:
  * For each cost variant (Euclidean baseline + three alternatives), run
    DEFAULT_TRIALS trials at the default configuration (n=30, R=3, E=14,
    L=10, seed=42).
  * For each trial, generate the instance under the variant's cost (so
    optimal_dist reflects the same metric as the robot's travel cost),
    then run Model 4 (p/d) and Model 4* (p/d^2) on identical instances.
  * Record mean and median FCR per (variant, model).

Variants:
  A. Manhattan. d(p,q) = |px-qx| + |py-qy|.
  B. Heterogeneous speeds. Each robot r has speed v_r ~ U[0.7, 1.3];
     effective distance for robot r is d_euclidean(p,q) / v_r.
  C. Obstacle penalty. Three circular obstacles (radius 0.5, fixed
     positions). Segment crossings incur a penalty of 2*r_obs per
     obstacle crossed on top of the Euclidean length.

Outputs:
  - thesis/figures/fig_cost_sensitivity.png  (grouped bar chart)
  - experiments/data/exp3_cost_sensitivity.csv
  - prints the headline comparison

Usage: python experiments/exp3_cost_sensitivity.py
"""
from __future__ import annotations

import os
import random

import numpy as np
import matplotlib.pyplot as plt

from _common import (
    DEFAULT_E, DEFAULT_L, DEFAULT_N, DEFAULT_R, DEFAULT_SEED, DEFAULT_TRIALS,
    DATA_DIR, enable_utf8_stdout, save_fig, setup_style, write_csv,
)

# pylint: disable=wrong-import-position
import main as sar
from main import (
    bid_p_over_d, bid_p_over_d2, generate_instance, model_4_auction_multi,
)


# ----------------------- cost-model primitives -----------------------


def euclidean(p1, p2):
    return ((p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2) ** 0.5


def manhattan(p1, p2):
    return abs(p1[0] - p2[0]) + abs(p1[1] - p2[1])


# Variant C obstacle configuration. Radius 0.5 hits ~27 % segment-crossing
# rate with 30 nodes in a 10x10 area (calibrated empirically; see the
# experiment docstring and the commit message for details).
OBS_CENTERS = [(3.0, 3.0), (7.0, 5.0), (5.0, 7.5)]
OBS_RADIUS = 0.5
OBS_PENALTY = 2.0 * OBS_RADIUS  # per obstacle crossed


def _segment_hits_circle(p1, p2, c, r):
    """Return True iff the closed segment p1-p2 intersects the closed disk
    of radius r centred at c. Standard projection test."""
    ax, ay = p1
    bx, by = p2
    cx, cy = c
    abx, aby = bx - ax, by - ay
    acx, acy = cx - ax, cy - ay
    ab_len2 = abx * abx + aby * aby
    if ab_len2 < 1e-12:
        return (ax - cx) ** 2 + (ay - cy) ** 2 <= r * r
    t = (abx * acx + aby * acy) / ab_len2
    t = max(0.0, min(1.0, t))
    px, py = ax + t * abx, ay + t * aby
    return (px - cx) ** 2 + (py - cy) ** 2 <= r * r


def obstacle_distance(p1, p2):
    base = euclidean(p1, p2)
    n_hits = sum(1 for c in OBS_CENTERS
                 if _segment_hits_circle(p1, p2, c, OBS_RADIUS))
    return base + n_hits * OBS_PENALTY


# ----------------------- variant dispatchers -----------------------


def make_dist_fn(variant, speeds=None):
    """Return a dist_fn(p1, p2, r) closure for the given variant.

    `speeds` is a mapping {r: v_r} — required for variant='hetero'.
    """
    if variant == 'euclid':
        def _fn(p1, p2, r=None):
            return euclidean(p1, p2)
        return _fn
    if variant == 'manhattan':
        def _fn(p1, p2, r=None):
            return manhattan(p1, p2)
        return _fn
    if variant == 'hetero':
        assert speeds is not None
        def _fn(p1, p2, r=None):
            # r is None only on pre-instance calls from generate_instance;
            # experiment supplies r on every in-model call.
            if r is None:
                return euclidean(p1, p2)
            return euclidean(p1, p2) / speeds[r]
        return _fn
    if variant == 'obstacle':
        def _fn(p1, p2, r=None):
            return obstacle_distance(p1, p2)
        return _fn
    raise ValueError(f'unknown variant {variant}')


# ----------------------- instance generation -----------------------


def generate_instance_for_variant(variant, seed, speeds=None):
    """Generate an instance whose `optimal_dist` reflects the variant's
    cost model. For Manhattan and Obstacle this just rewires the distance
    used during target acceptance; for Heterogeneous speeds, optimal_dist
    is min over r of d_eucl(base_r, target) / v_r — the best cost any
    robot could achieve.

    The underlying geometry (node positions, bases, priors, target
    identity) is identical to what `generate_instance` would produce
    under Euclidean distance for this seed. Only `optimal_dist` varies.
    We then bound max_opt_dist by the expected effective cost so the
    target stays reachable.
    """
    # Generate geometry under Euclidean, then re-score optimal_dist.
    # max_opt_dist = E/2 under Euclidean means the 2d round-trip fits in E;
    # for non-Euclidean variants, the same geometry remains reachable
    # in expectation, but we tighten by 20 % to cushion variant cost
    # inflation (Manhattan is up to sqrt(2)x Euclidean, obstacle penalty
    # adds at most ~3 units, hetero-speed up to 1/0.7 ~ 1.43x).
    inst = generate_instance(DEFAULT_N, DEFAULT_R, DEFAULT_L,
                             seed=seed, min_opt_dist=1.0,
                             max_opt_dist=DEFAULT_E / 2.0 * 0.7)

    dist_fn = make_dist_fn(variant, speeds=speeds)
    bases = inst['bases']
    tgt_pos = inst['node_positions'][inst['target']]
    # Compute optimal_dist under the variant's metric.
    per_robot = [dist_fn(bases[r], tgt_pos, r) for r in range(DEFAULT_R)]
    inst['optimal_dist'] = min(per_robot)
    return inst


# ----------------------- variant runner -----------------------


def run_variant(variant, trials, speeds_per_trial=None):
    """Return a dict {model_label: [fcr, ...]} for one cost variant."""
    out = {'M4 (p/d)': [], 'M4* (p/d^2)': []}

    for t in range(trials):
        # Heterogeneous speeds: redraw per trial so speeds contribute
        # trial-to-trial variance (same seeding strategy for the noise
        # RNG that exp1 uses for prior corruption).
        speeds = speeds_per_trial[t] if speeds_per_trial is not None else None
        inst = generate_instance_for_variant(variant, seed=DEFAULT_SEED + t,
                                             speeds=speeds)
        dist_fn = make_dist_fn(variant, speeds=speeds)

        # Deterministic tie-breaking across models.
        random.seed(DEFAULT_SEED + t)
        np.random.seed(DEFAULT_SEED + t)
        r_m4 = model_4_auction_multi(inst, DEFAULT_E,
                                     bid_func=bid_p_over_d,
                                     dist_fn=dist_fn)
        random.seed(DEFAULT_SEED + t)
        np.random.seed(DEFAULT_SEED + t)
        r_m4s = model_4_auction_multi(inst, DEFAULT_E,
                                      bid_func=bid_p_over_d2,
                                      dist_fn=dist_fn)

        for label, res in (('M4 (p/d)', r_m4), ('M4* (p/d^2)', r_m4s)):
            if res['found_by'] is not None and res['optimal_dist'] > 1e-9:
                fcr = res['robot_dists'][res['found_by']] / res['optimal_dist']
                out[label].append(fcr)

    return out


# ----------------------- main entry point -----------------------


VARIANTS = [
    ('euclid',    'Euclidean'),
    ('manhattan', 'Manhattan'),
    ('hetero',    'Heterogeneous'),
    ('obstacle',  'Obstacle'),
]


def run():
    enable_utf8_stdout()
    setup_style()
    print('Experiment 3: Cost Sensitivity')
    print(f'  {DEFAULT_TRIALS} trials, n={DEFAULT_N}, R={DEFAULT_R}, '
          f'E={DEFAULT_E}, L={DEFAULT_L}')
    print(f'  variants: {[v for _, v in VARIANTS]}')

    # Pre-draw per-trial robot speeds for variant B so both M4 and M4*
    # see the same speed draws.
    speed_rng = np.random.default_rng(DEFAULT_SEED + 7919)
    speeds_per_trial = [
        {r: float(speed_rng.uniform(0.7, 1.3)) for r in range(DEFAULT_R)}
        for _ in range(DEFAULT_TRIALS)
    ]

    # Diagnostics: obstacle-crossing rate on a sample of node pairs.
    _report_obstacle_rate()

    rows = []
    per_variant = {}
    for key, label in VARIANTS:
        sp = speeds_per_trial if key == 'hetero' else None
        fcrs = run_variant(key, DEFAULT_TRIALS, speeds_per_trial=sp)
        per_variant[key] = fcrs
        m4_mean = float(np.mean(fcrs['M4 (p/d)']))
        m4_med = float(np.median(fcrs['M4 (p/d)']))
        m4s_mean = float(np.mean(fcrs['M4* (p/d^2)']))
        m4s_med = float(np.median(fcrs['M4* (p/d^2)']))
        delta_pct = (m4_mean - m4s_mean) / m4_mean * 100.0
        print(f'  {label:14s}  '
              f'M4 mean={m4_mean:5.2f} med={m4_med:5.2f}  |  '
              f'M4* mean={m4s_mean:5.2f} med={m4s_med:5.2f}  |  '
              f'delta={delta_pct:+5.1f}%')
        rows.append((label, 'M4 (p/d)',    m4_mean, m4_med, 0.0))
        rows.append((label, 'M4* (p/d^2)', m4s_mean, m4s_med, delta_pct))

    # ---- bar chart ----
    fig, ax = plt.subplots(figsize=(7.2, 4.5))
    n_var = len(VARIANTS)
    x = np.arange(n_var)
    width = 0.38

    m4_means = [float(np.mean(per_variant[k]['M4 (p/d)'])) for k, _ in VARIANTS]
    m4s_means = [float(np.mean(per_variant[k]['M4* (p/d^2)'])) for k, _ in VARIANTS]

    bars_m4 = ax.bar(x - width / 2, m4_means, width,
                     color='#6A9A47', label='M4 ($p/d$)',
                     edgecolor='#3d5a29', linewidth=0.8)
    bars_m4s = ax.bar(x + width / 2, m4s_means, width,
                      color='#2E7D32', label='M4* ($p/d^2$)',
                      edgecolor='#174218', linewidth=0.8)

    # Label each bar with its FCR value.
    for bars in (bars_m4, bars_m4s):
        for b in bars:
            h = b.get_height()
            ax.text(b.get_x() + b.get_width() / 2, h * 1.01,
                    f'{h:.2f}', ha='center', va='bottom',
                    fontsize=9, color='#222')

    ax.set_xticks(x)
    ax.set_xticklabels([lbl for _, lbl in VARIANTS])
    ax.set_ylabel('Mean Finder Competitive Ratio')
    ax.set_title('Generalisation of $p/d^2$ across cost models')
    ax.legend(loc='upper right', framealpha=0.92)
    ymax = max(max(m4_means), max(m4s_means)) * 1.28
    ax.set_ylim(0, ymax)
    ax.grid(axis='y', alpha=0.25)
    ax.grid(axis='x', visible=False)

    save_fig(fig, 'fig_cost_sensitivity.png')

    write_csv(os.path.join(DATA_DIR, 'exp3_cost_sensitivity.csv'),
              rows, header=['variant', 'model', 'mean_fcr',
                            'median_fcr', 'delta_pct'])

    # Headline summary for the thesis prose.
    print()
    print('  Headline numbers for thesis:')
    for key, label in VARIANTS:
        m4m = float(np.mean(per_variant[key]['M4 (p/d)']))
        m4sm = float(np.mean(per_variant[key]['M4* (p/d^2)']))
        delta = (m4m - m4sm) / m4m * 100.0
        winner = 'M4*' if m4sm < m4m else 'M4 '
        print(f'  {label:14s}  M4={m4m:.2f}  M4*={m4sm:.2f}  '
              f'M4* wins by {delta:+.1f}%  ({winner})')


def _report_obstacle_rate():
    """Quick sanity: fraction of random node-pair segments that cross at
    least one obstacle under the calibrated config."""
    rng = np.random.default_rng(1234)
    n_pairs, n_hits = 0, 0
    for _ in range(50):
        pts = [(rng.uniform(0, DEFAULT_L), rng.uniform(0, DEFAULT_L))
               for _ in range(DEFAULT_N)]
        for i in range(len(pts)):
            for j in range(i + 1, len(pts)):
                n_pairs += 1
                for c in OBS_CENTERS:
                    if _segment_hits_circle(pts[i], pts[j], c, OBS_RADIUS):
                        n_hits += 1
                        break
    pct = 100.0 * n_hits / max(1, n_pairs)
    print(f'  obstacle crossing rate (sanity): {pct:.1f}% of segments')


if __name__ == '__main__':
    run()
