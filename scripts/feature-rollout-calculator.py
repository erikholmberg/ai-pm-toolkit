#!/usr/bin/env python3
"""
Feature Rollout Calculator

Estimate phased rollout timeline: for each phase (e.g. 1% → 5% → 25% → 100%),
compute daily exposed users and recommended minimum days. Complements
experiment-duration-calculator.py and AI feature launch checklists.

Usage:
    python feature-rollout-calculator.py --daily-volume 100000
    python feature-rollout-calculator.py --daily-volume 50000 --phases 1 5 10 25 50 100
    python feature-rollout-calculator.py --daily-volume 100000 --min-days-per-phase 7

Requirements:
    None (stdlib only).
"""

import argparse
import sys
from typing import List


def rollout_phases(
    daily_volume: int,
    phase_pcts: List[float],
    min_days_per_phase: int,
) -> List[dict]:
    """
    For each phase, return percentage, daily exposed users, min days, and cumulative days.

    Args:
        daily_volume: Total daily users or requests.
        phase_pcts: Traffic percentages per phase (e.g. [1, 5, 25, 100]).
        min_days_per_phase: Minimum days to hold each phase before advancing.

    Returns:
        List of dicts with phase_num, pct, daily_exposed, min_days, cumulative_days.
    """
    if not phase_pcts or daily_volume <= 0:
        return []
    cumulative = 0
    result = []
    for i, pct in enumerate(phase_pcts, 1):
        daily_exposed = max(0, int(daily_volume * (pct / 100)))
        cumulative += min_days_per_phase
        result.append({
            "phase_num": i,
            "pct": pct,
            "daily_exposed": daily_exposed,
            "min_days": min_days_per_phase,
            "cumulative_days": cumulative,
        })
    return result


def main():
    parser = argparse.ArgumentParser(
        description="Phased feature rollout: timeline and daily exposed users per phase."
    )
    parser.add_argument(
        "--daily-volume",
        "-d",
        type=int,
        required=True,
        help="Total daily users or requests (traffic to the feature surface)",
    )
    parser.add_argument(
        "--phases",
        "-p",
        type=float,
        nargs="+",
        default=[1.0, 5.0, 25.0, 100.0],
        help="Rollout percentages per phase (default: 1 5 25 100)",
    )
    parser.add_argument(
        "--min-days-per-phase",
        type=int,
        default=3,
        help="Minimum days to hold each phase before advancing (default: 3)",
    )
    args = parser.parse_args()

    if args.daily_volume < 1:
        print("Error: --daily-volume must be >= 1", file=sys.stderr)
        return 1
    if args.min_days_per_phase < 1:
        print("Error: --min-days-per-phase must be >= 1", file=sys.stderr)
        return 1
    invalid = [p for p in args.phases if not (0 < p <= 100)]
    if invalid:
        print("Error: all --phases must be in (0, 100]", file=sys.stderr)
        return 1

    phases = sorted(args.phases)
    rows = rollout_phases(args.daily_volume, phases, args.min_days_per_phase)
    total_days = rows[-1]["cumulative_days"] if rows else 0

    print("\n" + "=" * 70)
    print("FEATURE ROLLOUT TIMELINE")
    print("=" * 70)
    print(f"\n  Daily volume:       {args.daily_volume:,}")
    print(f"  Min days per phase: {args.min_days_per_phase}")
    print(f"  Phases:             {phases}")
    print()
    print(f"  {'Phase':<8}  {'% traffic':>10}  {'Daily exposed':>14}  {'Min days':>10}  {'Cumulative days':>16}")
    print("  " + "-" * 64)
    for r in rows:
        print(f"  {r['phase_num']:<8}  {r['pct']:>9.1f}%  {r['daily_exposed']:>14,}  {r['min_days']:>10}  {r['cumulative_days']:>16}")
    print("  " + "-" * 64)
    print(f"\n  Total time to 100%: ~{total_days} days (~{total_days / 7:.1f} weeks)")
    print("\n  Use with launch/ai-feature-launch-checklist.md; adjust phases for risk.")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    sys.exit(main())
