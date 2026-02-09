#!/usr/bin/env python3
"""
AI Initiative ROI / Payback Calculator

Estimate payback period and ROI for an AI project: one-time dev cost, recurring
AI cost, and monthly benefit (revenue or cost savings). Complements
ai-unit-economics-calculator.py and strategy/ai-product-strategy-framework.md.

Usage:
    python ai-initiative-roi-calculator.py --dev-cost 50000 --monthly-ai-cost 2000 --monthly-benefit 10000
    python ai-initiative-roi-calculator.py --dev-cost 80000 --monthly-ai-cost 5000 --monthly-benefit 15000 --months 24

Requirements:
    None (stdlib only).
"""

import argparse
import math
import sys
from typing import Optional, Tuple


def payback_months(
    one_time_cost: float,
    monthly_benefit: float,
    monthly_cost: float,
) -> Optional[float]:
    """
    Months until cumulative net benefit equals one-time cost.

    Net per month = monthly_benefit - monthly_cost.
    Returns None if net is <= 0 (no payback).
    """
    net = monthly_benefit - monthly_cost
    if net <= 0:
        return None
    return one_time_cost / net


def roi_over_horizon(
    one_time_cost: float,
    monthly_ai_cost: float,
    monthly_benefit: float,
    months: int,
) -> Tuple[float, float]:
    """
    Total cost and total benefit over a horizon; ROI = (benefit - cost) / cost * 100.

    Returns (total_cost, roi_pct). Cost = one_time + monthly_ai_cost * months.
    Benefit = monthly_benefit * months.
    """
    total_cost = one_time_cost + monthly_ai_cost * months
    total_benefit = monthly_benefit * months
    if total_cost <= 0:
        return total_cost, 0.0
    roi = 100.0 * (total_benefit - total_cost) / total_cost
    return total_cost, roi


def main():
    parser = argparse.ArgumentParser(
        description="AI initiative: payback period and ROI over a time horizon."
    )
    parser.add_argument(
        "--dev-cost",
        type=float,
        required=True,
        help="One-time development cost (USD)",
    )
    parser.add_argument(
        "--monthly-ai-cost",
        type=float,
        default=0.0,
        help="Recurring monthly AI/infra cost (USD)",
    )
    parser.add_argument(
        "--monthly-benefit",
        type=float,
        required=True,
        help="Monthly benefit: revenue increase or cost savings (USD)",
    )
    parser.add_argument(
        "--months",
        type=int,
        default=24,
        help="Horizon for ROI (default: 24)",
    )
    args = parser.parse_args()

    if args.dev_cost < 0 or args.monthly_ai_cost < 0 or args.monthly_benefit < 0:
        print("Error: costs and benefit must be >= 0", file=sys.stderr)
        return 1
    if args.months < 1:
        print("Error: --months must be >= 1", file=sys.stderr)
        return 1

    payback = payback_months(args.dev_cost, args.monthly_benefit, args.monthly_ai_cost)
    cost_12, roi_12 = roi_over_horizon(
        args.dev_cost, args.monthly_ai_cost, args.monthly_benefit, 12
    )
    cost_24, roi_24 = roi_over_horizon(
        args.dev_cost, args.monthly_ai_cost, args.monthly_benefit, args.months
    )
    total_benefit_12 = args.monthly_benefit * 12
    total_benefit_24 = args.monthly_benefit * args.months

    print("\n" + "=" * 60)
    print("AI INITIATIVE ROI / PAYBACK")
    print("=" * 60)
    print("\n📋 INPUTS:")
    print(f"   • One-time dev cost:    ${args.dev_cost:,.2f}")
    print(f"   • Monthly AI cost:      ${args.monthly_ai_cost:,.2f}")
    print(f"   • Monthly benefit:      ${args.monthly_benefit:,.2f}")
    print("\n⏱️  PAYBACK:")
    if payback is not None:
        print(f"   • Payback period:       ~{math.ceil(payback)} months")
        if payback > 24:
            print("   ⚠️  Payback > 24 months — consider scope or benefit assumptions")
    else:
        print("   • Payback:             N/A (monthly benefit ≤ monthly AI cost)")
    print("\n📈 ROI:")
    print(f"   • At 12 months:         Total cost ${cost_12:,.2f}  |  Benefit ${total_benefit_12:,.2f}  |  ROI {roi_12:+.1f}%")
    print(f"   • At {args.months} months:        Total cost ${cost_24:,.2f}  |  Benefit ${total_benefit_24:,.2f}  |  ROI {roi_24:+.1f}%")
    print("\n" + "=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
