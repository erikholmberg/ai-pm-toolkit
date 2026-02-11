#!/usr/bin/env python3
"""
Capacity Planning Calculator

Estimate available team capacity given headcount, PTO, holidays, meeting load,
and focus-time assumptions. Outputs developer-days or story-point equivalents
per sprint or per quarter. Supports roadmap feasibility checks.

Usage:
    python capacity-planning-calculator.py --team 6 --sprint-days 10 --pto 2 --meetings 0.2
    python capacity-planning-calculator.py --team 5 --quarter --pto-per-person 8 --holidays 3 --meetings 0.25
    python capacity-planning-calculator.py --team 4 --sprint-days 10 --pto 1.5 --meetings 0.15 --points-per-day 4

Requirements:
    None (stdlib only).
"""

import argparse
import sys
from typing import Optional, Tuple


def available_days(
    team_size: int,
    period_days: int,
    pto_days: float = 0,
    holiday_days: float = 0,
    meeting_load_pct: float = 0.0,
) -> Tuple[float, float]:
    """
    Compute available developer-days in a period.

    Args:
        team_size: Number of developers
        period_days: Working days in the period (e.g. 10 for 2-week sprint)
        pto_days: Total PTO/leave days across team in period
        holiday_days: Company holidays in period
        meeting_load_pct: Fraction of time in meetings (0.2 = 20%)

    Returns:
        (total_developer_days, developer_days_per_person)
    """
    if team_size <= 0 or period_days <= 0:
        return 0.0, 0.0

    # Person-days before deductions
    raw_person_days = team_size * period_days

    # PTO and holidays reduce available person-days
    unavailable = pto_days + (holiday_days * team_size)
    available_person_days = max(0.0, raw_person_days - unavailable)

    # Meeting load reduces effective capacity (meetings affect everyone)
    focus_multiplier = 1.0 - meeting_load_pct
    effective_person_days = available_person_days * focus_multiplier

    per_person = effective_person_days / team_size if team_size > 0 else 0.0

    return round(effective_person_days, 1), round(per_person, 1)


def days_to_story_points(
    developer_days: float,
    points_per_day: float,
) -> float:
    """Convert developer-days to story points using team velocity calibration."""
    if points_per_day <= 0:
        return 0.0
    return round(developer_days * points_per_day, 1)


def main():
    parser = argparse.ArgumentParser(
        description="Estimate team capacity: developer-days and story points per sprint or quarter."
    )
    parser.add_argument(
        "--team", "-t", type=int, required=True,
        help="Number of developers",
    )
    parser.add_argument(
        "--sprint-days", type=int, default=10,
        help="Working days per sprint (default: 10 for 2-week sprint)",
    )
    parser.add_argument(
        "--quarter", action="store_true",
        help="Compute for quarter (~63 working days) instead of sprint",
    )
    parser.add_argument(
        "--pto", "-p", type=float, default=0,
        help="Total PTO/leave days across team in period",
    )
    parser.add_argument(
        "--pto-per-person", type=float,
        help="PTO days per person (multiplied by team size)",
    )
    parser.add_argument(
        "--holidays", type=float, default=0,
        help="Company holidays in period (reduce each person's days)",
    )
    parser.add_argument(
        "--meetings", "-m", type=float, default=0.0,
        help="Meeting load as fraction 0-1 (e.g. 0.2 = 20%% of time in meetings)",
    )
    parser.add_argument(
        "--points-per-day", type=float,
        help="Story points per developer-day (for velocity conversion)",
    )
    parser.add_argument(
        "--buffer", type=float, default=0.0,
        help="Additional buffer as fraction (e.g. 0.1 = 10%% for unplanned work)",
    )
    args = parser.parse_args()

    if args.team <= 0:
        print("Error: --team must be positive.", file=sys.stderr)
        return 1

    period_days = 63 if args.quarter else args.sprint_days  # ~63 working days per quarter

    pto = args.pto
    if args.pto_per_person is not None:
        pto = args.pto_per_person * args.team

    meeting_load = max(0.0, min(1.0, args.meetings))
    buffer = max(0.0, min(1.0, args.buffer))

    dev_days, dev_days_per_person = available_days(
        team_size=args.team,
        period_days=period_days,
        pto_days=pto,
        holiday_days=args.holidays,
        meeting_load_pct=meeting_load,
    )

    # Apply buffer if specified
    if buffer > 0:
        dev_days_buffered = dev_days * (1 - buffer)
    else:
        dev_days_buffered = dev_days

    period_label = "quarter" if args.quarter else "sprint"
    print("\n" + "=" * 70)
    print("📊 CAPACITY PLANNING CALCULATOR")
    print("=" * 70)

    print(f"\n📋 INPUTS:")
    print(f"   • Team size:         {args.team} developers")
    print(f"   • Period:            {period_label} ({period_days} working days)")
    print(f"   • PTO (total):       {pto:.1f} days")
    print(f"   • Holidays:          {args.holidays:.1f} days")
    print(f"   • Meeting load:      {meeting_load:.0%}")
    if buffer > 0:
        print(f"   • Buffer:            {buffer:.0%}")

    print(f"\n📈 CAPACITY:")
    print(f"   • Available:         {dev_days:.1f} developer-days")
    print(f"   • Per developer:      {dev_days_per_person:.1f} days")
    if buffer > 0:
        print(f"   • After buffer:      {dev_days_buffered:.1f} developer-days (for planning)")

    if args.points_per_day and args.points_per_day > 0:
        pts = days_to_story_points(dev_days, args.points_per_day)
        pts_buffered = days_to_story_points(dev_days_buffered, args.points_per_day)
        print(f"\n📐 VELOCITY ESTIMATE ({args.points_per_day} pts/day):")
        print(f"   • Expected output:  ~{pts:.0f} story points")
        if buffer > 0:
            print(f"   • Conservative:      ~{pts_buffered:.0f} story points (with buffer)")

    # Quick reference
    print(f"\n💡 TIPS:")
    print(f"   • Calibrate points_per_day from recent sprint velocity ÷ developer-days")
    print(f"   • Meeting load 20-25%% is common; 30%%+ may indicate overload")
    print(f"   • Add 10%% buffer for bugs, support, unplanned work")
    print("\n" + "=" * 70)

    return 0


if __name__ == "__main__":
    sys.exit(main())
