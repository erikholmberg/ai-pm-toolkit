#!/usr/bin/env python3
"""
Budget Burn Summary

Summarize budget vs actual from CSV: spend to date, variance vs plan, and run rate.
Lightweight budget tracking for PM/ops and program reviews.

Usage:
    # Basic (period, planned, actual)
    python budget-burn-summary.py --csv budget.csv

    # Group by category
    python budget-burn-summary.py --csv budget.csv --group-by category

    # Export
    python budget-burn-summary.py --csv budget.csv --markdown report.md --output report.json

CSV format:
    period,planned,actual,category
    2025-01,10000,9500,Engineering
    2025-02,10000,10200,Engineering
    2025-01,3000,3200,Marketing

    Required: period (e.g. 2025-01 or Jan 2025), planned, actual.
    Optional: category (or area) for --group-by. Amounts: numbers, no currency symbol.

Requirements:
    None (stdlib only).
"""

import argparse
import csv
import json
import sys
from collections import defaultdict
from typing import Any, Dict, List, Optional


def _col(fieldnames: List[str], *aliases: str) -> Optional[str]:
    lower_map = {f.lower().strip(): f for f in fieldnames}
    for alias in aliases:
        if alias.lower().strip() in lower_map:
            return lower_map[alias.lower().strip()]
    return None


def parse_amount(val: str) -> float:
    if not val or not str(val).strip():
        return 0.0
    s = str(val).strip().replace(",", "").replace(" ", "").lstrip("$€£")
    try:
        return float(s)
    except ValueError:
        return 0.0


def load_budget(
    path: str,
    period_col: str = "period",
    planned_col: str = "planned",
    actual_col: str = "actual",
    category_col: str = "category",
) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fields = reader.fieldnames or []
        c_period = _col(fields, period_col, "period", "month", "date", "interval")
        c_planned = _col(fields, planned_col, "planned", "budget", "plan", "expected")
        c_actual = _col(fields, actual_col, "actual", "spend", "spent", "realized")
        c_cat = _col(fields, category_col, "category", "area", "team", "bucket")

        missing = []
        if not c_period:
            missing.append("period (or month, date, interval)")
        if not c_planned:
            missing.append("planned (or budget, plan, expected)")
        if not c_actual:
            missing.append("actual (or spend, spent, realized)")
        if missing:
            raise ValueError(
                f"Required column(s) not found in CSV: {', '.join(missing)}. "
                f"Columns in file: {list(fields)}"
            )

        for row in reader:
            period = (row.get(c_period, "") or "").strip()
            if not period:
                continue
            planned = parse_amount(row.get(c_planned, "") or "")
            actual = parse_amount(row.get(c_actual, "") or "")
            category = (row.get(c_cat or "category", "") or "").strip() or "—"
            rows.append({
                "period": period,
                "planned": planned,
                "actual": actual,
                "category": category,
            })
    rows.sort(key=lambda r: (r["period"], r["category"]))
    return rows


def summarize_burn(
    rows: List[Dict[str, Any]],
    group_by_category: bool,
) -> Dict[str, Any]:
    total_planned = sum(r["planned"] for r in rows)
    total_actual = sum(r["actual"] for r in rows)
    variance = total_actual - total_planned
    variance_pct = (variance / total_planned * 100) if total_planned else 0
    n_periods = len(set(r["period"] for r in rows)) or 1
    run_rate_actual = total_actual / n_periods if n_periods else 0
    run_rate_planned = total_planned / n_periods if n_periods else 0

    by_period: Dict[str, Dict[str, float]] = defaultdict(lambda: {"planned": 0, "actual": 0})
    for r in rows:
        by_period[r["period"]]["planned"] += r["planned"]
        by_period[r["period"]]["actual"] += r["actual"]
    periods_sorted = sorted(by_period.keys())
    by_period_list = [
        {
            "period": p,
            "planned": by_period[p]["planned"],
            "actual": by_period[p]["actual"],
            "variance": by_period[p]["actual"] - by_period[p]["planned"],
        }
        for p in periods_sorted
    ]

    by_category: Dict[str, Dict[str, Any]] = {}
    if group_by_category:
        by_cat: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        for r in rows:
            by_cat[r["category"]].append(r)
        for cat, items in sorted(by_cat.items()):
            p = sum(x["planned"] for x in items)
            a = sum(x["actual"] for x in items)
            v = a - p
            vp = (v / p * 100) if p else 0
            by_category[cat] = {
                "planned": round(p, 2),
                "actual": round(a, 2),
                "variance": round(v, 2),
                "variance_pct": round(vp, 1),
            }

    return {
        "total_planned": round(total_planned, 2),
        "total_actual": round(total_actual, 2),
        "variance": round(variance, 2),
        "variance_pct": round(variance_pct, 1),
        "n_periods": n_periods,
        "run_rate_planned": round(run_rate_planned, 2),
        "run_rate_actual": round(run_rate_actual, 2),
        "by_period": by_period_list,
        "by_category": by_category,
    }


def print_report(result: Dict[str, Any]) -> None:
    print("\n" + "=" * 70)
    print("💰 BUDGET BURN SUMMARY")
    print("=" * 70)

    total_planned = result["total_planned"]
    total_actual = result["total_actual"]
    variance = result["variance"]
    variance_pct = result["variance_pct"]
    print(f"\n   Total planned:  {total_planned:,.2f}")
    print(f"   Total actual:   {total_actual:,.2f}")
    print(f"   Variance:       {variance:+,.2f}  ({variance_pct:+.1f}%)")
    print(f"   Run rate:       {result['run_rate_actual']:,.2f} actual / {result['run_rate_planned']:,.2f} planned per period ({result['n_periods']} periods)")

    if result.get("by_period"):
        print(f"\n   {'Period':<14} {'Planned':>12} {'Actual':>12} {'Variance':>12}")
        print("   " + "─" * 52)
        for r in result["by_period"]:
            print(f"   {r['period']:<14} {r['planned']:>12,.2f} {r['actual']:>12,.2f} {r['variance']:>+12,.2f}")

    if result.get("by_category"):
        print(f"\n   By category:")
        print(f"   {'Category':<18} {'Planned':>12} {'Actual':>12} {'Var %':>8}")
        print("   " + "─" * 52)
        for cat, s in result["by_category"].items():
            print(f"   {cat:<18} {s['planned']:>12,.2f} {s['actual']:>12,.2f} {s['variance_pct']:>+7.1f}%")

    print("\n   💡 Use for program and ops budget tracking.\n")


def to_json_result(result: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "total_planned": result["total_planned"],
        "total_actual": result["total_actual"],
        "variance": result["variance"],
        "variance_pct": result["variance_pct"],
        "n_periods": result["n_periods"],
        "run_rate_planned": result["run_rate_planned"],
        "run_rate_actual": result["run_rate_actual"],
        "by_period": result.get("by_period", []),
        "by_category": result.get("by_category", {}),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Budget vs actual: variance, run rate, optional by category.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--csv", "-c", required=True, help="Path to budget CSV (period, planned, actual)")
    parser.add_argument("--group-by", type=str, default=None, metavar="COL", help="Group by category/area")
    parser.add_argument("--markdown", metavar="FILE", help="Write Markdown report to FILE")
    parser.add_argument("--output", "-o", metavar="FILE", help="Write JSON result to FILE")
    args = parser.parse_args()

    try:
        rows = load_budget(args.csv)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    if not rows:
        print("No valid rows in CSV (need period, planned, actual).", file=sys.stderr)
        return 1

    result = summarize_burn(rows, group_by_category=args.group_by is not None)
    print_report(result)

    if args.markdown:
        with open(args.markdown, "w", encoding="utf-8") as f:
            f.write("# Budget Burn Summary\n\n")
            f.write(f"- **Total planned:** {result['total_planned']:,.2f}\n")
            f.write(f"- **Total actual:** {result['total_actual']:,.2f}\n")
            f.write(f"- **Variance:** {result['variance']:+,.2f} ({result['variance_pct']:+.1f}%)\n")
            f.write(f"- **Run rate:** {result['run_rate_actual']:,.2f} actual / {result['run_rate_planned']:,.2f} planned per period\n\n")
            f.write("| Period | Planned | Actual | Variance |\n")
            f.write("|--------|---------|--------|----------|\n")
            for r in result.get("by_period", []):
                f.write(f"| {r['period']} | {r['planned']:,.2f} | {r['actual']:,.2f} | {r['variance']:+,.2f} |\n")
            if result.get("by_category"):
                f.write("\n## By category\n\n")
                f.write("| Category | Planned | Actual | Var % |\n")
                f.write("|----------|---------|--------|-------|\n")
                for cat, s in result["by_category"].items():
                    f.write(f"| {cat} | {s['planned']:,.2f} | {s['actual']:,.2f} | {s['variance_pct']:+.1f}% |\n")
        print(f"Wrote Markdown to {args.markdown}")

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(to_json_result(result), f, indent=2)
        print(f"Wrote JSON to {args.output}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
