"""Experiment 7 — Prior Sensitivity Analysis.

Tests whether the model ordering  M2 < M4* <= M4 < M3 < H_d < M1  holds
across five qualitatively different prior distributions.  For each prior
shape we run 500 paired trials (all six models see the same instance).

Prior shapes
------------
  concentrated   Dirichlet(alpha=0.2): very peaky, one site dominates
  moderate       Uniform(0.1,1.0) normalised (paper baseline)
  diffuse        Dirichlet(alpha=2.0): broader, no strong peak
  near-uniform   Dirichlet(alpha=10.0): nearly flat p_i ~ 1/n
  power-law      raw[i] = U(0,1)^3, normalised: heavy-tailed skew

For each prior type the experiment:
  * generates positions and bases with generate_instance() (seed-based)
  * replaces node_probs + resamples the target from the new probs
    (with the same min_opt_dist / max_opt_dist guards as generate_instance)
  * runs all six models and records per-trial FCR
  * checks whether the ordering holds
  * saves fig_prior_sensitivity.png  (grouped bar chart)
  * prints a LaTeX table

Key questions
-------------
  1. Is the model ordering robust across prior shapes?
  2. Does M4* advantage over M4 grow with concentration?
  3. Does probability-aware bidding (M3 vs H_d) matter more when
     priors are concentrated?

Usage
-----
  cd <repo_root>/experiments
  python exp7_prior_sensitivity.py
"""
from __future__ import annotations

import os
import sys
import random

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from _common import (
    DEFAULT_E, DEFAULT_L, DEFAULT_N, DEFAULT_R, DEFAULT_SEED,
    DATA_DIR, FIG_DIR,
    enable_utf8_stdout, save_fig, setup_style, write_csv,
)

import main as sar
from main import (
    bid_p_over_d,
    bid_p_over_d2,
    euclidean_distance,
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
N_TRIALS = 500
N        = DEFAULT_N    # 30 nodes
R        = DEFAULT_R    # 3 robots
E        = DEFAULT_E    # 14.0 energy
L        = DEFAULT_L    # 10.0 area scale
SEED     = DEFAULT_SEED

MODEL_LABELS = ['M2', 'M4*', 'M4', 'M3', 'H_d', 'M1']

# Paper ordering (best to worst, i.e. lowest FCR first):
#   M2 < M4* <= M4 < M3 < H_d < M1
# "M4* <= M4" is a weak inequality — they can tie.
ORDERING_PAIRS = [
    ('M2',  'M4*'),   # M2  < M4*
    ('M4*', 'M4'),    # M4* <= M4  (weak)
    ('M4',  'M3'),    # M4  < M3
    ('M3',  'H_d'),   # M3  < H_d
    ('H_d', 'M1'),    # H_d < M1
]

PRIOR_TYPES = [
    'concentrated',   # Dirichlet(0.2)
    'moderate',       # Uniform(0.1,1.0)  — paper baseline
    'diffuse',        # Dirichlet(2.0)
    'near-uniform',   # Dirichlet(10.0)
    'power-law',      # U(0,1)^3 normalised
]


# ---------------------------------------------------------------------------
# Prior generators
# ---------------------------------------------------------------------------

def _make_priors(prior_type: str, n_nodes: int, rng: np.random.Generator) -> dict:
    """Return a normalised {node_id: probability} dict.

    All generators produce strictly positive probabilities; normalisatio
    is always applied so that sum == 1.0.
    """
    ids = list(range(n_nodes))
    if prior_type == 'moderate':
        raw = rng.uniform(0.1, 1.0, size=n_nodes)
    elif prior_type == 'concentrated':
        raw = rng.dirichlet(0.2 * np.ones(n_nodes))
        # dirichlet already sums to 1; skip re-normalisation below
        return {i: float(raw[i]) for i in ids}
    elif prior_type == 'diffuse':
        raw = rng.dirichlet(2.0 * np.ones(n_nodes))
        return {i: float(raw[i]) for i in ids}
    elif prior_type == 'near-uniform':
        raw = rng.dirichlet(10.0 * np.ones(n_nodes))
        return {i: float(raw[i]) for i in ids}
    elif prior_type == 'power-law':
        raw = rng.uniform(0.0, 1.0, size=n_nodes) ** 3
        raw = np.clip(raw, 1e-6, None)
    else:
        raise ValueError(f'Unknown prior_type: {prior_type!r}')

    total = float(raw.sum())
    return {i: float(raw[i]) / total for i in ids}


def _resample_target(node_probs: dict, node_positions: dict, bases: dict,
                     rng: np.random.Generator,
                     min_opt_dist: float = 1.0,
                     max_opt_dist: float | None = None,
                     max_attempts: int = 300) -> tuple[int, float]:
    """Draw target from node_probs, reject if geometric constraints fail.

    Returns (target_node_id, optimal_dist).
    Falls back to the closest-to-constraint node if all samples are
    rejected (prevents infinite loops for near-uniform priors where many
    nodes are far from every base).
    """
    nodes = list(node_probs.keys())
    weights = [node_probs[n] for n in nodes]

    def _opt_dist(node):
        return min(euclidean_distance(bases[r], node_positions[node])
                   for r in range(len(bases)))

    best_fallback, best_fallback_opt = None, None

    for _ in range(max_attempts):
        target = rng.choice(nodes, p=weights / np.array(weights, dtype=float).sum())
        target = int(target)
        opt = _opt_dist(target)
        ok = opt >= min_opt_dist
        if max_opt_dist is not None:
            ok = ok and (opt <= max_opt_dist)
        if ok:
            return target, opt
        # track best fallback (closest to max_opt_dist from below)
        if max_opt_dist is not None and opt <= max_opt_dist:
            if best_fallback_opt is None or abs(opt - min_opt_dist) < abs(best_fallback_opt - min_opt_dist):
                best_fallback, best_fallback_opt = target, opt

    # If we failed to find a valid sample, use fallback or brute-force
    if best_fallback is not None:
        return best_fallback, best_fallback_opt

    # Last resort: pick node with highest prob that satisfies max constraint
    candidates = []
    for n in nodes:
        opt = _opt_dist(n)
        if max_opt_dist is None or opt <= max_opt_dist:
            candidates.append((node_probs[n], opt, n))
    if candidates:
        candidates.sort(reverse=True)
        n = candidates[0][2]
        return n, _opt_dist(n)

    # Absolute last resort: just pick the highest-prob node
    best_n = max(nodes, key=lambda n: node_probs[n])
    return best_n, _opt_dist(best_n)


# ---------------------------------------------------------------------------
# FCR helper
# ---------------------------------------------------------------------------

def _fcr(result: dict) -> float | None:
    finder = result.get('found_by')
    if finder is None:
        return None
    opt = result.get('optimal_dist', 0.0)
    if opt <= 0:
        return None
    return result['robot_dists'][finder] / opt


# ---------------------------------------------------------------------------
# Run one prior type × N_TRIALS
# ---------------------------------------------------------------------------

def run_prior_type(prior_type: str, n_trials: int, seed: int) -> dict[str, list[float]]:
    """Run all models on n_trials instances with the given prior type.

    Returns {model_label: [fcr, ...]} (NaN entries excluded).
    """
    rng = np.random.default_rng(seed)
    fcrs: dict[str, list[float]] = {m: [] for m in MODEL_LABELS}

    for t in range(n_trials):
        trial_seed = seed + t

        # ---- Step 1: generate base geometry (positions + bases)
        # Use generate_instance for positions/bases/optimal_dist with a local seed.
        # We then REPLACE node_probs and resample the target.
        base_inst = generate_instance(N, R, L, seed=trial_seed,
                                      min_opt_dist=1.0, max_opt_dist=E / 2.0)
        node_positions = base_inst['node_positions']
        bases = base_inst['bases']

        # ---- Step 2: replace priors
        node_probs = _make_priors(prior_type, N, rng)

        # ---- Step 3: resample target from new probs (same geometric guards)
        target, opt_dist = _resample_target(
            node_probs, node_positions, bases, rng,
            min_opt_dist=1.0, max_opt_dist=E / 2.0,
        )

        inst = {
            'node_positions': node_positions,
            'node_probs': node_probs,
            'bases': bases,
            'target': target,
            'optimal_dist': opt_dist,
        }

        # ---- Step 4: run all models
        r_m1  = model_1_random_infinite(inst)
        r_m2  = model_2_auction_infinite(inst)
        r_hd  = model_hungarian_single(inst, E)
        r_m3  = model_3_auction_single(inst, E, bid_p_over_d)
        r_m4  = model_4_auction_multi(inst, E, bid_p_over_d)
        r_m4s = model_4_auction_multi(inst, E, bid_p_over_d2)

        for label, res in [('M1', r_m1), ('M2', r_m2), ('H_d', r_hd),
                            ('M3', r_m3), ('M4', r_m4), ('M4*', r_m4s)]:
            v = _fcr(res)
            if v is not None:
                fcrs[label].append(v)

    return fcrs


# ---------------------------------------------------------------------------
# Ordering check
# ---------------------------------------------------------------------------

def check_ordering(means: dict[str, float]) -> dict[tuple, bool]:
    """Return dict {(m_lower, m_higher): holds?} for each ordering pair.

    For the weak pair (M4*, M4) 'holds' means mean(M4*) <= mean(M4).
    For all strict pairs 'holds' means mean(lower) < mean(higher).
    """
    results = {}
    for (lo, hi) in ORDERING_PAIRS:
        if lo == 'M4*' and hi == 'M4':   # weak inequality
            results[(lo, hi)] = means[lo] <= means[hi]
        else:
            results[(lo, hi)] = means[lo] < means[hi]
    return results


# ---------------------------------------------------------------------------
# Plotting
# ---------------------------------------------------------------------------

COLORS_MODEL = {
    'M1':  '#C62828',
    'M2':  '#1565C0',
    'H_d': '#6A1B9A',
    'M3':  '#E65100',
    'M4':  '#558B2F',
    'M4*': '#1B5E20',
}


def plot_grouped_bar(all_means: dict[str, dict[str, float]],
                     all_stds: dict[str, dict[str, float]]) -> plt.Figure:
    """Grouped bar chart: x = prior_type, groups = models.

    Order within each group: M2, M4*, M4, M3, H_d, M1 (best → worst).
    """
    setup_style()
    fig, ax = plt.subplots(figsize=(10, 5))

    n_prior  = len(PRIOR_TYPES)
    n_models = len(MODEL_LABELS)
    bar_w    = 0.13
    group_w  = bar_w * n_models
    x        = np.arange(n_prior)

    for mi, model in enumerate(MODEL_LABELS):
        offsets = x + (mi - n_models / 2 + 0.5) * bar_w
        means   = [all_means[pt][model] for pt in PRIOR_TYPES]
        stds    = [all_stds[pt][model]  for pt in PRIOR_TYPES]
        ax.bar(offsets, means,
               width=bar_w,
               color=COLORS_MODEL[model],
               label=model,
               alpha=0.88,
               edgecolor='white',
               linewidth=0.5,
               yerr=[s / np.sqrt(N_TRIALS) * 1.96 for s in stds],  # 95% CI
               capsize=2,
               error_kw={'elinewidth': 0.8})

    ax.set_xticks(x)
    ax.set_xticklabels(
        ['Concentrated\n(Dir 0.2)', 'Moderate\n(Uniform)', 'Diffuse\n(Dir 2.0)',
         'Near-Uniform\n(Dir 10.0)', 'Power-Law\n(U^3)'],
        fontsize=9,
    )
    ax.set_ylabel('Mean Finder Competitive Ratio (FCR)', fontsize=11)
    ax.set_title('Prior Sensitivity: FCR by Model and Prior Shape\n'
                 f'({N_TRIALS} paired trials, n={N}, R={R}, E={E})', fontsize=11)
    ax.legend(title='Model', bbox_to_anchor=(1.01, 1), loc='upper left',
              fontsize=9, title_fontsize=9)
    ax.set_ylim(bottom=0)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    fig.tight_layout()
    return fig


# ---------------------------------------------------------------------------
# LaTeX table
# ---------------------------------------------------------------------------

def print_latex_table(all_means, all_stds, ordering_results):
    """Print a copy-pasteable LaTeX table."""
    col_header = ' & '.join(f'\\textbf{{{m}}}' for m in MODEL_LABELS)
    print()
    print('% ===== LaTeX table for exp7_prior_sensitivity =====')
    print('\\begin{table}[ht]')
    print('\\centering')
    print('\\caption{Mean Finder Competitive Ratio by Prior Shape '
          f'({N_TRIALS} trials, $n={N}$, $R={R}$, $E={E}$). '
          'Ordering checks: \\checkmark = M2<M4*$\\le$M4<M3<H$_d$<M1 holds; '
          '\\ding{55} = at least one pair violated.}')
    print('\\label{tab:prior_sensitivity}')
    print('\\small')
    print('\\begin{tabular}{l' + 'r' * len(MODEL_LABELS) + 'c}')
    print('\\toprule')
    print(f'Prior Shape & {col_header} & Ordering \\\\ \\midrule')

    nice_names = {
        'concentrated': 'Concentrated (Dir~0.2)',
        'moderate':     'Moderate (Uniform)',
        'diffuse':      'Diffuse (Dir~2.0)',
        'near-uniform': 'Near-Uniform (Dir~10.0)',
        'power-law':    'Power-Law ($U^3$)',
    }

    for pt in PRIOR_TYPES:
        vals = ' & '.join(f'{all_means[pt][m]:.2f}' for m in MODEL_LABELS)
        order_ok = all(ordering_results[pt].values())
        order_sym = '\\checkmark' if order_ok else '\\ding{55}'
        print(f'{nice_names[pt]} & {vals} & {order_sym} \\\\')

    print('\\bottomrule')
    print('\\end{tabular}')
    print('\\end{table}')
    print()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run():
    enable_utf8_stdout()
    print('=' * 72)
    print('  Experiment 7: Prior Sensitivity Analysis')
    print(f'  {N_TRIALS} paired trials  n={N}  R={R}  E={E}  L={L}')
    print(f'  Prior types: {", ".join(PRIOR_TYPES)}')
    print('=' * 72)

    all_fcrs: dict[str, dict[str, list[float]]] = {}
    all_means: dict[str, dict[str, float]] = {}
    all_stds:  dict[str, dict[str, float]] = {}
    all_order: dict[str, dict[tuple, bool]] = {}

    for pt in PRIOR_TYPES:
        print(f'\n  --- Prior type: {pt} ---')
        pt_seed = SEED + PRIOR_TYPES.index(pt) * 10_000
        fcrs = run_prior_type(pt, N_TRIALS, pt_seed)
        all_fcrs[pt] = fcrs

        means = {m: float(np.mean(fcrs[m])) if fcrs[m] else float('nan')
                 for m in MODEL_LABELS}
        stds  = {m: float(np.std(fcrs[m], ddof=1)) if len(fcrs[m]) > 1 else 0.0
                 for m in MODEL_LABELS}
        all_means[pt] = means
        all_stds[pt]  = stds
        all_order[pt] = check_ordering(means)

        print(f'  {"Model":<8} {"mean":>7} {"std":>7} {"n":>5}')
        print('  ' + '-' * 32)
        for m in MODEL_LABELS:
            print(f'  {m:<8} {means[m]:>7.3f} {stds[m]:>7.3f} {len(fcrs[m]):>5}')

        print()
        print('  Ordering checks (M2 < M4* <= M4 < M3 < H_d < M1):')
        for (lo, hi), holds in all_order[pt].items():
            sym = 'OK  ' if holds else 'FAIL'
            print(f'    {lo} < {hi}: [{sym}]  ({means[lo]:.3f} vs {means[hi]:.3f})')
        order_ok = all(all_order[pt].values())
        print(f'  >> Full ordering holds: {"YES" if order_ok else "NO"}')

    # ------------------------------------------------------------------
    # Cross-prior analysis
    # ------------------------------------------------------------------
    print()
    print('=' * 72)
    print('  CROSS-PRIOR SUMMARY')
    print('=' * 72)

    # Header row
    col_w = 10
    header = f'  {"Prior":<16}' + ''.join(f'{m:>{col_w}}' for m in MODEL_LABELS) + '  Ordering'
    print(header)
    print('  ' + '-' * (16 + col_w * len(MODEL_LABELS) + 10))

    for pt in PRIOR_TYPES:
        row = f'  {pt:<16}'
        for m in MODEL_LABELS:
            row += f'{all_means[pt][m]:>{col_w}.3f}'
        order_ok = all(all_order[pt].values())
        row += f'  {"HOLDS" if order_ok else "VIOLATED"}'
        print(row)

    # ------------------------------------------------------------------
    # M4* vs M4 advantage by prior type
    # ------------------------------------------------------------------
    print()
    print('  M4* vs M4 advantage (higher = M4* more beneficial):')
    for pt in PRIOR_TYPES:
        m4  = all_means[pt]['M4']
        m4s = all_means[pt]['M4*']
        if m4 > 0:
            pct = (m4 - m4s) / m4 * 100.0
        else:
            pct = 0.0
        print(f'    {pt:<16}  M4={m4:.3f}  M4*={m4s:.3f}  '
              f'advantage={pct:+.2f}%')

    # ------------------------------------------------------------------
    # M3 vs H_d advantage by prior type
    # ------------------------------------------------------------------
    print()
    print('  M3 vs H_d advantage (prob-aware bidding benefit):')
    for pt in PRIOR_TYPES:
        hd  = all_means[pt]['H_d']
        m3  = all_means[pt]['M3']
        if hd > 0:
            pct = (hd - m3) / hd * 100.0
        else:
            pct = 0.0
        print(f'    {pt:<16}  H_d={hd:.3f}  M3={m3:.3f}  '
              f'M3 advantage={pct:+.2f}%')

    # ------------------------------------------------------------------
    # LaTeX table
    # ------------------------------------------------------------------
    print_latex_table(all_means, all_stds, all_order)

    # ------------------------------------------------------------------
    # Save CSV
    # ------------------------------------------------------------------
    csv_rows = []
    for pt in PRIOR_TYPES:
        for m in MODEL_LABELS:
            for v in all_fcrs[pt][m]:
                csv_rows.append([pt, m, f'{v:.6f}'])
    write_csv(
        os.path.join(DATA_DIR, 'exp7_prior_sensitivity.csv'),
        csv_rows,
        ['prior_type', 'model', 'fcr'],
    )

    # Summary CSV
    summary_rows = []
    for pt in PRIOR_TYPES:
        for m in MODEL_LABELS:
            summary_rows.append([
                pt, m,
                f'{all_means[pt][m]:.4f}',
                f'{all_stds[pt][m]:.4f}',
                len(all_fcrs[pt][m]),
            ])
    write_csv(
        os.path.join(DATA_DIR, 'exp7_prior_sensitivity_summary.csv'),
        summary_rows,
        ['prior_type', 'model', 'mean_fcr', 'std_fcr', 'n'],
    )

    # ------------------------------------------------------------------
    # Figure
    # ------------------------------------------------------------------
    fig = plot_grouped_bar(all_means, all_stds)
    save_fig(fig, 'fig_prior_sensitivity.png')
    print()
    print('Done.')


if __name__ == '__main__':
    run()
