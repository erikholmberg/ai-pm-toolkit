#!/usr/bin/env python3
"""
Customer Health Score Trend

Track health scores over time from CSV. Report trend and at-risk count (below
threshold). Complements churn-risk-calculator with a time-series view.

Usage:
    # Basic (date, account_id, health_score)
    python customer-health-score-trend.py --csv health.csv

    # At-risk = score below 50
    python customer-health-score-trend.py --csv health.csv --at-risk-below 50

    # Group by segment
    python customer-health-score-trend.py --csv health.csv --group-by segment --at-risk-below 40

    # Chart and export
    python customer-health-score-trend.py --csv health.csv --chart --markdown report.md --output report.json

CSV format:
    date,account_id,health_score,segment
    2025-01-01,acct-001,72,Enterprise
    2025-01-01,acct-002,45,SMB
    2025-01-08,acct-001,68,Enterprise

    Required: date, health_score (or score, health).
    Optional: account_id (or account), segment for --group-by.

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


def _num(val: str) -> float:
    if not val or not str(val).strip():
        return 0.0
    try:
        return float(str(val).strip().replace(",", ""))
    except ValueError:
        return 0.0


def load_health(
    path: str,
    date_col: str = "date",
    account_col: str = "account_id",
    score_col: str = "health_score",
    segment_col: str = "segment",
) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fields = reader.fieldnames or []
        c_date = _col(fields, date_col, "date", "timestamp", "time", "period")
        c_account = _col(fields, account_col, "account_id", "account", "customer", "id")
        c_score = _col(fields, score_col, "health_score", "score", "health", "value")
        c_seg = _col(fields, segment_col, "segment", "tier", "area", "group")

        if not c_date or not c_score:
            raise ValueError(
                f"Required column(s) not found. Need date and health_score (or score, health). "
                f"Columns in file: {list(fields)}"
            )

        for row in reader:
            dt = parse_date((row.get(c_date, "") or "").strip())
            score = _num(row.get(c_score, "") or "")
            if not dt:
                continue
            account = (row.get(c_account, "") or "").strip() or "—"
            segment = (row.get(c_seg, "") or "").strip() or "—"
            rows.append({
                "date": dt,
                "date_str": dt.strftime("%Y-%m-%d"),
                "account_id": account,
                "health_score": score,
                "segment": segment,
            })
    rows.sort(key=lambda r: (r["date"], r["account_id"]))
    return rows


def summarize(
    rows: List[Dict[str, Any]],
    at_risk_below: float,
    group_by_segment: bool,
) -> Dict[str, Any]:
    if not rows:
        return {
            "by_period": [],
            "avg_score": 0,
            "at_risk_count": 0,
            "trend_delta": None,
            "by_segment": {},
        }

    by_date: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for r in rows:
        by_date[r["date_str"]].append(r)

    periods_sorted = sorted(by_date.keys())
    by_period = []
    for p in periods_sorted:
        items = by_date[p]
        scores = [x["health_score"] for x in items]
        at_risk = sum(1 for s in scores if s < at_risk_below)
        avg = sum(scores) / len(scores) if scores else 0
        by_period.append({
            "period": p,
            "avg_score": round(avg, 1),
            "count": len(items),
            "at_risk_count": at_risk,
        })

    avg_scores = [x["avg_score"] for x in by_period]
    trend_delta: Optional[float] = None
    if len(avg_scores) >= 4:
        mid = len(avg_scores) // 2
        first = sum(avg_scores[:mid]) / mid
        second = sum(avg_scores[mid:]) / (len(avg_scores) - mid)
        trend_delta = round(second - first, 1)

    latest = by_period[-1] if by_period else {}
    total_at_risk = sum(x["at_risk_count"] for x in by_period)
    latest_at_risk = latest.get("at_risk_count", 0)

    by_segment: Dict[str, Dict[str, Any]] = {}
    if group_by_segment:
        by_seg: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        for r in rows:
            by_seg[r["segment"]].append(r)
        for seg, items in sorted(by_seg.items()):
            scores = [x["health_score"] for x in items]
            at_risk = sum(1 for s in scores if s < at_risk_below)
            avg = sum(scores) / len(scores) if scores else 0
            by_segment[seg] = {
                "avg_score": round(avg, 1),
                "count": len(items),
                "at_risk_count": at_risk,
            }

    return {
        "by_period": by_period,
        "periods": periods_sorted,
        "avg_score": round(sum(s["health_score"] for s in rows) / len(rows), 1),
        "at_risk_below": at_risk_below,
        "latest_at_risk": latest_at_risk,
        "total_at_risk_sum": total_at_risk,
        "trend_delta": trend_delta,
        "by_segment": by_segment,
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
    print("❤️  CUSTOMER HEALTH SCORE TREND")
    print("=" * 70)

    if not result.get("by_period"):
        print("\n   No health data in CSV (need date, health_score).\n")
        return

    print(f"\n   At-risk threshold: score < {result['at_risk_below']}")
    print(f"   Overall avg score: {result['avg_score']:.1f}")
    print(f"   Latest period at-risk: {result['latest_at_risk']} accounts")
    if result.get("trend_delta") is not None:
        print(f"   Trend: avg score {result['trend_delta']:+.1f} (2nd half vs 1st half)")

    print(f"\n   {'Period':<14} {'Avg score':>10} {'Count':>8} {'At-risk':>8}")
    print("   " + "─" * 44)
    for r in result["by_period"]:
        print(f"   {r['period']:<14} {r['avg_score']:>10.1f} {r['count']:>8} {r['at_risk_count']:>8}")

    if chart and result.get("by_period"):
        avgs = [x["avg_score"] for x in result["by_period"]]
        mn, mx = min(avgs), max(avgs)
        print(f"\n   Avg score trend:")
        print("   ", end="")
        for r in result["by_period"]:
            print(_bar(r["avg_score"], mn, mx, 6), end=" ")
        print(f"  ({mn:.1f} → {mx:.1f})")

    if result.get("by_segment"):
        print(f"\n   By segment:")
        for seg, s in result["by_segment"].items():
            print(f"      {seg:<16} avg={s['avg_score']:.1f}  at-risk={s['at_risk_count']}")

    print("\n   💡 Use with churn-risk-calculator for time-series health view.\n")


def to_json_result(result: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "by_period": result.get("by_period", []),
        "avg_score": result.get("avg_score", 0),
        "at_risk_below": result.get("at_risk_below", 50),
        "latest_at_risk": result.get("latest_at_risk", 0),
        "trend_delta": result.get("trend_delta"),
        "by_segment": result.get("by_segment", {}),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Track customer health score trend and at-risk count.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--csv", "-c", required=True, help="Path to health CSV (date, health_score)")
    parser.add_argument("--at-risk-below", type=float, default=50, metavar="N", help="Score below this = at-risk (default: 50)")
    parser.add_argument("--group-by", type=str, default=None, metavar="COL", help="Group by segment")
    parser.add_argument("--chart", action="store_true", help="Print avg score trend bars")
    parser.add_argument("--markdown", metavar="FILE", help="Write Markdown report to FILE")
    parser.add_argument("--output", "-o", metavar="FILE", help="Write JSON result to FILE")
    args = parser.parse_args()

    try:
        rows = load_health(args.csv)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    if not rows:
        print("No valid rows in CSV (need date, health_score).", file=sys.stderr)
        return 1

    result = summarize(rows, args.at_risk_below, group_by_segment=args.group_by is not None)
    print_report(result, args.chart)

    if args.markdown and result.get("by_period"):
        with open(args.markdown, "w", encoding="utf-8") as f:
            f.write("# Customer Health Score Trend\n\n")
            f.write(f"- **At-risk:** score < {result['at_risk_below']}\n")
            f.write(f"- **Overall avg:** {result['avg_score']:.1f}\n")
            f.write(f"- **Latest at-risk:** {result['latest_at_risk']}\n")
            trend_val = result.get('trend_delta')
            f.write(f"- **Trend:** {f'{trend_val:+.1f}' if trend_val is not None else '—'}\n\n")
            f.write("| Period | Avg score | Count | At-risk |\n")
            f.write("|--------|-----------|-------|--------|\n")
            for r in result["by_period"]:
                f.write(f"| {r['period']} | {r['avg_score']:.1f} | {r['count']} | {r['at_risk_count']} |\n")
        print(f"Wrote Markdown to {args.markdown}")

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(to_json_result(result), f, indent=2)
        print(f"Wrote JSON to {args.output}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
