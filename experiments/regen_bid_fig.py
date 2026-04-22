"""Regenerate fig_bid_variants.png at 5,000 trials.

Run from the repo root:
    python experiments/regen_bid_fig.py
"""
from __future__ import annotations

import os
import sys

# Ensure the repo root is on the path so `main` is importable.
_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import matplotlib
matplotlib.use('Agg')  # non-interactive backend — safe on all platforms

from main import run_bid_variants, plot_bid_variants, setup_style

# Output path — paper uses \graphicspath{{../figures/}}
SAVE_PATH = os.path.join(_ROOT, 'figures', 'fig_bid_variants.png')

if __name__ == '__main__':
    # Apply the same matplotlib style as main.py's figures.
    setup_style()

    print('Running bid-variant simulation: n=30, R=3, L=10, E=14, trials=5000, seed=42')
    bid_results = run_bid_variants(n=30, R=3, L=10, E=14, n_trials=5000, seed=42)

    # Print summary of mean FCR per variant (sorted best → worst).
    import numpy as np
    sorted_variants = sorted(bid_results.items(),
                             key=lambda kv: np.mean(kv[1]) if kv[1] else 999)
    print('\nBid variant results (sorted by mean FCR, best first):')
    for name, fcrs in sorted_variants:
        if fcrs:
            print(f'  {name:20s}  mean={np.mean(fcrs):.4f}  std={np.std(fcrs):.4f}  n={len(fcrs)}')
        else:
            print(f'  {name:20s}  no valid trials')

    plot_bid_variants(bid_results, SAVE_PATH)

    size = os.path.getsize(SAVE_PATH)
    print(f'\nDone — figures/fig_bid_variants.png written (5000 trials)')
    print(f'File size: {size:,} bytes  ({SAVE_PATH})')
