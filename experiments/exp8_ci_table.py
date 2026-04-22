"""Experiment 8 — High-Trial Confidence Interval Table (5000 trials).

Runs 5000 paired trials at the default config (n=30, R=3, E=14, L=10) for all
seven models and produces:
  - Precise mean / median / std / 95% CI for each model.
  - Pairwise statistical-separation check: mean_diff > sum_of_CIs  →  clearly
    separated (no overlap at 95% confidence).
  - A ready-to-paste LaTeX tabular block for the paper.
  - A horizontal error-bar plot (mean ± 95% CI) showing all seven models.
  - experiments/data/exp8_ci_table.csv

Key scientific question:  is M4* vs M4 clearly separated at N=5000?

Usage:
  cd <repo_root>/experiments
  python exp8_ci_table.py
"""
from __future__ import annotations

import math
import os
import sys

import numpy as np
import matplotlib.pyplot as plt
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
N_TRIALS = 5000
Z95      = 1.96          # normal quantile for 95% CI

MODEL_LABELS = ['M1', 'M2', 'HungarianD', 'HungarianPD', 'M3', 'M4', 'M4*']

# Key consecutive pairs for separation analysis (lower-FCR model first)
PAIR_CHECKS = [
    ('M2',  'M1',        'Value of coordination     (M2  vs M1)'),
    ('M3',  'HungarianD','Prob-aware vs dist-only   (M3  vs H_d)'),
    ('M4',  'M3',        'Multi-node vs single sort (M4  vs M3)'),
    ('M4*', 'M4',        'p/d^2 vs p/d bid          (M4* vs M4)'),
]


# ---------------------------------------------------------------------------
# Helper: Hungarian with p/d weighting (mirrors exp4)
# ---------------------------------------------------------------------------

def _run_hungarian_pd(inst: dict, energy: float) -> dict:
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
        col_nodes = sorted(
            n for n in unvisited
            if any(2 * math.dist(bases[r], inst['node_positions'][n]) <= energy
                   for r in range(n_robots))
        )
        if not col_nodes:
            break

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


def _compute_fcr(result: dict) -> float | None:
    finder = result.get('found_by')
    if finder is None:
        return None
    dists = result.get('robot_dists', {})
    opt   = result.get('optimal_dist', 0.0)
    if opt <= 0:
        return None
    return dists[finder] / opt


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run():
    enable_utf8_stdout()
    setup_style()

    print('Experiment 8: High-Trial CI Table')
    print(f'  {N_TRIALS} paired trials  n={DEFAULT_N}  R={DEFAULT_R}  '
          f'E={DEFAULT_E}  L={DEFAULT_L}')
    print()

    # ------------------------------------------------------------------
    # 1.  Run all models on N_TRIALS identical instances.
    # ------------------------------------------------------------------
    fcr_by_model: dict[str, list[float]] = {m: [] for m in MODEL_LABELS}

    for t in range(N_TRIALS):
        if t % 500 == 0:
            print(f'  trial {t}/{N_TRIALS}...')

        trial_seed = DEFAULT_SEED + t
        inst = generate_instance(
            DEFAULT_N, DEFAULT_R, DEFAULT_L,
            seed=trial_seed,
            min_opt_dist=1.0,
            max_opt_dist=DEFAULT_E / 2.0,
        )

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

    print(f'  trial {N_TRIALS}/{N_TRIALS}... done')
    print()

    # ------------------------------------------------------------------
    # 2.  Summary statistics.
    # ------------------------------------------------------------------
    summary: dict[str, dict] = {}
    for m in MODEL_LABELS:
        arr  = np.array([x for x in fcr_by_model[m] if not np.isnan(x)])
        n    = len(arr)
        mean = float(arr.mean())
        med  = float(np.median(arr))
        std  = float(arr.std(ddof=1))
        ci95 = Z95 * std / math.sqrt(n)
        summary[m] = dict(mean=mean, median=med, std=std, ci95=ci95, n=n,
                          arr=arr)

    print('  Summary  (mean ± 95% CI  |  median  |  std  |  n):')
    for m in MODEL_LABELS:
        s = summary[m]
        print(f'    {m:12s}  {s["mean"]:7.4f} ± {s["ci95"]:.4f}'
              f'  med={s["median"]:7.4f}  std={s["std"]:6.4f}  n={s["n"]}')
    print()

    # ------------------------------------------------------------------
    # 3.  Pairwise statistical separation.
    # ------------------------------------------------------------------
    print('  Pairwise separation  (mean_diff > sum_of_CIs → clearly separated):')
    sep_rows = []
    for m_lower, m_higher, label in PAIR_CHECKS:
        sl = summary[m_lower]
        sh = summary[m_higher]
        mean_diff  = sh['mean'] - sl['mean']          # positive ↔ m_higher is worse
        sum_cis    = sl['ci95'] + sh['ci95']
        separated  = mean_diff > sum_cis
        pct        = 100.0 * mean_diff / sh['mean'] if sh['mean'] > 0 else 0.0
        tag        = 'CLEARLY SEPARATED' if separated else 'NOT CLEARLY SEPARATED'
        print(f'    {label}')
        print(f'      {m_lower}: {sl["mean"]:.4f} ± {sl["ci95"]:.4f}'
              f'   {m_higher}: {sh["mean"]:.4f} ± {sh["ci95"]:.4f}')
        print(f'      mean_diff={mean_diff:.4f}  sum_CIs={sum_cis:.4f}'
              f'  pct={pct:.1f}%  → {tag}')
        sep_rows.append([m_lower, m_higher,
                         f'{sl["mean"]:.4f}', f'{sl["ci95"]:.4f}',
                         f'{sh["mean"]:.4f}', f'{sh["ci95"]:.4f}',
                         f'{mean_diff:.4f}', f'{sum_cis:.4f}',
                         f'{pct:.2f}', tag])
    print()

    # ------------------------------------------------------------------
    # 4.  Save CSV.
    # ------------------------------------------------------------------
    # Per-trial data
    write_csv(
        os.path.join(DATA_DIR, 'exp8_ci_table.csv'),
        [[t] + [fcr_by_model[m][t] for m in MODEL_LABELS] for t in range(N_TRIALS)],
        ['trial'] + MODEL_LABELS,
    )
    # Stats summary
    write_csv(
        os.path.join(DATA_DIR, 'exp8_stats.csv'),
        [[m, f"{summary[m]['mean']:.6f}", f"{summary[m]['median']:.6f}",
          f"{summary[m]['std']:.6f}", f"{summary[m]['ci95']:.6f}", summary[m]['n']]
         for m in MODEL_LABELS],
        ['model', 'mean_fcr', 'median_fcr', 'std', 'ci95', 'n'],
    )
    # Separation checks
    write_csv(
        os.path.join(DATA_DIR, 'exp8_separation.csv'),
        sep_rows,
        ['model_lower', 'model_higher',
         'mean_lower', 'ci95_lower',
         'mean_higher', 'ci95_higher',
         'mean_diff', 'sum_cis', 'pct_improvement', 'separation'],
    )

    # ------------------------------------------------------------------
    # 5.  Horizontal error-bar plot.
    # ------------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(8.5, 4.5))

    y      = np.arange(len(MODEL_LABELS))
    means  = [summary[m]['mean'] for m in MODEL_LABELS]
    cis    = [summary[m]['ci95'] for m in MODEL_LABELS]
    colors = ['#d62728', '#1f77b4', '#8c564b', '#9467bd',
              '#ff7f0e', '#2ca02c', '#17becf']

    ax.barh(y, means, xerr=cis, color=colors, alpha=0.82, height=0.55,
            capsize=5, error_kw={'elinewidth': 1.6, 'ecolor': '#222'})
    ax.set_yticks(y)
    ax.set_yticklabels(MODEL_LABELS)
    ax.set_xlabel('Mean Finder Competitive Ratio (FCR)')
    ax.set_title(
        f'Mean FCR with 95\\% Confidence Intervals\n'
        f'({N_TRIALS:,} paired trials, $n={DEFAULT_N}$, $R={DEFAULT_R}$, '
        f'$E={DEFAULT_E}$, $L={DEFAULT_L}$)',
        fontsize=11)
    ax.set_xlim(0, max(means) * 1.25)

    # Annotate with "mean ± ci" text
    for i, m in enumerate(MODEL_LABELS):
        s = summary[m]
        ax.text(s['mean'] + s['ci95'] + 0.02,
                i, f'{s["mean"]:.3f} ± {s["ci95"]:.3f}',
                va='center', fontsize=8.5)

    ax.invert_yaxis()   # M1 at top, M4* at bottom
    fig.tight_layout()
    save_fig(fig, 'fig_ci_table.png')

    # ------------------------------------------------------------------
    # 6.  LaTeX tabular block.
    # ------------------------------------------------------------------
    print()
    print('=' * 70)
    print('  LATEX TABLE  (copy-paste into paper)')
    print('=' * 70)

    # Friendly display names
    display = {
        'M1':         r'$\mathcal{M}_1$ (Random)',
        'M2':         r'$\mathcal{M}_2$ (Auction, $\infty$)',
        'HungarianD': r'$H_d$ (Hungarian, dist.)',
        'HungarianPD':r'$H_{pd}$ (Hungarian, $p/d$)',
        'M3':         r'$\mathcal{M}_3$ (Auction, single)',
        'M4':         r'$\mathcal{M}_4$ (Auction, multi, $p/d$)',
        'M4*':        r'$\mathcal{M}_4^*$ (Auction, multi, $p/d^2$)',
    }

    latex_lines = []
    latex_lines.append(r'\begin{table}[t]')
    latex_lines.append(r'\centering')
    latex_lines.append(
        r'\caption{Mean FCR with 95\,\% confidence intervals over '
        f'{N_TRIALS:,}' + r' paired trials ($n=30$, $R=3$, $E=14$, $L=10$).}')
    latex_lines.append(r'\label{tab:ci_table}')
    latex_lines.append(r'\begin{tabular}{@{}lrrrr@{}}')
    latex_lines.append(r'\toprule')
    latex_lines.append(r'Model & FCR (mean) & 95\,\% CI ($\pm$) & Median & Std \\')
    latex_lines.append(r'\midrule')
    for m in MODEL_LABELS:
        s   = summary[m]
        dm  = display[m]
        latex_lines.append(
            f'{dm} & {s["mean"]:.3f} & {s["ci95"]:.3f} & '
            f'{s["median"]:.3f} & {s["std"]:.3f} \\\\')
    latex_lines.append(r'\bottomrule')
    latex_lines.append(r'\end{tabular}')
    latex_lines.append(r'\end{table}')

    for line in latex_lines:
        print(line)

    print()
    print('  KEY RESULT — M4* vs M4 separation:')
    for row in sep_rows:
        if row[0] == 'M4*' and row[1] == 'M4':
            print(f'    M4*: {row[2]} ± {row[3]}   M4: {row[4]} ± {row[5]}')
            print(f'    mean_diff = {row[6]}   sum_CIs = {row[7]}')
            print(f'    M4* improves over M4 by {row[8]}%')
            print(f'    Statistical separation: {row[9]}')
    print('=' * 70)


if __name__ == '__main__':
    run()
