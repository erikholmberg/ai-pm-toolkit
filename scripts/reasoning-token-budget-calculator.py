#!/usr/bin/env python3
"""
Reasoning Token Budget Calculator

For "extended thinking" / reasoning-token models (e.g. Claude with extended
thinking, OpenAI o-series): estimate the cost and latency impact of dialing
reasoning effort up or down. PMs use this to decide whether a quality bump
from "high" reasoning effort is worth the cost/latency multiple, before
wiring effort level into a product surface.

Reasoning tokens are modeled as a multiplier of output tokens (the model
"thinks" proportionally more before answering) and are billed at the
output-token rate, per common provider pricing. Multipliers and a rough
latency-per-1K-token constant are editable constants below — treat them as
planning assumptions, not guarantees; validate against real traces when
available.

Usage:
    python reasoning-token-budget-calculator.py
    python reasoning-token-budget-calculator.py --reasoning-effort high --requests-per-month 500000
    python reasoning-token-budget-calculator.py --input-tokens 2000 --output-tokens 600 \\
        --reasoning-effort medium --input-cost-per-m 3 --output-cost-per-m 15
    python reasoning-token-budget-calculator.py --output report.json

Requirements:
    None (stdlib only).
"""

import argparse
import json
import sys
from typing import Any, Dict


# ---------------------------------------------------------------------------
# Assumptions (editable) — reasoning tokens as a multiplier of output tokens,
# and a rough latency multiplier vs a non-reasoning call at the same effort
# tier. These are planning heuristics; verify against real usage/latency
# traces before committing to a budget.
# ---------------------------------------------------------------------------

REASONING_TOKEN_MULTIPLIER: Dict[str, float] = {
    "low": 1.0,      # ~1x output tokens spent "thinking"
    "medium": 3.0,   # ~3x output tokens
    "high": 8.0,     # ~8x output tokens
}

REASONING_LATENCY_MULTIPLIER: Dict[str, float] = {
    "low": 1.2,
    "medium": 2.5,
    "high": 5.0,
}

# Rough planning constant: ms of wall-clock time per 1K total (input+output+
# reasoning) tokens for a non-reasoning call, before the effort multiplier above.
BASE_MS_PER_1K_TOKENS = 25.0


# ---------------------------------------------------------------------------
# Core calculations
# ---------------------------------------------------------------------------

def estimate_tier(
    effort: str,
    input_tokens: float,
    output_tokens: float,
    requests_per_month: int,
    input_cost_per_m: float,
    output_cost_per_m: float,
) -> Dict[str, Any]:
    """Cost & latency estimate for a single reasoning-effort tier."""
    reasoning_tokens = output_tokens * REASONING_TOKEN_MULTIPLIER[effort]
    billed_output_tokens = output_tokens + reasoning_tokens  # reasoning billed at output rate

    input_cost = (input_tokens / 1_000_000) * input_cost_per_m
    output_cost = (billed_output_tokens / 1_000_000) * output_cost_per_m
    cost_per_request = input_cost + output_cost
    monthly_cost = cost_per_request * requests_per_month

    total_tokens = input_tokens + billed_output_tokens
    latency_ms = (total_tokens / 1000) * BASE_MS_PER_1K_TOKENS * REASONING_LATENCY_MULTIPLIER[effort]

    return {
        "effort": effort,
        "reasoning_token_multiplier": REASONING_TOKEN_MULTIPLIER[effort],
        "reasoning_tokens": round(reasoning_tokens, 0),
        "billed_output_tokens": round(billed_output_tokens, 0),
        "input_cost": round(input_cost, 6),
        "output_cost": round(output_cost, 6),
        "cost_per_request": round(cost_per_request, 6),
        "monthly_cost": round(monthly_cost, 2),
        "annual_cost": round(monthly_cost * 12, 2),
        "latency_ms": round(latency_ms, 0),
        "latency_s": round(latency_ms / 1000, 2),
    }


def compare_tiers(
    input_tokens: float,
    output_tokens: float,
    requests_per_month: int,
    input_cost_per_m: float,
    output_cost_per_m: float,
    selected: str,
) -> Dict[str, Any]:
    tiers = {
        effort: estimate_tier(effort, input_tokens, output_tokens, requests_per_month, input_cost_per_m, output_cost_per_m)
        for effort in ("low", "medium", "high")
    }
    return {
        "inputs": {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "requests_per_month": requests_per_month,
            "input_cost_per_m": input_cost_per_m,
            "output_cost_per_m": output_cost_per_m,
            "selected_effort": selected,
        },
        "tiers": tiers,
    }


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def _fmt_usd(amount: float) -> str:
    if abs(amount) >= 1000:
        return f"${amount:,.2f}"
    elif abs(amount) >= 1:
        return f"${amount:.2f}"
    else:
        return f"${amount:.4f}"


def print_report(result: Dict[str, Any]) -> None:
    inp = result["inputs"]
    tiers = result["tiers"]
    selected = inp["selected_effort"]

    print("\n" + "=" * 78)
    print("🧠 REASONING TOKEN BUDGET CALCULATOR")
    print("=" * 78)

    print(f"\n📋 REQUEST PROFILE:")
    print(f"   • Input tokens/request:   {inp['input_tokens']:,g}")
    print(f"   • Output tokens/request:  {inp['output_tokens']:,g}  (pre-reasoning)")
    print(f"   • Requests/month:         {inp['requests_per_month']:,}")
    print(f"   • Price ($/1M in / out):  {_fmt_usd(inp['input_cost_per_m'])} / {_fmt_usd(inp['output_cost_per_m'])}")
    print(f"   • Selected effort:        {selected.upper()}")

    print(f"\n⚙️  ASSUMPTIONS (editable constants in script):")
    print(f"   {'Effort':<10} {'Reasoning ×output':>18} {'Latency ×base':>15}")
    for e in ("low", "medium", "high"):
        print(f"   {e:<10} {REASONING_TOKEN_MULTIPLIER[e]:>17.1f}x {REASONING_LATENCY_MULTIPLIER[e]:>14.1f}x")

    print(f"\n📊 COST & LATENCY BY TIER:\n")
    cols = ["low", "medium", "high"]
    header = f"   {'Metric':<26}" + "".join(f"{c.upper():>16}" for c in cols)
    print(header)
    print(f"   {'─'*26}" + "".join(f"{'─'*16}" for _ in cols))

    def row(label: str, fmt, key=None, sub=None):
        vals = []
        for c in cols:
            t = tiers[c]
            v = t[sub][key] if sub else t[key]
            vals.append(fmt(v))
        marker_row = f"   {label:<26}" + "".join(f"{v:>16}" for v in vals)
        print(marker_row)

    row("Reasoning tokens", lambda v: f"{v:,.0f}", "reasoning_tokens")
    row("Billed output tokens", lambda v: f"{v:,.0f}", "billed_output_tokens")
    row("Cost / request", _fmt_usd, "cost_per_request")
    row("Monthly cost", _fmt_usd, "monthly_cost")
    row("Annual cost", _fmt_usd, "annual_cost")
    row("Latency / request", lambda v: f"{v:.1f}s", "latency_s")

    print(f"\n   Selected tier → {selected.upper()}")
    sel = tiers[selected]
    low = tiers["low"]
    if selected != "low":
        cost_mult = sel["cost_per_request"] / low["cost_per_request"] if low["cost_per_request"] > 0 else None
        lat_mult = sel["latency_s"] / low["latency_s"] if low["latency_s"] > 0 else None
        print(f"   💡 vs LOW effort: {cost_mult:.1f}x cost, {lat_mult:.1f}x latency" if cost_mult and lat_mult else "")
        print(f"      Monthly delta vs LOW: {_fmt_usd(sel['monthly_cost'] - low['monthly_cost'])}")

    high = tiers["high"]
    if selected != "high":
        headroom_cost = high["monthly_cost"] - sel["monthly_cost"]
        print(f"   💡 Upgrading to HIGH would add {_fmt_usd(headroom_cost)}/month for ~{high['latency_s']/sel['latency_s']:.1f}x latency" if sel["latency_s"] > 0 else "")

    print(f"\n💡 GUIDANCE:")
    print(f"   • Reasoning tokens are typically billed at the OUTPUT token rate — they can dominate cost even when visible output is short.")
    print(f"   • Reserve HIGH effort for requests where quality materially changes the outcome (multi-step math, planning, code review); default to LOW/MEDIUM for routine requests.")
    print(f"   • Consider a router: classify request difficulty first, only pay for high reasoning effort on the subset that needs it.")
    print(f"   • Multipliers above are planning assumptions — replace with measured values from your provider/model once you have production traces.")

    print("\n" + "=" * 78)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Estimate cost & latency of extended-thinking/reasoning-token models "
                    "at low/medium/high reasoning effort, side by side.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s
  %(prog)s --reasoning-effort high --requests-per-month 500000
  %(prog)s --input-tokens 2000 --output-tokens 600 --reasoning-effort medium \\
           --input-cost-per-m 3 --output-cost-per-m 15
  %(prog)s --output report.json
        """,
    )
    parser.add_argument("--input-tokens", type=float, default=1000.0, help="Input tokens per request (default: 1000)")
    parser.add_argument("--output-tokens", type=float, default=400.0, help="Visible output tokens per request, pre-reasoning (default: 400)")
    parser.add_argument("--reasoning-effort", choices=["low", "medium", "high"], default="medium", help="Selected/current reasoning effort tier to highlight (default: medium)")
    parser.add_argument("--requests-per-month", type=int, default=100000, help="Monthly request volume (default: 100000)")
    parser.add_argument("--input-cost-per-m", type=float, default=3.00, help="USD per 1M input tokens (default: 3.00)")
    parser.add_argument("--output-cost-per-m", type=float, default=15.00, help="USD per 1M output tokens; reasoning tokens billed at this rate too (default: 15.00)")
    parser.add_argument("--output", "-o", type=str, help="Write report to JSON file")
    args = parser.parse_args()

    if args.input_tokens < 0 or args.output_tokens < 0:
        print("Error: token counts must be >= 0.", file=sys.stderr)
        return 1
    if args.requests_per_month < 0:
        print("Error: --requests-per-month must be >= 0.", file=sys.stderr)
        return 1

    result = compare_tiers(
        input_tokens=args.input_tokens,
        output_tokens=args.output_tokens,
        requests_per_month=args.requests_per_month,
        input_cost_per_m=args.input_cost_per_m,
        output_cost_per_m=args.output_cost_per_m,
        selected=args.reasoning_effort,
    )

    print_report(result)

    if args.output:
        with open(args.output, "w") as f:
            json.dump(result, f, indent=2)
        print(f"\n📁 Report saved to {args.output}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
