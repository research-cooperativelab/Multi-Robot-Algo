"""Experiment 2 — The Target-Delay Anomaly.

Hypothesis: 2-opt post-processing on Model 4* tours reduces total tour
length (as intended) yet INCREASES mean finder competitive ratio (FCR).
The mechanism is that 2-opt is oblivious to target position: it
redistributes where-within-the-tour the target happens to fall,
typically pushing high-probability-rich sites (which greedy-by-bid
visits FIRST) toward middle tour positions. Since real targets cluster
in high-probability sites, the target ends up later in the tour and
the finder walks farther before reaching it.

Protocol:
  * 500 trials at the default config (n=30, R=3, E=14, L=10, seed=42).
  * Identical pre-generated instances are fed to greedy M4* and
    2-opt-M4* with the p/d^2 bid so the comparison is paired.
  * For each trial where the target is found, record:
      - target_rank_in_tour : 1-indexed position of the target within
        the finder's tour (round_data[-1]['tour_per_robot'][finder]).
      - tour_length         : geometric length of that same tour,
        including base -> first-site and last-site -> base legs.
      - fcr                 : finder competitive ratio.

Outputs:
  - thesis/figures/fig_target_delay.png
      Left  panel: histogram of target-rank-in-tour (greedy vs 2-opt).
      Right panel: scatter of tour-length reduction vs FCR increase
                   (per trial, 2-opt minus greedy).
  - experiments/data/exp2_target_delay.csv
      columns: trial, model, target_rank_in_tour, tour_length, fcr.

Usage: python experiments/exp2_target_delay.py
"""
from __future__ import annotations

import math
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
    bid_p_over_d2, euclidean_distance, generate_instance,
    model_4_auction_multi, model_4_auction_multi_2opt,
)


def _tour_length(tour_nodes, base_pos, node_positions):
    """Total tour distance including base -> first and last -> base."""
    if not tour_nodes:
        return 0.0
    total = euclidean_distance(base_pos, node_positions[tour_nodes[0]])
    for k in range(len(tour_nodes) - 1):
        total += euclidean_distance(node_positions[tour_nodes[k]],
                                    node_positions[tour_nodes[k + 1]])
    total += euclidean_distance(node_positions[tour_nodes[-1]], base_pos)
    return total


def _extract_per_trial(result, instance):
    """Pull the three observables for a single (trial, model) cell.

    Returns (target_rank, tour_length, fcr) or None if the target was
    not found or the finder's tour is empty.
    """
    if result['found_by'] is None:
        return None
    finder = result['found_by']
    # The last round is the one the target was found in.
    last = result['round_data'][-1]
    tour_per_robot = last.get('tour_per_robot')
    if tour_per_robot is None or finder not in tour_per_robot:
        return None
    finder_tour = tour_per_robot[finder]
    target = instance['target']
    if target not in finder_tour:
        return None
    rank = finder_tour.index(target) + 1  # 1-indexed

    bases = instance['bases']
    node_positions = instance['node_positions']
    tlen = _tour_length(finder_tour, bases[finder], node_positions)

    opt = result['optimal_dist']
    if opt < 1e-9:
        return None
    fcr = result['robot_dists'][finder] / opt
    return rank, tlen, fcr


def run():
    enable_utf8_stdout()
    setup_style()
    print('Experiment 2: The Target-Delay Anomaly')
    print(f'  {DEFAULT_TRIALS} trials, n={DEFAULT_N}, R={DEFAULT_R}, '
          f'E={DEFAULT_E}, L={DEFAULT_L}')

    # Pre-generate instances once; both models see identical inputs.
    trials = []
    for t in range(DEFAULT_TRIALS):
        trial_seed = DEFAULT_SEED + t
        inst = generate_instance(DEFAULT_N, DEFAULT_R, DEFAULT_L,
                                 seed=trial_seed,
                                 min_opt_dist=1.0,
                                 max_opt_dist=DEFAULT_E / 2.0)
        trials.append(inst)

    rows = []           # rows for the CSV
    greedy = []         # list of (rank, tlen, fcr) for greedy M4*
    twoopt = []         # list of (rank, tlen, fcr) for 2-opt M4*
    paired = []         # list of (d_tlen, d_fcr) for trials where
                        # BOTH models found the target.

    n_greedy_found = 0
    n_twoopt_found = 0
    n_paired_trials = 0
    n_twoopt_worse = 0
    n_twoopt_same = 0
    n_twoopt_better = 0

    for t, inst in enumerate(trials):
        # Model 4* greedy.
        random.seed(DEFAULT_SEED + t)
        np.random.seed(DEFAULT_SEED + t)
        r_greedy = model_4_auction_multi(inst, DEFAULT_E,
                                         bid_func=bid_p_over_d2)

        # Model 4* with 2-opt.
        random.seed(DEFAULT_SEED + t)
        np.random.seed(DEFAULT_SEED + t)
        r_twoopt = model_4_auction_multi_2opt(inst, DEFAULT_E,
                                              bid_func=bid_p_over_d2)

        g = _extract_per_trial(r_greedy, inst)
        o = _extract_per_trial(r_twoopt, inst)

        if g is not None:
            greedy.append(g)
            rows.append((t, 'M4* greedy', g[0], g[1], g[2]))
            n_greedy_found += 1
        if o is not None:
            twoopt.append(o)
            rows.append((t, 'M4* 2-opt', o[0], o[1], o[2]))
            n_twoopt_found += 1

        if g is not None and o is not None:
            # tour-length reduction from 2-opt is (greedy_tlen - twoopt_tlen):
            # positive => 2-opt shortened the tour.
            d_tlen = g[1] - o[1]
            # FCR increase from 2-opt is (twoopt_fcr - greedy_fcr):
            # positive => 2-opt made FCR worse.
            d_fcr = o[2] - g[2]
            paired.append((d_tlen, d_fcr))
            n_paired_trials += 1
            if d_fcr > 1e-9:
                n_twoopt_worse += 1
            elif d_fcr < -1e-9:
                n_twoopt_better += 1
            else:
                n_twoopt_same += 1

    # --- Numerical summary -------------------------------------------------
    greedy_ranks = np.array([g[0] for g in greedy])
    twoopt_ranks = np.array([o[0] for o in twoopt])
    greedy_tlens = np.array([g[1] for g in greedy])
    twoopt_tlens = np.array([o[1] for o in twoopt])
    greedy_fcrs = np.array([g[2] for g in greedy])
    twoopt_fcrs = np.array([o[2] for o in twoopt])

    mean_rank_greedy = float(np.mean(greedy_ranks))
    mean_rank_twoopt = float(np.mean(twoopt_ranks))
    mean_fcr_greedy = float(np.mean(greedy_fcrs))
    mean_fcr_twoopt = float(np.mean(twoopt_fcrs))
    mean_tlen_greedy = float(np.mean(greedy_tlens))
    mean_tlen_twoopt = float(np.mean(twoopt_tlens))

    paired_dtlen = np.array([p[0] for p in paired])
    paired_dfcr = np.array([p[1] for p in paired])

    mean_tlen_reduction = float(np.mean(paired_dtlen))
    mean_fcr_increase = float(np.mean(paired_dfcr))
    frac_worse = n_twoopt_worse / max(n_paired_trials, 1)
    frac_better = n_twoopt_better / max(n_paired_trials, 1)
    frac_same = n_twoopt_same / max(n_paired_trials, 1)

    if len(paired_dtlen) > 1:
        corr = float(np.corrcoef(paired_dtlen, paired_dfcr)[0, 1])
    else:
        corr = float('nan')

    print()
    print('  Summary:')
    print(f'  trials where both models found target: {n_paired_trials}/{DEFAULT_TRIALS}')
    print(f'  greedy  M4*: mean target-rank = {mean_rank_greedy:5.3f}, '
          f'mean FCR = {mean_fcr_greedy:5.3f}, '
          f'mean tour length = {mean_tlen_greedy:5.3f}')
    print(f'  2-opt   M4*: mean target-rank = {mean_rank_twoopt:5.3f}, '
          f'mean FCR = {mean_fcr_twoopt:5.3f}, '
          f'mean tour length = {mean_tlen_twoopt:5.3f}')
    print(f'  2-opt tour-length reduction (paired): '
          f'{mean_tlen_reduction:+.3f} (positive = shorter)')
    print(f'  2-opt FCR increase (paired):          '
          f'{mean_fcr_increase:+.3f} (positive = worse)')
    print(f'  fraction of trials where 2-opt made FCR worse: '
          f'{frac_worse:.1%}')
    print(f'  fraction where 2-opt made FCR better:          '
          f'{frac_better:.1%}')
    print(f'  fraction where FCR unchanged:                   '
          f'{frac_same:.1%}')
    print(f'  correlation(tour-length reduction, FCR increase) = '
          f'{corr:+.3f}')

    # --- Figure: two-panel -------------------------------------------------
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11.5, 4.6))

    # Panel 1: side-by-side rank histogram.
    max_rank = int(max(greedy_ranks.max() if greedy_ranks.size else 1,
                       twoopt_ranks.max() if twoopt_ranks.size else 1))
    # Integer bin edges: [0.5, 1.5, ..., max_rank + 0.5].
    edges = np.arange(0.5, max_rank + 1.5, 1.0)
    centers = np.arange(1, max_rank + 1)
    width = 0.38

    g_counts, _ = np.histogram(greedy_ranks, bins=edges)
    o_counts, _ = np.histogram(twoopt_ranks, bins=edges)

    ax1.bar(centers - width / 2, g_counts, width=width,
            color='#2E7D32', alpha=0.85, label='M4* greedy',
            edgecolor='#1B4A1E', linewidth=0.5)
    ax1.bar(centers + width / 2, o_counts, width=width,
            color='#C65A3A', alpha=0.85, label='M4* + 2-opt',
            edgecolor='#7A2F18', linewidth=0.5)

    ax1.axvline(mean_rank_greedy, color='#2E7D32', ls=':',
                lw=1.4, alpha=0.85)
    ax1.axvline(mean_rank_twoopt, color='#C65A3A', ls=':',
                lw=1.4, alpha=0.85)
    ax1.set_xlabel('Target rank within finder tour (1 = first site visited)')
    ax1.set_ylabel('Number of trials')
    ax1.set_title('Where the target falls in the finder tour')
    ax1.set_xticks(centers)
    ax1.legend(loc='upper right', framealpha=0.92)

    # Panel 2: scatter of (tour-length reduction) vs (FCR increase).
    ax2.axhline(0, color='#888', lw=0.8, ls='-', alpha=0.7)
    ax2.axvline(0, color='#888', lw=0.8, ls='-', alpha=0.7)
    ax2.scatter(paired_dtlen, paired_dfcr,
                s=18, alpha=0.55, color='#2E5EAA',
                edgecolor='none')

    # Fit line for mechanism visibility (least squares through origin
    # is less honest than a plain OLS line, so use plain OLS).
    if len(paired_dtlen) >= 2:
        a, b = np.polyfit(paired_dtlen, paired_dfcr, 1)
        xs = np.linspace(paired_dtlen.min(), paired_dtlen.max(), 2)
        ax2.plot(xs, a * xs + b, color='#C65A3A', lw=1.8,
                 label=f'OLS slope = {a:+.3f}')
        ax2.legend(loc='upper left', framealpha=0.92)

    ax2.set_xlabel(r'Tour-length reduction from 2-opt '
                   r'$(\ell_{\mathrm{greedy}} - \ell_{\mathrm{2opt}})$')
    ax2.set_ylabel(r'FCR increase from 2-opt '
                   r'$(\mathrm{FCR}_{\mathrm{2opt}} - '
                   r'\mathrm{FCR}_{\mathrm{greedy}})$')
    ax2.set_title('Shorter tour, worse finder-centric FCR')

    # Annotate the quadrant counts to make the mechanism legible.
    q_upper_right = int(np.sum((paired_dtlen > 0) & (paired_dfcr > 0)))
    q_lower_right = int(np.sum((paired_dtlen > 0) & (paired_dfcr < 0)))
    xmin, xmax = ax2.get_xlim()
    ymin, ymax = ax2.get_ylim()
    # Upper-right: 2-opt shortened tour but made FCR worse. This is
    # the "Target-Delay" quadrant — the paradoxical outcome.
    ax2.text(xmax * 0.98, ymax * 0.88,
             f'n={q_upper_right}\n(shorter, worse)',
             ha='right', va='top', fontsize=8, color='#7A2F18',
             bbox=dict(boxstyle='round,pad=0.25', fc='#FFF5F0',
                       ec='#C65A3A', lw=0.6))
    # Lower-right: 2-opt helped both length and FCR. The ideal case.
    ax2.text(xmax * 0.98, ymin * 0.88,
             f'n={q_lower_right}\n(shorter, better)',
             ha='right', va='bottom', fontsize=8, color='#1B4A1E',
             bbox=dict(boxstyle='round,pad=0.25', fc='#F0F7F0',
                       ec='#2E7D32', lw=0.6))

    fig.suptitle('Experiment 2: The Target-Delay Anomaly '
                 '(M4* with vs. without 2-opt, 500 trials)',
                 y=1.02)
    save_fig(fig, 'fig_target_delay.png')

    # --- CSV --------------------------------------------------------------
    write_csv(os.path.join(DATA_DIR, 'exp2_target_delay.csv'),
              rows,
              header=['trial', 'model', 'target_rank_in_tour',
                      'tour_length', 'fcr'])

    # --- Final headline numbers for the thesis ----------------------------
    print()
    print('  Headline numbers for thesis:')
    print(f'    mean target rank, greedy  M4* : {mean_rank_greedy:.3f}')
    print(f'    mean target rank, 2-opt   M4* : {mean_rank_twoopt:.3f}')
    print(f'    mean FCR,         greedy  M4* : {mean_fcr_greedy:.3f}')
    print(f'    mean FCR,         2-opt   M4* : {mean_fcr_twoopt:.3f}')
    delta_pct = (mean_fcr_twoopt - mean_fcr_greedy) / mean_fcr_greedy * 100
    print(f'    FCR degradation from 2-opt    : {delta_pct:+.2f}%')
    print(f'    trials where 2-opt made FCR worse: '
          f'{n_twoopt_worse}/{n_paired_trials} ({frac_worse:.1%})')
    print(f'    mean tour-length reduction    : {mean_tlen_reduction:+.3f}')
    print(f'    corr(tlen-reduction, FCR-inc) : {corr:+.3f}')


if __name__ == '__main__':
    run()
