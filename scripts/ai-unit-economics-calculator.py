#!/usr/bin/env python3
"""
AI Unit Economics / ROI Calculator

Estimate cost per user, margin impact, and breakeven for AI-powered features.
Inputs: cost per request (or derive from Bedrock), volume, revenue.
Aligns with evals/metrics/ai-product-metrics.md (cost per request, margin impact).

Usage:
    python ai-unit-economics-calculator.py --cost-per-request 0.002 --requests-per-month 1e6 --revenue-per-user 5
    python ai-unit-economics-calculator.py --cost-per-request 0.001 --requests-per-month 500000 --revenue-per-user 10 --mau 100000
    python ai-unit-economics-calculator.py --input-tokens 500 --output-tokens 200 --model claude --requests-per-month 1e6 --revenue-per-user 8

Requirements:
    None for --cost-per-request mode.
    For --model mode: same as bedrock-cost-calculator (no extra deps; uses same pricing dict).
"""

import argparse
import sys
from typing import Tuple, Optional

# Optional: reuse Bedrock pricing if script is run from repo (same dir as bedrock-cost-calculator)
try:
    from importlib.util import spec_from_file_location, module_from_spec
    from pathlib import Path
    _bedrock_path = Path(__file__).resolve().parent / "bedrock-cost-calculator.py"
    if _bedrock_path.exists():
        _spec = spec_from_file_location("bedrock_cost_calculator", _bedrock_path)
        _mod = module_from_spec(_spec)
        _spec.loader.exec_module(_mod)
        estimate_cost = _mod.estimate_cost
        get_pricing = _mod.get_pricing
        BEDROCK_AVAILABLE = True
    else:
        BEDROCK_AVAILABLE = False
except Exception:
    BEDROCK_AVAILABLE = False


def cost_per_user(
    total_cost_usd: float,
    active_users: int,
) -> float:
    """Cost per active user (e.g. per MAU)."""
    if active_users <= 0:
        return 0.0
    return total_cost_usd / active_users


def margin_impact_pct(
    ai_cost_usd: float,
    revenue_usd: float,
) -> Optional[float]:
    """AI cost as % of revenue. None if revenue is 0."""
    if revenue_usd <= 0:
        return None
    return 100.0 * (ai_cost_usd / revenue_usd)


def breakeven_requests(
    cost_per_request: float,
    revenue_per_request: float,
) -> Optional[float]:
    """Requests needed for revenue to equal cost (break-even). None if revenue per request <= 0."""
    if revenue_per_request <= 0:
        return None
    if cost_per_request <= 0:
        return 0.0
    return cost_per_request / revenue_per_request


def main():
    parser = argparse.ArgumentParser(
        description="AI unit economics: cost per user, margin impact, breakeven."
    )
    parser.add_argument(
        "--cost-per-request",
        "-c",
        type=float,
        help="Average cost per AI request (USD). Use this or (--input-tokens + --output-tokens + --model).",
    )
    parser.add_argument(
        "--input-tokens",
        "-i",
        type=int,
        help="Input tokens per request (for Bedrock cost; use with --output-tokens and --model).",
    )
    parser.add_argument(
        "--output-tokens",
        "-o",
        type=int,
        help="Output tokens per request (for Bedrock cost).",
    )
    parser.add_argument(
        "--model",
        "-m",
        type=str,
        default="claude",
        help="Model ID for Bedrock cost (default: claude). Ignored without --input-tokens/--output-tokens.",
    )
    parser.add_argument(
        "--requests-per-month",
        "-r",
        type=float,
        required=True,
        help="Total AI requests per month (e.g. 1000000 or 1e6).",
    )
    parser.add_argument(
        "--revenue-per-user",
        type=float,
        help="Revenue per user per month (USD). Used with --mau for margin impact.",
    )
    parser.add_argument(
        "--revenue-per-request",
        type=float,
        help="Revenue attributed per request (USD). Used for breakeven.",
    )
    parser.add_argument(
        "--mau",
        type=int,
        help="Monthly active users. If set, report cost per user.",
    )
    parser.add_argument(
        "--total-revenue",
        type=float,
        help="Total monthly revenue (USD). If set, report AI cost as %% of revenue.",
    )
    args = parser.parse_args()

    # Resolve cost per request
    if args.cost_per_request is not None:
        if args.cost_per_request < 0:
            print("Error: --cost-per-request must be >= 0", file=sys.stderr)
            return 1
        cost_per_request = args.cost_per_request
    elif args.input_tokens is not None and args.output_tokens is not None:
        if not BEDROCK_AVAILABLE:
            print("Error: Bedrock pricing not available (bedrock-cost-calculator.py not found). Use --cost-per-request.", file=sys.stderr)
            return 1
        _, _, total = estimate_cost(args.input_tokens, args.output_tokens, args.model)
        cost_per_request = total
    else:
        parser.print_help()
        print("\nExample: --cost-per-request 0.002 --requests-per-month 1000000 --revenue-per-user 5 --mau 200000", file=sys.stderr)
        return 0

    requests = max(0.0, args.requests_per_month)
    total_ai_cost = cost_per_request * requests

    # Outputs
    print("\n" + "=" * 60)
    print("📊 AI UNIT ECONOMICS")
    print("=" * 60)
    print("\n📋 INPUTS:")
    print(f"   • Cost per request:     ${cost_per_request:.6f}")
    print(f"   • Requests per month:   {requests:,.0f}")
    if args.mau:
        print(f"   • MAU:                 {args.mau:,}")
    if args.revenue_per_user is not None:
        print(f"   • Revenue per user:     ${args.revenue_per_user:.2f}/month")
    if args.total_revenue is not None:
        print(f"   • Total revenue:       ${args.total_revenue:,.2f}/month")
    if args.revenue_per_request is not None:
        print(f"   • Revenue per request: ${args.revenue_per_request:.4f}")

    print("\n📈 COST:")
    print(f"   • Total AI cost/month:  ${total_ai_cost:,.2f}")

    if args.mau and args.mau > 0:
        cpu = cost_per_user(total_ai_cost, args.mau)
        print(f"   • Cost per user (MAU): ${cpu:.4f}/month")

    revenue_for_margin = args.total_revenue
    if revenue_for_margin is None and args.revenue_per_user is not None and args.mau is not None and args.mau > 0:
        revenue_for_margin = args.revenue_per_user * args.mau
    if revenue_for_margin is not None and revenue_for_margin > 0:
        pct = margin_impact_pct(total_ai_cost, revenue_for_margin)
        if pct is not None:
            print(f"\n📉 MARGIN IMPACT:")
            print(f"   • AI cost as %% of revenue: {pct:.2f}%%")

    if args.revenue_per_request is not None and args.revenue_per_request > 0:
        be = breakeven_requests(cost_per_request, args.revenue_per_request)
        if be is not None:
            print(f"\n🎯 BREAKEVEN (revenue = cost):")
            print(f"   • Requests needed: {be:,.0f} (per request revenue ${args.revenue_per_request:.4f})")

    print("\n" + "=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
