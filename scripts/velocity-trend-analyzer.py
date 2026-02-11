#!/usr/bin/env python3
"""
Velocity Trend Analyzer

Compute velocity trends from sprint story points (or equivalent) over time.
Calculates rolling average, trend direction (up/down/flat), confidence intervals,
and flags concerning drops. Complements jira-sprint-retrospective prompt and
roadmap forecasting.

Usage:
    python velocity-trend-analyzer.py --sprints 38 42 35 45 40 48
    python velocity-trend-analyzer.py --csv sprints.csv --sprint-column points --date-column end_date
    python velocity-trend-analyzer.py --sprints 30 32 28 35 33 --window 3 --target 40

CSV format (header row required):
    sprint,points,end_date
    Sprint 45,38,2025-01-17
    Sprint 46,42,2025-01-31
    ...

Requirements:
    None (stdlib only). Optional: scipy for confidence intervals.
"""

import argparse
import csv
import math
import sys
from typing import Dict, List, Optional, Tuple


def load_from_csv(
    path: str,
    points_column: str = "points",
    date_column: Optional[str] = None,
) -> List[Tuple[Optional[str], float]]:
    """Load (sprint_id, points) pairs from CSV. Returns list ordered by row."""
    rows: List[Tuple[Optional[str], float]] = []
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                pts = float(row[points_column])
            except (KeyError, ValueError):
                continue
            sid = row.get("sprint") or row.get("sprint_id") or row.get("date") or row.get(date_column or "date")
            rows.append((sid, pts))
    return rows


def rolling_average(values: List[float], window: int) -> List[Optional[float]]:
    """Rolling average. Returns None for positions before window fills."""
    result: List[Optional[float]] = []
    for i in range(len(values)):
        if i < window - 1:
            result.append(None)
        else:
            slice_vals = values[i - window + 1 : i + 1]
            result.append(sum(slice_vals) / len(slice_vals))
    return result


def linear_trend(values: List[float]) -> Tuple[float, str]:
    """
    Simple linear regression slope (per-period change).
    Returns (slope, direction_label).
    """
    n = len(values)
    if n < 2:
        return 0.0, "insufficient data"

    x_mean = (n - 1) / 2
    y_mean = sum(values) / n

    numerator = sum((i - x_mean) * (v - y_mean) for i, v in enumerate(values))
    denominator = sum((i - x_mean) ** 2 for i in range(n))
    slope = numerator / denominator if denominator != 0 else 0.0

    if slope > 0.5:
        direction = "increasing"
    elif slope < -0.5:
        direction = "decreasing"
    else:
        direction = "flat"

    return slope, direction


def confidence_interval(
    values: List[float],
    confidence: float = 0.95,
) -> Optional[Tuple[float, float]]:
    """95% CI for the mean. Returns (lower, upper) or None if scipy unavailable."""
    n = len(values)
    if n < 2:
        return None

    mean = sum(values) / n
    variance = sum((x - mean) ** 2 for x in values) / (n - 1)
    std_err = math.sqrt(variance / n)

    try:
        from scipy import stats
        t_val = stats.t.ppf((1 + confidence) / 2, df=n - 1)
        margin = t_val * std_err
        return (mean - margin, mean + margin)
    except ImportError:
        # Fallback: approximate with 1.96 for large n
        if n >= 30:
            margin = 1.96 * std_err
            return (mean - margin, mean + margin)
        return None


def trend_report(
    points: List[float],
    sprint_ids: Optional[List[str]] = None,
    window: int = 3,
    target: Optional[float] = None,
    confidence: float = 0.95,
) -> Dict:
    """Generate a full trend report."""
    n = len(points)
    mean = sum(points) / n if n else 0
    slope, direction = linear_trend(points)
    rolling = rolling_average(points, window)

    # Last rolling avg
    last_rolling = None
    for r in reversed(rolling):
        if r is not None:
            last_rolling = r
            break

    # CI for overall mean
    ci = confidence_interval(points, confidence)

    # Count sprints below target
    below_target = sum(1 for p in points if target is not None and p < target) if target else 0
    hit_rate = 100 * (n - below_target) / n if target and n else None

    # Detect significant drop (last sprint vs recent avg)
    drop_flag = False
    drop_pct = None
    if n >= 2 and last_rolling and last_rolling > 0:
        last_val = points[-1]
        if last_val < last_rolling * 0.85:  # 15% drop
            drop_flag = True
            drop_pct = 100 * (last_rolling - last_val) / last_rolling

    return {
        "n_sprints": n,
        "sprint_ids": sprint_ids,
        "points": points,
        "mean": mean,
        "rolling_window": window,
        "rolling_avg": rolling,
        "last_rolling_avg": last_rolling,
        "slope": slope,
        "trend_direction": direction,
        "confidence_interval": ci,
        "target": target,
        "below_target_count": below_target if target else None,
        "hit_rate_pct": hit_rate,
        "drop_detected": drop_flag,
        "drop_pct": drop_pct,
    }


def print_report(report: Dict) -> None:
    """Pretty-print velocity trend report."""
    r = report
    n = r["n_sprints"]
    points = r["points"]
    sprint_ids = r["sprint_ids"] or [f"S{i+1}" for i in range(n)]

    print("\n" + "=" * 70)
    print("📊 VELOCITY TREND ANALYZER")
    print("=" * 70)

    print(f"\n📋 OVERVIEW:")
    print(f"   • Sprints analyzed:  {n}")
    print(f"   • Rolling window:    {r['rolling_window']}")
    if r["target"]:
        print(f"   • Target velocity:   {r['target']} points")
        print(f"   • Hit rate:         {r['hit_rate_pct']:.0f}% ({n - r['below_target_count']}/{n} sprints)")

    print(f"\n📈 RAW VELOCITY:")
    for i, (sid, pt) in enumerate(zip(sprint_ids, points)):
        bar_len = int(40 * pt / max(points)) if max(points) > 0 else 0
        bar = "█" * bar_len + "░" * (40 - bar_len)
        rolling_str = f"  → rolling: {r['rolling_avg'][i]:.1f}" if r["rolling_avg"][i] is not None else ""
        target_mark = " ⚠️ below target" if r["target"] and pt < r["target"] else ""
        print(f"   {str(sid):<12}  {pt:>6.1f}  {bar}{rolling_str}{target_mark}")

    print(f"\n📐 STATISTICS:")
    print(f"   • Mean velocity:    {r['mean']:.1f} points")
    if r["last_rolling_avg"] is not None:
        print(f"   • Recent avg ({r['rolling_window']} sprints): {r['last_rolling_avg']:.1f} points")
    print(f"   • Trend:            {r['trend_direction']} (slope: {r['slope']:+.2f} points/sprint)")
    if r["confidence_interval"]:
        lo, hi = r["confidence_interval"]
        print(f"   • 95% CI for mean:  [{lo:.1f}, {hi:.1f}]")

    if r["drop_detected"]:
        print(f"\n⚠️  DROP DETECTED:")
        print(f"   Last sprint ({points[-1]:.0f}) is ~{r['drop_pct']:.0f}% below recent average.")
        print(f"   Consider discussing in next retrospective: blockers, scope creep, context switching?")

    # Forecast note
    if r["trend_direction"] == "increasing" and r["last_rolling_avg"] is not None:
        print(f"\n📈 FORECAST:")
        print(f"   Velocity trending up. Next sprint prediction: ~{r['last_rolling_avg']:.0f}–{r['last_rolling_avg'] + r['slope']:.0f} points")
    elif r["trend_direction"] == "decreasing" and r["last_rolling_avg"] is not None:
        print(f"\n📉 FORECAST:")
        print(f"   Velocity trending down. Investigate causes before planning assumes prior levels.")

    print("\n" + "=" * 70)


def main():
    parser = argparse.ArgumentParser(
        description="Analyze sprint velocity trends: rolling average, trend direction, confidence intervals."
    )
    parser.add_argument(
        "--sprints", "-s", type=float, nargs="+",
        help="Story points per sprint (ordered oldest to newest)",
    )
    parser.add_argument(
        "--csv", type=str,
        help="CSV file with sprint and points columns",
    )
    parser.add_argument(
        "--points-column", default="points",
        help="Column name for story points (default: points)",
    )
    parser.add_argument(
        "--window", "-w", type=int, default=3,
        help="Rolling average window in sprints (default: 3)",
    )
    parser.add_argument(
        "--target", "-t", type=float,
        help="Target velocity (for hit rate and below-target flags)",
    )
    parser.add_argument(
        "--confidence", type=float, default=0.95,
        help="Confidence level for CI (default: 0.95)",
    )
    parser.add_argument(
        "--output", "-o", type=str,
        help="Write report JSON to file",
    )
    args = parser.parse_args()

    points: List[float] = []
    sprint_ids: Optional[List[str]] = []

    if args.csv:
        try:
            rows = load_from_csv(args.csv, args.points_column)
            sprint_ids = [r[0] for r in rows if r[0]]
            points = [r[1] for r in rows]
        except Exception as e:
            print(f"Error reading CSV: {e}", file=sys.stderr)
            return 1
    elif args.sprints:
        points = list(args.sprints)
        sprint_ids = None
    else:
        parser.print_help()
        print("\nExample: --sprints 38 42 35 45 40 48 --window 3 --target 45", file=sys.stderr)
        return 0

    if len(points) < 2:
        print("Error: need at least 2 sprints to analyze.", file=sys.stderr)
        return 1

    if args.window < 1 or args.window > len(points):
        print("Error: --window must be between 1 and number of sprints.", file=sys.stderr)
        return 1

    report = trend_report(
        points,
        sprint_ids=sprint_ids,
        window=args.window,
        target=args.target,
        confidence=args.confidence,
    )

    if report["confidence_interval"]:
        report["confidence_interval"] = list(report["confidence_interval"])

    print_report(report)

    if args.output:
        import json
        with open(args.output, "w") as f:
            json.dump(report, f, indent=2)
        print(f"Report saved to {args.output}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
