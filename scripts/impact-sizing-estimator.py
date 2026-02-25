#!/usr/bin/env python3
"""
Impact Sizing Estimator

Quick back-of-envelope impact sizing for product features. Given a feature's
estimated reach, conversion lift, and revenue-per-conversion, estimate the
expected annual impact in dollars. Supports multiple scenarios (low/mid/high),
sensitivity analysis, and comparison across initiatives.

The mental model:
    Impact = Reach × Conversion Lift × Revenue per Conversion × Time

Helps PMs quantify "how big is this?" before investing eng resources.

Usage:
    # Quick single estimate
    python impact-sizing-estimator.py \\
        --name "Checkout CTA redesign" \\
        --reach 500000 --conversion 3.2 --lift 10 --rev-per-conversion 48

    # With scenarios (low/mid/high)
    python impact-sizing-estimator.py \\
        --name "AI Recommendations" \\
        --reach 200000 \\
        --conversion 5 --lift-low 5 --lift-mid 12 --lift-high 20 \\
        --rev-per-conversion 65

    # Multiple initiatives (batch comparison)
    python impact-sizing-estimator.py \\
        --initiative "Checkout CTA:500000:3.2:10:48" \\
        --initiative "AI Recs:200000:5:12:65" \\
        --initiative "Onboarding v2:100000:15:8:30"

    Format: "Name:reach:conversion_pct:lift_pct:rev_per_conversion"

    # From CSV
    python impact-sizing-estimator.py --csv initiatives.csv

    # With eng cost for ROI
    python impact-sizing-estimator.py \\
        --name "New feature" \\
        --reach 300000 --conversion 4 --lift 15 --rev-per-conversion 50 \\
        --eng-weeks 8 --eng-cost-per-week 5000

CSV format:
    name,reach,conversion_pct,lift_pct,rev_per_conversion,eng_weeks,eng_cost_per_week
    Checkout CTA,500000,3.2,10,48,4,5000
    AI Recs,200000,5,12,65,12,5000
    Onboarding v2,100000,15,8,30,6,5000

Requirements:
    None (stdlib only).
"""

import argparse
import csv
import json
import sys
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Impact sizing
# ---------------------------------------------------------------------------

def size_impact(
    name: str,
    reach: int,
    conversion_pct: float,
    lift_pct: float,
    rev_per_conversion: float,
    lift_low: Optional[float] = None,
    lift_mid: Optional[float] = None,
    lift_high: Optional[float] = None,
    eng_weeks: Optional[float] = None,
    eng_cost_per_week: float = 5000,
    time_horizon_months: int = 12,
) -> Dict[str, Any]:
    """
    Estimate annualized impact of a feature.

    reach: users who will encounter the feature (annual)
    conversion_pct: current baseline conversion rate
    lift_pct: expected relative lift in conversion (e.g. 10 = 10% relative improvement)
    rev_per_conversion: revenue generated per conversion event
    """
    # Current state
    current_conversions = reach * conversion_pct / 100
    current_revenue = current_conversions * rev_per_conversion

    # Impact calculation
    new_conversion_pct = conversion_pct * (1 + lift_pct / 100)
    new_conversions = reach * new_conversion_pct / 100
    incremental_conversions = new_conversions - current_conversions
    incremental_revenue = incremental_conversions * rev_per_conversion

    # Time-adjusted
    annual_factor = time_horizon_months / 12
    annual_impact = incremental_revenue * annual_factor

    # Scenarios
    scenarios = None
    if lift_low is not None or lift_high is not None:
        low = lift_low if lift_low is not None else lift_pct * 0.5
        mid = lift_mid if lift_mid is not None else lift_pct
        high = lift_high if lift_high is not None else lift_pct * 1.5

        scenarios = {}
        for label, scenario_lift in [("low", low), ("mid", mid), ("high", high)]:
            s_new_conv_pct = conversion_pct * (1 + scenario_lift / 100)
            s_new_conv = reach * s_new_conv_pct / 100
            s_incr_conv = s_new_conv - current_conversions
            s_incr_rev = s_incr_conv * rev_per_conversion * annual_factor
            scenarios[label] = {
                "lift_pct": scenario_lift,
                "new_conversion_pct": round(s_new_conv_pct, 3),
                "incremental_conversions": round(s_incr_conv, 0),
                "annual_impact": round(s_incr_rev, 2),
            }

    # Eng cost / ROI
    eng_cost = None
    roi = None
    payback_months = None
    if eng_weeks is not None:
        eng_cost = eng_weeks * eng_cost_per_week
        if eng_cost > 0 and annual_impact > 0:
            roi = (annual_impact - eng_cost) / eng_cost * 100
            monthly_impact = annual_impact / 12
            payback_months = eng_cost / monthly_impact if monthly_impact > 0 else None

    # Confidence
    if scenarios:
        spread = scenarios["high"]["annual_impact"] - scenarios["low"]["annual_impact"]
        mid_val = scenarios["mid"]["annual_impact"]
        cv = spread / mid_val * 100 if mid_val > 0 else 0
        if cv < 50:
            confidence = "high"
            confidence_label = "🟢 High — narrow estimate range"
        elif cv < 100:
            confidence = "medium"
            confidence_label = "🟡 Medium — moderate uncertainty"
        else:
            confidence = "low"
            confidence_label = "🔴 Low — wide estimate range, validate assumptions"
    else:
        confidence = "single_estimate"
        confidence_label = "⬜ Single estimate — consider adding scenarios"

    return {
        "name": name,
        "reach": reach,
        "conversion_pct": conversion_pct,
        "lift_pct": lift_pct,
        "rev_per_conversion": rev_per_conversion,
        "time_horizon_months": time_horizon_months,
        "current_conversions": round(current_conversions, 0),
        "current_revenue": round(current_revenue, 2),
        "new_conversion_pct": round(new_conversion_pct, 3),
        "incremental_conversions": round(incremental_conversions, 0),
        "incremental_revenue": round(incremental_revenue, 2),
        "annual_impact": round(annual_impact, 2),
        "scenarios": scenarios,
        "eng_cost": eng_cost,
        "roi_pct": round(roi, 1) if roi is not None else None,
        "payback_months": round(payback_months, 1) if payback_months is not None else None,
        "confidence": confidence,
        "confidence_label": confidence_label,
    }


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def parse_initiative_string(s: str) -> Dict[str, Any]:
    """Parse 'Name:reach:conversion:lift:rev_per_conv[:eng_weeks]'."""
    parts = s.rsplit(":", 5)
    if len(parts) < 5:
        raise ValueError(
            f"Invalid initiative '{s}'. "
            "Format: Name:reach:conversion_pct:lift_pct:rev_per_conversion[:eng_weeks]"
        )

    name = parts[0].strip()
    try:
        reach = int(float(parts[1].strip()))
        conversion = float(parts[2].strip())
        lift = float(parts[3].strip())
        rev = float(parts[4].strip())
        eng_weeks = float(parts[5].strip()) if len(parts) > 5 else None
    except (ValueError, IndexError) as e:
        raise ValueError(f"Invalid numbers in initiative '{name}': {e}")

    return {
        "name": name,
        "reach": reach,
        "conversion_pct": conversion,
        "lift_pct": lift,
        "rev_per_conversion": rev,
        "eng_weeks": eng_weeks,
    }


def _col(fieldnames: List[str], *aliases: str) -> Optional[str]:
    lower_map = {f.lower().strip(): f for f in fieldnames}
    for alias in aliases:
        if alias.lower().strip() in lower_map:
            return lower_map[alias.lower().strip()]
    return None


def load_csv(path: str) -> List[Dict[str, Any]]:
    """Load initiatives from CSV."""
    initiatives: List[Dict[str, Any]] = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fields = reader.fieldnames or []

        c_name = _col(fields, "name", "initiative", "feature", "project")
        c_reach = _col(fields, "reach", "users", "audience", "traffic")
        c_conv = _col(fields, "conversion_pct", "conversion", "cvr", "baseline_rate")
        c_lift = _col(fields, "lift_pct", "lift", "expected_lift", "mde")
        c_rev = _col(fields, "rev_per_conversion", "revenue", "aov", "arpu", "value")
        c_eng = _col(fields, "eng_weeks", "effort", "weeks", "dev_weeks")
        c_cost = _col(fields, "eng_cost_per_week", "cost_per_week", "weekly_cost")

        for row in reader:
            name = row.get(c_name or "name", "").strip()
            if not name:
                continue

            def _num(col: Optional[str], default: Optional[float] = None) -> Optional[float]:
                if not col:
                    return default
                raw = row.get(col, "").strip().rstrip("%").replace(",", "").replace("$", "")
                try:
                    return float(raw) if raw else default
                except ValueError:
                    return default

            initiatives.append({
                "name": name,
                "reach": int(_num(c_reach, 0) or 0),
                "conversion_pct": _num(c_conv, 0) or 0,
                "lift_pct": _num(c_lift, 0) or 0,
                "rev_per_conversion": _num(c_rev, 0) or 0,
                "eng_weeks": _num(c_eng),
                "eng_cost_per_week": _num(c_cost, 5000) or 5000,
            })

    return initiatives


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


def _fmt_num(n: float) -> str:
    if abs(n) >= 1_000_000:
        return f"{n / 1_000_000:,.1f}M"
    elif abs(n) >= 1_000:
        return f"{n / 1_000:,.1f}K"
    else:
        return f"{n:,.0f}"


def _bar(value: float, max_val: float, width: int = 25) -> str:
    if max_val <= 0:
        return "░" * width
    ratio = min(1.0, max(0.0, value / max_val))
    filled = int(ratio * width)
    return "█" * filled + "░" * (width - filled)


def print_report(results: List[Dict[str, Any]]) -> None:
    """Pretty-print impact sizing results."""
    print("\n" + "=" * 78)
    print("💰 IMPACT SIZING ESTIMATOR")
    print("=" * 78)

    # Summary ranking
    if len(results) > 1:
        print(f"\n{'─'*78}")
        print(f"\n📊 INITIATIVE RANKING (by annual impact):\n")

        sorted_results = sorted(results, key=lambda x: -x["annual_impact"])
        max_impact = sorted_results[0]["annual_impact"] if sorted_results else 1

        print(f"   {'#':<3} {'Initiative':<22} {'Impact':>12} {'ROI':>8} {'Lift':>6}")
        print(f"   {'─'*3} {'─'*22} {'─'*12} {'─'*8} {'─'*6}")

        for i, r in enumerate(sorted_results):
            roi_str = f"{r['roi_pct']:.0f}%" if r['roi_pct'] is not None else "—"
            print(
                f"   {i+1:<3} {r['name'][:22]:<22} "
                f"{_fmt_money(r['annual_impact']):>12} "
                f"{roi_str:>8} "
                f"{r['lift_pct']:>5.0f}%"
            )

        print(f"\n   Impact comparison:")
        for r in sorted_results:
            bar = _bar(r["annual_impact"], max_impact, 30)
            print(f"   {r['name'][:16]:<16} {bar} {_fmt_money(r['annual_impact'])}")

        total_impact = sum(r["annual_impact"] for r in results)
        print(f"\n   Combined annual impact: {_fmt_money(total_impact)}")

    # Detailed per-initiative
    for r in results:
        print(f"\n{'─'*78}")
        print(f"\n📋 {r['name'].upper()}\n")

        # Input assumptions
        print(f"   ASSUMPTIONS:")
        print(f"   Reach (annual):      {_fmt_num(r['reach'])} users")
        print(f"   Baseline conversion: {r['conversion_pct']:.2f}%")
        print(f"   Expected lift:       {r['lift_pct']:.1f}% relative")
        print(f"   Rev per conversion:  ${r['rev_per_conversion']:,.2f}")

        # Impact calculation
        print(f"\n   CALCULATION:")
        print(f"   {_fmt_num(r['reach'])} reach × {r['conversion_pct']:.2f}% conversion = {_fmt_num(r['current_conversions'])} conversions today")
        print(f"   With {r['lift_pct']:.1f}% lift → {r['new_conversion_pct']:.3f}% conversion")
        print(f"   Incremental conversions: +{_fmt_num(r['incremental_conversions'])}")
        print(f"   × ${r['rev_per_conversion']:,.2f} per conversion")

        print(f"\n   📈 ANNUAL IMPACT: {_fmt_money(r['annual_impact'])}")

        # Scenarios
        if r["scenarios"]:
            print(f"\n   🎯 SCENARIO ANALYSIS:")
            print(f"   {'Scenario':<12} {'Lift':>6} {'Impact':>14}")
            print(f"   {'─'*12} {'─'*6} {'─'*14}")

            for label in ["low", "mid", "high"]:
                s = r["scenarios"][label]
                marker = " ←" if label == "mid" else ""
                print(f"   {label.capitalize():<12} {s['lift_pct']:>5.1f}% {_fmt_money(s['annual_impact']):>14}{marker}")

            # Range bar
            low_val = r["scenarios"]["low"]["annual_impact"]
            mid_val = r["scenarios"]["mid"]["annual_impact"]
            high_val = r["scenarios"]["high"]["annual_impact"]
            range_width = 40
            if high_val > low_val:
                mid_pos = int((mid_val - low_val) / (high_val - low_val) * range_width)
            else:
                mid_pos = range_width // 2
            range_bar = "░" * mid_pos + "█" + "░" * (range_width - mid_pos - 1)
            print(f"\n   {_fmt_money(low_val)} [{range_bar}] {_fmt_money(high_val)}")
            padding = " " * (len(_fmt_money(low_val)) + 2 + mid_pos)
            print(f"   {padding}▲ {_fmt_money(mid_val)}")

        print(f"\n   Confidence: {r['confidence_label']}")

        # Eng cost / ROI
        if r["eng_cost"] is not None:
            print(f"\n   💼 INVESTMENT & ROI:")
            print(f"   Engineering cost:    {_fmt_money(r['eng_cost'])}")
            print(f"   Annual impact:       {_fmt_money(r['annual_impact'])}")
            if r["roi_pct"] is not None:
                roi_emoji = "🟢" if r["roi_pct"] > 200 else "🟡" if r["roi_pct"] > 50 else "🔴"
                print(f"   ROI:                 {r['roi_pct']:.0f}% {roi_emoji}")
            if r["payback_months"] is not None:
                pb_emoji = "🟢" if r["payback_months"] < 3 else "🟡" if r["payback_months"] < 6 else "🔴"
                print(f"   Payback period:      {r['payback_months']:.1f} months {pb_emoji}")

    # Guidance
    print(f"\n{'─'*78}")
    print(f"\n💡 SIZING TIPS:")
    print(f"   • Always use conservative estimates — bias toward the low scenario")
    print(f"   • Reach = users who encounter the feature, not total user base")
    print(f"   • Lift is relative — 10% lift on 5% conversion = 5.5% new rate")
    print(f"   • Include ramp-up time — full impact rarely starts day one")
    print(f"   • ROI >200% = strong bet, 50-200% = reasonable, <50% = scrutinize")
    print(f"   • Size multiple initiatives to force-rank your roadmap")
    print("\n" + "=" * 78)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Estimate the annual revenue impact of product features. "
                    "Quick sizing to quantify 'how big is this?' before investing.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --name "CTA Redesign" --reach 500000 --conversion 3.2 --lift 10 --rev-per-conversion 48
  %(prog)s --initiative "CTA:500000:3.2:10:48" --initiative "AI Recs:200000:5:12:65"
  %(prog)s --csv initiatives.csv
        """,
    )

    # Single initiative
    parser.add_argument("--name", type=str, help="Initiative name")
    parser.add_argument("--reach", type=int, help="Annual user reach")
    parser.add_argument("--conversion", type=float, help="Baseline conversion rate (%%)")
    parser.add_argument("--lift", type=float, help="Expected relative lift (%%)")
    parser.add_argument("--rev-per-conversion", type=float, help="Revenue per conversion ($)")
    parser.add_argument("--lift-low", type=float, help="Low scenario lift (%%) ")
    parser.add_argument("--lift-mid", type=float, help="Mid scenario lift (%%)")
    parser.add_argument("--lift-high", type=float, help="High scenario lift (%%)")
    parser.add_argument("--eng-weeks", type=float, help="Engineering effort in weeks")
    parser.add_argument("--eng-cost-per-week", type=float, default=5000,
                        help="Cost per eng-week (default: $5000)")

    # Batch
    parser.add_argument("--initiative", type=str, action="append",
                        help="Initiative: 'Name:reach:conv:lift:rev[:eng_weeks]'")
    parser.add_argument("--csv", "-c", type=str, help="CSV file with initiatives")

    parser.add_argument("--output", "-o", type=str, help="Write JSON results to file")
    args = parser.parse_args()

    results: List[Dict[str, Any]] = []

    if args.csv:
        try:
            initiatives = load_csv(args.csv)
        except Exception as e:
            print(f"Error loading CSV: {e}", file=sys.stderr)
            return 1

        for init in initiatives:
            results.append(size_impact(
                name=init["name"],
                reach=init["reach"],
                conversion_pct=init["conversion_pct"],
                lift_pct=init["lift_pct"],
                rev_per_conversion=init["rev_per_conversion"],
                eng_weeks=init.get("eng_weeks"),
                eng_cost_per_week=init.get("eng_cost_per_week", 5000),
            ))

    if args.initiative:
        for i_str in args.initiative:
            try:
                init = parse_initiative_string(i_str)
            except ValueError as e:
                print(f"Error: {e}", file=sys.stderr)
                return 1
            results.append(size_impact(
                name=init["name"],
                reach=init["reach"],
                conversion_pct=init["conversion_pct"],
                lift_pct=init["lift_pct"],
                rev_per_conversion=init["rev_per_conversion"],
                eng_weeks=init.get("eng_weeks"),
            ))

    if args.name and args.reach and args.conversion is not None and args.lift is not None and args.rev_per_conversion is not None:
        results.append(size_impact(
            name=args.name,
            reach=args.reach,
            conversion_pct=args.conversion,
            lift_pct=args.lift,
            rev_per_conversion=args.rev_per_conversion,
            lift_low=args.lift_low,
            lift_mid=args.lift_mid,
            lift_high=args.lift_high,
            eng_weeks=args.eng_weeks,
            eng_cost_per_week=args.eng_cost_per_week,
        ))

    if not results:
        print("Error: provide --name + --reach + --conversion + --lift + --rev-per-conversion, "
              "--initiative, or --csv.", file=sys.stderr)
        parser.print_help(sys.stderr)
        return 1

    # Report
    print_report(results)

    # JSON output
    if args.output:
        with open(args.output, "w") as f:
            json.dump({"initiatives": results}, f, indent=2)
        print(f"\n📁 Results saved to {args.output}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
