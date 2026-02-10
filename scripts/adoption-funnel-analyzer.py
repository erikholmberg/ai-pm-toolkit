#!/usr/bin/env python3
"""
Adoption Funnel Analyzer

Given step-by-step funnel counts, calculate conversion rates, drop-off points,
and (optionally) statistical significance of changes between two periods.
AI features often have unique activation funnels (e.g. onboarding → first prompt
→ successful result → repeat use); this tool makes funnel analysis fast.

Usage:
    python adoption-funnel-analyzer.py --steps "Visit:10000" "Signup:4000" "First Prompt:2500" "Repeat:800"
    python adoption-funnel-analyzer.py --steps "Visit:10000" "Signup:4000" "Activate:2500" --compare "Visit:9500" "Signup:4200" "Activate:2800"
    python adoption-funnel-analyzer.py --csv funnel.csv

CSV format (header row required):
    step,count
    Visit,10000
    Signup,4000
    ...

Or for comparison:
    step,period_a,period_b
    Visit,10000,9500
    Signup,4000,4200
    ...

Requirements:
    None (stdlib only). Optional: scipy for significance testing.
"""

import argparse
import csv
import math
import sys
from typing import Dict, List, Optional, Tuple



def parse_step(s: str) -> Tuple[str, int]:
    """Parse 'StepName:count' into (name, count)."""
    parts = s.rsplit(":", 1)
    if len(parts) != 2:
        raise ValueError(f"Invalid step format '{s}'. Expected 'Name:count'.")
    name = parts[0].strip()
    count = int(parts[1].strip())
    return name, count


def load_csv_single(path: str) -> List[Tuple[str, int]]:
    """Load step,count CSV."""
    steps: List[Tuple[str, int]] = []
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = row.get("step", "").strip()
            count = int(row.get("count", 0))
            steps.append((name, count))
    return steps


def load_csv_compare(path: str) -> Tuple[List[Tuple[str, int]], List[Tuple[str, int]]]:
    """Load step,period_a,period_b CSV."""
    a: List[Tuple[str, int]] = []
    b: List[Tuple[str, int]] = []
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = row.get("step", "").strip()
            a.append((name, int(row.get("period_a", 0))))
            b.append((name, int(row.get("period_b", 0))))
    return a, b


def conversion_rate(from_count: int, to_count: int) -> Optional[float]:
    """Step-to-step conversion rate as percentage."""
    if from_count <= 0:
        return None
    return 100.0 * to_count / from_count


def overall_conversion(first: int, last: int) -> Optional[float]:
    """End-to-end conversion rate."""
    if first <= 0:
        return None
    return 100.0 * last / first


def biggest_drop_index(steps: List[Tuple[str, int]]) -> Optional[int]:
    """Find the step transition with the largest absolute drop-off."""
    if len(steps) < 2:
        return None
    max_drop = 0
    max_idx = 0
    for i in range(len(steps) - 1):
        drop = steps[i][1] - steps[i + 1][1]
        if drop > max_drop:
            max_drop = drop
            max_idx = i
    return max_idx


def proportion_z_test(
    count_a: int, total_a: int,
    count_b: int, total_b: int,
) -> Tuple[float, float]:
    """
    Two-proportion z-test for comparing conversion rates.
    Returns (z_statistic, p_value).
    Requires scipy for p-value; returns p=-1 without it.
    """
    if total_a <= 0 or total_b <= 0:
        return 0.0, -1.0

    p1 = count_a / total_a
    p2 = count_b / total_b
    p_pool = (count_a + count_b) / (total_a + total_b)

    se = math.sqrt(p_pool * (1 - p_pool) * (1 / total_a + 1 / total_b))
    if se == 0:
        return 0.0, -1.0

    z = (p1 - p2) / se

    try:
        from scipy import stats as sp_stats
        p_value = 2 * (1 - sp_stats.norm.cdf(abs(z)))
        return z, p_value
    except ImportError:
        return z, -1.0


def print_funnel(steps: List[Tuple[str, int]], label: str = "FUNNEL") -> None:
    """Print a single funnel analysis."""
    if not steps:
        return

    first_count = steps[0][1]
    max_name_len = max(len(s[0]) for s in steps)

    print(f"\n📈 {label}:")
    for i, (name, count) in enumerate(steps):
        # Step-to-step conversion
        if i == 0:
            step_conv = "—"
            drop = "—"
        else:
            prev_count = steps[i - 1][1]
            rate = conversion_rate(prev_count, count)
            step_conv = f"{rate:.1f}%" if rate is not None else "—"
            dropped = prev_count - count
            drop = f"-{dropped:,}"

        # Overall conversion from top
        overall = conversion_rate(first_count, count)
        overall_str = f"{overall:.1f}%" if overall is not None else "—"

        # Visual bar
        bar_len = int(40 * count / first_count) if first_count > 0 else 0
        bar = "█" * bar_len + "░" * (40 - bar_len)

        print(f"   {name:<{max_name_len}}  {count:>10,}  {bar}  step: {step_conv:>6}  overall: {overall_str:>6}  {drop:>8}")

    # Biggest drop-off
    drop_idx = biggest_drop_index(steps)
    if drop_idx is not None:
        from_step = steps[drop_idx]
        to_step = steps[drop_idx + 1]
        dropped = from_step[1] - to_step[1]
        drop_pct = 100 * dropped / from_step[1] if from_step[1] > 0 else 0
        print(f"\n   ⚠️  Biggest drop-off: {from_step[0]} → {to_step[0]}")
        print(f"      Lost {dropped:,} users ({drop_pct:.1f}% of {from_step[0]})")

    # Overall
    oc = overall_conversion(first_count, steps[-1][1])
    if oc is not None:
        print(f"\n   📊 End-to-end conversion: {oc:.2f}% ({steps[0][0]} → {steps[-1][0]})")


def print_comparison(
    steps_a: List[Tuple[str, int]],
    steps_b: List[Tuple[str, int]],
) -> None:
    """Print comparison between two periods."""
    if not steps_a or not steps_b:
        return

    print(f"\n📊 PERIOD COMPARISON:")
    max_name_len = max(
        max(len(s[0]) for s in steps_a),
        max(len(s[0]) for s in steps_b),
    )

    for i in range(min(len(steps_a), len(steps_b))):
        name_a, count_a = steps_a[i]
        name_b, count_b = steps_b[i]
        name = name_a  # assume same step names

        if i == 0:
            conv_a_str = conv_b_str = "—"
            sig_str = ""
        else:
            prev_a = steps_a[i - 1][1]
            prev_b = steps_b[i - 1][1]
            conv_a = conversion_rate(prev_a, count_a)
            conv_b = conversion_rate(prev_b, count_b)
            conv_a_str = f"{conv_a:.1f}%" if conv_a is not None else "—"
            conv_b_str = f"{conv_b:.1f}%" if conv_b is not None else "—"

            # Significance test
            z, p = proportion_z_test(count_a, prev_a, count_b, prev_b)
            if p >= 0:
                sig_str = f"  p={p:.3f}" + (" *" if p < 0.05 else "")
            elif abs(z) > 0:
                sig_str = f"  z={z:.2f}"
            else:
                sig_str = ""

        diff = count_b - count_a
        diff_pct = 100 * diff / count_a if count_a > 0 else 0
        arrow = "↑" if diff > 0 else ("↓" if diff < 0 else "→")

        print(f"   {name:<{max_name_len}}  A: {count_a:>9,} ({conv_a_str:>6})  B: {count_b:>9,} ({conv_b_str:>6})  {arrow} {diff:+,} ({diff_pct:+.1f}%){sig_str}")

    # Overall comparison
    oc_a = overall_conversion(steps_a[0][1], steps_a[-1][1])
    oc_b = overall_conversion(steps_b[0][1], steps_b[-1][1])
    if oc_a is not None and oc_b is not None:
        delta = oc_b - oc_a
        print(f"\n   End-to-end: Period A {oc_a:.2f}% → Period B {oc_b:.2f}% ({delta:+.2f}pp)")


def main():
    parser = argparse.ArgumentParser(
        description="Analyze adoption funnels: conversion rates, drop-off, and period comparison."
    )
    parser.add_argument(
        "--steps", nargs="+",
        help="Funnel steps as 'Name:count' pairs (e.g. 'Visit:10000' 'Signup:4000')",
    )
    parser.add_argument(
        "--compare", nargs="+",
        help="Second period steps for comparison (same format as --steps)",
    )
    parser.add_argument(
        "--csv", type=str,
        help="CSV file (columns: step,count or step,period_a,period_b)",
    )
    args = parser.parse_args()

    steps_a: List[Tuple[str, int]] = []
    steps_b: List[Tuple[str, int]] = []

    if args.csv:
        try:
            # Detect format by reading header
            with open(args.csv, newline="") as f:
                reader = csv.DictReader(f)
                if reader.fieldnames and "period_a" in reader.fieldnames:
                    steps_a, steps_b = load_csv_compare(args.csv)
                else:
                    steps_a = load_csv_single(args.csv)
        except Exception as e:
            print(f"Error reading CSV: {e}", file=sys.stderr)
            return 1
    elif args.steps:
        try:
            steps_a = [parse_step(s) for s in args.steps]
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1
        if args.compare:
            try:
                steps_b = [parse_step(s) for s in args.compare]
            except ValueError as e:
                print(f"Error: {e}", file=sys.stderr)
                return 1
    else:
        parser.print_help()
        print("\nExample: --steps 'Visit:10000' 'Signup:4000' 'First Use:2500' 'Repeat:800'", file=sys.stderr)
        return 0

    if not steps_a:
        print("Error: no funnel data provided.", file=sys.stderr)
        return 1

    print("\n" + "=" * 100)
    print("📊 ADOPTION FUNNEL ANALYSIS")
    print("=" * 100)

    if steps_b:
        print_funnel(steps_a, "PERIOD A")
        print_funnel(steps_b, "PERIOD B")
        print_comparison(steps_a, steps_b)
    else:
        print_funnel(steps_a, "FUNNEL")

    print("\n" + "=" * 100)
    return 0


if __name__ == "__main__":
    sys.exit(main())
