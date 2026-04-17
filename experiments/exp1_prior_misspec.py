"""Experiment 1 — Prior Misspecification.

Hypothesis: The p/d^2 bid (Model 4*) is MORE ROBUST to noisy priors than
the classical p/d bid (Model 4), because the quadratic distance penalty
dominates the probability signal when the probability signal is noisy.

Protocol:
  * Generate 500 instances at the default config (n=30, R=3, E=14, L=10).
    The target is sampled from the TRUE priors during generation.
  * For each sigma in {0.0, 0.1, 0.2, 0.3, 0.5, 0.8, 1.0}, corrupt the
    node_probs that algorithms observe by a Gaussian multiplicative noise
    with std sigma on raw scores (see _common.corrupt_priors).
  * Run Model 4 (p/d bid) and Model 4* (p/d^2 bid) on each noisy instance.
  * Record mean and median FCR for both models at each noise level.

Outputs:
  - thesis/figures/fig_prior_misspec.png (two-line plot: M4 vs M4*)
  - experiments/data/exp1_prior_misspec.csv (sigma, model, mean, median)

Usage: python experiments/exp1_prior_misspec.py
"""
from __future__ import annotations

import os
import random

import numpy as np
import matplotlib.pyplot as plt

from _common import (
    DEFAULT_E, DEFAULT_L, DEFAULT_N, DEFAULT_R, DEFAULT_SEED, DEFAULT_TRIALS,
    DATA_DIR, corrupt_priors, enable_utf8_stdout, save_fig, setup_style,
    write_csv,
)

# pylint: disable=wrong-import-position
import main as sar
from main import (
    bid_p_over_d, bid_p_over_d2, generate_instance,
    model_4_auction_multi,
)


SIGMAS = [0.0, 0.1, 0.2, 0.3, 0.5, 0.8, 1.0]


def run():
    enable_utf8_stdout()
    setup_style()
    print('Experiment 1: Prior Misspecification')
    print(f'  {DEFAULT_TRIALS} trials, n={DEFAULT_N}, R={DEFAULT_R}, '
          f'E={DEFAULT_E}, L={DEFAULT_L}')
    print(f'  sigmas: {SIGMAS}')

    rng = np.random.default_rng(DEFAULT_SEED)
    rows = []
    summary = {'M4 (p/d)': {s: [] for s in SIGMAS},
               'M4* (p/d^2)': {s: [] for s in SIGMAS}}

    # Pre-generate the trial instances once so both bids see identical instances.
    trials = []
    for t in range(DEFAULT_TRIALS):
        trial_seed = DEFAULT_SEED + t
        inst = generate_instance(DEFAULT_N, DEFAULT_R, DEFAULT_L,
                                 seed=trial_seed,
                                 min_opt_dist=1.0,
                                 max_opt_dist=DEFAULT_E / 2.0)
        trials.append(inst)

    for sigma in SIGMAS:
        # Separate RNG for the noise so results depend only on (sigma, trial).
        noise_rng = np.random.default_rng(DEFAULT_SEED + 97 * int(sigma * 100))
        for t, inst in enumerate(trials):
            noisy_inst = corrupt_priors(inst, sigma, noise_rng)

            # Determinism of the model's own random choices (e.g. ties)
            random.seed(DEFAULT_SEED + t)
            np.random.seed(DEFAULT_SEED + t)
            r_m4 = model_4_auction_multi(noisy_inst, DEFAULT_E,
                                         bid_func=bid_p_over_d)
            random.seed(DEFAULT_SEED + t)
            np.random.seed(DEFAULT_SEED + t)
            r_m4s = model_4_auction_multi(noisy_inst, DEFAULT_E,
                                          bid_func=bid_p_over_d2)

            for label, res in (('M4 (p/d)', r_m4), ('M4* (p/d^2)', r_m4s)):
                if res['found_by'] is not None:
                    fcr = res['robot_dists'][res['found_by']] / \
                          res['optimal_dist']
                    summary[label][sigma].append(fcr)

        m4_mean = float(np.mean(summary['M4 (p/d)'][sigma]))
        m4_med = float(np.median(summary['M4 (p/d)'][sigma]))
        m4s_mean = float(np.mean(summary['M4* (p/d^2)'][sigma]))
        m4s_med = float(np.median(summary['M4* (p/d^2)'][sigma]))
        print(f'  sigma={sigma:.1f}  '
              f'M4 mean={m4_mean:5.2f} med={m4_med:5.2f}  |  '
              f'M4* mean={m4s_mean:5.2f} med={m4s_med:5.2f}')
        rows.append((sigma, 'M4 (p/d)', m4_mean, m4_med,
                     len(summary['M4 (p/d)'][sigma])))
        rows.append((sigma, 'M4* (p/d^2)', m4s_mean, m4s_med,
                     len(summary['M4* (p/d^2)'][sigma])))

    # Plot
    fig, ax = plt.subplots(figsize=(7.2, 4.5))

    m4_means = [np.mean(summary['M4 (p/d)'][s]) for s in SIGMAS]
    m4s_means = [np.mean(summary['M4* (p/d^2)'][s]) for s in SIGMAS]
    m4_meds = [np.median(summary['M4 (p/d)'][s]) for s in SIGMAS]
    m4s_meds = [np.median(summary['M4* (p/d^2)'][s]) for s in SIGMAS]

    ax.plot(SIGMAS, m4_means, 'o-', color='#6A9A47',
            label='M4 ($p/d$)', lw=2.4, markersize=8)
    ax.plot(SIGMAS, m4s_means, 's-', color='#2E7D32',
            label='M4* ($p/d^2$)', lw=2.4, markersize=8)
    ax.plot(SIGMAS, m4_meds, 'o--', color='#6A9A47', alpha=0.45,
            label='M4 median', lw=1.5, markersize=6)
    ax.plot(SIGMAS, m4s_meds, 's--', color='#2E7D32', alpha=0.45,
            label='M4* median', lw=1.5, markersize=6)

    # Reference line at sigma=0
    ax.axvline(0.0, color='#999', ls=':', lw=1.0, alpha=0.6)
    ax.text(0.02, ax.get_ylim()[1] * 0.95, 'true priors',
            rotation=90, color='#555', fontsize=9, va='top')

    ax.set_xlabel(r'Prior-noise standard deviation $\sigma$')
    ax.set_ylabel('Mean / Median Finder Competitive Ratio')
    ax.set_title('Robustness of $p/d^2$ bid to corrupted priors')
    ax.legend(loc='upper left', framealpha=0.92)
    ax.set_xlim(-0.05, max(SIGMAS) + 0.05)

    save_fig(fig, 'fig_prior_misspec.png')

    write_csv(os.path.join(DATA_DIR, 'exp1_prior_misspec.csv'),
              rows, header=['sigma', 'model', 'mean_fcr',
                            'median_fcr', 'n_trials'])

    # Quick numeric summary for the thesis prose
    print()
    print('  Headline numbers for thesis:')
    m4_base = np.mean(summary['M4 (p/d)'][0.0])
    m4s_base = np.mean(summary['M4* (p/d^2)'][0.0])
    m4_noisy = np.mean(summary['M4 (p/d)'][0.5])
    m4s_noisy = np.mean(summary['M4* (p/d^2)'][0.5])
    print(f'  at sigma=0.0:  M4={m4_base:.3f}, M4*={m4s_base:.3f}, '
          f'delta={m4_base - m4s_base:+.3f}')
    print(f'  at sigma=0.5:  M4={m4_noisy:.3f}, M4*={m4s_noisy:.3f}, '
          f'delta={m4_noisy - m4s_noisy:+.3f}')
    m4_degrade = (m4_noisy - m4_base) / m4_base * 100
    m4s_degrade = (m4_noisy - m4s_base) / m4s_base * 100
    print(f'  M4  degrades by {m4_degrade:+.1f}% at sigma=0.5')
    print(f'  M4* degrades by {m4s_degrade:+.1f}% at sigma=0.5')


if __name__ == '__main__':
    run()
