#!/usr/bin/env python3
"""
Token Counter & Cost Estimator

Count tokens in text (prompts, files) and estimate API cost for common LLM models.

Usage:
    python token-counter.py "Your prompt text here"
    python token-counter.py --file prompt.txt
    python token-counter.py --file prompt.txt --model gpt-4o --output-tokens 500
    echo "Prompt" | python token-counter.py

Optional: pip install tiktoken for accurate OpenAI token counts (else uses ~4 chars/token estimate).
"""

import argparse
import sys
from pathlib import Path
from typing import Dict, Optional, Tuple

# Approximate USD per 1M tokens (input / output) - keep in sync with evals/scripts/eval-cost-calculator.py
PRICING: Dict[str, Dict[str, float]] = {
    "claude-3-opus-20240229": {"input": 15.0, "output": 75.0},
    "claude-3-sonnet-20240229": {"input": 3.0, "output": 15.0},
    "claude-3-haiku-20240307": {"input": 0.25, "output": 1.25},
    "claude-3-5-sonnet-20241022": {"input": 3.0, "output": 15.0},
    "gpt-4o": {"input": 2.5, "output": 10.0},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "gpt-4-turbo": {"input": 10.0, "output": 30.0},
    "gpt-4": {"input": 30.0, "output": 60.0},
    "gpt-3.5-turbo": {"input": 0.50, "output": 1.50},
}

# Fallback: rough tokens per character (English text)
CHARS_PER_TOKEN_ESTIMATE = 4


def count_tokens_tiktoken(text: str) -> Optional[int]:
    """Count tokens using tiktoken (OpenAI encoding). Returns None if tiktoken not available."""
    try:
        import tiktoken
        enc = tiktoken.get_encoding("cl100k_base")
        return len(enc.encode(text))
    except Exception:
        return None


def count_tokens_estimate(text: str) -> int:
    """Estimate token count from character count."""
    if not text:
        return 0
    return max(1, len(text) // CHARS_PER_TOKEN_ESTIMATE)


def count_tokens(text: str) -> Tuple[int, bool]:
    """
    Return (token_count, used_tiktoken).
    Uses tiktoken if available, else character-based estimate.
    """
    n = count_tokens_tiktoken(text)
    if n is not None:
        return n, True
    return count_tokens_estimate(text), False


def get_pricing(model: str) -> Dict[str, float]:
    """Get pricing for model (per 1M tokens). Matches by substring."""
    model_lower = model.lower()
    for key, val in PRICING.items():
        if key.lower() in model_lower or model_lower in key.lower():
            return val
    return {"input": 3.0, "output": 15.0}  # default


def estimate_cost(
    input_tokens: int,
    output_tokens: int,
    model: str
) -> Tuple[float, float, float]:
    """Return (input_cost_usd, output_cost_usd, total_cost_usd)."""
    p = get_pricing(model)
    inc = (input_tokens / 1_000_000) * p["input"]
    out = (output_tokens / 1_000_000) * p["output"]
    return round(inc, 6), round(out, 6), round(inc + out, 6)


def main():
    parser = argparse.ArgumentParser(
        description="Count tokens and estimate API cost for LLM prompts"
    )
    parser.add_argument("text", nargs="?", help="Text to count (or use --file / stdin)")
    parser.add_argument("--file", "-f", help="Read text from file")
    parser.add_argument("--model", "-m", default="gpt-4o", help="Model name for cost estimate")
    parser.add_argument("--output-tokens", "-o", type=int, default=None,
                        help="Expected output tokens (for cost). If omitted, assumes same as input.")
    parser.add_argument("--list-models", action="store_true", help="List models and pricing")
    parser.add_argument("--no-cost", action="store_true", help="Only print token count")
    args = parser.parse_args()

    if args.list_models:
        print("Models (USD per 1M tokens, input / output):")
        for name, p in PRICING.items():
            print(f"  {name}: ${p['input']} / ${p['output']}")
        return 0

    if args.file:
        path = Path(args.file)
        if not path.exists():
            print(f"File not found: {args.file}", file=sys.stderr)
            return 1
        text = path.read_text()
    elif args.text:
        text = args.text
    else:
        text = sys.stdin.read()

    n_tokens, used_tiktoken = count_tokens(text)
    print(f"Tokens: {n_tokens:,}" + (" (tiktoken)" if used_tiktoken else " (estimate)"))

    if args.no_cost:
        return 0

    out_tokens = args.output_tokens if args.output_tokens is not None else n_tokens
    inc_cost, out_cost, total = estimate_cost(n_tokens, out_tokens, args.model)
    print(f"Model: {args.model}")
    print(f"Input tokens:  {n_tokens:,}  → ${inc_cost:.4f}")
    print(f"Output tokens: {out_tokens:,}  → ${out_cost:.4f}")
    print(f"Total estimate: ${total:.4f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
