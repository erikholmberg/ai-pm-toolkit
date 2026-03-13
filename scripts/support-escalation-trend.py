#!/usr/bin/env python3
"""
Support / Escalation Trend

Report support or escalation ticket counts per week or month and trend from CSV.
Use for capacity planning, spotting spikes, and non-incident escalation tracking.
Same pattern as incident-rate-trend but for tickets/cases.

Usage:
    # Counts per week (default)
    python support-escalation-trend.py --csv tickets.csv

    # Per month; last 12 periods
    python support-escalation-trend.py --csv tickets.csv --period month --weeks 12

    # Group by product or severity
    python support-escalation-trend.py --csv tickets.csv --group-by severity

    # Chart and export
    python support-escalation-trend.py --csv tickets.csv --chart --markdown report.md --output report.json

CSV format:
    date,product,severity
    2025-01-15,API,high
    2025-01-22,Dashboard,medium
    2025-01-28,API,

    Required: date (one row per ticket, or use count column for pre-aggregated).
    Optional: product, severity, count (if each row = period with count).

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


def load_tickets(
    path: str,
    date_col: str = "date",
    count_col: str = "count",
    product_col: str = "product",
    severity_col: str = "severity",
) -> List[Dict[str, Any]]:
    """Load tickets: one row per ticket (date) or one row per period (date + count)."""
    rows: List[Dict[str, Any]] = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fields = reader.fieldnames or []
        c_date = _col(fields, date_col, "date", "timestamp", "created", "opened")
        c_count = _col(fields, count_col, "count", "tickets", "n", "volume")
        c_product = _col(fields, product_col, "product", "team", "source", "area")
        c_severity = _col(fields, severity_col, "severity", "priority", "level")

        for row in reader:
            raw_date = (row.get(c_date or "date", "") or "").strip()
            dt = parse_date(raw_date)
            if not dt:
                continue

            raw_count = (row.get(c_count or "count", "") or "").strip().replace(",", "")
            count = 1
            if raw_count:
                try:
                    count = max(1, int(float(raw_count)))
                except ValueError:
                    pass

            product = (row.get(c_product or "product", "") or "").strip() or "—"
            severity = (row.get(c_severity or "severity", "") or "").strip() or "—"

            for _ in range(count):
                rows.append({
                    "date": dt,
                    "product": product,
                    "severity": severity,
                })
    rows.sort(key=lambda r: r["date"])
    return rows


def group_by_period(
    tickets: List[Dict[str, Any]],
    period: str,
    periods_limit: Optional[int],
) -> Dict[str, Any]:
    by_key: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for t in tickets:
        dt = t["date"]
        if period == "month":
            key = dt.strftime("%Y-%m")
        else:
            iso = dt.isocalendar()
            key = f"{iso[0]}-W{iso[1]:02d}"
        by_key[key].append(t)

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


def group_by_column(tickets: List[Dict[str, Any]], col: str) -> Dict[str, Dict[str, Any]]:
    by_col: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for t in tickets:
        key = t.get(col, "—")
        by_col[key].append(t)
    return {
        k: {"count": len(v)}
        for k, v in sorted(by_col.items(), key=lambda x: -len(x[1]))
    }


def _bar(value: float, max_val: float, width: int = 20) -> str:
    if max_val <= 0:
        return "░" * width
    ratio = min(1.0, max(0.0, value / max_val))
    filled = int(ratio * width)
    return "█" * filled + "░" * (width - filled)


def print_report(result: Dict[str, Any], by_group: Dict[str, Dict[str, Any]], chart: bool) -> None:
    print("\n" + "=" * 70)
    print("📬 SUPPORT / ESCALATION TREND")
    print("=" * 70)

    total = result["total"]
    period = result["period"]
    print(f"\n   Period:       {period}")
    print(f"   Total:       {total} tickets")
    print(f"   Avg/period:  {result['avg_per_period']:.1f}")
    print(f"   Range:       {result['min_count']} – {result['max_count']} per period")
    if result.get("trend_delta") is not None:
        d = result["trend_delta"]
        direction = "↑" if d > 0 else "↓" if d < 0 else "→"
        print(f"   Trend:       {direction} {abs(d):.1f} tickets/period (2nd half vs 1st half)")

    print(f"\n   {'Period':<14} {'Count':>8}")
    print("   " + "─" * 24)
    for p in result["periods"]:
        print(f"   {p:<14} {result['counts'][p]:>8}")

    if chart and result["periods"]:
        max_c = max(result["counts"].values()) or 1
        print(f"\n   Count by period:")
        for p in result["periods"]:
            bar = _bar(result["counts"][p], max_c, 25)
            print(f"   {p:<12} {bar} {result['counts'][p]}")

    if by_group:
        print(f"\n   By group:")
        for name, stats in by_group.items():
            print(f"      {name:<16} {stats['count']:>6} tickets")

    print("\n   💡 Use for capacity planning and escalation tracking.\n")


def to_json_result(result: Dict[str, Any], by_group: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    out = {
        "period": result["period"],
        "periods": result["periods"],
        "counts": result["counts"],
        "total": result["total"],
        "avg_per_period": result["avg_per_period"],
        "trend_delta": result.get("trend_delta"),
    }
    if by_group:
        out["by_group"] = by_group
    return out


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Report support/escalation ticket trend from CSV.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--csv", "-c", required=True, help="Path to tickets CSV (date required)")
    parser.add_argument("--period", "-p", choices=["week", "month"], default="week", help="Group by week (default) or month")
    parser.add_argument("--weeks", "-w", type=int, default=None, metavar="N", help="Limit to last N periods")
    parser.add_argument("--group-by", type=str, default=None, metavar="COL", help="Also group by column (e.g. product, severity)")
    parser.add_argument("--chart", action="store_true", help="Print bar chart of counts by period")
    parser.add_argument("--markdown", metavar="FILE", help="Write Markdown report to FILE")
    parser.add_argument("--output", "-o", metavar="FILE", help="Write JSON result to FILE")
    args = parser.parse_args()

    tickets = load_tickets(args.csv)
    if not tickets:
        print("No tickets with valid date in CSV.", file=sys.stderr)
        return 1

    result = group_by_period(tickets, args.period, args.weeks)
    by_group = {}
    if args.group_by:
        col = "product" if args.group_by.lower() in ("product", "team", "source", "area") else "severity"
        by_group = group_by_column(tickets, col)

    print_report(result, by_group, args.chart)

    if args.markdown:
        with open(args.markdown, "w", encoding="utf-8") as f:
            f.write("# Support / Escalation Trend\n\n")
            f.write(f"- **Total tickets:** {result['total']}\n")
            f.write(f"- **Avg per {result['period']}:** {result['avg_per_period']}\n")
            if result.get("trend_delta") is not None:
                f.write(f"- **Trend (2nd vs 1st half):** {result['trend_delta']:+.1f}\n")
            f.write("\n| Period | Count |\n")
            f.write("|--------|-------|\n")
            for p in result["periods"]:
                f.write(f"| {p} | {result['counts'][p]} |\n")
        print(f"Wrote Markdown to {args.markdown}")

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(to_json_result(result, by_group), f, indent=2)
        print(f"Wrote JSON to {args.output}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
