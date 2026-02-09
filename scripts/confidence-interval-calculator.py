#!/usr/bin/env python3
"""
Confidence Interval Calculator

Compute confidence intervals for proportions (Wilson score) or means (normal approximation).
Useful for reporting metrics and stakeholder updates. Reuses logic aligned with A/B analysis.

Usage:
    python confidence-interval-calculator.py --n 500 --proportion 0.32
    python confidence-interval-calculator.py --n 500 --proportion 0.32 --confidence 0.90
    python confidence-interval-calculator.py --n 200 --mean 4.2 --std 1.1

Requirements:
    pip install scipy (for Wilson and mean CI).
"""

import argparse
import math
import sys
from typing import Optional, Tuple

try:
    from scipy import stats
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False


def wilson_ci(
    n: int,
    p: float,
    confidence: float = 0.95,
) -> Tuple[float, float]:
    """
    Wilson score interval for a proportion. Better than normal approx for small n or extreme p.

    Args:
        n: Sample size.
        p: Observed proportion (0 <= p <= 1).
        confidence: Confidence level (e.g. 0.95 for 95%).

    Returns:
        (lower, upper) bounds.
    """
    if not SCIPY_AVAILABLE:
        raise RuntimeError("scipy is required. Run: pip install scipy")
    if n <= 0:
        return (0.0, 1.0)
    z = stats.norm.ppf(1 - (1 - confidence) / 2)
    z2 = z * z
    denom = 1 + z2 / n
    center = (p + z2 / (2 * n)) / denom
    margin = (z / denom) * math.sqrt(p * (1 - p) / n + z2 / (4 * n * n))
    low = max(0.0, center - margin)
    high = min(1.0, center + margin)
    return (low, high)


def mean_ci(
    n: int,
    mean: float,
    std: float,
    confidence: float = 0.95,
) -> Tuple[float, float]:
    """
    Normal-approximation CI for the mean (uses t if you prefer; here we use z for simplicity).

    Args:
        n: Sample size.
        mean: Sample mean.
        std: Sample standard deviation.
        confidence: Confidence level.

    Returns:
        (lower, upper) bounds.
    """
    if not SCIPY_AVAILABLE:
        raise RuntimeError("scipy is required. Run: pip install scipy")
    if n <= 0 or std < 0:
        return (mean, mean)
    z = stats.norm.ppf(1 - (1 - confidence) / 2)
    se = std / math.sqrt(n)
    return (mean - z * se, mean + z * se)


def main():
    parser = argparse.ArgumentParser(
        description="Confidence intervals for proportions (Wilson) or means."
    )
    parser.add_argument("--n", type=int, required=True, help="Sample size")
    parser.add_argument(
        "--proportion",
        "-p",
        type=float,
        help="Observed proportion (0–1), e.g. 0.32 for 32%%",
    )
    parser.add_argument(
        "--mean",
        "-m",
        type=float,
        help="Sample mean (use with --std for mean CI)",
    )
    parser.add_argument(
        "--std",
        "-s",
        type=float,
        help="Sample standard deviation (use with --mean)",
    )
    parser.add_argument(
        "--confidence",
        "-c",
        type=float,
        default=0.95,
        help="Confidence level (default: 0.95)",
    )
    args = parser.parse_args()

    if args.n < 1:
        print("Error: --n must be >= 1", file=sys.stderr)
        return 1
    if not 0 < args.confidence < 1:
        print("Error: --confidence must be in (0, 1)", file=sys.stderr)
        return 1

    if args.proportion is not None:
        if not 0 <= args.proportion <= 1:
            print("Error: --proportion must be in [0, 1]", file=sys.stderr)
            return 1
        if not SCIPY_AVAILABLE:
            print("Error: scipy required. Run: pip install scipy", file=sys.stderr)
            return 1
        low, high = wilson_ci(args.n, args.proportion, args.confidence)
        pct = args.confidence * 100
        print("\n" + "=" * 60)
        print("CONFIDENCE INTERVAL (PROPORTION — WILSON SCORE)")
        print("=" * 60)
        print(f"\n  Sample size:     {args.n:,}")
        print(f"  Observed rate:   {args.proportion * 100:.2f}%")
        print(f"  Confidence:      {pct:.0f}%")
        print(f"\n  {pct:.0f}% CI:  [{low * 100:.2f}% , {high * 100:.2f}%]")
        print("=" * 60)
        return 0

    if args.mean is not None and args.std is not None:
        if args.std < 0:
            print("Error: --std must be >= 0", file=sys.stderr)
            return 1
        if not SCIPY_AVAILABLE:
            print("Error: scipy required. Run: pip install scipy", file=sys.stderr)
            return 1
        low, high = mean_ci(args.n, args.mean, args.std, args.confidence)
        pct = args.confidence * 100
        print("\n" + "=" * 60)
        print("CONFIDENCE INTERVAL (MEAN — NORMAL APPROX)")
        print("=" * 60)
        print(f"\n  Sample size:     {args.n:,}")
        print(f"  Sample mean:     {args.mean:.4f}")
        print(f"  Sample std dev:  {args.std:.4f}")
        print(f"  Confidence:      {pct:.0f}%")
        print(f"\n  {pct:.0f}% CI:  [{low:.4f} , {high:.4f}]")
        print("=" * 60)
        return 0

    parser.print_help()
    print("\nExamples:", file=sys.stderr)
    print("  Proportion: --n 500 --proportion 0.32", file=sys.stderr)
    print("  Mean:       --n 200 --mean 4.2 --std 1.1", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
