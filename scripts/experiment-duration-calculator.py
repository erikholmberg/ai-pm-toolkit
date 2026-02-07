#!/usr/bin/env python3
"""
Experiment Duration Calculator

Estimate how long an A/B or multivariate test must run to reach required sample size.
Complements ab-test-calculator.py: use that for sample size and significance; use this
for "how many days?" given your traffic.

Usage:
    python experiment-duration-calculator.py --baseline 0.05 --mde 0.10 --daily-visitors 5000
    python experiment-duration-calculator.py --baseline 0.03 --mde 0.15 --daily-visitors 10000 --traffic 0.5 --variants 3
    python experiment-duration-calculator.py --sample-size 5000 --daily-visitors 3000

Requirements:
    pip install scipy
"""

import math
import argparse
from typing import Tuple

try:
    from scipy import stats
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False


def calculate_sample_size(
    baseline_rate: float,
    minimum_detectable_effect: float,
    alpha: float = 0.05,
    power: float = 0.80,
    two_tailed: bool = True,
) -> int:
    """
    Required sample size per variant for an A/B test.
    Same formula as ab-test-calculator.py.
    """
    if not SCIPY_AVAILABLE:
        raise RuntimeError("scipy is required. Run: pip install scipy")
    p1 = baseline_rate
    p2 = baseline_rate * (1 + minimum_detectable_effect)
    p_pooled = (p1 + p2) / 2
    if two_tailed:
        z_alpha = stats.norm.ppf(1 - alpha / 2)
    else:
        z_alpha = stats.norm.ppf(1 - alpha)
    z_beta = stats.norm.ppf(power)
    numerator = (
        z_alpha * math.sqrt(2 * p_pooled * (1 - p_pooled))
        + z_beta * math.sqrt(p1 * (1 - p1) + p2 * (1 - p2))
    ) ** 2
    denominator = (p2 - p1) ** 2
    return max(1, math.ceil(numerator / denominator))


def calculate_duration_days(
    sample_size_per_variant: int,
    daily_visitors: int,
    traffic_allocation: float = 1.0,
    num_variants: int = 2,
) -> int:
    """
    Days to run the experiment.

    Args:
        sample_size_per_variant: Required sample size per variant.
        daily_visitors: Total daily visitors (or events) to the experiment surface.
        traffic_allocation: Fraction of traffic in the test (default 1.0).
        num_variants: Number of variants including control (default 2).

    Returns:
        Minimum whole days to reach required sample per variant.
    """
    if daily_visitors <= 0 or traffic_allocation <= 0 or num_variants < 1:
        return 0
    daily_per_variant = (daily_visitors * traffic_allocation) / num_variants
    if daily_per_variant <= 0:
        return 0
    return max(1, math.ceil(sample_size_per_variant / daily_per_variant))


def main():
    parser = argparse.ArgumentParser(
        description="Estimate experiment duration (days to run) from baseline, MDE, and traffic."
    )
    parser.add_argument(
        "--baseline",
        "-b",
        type=float,
        help="Baseline conversion rate (e.g. 0.05 for 5%%)",
    )
    parser.add_argument(
        "--mde",
        "-m",
        type=float,
        help="Minimum detectable effect as relative lift (e.g. 0.10 for 10%%)",
    )
    parser.add_argument(
        "--daily-visitors",
        "-d",
        type=int,
        required=True,
        help="Average daily visitors (or events) to the experiment",
    )
    parser.add_argument(
        "--sample-size",
        type=int,
        help="Use this sample size instead of calculating from baseline/MDE (skip --baseline/--mde)",
    )
    parser.add_argument(
        "--traffic",
        "-t",
        type=float,
        default=1.0,
        help="Fraction of traffic in the test (default: 1.0)",
    )
    parser.add_argument(
        "--variants",
        "-v",
        type=int,
        default=2,
        help="Number of variants including control (default: 2)",
    )
    parser.add_argument(
        "--alpha",
        type=float,
        default=0.05,
        help="Significance level (default: 0.05)",
    )
    parser.add_argument(
        "--power",
        type=float,
        default=0.80,
        help="Statistical power (default: 0.80)",
    )
    args = parser.parse_args()

    if args.sample_size is not None:
        if args.sample_size < 1:
            print("Error: --sample-size must be >= 1")
            return 1
        sample_per_variant = args.sample_size
        baseline_mde_note = ""
    elif args.baseline is not None and args.mde is not None:
        if not 0 < args.baseline < 1 or not args.mde > 0:
            print("Error: --baseline must be in (0,1) and --mde must be positive")
            return 1
        if not SCIPY_AVAILABLE:
            print("Error: scipy required. Run: pip install scipy")
            return 1
        sample_per_variant = calculate_sample_size(
            args.baseline, args.mde, args.alpha, args.power
        )
        baseline_mde_note = (
            f"  Baseline: {args.baseline * 100:.2f}%  |  MDE: {args.mde * 100:.0f}% relative  |  "
            f"α={args.alpha}, power={args.power}\n"
        )
    else:
        parser.print_help()
        print("\nExample: --baseline 0.05 --mde 0.10 --daily-visitors 5000")
        print("     or: --sample-size 5000 --daily-visitors 5000")
        return 0

    days = calculate_duration_days(
        sample_per_variant,
        args.daily_visitors,
        args.traffic,
        args.variants,
    )
    daily_per_variant = (args.daily_visitors * args.traffic) / args.variants

    print("\n" + "=" * 60)
    print("⏱️  EXPERIMENT DURATION ESTIMATE")
    print("=" * 60)
    if baseline_mde_note:
        print("\n📋 " + baseline_mde_note.strip())
    print("\n📈 SAMPLE SIZE:")
    print(f"   • Required per variant: {sample_per_variant:,}")
    print(f"   • Total (all variants):  {sample_per_variant * args.variants:,}")
    print("\n📊 TRAFFIC:")
    print(f"   • Daily visitors:        {args.daily_visitors:,}")
    print(f"   • Traffic in test:       {args.traffic * 100:.0f}%")
    print(f"   • Variants:              {args.variants}")
    print(f"   • Daily per variant:     ~{daily_per_variant:,.0f}")
    print("\n⏱️  DURATION:")
    print(f"   • Estimated run length:  ~{days} days")
    if days > 28:
        print(f"   • (~{days / 7:.1f} weeks)")
    if days > 90:
        print("   ⚠️  Consider higher traffic, larger MDE, or fewer variants")
    print("\n" + "=" * 60)
    return 0


if __name__ == "__main__":
    exit(main())
