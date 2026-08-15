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

# Pricing lives in scripts/model_pricing.py so every cost script agrees on one
# table. Run `python model_pricing.py --check` to see what needs re-verifying.
import model_pricing

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
    """Get pricing for model (per 1M tokens) from the shared table."""
    try:
        p = model_pricing.lookup(model)
    except model_pricing.UnknownModelError as e:
        print(f"Warning: {e}", file=sys.stderr)
        print("Falling back to claude-sonnet-5 pricing.", file=sys.stderr)
        p = model_pricing.lookup("claude-sonnet-5")
    else:
        model_pricing.warn_if_stale(model)
    return {"input": p.input_per_mtok, "output": p.output_per_mtok}


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
    if used_tiktoken and "claude" in args.model.lower():
        print(
            "Warning: tiktoken uses OpenAI's cl100k_base encoding, which is not "
            "Claude's tokenizer — this count (and the cost below) will be off. "
            "For an exact figure use the Anthropic count_tokens endpoint.",
            file=sys.stderr,
        )

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
