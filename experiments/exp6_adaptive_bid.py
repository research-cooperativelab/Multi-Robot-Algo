"""Experiment 6 — Adaptive Bid Exponent: Does p/d^alpha beat p/d^2?

Tests bid functions of the form b(r, i) = p_i / d^alpha where alpha varies,
plus an adaptive variant where alpha scales with energy consumption.

Bid variants tested:
  alpha_1.0  — Standard p/d  (paper M4)
  alpha_1.5  — Intermediate
  alpha_2.0  — p/d^2 (paper M4*)
  alpha_2.5  — More aggressive
  alpha_3.0  — Very aggressive
  adaptive   — alpha(E_rem) = 1 + fraction_used
               fraction_used = (E - E_rem) / E
               so alpha starts at 1.0 (full battery) -> 2.0 (empty battery)

The adaptive bid is implemented as a modified auction loop that, for each
robot's sortie, uses the remaining-energy fraction at the time of the Phase 1
auction assignment to set the exponent. This captures the foreclosure argument
from the paper's Corollary dynamically: when energy is tight, penalise distance
more aggressively.

Key question: Is p/d^2 (alpha=2) truly optimal, or does a higher static or
adaptive exponent win?

Outputs:
  experiments/data/exp6_adaptive_bid.csv   (per-trial FCR for all 6 variants)
  experiments/data/exp6_stats.csv          (per-variant summary stats)
  thesis/figures/fig_adaptive_bid.png      (bar chart with 95% CI)

Usage:
  cd <repo_root>/experiments
  python exp6_adaptive_bid.py
"""
from __future__ import annotations

import math
import os
import sys

import numpy as np
import matplotlib.pyplot as plt
from scipy.stats import wilcoxon

# ---------------------------------------------------------------------------
# Path setup (mirrors every other experiment)
# ---------------------------------------------------------------------------
_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from _common import (
    DEFAULT_E, DEFAULT_L, DEFAULT_N, DEFAULT_R, DEFAULT_SEED,
    DATA_DIR, FIG_DIR,
    enable_utf8_stdout, save_fig, setup_style, write_csv,
)

import main as sar
from main import (
    generate_instance,
    model_4_auction_multi,
    bid_p_over_d,
    bid_p_over_d2,
    euclidean_distance,
    entropy,
    bayesian_update,
    run_auction,
)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
N_TRIALS = 1000
ALPHA_VARIANTS = [1.0, 1.5, 2.0, 2.5, 3.0]
VARIANT_LABELS = ['alpha_1.0', 'alpha_1.5', 'alpha_2.0', 'alpha_2.5', 'alpha_3.0', 'adaptive']


# ---------------------------------------------------------------------------
# Adaptive Model 4
# ---------------------------------------------------------------------------

def model_4_adaptive_bid(instance, energy):
    """
    MODEL 4 with adaptive bid exponent.

    Robots recharge to full energy E at their base between sorties (same as
    the standard model_4_auction_multi). The adaptive exponent reflects
    within-sortie energy depletion:

        alpha = 1 + fraction_used
        fraction_used = (E - E_rem_in_current_sortie) / E

    At the Phase 1 auction each robot has full energy, so:
        E_rem = E  =>  fraction_used = 0  =>  alpha = 1.0  (same as p/d)

    As the robot moves through its chain, E_rem decreases:
        When half the energy is spent:  fraction_used = 0.5  =>  alpha = 1.5
        When energy runs out:           fraction_used -> 1.0  =>  alpha -> 2.0

    This directly captures the foreclosure argument: a robot that has already
    consumed most of its sortie budget should penalise further distance more
    steeply, since the marginal cost of an extra metre is superlinear.

    The Phase 1 auction always uses alpha=1.0 (full battery at sortie start).
    The greedy chain extension uses the per-robot within-sortie alpha that
    evolves as distance accumulates.
    """
    np_ = instance['node_positions']
    probs = dict(instance['node_probs'])
    bases = instance['bases']
    target = instance['target']
    opt = instance['optimal_dist']
    n_robots = len(bases)

    available = set(np_.keys())
    robot_dists = {r: 0.0 for r in range(n_robots)}
    round_data = []
    iteration = 0

    while available:
        iteration += 1
        H_before = entropy(probs)

        # Phase 1: SSI Auction — robots start each sortie with full energy E.
        # At sortie start fraction_used=0 => alpha=1.0 (same as standard p/d).
        robot_bids = {}
        for r in range(n_robots):
            bids = []
            for n in available:
                d = euclidean_distance(bases[r], np_[n])
                # Energy feasibility: round-trip 2*d <= E
                if 2 * d <= energy and d > 0 and probs.get(n, 0) > 0:
                    # alpha=1.0 at sortie start
                    bv = probs[n] / d
                    bids.append((n, bv, d))
            bids.sort(key=lambda x: x[1], reverse=True)
            robot_bids[r] = bids

        if all(len(b) == 0 for b in robot_bids.values()):
            break
        first_assigned = run_auction(robot_bids)
        if not first_assigned:
            break

        # Phase 2: Greedy chain extension with adaptive alpha.
        # robot_sortie_dist[r] = distance accumulated so far in THIS sortie.
        all_claimed = set(n for n, d in first_assigned.values())
        robot_tours = {}
        robot_rem = {}   # remaining energy budget within this sortie
        robot_pos = {}
        robot_sortie_dist = {}  # distance walked so far this sortie (for alpha)

        for r, (node, dist) in first_assigned.items():
            robot_tours[r] = [(node, dist)]
            robot_pos[r] = np_[node]
            robot_rem[r] = energy - dist
            robot_sortie_dist[r] = dist

        active = set(first_assigned.keys())
        while active:
            progress = False
            for r in list(active):
                # Adaptive alpha: based on fraction of E already consumed this sortie
                fraction_used = robot_sortie_dist[r] / energy  # in (0, 1)
                alpha = 1.0 + fraction_used                    # in (1.0, 2.0)

                best_node, best_bid, best_d = None, -1, 0
                for n in available - all_claimed:
                    d_to = euclidean_distance(robot_pos[r], np_[n])
                    d_back = euclidean_distance(np_[n], bases[r])
                    if d_to + d_back <= robot_rem[r] and d_to > 0 and probs.get(n, 0) > 0:
                        bv = probs[n] / (d_to ** alpha)
                        if bv > best_bid:
                            best_bid, best_d, best_node = bv, d_to, n
                if best_node is None:
                    active.discard(r)
                else:
                    robot_tours[r].append((best_node, best_d))
                    all_claimed.add(best_node)
                    robot_rem[r] -= best_d
                    robot_sortie_dist[r] += best_d
                    robot_pos[r] = np_[best_node]
                    progress = True
            if not progress:
                break

        # Phase 3: Execute tours (same as model_4_auction_multi)
        found, finder = False, None
        visited = set()
        prob_cap = 0.0

        for r, tour in robot_tours.items():
            for node, d in tour:
                robot_dists[r] += d
                visited.add(node)
                prob_cap += probs.get(node, 0)
                if node == target:
                    found, finder = True, r
                    break
            if found and r == finder:
                pass  # finder stops — no return trip
            else:
                if tour:
                    last_node = tour[-1][0]
                    robot_dists[r] += euclidean_distance(np_[last_node], bases[r])

        probs = bayesian_update(probs, visited)
        available -= visited
        H_after = entropy(probs) if available else 0

        round_data.append({
            'round': iteration,
            'entropy_before': H_before,
            'entropy_after': H_after,
            'prob_captured': prob_cap,
            'sites_visited': len(visited),
            'found_target': found,
        })

        if found:
            return {
                'model': 'M4_adaptive',
                'found_by': finder,
                'robot_dists': dict(robot_dists),
                'optimal_dist': opt,
                'iterations': iteration,
                'round_data': round_data,
            }

    return {
        'model': 'M4_adaptive',
        'found_by': None,
        'robot_dists': dict(robot_dists),
        'optimal_dist': opt,
        'iterations': iteration,
        'round_data': round_data,
    }


# ---------------------------------------------------------------------------
# Helper: build a static-alpha bid function closure
# ---------------------------------------------------------------------------

def make_alpha_bid(alpha: float):
    """Return a bid_func(p, d, E=None) that computes p / d^alpha."""
    def _bid(p, d, E=None):
        return p / (d ** alpha) if d > 0 else 0.0
    _bid.__name__ = f'bid_alpha_{alpha}'
    return _bid


# ---------------------------------------------------------------------------
# Helper: extract FCR from a result dict
# ---------------------------------------------------------------------------

def _compute_fcr(result: dict):
    finder = result.get('found_by')
    if finder is None:
        return None
    dists = result.get('robot_dists', {})
    opt = result.get('optimal_dist', 0.0)
    if opt <= 0:
        return None
    return dists[finder] / opt


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run():
    enable_utf8_stdout()
    setup_style()

    print('Experiment 6: Adaptive Bid Exponent')
    print(f'  {N_TRIALS} paired trials  n={DEFAULT_N}  R={DEFAULT_R}  '
          f'E={DEFAULT_E}  L={DEFAULT_L}')
    print(f'  Variants: {VARIANT_LABELS}')
    print()

    # ------------------------------------------------------------------
    # Build bid functions
    # ------------------------------------------------------------------
    static_bid_fns = {f'alpha_{a}': make_alpha_bid(a) for a in ALPHA_VARIANTS}

    # Verify our alpha_2.0 matches the canonical bid_p_over_d2 (sanity check)
    # bid_p_over_d2(p, d) = p / d^2 — same as make_alpha_bid(2.0)(p, d)

    # ------------------------------------------------------------------
    # 1. Run all variants on N_TRIALS identical instances.
    # ------------------------------------------------------------------
    fcr_by_variant: dict[str, list] = {v: [] for v in VARIANT_LABELS}

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

        # Static alpha variants
        for a in ALPHA_VARIANTS:
            label = f'alpha_{a}'
            result = model_4_auction_multi(inst, DEFAULT_E, static_bid_fns[label])
            fcr_by_variant[label].append(_compute_fcr(result) or np.nan)

        # Adaptive variant
        result_adp = model_4_adaptive_bid(inst, DEFAULT_E)
        fcr_by_variant['adaptive'].append(_compute_fcr(result_adp) or np.nan)

    # ------------------------------------------------------------------
    # 2. Summary statistics.
    # ------------------------------------------------------------------
    print()
    print('  Summary  (mean ± 95% CI  |  median  |  std  |  n_valid):')
    print(f'  {"Variant":<14}  {"Mean":>7}  {"±95%CI":>7}  {"Median":>8}  {"Std":>7}  {"n":>5}')
    print('  ' + '-' * 58)
    summary: dict[str, dict] = {}
    for v in VARIANT_LABELS:
        arr = np.array([x for x in fcr_by_variant[v] if not np.isnan(x)])
        mean = arr.mean()
        med  = np.median(arr)
        std  = arr.std(ddof=1)
        ci95 = 1.96 * std / np.sqrt(len(arr))
        summary[v] = dict(mean=mean, median=med, std=std, ci95=ci95, n=len(arr))
        print(f'  {v:<14}  {mean:>7.3f}  {ci95:>7.3f}  {med:>8.3f}  {std:>7.3f}  {len(arr):>5}')

    # ------------------------------------------------------------------
    # 3. Paired Wilcoxon tests: each variant vs alpha_2.0 (our M4*)
    # ------------------------------------------------------------------
    print()
    print('  Paired Wilcoxon tests (each variant vs alpha_2.0 = M4*):')
    baseline = 'alpha_2.0'
    wilcox_rows = []
    for v in VARIANT_LABELS:
        if v == baseline:
            continue
        a = np.array(fcr_by_variant[baseline])
        b = np.array(fcr_by_variant[v])
        mask = ~(np.isnan(a) | np.isnan(b))
        a_clean, b_clean = a[mask], b[mask]
        diff = b_clean - a_clean
        if np.all(diff == 0):
            print(f'    {v:14s} vs alpha_2.0: identical — skip')
            continue
        try:
            stat, p_two = wilcoxon(diff)
        except Exception as exc:
            print(f'    {v:14s} vs alpha_2.0: wilcoxon error ({exc})')
            continue
        direction = 'lower' if b_clean.mean() < a_clean.mean() else 'higher'
        tag = ('p<0.001' if p_two < 0.001 else
               ('p<0.01' if p_two < 0.01 else
                ('p<0.05' if p_two < 0.05 else f'p={p_two:.4f}')))
        delta_pct = (b_clean.mean() - a_clean.mean()) / a_clean.mean() * 100
        print(f'    {v:14s} vs alpha_2.0:  '
              f'{b_clean.mean():.4f} vs {a_clean.mean():.4f}  '
              f'delta={delta_pct:+.1f}%  W={stat:.0f}  {tag}  ({direction})')
        wilcox_rows.append([v, baseline, f'{b_clean.mean():.4f}',
                            f'{a_clean.mean():.4f}', f'{delta_pct:.2f}',
                            f'{stat:.0f}', f'{p_two:.4e}', tag, direction])

    # ------------------------------------------------------------------
    # 4. Save CSV data.
    # ------------------------------------------------------------------
    write_csv(
        os.path.join(DATA_DIR, 'exp6_adaptive_bid.csv'),
        [[t] + [fcr_by_variant[v][t] for v in VARIANT_LABELS] for t in range(N_TRIALS)],
        ['trial'] + VARIANT_LABELS,
    )
    write_csv(
        os.path.join(DATA_DIR, 'exp6_stats.csv'),
        [[v, f"{summary[v]['mean']:.4f}", f"{summary[v]['median']:.4f}",
          f"{summary[v]['std']:.4f}", f"{summary[v]['ci95']:.4f}", summary[v]['n']]
         for v in VARIANT_LABELS],
        ['variant', 'mean_fcr', 'median_fcr', 'std', 'ci95', 'n'],
    )
    if wilcox_rows:
        write_csv(
            os.path.join(DATA_DIR, 'exp6_wilcoxon.csv'),
            wilcox_rows,
            ['variant', 'baseline', 'mean_variant', 'mean_baseline',
             'delta_pct', 'W_stat', 'p_value', 'tag', 'direction'],
        )

    # ------------------------------------------------------------------
    # 5. Bar chart with 95% CI.
    # ------------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(9.0, 4.5))
    x     = np.arange(len(VARIANT_LABELS))
    means = [summary[v]['mean'] for v in VARIANT_LABELS]
    cis   = [summary[v]['ci95'] for v in VARIANT_LABELS]

    # Color scheme: grey ramp for static, distinct for adaptive
    bar_colors = ['#9ecae1', '#6baed6', '#2171b5', '#08519c', '#08306b', '#e6550d']

    bars = ax.bar(x, means, color=bar_colors, alpha=0.88, width=0.62,
                  yerr=cis, capsize=5,
                  error_kw={'elinewidth': 1.5, 'ecolor': '#333'})

    # Highlight the winner
    best_idx = int(np.argmin(means))
    bars[best_idx].set_edgecolor('#FFD700')
    bars[best_idx].set_linewidth(2.5)

    # Annotate each bar with its mean value
    for bar, m in zip(bars, means):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + max(cis) * 0.25,
                f'{m:.3f}', ha='center', va='bottom', fontsize=9, fontweight='bold')

    # Axis labels
    tick_labels = [
        r'$\alpha=1.0$' + '\n(p/d)',
        r'$\alpha=1.5$',
        r'$\alpha=2.0$' + '\n(p/d²)',
        r'$\alpha=2.5$',
        r'$\alpha=3.0$',
        'Adaptive\n' + r'$\alpha(E_{\rm rem})$',
    ]
    ax.set_xticks(x)
    ax.set_xticklabels(tick_labels, fontsize=10)
    ax.set_ylabel('Mean Finder Competitive Ratio (FCR)', fontsize=12)
    ax.set_title(
        f'Bid Exponent Sweep: $b(r,i) = p_i / d^{{\\alpha}}$ '
        f'with Adaptive Variant\n'
        f'({N_TRIALS} paired trials, $n={DEFAULT_N}$, $R={DEFAULT_R}$, $E={DEFAULT_E}$)',
        fontsize=11)
    ax.set_ylim(0, max(means) * 1.18)

    # Reference line at alpha=2.0
    ax.axhline(summary['alpha_2.0']['mean'], color='#2171b5',
               linestyle='--', linewidth=1.0, alpha=0.55,
               label=r'$\alpha=2.0$ baseline (M4*)')
    ax.legend(fontsize=9)

    fig.tight_layout()
    save_fig(fig, 'fig_adaptive_bid.png')

    # ------------------------------------------------------------------
    # 6. LaTeX-ready table.
    # ------------------------------------------------------------------
    print()
    print('=' * 70)
    print('  LATEX-READY TABLE (copy into thesis/paper)')
    print('=' * 70)
    print(r'  \begin{tabular}{lrrrr}')
    print(r'  \hline')
    print(r'  Bid variant & Mean FCR & $\pm$95\%~CI & Median & Std \\')
    print(r'  \hline')
    tex_labels = {
        'alpha_1.0': r'$p/d^{1.0}$ (M4, standard)',
        'alpha_1.5': r'$p/d^{1.5}$',
        'alpha_2.0': r'$p/d^{2.0}$ (M4*, paper bid)',
        'alpha_2.5': r'$p/d^{2.5}$',
        'alpha_3.0': r'$p/d^{3.0}$',
        'adaptive':  r'Adaptive $\alpha(E_{\rm rem})$',
    }
    for v in VARIANT_LABELS:
        s = summary[v]
        star = ' $\\star$' if v == VARIANT_LABELS[best_idx] else ''
        print(f'  {tex_labels[v]}{star} & {s["mean"]:.3f} & {s["ci95"]:.3f} '
              f'& {s["median"]:.3f} & {s["std"]:.3f} \\\\')
    print(r'  \hline')
    print(r'  \end{tabular}')
    print()

    # ------------------------------------------------------------------
    # 7. Plain-English summary.
    # ------------------------------------------------------------------
    winner = VARIANT_LABELS[best_idx]
    winner_mean = means[best_idx]
    alpha2_mean = summary['alpha_2.0']['mean']
    improvement = (alpha2_mean - winner_mean) / alpha2_mean * 100

    print('  KEY FINDINGS')
    print('  ' + '-' * 60)
    print(f'  Winner: {winner}  (mean FCR = {winner_mean:.4f})')
    print(f'  p/d^2 (alpha=2.0): mean FCR = {alpha2_mean:.4f}')
    if winner == 'alpha_2.0':
        print('  -> p/d^2 is CONFIRMED OPTIMAL among all tested variants.')
    else:
        print(f'  -> {winner} beats p/d^2 by {improvement:.2f}% (mean FCR difference)')
        if improvement > 0.5:
            print('  -> This is a MEANINGFUL improvement; consider updating Result 4.')
        else:
            print('  -> Improvement is MARGINAL; p/d^2 claim in the paper is robust.')

    print()
    print('  Full ranking (best to worst):')
    ranked = sorted(VARIANT_LABELS, key=lambda v: summary[v]['mean'])
    for rank, v in enumerate(ranked, 1):
        s = summary[v]
        delta = (s['mean'] - alpha2_mean) / alpha2_mean * 100
        marker = ' <-- WINNER' if rank == 1 else (' <-- M4* baseline' if v == 'alpha_2.0' else '')
        print(f'    {rank}. {v:<14}  mean={s["mean"]:.4f}  '
              f'ci95=±{s["ci95"]:.4f}  delta_vs_alpha2={delta:+.2f}%{marker}')
    print('=' * 70)


if __name__ == '__main__':
    run()
