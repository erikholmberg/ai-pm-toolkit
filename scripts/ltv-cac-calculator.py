#!/usr/bin/env python3
"""
LTV / CAC Calculator

Compute Customer Lifetime Value (LTV), Customer Acquisition Cost (CAC), and
LTV:CAC ratio from cohort revenue data. Supports multiple calculation methods
(simple, cohort-based, discounted) and produces a health assessment.

Usage:
    # Simple mode: key metrics directly
    python ltv-cac-calculator.py --arpu 50 --churn-rate 5 --gross-margin 70 --cac 200

    # With payback and growth context
    python ltv-cac-calculator.py --arpu 85 --churn-rate 3 --gross-margin 75 --cac 350 \\
        --discount-rate 10 --monthly-new-customers 500

    # Cohort mode: revenue per cohort over time from CSV
    python ltv-cac-calculator.py --csv cohorts.csv --cac 200

    # Multiple scenarios
    python ltv-cac-calculator.py --arpu 50 --churn-rate 5 --gross-margin 70 --cac 200 \\
        --scenarios --output report.json

CSV format — cohort mode (header row required):
    cohort,month_0,month_1,month_2,month_3,...,month_12
    Jan-25,10000,8500,7200,6800,...,4500
    Feb-25,12000,10200,8800,8100,...,5200

    Each row is a cohort; columns are total revenue from that cohort in each month.
    The calculator derives retention and revenue curves from the data.

Requirements:
    None (stdlib only).
"""

import argparse
import csv
import json
import math
import sys
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# LTV calculation methods
# ---------------------------------------------------------------------------

def ltv_simple(arpu: float, churn_rate_pct: float, gross_margin_pct: float = 100.0) -> Dict[str, float]:
    """
    Simple LTV = (ARPU × Gross Margin) / Churn Rate

    Args:
        arpu: Average Revenue Per User per month (USD).
        churn_rate_pct: Monthly churn rate (e.g. 5 = 5%).
        gross_margin_pct: Gross margin percentage (default 100%).

    Returns:
        Dict with ltv, avg_lifespan_months, monthly_contribution.
    """
    if churn_rate_pct <= 0:
        return {"ltv": float("inf"), "avg_lifespan_months": float("inf"), "monthly_contribution": arpu * gross_margin_pct / 100}

    churn = churn_rate_pct / 100.0
    margin = gross_margin_pct / 100.0
    monthly_contrib = arpu * margin
    avg_lifespan = 1.0 / churn  # months
    ltv = monthly_contrib * avg_lifespan

    return {
        "ltv": round(ltv, 2),
        "avg_lifespan_months": round(avg_lifespan, 1),
        "monthly_contribution": round(monthly_contrib, 2),
    }


def ltv_discounted(
    arpu: float,
    churn_rate_pct: float,
    gross_margin_pct: float = 100.0,
    annual_discount_rate_pct: float = 10.0,
    horizon_months: int = 60,
) -> Dict[str, float]:
    """
    Discounted LTV: sum of discounted monthly contributions over a horizon,
    accounting for retention decay.

    LTV = Σ (ARPU × Margin × Retention^t × Discount^t)  for t=0..horizon
    """
    churn = churn_rate_pct / 100.0
    margin = gross_margin_pct / 100.0
    monthly_discount = (1 + annual_discount_rate_pct / 100.0) ** (1 / 12) - 1
    monthly_contrib = arpu * margin

    ltv = 0.0
    retention = 1.0
    for t in range(horizon_months):
        discount_factor = 1.0 / ((1 + monthly_discount) ** t)
        ltv += monthly_contrib * retention * discount_factor
        retention *= (1 - churn)
        if retention < 0.001:
            break

    return {
        "ltv_discounted": round(ltv, 2),
        "discount_rate_annual": annual_discount_rate_pct,
        "horizon_months": horizon_months,
    }


def ltv_from_cohort(monthly_revenues: List[float]) -> Dict[str, Any]:
    """
    Compute LTV from a cohort's monthly revenue over time.

    monthly_revenues: [month0_revenue, month1_revenue, ...] for a cohort.
    Assumes month_0 is full revenue; subsequent months show retention effect.
    """
    if not monthly_revenues or monthly_revenues[0] <= 0:
        return {"ltv_cohort": 0, "retention_curve": [], "implied_churn_rates": []}

    base = monthly_revenues[0]
    retention_curve = [round(r / base, 4) for r in monthly_revenues]

    # Implied monthly churn rates
    churn_rates = []
    for i in range(1, len(retention_curve)):
        if retention_curve[i - 1] > 0:
            churn = 1 - (retention_curve[i] / retention_curve[i - 1])
            churn_rates.append(round(max(0, churn) * 100, 2))
        else:
            churn_rates.append(0.0)

    # LTV = sum of all monthly revenues per initial customer
    # (revenue is already for the whole cohort, so LTV per customer = sum / initial_customers)
    # Since we don't know customer count, LTV index = sum of retention curve
    ltv_index = sum(retention_curve)

    # Average monthly churn
    avg_churn = sum(churn_rates) / len(churn_rates) if churn_rates else 0

    return {
        "ltv_index": round(ltv_index, 2),
        "months_tracked": len(monthly_revenues),
        "retention_month_1": retention_curve[1] if len(retention_curve) > 1 else None,
        "retention_month_6": retention_curve[6] if len(retention_curve) > 6 else None,
        "retention_month_12": retention_curve[12] if len(retention_curve) > 12 else None,
        "avg_monthly_churn_pct": round(avg_churn, 2),
        "retention_curve": retention_curve,
        "implied_churn_rates": churn_rates,
    }


# ---------------------------------------------------------------------------
# CAC & ratio analysis
# ---------------------------------------------------------------------------

def cac_analysis(
    cac: float,
    ltv: float,
    monthly_contrib: float,
) -> Dict[str, Any]:
    """
    Compute LTV:CAC ratio, payback period, and health assessment.
    """
    if cac <= 0:
        return {
            "ltv_cac_ratio": float("inf"),
            "payback_months": 0,
            "health": "⚠️  CAC is zero — are you tracking acquisition costs?",
        }

    ratio = ltv / cac
    payback = cac / monthly_contrib if monthly_contrib > 0 else float("inf")

    # Health assessment
    if ratio >= 5:
        health = "🟢 Excellent — consider investing more in growth"
    elif ratio >= 3:
        health = "🟢 Healthy — sustainable unit economics"
    elif ratio >= 2:
        health = "🟡 Acceptable — monitor closely, optimize CAC or retention"
    elif ratio >= 1:
        health = "🟠 Warning — barely breaking even on acquisition"
    else:
        health = "🔴 Unsustainable — losing money on every customer"

    return {
        "ltv_cac_ratio": round(ratio, 2),
        "payback_months": round(payback, 1),
        "health": health,
    }


# ---------------------------------------------------------------------------
# Scenario analysis
# ---------------------------------------------------------------------------

def scenario_analysis(
    arpu: float,
    churn_rate_pct: float,
    gross_margin_pct: float,
    cac: float,
) -> Dict[str, Dict[str, Any]]:
    """Run best/base/worst scenarios with ±20% on key inputs."""
    scenarios = {
        "pessimistic": {
            "arpu": arpu * 0.8,
            "churn": churn_rate_pct * 1.3,
            "margin": gross_margin_pct * 0.9,
            "cac": cac * 1.2,
        },
        "base": {
            "arpu": arpu,
            "churn": churn_rate_pct,
            "margin": gross_margin_pct,
            "cac": cac,
        },
        "optimistic": {
            "arpu": arpu * 1.2,
            "churn": churn_rate_pct * 0.7,
            "margin": gross_margin_pct,
            "cac": cac * 0.85,
        },
    }

    results = {}
    for name, params in scenarios.items():
        ltv_data = ltv_simple(params["arpu"], params["churn"], params["margin"])
        cac_data = cac_analysis(params["cac"], ltv_data["ltv"], ltv_data["monthly_contribution"])
        results[name] = {
            "arpu": round(params["arpu"], 2),
            "churn_pct": round(params["churn"], 2),
            "cac": round(params["cac"], 2),
            "ltv": ltv_data["ltv"],
            "ltv_cac_ratio": cac_data["ltv_cac_ratio"],
            "payback_months": cac_data["payback_months"],
        }

    return results


# ---------------------------------------------------------------------------
# CSV loading
# ---------------------------------------------------------------------------

def load_cohort_csv(path: str) -> Dict[str, List[float]]:
    """Load cohort revenue data from CSV. Returns {cohort_name: [monthly_revenues]}."""
    cohorts: Dict[str, List[float]] = {}
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fields = reader.fieldnames or []
        # First column is cohort name, rest are month_0, month_1, ...
        cohort_col = fields[0]
        month_cols = [c for c in fields[1:] if c.lower().startswith("month")]
        if not month_cols:
            # Try numeric columns
            month_cols = fields[1:]

        for row in reader:
            name = row[cohort_col].strip()
            revenues = []
            for mc in month_cols:
                try:
                    revenues.append(float(row[mc]))
                except (ValueError, KeyError):
                    revenues.append(0.0)
            if revenues:
                cohorts[name] = revenues
    return cohorts


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def _bar(value: float, max_val: float, width: int = 25) -> str:
    if max_val <= 0:
        return "░" * width
    ratio = min(1.0, max(0.0, value / max_val))
    filled = int(ratio * width)
    return "█" * filled + "░" * (width - filled)


def print_report(
    arpu: float,
    churn_rate_pct: float,
    gross_margin_pct: float,
    cac: float,
    ltv_data: Dict[str, float],
    ltv_disc: Optional[Dict[str, float]],
    cac_data: Dict[str, Any],
    scenarios: Optional[Dict[str, Dict[str, Any]]],
    monthly_new_customers: Optional[int],
    cohort_results: Optional[Dict[str, Dict[str, Any]]],
) -> None:
    """Pretty-print LTV/CAC analysis."""
    print("\n" + "=" * 78)
    print("📊 LTV / CAC CALCULATOR")
    print("=" * 78)

    print(f"\n📋 INPUTS:")
    print(f"   • ARPU (monthly):        ${arpu:,.2f}")
    print(f"   • Monthly churn rate:    {churn_rate_pct:.1f}%")
    print(f"   • Gross margin:          {gross_margin_pct:.0f}%")
    print(f"   • CAC:                   ${cac:,.2f}")
    if monthly_new_customers:
        print(f"   • New customers/month:   {monthly_new_customers:,}")

    print(f"\n💰 CUSTOMER LIFETIME VALUE:")
    print(f"   • Monthly contribution:  ${ltv_data['monthly_contribution']:,.2f}  (ARPU × margin)")
    print(f"   • Avg lifespan:          {ltv_data['avg_lifespan_months']:.1f} months")
    print(f"   • LTV (simple):          ${ltv_data['ltv']:,.2f}")
    if ltv_disc:
        print(f"   • LTV (discounted):      ${ltv_disc['ltv_discounted']:,.2f}  ({ltv_disc['discount_rate_annual']:.0f}% annual, {ltv_disc['horizon_months']}mo horizon)")

    print(f"\n📈 UNIT ECONOMICS:")
    print(f"   • LTV : CAC ratio:       {cac_data['ltv_cac_ratio']:.1f}x")
    print(f"   • Payback period:        {cac_data['payback_months']:.1f} months")
    print(f"   • {cac_data['health']}")

    # Visual ratio gauge
    ratio = min(cac_data["ltv_cac_ratio"], 6)
    gauge_bar = _bar(ratio, 6, 30)
    markers = "1x        2x        3x        4x        5x       6x+"
    print(f"\n   LTV:CAC  {gauge_bar}")
    print(f"            {markers}")
    if cac_data["ltv_cac_ratio"] < 3:
        print(f"            {'↑':>{int(ratio / 6 * 30) + 1}} ({cac_data['ltv_cac_ratio']:.1f}x)")

    # Monthly economics
    if monthly_new_customers:
        monthly_acq_cost = cac * monthly_new_customers
        monthly_ltv_created = ltv_data["ltv"] * monthly_new_customers
        net_value_created = monthly_ltv_created - monthly_acq_cost
        print(f"\n📊 MONTHLY ECONOMICS ({monthly_new_customers:,} new customers):")
        print(f"   • Acquisition spend:     ${monthly_acq_cost:,.2f}")
        print(f"   • LTV created:           ${monthly_ltv_created:,.2f}")
        print(f"   • Net value created:     ${net_value_created:,.2f}")
        annual_net = net_value_created * 12
        print(f"   • Annualized:            ${annual_net:,.2f}")

    # Cohort analysis
    if cohort_results:
        print(f"\n📐 COHORT ANALYSIS:")
        for name, cdata in cohort_results.items():
            retention_m1 = cdata.get("retention_month_1")
            avg_churn = cdata.get("avg_monthly_churn_pct", 0)
            print(f"\n   {name}:")
            print(f"      Months tracked:     {cdata['months_tracked']}")
            if retention_m1 is not None:
                print(f"      Month-1 retention:  {retention_m1:.0%}")
            r6 = cdata.get("retention_month_6")
            if r6 is not None:
                print(f"      Month-6 retention:  {r6:.0%}")
            r12 = cdata.get("retention_month_12")
            if r12 is not None:
                print(f"      Month-12 retention: {r12:.0%}")
            print(f"      Avg monthly churn:  {avg_churn:.1f}%")
            print(f"      LTV index:          {cdata['ltv_index']:.1f}× initial month")

            # Mini retention curve
            curve = cdata.get("retention_curve", [])
            if len(curve) >= 3:
                max_months = min(12, len(curve))
                curve_str = " ".join(f"{curve[i]:.0%}" if i < max_months else "" for i in range(max_months))
                print(f"      Retention curve:    {curve_str}")

    # Scenarios
    if scenarios:
        print(f"\n🎯 SCENARIO ANALYSIS:")
        print(f"   {'Scenario':<14} {'ARPU':>8} {'Churn':>7} {'CAC':>8} {'LTV':>10} {'LTV:CAC':>9} {'Payback':>9}")
        print(f"   {'─'*14} {'─'*8} {'─'*7} {'─'*8} {'─'*10} {'─'*9} {'─'*9}")
        for name in ["pessimistic", "base", "optimistic"]:
            s = scenarios[name]
            emoji = {"pessimistic": "📉", "base": "📊", "optimistic": "📈"}[name]
            print(
                f"   {emoji} {name:<12} ${s['arpu']:>6,.0f} {s['churn_pct']:>5.1f}% "
                f"${s['cac']:>6,.0f} ${s['ltv']:>8,.0f} {s['ltv_cac_ratio']:>8.1f}x {s['payback_months']:>7.1f}mo"
            )

    # Benchmarks
    print(f"\n💡 BENCHMARKS & TIPS:")
    print(f"   • LTV:CAC ≥ 3x is healthy for SaaS (target 3-5x)")
    print(f"   • Payback < 12 months is good; < 6 months is great")
    print(f"   • LTV:CAC > 5x may mean you're under-investing in growth")
    print(f"   • Improve LTV: reduce churn, increase ARPU (upsell, expansion)")
    print(f"   • Reduce CAC: improve conversion, refine targeting, organic channels")
    print("\n" + "=" * 78)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Calculate Customer Lifetime Value (LTV), Customer Acquisition Cost (CAC), "
                    "and LTV:CAC ratio with health assessment.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --arpu 50 --churn-rate 5 --gross-margin 70 --cac 200
  %(prog)s --arpu 85 --churn-rate 3 --gross-margin 75 --cac 350 --discount-rate 10
  %(prog)s --csv cohorts.csv --cac 200 --arpu 50 --churn-rate 5 --gross-margin 70
  %(prog)s --arpu 50 --churn-rate 5 --gross-margin 70 --cac 200 --scenarios
        """,
    )
    parser.add_argument("--arpu", type=float, help="Average Revenue Per User per month (USD)")
    parser.add_argument("--churn-rate", type=float, help="Monthly churn rate (e.g. 5 = 5%%)")
    parser.add_argument("--gross-margin", type=float, default=100.0, help="Gross margin %% (default: 100)")
    parser.add_argument("--cac", type=float, default=0.0, help="Customer Acquisition Cost (USD)")
    parser.add_argument("--discount-rate", type=float, help="Annual discount rate %% for discounted LTV (e.g. 10)")
    parser.add_argument("--monthly-new-customers", type=int, help="New customers acquired per month (for monthly economics)")
    parser.add_argument("--csv", type=str, help="CSV file with cohort revenue data")
    parser.add_argument("--scenarios", action="store_true", help="Run best/base/worst scenario analysis")
    parser.add_argument("--output", "-o", type=str, help="Write report to JSON file")
    args = parser.parse_args()

    if not args.arpu and not args.csv:
        print("Error: provide --arpu (and --churn-rate) or --csv for cohort analysis.", file=sys.stderr)
        parser.print_help(sys.stderr)
        return 1

    if args.arpu and not args.churn_rate:
        print("Error: --churn-rate is required with --arpu.", file=sys.stderr)
        return 1

    # Simple / discounted LTV
    ltv_data = None
    ltv_disc = None
    cac_data = None
    scenarios = None
    cohort_results = None

    if args.arpu:
        ltv_data = ltv_simple(args.arpu, args.churn_rate, args.gross_margin)

        if args.discount_rate:
            ltv_disc = ltv_discounted(args.arpu, args.churn_rate, args.gross_margin, args.discount_rate)

        cac_data = cac_analysis(args.cac, ltv_data["ltv"], ltv_data["monthly_contribution"])

        if args.scenarios:
            scenarios = scenario_analysis(args.arpu, args.churn_rate, args.gross_margin, args.cac)

    # Cohort analysis
    if args.csv:
        try:
            cohorts = load_cohort_csv(args.csv)
        except Exception as e:
            print(f"Error loading CSV: {e}", file=sys.stderr)
            return 1

        if not cohorts:
            print("Error: no valid cohort data found.", file=sys.stderr)
            return 1

        cohort_results = {name: ltv_from_cohort(revs) for name, revs in cohorts.items()}

        # If no simple LTV provided, derive from cohort averages
        if not ltv_data:
            avg_churn = sum(c["avg_monthly_churn_pct"] for c in cohort_results.values()) / len(cohort_results)
            ltv_data = ltv_simple(args.arpu or 0, avg_churn, args.gross_margin)
            cac_data = cac_analysis(args.cac, ltv_data["ltv"], ltv_data["monthly_contribution"])

    # Guard: ensure ltv_data was computed before printing
    if ltv_data is None:
        print("Error: could not compute LTV. Provide --arpu/--churn-rate or a valid --csv.", file=sys.stderr)
        return 1
    if cac_data is None:
        cac_data = cac_analysis(args.cac, ltv_data["ltv"], ltv_data["monthly_contribution"])

    # Print report
    print_report(
        arpu=args.arpu or 0,
        churn_rate_pct=args.churn_rate or 0,
        gross_margin_pct=args.gross_margin,
        cac=args.cac,
        ltv_data=ltv_data,
        ltv_disc=ltv_disc,
        cac_data=cac_data,
        scenarios=scenarios,
        monthly_new_customers=args.monthly_new_customers,
        cohort_results=cohort_results,
    )

    # JSON output
    if args.output:
        report: Dict[str, Any] = {
            "inputs": {
                "arpu": args.arpu,
                "churn_rate_pct": args.churn_rate,
                "gross_margin_pct": args.gross_margin,
                "cac": args.cac,
            },
            "ltv": ltv_data,
            "cac_analysis": cac_data,
        }
        if ltv_disc:
            report["ltv_discounted"] = ltv_disc
        if scenarios:
            report["scenarios"] = scenarios
        if cohort_results:
            report["cohort_analysis"] = cohort_results
        with open(args.output, "w") as f:
            json.dump(report, f, indent=2)
        print(f"\n📁 Report saved to {args.output}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
