#!/usr/bin/env python3
"""
Revenue Waterfall / MRR Decomposition

Decompose Monthly Recurring Revenue (MRR) into its moving parts:
    - New MRR       — revenue from new customers
    - Expansion MRR — upsells, cross-sells, upgrades from existing customers
    - Contraction   — downgrades, reduced usage
    - Churned MRR   — revenue lost from cancellations
    - Reactivation  — returning customers (optional)

Shows net MRR movement, health ratios, and projects forward based on trends.
Essential for SaaS PMs tracking growth quality and investor reporting.

Usage:
    # Inline monthly data
    python revenue-waterfall.py \\
        --month "Jan:50000:8000:3000:1500:2000:500" \\
        --month "Feb:57000:9000:3500:1800:2200:600" \\
        --month "Mar:66100:10000:4000:2000:2500:800"

    Format: "Label:starting_mrr:new:expansion:contraction:churn:reactivation"
    (reactivation is optional)

    # From CSV
    python revenue-waterfall.py --csv mrr_data.csv

    # Quick single-month analysis
    python revenue-waterfall.py \\
        --starting-mrr 100000 \\
        --new 12000 --expansion 5000 \\
        --contraction 2000 --churn 3500 --reactivation 800

CSV format:
    month,starting_mrr,new,expansion,contraction,churn,reactivation
    2024-01,50000,8000,3000,1500,2000,500
    2024-02,57000,9000,3500,1800,2200,600

    Required: month, starting_mrr, new
    Optional: expansion, contraction, churn, reactivation

Requirements:
    None (stdlib only).
"""

import argparse
import csv
import json
import sys
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# MRR decomposition
# ---------------------------------------------------------------------------

def decompose_month(
    label: str,
    starting_mrr: float,
    new: float,
    expansion: float = 0,
    contraction: float = 0,
    churn: float = 0,
    reactivation: float = 0,
) -> Dict[str, Any]:
    """Decompose a single month's MRR movement."""
    gross_new = new + expansion + reactivation
    gross_loss = contraction + churn
    net_new = gross_new - gross_loss
    ending_mrr = starting_mrr + net_new

    # Ratios
    quick_ratio = gross_new / gross_loss if gross_loss > 0 else float("inf")
    net_retention = (starting_mrr + expansion - contraction - churn) / starting_mrr * 100 if starting_mrr > 0 else 100
    gross_retention = (starting_mrr - churn) / starting_mrr * 100 if starting_mrr > 0 else 100
    logo_churn_pct = churn / starting_mrr * 100 if starting_mrr > 0 else 0
    growth_rate = net_new / starting_mrr * 100 if starting_mrr > 0 else 0

    return {
        "label": label,
        "starting_mrr": round(starting_mrr, 2),
        "new": round(new, 2),
        "expansion": round(expansion, 2),
        "contraction": round(contraction, 2),
        "churn": round(churn, 2),
        "reactivation": round(reactivation, 2),
        "gross_new": round(gross_new, 2),
        "gross_loss": round(gross_loss, 2),
        "net_new": round(net_new, 2),
        "ending_mrr": round(ending_mrr, 2),
        "quick_ratio": round(quick_ratio, 2) if quick_ratio != float("inf") else None,
        "net_retention_pct": round(net_retention, 1),
        "gross_retention_pct": round(gross_retention, 1),
        "logo_churn_pct": round(logo_churn_pct, 1),
        "growth_rate_pct": round(growth_rate, 1),
    }


def analyze_trends(months: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Analyze trends across multiple months."""
    if len(months) < 2:
        return {"trend": "insufficient_data", "months_analyzed": len(months)}

    n = len(months)

    # Averages
    avg_new = sum(m["new"] for m in months) / n
    avg_expansion = sum(m["expansion"] for m in months) / n
    avg_contraction = sum(m["contraction"] for m in months) / n
    avg_churn = sum(m["churn"] for m in months) / n
    avg_net_new = sum(m["net_new"] for m in months) / n
    avg_growth = sum(m["growth_rate_pct"] for m in months) / n

    quick_ratios = [m["quick_ratio"] for m in months if m["quick_ratio"] is not None]
    avg_quick_ratio = sum(quick_ratios) / len(quick_ratios) if quick_ratios else None

    net_retentions = [m["net_retention_pct"] for m in months]
    avg_ndr = sum(net_retentions) / len(net_retentions)

    # Trends (compare first half to second half)
    mid = n // 2
    first_half = months[:mid] if mid > 0 else months[:1]
    second_half = months[mid:]

    new_trend = sum(m["new"] for m in second_half) / len(second_half) - \
                sum(m["new"] for m in first_half) / len(first_half)
    churn_trend = sum(m["churn"] for m in second_half) / len(second_half) - \
                  sum(m["churn"] for m in first_half) / len(first_half)

    # Net MRR growth direction
    mrr_values = [m["ending_mrr"] for m in months]
    mrr_increasing = mrr_values[-1] > mrr_values[0]

    # Implied annual run rate
    latest = months[-1]["ending_mrr"]
    arr = latest * 12

    return {
        "months_analyzed": n,
        "starting_mrr": months[0]["starting_mrr"],
        "ending_mrr": months[-1]["ending_mrr"],
        "total_net_new": round(sum(m["net_new"] for m in months), 2),
        "arr": round(arr, 2),
        "avg_new": round(avg_new, 2),
        "avg_expansion": round(avg_expansion, 2),
        "avg_contraction": round(avg_contraction, 2),
        "avg_churn": round(avg_churn, 2),
        "avg_net_new": round(avg_net_new, 2),
        "avg_growth_pct": round(avg_growth, 1),
        "avg_quick_ratio": round(avg_quick_ratio, 2) if avg_quick_ratio else None,
        "avg_ndr": round(avg_ndr, 1),
        "new_trend_direction": "up" if new_trend > 0 else "down",
        "churn_trend_direction": "up" if churn_trend > 0 else "down",
        "mrr_direction": "growing" if mrr_increasing else "shrinking",
    }


def project_forward(
    months: List[Dict[str, Any]],
    n_months: int = 6,
) -> List[Dict[str, Any]]:
    """Project MRR forward based on recent averages."""
    if len(months) < 2:
        return []

    recent = months[-3:] if len(months) >= 3 else months
    avg_new = sum(m["new"] for m in recent) / len(recent)
    avg_expansion = sum(m["expansion"] for m in recent) / len(recent)
    avg_contraction = sum(m["contraction"] for m in recent) / len(recent)
    avg_churn = sum(m["churn"] for m in recent) / len(recent)
    avg_reactivation = sum(m["reactivation"] for m in recent) / len(recent)

    projections = []
    current_mrr = months[-1]["ending_mrr"]

    for i in range(1, n_months + 1):
        gross_new = avg_new + avg_expansion + avg_reactivation
        gross_loss = avg_contraction + avg_churn
        net_new = gross_new - gross_loss
        ending_mrr = current_mrr + net_new

        projections.append({
            "month": f"P+{i}",
            "starting_mrr": round(current_mrr, 2),
            "net_new": round(net_new, 2),
            "ending_mrr": round(ending_mrr, 2),
        })
        current_mrr = ending_mrr

    return projections


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def parse_month_string(s: str) -> Dict[str, Any]:
    """Parse 'Label:starting:new:expansion:contraction:churn:reactivation'."""
    parts = s.split(":")
    if len(parts) < 4:
        raise ValueError(
            f"Invalid month data '{s}'. "
            "Format: Label:starting_mrr:new:expansion:contraction:churn[:reactivation]"
        )
    try:
        label = parts[0].strip()
        starting = float(parts[1].strip())
        new = float(parts[2].strip())
        expansion = float(parts[3].strip()) if len(parts) > 3 else 0
        contraction = float(parts[4].strip()) if len(parts) > 4 else 0
        churn = float(parts[5].strip()) if len(parts) > 5 else 0
        reactivation = float(parts[6].strip()) if len(parts) > 6 else 0
    except (ValueError, IndexError) as e:
        raise ValueError(f"Invalid numbers in '{s}': {e}")

    return decompose_month(label, starting, new, expansion, contraction, churn, reactivation)


def _col(fieldnames: List[str], *aliases: str) -> Optional[str]:
    lower_map = {f.lower().strip(): f for f in fieldnames}
    for alias in aliases:
        if alias.lower().strip() in lower_map:
            return lower_map[alias.lower().strip()]
    return None


def load_csv(path: str) -> List[Dict[str, Any]]:
    """Load MRR data from CSV."""
    months: List[Dict[str, Any]] = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fields = reader.fieldnames or []

        c_label = _col(fields, "month", "period", "date", "label")
        c_starting = _col(fields, "starting_mrr", "start_mrr", "beginning_mrr", "opening_mrr", "mrr")
        c_new = _col(fields, "new", "new_mrr", "new_revenue")
        c_expansion = _col(fields, "expansion", "expansion_mrr", "upsell", "upgrade")
        c_contraction = _col(fields, "contraction", "contraction_mrr", "downgrade")
        c_churn = _col(fields, "churn", "churned_mrr", "churn_mrr", "lost")
        c_reactivation = _col(fields, "reactivation", "reactivation_mrr", "winback", "reactivated")

        for row in reader:
            label = row.get(c_label or "month", "").strip()
            if not label:
                continue

            def _num(col_name: Optional[str], default: float = 0) -> float:
                if not col_name:
                    return default
                raw = row.get(col_name, "").strip().replace(",", "").replace("$", "")
                if not raw:
                    return default
                try:
                    return float(raw)
                except ValueError:
                    return default

            starting = _num(c_starting)
            new = _num(c_new)
            expansion = _num(c_expansion)
            contraction = _num(c_contraction)
            churn = _num(c_churn)
            reactivation = _num(c_reactivation)

            months.append(decompose_month(label, starting, new, expansion, contraction, churn, reactivation))

    return months


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def _fmt_money(val: float) -> str:
    if abs(val) >= 1_000_000:
        return f"${val / 1_000_000:,.1f}M"
    elif abs(val) >= 1_000:
        return f"${val / 1_000:,.1f}K"
    else:
        return f"${val:,.0f}"


def _bar(value: float, max_val: float, width: int = 20) -> str:
    if max_val <= 0:
        return "░" * width
    ratio = min(1.0, max(0.0, value / max_val))
    filled = int(ratio * width)
    return "█" * filled + "░" * (width - filled)


def _signed(val: float) -> str:
    if val >= 0:
        return f"+{_fmt_money(val)}"
    return f"-{_fmt_money(abs(val))}"


def print_report(
    months: List[Dict[str, Any]],
    trends: Optional[Dict[str, Any]],
    projections: Optional[List[Dict[str, Any]]],
) -> None:
    """Pretty-print MRR waterfall analysis."""
    print("\n" + "=" * 78)
    print("💧 REVENUE WATERFALL / MRR DECOMPOSITION")
    print("=" * 78)

    # Single-month view
    if len(months) == 1:
        m = months[0]
        print(f"\n📋 MONTH: {m['label']}")
        print(f"\n   Starting MRR:   {_fmt_money(m['starting_mrr'])}")
        print(f"\n   ➕ New:          {_signed(m['new'])}")
        print(f"   ➕ Expansion:    {_signed(m['expansion'])}")
        print(f"   ➕ Reactivation: {_signed(m['reactivation'])}")
        print(f"   ➖ Contraction:  -{_fmt_money(m['contraction'])}")
        print(f"   ➖ Churn:        -{_fmt_money(m['churn'])}")
        print(f"\n   Net new MRR:    {_signed(m['net_new'])}")
        print(f"   Ending MRR:     {_fmt_money(m['ending_mrr'])}")

        print(f"\n   📊 KEY RATIOS:")
        qr = m['quick_ratio']
        qr_str = f"{qr:.2f}" if qr is not None else "∞"
        qr_health = "🟢 Healthy (>4)" if qr and qr > 4 else "🟡 Okay (2-4)" if qr and qr > 2 else "🔴 Concerning (<2)" if qr else "🟢 No loss"
        print(f"   Quick ratio:       {qr_str}  {qr_health}")
        print(f"   Net retention:     {m['net_retention_pct']:.1f}%  {'🟢 >100%' if m['net_retention_pct'] > 100 else '🔴 <100%'}")
        print(f"   Gross retention:   {m['gross_retention_pct']:.1f}%  {'🟢 >90%' if m['gross_retention_pct'] > 90 else '🔴 <90%'}")
        print(f"   MRR growth:        {m['growth_rate_pct']:.1f}%")
        print(f"   Logo churn:        {m['logo_churn_pct']:.1f}%")

    # Multi-month view
    if len(months) > 1:
        print(f"\n{'─'*78}")
        print(f"\n📅 MRR WATERFALL ({len(months)} months):\n")

        # Table header
        print(f"   {'Month':<10} {'Start':>10} {'New':>8} {'Exp':>8} {'Contr':>8} {'Churn':>8} {'React':>8} {'Net':>9} {'End':>10}")
        print(f"   {'─'*10} {'─'*10} {'─'*8} {'─'*8} {'─'*8} {'─'*8} {'─'*8} {'─'*9} {'─'*10}")

        for m in months:
            net_sign = "+" if m["net_new"] >= 0 else ""
            print(
                f"   {m['label'][:10]:<10} "
                f"{_fmt_money(m['starting_mrr']):>10} "
                f"{_fmt_money(m['new']):>8} "
                f"{_fmt_money(m['expansion']):>8} "
                f"{_fmt_money(m['contraction']):>8} "
                f"{_fmt_money(m['churn']):>8} "
                f"{_fmt_money(m['reactivation']):>8} "
                f"{net_sign}{_fmt_money(m['net_new']):>8} "
                f"{_fmt_money(m['ending_mrr']):>10}"
            )

        # Visual waterfall for the latest month
        m = months[-1]
        print(f"\n   📊 LATEST MONTH ({m['label']}) WATERFALL:")
        max_comp = max(m["new"], m["expansion"], m["contraction"], m["churn"], m["reactivation"], 1)
        print(f"   New          {_bar(m['new'], max_comp, 25)} {_fmt_money(m['new'])}")
        print(f"   Expansion    {_bar(m['expansion'], max_comp, 25)} {_fmt_money(m['expansion'])}")
        print(f"   Reactivation {_bar(m['reactivation'], max_comp, 25)} {_fmt_money(m['reactivation'])}")
        print(f"   Contraction  {_bar(m['contraction'], max_comp, 25)} -{_fmt_money(m['contraction'])}")
        print(f"   Churn        {_bar(m['churn'], max_comp, 25)} -{_fmt_money(m['churn'])}")

        # Key ratios over time
        print(f"\n   📈 KEY RATIOS OVER TIME:\n")
        print(f"   {'Month':<10} {'Quick Ratio':>12} {'Net Ret':>10} {'Gross Ret':>10} {'Growth':>8}")
        print(f"   {'─'*10} {'─'*12} {'─'*10} {'─'*10} {'─'*8}")

        for m in months:
            qr = f"{m['quick_ratio']:.2f}" if m['quick_ratio'] is not None else "∞"
            print(
                f"   {m['label'][:10]:<10} "
                f"{qr:>12} "
                f"{m['net_retention_pct']:>9.1f}% "
                f"{m['gross_retention_pct']:>9.1f}% "
                f"{m['growth_rate_pct']:>7.1f}%"
            )

        # MRR sparkline
        vals = [m["ending_mrr"] for m in months]
        blocks = " ▁▂▃▄▅▆▇█"
        mx = max(vals) if vals else 1
        mn = min(vals) if vals else 0
        rng = mx - mn if mx > mn else 1
        spark = "".join(blocks[min(8, int((v - mn) / rng * 8))] for v in vals)
        print(f"\n   MRR trend: {spark}  ({_fmt_money(vals[0])} → {_fmt_money(vals[-1])})")

    # Trends
    if trends and trends.get("months_analyzed", 0) >= 2:
        print(f"\n{'─'*78}")
        print(f"\n📊 TREND ANALYSIS ({trends['months_analyzed']} months):\n")
        print(f"   MRR journey:      {_fmt_money(trends['starting_mrr'])} → {_fmt_money(trends['ending_mrr'])} ({_signed(trends['total_net_new'])})")
        print(f"   ARR (run rate):   {_fmt_money(trends['arr'])}")
        print(f"   Direction:        {'📈 ' + trends['mrr_direction'].upper() if trends['mrr_direction'] == 'growing' else '📉 ' + trends['mrr_direction'].upper()}")
        print(f"\n   Averages:")
        print(f"   Avg new MRR:      {_fmt_money(trends['avg_new'])}/mo")
        print(f"   Avg expansion:    {_fmt_money(trends['avg_expansion'])}/mo")
        print(f"   Avg contraction:  {_fmt_money(trends['avg_contraction'])}/mo")
        print(f"   Avg churn:        {_fmt_money(trends['avg_churn'])}/mo")
        print(f"   Avg net new:      {_signed(trends['avg_net_new'])}/mo")
        print(f"   Avg growth:       {trends['avg_growth_pct']:.1f}%/mo")

        if trends["avg_quick_ratio"]:
            qr = trends["avg_quick_ratio"]
            print(f"\n   Avg quick ratio:  {qr:.2f}  ", end="")
            if qr > 4:
                print("🟢 Excellent — strong growth vs. loss")
            elif qr > 2:
                print("🟡 Healthy — growth outpaces loss")
            else:
                print("🔴 Concerning — losses approaching gains")

        ndr = trends["avg_ndr"]
        print(f"   Avg net retention: {ndr:.1f}%  ", end="")
        if ndr > 120:
            print("🟢 Best-in-class")
        elif ndr > 100:
            print("🟢 Net positive retention")
        elif ndr > 90:
            print("🟡 Revenue eroding slowly")
        else:
            print("🔴 Significant revenue leak")

        # Trend signals
        signals = []
        if trends["new_trend_direction"] == "up":
            signals.append("📈 New MRR accelerating")
        else:
            signals.append("📉 New MRR decelerating")

        if trends["churn_trend_direction"] == "up":
            signals.append("⚠️  Churn increasing — investigate causes")
        else:
            signals.append("✅ Churn decreasing — retention improving")

        if signals:
            print(f"\n   Signals:")
            for s in signals:
                print(f"   {s}")

    # Projections
    if projections:
        print(f"\n{'─'*78}")
        print(f"\n🔮 MRR PROJECTION (next {len(projections)} months, based on recent averages):\n")
        print(f"   {'Month':>8} {'Starting':>12} {'Net New':>10} {'Ending':>12}")
        print(f"   {'─'*8} {'─'*12} {'─'*10} {'─'*12}")

        for p in projections:
            print(f"   {p['month']:>8} {_fmt_money(p['starting_mrr']):>12} {_signed(p['net_new']):>10} {_fmt_money(p['ending_mrr']):>12}")

        final_arr = projections[-1]["ending_mrr"] * 12
        print(f"\n   Projected ARR in {len(projections)} months: {_fmt_money(final_arr)}")

    # Guidance
    print(f"\n{'─'*78}")
    print(f"\n💡 BENCHMARKS:")
    print(f"   • Quick ratio >4 = best-in-class, 2-4 = healthy, <2 = concerning")
    print(f"   • Net dollar retention >120% = elite, 100-120% = good, <100% = leaking")
    print(f"   • Gross retention >90% = healthy for SaaS, <85% = red flag")
    print(f"   • Monthly logo churn <2% for enterprise, <5% for SMB")
    print(f"   • Expansion > Churn = 'negative churn' — the gold standard")
    print("\n" + "=" * 78)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Decompose MRR into new, expansion, contraction, churn, and reactivation. "
                    "Track revenue quality and project forward.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --starting-mrr 100000 --new 12000 --expansion 5000 --contraction 2000 --churn 3500
  %(prog)s --month "Jan:50000:8000:3000:1500:2000:500" --month "Feb:57000:9000:3500:1800:2200:600"
  %(prog)s --csv mrr_data.csv --project 6
        """,
    )

    # Single month
    parser.add_argument("--starting-mrr", type=float, help="Starting MRR for single-month mode")
    parser.add_argument("--new", type=float, help="New MRR")
    parser.add_argument("--expansion", type=float, default=0, help="Expansion MRR")
    parser.add_argument("--contraction", type=float, default=0, help="Contraction MRR")
    parser.add_argument("--churn", type=float, default=0, help="Churned MRR")
    parser.add_argument("--reactivation", type=float, default=0, help="Reactivation MRR")

    # Multi-month
    parser.add_argument("--month", type=str, action="append",
                        help="Month data: 'Label:start:new:exp:contr:churn[:react]'")
    parser.add_argument("--csv", "-c", type=str, help="CSV with monthly MRR data")

    # Projection
    parser.add_argument("--project", type=int, default=0,
                        help="Project forward N months (default: 0)")

    parser.add_argument("--output", "-o", type=str, help="Write JSON results to file")
    args = parser.parse_args()

    months: List[Dict[str, Any]] = []

    # Single-month mode
    if args.starting_mrr is not None and args.new is not None:
        m = decompose_month(
            "Current",
            args.starting_mrr,
            args.new,
            args.expansion,
            args.contraction,
            args.churn,
            args.reactivation,
        )
        months.append(m)

    # Multi-month inline
    if args.month:
        for ms in args.month:
            try:
                months.append(parse_month_string(ms))
            except ValueError as e:
                print(f"Error: {e}", file=sys.stderr)
                return 1

    # CSV
    if args.csv:
        try:
            csv_months = load_csv(args.csv)
            months.extend(csv_months)
        except Exception as e:
            print(f"Error loading CSV: {e}", file=sys.stderr)
            return 1

    if not months:
        print("Error: provide data via --starting-mrr + --new, --month, or --csv.", file=sys.stderr)
        parser.print_help(sys.stderr)
        return 1

    # Analysis
    trends = analyze_trends(months) if len(months) >= 2 else None
    projections = project_forward(months, args.project) if args.project > 0 and len(months) >= 2 else None

    # Report
    print_report(months, trends, projections)

    # JSON output
    if args.output:
        report: Dict[str, Any] = {
            "months": months,
        }
        if trends:
            report["trends"] = trends
        if projections:
            report["projections"] = projections
        with open(args.output, "w") as f:
            json.dump(report, f, indent=2)
        print(f"\n📁 Results saved to {args.output}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
