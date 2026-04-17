# SearchFCR

**A benchmark and reference implementation for budgeted multi-robot search with probability-aware auctions.**

SearchFCR packages the algorithms and experiments from the CSULB honors thesis *On the Numerical Analysis of Multi-Robot Search and Rescue Algorithms in Unknown Environments* (Babaeiyan Ghamsari, 2026) as a reusable Python library, a command-line tool, and a set of reproducible benchmarks. The thesis introduces a bid function `p/d²` that outperforms the classical `p/d` Stone-rule bid by 4.2% under finite energy, with three supporting experiments (prior-misspecification robustness, target-delay anomaly, cost-sensitivity generalization).

<p align="center">
  <img src="thesis/figures/fig_m1_vs_m4star.png" width="720" alt="M1 vs M4* on the same instance"/><br/>
  <em>Same instance, same seed. <strong>M1 (left)</strong> — robots pick sites independently and fly spaghetti. <strong>M4* (right)</strong> — auction-coordinated <code>p/d²</code> bidding, 18× lower finder travel.</em>
</p>

## Why this exists

Multi-robot search-and-rescue has been studied from three angles — online competitive analysis (the cow-path problem), market-based auction coordination, and energy-constrained graph exploration — each in isolation. No prior work unifies all three into a single benchmark. SearchFCR fills that gap:

- **Four models** spanning the {energy × communication} design space (M1–M4, plus M4* with the `p/d²` bid).
- **Four bid functions** (`p`, `1/d`, `p/d`, `p/d²`, `p·e^{−d/E}`) with a documented API for adding more.
- **Three cost models** (Euclidean, Manhattan, obstacle-penalty) plus heterogeneous-speed fleets.
- **Theoretical upper bounds** on finder competitive ratio for each model, empirically validated.
- **Seven reproducible benchmark suites** with fixed seeds so your numbers match ours bit-for-bit.

## Headline findings (thesis Table II, 500 trials)

| Model | Mean FCR | Median | σ | What it tells us |
|---|---:|---:|---:|---|
| M1 Random (∞ E) | 18.55 | 14.59 | 17.12 | Without coordination, FCR is a disaster. |
| M2 Auction (∞ E, N2N) | 2.83 | 1.98 | 2.53 | With unlimited battery, auctions are excellent. |
| H<sub>d</sub> Hungarian (E, dist-only) | 6.80 | 6.60 | 3.60 | Centralized, probability-blind. |
| H<sub>p/d</sub> Hungarian (E, p/d) | 6.31 | 5.19 | 3.55 | Probability-aware, centralized. |
| M3 Auction (E, p/d) | 6.41 | 5.13 | 4.83 | Probability-aware, distributed. Single sortie. |
| M4 Auction (E, p/d) | 3.11 | 2.21 | 2.22 | Single sortie → chain = 92% of the energy gap recovered. |
| **M4\* Auction (E, p/d²)** | **2.98** | **2.19** | **1.97** | **Quadratic distance penalty → 4.2% further improvement.** |

## Install

```bash
git clone https://github.com/foojanbabaeeian/Multi-Robot-Algo.git
cd Multi-Robot-Algo
pip install -e .
```

Requires Python ≥ 3.10, numpy, scipy, matplotlib. Install completes in about 20 seconds on a cold machine.

## One-line reproduction of every thesis figure

```bash
python reproduce_thesis.py
```

Takes ~3 minutes on a modern laptop. Reproduces every figure in `thesis/figures/` and every CSV in `experiments/data/`. Add `--quick` for a 100-trial iteration that finishes in 45 seconds.

## CLI quickstart

```bash
# Generate an instance
searchfcr generate --n 30 --r 3 --L 10 --seed 42 -o instance.json

# Run one model
searchfcr run --instance instance.json --model M4star --energy 14 --bid p_over_d2

# Sweep the energy budget
searchfcr sweep --param energy --range 8,30 --step 2 --trials 500 \
                --models M3,M4,M4star --output energy_sweep.csv

# Run the thesis's default benchmark suite
searchfcr bench --suite default
```

All subcommands accept `--help`.

## Library quickstart

```python
from searchfcr import Instance, run

# Generate a random instance (target drawn from priors)
instance = Instance.generate(n=30, r=3, L=10.0, seed=42)

# Run each model
for model in ["M1", "M2", "M3", "M4", "M4star", "HungarianD", "HungarianPD"]:
    result = run(model, instance, energy=14.0, bid="p_over_d2")
    print(f"{model:12s}  FCR={result.fcr:5.2f}  found={result.found}  "
          f"iters={result.iterations}")
```

## The four new contributions of the thesis

The thesis extends the base framework with four experimentally validated results. Each lives in its own module so you can point reviewers at a single file.

1. **The `p/d²` bid function** — under finite energy, the classical Stone-rule `p/d` bid over-commits to distant high-probability sites. The cost-foreclosure argument (thesis §3.3) says the effective marginal cost of distance is superlinear, so the bid should penalize `d²`. Empirically: 4.2% FCR improvement on the default config, 8.6% on the obstacle-cost variant. See `searchfcr/bids.py`.

2. **The Target-Delay Anomaly** — 2-opt post-processing shortens tours on average but *worsens* FCR by 6.58%, because it re-orders sites by geometric efficiency rather than probability-weighted reward. This is counterintuitive: the standard robotics pipeline ("build a tour, polish with 2-opt") is actively harmful for finder-centric metrics under Bayesian priors. See `experiments/exp2_target_delay.py`.

3. **Prior-misspecification robustness** — the `p/d²` advantage over `p/d` widens as priors become noisy. At σ=0 the absolute margin is 0.13 FCR; at σ=0.5 it is 0.49 FCR; at σ=1.0 it is 0.43 FCR. See `experiments/exp1_prior_misspec.py`.

4. **Cost-model generalization** — `p/d²` wins under all four cost models tested (Euclidean, Manhattan, heterogeneous-speed fleet, obstacle-penalty). The foreclosure argument does not depend on the metric. See `experiments/exp3_cost_sensitivity.py`.

## Repository layout

```
searchfcr/            # The stable, testable public API. Import from here.
  instance.py         # Instance dataclass + JSON schema v1
  models.py           # run(), MODELS, RunResult
  bids.py             # Bid enum and bid functions
  metrics.py          # fcr(), entropy()
  bounds.py           # theoretical FCR upper bounds
  cli.py              # argparse CLI → `searchfcr` entry point

main.py               # Original monolithic research script (the source of truth
                      # that searchfcr/ wraps). Still runnable as before.

experiments/          # Three thesis-level extensions, each self-contained.
  exp1_prior_misspec.py    # Experiment 1 — prior misspecification robustness.
  exp2_target_delay.py     # Experiment 2 — the Target-Delay Anomaly.
  exp3_cost_sensitivity.py # Experiment 3 — cost-model generalization.
  data/               # Raw CSV outputs; regenerated by reproduce_thesis.py.

thesis/               # LaTeX sources, figures, chapter prose.
  Chapters/*.tex      # One chapter per file; compiled via thesis/main.tex
  figures/            # PNG output of every figure; regenerated on demand.
  make_thesis_figures.py  # Four pedagogical figures (not in paper).

paper/                # IEEE conference-format version of the paper.

pybullet_demo/        # 3D physics-based demo (M1 vs M4* on simulated drones).

backend/              # FastAPI server wrapping main.py for the React UI.
sar-sim/              # React/Vite interactive simulator.

tests/                # pytest suite (37 tests, 25 s).
reproduce_thesis.py   # One-command pipeline.
```

## Contributing and benchmarks

If you write a new model or bid function that beats M4*'s FCR on the default benchmark suite, please open a pull request with:

1. A new file under `searchfcr/models.py` or `searchfcr/bids.py`.
2. A corresponding test under `tests/`.
3. The benchmark numbers from `searchfcr bench --suite default --trials 500`.

We will update the headline table above and add you as a co-author of the SearchFCR benchmark.

## Cite

```bibtex
@thesis{BabaeiyanGhamsari2026,
  author = {Babaeiyan Ghamsari, Fozhan},
  title  = {On the Numerical Analysis of Multi-Robot Search and Rescue
            Algorithms in Unknown Environments},
  school = {California State University, Long Beach},
  year   = {2026},
  type   = {Honors thesis},
  url    = {https://github.com/foojanbabaeeian/Multi-Robot-Algo}
}

@software{SearchFCR2026,
  author  = {Babaeiyan Ghamsari, Fozhan and Morales-Ponce, Oscar},
  title   = {{SearchFCR}: A Benchmark for Budgeted Multi-Robot Search
             with Probability-Aware Auctions},
  version = {0.1.0},
  year    = {2026},
  url     = {https://github.com/foojanbabaeeian/Multi-Robot-Algo}
}
```

## License

MIT. See `LICENSE`.
