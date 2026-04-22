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
  - experiments/data/exp4_stats.csv         (summary: model stats + p-values)
  - thesis/figures/fig_significance_ci.png  (FCR means with 95% CI error bars)

Usage:
  cd <repo_root>
  python experiments/exp4_significance.py

After running, copy the p-values from exp4_stats.csv into the thesis Table II
in thesis/Chapters/results.tex.
"""
from __future__ import annotations

import os
import random
import sys

import numpy as np
import matplotlib.pyplot as plt
from scipy.stats import wilcoxon

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
N_TRIALS  = 1000   # increase from the default 500 for tighter CIs
ALPHA     = 0.05
N_TESTS   = 4      # Bonferroni denominator

MODEL_LABELS = ['M1', 'M2', 'HungarianD', 'HungarianPD', 'M3', 'M4', 'M4*']

# Four primary comparisons (lower model is expected to have lower FCR).
COMPARISONS = [
    ('M2',   'M1',        'Value of coordination (M2 vs M1)'),
    ('M3',   'HungarianD','Probability vs distance (M3 vs H_d)'),
    ('M4',   'M3',        'Multi-node vs single sortie (M4 vs M3)'),
    ('M4*',  'M4',        'p/d^2 vs p/d bid (M4* vs M4)'),
]


# ---------------------------------------------------------------------------
# Helper: HungarianPD — Hungarian with p/d cost (see models.py for rationale)
# ---------------------------------------------------------------------------

def _run_hungarian_pd(inst: dict, energy: float) -> dict:
    """Hungarian assignment using -p_i/d as cost (probability-weighted)."""
    from scipy.optimize import linear_sum_assignment
    import math

    nodes     = list(inst['node_positions'].keys())
    probs     = inst['node_probs']
    bases     = inst['robot_bases']
    n_robots  = inst['num_robots']
    target    = inst['target']

    visited: set = set()
    robot_dists  = {r: 0.0 for r in range(n_robots)}
    robot_pos    = {r: tuple(bases[r]) for r in range(n_robots)}
    iterations   = 0
    finder       = None

    unvisited = set(nodes)
    while unvisited:
        iterations += 1
        # Build cost matrix: rows = robots, cols = feasible unvisited sites
        feasible = [n for n in sorted(unvisited)
                    if 2 * math.dist(robot_pos[r], inst['node_positions'][n]) <= energy
                    for r in range(n_robots)]
        # unique feasible nodes across all robots (for column index)
        col_nodes = sorted({n for n in unvisited
                            if any(2 * math.dist(tuple(bases[r]),
                                                  inst['node_positions'][n]) <= energy
                                   for r in range(n_robots))})
        if not col_nodes:
            break

        cost = np.full((n_robots, len(col_nodes)), 1e9)
        for ri in range(n_robots):
            for ci, node in enumerate(col_nodes):
                d = math.dist(tuple(bases[ri]), inst['node_positions'][node])
                if 2 * d <= energy:
                    p = probs.get(node, 0.0)
                    cost[ri, ci] = -(p / d) if d > 0 else -1e9

        row_ind, col_ind = linear_sum_assignment(cost)
        assigned = {}
        for ri, ci in zip(row_ind, col_ind):
            if cost[ri, ci] < 1e8:
                assigned[ri] = col_nodes[ci]

        if not assigned:
            break

        for r, node in assigned.items():
            d = math.dist(tuple(bases[r]), inst['node_positions'][node])
            robot_dists[r] += 2 * d
            visited.add(node)
            unvisited.discard(node)
            probs = dict(probs)
            probs[node] = 0.0
            total = sum(probs.values())
            if total > 0:
                probs = {k: v / total for k, v in probs.items()}
            if node == target:
                finder = r
                break
        if finder is not None:
            break

    opt_dist = min(math.dist(tuple(bases[r]), inst['node_positions'][target])
                   for r in range(n_robots))
    fcr = (robot_dists[finder] / opt_dist) if finder is not None and opt_dist > 0 else None
    return {'finder': finder, 'fcr': fcr, 'iterations': iterations,
            'robot_dists': robot_dists}


# ---------------------------------------------------------------------------
# Main experiment
# ---------------------------------------------------------------------------

def run():
    enable_utf8_stdout()
    setup_style()
    print('Experiment 4: Statistical Significance Tests')
    print(f'  {N_TRIALS} paired trials, n={DEFAULT_N}, R={DEFAULT_R}, '
          f'E={DEFAULT_E}, L={DEFAULT_L}')
    print(f'  Bonferroni-corrected alpha: {ALPHA / N_TESTS:.4f} ({N_TESTS} tests)')
    print()

    # ------------------------------------------------------------------
    # 1. Generate N_TRIALS instances and run all models.
    # ------------------------------------------------------------------
    fcr_by_model: dict[str, list[float]] = {m: [] for m in MODEL_LABELS}

    for t in range(N_TRIALS):
        if t % 100 == 0:
            print(f'  trial {t}/{N_TRIALS}...')

        trial_seed = DEFAULT_SEED + t
        inst = generate_instance(
            DEFAULT_N, DEFAULT_R, DEFAULT_L,
            seed=trial_seed,
            min_opt_dist=1.0,
            max_opt_dist=DEFAULT_E / 2.0,
        )
        # Deterministic model execution
        random.seed(trial_seed)
        np.random.seed(trial_seed)

        def _fcr(result):
            f = result.get('fcr') or result.get('FCR')
            if f is None or f != f:  # NaN check
                return np.nan
            return float(f)

        fcr_by_model['M1'].append(_fcr(model_1_random_infinite(inst)))
        fcr_by_model['M2'].append(_fcr(model_2_auction_infinite(inst)))
        fcr_by_model['HungarianD'].append(_fcr(model_hungarian_single(inst, DEFAULT_E)))
        fcr_by_model['HungarianPD'].append(_fcr(_run_hungarian_pd(inst, DEFAULT_E)))
        fcr_by_model['M3'].append(_fcr(model_3_auction_single(inst, DEFAULT_E, bid_p_over_d)))
        fcr_by_model['M4'].append(_fcr(model_4_auction_multi(inst, DEFAULT_E, bid_p_over_d)))
        fcr_by_model['M4*'].append(_fcr(model_4_auction_multi(inst, DEFAULT_E, bid_p_over_d2)))

    # ------------------------------------------------------------------
    # 2. Per-model summary statistics.
    # ------------------------------------------------------------------
    print()
    print('  Summary (mean ± 95% CI, median, std):')
    summary = {}
    for m in MODEL_LABELS:
        arr = np.array([x for x in fcr_by_model[m] if not np.isnan(x)])
        mean  = arr.mean()
        med   = np.median(arr)
        std   = arr.std(ddof=1)
        se    = std / np.sqrt(len(arr))
        ci95  = 1.96 * se
        summary[m] = dict(mean=mean, median=med, std=std, ci95=ci95, n=len(arr))
        print(f'    {m:15s}  mean={mean:6.3f} ± {ci95:.3f}  '
              f'median={med:6.3f}  std={std:6.3f}  n={len(arr)}')

    # ------------------------------------------------------------------
    # 3. Wilcoxon signed-rank tests with Bonferroni correction.
    # ------------------------------------------------------------------
    print()
    print(f'  Paired Wilcoxon signed-rank tests '
          f'(Bonferroni alpha = {ALPHA/N_TESTS:.4f}):')
    stat_rows = []
    for (m_better, m_worse, label) in COMPARISONS:
        a = np.array(fcr_by_model[m_better])
        b = np.array(fcr_by_model[m_worse])
        # Drop NaN pairs
        mask = ~(np.isnan(a) | np.isnan(b))
        a, b = a[mask], b[mask]
        # Wilcoxon: test that a < b (one-sided alternative)
        stat, p_two = wilcoxon(b - a, alternative='greater')
        bonf_sig = 'YES' if p_two < ALPHA / N_TESTS else 'NO'
        pct_improve = 100.0 * (b.mean() - a.mean()) / b.mean()
        print(f'    {label}')
        print(f'      {m_better}: {a.mean():.4f}  vs  {m_worse}: {b.mean():.4f}'
              f'  ({pct_improve:.1f}% improvement)')
        print(f'      W={stat:.1f}  p={p_two:.2e}  Bonferroni-sig: {bonf_sig}')
        stat_rows.append([m_better, m_worse, f'{a.mean():.4f}', f'{b.mean():.4f}',
                          f'{pct_improve:.1f}', f'{stat:.1f}', f'{p_two:.3e}',
                          'p<0.001' if p_two < 0.001 else
                          ('p<0.01' if p_two < 0.01 else f'p={p_two:.3f}'),
                          bonf_sig])

    # ------------------------------------------------------------------
    # 4. Save per-trial CSV.
    # ------------------------------------------------------------------
    per_trial_path = os.path.join(DATA_DIR, 'exp4_significance.csv')
    header = ['trial'] + MODEL_LABELS
    rows = [[t] + [fcr_by_model[m][t] for m in MODEL_LABELS]
            for t in range(N_TRIALS)]
    write_csv(per_trial_path, rows, header)

    # ------------------------------------------------------------------
    # 5. Save statistics CSV.
    # ------------------------------------------------------------------
    stats_path = os.path.join(DATA_DIR, 'exp4_stats.csv')
    stats_rows = []
    for m in MODEL_LABELS:
        s = summary[m]
        stats_rows.append([m, f"{s['mean']:.4f}", f"{s['median']:.4f}",
                           f"{s['std']:.4f}", f"{s['ci95']:.4f}", s['n']])
    write_csv(stats_path, stats_rows,
              ['model', 'mean_fcr', 'median_fcr', 'std', 'ci95', 'n_trials'])

    sig_path = os.path.join(DATA_DIR, 'exp4_wilcoxon.csv')
    write_csv(sig_path, stat_rows,
              ['model_lower', 'model_higher', 'mean_lower', 'mean_higher',
               'pct_improvement', 'W_stat', 'p_value', 'label', 'bonf_sig'])

    # ------------------------------------------------------------------
    # 6. Plot: FCR means with 95% CI error bars.
    # ------------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(8, 4.5))
    x     = np.arange(len(MODEL_LABELS))
    means = [summary[m]['mean']  for m in MODEL_LABELS]
    cis   = [summary[m]['ci95']  for m in MODEL_LABELS]
    colors = ['#d62728', '#1f77b4', '#8c564b', '#9467bd',
              '#ff7f0e', '#2ca02c', '#17becf']

    bars = ax.bar(x, means, color=colors, alpha=0.82, width=0.6,
                  yerr=cis, capsize=5, error_kw={'elinewidth': 1.4})
    ax.set_xticks(x)
    ax.set_xticklabels(MODEL_LABELS, rotation=20, ha='right')
    ax.set_ylabel('Mean Finder Competitive Ratio (FCR)')
    ax.set_title(
        f'Mean FCR with 95\\% Confidence Intervals\n'
        f'({N_TRIALS} paired trials, $n={DEFAULT_N}$, $R={DEFAULT_R}$, '
        f'$E={DEFAULT_E}$)',
        fontsize=11)
    # Annotate significance for the four tested pairs
    sig_annotations = {
        # (left_model_idx, right_model_idx, label)
        (MODEL_LABELS.index('M2'), MODEL_LABELS.index('M1'), '***'),
        (MODEL_LABELS.index('M3'), MODEL_LABELS.index('HungarianD'), '***'),
        (MODEL_LABELS.index('M4'), MODEL_LABELS.index('M3'), '***'),
        (MODEL_LABELS.index('M4*'), MODEL_LABELS.index('M4'), '***'),
    }
    ax.set_ylim(0, max(means) * 1.25)
    fig.tight_layout()
    save_fig(fig, 'fig_significance_ci.png')

    print()
    print('Done.')
    print()
    print('=== COPY THESE VALUES INTO thesis/Chapters/results.tex TABLE ===')
    print()
    print('Model            Mean FCR  95% CI    Median  Std')
    for m in MODEL_LABELS:
        s = summary[m]
        print(f'  {m:15s}  {s["mean"]:6.3f}  ±{s["ci95"]:.3f}    '
              f'{s["median"]:6.3f}  {s["std"]:.3f}')
    print()
    print('Wilcoxon p-values (add to table):')
    for row in stat_rows:
        print(f'  {row[0]:6s} vs {row[1]:11s}  {row[7]}  Bonf-sig={row[8]}')
    print()
    print('Add the "p-value" column to the LaTeX table using these values.')
    print('See experiments/data/exp4_wilcoxon.csv for full details.')


if __name__ == '__main__':
    run()
