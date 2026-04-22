"""Experiment 4 — Statistical Significance Tests (Wilcoxon + Bonferroni).

This experiment re-runs the main comparison on N_TRIALS identical instances and
performs paired Wilcoxon signed-rank tests between the key model pairs reported in
the thesis and paper.  Bonferroni correction is applied for the four primary
comparisons.

Protocol:
  * N_TRIALS = 1000 instances at the default config (n=30, R=3, E=14, L=10).
    All models see identical instances to enable paired comparison.
  * Per-trial FCR is recorded for: M1, M2, M3, M4, M4*, HungarianD, HungarianPD.
  * Paired Wilcoxon signed-rank tests are run for four key pairs:
      1. M2 vs M1       — value of coordination
      2. M3 vs HungarianD — probability-aware vs distance-only
      3. M4 vs M3       — multi-node vs single-node sortie
      4. M4* vs M4      — p/d^2 vs p/d bid
  * Bonferroni-corrected significance threshold: alpha/4 = 0.0125.
  * 95% confidence intervals on each model's mean FCR are also reported.

Outputs:
  - experiments/data/exp4_significance.csv  (per-trial FCR for all models)
  - experiments/data/exp4_wilcoxon.csv      (Wilcoxon test results)
  - experiments/data/exp4_stats.csv         (per-model summary stats)
  - thesis/figures/fig_significance_ci.png  (FCR means with 95% CI)

Usage:
  cd <repo_root>/experiments
  python exp4_significance.py
"""
from __future__ import annotations

import os
import sys

import numpy as np
import matplotlib.pyplot as plt
from scipy.stats import wilcoxon
from scipy.optimize import linear_sum_assignment

from _common import (
    DEFAULT_E, DEFAULT_L, DEFAULT_N, DEFAULT_R, DEFAULT_SEED,
    DATA_DIR, enable_utf8_stdout, save_fig, setup_style, write_csv,
)

import main as sar
from main import (
    bid_p_over_d,
    bid_p_over_d2,
    generate_instance,
    model_1_random_infinite,
    model_2_auction_infinite,
    model_3_auction_single,
    model_4_auction_multi,
    model_hungarian_single,
)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
N_TRIALS = 1000
ALPHA    = 0.05
N_TESTS  = 4   # Bonferroni denominator

MODEL_LABELS = ['M1', 'M2', 'HungarianD', 'HungarianPD', 'M3', 'M4', 'M4*']

COMPARISONS = [
    ('M2',  'M1',        'Value of coordination     (M2  vs M1)'),
    ('M3',  'HungarianD','Probability vs distance   (M3  vs H_d)'),
    ('M4',  'M3',        'Multi-node vs single sort (M4  vs M3)'),
    ('M4*', 'M4',        'p/d^2 vs p/d bid          (M4* vs M4)'),
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _compute_fcr(result: dict) -> float | None:
    """Extract FCR from a model result dict using found_by + robot_dists."""
    finder = result.get('found_by')
    if finder is None:
        return None
    dists = result.get('robot_dists', {})
    opt   = result.get('optimal_dist', 0.0)
    if opt <= 0:
        return None
    return dists[finder] / opt


def _run_hungarian_pd(inst: dict, energy: float) -> dict:
    """Hungarian assignment using -p_i/d as the cost (probability-weighted).

    Mirrors the single-sortie structure of model_hungarian_single but uses
    probability-weighted costs instead of pure distance.
    """
    import math

    nodes    = list(inst['node_positions'].keys())
    probs    = dict(inst['node_probs'])
    bases    = inst['bases']
    n_robots = len(bases)
    target   = inst['target']

    robot_dists = {r: 0.0 for r in range(n_robots)}
    iterations  = 0
    finder      = None

    unvisited = set(nodes)
    while unvisited:
        iterations += 1
        # feasible sites for each robot (round-trip within energy)
        col_nodes = sorted(
            n for n in unvisited
            if any(2 * math.dist(bases[r], inst['node_positions'][n]) <= energy
                   for r in range(n_robots))
        )
        if not col_nodes:
            break

        # cost matrix: row=robot, col=site; cost = -p/d (minimise)
        cost = np.full((n_robots, len(col_nodes)), 1e9)
        for ri in range(n_robots):
            for ci, node in enumerate(col_nodes):
                d = math.dist(bases[ri], inst['node_positions'][node])
                if 2 * d <= energy and d > 0:
                    cost[ri, ci] = -(probs.get(node, 0.0) / d)

        row_ind, col_ind = linear_sum_assignment(cost)

        found_this_round = False
        for ri, ci in zip(row_ind, col_ind):
            if cost[ri, ci] >= 1e8:
                continue
            node = col_nodes[ci]
            d = math.dist(bases[ri], inst['node_positions'][node])
            robot_dists[ri] += 2 * d
            unvisited.discard(node)
            probs[node] = 0.0
            total = sum(probs.values())
            if total > 0:
                probs = {k: v / total for k, v in probs.items()}
            if node == target:
                finder = ri
                found_this_round = True
                break
        if found_this_round:
            break

    opt_dist = inst['optimal_dist']
    fcr = (robot_dists[finder] / opt_dist) if finder is not None and opt_dist > 0 else None
    return {'found_by': finder, 'robot_dists': robot_dists,
            'optimal_dist': opt_dist, 'iterations': iterations, 'fcr': fcr}


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run():
    enable_utf8_stdout()
    setup_style()
    print('Experiment 4: Statistical Significance Tests')
    print(f'  {N_TRIALS} paired trials  n={DEFAULT_N}  R={DEFAULT_R}  '
          f'E={DEFAULT_E}  L={DEFAULT_L}')
    print(f'  Bonferroni-corrected alpha: {ALPHA/N_TESTS:.4f}  ({N_TESTS} tests)')
    print()

    # ------------------------------------------------------------------
    # 1. Run all models on N_TRIALS identical instances.
    # ------------------------------------------------------------------
    fcr_by_model: dict[str, list[float]] = {m: [] for m in MODEL_LABELS}

    for t in range(N_TRIALS):
        if t % 200 == 0:
            print(f'  trial {t}/{N_TRIALS}...')

        trial_seed = DEFAULT_SEED + t
        inst = generate_instance(
            DEFAULT_N, DEFAULT_R, DEFAULT_L,
            seed=trial_seed,
            min_opt_dist=1.0,
            max_opt_dist=DEFAULT_E / 2.0,
        )
        # NOTE: do NOT reset random state here — using the same seed as
        # generate_instance() would correlate M1's random site draws with
        # the instance's probability structure, causing M1 to accidentally
        # select the target on iteration 1 nearly every trial.

        fcr_by_model['M1'].append(
            _compute_fcr(model_1_random_infinite(inst)) or np.nan)
        fcr_by_model['M2'].append(
            _compute_fcr(model_2_auction_infinite(inst)) or np.nan)
        fcr_by_model['HungarianD'].append(
            _compute_fcr(model_hungarian_single(inst, DEFAULT_E)) or np.nan)
        fcr_by_model['HungarianPD'].append(
            _compute_fcr(_run_hungarian_pd(inst, DEFAULT_E)) or np.nan)
        fcr_by_model['M3'].append(
            _compute_fcr(model_3_auction_single(inst, DEFAULT_E, bid_p_over_d)) or np.nan)
        fcr_by_model['M4'].append(
            _compute_fcr(model_4_auction_multi(inst, DEFAULT_E, bid_p_over_d)) or np.nan)
        fcr_by_model['M4*'].append(
            _compute_fcr(model_4_auction_multi(inst, DEFAULT_E, bid_p_over_d2)) or np.nan)

    # ------------------------------------------------------------------
    # 2. Summary statistics.
    # ------------------------------------------------------------------
    print()
    print('  Summary  (mean ± 95% CI  |  median  |  std  |  n):')
    summary: dict[str, dict] = {}
    for m in MODEL_LABELS:
        arr = np.array([x for x in fcr_by_model[m] if not np.isnan(x)])
        mean = arr.mean()
        med  = np.median(arr)
        std  = arr.std(ddof=1)
        ci95 = 1.96 * std / np.sqrt(len(arr))
        summary[m] = dict(mean=mean, median=med, std=std, ci95=ci95, n=len(arr))
        print(f'    {m:12s}  {mean:7.3f} ± {ci95:.3f}  '
              f'med={med:7.3f}  std={std:6.3f}  n={len(arr)}')

    # ------------------------------------------------------------------
    # 3. Paired Wilcoxon signed-rank tests + Bonferroni.
    # ------------------------------------------------------------------
    print()
    print(f'  Paired Wilcoxon tests  (Bonferroni alpha = {ALPHA/N_TESTS:.4f}):')
    stat_rows = []
    for m_better, m_worse, label in COMPARISONS:
        a = np.array(fcr_by_model[m_better])
        b = np.array(fcr_by_model[m_worse])
        mask = ~(np.isnan(a) | np.isnan(b))
        a, b = a[mask], b[mask]
        # one-sided: test that b - a > 0 (m_better has strictly lower FCR)
        stat, p_two = wilcoxon(b - a, alternative='greater')
        sig = p_two < ALPHA / N_TESTS
        pct = 100.0 * (b.mean() - a.mean()) / b.mean()
        tag = ('p<0.001' if p_two < 0.001 else
               ('p<0.01' if p_two < 0.01 else f'p={p_two:.4f}'))
        print(f'    {label}')
        print(f'      {m_better}: {a.mean():.4f}  vs  {m_worse}: {b.mean():.4f}'
              f'  (+{pct:.1f}%)')
        print(f'      W={stat:.0f}  p={p_two:.3e}  tag={tag}  '
              f'Bonf-sig={"YES" if sig else "NO"}')
        stat_rows.append([m_better, m_worse, f'{a.mean():.4f}', f'{b.mean():.4f}',
                          f'{pct:.2f}', f'{stat:.0f}', f'{p_two:.4e}',
                          tag, 'YES' if sig else 'NO'])

    # ------------------------------------------------------------------
    # 4. Save data.
    # ------------------------------------------------------------------
    write_csv(
        os.path.join(DATA_DIR, 'exp4_significance.csv'),
        [[t] + [fcr_by_model[m][t] for m in MODEL_LABELS] for t in range(N_TRIALS)],
        ['trial'] + MODEL_LABELS,
    )
    write_csv(
        os.path.join(DATA_DIR, 'exp4_stats.csv'),
        [[m, f"{summary[m]['mean']:.4f}", f"{summary[m]['median']:.4f}",
          f"{summary[m]['std']:.4f}", f"{summary[m]['ci95']:.4f}", summary[m]['n']]
         for m in MODEL_LABELS],
        ['model', 'mean_fcr', 'median_fcr', 'std', 'ci95', 'n'],
    )
    write_csv(
        os.path.join(DATA_DIR, 'exp4_wilcoxon.csv'),
        stat_rows,
        ['model_lower', 'model_higher', 'mean_lower', 'mean_higher',
         'pct_improvement', 'W_stat', 'p_value', 'tag', 'bonf_sig'],
    )

    # ------------------------------------------------------------------
    # 5. CI bar chart.
    # ------------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(8.5, 4.5))
    x      = np.arange(len(MODEL_LABELS))
    means  = [summary[m]['mean'] for m in MODEL_LABELS]
    cis    = [summary[m]['ci95'] for m in MODEL_LABELS]
    colors = ['#d62728', '#1f77b4', '#8c564b', '#9467bd',
              '#ff7f0e', '#2ca02c', '#17becf']

    ax.bar(x, means, color=colors, alpha=0.82, width=0.62,
           yerr=cis, capsize=5, error_kw={'elinewidth': 1.5, 'ecolor': '#333'})
    ax.set_xticks(x)
    ax.set_xticklabels(MODEL_LABELS, rotation=18, ha='right')
    ax.set_ylabel('Mean Finder Competitive Ratio (FCR)')
    ax.set_title(
        f'Mean FCR with 95\\% Confidence Intervals\n'
        f'({N_TRIALS} paired trials, $n={DEFAULT_N}$, $R={DEFAULT_R}$, $E={DEFAULT_E}$)',
        fontsize=11)
    ax.set_ylim(0, max(means) * 1.20)

    # Significance brackets for the four key pairs
    def _bracket(ax, x1, x2, y, label, dy=0.6):
        top = y + dy
        ax.plot([x1, x1, x2, x2], [y, top, top, y], lw=1.0, color='#333')
        ax.text((x1 + x2) / 2, top + 0.1, label,
                ha='center', va='bottom', fontsize=8)

    h = max(means) * 1.08
    gap = max(means) * 0.06
    # pairs (left_x, right_x) in MODEL_LABELS order
    pair_xs = [(MODEL_LABELS.index('M2'),   MODEL_LABELS.index('M1')),
               (MODEL_LABELS.index('M3'),   MODEL_LABELS.index('HungarianD')),
               (MODEL_LABELS.index('M4'),   MODEL_LABELS.index('M3')),
               (MODEL_LABELS.index('M4*'),  MODEL_LABELS.index('M4'))]
    for i, (xi, xj) in enumerate(pair_xs):
        _bracket(ax, min(xi, xj), max(xi, xj), h + i * gap, '***', dy=gap * 0.4)

    fig.tight_layout()
    save_fig(fig, 'fig_significance_ci.png')

    # ------------------------------------------------------------------
    # 6. Print copy-paste summary for thesis table.
    # ------------------------------------------------------------------
    print()
    print('=' * 62)
    print('  COPY INTO thesis/Chapters/results.tex TABLE')
    print('=' * 62)
    print(f'  {"Model":<22} {"Mean":>7} {"±95%CI":>8} {"Median":>8} {"Std":>7}')
    print('  ' + '-' * 54)
    for m in MODEL_LABELS:
        s = summary[m]
        print(f'  {m:<22} {s["mean"]:>7.3f} {s["ci95"]:>8.3f} '
              f'{s["median"]:>8.3f} {s["std"]:>7.3f}')
    print()
    print('  Wilcoxon tags (for p-value column):')
    for row in stat_rows:
        print(f'    {row[0]:5s} vs {row[1]:11s}  {row[7]}  (Bonf-sig={row[8]})')
    print('=' * 62)


if __name__ == '__main__':
    run()
