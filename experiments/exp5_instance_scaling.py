"""Experiment 5 — Instance Scaling (n and R generalization).

This experiment tests whether the model ranking and the headline findings
(Findings 1–4 of the thesis) generalize beyond the default n=30, R=3
configuration.

Protocol:
  * N sweep: n ∈ {30, 50, 100} at default R=3, E=14, L=10.
    500 trials per n value, identical instances across all models.
  * R sweep: R ∈ {1, 2, 3, 4, 5, 6, 8, 10} at default n=30, E=14.
    500 trials per R value.
  * Models evaluated: M1, M2, M3, M4, M4*, HungarianD.

Hypothesis: the relative ordering
  M2 < M4* ≤ M4 < M3 < H_d < M1
is preserved across all (n, R) configurations tested.

Outputs:
  - experiments/data/exp5_n_sweep.csv      (mean FCR by n, model)
  - experiments/data/exp5_r_sweep.csv      (mean FCR by R, model)
  - thesis/figures/fig_instance_scaling.png (2-panel: n sweep + R sweep)

Usage:
  cd <repo_root>/experiments
  python exp5_instance_scaling.py
"""
from __future__ import annotations

import os
import sys

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec

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
N_VALUES    = [30, 50, 100]   # instance sizes for n-sweep
R_VALUES    = [1, 2, 3, 4, 5, 6, 8, 10]  # fleet sizes for R-sweep
N_TRIALS    = 500             # per configuration

MODEL_LABELS   = ['M1', 'M2', 'H_d', 'M3', 'M4', 'M4*']
MODEL_COLORS   = {
    'M1':  '#d62728',
    'M2':  '#1f77b4',
    'H_d': '#8c564b',
    'M3':  '#ff7f0e',
    'M4':  '#2ca02c',
    'M4*': '#17becf',
}
MODEL_MARKERS  = {'M1': 'o', 'M2': 's', 'H_d': 'D', 'M3': '^', 'M4': 'v', 'M4*': '*'}


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _compute_fcr(result: dict) -> float | None:
    finder = result.get('found_by')
    if finder is None:
        return None
    dists = result.get('robot_dists', {})
    opt   = result.get('optimal_dist', 0.0)
    if opt <= 0:
        return None
    return dists[finder] / opt


def _run_config(n: int, r: int, trials: int, base_seed: int) -> dict[str, list[float]]:
    """Run all models on `trials` identical instances for given (n, r).

    Returns dict of model -> list of FCR values (NaN on failure).
    """
    fcr: dict[str, list] = {m: [] for m in MODEL_LABELS}
    for t in range(trials):
        inst = generate_instance(
            n, r, DEFAULT_L,
            seed=base_seed + t,
            min_opt_dist=1.0,
            max_opt_dist=DEFAULT_E / 2.0,
        )
        fcr['M1'].append( _compute_fcr(model_1_random_infinite(inst)) or np.nan)
        fcr['M2'].append( _compute_fcr(model_2_auction_infinite(inst)) or np.nan)
        fcr['H_d'].append(_compute_fcr(model_hungarian_single(inst, DEFAULT_E)) or np.nan)
        fcr['M3'].append( _compute_fcr(model_3_auction_single(inst, DEFAULT_E, bid_p_over_d)) or np.nan)
        fcr['M4'].append( _compute_fcr(model_4_auction_multi(inst, DEFAULT_E, bid_p_over_d)) or np.nan)
        fcr['M4*'].append(_compute_fcr(model_4_auction_multi(inst, DEFAULT_E, bid_p_over_d2)) or np.nan)
    return {m: np.nanmean(fcr[m]) for m in MODEL_LABELS}


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run():
    enable_utf8_stdout()
    setup_style()
    print('Experiment 5: Instance Scaling')
    print(f'  n sweep: {N_VALUES}  (R={DEFAULT_R}, E={DEFAULT_E})')
    print(f'  R sweep: {R_VALUES}  (n={DEFAULT_N}, E={DEFAULT_E})')
    print(f'  {N_TRIALS} trials per configuration')
    print()

    # ------------------------------------------------------------------
    # 1. n sweep (R fixed at default)
    # ------------------------------------------------------------------
    print('  Running n sweep...')
    n_sweep: dict[int, dict[str, float]] = {}
    for n in N_VALUES:
        print(f'    n={n}...', end=' ', flush=True)
        n_sweep[n] = _run_config(n, DEFAULT_R, N_TRIALS, DEFAULT_SEED)
        row = '  '.join(f'{m}={n_sweep[n][m]:.3f}' for m in MODEL_LABELS)
        print(row)

    n_rows = []
    for n in N_VALUES:
        for m in MODEL_LABELS:
            n_rows.append([n, m, f'{n_sweep[n][m]:.4f}'])
    write_csv(os.path.join(DATA_DIR, 'exp5_n_sweep.csv'), n_rows,
              ['n', 'model', 'mean_fcr'])

    # ------------------------------------------------------------------
    # 2. R sweep (n fixed at default)
    # ------------------------------------------------------------------
    print('  Running R sweep...')
    r_sweep: dict[int, dict[str, float]] = {}
    for r in R_VALUES:
        print(f'    R={r}...', end=' ', flush=True)
        r_sweep[r] = _run_config(DEFAULT_N, r, N_TRIALS, DEFAULT_SEED + 5000)
        row = '  '.join(f'{m}={r_sweep[r][m]:.3f}' for m in MODEL_LABELS)
        print(row)

    r_rows = []
    for r in R_VALUES:
        for m in MODEL_LABELS:
            r_rows.append([r, m, f'{r_sweep[r][m]:.4f}'])
    write_csv(os.path.join(DATA_DIR, 'exp5_r_sweep.csv'), r_rows,
              ['R', 'model', 'mean_fcr'])

    # ------------------------------------------------------------------
    # 3. Plot: two-panel figure.
    # ------------------------------------------------------------------
    fig = plt.figure(figsize=(12, 5))
    gs  = gridspec.GridSpec(1, 2, wspace=0.35)

    # Panel A: n sweep
    ax1 = fig.add_subplot(gs[0])
    for m in MODEL_LABELS:
        vals = [n_sweep[n][m] for n in N_VALUES]
        ax1.plot(N_VALUES, vals,
                 marker=MODEL_MARKERS[m], color=MODEL_COLORS[m],
                 label=m, linewidth=2.0, markersize=8)
    ax1.set_xlabel('Number of candidate sites $n$')
    ax1.set_ylabel('Mean Finder Competitive Ratio (FCR)')
    ax1.set_title(f'FCR vs.\ $n$ ($R={DEFAULT_R}$, $E={DEFAULT_E}$,\n{N_TRIALS} trials per point)')
    ax1.legend(loc='upper right', fontsize=9)
    ax1.set_xticks(N_VALUES)

    # Panel B: R sweep
    ax2 = fig.add_subplot(gs[1])
    for m in MODEL_LABELS:
        vals = [r_sweep[r][m] for r in R_VALUES]
        ax2.plot(R_VALUES, vals,
                 marker=MODEL_MARKERS[m], color=MODEL_COLORS[m],
                 label=m, linewidth=2.0, markersize=8)
    ax2.set_xlabel('Fleet size $R$')
    ax2.set_ylabel('Mean Finder Competitive Ratio (FCR)')
    ax2.set_title(f'FCR vs.\ $R$ ($n={DEFAULT_N}$, $E={DEFAULT_E}$,\n{N_TRIALS} trials per point)')
    ax2.legend(loc='upper right', fontsize=9)
    ax2.set_xticks(R_VALUES)

    save_fig(fig, 'fig_instance_scaling.png')

    # ------------------------------------------------------------------
    # 4. Print summary table.
    # ------------------------------------------------------------------
    print()
    print('=== n sweep summary ===')
    print(f'{"n":>5}  ' + '  '.join(f'{m:>8}' for m in MODEL_LABELS))
    for n in N_VALUES:
        print(f'{n:>5}  ' + '  '.join(f'{n_sweep[n][m]:>8.3f}' for m in MODEL_LABELS))
    print()
    print('=== R sweep summary ===')
    print(f'{"R":>5}  ' + '  '.join(f'{m:>8}' for m in MODEL_LABELS))
    for r in R_VALUES:
        print(f'{r:>5}  ' + '  '.join(f'{r_sweep[r][m]:>8.3f}' for m in MODEL_LABELS))

    # Verify ordering preserved
    print()
    print('=== Ordering check (M2 < M4* ≤ M4 < M3 < H_d < M1) ===')
    for n in N_VALUES:
        v = n_sweep[n]
        ok = v['M2'] < v['M4*'] and v['M4*'] <= v['M4'] and v['M4'] < v['M3'] \
             and v['M3'] < v['H_d'] and v['H_d'] < v['M1']
        print(f'  n={n:>3}: {"PASS" if ok else "FAIL"} '
              f'(M2={v["M2"]:.2f} M4*={v["M4*"]:.2f} M4={v["M4"]:.2f} '
              f'M3={v["M3"]:.2f} H_d={v["H_d"]:.2f} M1={v["M1"]:.2f})')
    for r in R_VALUES:
        v = r_sweep[r]
        ok = v['M2'] < v['M4*'] and v['M4*'] <= v['M4'] and v['M4'] < v['M3'] \
             and v['M3'] < v['H_d'] and v['H_d'] < v['M1']
        print(f'  R={r:>2}: {"PASS" if ok else "FAIL"} '
              f'(M2={v["M2"]:.2f} M4*={v["M4*"]:.2f} M4={v["M4"]:.2f} '
              f'M3={v["M3"]:.2f} H_d={v["H_d"]:.2f} M1={v["M1"]:.2f})')

    print()
    print('Done.')


if __name__ == '__main__':
    run()
