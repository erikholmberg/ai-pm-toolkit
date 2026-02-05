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

# USD per 1M tokens (input, output) — On-Demand, US East (N. Virginia) where applicable
# Source: https://aws.amazon.com/bedrock/pricing/ (verify for your region)
BEDROCK_PRICING: Dict[str, Tuple[float, float]] = {
    # Anthropic
    "anthropic.claude-3-5-sonnet-v2": (3.00, 15.00),
    "anthropic.claude-3-5-sonnet": (3.00, 15.00),
    "anthropic.claude-3-sonnet": (3.00, 15.00),
    "anthropic.claude-3-haiku": (0.25, 1.25),
    "anthropic.claude-3-opus": (15.00, 75.00),
    "claude-3-5-sonnet": (3.00, 15.00),
    "claude-3-sonnet": (3.00, 15.00),
    "claude-3-haiku": (0.25, 1.25),
    "claude-3-opus": (15.00, 75.00),
    "claude": (3.00, 15.00),
    # Amazon
    "amazon.titan-text-express": (0.80, 3.20),
    "amazon.titan-text-lite": (0.30, 0.40),
    "titan-text-express": (0.80, 3.20),
    "titan-text-lite": (0.30, 0.40),
    "titan": (0.80, 3.20),
    # Meta Llama (examples)
    "meta.llama3-2-1b": (0.10, 0.10),
    "meta.llama3-2-3b": (0.12, 0.12),
    "meta.llama3-2-70b": (0.99, 0.99),
    "meta.llama2-13b": (0.75, 1.00),
    "meta.llama2-70b": (1.95, 2.56),
    "llama3": (0.12, 0.12),
    "llama2": (0.75, 1.00),
    # Mistral
    "mistral.mistral-large-3": (0.50, 1.50),
    "mistral.ministral-8b": (0.15, 0.15),
    "mistral.magistral-small": (0.50, 1.50),
    "mistral-large": (0.50, 1.50),
    "mistral": (0.50, 1.50),
    # Cohere (example)
    "cohere.command-r-plus": (1.50, 2.00),
    "cohere.command": (1.50, 2.00),
    "cohere": (1.50, 2.00),
}


def get_pricing(model: str) -> Tuple[float, float]:
    """Return (input $/1M, output $/1M). Match by model ID or substring."""
    model_lower = model.lower().strip()
    # Exact match first
    if model_lower in BEDROCK_PRICING:
        return BEDROCK_PRICING[model_lower]
    # Substring match
    for key, val in BEDROCK_PRICING.items():
        if key in model_lower or model_lower in key:
            return val
    # Default to Claude 3.5 Sonnet
    return (3.00, 15.00)


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
        print("Bedrock models (USD per 1M tokens, input / output). On-demand, US East (N. Virginia):")
        seen = set()
        for name in sorted(BEDROCK_PRICING.keys()):
            if name in seen:
                continue
            p = BEDROCK_PRICING[name]
            print(f"  {name}: ${p[0]:.2f} / ${p[1]:.2f}")
            seen.add(name)
        print("\nPricing: https://aws.amazon.com/bedrock/pricing/")
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
