#!/usr/bin/env python3
"""
Sprint Burndown Checker

Compare actual burndown (CSV of daily remaining points) to an ideal linear
burndown. Reports on track / behind / ahead and optional per-day comparison
and a simple text chart.

Usage:
    # CSV with date and remaining points
    python sprint-burndown-checker.py --csv burndown.csv

    # Specify sprint length and total committed (if not in CSV)
    python sprint-burndown-checker.py --csv burndown.csv --sprint-days 14 --total 55

    # Show ASCII chart by day
    python sprint-burndown-checker.py --csv burndown.csv --chart

    # Export report
    python sprint-burndown-checker.py --csv burndown.csv --markdown report.md --output report.json

CSV format:
    date,remaining_points
    2025-02-01,55
    2025-02-02,52
    2025-02-03,48

    Required: date, remaining_points (or remaining_estimate)
    Optional: total (sprint start total; if missing, first row's remaining is used)

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
# Date parsing
# ---------------------------------------------------------------------------

def parse_date(s: str) -> Optional[datetime]:
    if not s or not s.strip():
        return None
    s = s.strip()[:32]
    for fmt, trim in [
        ("%Y-%m-%dT%H:%M:%S", 19),
        ("%Y-%m-%d %H:%M:%S", 19),
        ("%Y-%m-%d", 10),
        ("%Y/%m/%d", 10),
        ("%m/%d/%Y", 10),
        ("%d/%m/%Y", 10),
    ]:
        try:
            return datetime.strptime(s[:trim].strip(), fmt)
        except ValueError:
            continue
    return None


def _col(fieldnames: List[str], *aliases: str) -> Optional[str]:
    lower_map = {f.lower().strip(): f for f in fieldnames}
    for alias in aliases:
        if alias.lower().strip() in lower_map:
            return lower_map[alias.lower().strip()]
    return None


# ---------------------------------------------------------------------------
# Load burndown CSV
# ---------------------------------------------------------------------------

def load_burndown_csv(
    path: str,
    date_col: str = "date",
    remaining_col: str = "remaining_points",
    total_col: str = "total",
) -> Tuple[List[Dict[str, Any]], Optional[float]]:
    """Load burndown snapshots from CSV. Returns (rows, optional_total_from_csv)."""
    rows: List[Dict[str, Any]] = []
    total_from_csv: Optional[float] = None
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fields = reader.fieldnames or []

        c_date = _col(fields, date_col, "date", "day", "timestamp", "datetime")
        c_remaining = _col(
            fields,
            remaining_col,
            "remaining_points",
            "remaining_estimate",
            "remaining",
            "points_remaining",
        )
        c_total = _col(fields, total_col, "total", "total_points", "committed", "scope")

        for row in reader:
            raw_date = (row.get(c_date or "date", "") or "").strip()
            dt = parse_date(raw_date)
            if not dt:
                continue

            raw_rem = (row.get(c_remaining or "remaining_points", "") or "").strip().replace(",", "")
            try:
                remaining = float(raw_rem) if raw_rem else None
            except ValueError:
                remaining = None
            if remaining is None:
                continue

            if c_total and row.get(c_total, "").strip():
                try:
                    total_from_csv = float((row.get(c_total, "") or "").strip().replace(",", ""))
                except ValueError:
                    pass

            rows.append({"date": dt, "remaining": remaining})

    rows.sort(key=lambda r: r["date"])
    return rows, total_from_csv


# ---------------------------------------------------------------------------
# Burndown analysis
# ---------------------------------------------------------------------------

def compute_ideal_remaining(
    total: float,
    start_date: datetime,
    end_date: datetime,
    at_date: datetime,
) -> float:
    """Ideal remaining at at_date (linear from total at start to 0 at end)."""
    if end_date <= start_date:
        return total if at_date <= start_date else 0.0
    span = (end_date - start_date).total_seconds()
    elapsed = (at_date - start_date).total_seconds()
    if elapsed <= 0:
        return total
    if elapsed >= span:
        return 0.0
    return total * (1.0 - elapsed / span)


def analyze_burndown(
    snapshots: List[Dict[str, Any]],
    total_points: float,
    sprint_days: Optional[int],
) -> Dict[str, Any]:
    """Compare actual vs ideal; compute per-day status and overall status."""
    if not snapshots or total_points <= 0:
        return {
            "snapshots": [],
            "daily": [],
            "overall_status": "unknown",
            "total_points": total_points,
            "sprint_days": sprint_days,
        }

    start_date = snapshots[0]["date"]
    if sprint_days is not None:
        end_date = start_date + timedelta(days=sprint_days)
    else:
        end_date = snapshots[-1]["date"]

    daily: List[Dict[str, Any]] = []
    for s in snapshots:
        actual = s["remaining"]
        ideal = compute_ideal_remaining(total_points, start_date, end_date, s["date"])
        delta = actual - ideal
        if delta <= -1:
            day_status = "ahead"
        elif delta >= 1:
            day_status = "behind"
        else:
            day_status = "on_track"
        daily.append({
            "date": s["date"].strftime("%Y-%m-%d"),
            "actual_remaining": round(actual, 1),
            "ideal_remaining": round(ideal, 1),
            "delta": round(delta, 1),
            "status": day_status,
        })

    # Overall status from latest snapshot
    last = daily[-1]
    d = last["delta"]
    if d <= -1:
        overall = "ahead"
    elif d >= 1:
        overall = "behind"
    else:
        overall = "on_track"

    # Display calendar days (inclusive) when inferred from data
    sprint_days_val = (
        sprint_days
        if sprint_days is not None
        else (end_date - start_date).days + 1
    )

    return {
        "snapshots": snapshots,
        "daily": daily,
        "overall_status": overall,
        "total_points": total_points,
        "sprint_days": sprint_days_val,
        "start_date": start_date.strftime("%Y-%m-%d"),
        "end_date": end_date.strftime("%Y-%m-%d"),
    }


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def _bar(value: float, max_val: float, width: int = 20) -> str:
    if max_val <= 0:
        return "░" * width
    ratio = min(1.0, max(0.0, value / max_val))
    filled = int(ratio * width)
    return "█" * filled + "░" * (width - filled)


def print_report(result: Dict[str, Any], chart: bool = False) -> None:
    """Pretty-print burndown comparison."""
    print("\n" + "=" * 70)
    print("📉 SPRINT BURNDOWN CHECKER")
    print("=" * 70)

    daily = result.get("daily", [])
    if not daily:
        print("\nNo burndown data to report.")
        return

    total = result["total_points"]
    status = result["overall_status"]
    start = result.get("start_date", "")
    end = result.get("end_date", "")
    days = result.get("sprint_days", 0)

    print(f"\n   Sprint: {start} → {end}  ({days} days)  Total: {total:.0f} pts")
    print(f"\n   Overall: ", end="")
    if status == "ahead":
        print("🟢 AHEAD of ideal")
    elif status == "behind":
        print("🔴 BEHIND ideal")
    else:
        print("🟡 ON TRACK")

    print(f"\n   {'Date':<12} {'Actual':>8} {'Ideal':>8} {'Delta':>8}  Status")
    print("   " + "─" * 50)
    for row in daily:
        st = "ahead" if row["status"] == "ahead" else ("behind" if row["status"] == "behind" else "on track")
        print(f"   {row['date']:<12} {row['actual_remaining']:>8.1f} {row['ideal_remaining']:>8.1f} {row['delta']:>+8.1f}  {st}")

    if chart and daily:
        print(f"\n   Burndown (actual vs ideal):")
        max_pts = max(total, max(r["actual_remaining"] for r in daily))
        for row in daily:
            abar = _bar(row["actual_remaining"], max_pts, 18)
            ibar = _bar(row["ideal_remaining"], max_pts, 18)
            print(f"   {row['date']}  actual {abar} {row['actual_remaining']:.0f}  ideal {ibar} {row['ideal_remaining']:.0f}")

    print()


def to_json_result(result: Dict[str, Any]) -> Dict[str, Any]:
    """JSON-serializable result (no datetime objects)."""
    return {
        "overall_status": result["overall_status"],
        "total_points": result["total_points"],
        "sprint_days": result["sprint_days"],
        "start_date": result.get("start_date"),
        "end_date": result.get("end_date"),
        "daily": result.get("daily", []),
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Compare sprint burndown to ideal; report on track / behind / ahead.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--csv", required=True, help="Path to burndown CSV (date, remaining_points)")
    parser.add_argument("--sprint-days", type=int, default=None, help="Sprint length in days (default: infer from last date)")
    parser.add_argument("--total", type=float, default=None, help="Total committed points at sprint start (default: first row remaining)")
    parser.add_argument("--chart", action="store_true", help="Print simple ASCII burndown chart")
    parser.add_argument("--markdown", metavar="FILE", help="Write Markdown report to FILE")
    parser.add_argument("--output", "-o", metavar="FILE", help="Write JSON result to FILE")
    args = parser.parse_args()

    snapshots, total_from_csv = load_burndown_csv(args.csv)
    if not snapshots:
        print("No valid burndown rows in CSV.", file=sys.stderr)
        return 1

    total = args.total
    if total is None and total_from_csv is not None:
        total = total_from_csv
    if total is None:
        total = snapshots[0]["remaining"]

    result = analyze_burndown(snapshots, total, args.sprint_days)
    print_report(result, chart=args.chart)

    if args.markdown:
        with open(args.markdown, "w", encoding="utf-8") as f:
            f.write("# Sprint Burndown Report\n\n")
            f.write(f"- **Status:** {result['overall_status'].replace('_', ' ').title()}\n")
            f.write(f"- **Total points:** {result['total_points']}\n")
            f.write(f"- **Sprint:** {result.get('start_date')} → {result.get('end_date')}\n\n")
            f.write("| Date | Actual | Ideal | Delta | Status |\n")
            f.write("|------|--------|-------|-------|--------|\n")
            for row in result.get("daily", []):
                f.write(f"| {row['date']} | {row['actual_remaining']} | {row['ideal_remaining']} | {row['delta']:+.1f} | {row['status']} |\n")
        print(f"Wrote Markdown to {args.markdown}")

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(to_json_result(result), f, indent=2)
        print(f"Wrote JSON to {args.output}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
