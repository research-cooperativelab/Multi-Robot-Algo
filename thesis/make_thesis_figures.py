"""
Thesis-specific figure generator.

Produces four figures for readers without a multi-robot-systems background:
  fig_fcr_explanation.png   — what the finder competitive ratio means.
  fig_model_tree.png        — conceptual flowchart of the four models.
  fig_m4star_walkthrough.png — 4-panel M4* iteration (bid, chain, execute, update).
  fig_m1_vs_m4star.png      — M1 path spaghetti vs. M4* compact tours.

Each figure saves to ../thesis/figures/ (i.e., thesis/figures/).

Run from the worktree root or from thesis/:
    python thesis/make_thesis_figures.py
"""
from __future__ import annotations

import os
import sys

# Ensure we can import main.py from the worktree root
_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
sys.path.insert(0, _ROOT)

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Circle
from matplotlib.lines import Line2D

from main import (
    generate_instance,
    model_1_random_infinite,
    model_4_auction_multi,
    bid_p_over_d2,
    setup_style,
)

FIG_DIR = os.path.join(_HERE, 'figures')
os.makedirs(FIG_DIR, exist_ok=True)


# ──────────────────────────────────────────────────────────────────────────────
# Figure 1: FCR explanation
# ──────────────────────────────────────────────────────────────────────────────
def fig_fcr_explanation():
    """A single worked example explaining the Finder Competitive Ratio.

    We draw a base, a target, and a simple 3-site search path. The optimal
    (omniscient) distance is the straight line from base to target. The
    algorithm's finder distance is the actual polyline. FCR = actual / optimal.
    """
    setup_style()
    fig, ax = plt.subplots(figsize=(7.5, 4.5))

    # Positions
    base = np.array([1.0, 2.0])
    sites = {
        'A': np.array([3.5, 4.2]),   # visited first (wrong)
        'B': np.array([5.5, 1.2]),   # visited second (wrong)
        'T': np.array([7.5, 3.5]),   # TARGET, visited third
    }

    # Draw base
    ax.plot(*base, marker='s', markersize=16, color='#1565C0',
            markeredgecolor='black', markeredgewidth=1.2, zorder=5)
    ax.annotate('Base', base + np.array([-0.05, -0.55]), fontsize=12,
                ha='center', color='#1565C0', weight='bold')

    # Draw non-target sites
    for lbl in ('A', 'B'):
        p = sites[lbl]
        ax.plot(*p, marker='o', markersize=14, color='#CCCCCC',
                markeredgecolor='#555555', markeredgewidth=1.2, zorder=4)
        ax.annotate(lbl, p + np.array([0.0, 0.35]), fontsize=11,
                    ha='center', color='#333333')

    # Draw target
    p = sites['T']
    ax.plot(*p, marker='*', markersize=26, color='#2E7D32',
            markeredgecolor='black', markeredgewidth=1.2, zorder=5)
    ax.annotate('Target', p + np.array([0.05, 0.45]), fontsize=12,
                ha='center', color='#2E7D32', weight='bold')

    # Optimal path (dashed green): base → target
    ax.annotate('', xy=sites['T'], xytext=base,
                arrowprops=dict(arrowstyle='->', linestyle='--',
                                color='#2E7D32', lw=2.5))
    mid_opt = (base + sites['T']) / 2
    d_opt = np.linalg.norm(sites['T'] - base)
    ax.annotate(f'$d_{{opt}}$ = {d_opt:.2f}  (omniscient)',
                mid_opt + np.array([0.0, 0.45]), fontsize=11,
                color='#2E7D32', ha='center', weight='bold')

    # Actual finder path (solid red): base → A → B → T
    path = [base, sites['A'], sites['B'], sites['T']]
    path_xs = [p[0] for p in path]
    path_ys = [p[1] for p in path]
    ax.plot(path_xs, path_ys, color='#C62828', lw=2.8, zorder=3)
    # Arrowhead on the last leg
    ax.annotate('', xy=sites['T'], xytext=sites['B'],
                arrowprops=dict(arrowstyle='->', color='#C62828', lw=2.8))

    d_f = sum(np.linalg.norm(path[i+1] - path[i]) for i in range(3))
    fcr = d_f / d_opt
    ax.annotate(f'$D_f$ = {d_f:.2f}  (robot\'s actual travel)',
                np.array([4.5, 5.0]), fontsize=11, color='#C62828',
                ha='center', weight='bold')

    # FCR formula box, top right
    eq = (r'$\mathrm{FCR} = \dfrac{D_f}{d_{opt}} = '
          rf'\dfrac{{{d_f:.2f}}}{{{d_opt:.2f}}} = {fcr:.2f}$')
    ax.text(9.3, 5.0, eq, fontsize=13, ha='right', va='top',
            bbox=dict(boxstyle='round,pad=0.5', facecolor='#FFF8E1',
                      edgecolor='#F9A825', lw=1.4))
    ax.text(9.3, 3.9,
            'Read as: "the robot traveled\n'
            f'{fcr:.2f}$\\times$ as far as an all-knowing agent would."',
            fontsize=10, ha='right', va='top', style='italic',
            color='#555555')

    ax.set_xlim(0, 9.5)
    ax.set_ylim(0, 5.5)
    ax.set_aspect('equal')
    ax.grid(True, alpha=0.2)
    ax.set_xlabel('x')
    ax.set_ylabel('y')
    ax.set_title('Finder Competitive Ratio: worked example',
                 fontsize=12, weight='bold')

    # Legend
    legend_elems = [
        Line2D([0], [0], marker='s', color='w', markerfacecolor='#1565C0',
               markersize=10, label='Base'),
        Line2D([0], [0], marker='o', color='w', markerfacecolor='#CCCCCC',
               markeredgecolor='#555555', markersize=10,
               label='Candidate site'),
        Line2D([0], [0], marker='*', color='w', markerfacecolor='#2E7D32',
               markersize=14, label='Target'),
        Line2D([0], [0], color='#2E7D32', ls='--', lw=2.5,
               label='Optimal (omniscient)'),
        Line2D([0], [0], color='#C62828', lw=2.8,
               label='Actual finder path'),
    ]
    ax.legend(handles=legend_elems, loc='lower right', fontsize=9)

    out = os.path.join(FIG_DIR, 'fig_fcr_explanation.png')
    fig.savefig(out, dpi=300, bbox_inches='tight')
    plt.close(fig)
    print(f'  wrote {out}')


# ──────────────────────────────────────────────────────────────────────────────
# Figure 2: Conceptual model tree
# ──────────────────────────────────────────────────────────────────────────────
def fig_model_tree():
    """Flowchart: four models arranged by what each adds (comm, energy, chain)."""
    setup_style()
    fig, ax = plt.subplots(figsize=(9.0, 6.5))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 7.5)
    ax.axis('off')

    def box(x, y, w, h, title, body, color):
        rect = FancyBboxPatch((x - w/2, y - h/2), w, h,
                              boxstyle='round,pad=0.08',
                              linewidth=1.4, edgecolor='#333',
                              facecolor=color)
        ax.add_patch(rect)
        # Title on its own row near the top, body centered below it
        ax.text(x, y + h/2 - 0.30, title, ha='center', va='center',
                fontsize=11, weight='bold')
        ax.text(x, y - h/2 + 0.45, body, ha='center', va='center',
                fontsize=9, color='#222')

    def arrow(x1, y1, x2, y2, label=None):
        ax.annotate('', xy=(x2, y2), xytext=(x1, y1),
                    arrowprops=dict(arrowstyle='->', lw=1.6,
                                    color='#444'))
        if label:
            mx, my = (x1 + x2) / 2, (y1 + y2) / 2
            ax.text(mx, my, label, fontsize=10, ha='center', va='center',
                    bbox=dict(boxstyle='round,pad=0.2', facecolor='#FFF8E1',
                              edgecolor='#F9A825', lw=0.8),
                    color='#5D4037', style='italic')

    # Layout (4 levels, each adds a capability)
    w, h = 3.4, 1.5

    box(2.0, 6.3, w, h, 'M1: Random',
        'Each robot picks\nindependently.\nNo communication.',
        '#FFCDD2')

    box(8.0, 6.3, w, h, 'M2: Unconstrained Auction',
        'Robots bid and\ncoordinate.\nUnlimited battery.',
        '#BBDEFB')

    box(8.0, 3.5, w, h, 'M3: Single-Sortie',
        'Finite battery. One site\nper trip, then return.',
        '#FFE0B2')

    box(8.0, 0.8, w, h, 'M4 / M4*: Multi-Sortie',
        'Chain several sites per trip.\nM4* uses $p/d^2$ bids.',
        '#C8E6C9')

    # Arrows
    arrow(3.7, 6.3, 6.3, 6.3, label='+ communication\n& auction')
    arrow(8.0, 5.55, 8.0, 4.25, label='+ finite energy $E$')
    arrow(8.0, 2.75, 8.0, 1.55, label='+ chain extension')

    # "Research focus" callout
    ax.annotate('',
                xy=(6.3, 0.8), xytext=(4.0, 2.0),
                arrowprops=dict(arrowstyle='->', color='#2E7D32',
                                lw=2.0, ls='--'))
    ax.text(4.0, 2.3, 'Primary contribution:\nM4* with $p/d^2$ bid',
            fontsize=10, ha='center', va='bottom',
            color='#2E7D32', weight='bold', style='italic')

    # Title
    ax.text(5.0, 7.3, 'Four models, ordered by what each adds',
            ha='center', va='center', fontsize=12, weight='bold')

    out = os.path.join(FIG_DIR, 'fig_model_tree.png')
    fig.savefig(out, dpi=300, bbox_inches='tight')
    plt.close(fig)
    print(f'  wrote {out}')


# ──────────────────────────────────────────────────────────────────────────────
# Figures 3 and 4 share a helper for drawing an instance
# ──────────────────────────────────────────────────────────────────────────────
ROBOT_COLORS = ['#C62828', '#1565C0', '#2E7D32', '#6A1B9A', '#EF6C00']


def _draw_instance(ax, inst, show_probs=True, highlight_target=True,
                   visited=None, L=10.0):
    """Draw the base positions, candidate sites (size ∝ probability), and
    optionally mark visited sites. Instance fields are dicts."""
    visited = visited or set()

    np_positions = inst['node_positions']
    probs = dict(inst['node_probs'])
    bases = inst['bases']  # dict {r: (x, y)}
    p_max = max(probs.values()) if probs else 1.0

    # Sites
    for i, pos in np_positions.items():
        p = probs.get(i, 0)
        size = 40 + 220 * (p / p_max) if p_max > 0 else 40
        if i in visited:
            color = '#BDBDBD'
            edge = '#666666'
        elif show_probs:
            color = plt.cm.YlOrRd(0.25 + 0.5 * (p / p_max)) if p_max > 0 else '#E0E0E0'
            edge = '#8B4513'
        else:
            color = '#E0E0E0'
            edge = '#555'
        ax.scatter([pos[0]], [pos[1]], s=size, c=[color], edgecolors=edge,
                   linewidth=0.9, zorder=3)
        ax.text(pos[0], pos[1] + 0.25, str(i), fontsize=8,
                ha='center', color='#333')

    # Bases
    base_items = bases.items() if isinstance(bases, dict) else enumerate(bases)
    for r, base in base_items:
        color = ROBOT_COLORS[r % len(ROBOT_COLORS)]
        ax.scatter([base[0]], [base[1]], marker='s', s=180, c=color,
                   edgecolors='black', linewidth=1.4, zorder=5)
        ax.text(base[0], base[1] - 0.5, f'R{r}', fontsize=9,
                ha='center', color=color, weight='bold')

    # Target
    target = inst['target']
    if highlight_target and target in np_positions:
        tpos = np_positions[target]
        ax.scatter([tpos[0]], [tpos[1]], marker='*', s=280, c='#2E7D32',
                   edgecolors='black', linewidth=1.2, zorder=6)

    ax.set_xlim(-0.5, L + 0.5)
    ax.set_ylim(-0.5, L + 0.5)
    ax.set_aspect('equal')
    ax.grid(True, alpha=0.2)


def _draw_tour(ax, base, np_positions, tour, color, lw=1.8, style='-'):
    """Draw a robot's tour as a polyline base -> site -> site -> ... -> base."""
    if not tour:
        return
    # tour is either [node_id, ...] or [(node_id, dist), ...]
    node_ids = [t[0] if isinstance(t, (tuple, list)) else t for t in tour]
    xs = [base[0]] + [np_positions[n][0] for n in node_ids] + [base[0]]
    ys = [base[1]] + [np_positions[n][1] for n in node_ids] + [base[1]]
    ax.plot(xs, ys, color=color, lw=lw, ls=style, alpha=0.85, zorder=4)


# ──────────────────────────────────────────────────────────────────────────────
# Figure 3: M4* four-panel walkthrough
# ──────────────────────────────────────────────────────────────────────────────
def fig_m4star_walkthrough(seed=11, n=10, R=3, E=14.0, L=10.0):
    """Four panels showing one M4* iteration step-by-step.

    Panel A: initial instance (priors shown by size/color).
    Panel B: SSI auction assigns anchor sites with p/d² bids.
    Panel C: greedy chain extension fills remaining energy budget.
    Panel D: after round — Bayesian update concentrates probability.
    """
    setup_style()

    # Generate a small, clean instance
    inst = generate_instance(n, R, L, seed=seed)
    # Run M4* to completion but we'll hand-reconstruct the first iteration
    result = model_4_auction_multi(inst, E, bid_func=bid_p_over_d2)
    round_data = result['round_data']
    if not round_data:
        print('  no rounds produced; skipping m4star walkthrough')
        return

    # Reconstruct round 1 tours by re-running the per-round logic.
    # We pick the simplest approach: run model_4 once with a single iteration
    # snapshot is approximated by showing the tours as recorded in round_data.
    # The main `model_4_auction_multi` records detailed per-round sites_per_robot;
    # we use that to draw panel C tours.

    fig, axes = plt.subplots(1, 4, figsize=(16, 4.4))
    panel_titles = [
        '(A) Start: priors shown by size',
        '(B) Auction picks anchor sites',
        '(C) Chain extends to fill energy',
        '(D) Bayesian update after round 1',
    ]

    # Panel A: initial instance
    _draw_instance(axes[0], inst, show_probs=True, highlight_target=True, L=L)

    # Panel B: anchor sites (first node per robot's tour in round 1)
    first_round = round_data[0]
    tour_per_robot = first_round.get('tour_per_robot', {})
    _draw_instance(axes[1], inst, show_probs=True,
                   highlight_target=True, L=L)
    for r, chain in tour_per_robot.items():
        if not chain:
            continue
        base = inst['bases'][r]
        anchor = chain[0]
        color = ROBOT_COLORS[r % len(ROBOT_COLORS)]
        axes[1].annotate('', xy=inst['node_positions'][anchor], xytext=base,
                         arrowprops=dict(arrowstyle='->', lw=2.2,
                                         color=color))

    # Panel C: full chain per robot, drawn as base→...→base loop
    _draw_instance(axes[2], inst, show_probs=True,
                   highlight_target=True, L=L)
    for r, chain in tour_per_robot.items():
        if not chain:
            continue
        color = ROBOT_COLORS[r % len(ROBOT_COLORS)]
        _draw_tour(axes[2], inst['bases'][r], inst['node_positions'],
                   chain, color, lw=2.0)

    # Panel D: show posterior after round 1
    visited_round1 = set()
    for r, chain in tour_per_robot.items():
        for site in chain:
            visited_round1.add(site)
    # Updated priors
    from main import bayesian_update
    updated_probs = bayesian_update(dict(inst['node_probs']), visited_round1)
    updated_inst = {
        'node_positions': dict(inst['node_positions']),
        'node_probs': updated_probs,
        'bases': dict(inst['bases']),
        'target': inst['target'],
    }
    _draw_instance(axes[3], updated_inst, show_probs=True,
                   highlight_target=True, visited=visited_round1, L=L)

    # Titles
    for ax, title in zip(axes, panel_titles):
        ax.set_title(title, fontsize=11, weight='bold')
        ax.set_xticks([])
        ax.set_yticks([])

    fig.suptitle(
        f'Model 4* on an $n{{=}}{n}$, $R{{=}}{R}$, $E{{=}}{E}$ instance '
        f'(seed {seed})',
        fontsize=12, weight='bold', y=1.02)

    out = os.path.join(FIG_DIR, 'fig_m4star_walkthrough.png')
    fig.savefig(out, dpi=300, bbox_inches='tight')
    plt.close(fig)
    print(f'  wrote {out}')


# ──────────────────────────────────────────────────────────────────────────────
# Figure 4: M1 vs M4* same-instance comparison
# ──────────────────────────────────────────────────────────────────────────────
def fig_m1_vs_m4star(seed=7, n=30, R=3, E=14.0, L=10.0):
    """Two side-by-side panels: M1 spaghetti vs. M4* compact tours, same seed."""
    setup_style()

    inst = generate_instance(n, R, L, seed=seed)
    m1 = model_1_random_infinite(inst)
    m4s = model_4_auction_multi(inst, E, bid_func=bid_p_over_d2)

    fig, axes = plt.subplots(1, 2, figsize=(14, 6.2))

    # M1 panel: each M1 round-trip becomes a short out-and-back line
    _draw_instance(axes[0], inst, show_probs=True, highlight_target=True, L=L)
    for rd in m1.get('round_data', []):
        tpr = rd.get('tour_per_robot', {})
        for r, chain in tpr.items():
            if not chain:
                continue
            color = ROBOT_COLORS[r % len(ROBOT_COLORS)]
            base = inst['bases'][r]
            # M1 always has a single site per round-trip
            node = chain[0]
            np_ = inst['node_positions'][node]
            axes[0].plot([base[0], np_[0]], [base[1], np_[1]],
                         color=color, lw=1.2, alpha=0.45, zorder=3)

    # M4* panel: one tour per robot per round, drawn heavier
    _draw_instance(axes[1], inst, show_probs=True, highlight_target=True, L=L)
    for rd in m4s.get('round_data', []):
        tpr = rd.get('tour_per_robot', {})
        for r, chain in tpr.items():
            if not chain:
                continue
            color = ROBOT_COLORS[r % len(ROBOT_COLORS)]
            _draw_tour(axes[1], inst['bases'][r], inst['node_positions'],
                       chain, color, lw=1.8)

    # Compute FCRs
    def fcr_of(result):
        if not result.get('optimal_dist'):
            return None
        finder = result.get('found_by')
        if finder is None:
            return None
        return result['robot_dists'][finder] / result['optimal_dist']

    fcr_m1 = fcr_of(m1)
    fcr_m4s = fcr_of(m4s)
    axes[0].set_title(
        f'M1 Random: FCR = {fcr_m1:.2f}' if fcr_m1 is not None
        else 'M1 Random (target not found)',
        fontsize=12, weight='bold')
    axes[1].set_title(
        f'M4* (p/d$^2$): FCR = {fcr_m4s:.2f}' if fcr_m4s is not None
        else 'M4* (target not found)',
        fontsize=12, weight='bold')

    for ax in axes:
        ax.set_xticks([])
        ax.set_yticks([])

    fig.suptitle(
        f'Same instance (seed {seed}, n={n}, R={R}, E={E}), two algorithms',
        fontsize=12, weight='bold', y=1.01)

    out = os.path.join(FIG_DIR, 'fig_m1_vs_m4star.png')
    fig.savefig(out, dpi=300, bbox_inches='tight')
    plt.close(fig)
    print(f'  wrote {out}')


if __name__ == '__main__':
    # Force UTF-8 on Windows console (same as main.py fix)
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except AttributeError:
        pass

    print('Generating thesis-specific figures...')
    fig_fcr_explanation()
    fig_model_tree()
    fig_m4star_walkthrough()
    fig_m1_vs_m4star()
    print('Done.')
