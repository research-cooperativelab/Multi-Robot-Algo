"""reproduce_thesis.py — one-command regeneration of every thesis figure.

Running this script from the repo root:

    python reproduce_thesis.py

reproduces, in order, every numerical result and figure referenced in the
CSULB honors thesis 'On the Numerical Analysis of Multi-Robot Search and
Rescue Algorithms in Unknown Environments' (Babaeiyan Ghamsari, 2026).

What it runs, in order:
  1. main.py                              — six core thesis figures (Table 2,
                                            bounds, energy sweep, robot sweep,
                                            bid variants, iterations, snapshot).
  2. thesis/make_thesis_figures.py        — four pedagogical figures (FCR
                                            explanation, model tree, M4*
                                            walkthrough, M1 vs M4* comparison).
  3. experiments/exp1_prior_misspec.py    — Experiment 1 figure + CSV.
  4. experiments/exp2_target_delay.py     — Experiment 2 figure + CSV.
  5. experiments/exp3_cost_sensitivity.py — Experiment 3 figure + CSV.

All figures land under thesis/figures/; all raw numbers land under
experiments/data/. The LaTeX sources in thesis/Chapters/ reference these
outputs by name.

Run with --quick to use 100 trials instead of 500 (for fast iteration).

Requirements: numpy, scipy, matplotlib. PyBullet is optional (demo).

Usage:
    python reproduce_thesis.py            # full 500-trial rebuild
    python reproduce_thesis.py --quick    # 100-trial quick rebuild
    python reproduce_thesis.py --skip-main     # just the 4 pedagogical figs + exps
    python reproduce_thesis.py --skip-exps     # just the main pipeline + pedagogical
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time


ROOT = os.path.dirname(os.path.abspath(__file__))


def enable_utf8_stdout():
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except AttributeError:
        pass


def run_step(label, argv, cwd=ROOT):
    print()
    print('=' * 74)
    print(f'  {label}')
    print('=' * 74)
    t0 = time.time()
    env = dict(os.environ)
    env['PYTHONIOENCODING'] = 'utf-8'
    proc = subprocess.run(argv, cwd=cwd, env=env, check=False)
    dt = time.time() - t0
    if proc.returncode != 0:
        print(f'  FAILED in {dt:.1f}s (exit {proc.returncode})')
        return False
    print(f'  OK ({dt:.1f}s)')
    return True


def main():
    enable_utf8_stdout()
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--quick', action='store_true',
                        help='Use 100 trials instead of 500 (fast iteration).')
    parser.add_argument('--skip-main', action='store_true',
                        help='Skip main.py (the six core paper/thesis figures).')
    parser.add_argument('--skip-thesis-figs', action='store_true',
                        help='Skip the four pedagogical thesis figures.')
    parser.add_argument('--skip-exps', action='store_true',
                        help='Skip the three experiments (exp1/exp2/exp3).')
    args = parser.parse_args()

    python = sys.executable

    fig_dir = os.path.join(ROOT, 'thesis', 'figures')
    data_dir = os.path.join(ROOT, 'experiments', 'data')
    os.makedirs(fig_dir, exist_ok=True)
    os.makedirs(data_dir, exist_ok=True)

    print('SearchFCR — Thesis reproduction pipeline')
    print(f'  ROOT       : {ROOT}')
    print(f'  figures    -> {fig_dir}')
    print(f'  raw data   -> {data_dir}')
    print(f'  quick mode : {args.quick}')

    ok = True

    if not args.skip_main:
        cmd = [python, 'main.py', '--outdir', fig_dir]
        if args.quick:
            cmd.append('--quick')
        ok &= run_step('1/5  Main pipeline (main.py)', cmd)

    if not args.skip_thesis_figs:
        ok &= run_step('2/5  Pedagogical thesis figures',
                       [python, os.path.join('thesis', 'make_thesis_figures.py')])

    if not args.skip_exps:
        ok &= run_step('3/5  Experiment 1: Prior Misspecification',
                       [python, os.path.join('experiments',
                                             'exp1_prior_misspec.py')])
        ok &= run_step('4/5  Experiment 2: Target-Delay Anomaly',
                       [python, os.path.join('experiments',
                                             'exp2_target_delay.py')])
        ok &= run_step('5/5  Experiment 3: Cost Sensitivity',
                       [python, os.path.join('experiments',
                                             'exp3_cost_sensitivity.py')])

    print()
    print('=' * 74)
    if ok:
        print('  ALL STEPS COMPLETED SUCCESSFULLY')
        print(f'  Figures in: {fig_dir}')
        print(f'  Data    in: {data_dir}')
    else:
        print('  ONE OR MORE STEPS FAILED  (see logs above)')
    print('=' * 74)

    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
