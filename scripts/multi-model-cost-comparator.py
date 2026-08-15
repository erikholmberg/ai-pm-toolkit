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

# Pricing lives in scripts/model_pricing.py so every cost script agrees on one
# table. Run `python model_pricing.py --check` to see what needs re-verifying.
import model_pricing

ALL_MODELS: Dict[str, Tuple[float, float]] = {
    name: (p.input_per_mtok, p.output_per_mtok)
    for name, p in model_pricing.PRICING.items()
}


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
        for provider in sorted({p.provider for p in model_pricing.PRICING.values()}):
            print(f"{provider}:")
            for name in model_pricing.list_models(provider):
                p = model_pricing.PRICING[name]
                verified = f"verified {p.last_verified}" if p.last_verified else "UNVERIFIED"
                print(
                    f"  {name}: ${p.input_per_mtok:.3f} / ${p.output_per_mtok:.3f}"
                    f"  ({verified})"
                )
            print()
        model_pricing.warn_if_stale()
        return 0

    if args.input_tokens <= 0 and args.output_tokens <= 0:
        parser.print_help()
        print("\nExample: -i 1000 -o 500")
        return 0

    input_tokens = max(0, args.input_tokens)
    output_tokens = max(0, args.output_tokens)
    models = args.models if args.models else list(ALL_MODELS.keys())
    # Resolve shorthand names, aliases, and retired model IDs to a known key
    selected = []
    for m in models:
        try:
            selected.append(model_pricing.canonical_name(m))
        except model_pricing.UnknownModelError as e:
            print(f"Warning: {e}", file=sys.stderr)

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
    print(f"  {'Model':<34}  {'Input $/1M':>10}  {'Out $/1M':>10}  {'Total USD':>12}")
    print("  " + "-" * 70)
    for name, pi, po, total in rows:
        marker = "  ← lowest" if name == cheapest else ""
        print(f"  {name:<34}  ${pi:>9.2f}  ${po:>9.2f}  ${total:>11.4f}{marker}")
    print("  " + "-" * 70)
    print(f"\n  Cheapest for this usage: {cheapest}")

    # A cross-provider comparison is only as good as its weakest price. Call out
    # which of the compared models carry prices nobody has verified.
    suspect = [n for n, _, _, _ in rows if model_pricing.PRICING[n].is_stale()]
    if suspect:
        print(
            f"\n  ⚠️  {len(suspect)} of {len(rows)} models compared carry stale or "
            f"unverified prices:\n     {', '.join(suspect)}"
        )
        print("     This ranking may be wrong. Re-verify before quoting it.")
    print("\n  Verify current pricing at AWS, OpenAI, and Anthropic pricing pages.")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    sys.exit(main())
