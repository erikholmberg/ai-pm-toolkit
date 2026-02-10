#!/usr/bin/env python3
"""
Prompt Cost Optimizer

Analyze prompt token usage across models and recommend strategies to reduce
spend: model downgrade, prompt truncation, caching, and batching. Complements
token-counter.py and multi-model-cost-comparator.py by focusing on actionable
cost reduction.

Usage:
    python prompt-cost-optimizer.py --file system-prompt.txt --model gpt-4o --requests-per-month 500000
    python prompt-cost-optimizer.py "You are a helpful assistant..." --model claude-3-opus-20240229 --requests-per-month 1e6 --output-tokens 300
    python prompt-cost-optimizer.py --file prompt.txt --model gpt-4o --requests-per-month 200000 --cache-hit-rate 0.3

Requirements:
    None (stdlib only). Optional: tiktoken for accurate OpenAI token counts.
"""

import argparse
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple


# USD per 1M tokens (input / output)
PRICING: Dict[str, Dict[str, float]] = {
    "claude-3-opus-20240229":      {"input": 15.0,  "output": 75.0},
    "claude-3-sonnet-20240229":    {"input": 3.0,   "output": 15.0},
    "claude-3-haiku-20240307":     {"input": 0.25,  "output": 1.25},
    "claude-3-5-sonnet-20241022":  {"input": 3.0,   "output": 15.0},
    "gpt-4o":                      {"input": 2.5,   "output": 10.0},
    "gpt-4o-mini":                 {"input": 0.15,  "output": 0.60},
    "gpt-4-turbo":                 {"input": 10.0,  "output": 30.0},
    "gpt-4":                       {"input": 30.0,  "output": 60.0},
    "gpt-3.5-turbo":               {"input": 0.50,  "output": 1.50},
}

# Model downgrade suggestions: from -> list of cheaper alternatives
DOWNGRADE_MAP: Dict[str, List[str]] = {
    "claude-3-opus-20240229":     ["claude-3-5-sonnet-20241022", "claude-3-sonnet-20240229", "claude-3-haiku-20240307"],
    "claude-3-5-sonnet-20241022": ["claude-3-sonnet-20240229", "claude-3-haiku-20240307"],
    "claude-3-sonnet-20240229":   ["claude-3-haiku-20240307"],
    "gpt-4":                      ["gpt-4-turbo", "gpt-4o", "gpt-4o-mini"],
    "gpt-4-turbo":                ["gpt-4o", "gpt-4o-mini"],
    "gpt-4o":                     ["gpt-4o-mini"],
}

# Characters per token (fallback)
CHARS_PER_TOKEN_ESTIMATE = 4


def count_tokens(text: str) -> Tuple[int, bool]:
    """Return (token_count, used_tiktoken)."""
    try:
        import tiktoken
        enc = tiktoken.get_encoding("cl100k_base")
        return len(enc.encode(text)), True
    except Exception:
        if not text:
            return 0, False
        return max(1, len(text) // CHARS_PER_TOKEN_ESTIMATE), False


def get_pricing(model: str) -> Dict[str, float]:
    """Get pricing for model. Matches by substring."""
    model_lower = model.lower()
    for key, val in PRICING.items():
        if key.lower() in model_lower or model_lower in key.lower():
            return val
    return {"input": 3.0, "output": 15.0}


def monthly_cost(
    input_tokens: int,
    output_tokens: int,
    requests: float,
    model: str,
    cache_hit_rate: float = 0.0,
) -> float:
    """Estimate monthly cost in USD. Cached requests assumed to cost 0 for input tokens."""
    p = get_pricing(model)
    effective_requests = requests * (1.0 - cache_hit_rate)
    cached_requests = requests * cache_hit_rate
    # Cached requests: no input cost, still pay output
    input_cost = (input_tokens / 1_000_000) * p["input"] * effective_requests
    output_cost = (output_tokens / 1_000_000) * p["output"] * requests
    return input_cost + output_cost


def analyze_prompt_sections(text: str) -> Dict[str, int]:
    """Break prompt into rough sections by line count and estimate token weight."""
    lines = text.strip().split("\n")
    total = len(lines)
    if total == 0:
        return {}

    # Heuristic sections
    sections: Dict[str, List[str]] = {
        "system_instructions": [],
        "examples": [],
        "context": [],
        "other": [],
    }
    current = "system_instructions"
    example_keywords = {"example", "e.g.", "for instance", "sample", "demo"}
    context_keywords = {"context", "background", "given", "input", "data"}

    for line in lines:
        lower = line.lower().strip()
        if any(k in lower for k in example_keywords):
            current = "examples"
        elif any(k in lower for k in context_keywords):
            current = "context"
        sections[current].append(line)

    result: Dict[str, int] = {}
    for name, section_lines in sections.items():
        if section_lines:
            section_text = "\n".join(section_lines)
            tokens, _ = count_tokens(section_text)
            result[name] = tokens
    return result


def suggest_optimizations(
    input_tokens: int,
    output_tokens: int,
    model: str,
    requests: float,
    cache_hit_rate: float,
    prompt_text: Optional[str] = None,
) -> List[Dict[str, str]]:
    """Generate optimization suggestions with estimated savings."""
    suggestions: List[Dict[str, str]] = []
    current_cost = monthly_cost(input_tokens, output_tokens, requests, model, cache_hit_rate)

    # 1. Model downgrade
    model_key = None
    for key in DOWNGRADE_MAP:
        if key.lower() in model.lower() or model.lower() in key.lower():
            model_key = key
            break
    if model_key and model_key in DOWNGRADE_MAP:
        for alt in DOWNGRADE_MAP[model_key]:
            alt_cost = monthly_cost(input_tokens, output_tokens, requests, alt, cache_hit_rate)
            savings = current_cost - alt_cost
            if savings > 0:
                pct = 100.0 * savings / current_cost if current_cost > 0 else 0
                suggestions.append({
                    "strategy": f"Downgrade to {alt}",
                    "savings_usd": f"${savings:,.2f}/month",
                    "savings_pct": f"{pct:.0f}%",
                    "note": "Test quality on your eval suite before switching.",
                })

    # 2. Caching
    if cache_hit_rate < 0.5:
        for target_rate in [0.2, 0.4, 0.6]:
            if target_rate <= cache_hit_rate:
                continue
            cached_cost = monthly_cost(input_tokens, output_tokens, requests, model, target_rate)
            savings = current_cost - cached_cost
            if savings > 0:
                pct = 100.0 * savings / current_cost if current_cost > 0 else 0
                suggestions.append({
                    "strategy": f"Add prompt caching ({target_rate:.0%} hit rate)",
                    "savings_usd": f"${savings:,.2f}/month",
                    "savings_pct": f"{pct:.0f}%",
                    "note": "Cache identical system prompts/few-shot examples. Anthropic and OpenAI both support prompt caching.",
                })
            break  # show first useful caching tier

    # 3. Prompt truncation (if prompt text is large)
    if input_tokens > 500:
        for reduction in [0.25, 0.50]:
            reduced = int(input_tokens * (1.0 - reduction))
            reduced_cost = monthly_cost(reduced, output_tokens, requests, model, cache_hit_rate)
            savings = current_cost - reduced_cost
            if savings > 0:
                pct = 100.0 * savings / current_cost if current_cost > 0 else 0
                suggestions.append({
                    "strategy": f"Reduce prompt by {reduction:.0%} ({input_tokens - reduced:,} tokens)",
                    "savings_usd": f"${savings:,.2f}/month",
                    "savings_pct": f"{pct:.0f}%",
                    "note": "Remove redundant instructions, compress examples, or use reference IDs instead of inline context.",
                })

    # 4. Output token limit
    if output_tokens > 200:
        reduced_out = int(output_tokens * 0.5)
        reduced_cost = monthly_cost(input_tokens, reduced_out, requests, model, cache_hit_rate)
        savings = current_cost - reduced_cost
        if savings > 0:
            pct = 100.0 * savings / current_cost if current_cost > 0 else 0
            suggestions.append({
                "strategy": f"Cap output tokens to ~{reduced_out:,}",
                "savings_usd": f"${savings:,.2f}/month",
                "savings_pct": f"{pct:.0f}%",
                "note": "Use max_tokens parameter. Instruct model to be concise in system prompt.",
            })

    return suggestions


def main():
    parser = argparse.ArgumentParser(
        description="Analyze prompt token cost and recommend optimization strategies."
    )
    parser.add_argument("text", nargs="?", help="Prompt text (or use --file / stdin)")
    parser.add_argument("--file", "-f", help="Read prompt from file")
    parser.add_argument(
        "--model", "-m", default="gpt-4o",
        help="Model name for cost estimate (default: gpt-4o)",
    )
    parser.add_argument(
        "--requests-per-month", "-r", type=float, required=True,
        help="Expected requests per month (e.g. 500000 or 5e5)",
    )
    parser.add_argument(
        "--output-tokens", "-o", type=int, default=256,
        help="Expected output tokens per request (default: 256)",
    )
    parser.add_argument(
        "--cache-hit-rate", type=float, default=0.0,
        help="Current cache hit rate 0.0–1.0 (default: 0.0 = no caching)",
    )
    parser.add_argument(
        "--list-models", action="store_true",
        help="List available models and pricing",
    )
    args = parser.parse_args()

    if args.list_models:
        print("Models (USD per 1M tokens, input / output):")
        for name, p in PRICING.items():
            print(f"  {name}: ${p['input']} / ${p['output']}")
        return 0

    # Read prompt text
    if args.file:
        path = Path(args.file)
        if not path.exists():
            print(f"File not found: {args.file}", file=sys.stderr)
            return 1
        text = path.read_text()
    elif args.text:
        text = args.text
    elif not sys.stdin.isatty():
        text = sys.stdin.read()
    else:
        parser.print_help()
        print("\nExample: --file prompt.txt --model gpt-4o --requests-per-month 500000", file=sys.stderr)
        return 0

    input_tokens, used_tiktoken = count_tokens(text)
    output_tokens = args.output_tokens
    requests = max(0.0, args.requests_per_month)
    cache_hit_rate = max(0.0, min(1.0, args.cache_hit_rate))

    current_cost = monthly_cost(input_tokens, output_tokens, requests, args.model, cache_hit_rate)

    # Report
    print("\n" + "=" * 70)
    print("📊 PROMPT COST OPTIMIZER")
    print("=" * 70)

    token_method = "tiktoken" if used_tiktoken else "estimate"
    print(f"\n📋 INPUTS:")
    print(f"   • Prompt tokens:       {input_tokens:,} ({token_method})")
    print(f"   • Output tokens/req:   {output_tokens:,}")
    print(f"   • Model:               {args.model}")
    print(f"   • Requests/month:      {requests:,.0f}")
    if cache_hit_rate > 0:
        print(f"   • Cache hit rate:      {cache_hit_rate:.0%}")

    pricing = get_pricing(args.model)
    print(f"\n💰 CURRENT COST:")
    print(f"   • Input pricing:       ${pricing['input']}/1M tokens")
    print(f"   • Output pricing:      ${pricing['output']}/1M tokens")
    print(f"   • Monthly cost:        ${current_cost:,.2f}")
    print(f"   • Annual projection:   ${current_cost * 12:,.2f}")
    cost_per_req = current_cost / requests if requests > 0 else 0
    print(f"   • Cost per request:    ${cost_per_req:.6f}")

    # Prompt breakdown (if available)
    sections = analyze_prompt_sections(text)
    if len(sections) > 1 or (len(sections) == 1 and "other" not in sections):
        print(f"\n📝 PROMPT BREAKDOWN:")
        for name, tokens in sorted(sections.items(), key=lambda x: -x[1]):
            pct = 100 * tokens / input_tokens if input_tokens > 0 else 0
            print(f"   • {name.replace('_', ' ').title()}: {tokens:,} tokens ({pct:.0f}%)")

    # Optimization suggestions
    suggestions = suggest_optimizations(
        input_tokens, output_tokens, args.model, requests, cache_hit_rate, text
    )
    if suggestions:
        print(f"\n🔧 OPTIMIZATION STRATEGIES:")
        for i, s in enumerate(suggestions, 1):
            print(f"\n   {i}. {s['strategy']}")
            print(f"      Savings: {s['savings_usd']} ({s['savings_pct']})")
            print(f"      → {s['note']}")
    else:
        print(f"\n✅ No major optimization opportunities found at current scale.")

    print("\n" + "=" * 70)
    return 0


if __name__ == "__main__":
    sys.exit(main())
