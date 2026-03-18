#!/usr/bin/env python3
"""
Release Cadence Report

Track release count per week or month from CSV. Report trend (accelerating /
steady / slowing) and optional breakdown by product or channel. Complements
release-impact-summary with a time-series cadence view.

Usage:
    # Basic (date per release, one row per release)
    python release-cadence-report.py --csv releases.csv

    # By month; last 12 periods
    python release-cadence-report.py --csv releases.csv --period month --periods 12

    # Group by product or channel
    python release-cadence-report.py --csv releases.csv --group-by product

    # Chart and export
    python release-cadence-report.py --csv releases.csv --chart --markdown report.md --output report.json

CSV format:
    date,release_id,product
    2025-01-05,v2.0.0,API
    2025-01-12,v2.0.1,API
    2025-01-19,v2.1.0,Web

    Required: date (one row per release).
    Optional: release_id, version, product, channel for --group-by.

Requirements:
    None (stdlib only).
"""

import argparse
import csv
import json
import sys
from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, List, Optional


def parse_date(s: str) -> Optional[datetime]:
    if not s or not str(s).strip():
        return None
    s = str(s).strip()[:32]
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


def load_releases(
    path: str,
    date_col: str = "date",
    segment_col: str = "product",
) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fields = reader.fieldnames or []
        c_date = _col(fields, date_col, "date", "timestamp", "released", "release_date")
        c_seg = _col(fields, segment_col, "product", "channel", "segment", "area", "team")

        if not c_date:
            raise ValueError(
                f"Required column 'date' not found. Columns in file: {list(fields)}"
            )

        for row in reader:
            dt = parse_date((row.get(c_date, "") or "").strip())
            if not dt:
                continue
            segment = (row.get(c_seg, "") or "").strip() if c_seg else "—"
            if not segment:
                segment = "—"
            rows.append({
                "date": dt,
                "segment": segment,
            })
    rows.sort(key=lambda r: r["date"])
    return rows


def group_by_period(
    releases: List[Dict[str, Any]],
    period: str,
    periods_limit: Optional[int],
) -> Dict[str, Any]:
    by_key: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for r in releases:
        dt = r["date"]
        if period == "month":
            key = dt.strftime("%Y-%m")
        else:
            iso = dt.isocalendar()
            key = f"{iso[0]}-W{iso[1]:02d}"
        by_key[key].append(r)

    sorted_keys = sorted(by_key.keys())
    if periods_limit and sorted_keys:
        sorted_keys = sorted_keys[-periods_limit:]
        by_key = {k: by_key[k] for k in sorted_keys if k in by_key}

    counts = {k: len(by_key[k]) for k in sorted_keys}
    total = sum(counts.values())
    n_periods = len(counts)
    avg_per_period = total / n_periods if n_periods else 0

    trend_delta: Optional[float] = None
    if n_periods >= 4:
        mid = n_periods // 2
        first_avg = sum(counts[k] for k in sorted_keys[:mid]) / mid if mid else 0
        second_avg = sum(counts[k] for k in sorted_keys[mid:]) / (n_periods - mid) if (n_periods - mid) else 0
        trend_delta = second_avg - first_avg

    return {
        "period": period,
        "periods": sorted_keys,
        "counts": counts,
        "total": total,
        "avg_per_period": round(avg_per_period, 1),
        "min_count": min(counts.values()) if counts else 0,
        "max_count": max(counts.values()) if counts else 0,
        "trend_delta": round(trend_delta, 1) if trend_delta is not None else None,
    }


def group_by_segment(releases: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    by_seg: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for r in releases:
        by_seg[r["segment"]].append(r)
    return {
        seg: {"count": len(items), "releases": len(items)}
        for seg, items in sorted(by_seg.items(), key=lambda x: -len(x[1]))
    }


def _bar(value: float, max_val: float, width: int = 20) -> str:
    if max_val <= 0:
        return "░" * width
    ratio = min(1.0, max(0.0, value / max_val))
    filled = int(ratio * width)
    return "█" * filled + "░" * (width - filled)


def _trend_label(delta: Optional[float]) -> str:
    if delta is None:
        return "—"
    if delta > 0.3:
        return "accelerating"
    if delta < -0.3:
        return "slowing"
    return "steady"


def print_report(
    result: Dict[str, Any],
    by_segment: Dict[str, Dict[str, Any]],
    chart: bool,
) -> None:
    print("\n" + "=" * 70)
    print("🚀 RELEASE CADENCE REPORT")
    print("=" * 70)

    if not result.get("periods"):
        print("\n   No releases with valid date in CSV.\n")
        return

    print(f"\n   Period:       {result['period']}")
    print(f"   Total:       {result['total']} releases")
    print(f"   Avg/period:  {result['avg_per_period']:.1f}")
    print(f"   Range:       {result['min_count']} – {result['max_count']} per period")
    if result.get("trend_delta") is not None:
        d = result["trend_delta"]
        direction = "↑" if d > 0 else "↓" if d < 0 else "→"
        label = _trend_label(result["trend_delta"])
        print(f"   Trend:       {direction} {abs(d):.1f} releases/period (2nd half vs 1st) — {label}")

    print(f"\n   {'Period':<14} {'Releases':>10}")
    print("   " + "─" * 26)
    for p in result["periods"]:
        print(f"   {p:<14} {result['counts'][p]:>10}")

    if chart and result["periods"]:
        max_c = max(result["counts"].values()) or 1
        print(f"\n   Releases by period:")
        for p in result["periods"]:
            bar = _bar(result["counts"][p], max_c, 25)
            print(f"   {p:<12} {bar} {result['counts'][p]}")

    if by_segment:
        print(f"\n   By segment:")
        for seg, stats in by_segment.items():
            print(f"      {seg:<16} {stats['count']:>6} releases")

    print("\n   💡 Use with release-impact-summary for cadence + impact view.\n")


def to_json_result(result: Dict[str, Any], by_segment: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    out = {
        "period": result["period"],
        "periods": result["periods"],
        "counts": result["counts"],
        "total": result["total"],
        "avg_per_period": result["avg_per_period"],
        "trend_delta": result.get("trend_delta"),
    }
    if by_segment:
        out["by_segment"] = by_segment
    return out


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Report release cadence (releases per period) and trend from CSV.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--csv", "-c", required=True, help="Path to releases CSV (date, one row per release)")
    parser.add_argument("--period", "-p", choices=["week", "month"], default="week", help="Group by week (default) or month")
    parser.add_argument("--periods", type=int, default=None, metavar="N", help="Limit to last N periods")
    parser.add_argument("--group-by", type=str, default=None, metavar="COL", help="Also group by column (e.g. product, channel)")
    parser.add_argument("--chart", action="store_true", help="Print bar chart of releases by period")
    parser.add_argument("--markdown", metavar="FILE", help="Write Markdown report to FILE")
    parser.add_argument("--output", "-o", metavar="FILE", help="Write JSON result to FILE")
    args = parser.parse_args()

    try:
        rows = load_releases(args.csv)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    if not rows:
        print("No valid rows in CSV (need date).", file=sys.stderr)
        return 1

    result = group_by_period(rows, args.period, args.periods)
    by_segment = {}
    if args.group_by:
        by_segment = group_by_segment(rows)

    print_report(result, by_segment, args.chart)

    if args.markdown and result.get("periods"):
        with open(args.markdown, "w", encoding="utf-8") as f:
            f.write("# Release Cadence Report\n\n")
            f.write(f"- **Total releases:** {result['total']}\n")
            f.write(f"- **Avg per {result['period']}:** {result['avg_per_period']}\n")
            trend_val = result.get("trend_delta")
            f.write(f"- **Trend:** " + (f"{trend_val:+.1f} releases/period ({_trend_label(trend_val)})" if trend_val is not None else "—") + "\n\n")
            f.write("| Period | Releases |\n")
            f.write("|--------|----------|\n")
            for p in result["periods"]:
                f.write(f"| {p} | {result['counts'][p]} |\n")
        print(f"Wrote Markdown to {args.markdown}")

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(to_json_result(result, by_segment), f, indent=2)
        print(f"Wrote JSON to {args.output}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
