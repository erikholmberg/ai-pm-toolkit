#!/usr/bin/env python3
"""
Bedrock Cost Calculator

Estimate inference cost for Amazon Bedrock models (USD per 1M tokens).
Uses on-demand Standard tier pricing; region defaults to US East (N. Virginia).
Update from: https://aws.amazon.com/bedrock/pricing/

Usage:
    python bedrock-cost-calculator.py --input-tokens 1000 --output-tokens 500 --model claude
    python bedrock-cost-calculator.py --input-tokens 1000 --output-tokens 500 --model anthropic.claude-3-5-sonnet-v2
    python bedrock-cost-calculator.py --list-models
"""

import argparse
import sys
from typing import Dict, Tuple

# Pricing lives in scripts/model_pricing.py so every cost script agrees on one
# table. Bedrock is partner-operated with its own regional rates — entries there
# are prefixed `bedrock.`. Run `python model_pricing.py --check` to see what
# needs re-verifying.
import model_pricing


def get_pricing(model: str) -> Tuple[float, float]:
    """Return (input $/1M, output $/1M) from the shared table."""
    try:
        p = model_pricing.lookup(model)
    except model_pricing.UnknownModelError as e:
        print(f"Warning: {e}", file=sys.stderr)
        print("Falling back to claude-sonnet-5 pricing.", file=sys.stderr)
        p = model_pricing.lookup("claude-sonnet-5")
    else:
        model_pricing.warn_if_stale(model)
    return p.input_per_mtok, p.output_per_mtok


def estimate_cost(input_tokens: int, output_tokens: int, model: str) -> Tuple[float, float, float]:
    """Return (input_cost_usd, output_cost_usd, total_cost_usd)."""
    inp_price, out_price = get_pricing(model)
    inc = (input_tokens / 1_000_000) * inp_price
    out = (output_tokens / 1_000_000) * out_price
    return round(inc, 6), round(out, 6), round(inc + out, 6)


def main():
    parser = argparse.ArgumentParser(
        description="Estimate Amazon Bedrock inference cost (on-demand, Standard tier)"
    )
    parser.add_argument("--input-tokens", "-i", type=int, default=0, help="Input token count")
    parser.add_argument("--output-tokens", "-o", type=int, default=0, help="Output token count")
    parser.add_argument("--model", "-m", default="claude",
                        help="Model ID or substring (e.g. anthropic.claude-3-5-sonnet-v2, mistral-large)")
    parser.add_argument("--list-models", action="store_true", help="List known models and pricing")
    args = parser.parse_args()

    if args.list_models:
        print("Models (USD per 1M tokens, input / output).")
        print("Bedrock rates are on-demand, US East (N. Virginia).\n")
        for provider in ("bedrock", "anthropic"):
            names = model_pricing.list_models(provider)
            if not names:
                continue
            label = "Bedrock (partner-operated)" if provider == "bedrock" \
                else "Anthropic first-party API"
            print(f"{label}:")
            for name in names:
                p = model_pricing.PRICING[name]
                verified = f"verified {p.last_verified}" if p.last_verified else "UNVERIFIED"
                print(
                    f"  {name}: ${p.input_per_mtok:.2f} / ${p.output_per_mtok:.2f}"
                    f"  ({verified})"
                )
            print()
        model_pricing.warn_if_stale()
        print("Pricing: https://aws.amazon.com/bedrock/pricing/")
        return 0

    if args.input_tokens <= 0 and args.output_tokens <= 0:
        parser.print_help()
        print("\nExample: --input-tokens 1000 --output-tokens 500 --model claude")
        return 0

    input_tokens = max(0, args.input_tokens)
    output_tokens = max(0, args.output_tokens)
    inc_cost, out_cost, total = estimate_cost(input_tokens, output_tokens, args.model)
    inp_price, out_price = get_pricing(args.model)

    print("Bedrock cost estimate (on-demand)")
    print("-" * 40)
    print(f"  Model:           {args.model}")
    print(f"  Input tokens:    {input_tokens:,}  @ ${inp_price:.2f}/1M  = ${inc_cost:.4f}")
    print(f"  Output tokens:   {output_tokens:,}  @ ${out_price:.2f}/1M  = ${out_cost:.4f}")
    print(f"  Total:           ${total:.4f}")
    print("-" * 40)
    return 0


if __name__ == "__main__":
    sys.exit(main())
