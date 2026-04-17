"""Shared helpers for SearchFCR experiments."""
from __future__ import annotations

import os
import sys
import csv

import numpy as np
import matplotlib.pyplot as plt

# Add repo root to path so we can import main.py no matter where we're run from.
_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

# Output locations (figures go next to the other thesis figures so they
# compile in without path-juggling).
FIG_DIR = os.path.join(_ROOT, 'thesis', 'figures')
DATA_DIR = os.path.join(_HERE, 'data')
os.makedirs(FIG_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)

# Default experiment parameters — match thesis Table II baseline.
DEFAULT_N = 30
DEFAULT_R = 3
DEFAULT_E = 14.0
DEFAULT_L = 10.0
DEFAULT_TRIALS = 500
DEFAULT_SEED = 42


def enable_utf8_stdout():
    """Windows cp1252 cannot emit the infinity symbol used in model names."""
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except AttributeError:
        pass


def setup_style():
    """Matplotlib style matched to main.py's thesis figures."""
    plt.rcParams.update({
        'font.family': 'serif',
        'font.size': 11,
        'axes.labelsize': 12,
        'axes.titlesize': 12,
        'xtick.labelsize': 10,
        'ytick.labelsize': 10,
        'legend.fontsize': 9,
        'legend.framealpha': 0.92,
        'lines.linewidth': 2.0,
        'lines.markersize': 6,
        'figure.dpi': 300,
        'savefig.dpi': 300,
        'savefig.bbox': 'tight',
        'savefig.pad_inches': 0.05,
        'axes.grid': True,
        'grid.alpha': 0.25,
        'grid.linewidth': 0.5,
    })


def write_csv(path: str, rows, header):
    """Write a CSV for downstream plotting / sanity-checking."""
    with open(path, 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)
    print(f'  data:   {path}')


def save_fig(fig, name):
    """Save a figure into the thesis/figures/ directory."""
    path = os.path.join(FIG_DIR, name)
    fig.savefig(path, dpi=300, bbox_inches='tight')
    print(f'  figure: {path}')
    plt.close(fig)


def corrupt_priors(instance, sigma, rng):
    """Return a shallow-modified copy of `instance` whose node_probs are
    corrupted by Gaussian noise with std `sigma` on the raw scores, then
    renormalised. The target field is *not* changed: the target was
    sampled from the true priors during generate_instance(). Algorithms
    that read `node_probs` will therefore bid based on corrupted beliefs
    about a target placed under the true distribution.

    sigma = 0.0 returns the instance unchanged (a sanity-check line).
    """
    if sigma <= 0.0:
        return {**instance, 'node_probs': dict(instance['node_probs'])}

    true_probs = instance['node_probs']
    noisy = {}
    for i, p in true_probs.items():
        # Noise multiplier: (1 + eps). Clamp at a small positive so we
        # never produce negative probabilities (negatives after
        # renormalisation would flip the sign of bids).
        eps = rng.normal(0.0, sigma)
        noisy[i] = max(p * (1.0 + eps), 1e-6)
    total = sum(noisy.values())
    noisy = {i: v / total for i, v in noisy.items()}

    return {**instance, 'node_probs': noisy}
