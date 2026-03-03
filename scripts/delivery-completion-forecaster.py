#!/usr/bin/env python3
"""
Delivery / Completion Forecaster

Estimate when a backlog will be done using historical velocity or throughput
and confidence intervals (50%, 80%, 90%). Complements sprint-velocity-tracker
and capacity-planner: answers "when will we finish this scope?"

Supports:
    - Points-based: backlog in story points, history in points/sprint
    - Items-based: backlog in item count, history in items/week
    - CSV of past sprints or weekly throughput
    - Configurable sprint length and start date

Usage:
    # Points backlog, velocity from last 6 sprints
    python delivery-completion-forecaster.py --backlog 180 --velocity 34 38 36 41 39 42

    # From CSV (sprint, completed points)
    python delivery-completion-forecaster.py --backlog 200 --csv velocity.csv

    # Items backlog, throughput in items/week
    python delivery-completion-forecaster.py --backlog 24 --mode items --throughput 4 5 3 6 4 5

    # Custom sprint length and start date
    python delivery-completion-forecaster.py --backlog 120 --velocity 35 40 38 \\
        --sprint-days 14 --start 2025-08-01

    # Output JSON
    python delivery-completion-forecaster.py --backlog 180 --csv velocity.csv --output forecast.json

CSV format (points mode):
    sprint,completed,points
    S1,34,
    S2,38,
    Use "completed" or "points" column for velocity per sprint.

CSV format (items mode):
    week,items_completed,throughput
    2025-W01,5,
    Use "items_completed" or "throughput" column for items per period.

Requirements:
    None (stdlib only).
"""

import argparse
import csv
import json
import sys
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Percentile and forecast
# ---------------------------------------------------------------------------

def percentile_sorted(sorted_vals: List[float], p: float) -> float:
    """Linear interpolation percentile. p in 0..100."""
    if not sorted_vals:
        return 0.0
    n = len(sorted_vals)
    idx = p / 100.0 * (n - 1)
    lo = int(idx)
    hi = min(lo + 1, n - 1)
    w = idx - lo
    return sorted_vals[lo] * (1 - w) + sorted_vals[hi] * w


def velocity_distribution(velocities: List[float]) -> Dict[str, float]:
    """Compute mean, median, p10, p20, p80, p90 of velocity."""
    if not velocities:
        return {}
    sorted_v = sorted(velocities)
    n = len(sorted_v)
    return {
        "mean": sum(velocities) / n,
        "median": percentile_sorted(sorted_v, 50),
        "p10": percentile_sorted(sorted_v, 10),
        "p20": percentile_sorted(sorted_v, 20),
        "p80": percentile_sorted(sorted_v, 80),
        "p90": percentile_sorted(sorted_v, 90),
        "min": sorted_v[0],
        "max": sorted_v[-1],
    }


def forecast_completion(
    backlog: float,
    velocities: List[float],
    sprint_days: int = 14,
    start_date: Optional[datetime] = None,
) -> Dict[str, Any]:
    """
    Forecast completion using velocity distribution.
    Lower velocity → more sprints → later date. So we use p10/p20 for conservative (80/90%) estimates.
    """
    if not velocities or backlog <= 0:
        return {"error": "Need positive backlog and at least one velocity value"}

    dist = velocity_distribution(velocities)
    if start_date is None:
        start_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

    # Sprints needed = backlog / velocity. Higher velocity → fewer sprints.
    # p50: median velocity → median sprints
    # p80: we want 80% confidence we're done by then → use slower velocity (p20) so more sprints
    # p90: use p10 velocity
    med_vel = dist["median"]
    p20_vel = dist["p20"]
    p10_vel = dist["p10"]

    sprints_p50 = backlog / med_vel if med_vel > 0 else 0
    sprints_p80 = backlog / p20_vel if p20_vel > 0 else 0
    sprints_p90 = backlog / p10_vel if p10_vel > 0 else 0

    def date_from_sprints(sprints: float) -> str:
        days = int(round(sprints * sprint_days))
        d = start_date + timedelta(days=days)
        return d.strftime("%Y-%m-%d")

    return {
        "backlog": backlog,
        "unit": "points",
        "sprint_days": sprint_days,
        "start_date": start_date.strftime("%Y-%m-%d"),
        "velocity_distribution": dist,
        "n_sprints_historical": len(velocities),
        "forecast": {
            "p50": {
                "sprints_needed": round(sprints_p50, 1),
                "completion_date": date_from_sprints(sprints_p50),
                "velocity_used": round(med_vel, 1),
            },
            "p80": {
                "sprints_needed": round(sprints_p80, 1),
                "completion_date": date_from_sprints(sprints_p80),
                "velocity_used": round(p20_vel, 1),
            },
            "p90": {
                "sprints_needed": round(sprints_p90, 1),
                "completion_date": date_from_sprints(sprints_p90),
                "velocity_used": round(p10_vel, 1),
            },
        },
    }


def forecast_completion_items(
    backlog: float,
    throughputs: List[float],
    start_date: Optional[datetime] = None,
) -> Dict[str, Any]:
    """Forecast completion in items mode: throughput = items per week."""
    if not throughputs or backlog <= 0:
        return {"error": "Need positive backlog and at least one throughput value"}

    dist = velocity_distribution(throughputs)  # same stats
    if start_date is None:
        start_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

    med_t = dist["median"]
    p20_t = dist["p20"]
    p10_t = dist["p10"]

    weeks_p50 = backlog / med_t if med_t > 0 else 0
    weeks_p80 = backlog / p20_t if p20_t > 0 else 0
    weeks_p90 = backlog / p10_t if p10_t > 0 else 0

    def date_from_weeks(weeks: float) -> str:
        days = int(round(weeks * 7))
        d = start_date + timedelta(days=days)
        return d.strftime("%Y-%m-%d")

    return {
        "backlog": backlog,
        "unit": "items",
        "sprint_days": 7,
        "start_date": start_date.strftime("%Y-%m-%d"),
        "velocity_distribution": dist,
        "n_periods_historical": len(throughputs),
        "forecast": {
            "p50": {
                "weeks_needed": round(weeks_p50, 1),
                "completion_date": date_from_weeks(weeks_p50),
                "throughput_used": round(med_t, 1),
            },
            "p80": {
                "weeks_needed": round(weeks_p80, 1),
                "completion_date": date_from_weeks(weeks_p80),
                "throughput_used": round(p20_t, 1),
            },
            "p90": {
                "weeks_needed": round(weeks_p90, 1),
                "completion_date": date_from_weeks(weeks_p90),
                "throughput_used": round(p10_t, 1),
            },
        },
    }


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def _col(fieldnames: List[str], *aliases: str) -> Optional[str]:
    lower_map = {f.lower().strip(): f for f in fieldnames}
    for alias in aliases:
        key = alias.lower().strip()
        if key in lower_map:
            return lower_map[key]
    return None


def load_velocity_csv(path: str) -> List[float]:
    """Load velocity (points per sprint) from CSV."""
    vals: List[float] = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fields = reader.fieldnames or []
        c_points = _col(fields, "completed", "points", "velocity", "story_points", "done")
        for row in reader:
            raw = row.get(c_points or "completed", "").strip()
            if not raw:
                continue
            try:
                vals.append(float(raw.replace(",", "")))
            except ValueError:
                continue
    return vals


def load_throughput_csv(path: str) -> List[float]:
    """Load throughput (items per week) from CSV."""
    vals: List[float] = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fields = reader.fieldnames or []
        c_items = _col(fields, "items_completed", "throughput", "items", "count", "completed")
        for row in reader:
            raw = row.get(c_items or "items_completed", "").strip()
            if not raw:
                continue
            try:
                vals.append(float(raw.replace(",", "")))
            except ValueError:
                continue
    return vals


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def print_report(result: Dict[str, Any], mode: str) -> None:
    """Pretty-print forecast."""
    if result.get("error"):
        print(f"\n   ⚠️  {result['error']}\n")
        return

    unit = result.get("unit", "points")
    backlog = result["backlog"]
    dist = result.get("velocity_distribution", {})
    fc = result.get("forecast", {})

    print("\n" + "=" * 78)
    print("📅 DELIVERY / COMPLETION FORECAST")
    print("=" * 78)

    print(f"\n   Backlog:        {backlog:.0f} {unit}")
    print(f"   Start date:    {result['start_date']}")
    if unit == "points":
        print(f"   Sprint length: {result['sprint_days']} days")
    print(f"   History:       {result.get('n_sprints_historical', result.get('n_periods_historical', 0))} periods")

    print(f"\n   Velocity/throughput:  mean {dist.get('mean', 0):.1f}  median {dist.get('median', 0):.1f}  "
          f"min {dist.get('min', 0):.1f}  max {dist.get('max', 0):.1f}")

    print(f"\n{'─'*78}")
    print(f"\n   FORECAST:\n")
    if unit == "points":
        print(f"   {'Confidence':<12} {'Sprints needed':>14} {'Completion date':>16}  (velocity used)")
        print(f"   {'─'*12} {'─'*14} {'─'*16}  {'─'*18}")
        for label, pct in [("50%", "p50"), ("80%", "p80"), ("90%", "p90")]:
            x = fc.get(pct, {})
            print(f"   {label:<12} {x.get('sprints_needed', 0):>14.1f} {x.get('completion_date', ''):>16}  "
                  f"({x.get('velocity_used', 0):.1f} pts/sprint)")
    else:
        print(f"   {'Confidence':<12} {'Weeks needed':>14} {'Completion date':>16}  (throughput used)")
        print(f"   {'─'*12} {'─'*14} {'─'*16}  {'─'*18}")
        for label, pct in [("50%", "p50"), ("80%", "p80"), ("90%", "p90")]:
            x = fc.get(pct, {})
            print(f"   {label:<12} {x.get('weeks_needed', 0):>14.1f} {x.get('completion_date', ''):>16}  "
                  f"({x.get('throughput_used', 0):.1f} items/week)")

    print(f"\n{'─'*78}")
    print(f"\n   💡 Use 80–90% for commitments; 50% for best-case planning.")
    print(f"   Complements: sprint-velocity-tracker, capacity-planner, velocity-trend-analyzer")
    print("\n" + "=" * 78)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_date(s: str) -> Optional[datetime]:
    if not s or not s.strip():
        return None
    s = s.strip()
    for fmt in ["%Y-%m-%d", "%Y/%m/%d", "%m/%d/%Y"]:
        try:
            return datetime.strptime(s[:10], fmt)
        except ValueError:
            continue
    return None


def main():
    parser = argparse.ArgumentParser(
        description="Estimate completion date for a backlog using historical velocity or "
                    "throughput and confidence intervals (50%, 80%, 90%).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --backlog 180 --velocity 34 38 36 41 39 42
  %(prog)s --backlog 200 --csv velocity.csv --sprint-days 14
  %(prog)s --backlog 24 --mode items --throughput 4 5 3 6 4 5 --start 2025-08-01
        """,
    )

    parser.add_argument("--backlog", type=float, required=True, help="Backlog size (points or item count)")
    parser.add_argument("--mode", type=str, default="points", choices=["points", "items"],
                        help="points = story points/sprint, items = items/week")
    parser.add_argument("--velocity", type=float, nargs="*", help="Historical velocity (points per sprint)")
    parser.add_argument("--throughput", type=float, nargs="*", help="Historical throughput (items per week)")
    parser.add_argument("--csv", "-c", type=str, help="CSV file with completed points or items per period")
    parser.add_argument("--sprint-days", type=int, default=14, help="Sprint length in days (points mode)")
    parser.add_argument("--start", type=str, help="Start date (YYYY-MM-DD). Default: today")
    parser.add_argument("--output", "-o", type=str, help="Write JSON results to file")
    args = parser.parse_args()

    start_dt = parse_date(args.start) if args.start else None

    if args.mode == "items":
        if args.throughput:
            throughputs = args.throughput
        elif args.csv:
            try:
                throughputs = load_throughput_csv(args.csv)
            except Exception as e:
                print(f"Error loading CSV: {e}", file=sys.stderr)
                return 1
        else:
            print("Error: provide --throughput or --csv for items mode.", file=sys.stderr)
            return 1
        if not throughputs:
            print("Error: no throughput values found.", file=sys.stderr)
            return 1
        result = forecast_completion_items(args.backlog, throughputs, start_date=start_dt)
    else:
        if args.velocity:
            velocities = args.velocity
        elif args.csv:
            try:
                velocities = load_velocity_csv(args.csv)
            except Exception as e:
                print(f"Error loading CSV: {e}", file=sys.stderr)
                return 1
        else:
            print("Error: provide --velocity or --csv for points mode.", file=sys.stderr)
            return 1
        if not velocities:
            print("Error: no velocity values found.", file=sys.stderr)
            return 1
        result = forecast_completion(args.backlog, velocities, sprint_days=args.sprint_days, start_date=start_dt)

    print_report(result, args.mode)

    if args.output and not result.get("error"):
        with open(args.output, "w") as f:
            json.dump(result, f, indent=2)
        print(f"\n📁 Results saved to {args.output}")

    return 0 if not result.get("error") else 1


if __name__ == "__main__":
    sys.exit(main())
