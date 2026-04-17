"""Command-line interface for searchfcr.

Subcommands:

  - ``generate``  : emit one instance as JSON.
  - ``run``       : run one model on one instance; print a summary.
  - ``sweep``     : sweep a parameter; print a table + optional CSV.
  - ``bench``     : canonical benchmark suite (paper headline table).
  - ``list-models``, ``list-bids``.

Invocation:

  - ``python -m searchfcr ...`` (always works)
  - ``searchfcr ...``           (after ``pip install -e .``)
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
import sys
from pathlib import Path
from typing import Iterable

from . import __version__
from .bids import Bid, list_bids
from .bounds import bound_m1, bound_m2, bound_m3, bound_m4
from .instance import Instance
from .models import MODELS, canonical_model_name, run


# --------------------------------------------------------------------- helpers

def _parse_range(spec: str) -> tuple[float, float]:
    """Parse 'a,b' into (a, b) floats."""
    try:
        a, b = spec.split(",")
        return float(a), float(b)
    except Exception as exc:  # noqa: BLE001
        raise argparse.ArgumentTypeError(
            f"Expected 'low,high', got {spec!r}"
        ) from exc


def _parse_model_list(spec: str) -> list[str]:
    names = [s.strip() for s in spec.split(",") if s.strip()]
    return [canonical_model_name(n) for n in names]


def _mean(xs: Iterable[float]) -> float:
    xs = list(xs)
    return float(statistics.fmean(xs)) if xs else float("nan")


def _stdev(xs: Iterable[float]) -> float:
    xs = list(xs)
    if len(xs) < 2:
        return 0.0
    return float(statistics.stdev(xs))


def _median(xs: Iterable[float]) -> float:
    xs = list(xs)
    return float(statistics.median(xs)) if xs else float("nan")


# -------------------------------------------------------------------- commands

def cmd_generate(args: argparse.Namespace) -> int:
    inst = Instance.generate(
        n=args.n,
        r=args.r,
        L=args.L,
        seed=args.seed,
        min_opt_dist=args.min_opt_dist,
        max_opt_dist=args.max_opt_dist,
    )
    payload = json.dumps(inst.to_dict(), indent=2, sort_keys=True)
    if args.output and args.output != "-":
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(payload, encoding="utf-8")
        print(f"wrote {args.output}")
    else:
        sys.stdout.write(payload + "\n")
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    inst = Instance.load(args.instance)
    res = run(args.model, inst, energy=args.energy, bid=args.bid)

    found_by = res.finder if res.finder is not None else "-"
    fcr_str = f"{res.fcr:.4f}" if res.fcr is not None else "n/a"
    print(f"model         : {res.model}")
    print(f"fcr           : {fcr_str}")
    print(f"iterations    : {res.iterations}")
    print(f"found_by      : {found_by}")
    print(f"optimal_dist  : {res.optimal_dist:.4f}")
    print(f"found         : {res.found}")
    return 0


def cmd_sweep(args: argparse.Namespace) -> int:
    models = args.models or ["M3", "M4", "M4star"]
    models = [canonical_model_name(m) for m in models]

    low, high = args.range
    step = args.step
    # Inclusive range; fencepost for float step sizes.
    values: list[float] = []
    v = low
    while v <= high + 1e-9:
        values.append(round(v, 10))
        v += step

    # Sweep dispatch: only energy is currently supported as a CLI param.
    if args.param != "energy":
        raise SystemExit(f"Unsupported sweep param: {args.param!r} (expected 'energy').")

    rows: list[dict] = []
    header = ["param_value", "model", "trials", "mean_fcr", "median_fcr", "stdev_fcr", "fail_rate"]

    for val in values:
        for mn in models:
            fcrs: list[float] = []
            fails = 0
            for t in range(args.trials):
                inst = Instance.generate(
                    n=args.n,
                    r=args.r,
                    L=args.L,
                    seed=args.seed + t,
                    max_opt_dist=val / 2,
                )
                res = run(mn, inst, energy=val, bid=args.bid)
                if res.fcr is not None:
                    fcrs.append(res.fcr)
                else:
                    fails += 1
            rows.append(
                {
                    "param_value": val,
                    "model": mn,
                    "trials": args.trials,
                    "mean_fcr": _mean(fcrs),
                    "median_fcr": _median(fcrs),
                    "stdev_fcr": _stdev(fcrs),
                    "fail_rate": fails / args.trials if args.trials else 0.0,
                }
            )

    # Pretty-print a table to stdout.
    _print_table(rows, header)

    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        with open(args.output, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=header)
            w.writeheader()
            for row in rows:
                w.writerow(row)
        print(f"\nwrote CSV to {args.output}")

    return 0


def cmd_bench(args: argparse.Namespace) -> int:
    """Canonical benchmark: the thesis's headline config.

    Defaults: n=30, R=3, E=14, L=10, 500 trials, seed=42. ``--trials`` can
    override for a shorter smoke test (reviewers will often want 50-100).
    """
    if args.suite != "default":
        raise SystemExit(f"Unknown suite: {args.suite!r}")

    n, R, E, L = 30, 3, 14.0, 10.0
    trials = args.trials
    seed = args.seed

    params = f"n={n}, R={R}, E={E}, L={L}, {trials} trials, seed={seed}"
    print("=" * 74)
    print("  SEARCHFCR BENCHMARK (suite=default)")
    print(f"  {params}")
    print("=" * 74)

    # Bounds
    b = {
        "M1": bound_m1(n, R, E, L),
        "M2": bound_m2(n, R, E, L),
        "M3": bound_m3(n, R, E, L),
        "M4": bound_m4(n, R, E, L),
        "M4star": bound_m4(n, R, E, L),  # same bound as M4 (multi-node)
        "HungarianD": float("nan"),
        "HungarianPD": float("nan"),
    }

    per_model_fcrs: dict[str, list[float]] = {m: [] for m in MODELS}
    per_model_iters: dict[str, list[int]] = {m: [] for m in MODELS}
    per_model_fails: dict[str, int] = {m: 0 for m in MODELS}

    for t in range(trials):
        inst = Instance.generate(n=n, r=R, L=L, seed=seed + t, max_opt_dist=E / 2)
        for mn in MODELS:
            res = run(mn, inst, energy=E)
            if res.fcr is not None:
                per_model_fcrs[mn].append(res.fcr)
                per_model_iters[mn].append(res.iterations)
            else:
                per_model_fails[mn] += 1

    # Headline table
    print(
        f"\n  {'Model':<14} {'mean FCR':>10} {'median':>10} {'stdev':>10} "
        f"{'iters':>8} {'fails':>7} {'bound':>10} {'holds?':>7}"
    )
    print("  " + "-" * 80)
    for mn in MODELS:
        fcrs = per_model_fcrs[mn]
        iters = per_model_iters[mn]
        mean_f = _mean(fcrs)
        med_f = _median(fcrs)
        std_f = _stdev(fcrs)
        mean_i = _mean(iters)
        fail = per_model_fails[mn]
        bnd = b[mn]
        if math.isfinite(bnd):
            holds = "OK" if (not math.isnan(mean_f) and mean_f <= bnd) else "FAIL"
            bnd_str = f"{bnd:>10.2f}"
        else:
            holds = "-"
            bnd_str = f"{'n/a':>10}"
        print(
            f"  {mn:<14} {mean_f:>10.3f} {med_f:>10.3f} {std_f:>10.3f} "
            f"{mean_i:>8.2f} {fail:>7d} {bnd_str} {holds:>7}"
        )

    print()
    return 0


def cmd_list_models(args: argparse.Namespace) -> int:
    del args
    for m in MODELS:
        print(m)
    return 0


def cmd_list_bids(args: argparse.Namespace) -> int:
    del args
    for b in list_bids():
        print(b)
    return 0


# ---------------------------------------------------------------- table helper

def _print_table(rows: list[dict], header: list[str]) -> None:
    if not rows:
        print("(no rows)")
        return
    # Format each cell as string
    cells: list[list[str]] = []
    for row in rows:
        row_cells = []
        for k in header:
            v = row[k]
            if isinstance(v, float):
                row_cells.append(f"{v:.4f}")
            else:
                row_cells.append(str(v))
        cells.append(row_cells)
    widths = [
        max(len(header[i]), max(len(r[i]) for r in cells))
        for i in range(len(header))
    ]
    fmt = "  ".join(f"{{:>{w}}}" for w in widths)
    print(fmt.format(*header))
    print("  ".join("-" * w for w in widths))
    for r in cells:
        print(fmt.format(*r))


# ----------------------------------------------------------------------- entry

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="searchfcr",
        description="Benchmark for budgeted multi-robot search with "
        "probability-aware auctions.",
    )
    p.add_argument("--version", action="version", version=f"searchfcr {__version__}")
    sub = p.add_subparsers(dest="cmd", required=True, metavar="<command>")

    # generate ---------------------------------------------------------------
    p_gen = sub.add_parser("generate", help="Generate a problem instance (JSON).")
    p_gen.add_argument("--n", type=int, required=True, help="Number of nodes.")
    p_gen.add_argument("--r", type=int, required=True, help="Number of robots.")
    p_gen.add_argument("--L", type=float, required=True, help="Area edge length.")
    p_gen.add_argument("--seed", type=int, required=True, help="RNG seed.")
    p_gen.add_argument("--min-opt-dist", type=float, default=1.0)
    p_gen.add_argument("--max-opt-dist", type=float, default=None)
    p_gen.add_argument("-o", "--output", type=str, default="-", help="Output path (- for stdout).")
    p_gen.set_defaults(func=cmd_generate)

    # run --------------------------------------------------------------------
    p_run = sub.add_parser("run", help="Run one model on one instance.")
    p_run.add_argument("--instance", type=str, required=True, help="Path to instance JSON.")
    p_run.add_argument("--model", type=str, required=True, help=f"One of: {', '.join(MODELS)}")
    p_run.add_argument("--energy", type=float, default=14.0)
    p_run.add_argument("--bid", type=str, default=None, help=f"One of: {', '.join(list_bids())}")
    p_run.set_defaults(func=cmd_run)

    # sweep ------------------------------------------------------------------
    p_sw = sub.add_parser("sweep", help="Sweep a parameter across models.")
    p_sw.add_argument("--param", type=str, default="energy", choices=["energy"])
    p_sw.add_argument("--range", dest="range", type=_parse_range, required=True,
                      help="Inclusive range 'low,high'.")
    p_sw.add_argument("--step", type=float, default=2.0)
    p_sw.add_argument("--n", type=int, default=30)
    p_sw.add_argument("--r", type=int, default=3)
    p_sw.add_argument("--L", type=float, default=10.0)
    p_sw.add_argument("--trials", type=int, default=100)
    p_sw.add_argument("--seed", type=int, default=42)
    p_sw.add_argument("--models", type=_parse_model_list, default=None,
                      help="Comma-separated clean model names.")
    p_sw.add_argument("--bid", type=str, default=None)
    p_sw.add_argument("--output", type=str, default=None, help="Write CSV here.")
    p_sw.set_defaults(func=cmd_sweep)

    # bench ------------------------------------------------------------------
    p_b = sub.add_parser("bench", help="Run the canonical benchmark suite.")
    p_b.add_argument("--suite", type=str, default="default")
    p_b.add_argument("--trials", type=int, default=500)
    p_b.add_argument("--seed", type=int, default=42)
    p_b.set_defaults(func=cmd_bench)

    # list-models ------------------------------------------------------------
    p_lm = sub.add_parser("list-models", help="Print available model names.")
    p_lm.set_defaults(func=cmd_list_models)

    # list-bids --------------------------------------------------------------
    p_lb = sub.add_parser("list-bids", help="Print available bid names.")
    p_lb.set_defaults(func=cmd_list_bids)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args) or 0)


if __name__ == "__main__":
    raise SystemExit(main())
