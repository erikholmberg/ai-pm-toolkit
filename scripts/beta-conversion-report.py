#!/usr/bin/env python3
"""
Beta Conversion Report

Track waitlist size and converted users over time from CSV. Report conversion
rate by period and trend. For early access and beta programs.

Usage:
    # Basic (date, waitlist_size, converted)
    python beta-conversion-report.py --csv beta.csv

    # With optional feedback count column
    python beta-conversion-report.py --csv beta.csv --feedback-col feedback_count

    # Chart and export
    python beta-conversion-report.py --csv beta.csv --chart --markdown report.md --output report.json

CSV format:
    date,waitlist_size,converted,feedback_count
    2025-01-01,500,25,10
    2025-01-08,520,42,18
    2025-01-15,480,38,15

    Required: date, waitlist_size (or waitlist), converted.
    Optional: feedback_count (or feedback) for feedback volume.

Requirements:
    None (stdlib only).
"""

import argparse
import csv
import json
import sys
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


def _num(val: str) -> float:
    if not val or not str(val).strip():
        return 0.0
    try:
        return float(str(val).strip().replace(",", ""))
    except ValueError:
        return 0.0


def load_beta(
    path: str,
    date_col: str = "date",
    waitlist_col: str = "waitlist_size",
    converted_col: str = "converted",
    feedback_col: str = "feedback_count",
) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fields = reader.fieldnames or []
        c_date = _col(fields, date_col, "date", "timestamp", "time", "period")
        c_wait = _col(fields, waitlist_col, "waitlist_size", "waitlist", "waitlist_count", "n_waitlist")
        c_conv = _col(fields, converted_col, "converted", "conversions", "n_converted", "signed_up")
        c_fb = _col(fields, feedback_col, "feedback_count", "feedback", "n_feedback")

        if not c_date or not c_wait or not c_conv:
            raise ValueError(
                f"Required column(s) not found. Need date, waitlist_size, converted. "
                f"Columns in file: {list(fields)}"
            )

        for row in reader:
            dt = parse_date((row.get(c_date, "") or "").strip())
            waitlist = _num(row.get(c_wait, "") or "")
            converted = _num(row.get(c_conv, "") or "")
            if not dt:
                continue
            feedback = _num(row.get(c_fb, "") or "") if c_fb else 0.0
            rows.append({
                "date": dt,
                "date_str": dt.strftime("%Y-%m-%d"),
                "waitlist_size": waitlist,
                "converted": converted,
                "feedback_count": feedback,
                "conversion_pct": (100.0 * converted / waitlist) if waitlist else 0.0,
            })
    rows.sort(key=lambda r: r["date"])
    return rows


def summarize(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not rows:
        return {"periods": [], "rows": [], "total_waitlist": 0, "total_converted": 0, "overall_conversion_pct": 0, "trend_delta_pct": None}
    total_waitlist = sum(r["waitlist_size"] for r in rows)
    total_converted = sum(r["converted"] for r in rows)
    overall_pct = (100.0 * total_converted / total_waitlist) if total_waitlist else 0
    conversion_rates = [r["conversion_pct"] for r in rows]
    n = len(conversion_rates)
    trend_delta_pct: Optional[float] = None
    if n >= 4:
        mid = n // 2
        first_avg = sum(conversion_rates[:mid]) / mid
        second_avg = sum(conversion_rates[mid:]) / (n - mid)
        trend_delta_pct = second_avg - first_avg
    return {
        "periods": [r["date_str"] for r in rows],
        "rows": rows,
        "total_waitlist": round(total_waitlist, 0),
        "total_converted": round(total_converted, 0),
        "overall_conversion_pct": round(overall_pct, 1),
        "trend_delta_pct": round(trend_delta_pct, 1) if trend_delta_pct is not None else None,
        "latest_waitlist": rows[-1]["waitlist_size"],
        "latest_converted": rows[-1]["converted"],
        "latest_conversion_pct": rows[-1]["conversion_pct"],
    }


def _bar(value: float, max_val: float, width: int = 20) -> str:
    if max_val <= 0:
        return "░" * width
    ratio = min(1.0, max(0.0, value / max_val))
    filled = int(ratio * width)
    return "█" * filled + "░" * (width - filled)


def print_report(result: Dict[str, Any], chart: bool) -> None:
    print("\n" + "=" * 70)
    print("🧪 BETA CONVERSION REPORT")
    print("=" * 70)

    if not result.get("periods"):
        print("\n   No beta data in CSV (need date, waitlist_size, converted).\n")
        return

    print(f"\n   Periods:        {len(result['periods'])}")
    print(f"   Total waitlist: {result['total_waitlist']:,.0f}")
    print(f"   Total converted:{result['total_converted']:,.0f}")
    print(f"   Overall rate:   {result['overall_conversion_pct']:.1f}%")
    print(f"   Latest:         {result['latest_converted']:,.0f} / {result['latest_waitlist']:,.0f} ({result['latest_conversion_pct']:.1f}%)")
    if result.get("trend_delta_pct") is not None:
        print(f"   Trend:          conversion rate {result['trend_delta_pct']:+.1f} pp (2nd half vs 1st half)")

    print(f"\n   {'Date':<14} {'Waitlist':>10} {'Converted':>10} {'Rate %':>8}")
    print("   " + "─" * 46)
    for r in result["rows"]:
        print(f"   {r['date_str']:<14} {r['waitlist_size']:>10,.0f} {r['converted']:>10,.0f} {r['conversion_pct']:>7.1f}%")

    if chart and result.get("rows"):
        rates = [r["conversion_pct"] for r in result["rows"]]
        mx = max(rates) or 1
        print(f"\n   Conversion rate trend:")
        print("   ", end="")
        for r in result["rows"]:
            print(_bar(r["conversion_pct"], mx, 6), end=" ")
        print(f"  (0 → {mx:.1f}%)")

    print("\n   💡 Use for early access and beta program tracking.\n")


def to_json_result(result: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "periods": result.get("periods", []),
        "total_waitlist": result.get("total_waitlist", 0),
        "total_converted": result.get("total_converted", 0),
        "overall_conversion_pct": result.get("overall_conversion_pct", 0),
        "trend_delta_pct": result.get("trend_delta_pct"),
        "latest_waitlist": result.get("latest_waitlist", 0),
        "latest_converted": result.get("latest_converted", 0),
        "latest_conversion_pct": result.get("latest_conversion_pct", 0),
        "rows": [
            {"date": r["date_str"], "waitlist_size": r["waitlist_size"], "converted": r["converted"], "conversion_pct": r["conversion_pct"]}
            for r in result.get("rows", [])
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Track beta waitlist and conversion over time.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--csv", "-c", required=True, help="Path to beta CSV (date, waitlist_size, converted)")
    parser.add_argument("--feedback-col", type=str, default=None, metavar="COL", help="Optional column name for feedback count")
    parser.add_argument("--chart", action="store_true", help="Print conversion rate trend bars")
    parser.add_argument("--markdown", metavar="FILE", help="Write Markdown report to FILE")
    parser.add_argument("--output", "-o", metavar="FILE", help="Write JSON result to FILE")
    args = parser.parse_args()

    try:
        rows = load_beta(args.csv, feedback_col=args.feedback_col or "feedback_count")
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    if not rows:
        print("No valid rows in CSV (need date, waitlist_size, converted).", file=sys.stderr)
        return 1

    result = summarize(rows)
    print_report(result, args.chart)

    if args.markdown and result.get("periods"):
        with open(args.markdown, "w", encoding="utf-8") as f:
            f.write("# Beta Conversion Report\n\n")
            f.write(f"- **Total waitlist:** {result['total_waitlist']:,.0f}\n")
            f.write(f"- **Total converted:** {result['total_converted']:,.0f}\n")
            f.write(f"- **Overall conversion:** {result['overall_conversion_pct']:.1f}%\n")
            trend_val = result.get('trend_delta_pct')
            f.write(f"- **Trend:** {f'{trend_val:+.1f} pp' if trend_val is not None else '—'}\n\n")
            f.write("| Date | Waitlist | Converted | Rate % |\n")
            f.write("|------|----------|-----------|--------|\n")
            for r in result["rows"]:
                f.write(f"| {r['date_str']} | {r['waitlist_size']:,.0f} | {r['converted']:,.0f} | {r['conversion_pct']:.1f}% |\n")
        print(f"Wrote Markdown to {args.markdown}")

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(to_json_result(result), f, indent=2)
        print(f"Wrote JSON to {args.output}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
