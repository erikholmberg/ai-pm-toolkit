#!/usr/bin/env python3
"""
Feature Adoption Trend

Track adoption % or DAU/WAU over time from CSV. Report trend and a simple
label (growing / flattening / declining). Complements adoption-funnel-analyzer
and feature-adoption-scorecard with a time-series view.

Usage:
    # Basic (date, adoption_pct)
    python feature-adoption-trend.py --csv adoption.csv

    # Group by segment or feature
    python feature-adoption-trend.py --csv adoption.csv --group-by segment

    # Threshold for "flattening" (default: ±5%% change = flat)
    python feature-adoption-trend.py --csv adoption.csv --flat-threshold 3

    # Chart and export
    python feature-adoption-trend.py --csv adoption.csv --chart --markdown report.md --output report.json

CSV format:
    date,adoption_pct,segment
    2025-01-01,12.5,Web
    2025-01-08,14.2,Web
    2025-01-15,15.1,Web

    Required: date, adoption_pct (or adoption, dau, wau, value).
    Optional: segment (or feature) for --group-by.

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


def load_adoption(
    path: str,
    date_col: str = "date",
    value_col: str = "adoption_pct",
    segment_col: str = "segment",
) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fields = reader.fieldnames or []
        c_date = _col(fields, date_col, "date", "timestamp", "time", "period")
        c_value = _col(fields, value_col, "adoption_pct", "adoption", "adoption_rate", "dau", "wau", "value", "pct")
        c_seg = _col(fields, segment_col, "segment", "feature", "group", "area")

        if not c_date or not c_value:
            raise ValueError(
                f"Required column(s) not found. Need date and adoption_pct (or adoption, dau, wau, value). "
                f"Columns in file: {list(fields)}"
            )

        for row in reader:
            raw_date = (row.get(c_date, "") or "").strip()
            dt = parse_date(raw_date)
            raw_val = (row.get(c_value, "") or "").strip().replace(",", "")
            if not dt or not raw_val:
                continue
            try:
                value = float(raw_val)
            except ValueError:
                continue
            segment = (row.get(c_seg or "segment", "") or "").strip() or "—"
            rows.append({
                "date": dt,
                "date_str": dt.strftime("%Y-%m-%d"),
                "value": value,
                "segment": segment,
            })
    rows.sort(key=lambda r: (r["date"], r["segment"]))
    return rows


def compute_trend(
    series: List[Dict[str, Any]],
    flat_threshold_pct: float,
) -> Dict[str, Any]:
    """Series is sorted by date. Trend = second half avg - first half avg (as % of first half)."""
    if not series:
        return {"periods": [], "values": [], "trend_delta_pct": None, "label": "—"}
    values = [r["value"] for r in series]
    n = len(values)
    trend_delta_pct: Optional[float] = None
    label = "—"
    if n >= 4:
        mid = n // 2
        first_avg = sum(values[:mid]) / mid
        second_avg = sum(values[mid:]) / (n - mid)
        if first_avg != 0:
            trend_delta_pct = (second_avg - first_avg) / abs(first_avg) * 100
            if trend_delta_pct >= flat_threshold_pct:
                label = "growing"
            elif trend_delta_pct <= -flat_threshold_pct:
                label = "declining"
            else:
                label = "flattening"
    return {
        "periods": [r["date_str"] for r in series],
        "values": values,
        "min": min(values),
        "max": max(values),
        "latest": values[-1],
        "trend_delta_pct": round(trend_delta_pct, 1) if trend_delta_pct is not None else None,
        "label": label,
    }


def summarize(
    rows: List[Dict[str, Any]],
    flat_threshold_pct: float,
    group_by: bool,
) -> Dict[str, Any]:
    if not group_by:
        overall = compute_trend(rows, flat_threshold_pct)
        return {
            "overall": overall,
            "by_segment": {},
            "flat_threshold_pct": flat_threshold_pct,
        }
    by_seg: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for r in rows:
        by_seg[r["segment"]].append(r)
    overall_series = sorted(rows, key=lambda x: x["date"])
    overall = compute_trend(overall_series, flat_threshold_pct)
    by_segment = {}
    for seg, items in sorted(by_seg.items()):
        by_segment[seg] = compute_trend(items, flat_threshold_pct)
    return {
        "overall": overall,
        "by_segment": by_segment,
        "flat_threshold_pct": flat_threshold_pct,
    }


def _bar(value: float, min_val: float, max_val: float, width: int = 20) -> str:
    if max_val <= min_val:
        return "░" * width
    ratio = (value - min_val) / (max_val - min_val)
    ratio = max(0, min(1, ratio))
    filled = int(ratio * width)
    return "█" * filled + "░" * (width - filled)


def print_report(result: Dict[str, Any], chart: bool) -> None:
    print("\n" + "=" * 70)
    print("📈 FEATURE ADOPTION TREND")
    print("=" * 70)

    overall = result.get("overall", {})
    if not overall.get("periods"):
        print("\n   No adoption data in CSV (need date, adoption_pct).\n")
        return

    print(f"\n   Periods:    {len(overall['periods'])}")
    print(f"   Range:      {overall['min']:.2f} – {overall['max']:.2f}")
    print(f"   Latest:     {overall['latest']:.2f}")
    if overall.get("trend_delta_pct") is not None:
        print(f"   Trend:      {overall['trend_delta_pct']:+.1f}% (2nd half vs 1st half)")
    print(f"   Label:      {overall['label']} (threshold ±{result.get('flat_threshold_pct', 5)}%)")

    print(f"\n   {'Date':<14} {'Value':>10}")
    print("   " + "─" * 26)
    for i, p in enumerate(overall["periods"]):
        print(f"   {p:<14} {overall['values'][i]:>10.2f}")

    if chart and overall.get("values"):
        mn, mx = overall["min"], overall["max"]
        print(f"\n   Trend:")
        print("   ", end="")
        for v in overall["values"]:
            print(_bar(v, mn, mx, 6), end=" ")
        print(f"  ({mn:.2f} → {mx:.2f})")

    if result.get("by_segment"):
        print(f"\n   By segment:")
        for seg, data in result["by_segment"].items():
            print(f"      {seg:<16} latest={data['latest']:.2f}  {data['label']}")

    print("\n   💡 Use with adoption-funnel and feature-adoption-scorecard for time-series view.\n")


def to_json_result(result: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "overall": result.get("overall", {}),
        "by_segment": result.get("by_segment", {}),
        "flat_threshold_pct": result.get("flat_threshold_pct", 5),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Track adoption over time; label trend as growing/flattening/declining.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--csv", "-c", required=True, help="Path to adoption CSV (date, adoption_pct)")
    parser.add_argument("--group-by", type=str, default=None, metavar="COL", help="Group by segment/feature")
    parser.add_argument("--flat-threshold", type=float, default=5, metavar="PCT", help="%% change to treat as flattening (default: ±5)")
    parser.add_argument("--chart", action="store_true", help="Print simple trend bars")
    parser.add_argument("--markdown", metavar="FILE", help="Write Markdown report to FILE")
    parser.add_argument("--output", "-o", metavar="FILE", help="Write JSON result to FILE")
    args = parser.parse_args()

    try:
        rows = load_adoption(args.csv)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    if not rows:
        print("No valid rows in CSV (need date, adoption_pct).", file=sys.stderr)
        return 1

    result = summarize(rows, max(0, args.flat_threshold), group_by=args.group_by is not None)
    print_report(result, args.chart)

    if args.markdown and result.get("overall", {}).get("periods"):
        with open(args.markdown, "w", encoding="utf-8") as f:
            f.write("# Feature Adoption Trend\n\n")
            o = result["overall"]
            f.write(f"- **Latest:** {o['latest']:.2f}\n")
            f.write(f"- **Trend:** {o.get('trend_delta_pct', '—')}%\n")
            f.write(f"- **Label:** {o.get('label', '—')}\n\n")
            f.write("| Date | Value |\n")
            f.write("|------|-------|\n")
            for i, p in enumerate(o["periods"]):
                f.write(f"| {p} | {o['values'][i]:.2f} |\n")
        print(f"Wrote Markdown to {args.markdown}")

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(to_json_result(result), f, indent=2)
        print(f"Wrote JSON to {args.output}")

    return 0


if __name__ == "__main__":
    sys.exit(main())