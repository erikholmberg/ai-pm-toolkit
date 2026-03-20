#!/usr/bin/env python3
"""
Eval set & labeling economics

Estimate how many labeled (gold) examples you need to pin down a pass rate,
precision, or recall to a target margin of error—and what labeling will cost.

Uses the standard sample-size formula for a proportion:
  n = (z^2 * p * (1-p)) / E^2
with optional finite-population correction. For recall, optionally translate
required **positive** items into total gold-set size using --prevalence.

This plans **descriptive** precision of a metric on a gold set. For comparing
two models or variants on the same set, use paired methods / separate power
analysis (see ab-test-calculator.py / experiment tooling).

Usage:
    python eval-label-economics.py --margin 0.05 --confidence 0.95 --cost-per-label 2.50
    python eval-label-economics.py --mode precision --margin 0.03 --proportion 0.85 --cost-per-label 1
    python eval-label-economics.py --mode recall --margin 0.05 --proportion 0.7 --prevalence 0.2 --cost-per-label 0

Requirements:
    pip install scipy
"""

from __future__ import annotations

import argparse
import math
import sys
from typing import Optional

try:
    from scipy import stats
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False


def sample_size_proportion(
    margin: float,
    confidence: float,
    proportion: float,
    population: Optional[int] = None,
) -> int:
    """Sample size for estimating a proportion within ±margin at confidence."""
    if not 0 < margin < 1 or not 0 < confidence < 1 or not 0 <= proportion <= 1:
        return 0
    z = stats.norm.ppf(1 - (1 - confidence) / 2)
    p = proportion
    n = (z * z * p * (1 - p)) / (margin * margin)
    n = max(1, math.ceil(n))
    if population is not None and population > 0:
        n_corrected = n / (1 + (n - 1) / population)
        n = max(1, math.ceil(n_corrected))
    return n


def format_money(amount: float) -> str:
    if amount == 0:
        return "$0"
    return f"${amount:,.2f}"


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Gold-set size and labeling cost for target precision on pass rate, "
            "precision, or recall (proportion sample size)."
        )
    )
    parser.add_argument(
        "--mode",
        choices=("pass-rate", "precision", "recall"),
        default="pass-rate",
        help=(
            "What you are estimating on the gold set: overall pass rate, "
            "precision (among predicted positives), or recall (among true positives)."
        ),
    )
    parser.add_argument(
        "--margin",
        "-e",
        type=float,
        required=True,
        help="Target margin of error (half-width), e.g. 0.05 for ±5%% absolute.",
    )
    parser.add_argument(
        "--confidence",
        "-c",
        type=float,
        default=0.95,
        help="Confidence level (default: 0.95).",
    )
    parser.add_argument(
        "--proportion",
        "-p",
        type=float,
        default=0.5,
        help=(
            "Expected rate (pass rate, precision, or recall). Default 0.5 is "
            "conservative for variance. Use a pilot estimate when you have one."
        ),
    )
    parser.add_argument(
        "--prevalence",
        type=float,
        default=None,
        help=(
            "Fraction of gold-set items that are condition-positive (only for "
            "--mode recall). Required items n is for positives; total gold N ≈ n / prevalence."
        ),
    )
    parser.add_argument(
        "--population",
        "-N",
        type=int,
        default=None,
        help="Finite population correction if sampling without replacement from a catalog.",
    )
    parser.add_argument(
        "--cost-per-label",
        type=float,
        default=0.0,
        help="Cost per labeled example (review + tooling). Default 0 (size only).",
    )
    parser.add_argument(
        "--minutes-per-label",
        type=float,
        default=None,
        help="If set with --hourly-rate, cost = (minutes/60) * hourly_rate per label.",
    )
    parser.add_argument(
        "--hourly-rate",
        type=float,
        default=None,
        help="Used with --minutes-per-label to derive cost per label.",
    )
    args = parser.parse_args()

    if not SCIPY_AVAILABLE:
        print("Error: scipy required. Run: pip install scipy", file=sys.stderr)
        return 1
    if not 0 < args.margin < 1:
        print("Error: --margin must be in (0, 1)", file=sys.stderr)
        return 1
    if not 0 < args.confidence < 1:
        print("Error: --confidence must be in (0, 1)", file=sys.stderr)
        return 1
    if not 0 <= args.proportion <= 1:
        print("Error: --proportion must be in [0, 1]", file=sys.stderr)
        return 1
    if args.mode != "recall" and args.prevalence is not None:
        print("Error: --prevalence is only used with --mode recall", file=sys.stderr)
        return 1
    if args.mode == "recall" and args.prevalence is not None:
        if not 0 < args.prevalence <= 1:
            print("Error: --prevalence must be in (0, 1]", file=sys.stderr)
            return 1

    cost_per = float(args.cost_per_label)
    if args.minutes_per_label is not None or args.hourly_rate is not None:
        if args.minutes_per_label is None or args.hourly_rate is None:
            print(
                "Error: use both --minutes-per-label and --hourly-rate, or only --cost-per-label",
                file=sys.stderr,
            )
            return 1
        if args.minutes_per_label <= 0 or args.hourly_rate < 0:
            print("Error: --minutes-per-label and --hourly-rate must be positive (rate may be 0)", file=sys.stderr)
            return 1
        cost_per = (args.minutes_per_label / 60.0) * args.hourly_rate

    n_items = sample_size_proportion(
        args.margin, args.confidence, args.proportion, args.population
    )
    total_cost = n_items * cost_per

    mode_title = {
        "pass-rate": "PASS RATE (overall gold set)",
        "precision": "PRECISION (among items predicted positive)",
        "recall": "RECALL (among condition-positive items)",
    }[args.mode]

    n_gold_total: Optional[int] = None
    if args.mode == "recall" and args.prevalence is not None:
        n_gold_total = max(1, math.ceil(n_items / args.prevalence))

    print("\n" + "=" * 62)
    print("EVAL SET & LABEL ECONOMICS")
    print("=" * 62)
    print(f"\n📌 Metric: {mode_title}")
    print("\n📋 INPUTS:")
    print(f"   • Target half-width:  ±{100 * args.margin:.2f} percentage points")
    print(f"   • Confidence level:   {100 * args.confidence:.0f}%")
    print(f"   • Expected rate (p):  {100 * args.proportion:.1f}%")
    if args.population is not None:
        print(f"   • Finite population:  N = {args.population:,}")
    if args.mode == "recall" and args.prevalence is not None:
        print(f"   • Condition-positive prevalence in gold: {100 * args.prevalence:.1f}%")
    if cost_per > 0:
        print(f"   • Cost per label:     {format_money(cost_per)}")
    print("\n📈 RESULT:")
    if args.mode == "recall" and args.prevalence is not None:
        print(f"   • Labeled positives needed (for recall CI):  {n_items:,}")
        print(f"   • Approx. total gold set size:                {n_gold_total:,}")
        if cost_per > 0 and n_gold_total is not None:
            print(f"   • Labeling cost (all items in set):         {format_money(n_gold_total * cost_per)}")
    else:
        print(f"   • Items to label / include in gold set:  n = {n_items:,}")
        if cost_per > 0:
            print(f"   • Estimated labeling cost:               {format_money(total_cost)}")

    print("\n📎 Notes:")
    print("   • Uses normal approximation for n; Wilson CIs are tighter for small n—")
    print("     this is a planning estimate; confidence-interval-calculator.py for reported CIs.")
    if args.mode == "recall" and args.prevalence is None:
        print("   • For recall, n is **condition-positive** count; scale up by prevalence")
        print("     (total gold ≈ n / prevalence) or pass --prevalence.")
    print("   • For A/B or \"did the model improve?\", plan paired or two-sample power separately.")
    print("=" * 62)
    return 0


if __name__ == "__main__":
    sys.exit(main())
