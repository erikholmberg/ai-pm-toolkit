#!/usr/bin/env python3
"""
Survey Sample Size Calculator

Calculate sample size needed for a survey to achieve a target margin of error
at a given confidence level (for proportions). Use when planning surveys and
discovery research; different from A/B test sample size (which is for detecting a lift).

Usage:
    python survey-sample-size.py --margin 0.05 --confidence 0.95
    python survey-sample-size.py --margin 0.03 --proportion 0.5 --confidence 0.95
    python survey-sample-size.py --margin 0.05 --confidence 0.90 --population 10000

Formula: n = (z^2 * p * (1-p)) / E^2  for infinite population; finite population correction optional.

Requirements:
    None (stdlib only).
"""

import argparse
import math
import sys
from typing import Optional

from statistics import NormalDist


def _norm_ppf(p: float) -> float:
    """Inverse normal CDF (the quantile function).

    This was scipy's `stats.norm.ppf` — the only thing this script ever used
    scipy for, and the reason a clean checkout failed until someone ran
    `pip install scipy`. The stdlib has computed the same quantity since
    Python 3.8 at the same precision: ppf(0.975) is 1.959963985 either way.
    """
    return NormalDist().inv_cdf(p)


def sample_size(
    margin: float,
    confidence: float = 0.95,
    proportion: float = 0.5,
    population: Optional[int] = None,
) -> int:
    """
    Sample size for a proportion with target margin of error E and confidence level.

    n = (z^2 * p * (1-p)) / E^2. Use p=0.5 for conservative (largest) n.
    If population is given, apply finite population correction: n_adj = n / (1 + (n-1)/N).
    """
    if not 0 < margin < 1 or not 0 < confidence < 1 or not 0 <= proportion <= 1:
        return 0
    z = _norm_ppf(1 - (1 - confidence) / 2)
    p = proportion
    n = (z * z * p * (1 - p)) / (margin * margin)
    n = math.ceil(n)
    if population is not None and population > 0 and n > 0:
        # Finite population correction: n' = n / (1 + (n-1)/N)
        n_corrected = n / (1 + (n - 1) / population)
        n = max(1, math.ceil(n_corrected))
    return n


def main():
    parser = argparse.ArgumentParser(
        description="Survey sample size for target margin of error (proportions)."
    )
    parser.add_argument(
        "--margin",
        "-e",
        type=float,
        required=True,
        help="Target margin of error (e.g. 0.05 for ±5%%)",
    )
    parser.add_argument(
        "--confidence",
        "-c",
        type=float,
        default=0.95,
        help="Confidence level (default: 0.95)",
    )
    parser.add_argument(
        "--proportion",
        "-p",
        type=float,
        default=0.5,
        help="Expected proportion (default 0.5 = conservative)",
    )
    parser.add_argument(
        "--population",
        "-N",
        type=int,
        default=None,
        help="Finite population size (optional; applies correction)",
    )
    args = parser.parse_args()

    if not 0 < args.margin < 1:
        print("Error: --margin must be in (0, 1)", file=sys.stderr)
        return 1
    if not 0 < args.confidence < 1:
        print("Error: --confidence must be in (0, 1)", file=sys.stderr)
        return 1
    if not 0 <= args.proportion <= 1:
        print("Error: --proportion must be in [0, 1]", file=sys.stderr)
        return 1

    n = sample_size(args.margin, args.confidence, args.proportion, args.population)
    pct_conf = args.confidence * 100
    pct_margin = args.margin * 100

    print("\n" + "=" * 60)
    print("SURVEY SAMPLE SIZE")
    print("=" * 60)
    print("\n📋 INPUTS:")
    print(f"   • Margin of error:   ±{pct_margin:.1f}%")
    print(f"   • Confidence level:  {pct_conf:.0f}%")
    print(f"   • Assumed proportion: {args.proportion * 100:.1f}% (use 50% for conservative)")
    if args.population is not None:
        print(f"   • Population size:   {args.population:,} (finite correction applied)")
    print("\n📈 RESULT:")
    print(f"   • Required sample size:  n = {n:,}")
    if args.population is not None and n > args.population:
        print(f"   • (capped by population {args.population:,})")
    print("\n  For ±5% at 95% confidence, n ≈ 385 is a common rule of thumb (p=0.5).")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
