#!/usr/bin/env python3
"""
Multi-Model Cost Comparator

Compare inference cost across Amazon Bedrock, OpenAI, and Anthropic for a given
input/output token count. Uses on-demand / standard API pricing; verify current
rates at each provider's pricing page.

Usage:
    python multi-model-cost-comparator.py --input-tokens 1000 --output-tokens 500
    python multi-model-cost-comparator.py -i 50000 -o 2000 --list-models
    python multi-model-cost-comparator.py -i 1000 -o 500 --models gpt-4o claude-3-5-sonnet

Requirements:
    None (stdlib only).
"""

import argparse
import sys
from typing import Dict, List, Tuple

# USD per 1M tokens (input, output). Verify at provider pricing pages.
# Bedrock: https://aws.amazon.com/bedrock/pricing/
# OpenAI: https://platform.openai.com/docs/pricing
# Anthropic: https://www.anthropic.com/pricing

BEDROCK: Dict[str, Tuple[float, float]] = {
    "bedrock.claude-3-5-sonnet": (3.00, 15.00),
    "bedrock.claude-3-haiku": (0.25, 1.25),
    "bedrock.claude-3-opus": (15.00, 75.00),
    "bedrock.titan-text-express": (0.80, 3.20),
    "bedrock.mistral-large": (0.50, 1.50),
}

OPENAI: Dict[str, Tuple[float, float]] = {
    "gpt-4o": (2.50, 10.00),
    "gpt-4o-mini": (0.15, 0.60),
    "gpt-4-turbo": (10.00, 30.00),
}

ANTHROPIC: Dict[str, Tuple[float, float]] = {
    "claude-3-5-sonnet": (3.00, 15.00),
    "claude-3-haiku": (0.25, 1.25),
    "claude-3-opus": (15.00, 75.00),
}

ALL_MODELS: Dict[str, Tuple[float, float]] = {**BEDROCK, **OPENAI, **ANTHROPIC}


def cost(input_tokens: int, output_tokens: int, inp_per_m: float, out_per_m: float) -> float:
    """Total cost in USD for given token counts and $/1M rates."""
    return (input_tokens / 1_000_000) * inp_per_m + (output_tokens / 1_000_000) * out_per_m


def main():
    parser = argparse.ArgumentParser(
        description="Compare inference cost across Bedrock, OpenAI, and Anthropic."
    )
    parser.add_argument("--input-tokens", "-i", type=int, default=0, help="Input token count")
    parser.add_argument("--output-tokens", "-o", type=int, default=0, help="Output token count")
    parser.add_argument(
        "--models",
        "-m",
        nargs="*",
        help="Model IDs to compare (default: all). e.g. gpt-4o bedrock.claude-3-haiku",
    )
    parser.add_argument("--list-models", action="store_true", help="List known models and exit")
    args = parser.parse_args()

    if args.list_models:
        print("Models (USD per 1M tokens: input / output)\n")
        print("Bedrock:")
        for name, (pi, po) in BEDROCK.items():
            print(f"  {name}: ${pi:.2f} / ${po:.2f}")
        print("\nOpenAI:")
        for name, (pi, po) in OPENAI.items():
            print(f"  {name}: ${pi:.2f} / ${po:.2f}")
        print("\nAnthropic:")
        for name, (pi, po) in ANTHROPIC.items():
            print(f"  {name}: ${pi:.2f} / ${po:.2f}")
        print("\nVerify: AWS Bedrock, OpenAI, Anthropic pricing pages.")
        return 0

    if args.input_tokens <= 0 and args.output_tokens <= 0:
        parser.print_help()
        print("\nExample: -i 1000 -o 500")
        return 0

    input_tokens = max(0, args.input_tokens)
    output_tokens = max(0, args.output_tokens)
    models = args.models if args.models else list(ALL_MODELS.keys())
    # Resolve shorthand names to a known key
    selected = []
    for m in models:
        m_lower = m.lower().strip()
        if m_lower in ALL_MODELS:
            selected.append(m_lower)
        else:
            for key in ALL_MODELS:
                if m_lower in key or key.endswith(m_lower.replace("bedrock.", "")):
                    selected.append(key)
                    break
            else:
                selected.append(m_lower)  # keep as-is for display

    rows: List[Tuple[str, float, float, float]] = []
    for name in selected:
        if name not in ALL_MODELS:
            print(f"Warning: unknown model '{name}', skipping.", file=sys.stderr)
            continue
        pi, po = ALL_MODELS[name]
        total = cost(input_tokens, output_tokens, pi, po)
        rows.append((name, pi, po, total))

    if not rows:
        print("Error: no valid models selected.", file=sys.stderr)
        return 1

    rows.sort(key=lambda r: r[3])
    cheapest = rows[0][0]
    print("\n" + "=" * 70)
    print("MULTI-MODEL COST COMPARISON")
    print("=" * 70)
    print(f"\n  Input tokens:  {input_tokens:,}  |  Output tokens:  {output_tokens:,}\n")
    print(f"  {'Model':<28}  {'Input $/1M':>10}  {'Out $/1M':>10}  {'Total USD':>12}")
    print("  " + "-" * 64)
    for name, pi, po, total in rows:
        marker = "  ← lowest" if name == cheapest else ""
        print(f"  {name:<28}  ${pi:>9.2f}  ${po:>9.2f}  ${total:>11.4f}{marker}")
    print("  " + "-" * 64)
    print(f"\n  Cheapest for this usage: {cheapest}")
    print("\n  Verify current pricing at AWS, OpenAI, and Anthropic pricing pages.")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    sys.exit(main())
