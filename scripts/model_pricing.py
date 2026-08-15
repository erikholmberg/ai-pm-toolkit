#!/usr/bin/env python3
"""
Model Pricing (shared)

Single source of truth for LLM per-token pricing across the toolkit. Import this
instead of hardcoding a price table in each script — four scripts used to carry
overlapping tables that disagreed with each other.

Every entry carries its own `last_verified` date and `source`. Prices go stale
fast, so a stale or unverified entry produces a loud warning rather than a
confidently wrong number.

Usage (as a library):
    from model_pricing import lookup, cost, staleness_warnings, PRICING

    p = lookup("claude-opus-5")           # -> ModelPrice
    c = cost("claude-opus-5", 1_000_000, 500_000)
    for w in staleness_warnings():
        print(w)

Usage (as a CLI):
    python model_pricing.py --list
    python model_pricing.py --list --provider anthropic
    python model_pricing.py --check          # exit 1 if anything is stale/unverified
    python model_pricing.py --cost claude-opus-5 --input-tokens 1e6 --output-tokens 5e5

Pricing conventions:
    - All prices are USD per 1,000,000 tokens ("per MTok").
    - Anthropic first-party API rates. Bedrock/Vertex are partner-operated with
      separate pricing; entries prefixed `bedrock.` carry their own numbers.
    - Cache and batch rates are expressed as multipliers on the base input price
      because they are uniform across the family, not per-model constants.

Requirements:
    None (stdlib only).
"""

import argparse
import json
import sys
from dataclasses import dataclass, asdict
from datetime import date, datetime
from typing import Dict, List, Optional, Tuple

import toolkit_io

# How old a verified price can be before we warn. Pricing changes often enough
# that a quarter is a reasonable ceiling.
STALE_AFTER_DAYS = 90


@dataclass(frozen=True)
class ModelPrice:
    """Per-MTok pricing for one model."""

    input_per_mtok: float
    output_per_mtok: float
    provider: str
    source: str
    # ISO date the price was checked against `source`. None = never verified;
    # treat the numbers as indicative only.
    last_verified: Optional[str] = None
    notes: str = ""

    def age_days(self, today: Optional[date] = None) -> Optional[int]:
        if not self.last_verified:
            return None
        today = today or date.today()
        checked = datetime.strptime(self.last_verified, "%Y-%m-%d").date()
        return (today - checked).days

    def is_stale(self, today: Optional[date] = None) -> bool:
        age = self.age_days(today)
        return age is None or age > STALE_AFTER_DAYS


# ---------------------------------------------------------------------------
# Cache and batch multipliers (applied to the base input price)
# ---------------------------------------------------------------------------
# Anthropic: cache writes cost 1.25x base input at the 5-minute TTL and 2x at
# the 1-hour TTL; cache reads cost ~0.1x. Batch API is 50% off all token usage.
# Verified 2026-06-24 against platform.claude.com/docs/en/build-with-claude/prompt-caching
CACHE_WRITE_5M_MULTIPLIER = 1.25
CACHE_WRITE_1H_MULTIPLIER = 2.00
CACHE_READ_MULTIPLIER = 0.10
BATCH_DISCOUNT = 0.50  # fraction off both input and output

# Break-even reads for a cache entry to pay for itself, given the write premium:
#   5m TTL: 1.25x + 0.1x  < 2x  -> pays off from the 2nd request
#   1h TTL: 2.00x + 0.2x  < 3x  -> pays off from the 3rd request
CACHE_BREAKEVEN_REQUESTS = {"5m": 2, "1h": 3}


# ---------------------------------------------------------------------------
# The table
# ---------------------------------------------------------------------------
_ANTHROPIC_SOURCE = "https://platform.claude.com/docs/en/about-claude/models/overview"
_ANTHROPIC_VERIFIED = "2026-06-24"

PRICING: Dict[str, ModelPrice] = {
    # --- Anthropic first-party API ---------------------------------------
    "claude-fable-5": ModelPrice(
        10.00, 50.00, "anthropic", _ANTHROPIC_SOURCE, _ANTHROPIC_VERIFIED,
        "Most capable widely released model; 1M context, 128K max output.",
    ),
    "claude-mythos-5": ModelPrice(
        10.00, 50.00, "anthropic", _ANTHROPIC_SOURCE, _ANTHROPIC_VERIFIED,
        "Project Glasswing only; same capabilities and pricing as Fable 5.",
    ),
    "claude-opus-5": ModelPrice(
        5.00, 25.00, "anthropic", _ANTHROPIC_SOURCE, _ANTHROPIC_VERIFIED,
        "Current Opus. Fast mode is priced separately at 10.00/50.00.",
    ),
    "claude-opus-4-8": ModelPrice(
        5.00, 25.00, "anthropic", _ANTHROPIC_SOURCE, _ANTHROPIC_VERIFIED,
    ),
    "claude-opus-4-7": ModelPrice(
        5.00, 25.00, "anthropic", _ANTHROPIC_SOURCE, _ANTHROPIC_VERIFIED,
    ),
    "claude-opus-4-6": ModelPrice(
        5.00, 25.00, "anthropic", _ANTHROPIC_SOURCE, _ANTHROPIC_VERIFIED,
    ),
    "claude-sonnet-5": ModelPrice(
        3.00, 15.00, "anthropic", _ANTHROPIC_SOURCE, _ANTHROPIC_VERIFIED,
        "Introductory rate of 2.00/10.00 applies through 2026-08-31.",
    ),
    "claude-sonnet-4-6": ModelPrice(
        3.00, 15.00, "anthropic", _ANTHROPIC_SOURCE, _ANTHROPIC_VERIFIED,
    ),
    "claude-haiku-4-5": ModelPrice(
        1.00, 5.00, "anthropic", _ANTHROPIC_SOURCE, _ANTHROPIC_VERIFIED,
        "200K context (not 1M).",
    ),
    # --- Amazon Bedrock (partner-operated; separate pricing) --------------
    # Bedrock publishes its own rates per region. These are carried over from
    # the toolkit's original tables and have never been verified against the
    # AWS pricing page — treat as indicative until someone checks them.
    "bedrock.amazon-titan-text-express": ModelPrice(
        0.80, 3.20, "bedrock", "https://aws.amazon.com/bedrock/pricing/", None,
    ),
    "bedrock.amazon-titan-text-lite": ModelPrice(
        0.30, 0.40, "bedrock", "https://aws.amazon.com/bedrock/pricing/", None,
    ),
    "bedrock.meta-llama3-2-70b": ModelPrice(
        0.99, 0.99, "bedrock", "https://aws.amazon.com/bedrock/pricing/", None,
    ),
    "bedrock.meta-llama3-2-3b": ModelPrice(
        0.12, 0.12, "bedrock", "https://aws.amazon.com/bedrock/pricing/", None,
    ),
    "bedrock.mistral-large": ModelPrice(
        4.00, 12.00, "bedrock", "https://aws.amazon.com/bedrock/pricing/", None,
        "Two toolkit tables previously disagreed here (0.50/1.50 vs 4.00/12.00); "
        "the higher figure is kept pending verification.",
    ),
    "bedrock.cohere-command-r-plus": ModelPrice(
        1.50, 2.00, "bedrock", "https://aws.amazon.com/bedrock/pricing/", None,
    ),
    # --- Other vendors ----------------------------------------------------
    # Carried over from the toolkit's original tables. Unverified: the newest
    # entries here predate the current model generations, so any comparison
    # against them understates what a current competitor model costs.
    "gpt-4o": ModelPrice(
        2.50, 10.00, "openai", "https://openai.com/api/pricing/", None,
    ),
    "gpt-4o-mini": ModelPrice(
        0.15, 0.60, "openai", "https://openai.com/api/pricing/", None,
    ),
    "gpt-4-turbo": ModelPrice(
        10.00, 30.00, "openai", "https://openai.com/api/pricing/", None,
    ),
    "gemini-1.5-pro": ModelPrice(
        1.25, 5.00, "google", "https://ai.google.dev/pricing", None,
    ),
    "gemini-1.5-flash": ModelPrice(
        0.075, 0.30, "google", "https://ai.google.dev/pricing", None,
    ),
}

# Short aliases and legacy names -> canonical key. Keeps older CLI invocations
# working after the table was consolidated.
ALIASES: Dict[str, str] = {
    "claude": "claude-opus-5",
    "opus": "claude-opus-5",
    "sonnet": "claude-sonnet-5",
    "haiku": "claude-haiku-4-5",
    "fable": "claude-fable-5",
    "anthropic.claude-opus-5": "claude-opus-5",
    "anthropic.claude-sonnet-5": "claude-sonnet-5",
    "anthropic.claude-haiku-4-5": "claude-haiku-4-5",
    "titan": "bedrock.amazon-titan-text-express",
    "titan-text-express": "bedrock.amazon-titan-text-express",
    "titan-text-lite": "bedrock.amazon-titan-text-lite",
    "llama3": "bedrock.meta-llama3-2-3b",
    "mistral": "bedrock.mistral-large",
    "mistral-large": "bedrock.mistral-large",
    "cohere": "bedrock.cohere-command-r-plus",
    "gpt-4o-2024-08-06": "gpt-4o",
}

# Models the toolkit used to price that no longer exist. Pointing at the
# replacement beats silently falling through to a substring match.
RETIRED: Dict[str, str] = {
    "claude-3-5-sonnet": "claude-sonnet-5",
    "claude-3-5-sonnet-v2": "claude-sonnet-5",
    "claude-3-5-sonnet-20241022": "claude-sonnet-5",
    "claude-3-sonnet": "claude-sonnet-5",
    "claude-3-opus": "claude-opus-5",
    "claude-3-haiku": "claude-haiku-4-5",
    "claude-3-5-haiku": "claude-haiku-4-5",
    "claude-2.1": "claude-sonnet-5",
    "gpt-4": "gpt-4-turbo",
    "gpt-3.5-turbo": "gpt-4o-mini",
}


class UnknownModelError(KeyError):
    """Raised when a model name can't be resolved to a price."""


_retired_notices_shown: set = set()


def canonical_name(model: str) -> str:
    """Resolve a user-supplied model string to a key in PRICING.

    Resolution order: exact match, alias, retired-model redirect, then a unique
    substring match. Ambiguous substrings raise rather than guessing.
    """
    key = model.strip().lower()
    if key in PRICING:
        return key
    if key in ALIASES:
        return ALIASES[key]
    if key in RETIRED:
        replacement = RETIRED[key]
        # canonical_name runs several times per request (lookup, cost, warning);
        # the user only needs to be told once.
        if key not in _retired_notices_shown:
            _retired_notices_shown.add(key)
            print(
                f"Note: '{model}' is retired; pricing with its replacement "
                f"'{replacement}'.",
                file=sys.stderr,
            )
        return replacement

    matches = [name for name in PRICING if key in name]
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        raise UnknownModelError(
            f"'{model}' is ambiguous; matches {', '.join(sorted(matches))}"
        )
    raise UnknownModelError(
        f"Unknown model '{model}'. Known models: {', '.join(sorted(PRICING))}"
    )


def lookup(model: str) -> ModelPrice:
    """Return the ModelPrice for a model name (aliases and substrings allowed)."""
    return PRICING[canonical_name(model)]


def get_pricing(model: str) -> Tuple[float, float]:
    """Return (input_per_mtok, output_per_mtok). Compatibility shim for the
    per-script `get_pricing` helpers this module replaced."""
    p = lookup(model)
    return p.input_per_mtok, p.output_per_mtok


def cost(
    model: str,
    input_tokens: float,
    output_tokens: float,
    cached_input_tokens: float = 0.0,
    cache_write_tokens: float = 0.0,
    cache_ttl: str = "5m",
    batch: bool = False,
) -> Dict[str, float]:
    """Cost in USD for one request (or a batch of identical requests).

    `cached_input_tokens` are billed at the cache-read rate and `cache_write_tokens`
    at the cache-write rate; both are in addition to `input_tokens`, which covers
    the uncached remainder. This mirrors how the API reports usage.
    """
    p = lookup(model)
    write_multiplier = (
        CACHE_WRITE_1H_MULTIPLIER if cache_ttl == "1h" else CACHE_WRITE_5M_MULTIPLIER
    )

    per_token_in = p.input_per_mtok / 1_000_000
    per_token_out = p.output_per_mtok / 1_000_000

    input_cost = input_tokens * per_token_in
    output_cost = output_tokens * per_token_out
    cache_read_cost = cached_input_tokens * per_token_in * CACHE_READ_MULTIPLIER
    cache_write_cost = cache_write_tokens * per_token_in * write_multiplier

    total = input_cost + output_cost + cache_read_cost + cache_write_cost
    if batch:
        total *= 1 - BATCH_DISCOUNT

    return {
        "model": canonical_name(model),
        "input_cost": input_cost,
        "output_cost": output_cost,
        "cache_read_cost": cache_read_cost,
        "cache_write_cost": cache_write_cost,
        "total_cost": total,
        "batch_applied": batch,
    }


def staleness_warnings(today: Optional[date] = None) -> List[str]:
    """One warning line per stale or never-verified price entry."""
    warnings = []
    unverified = []
    stale = []
    for name, p in sorted(PRICING.items()):
        age = p.age_days(today)
        if age is None:
            unverified.append(name)
        elif age > STALE_AFTER_DAYS:
            stale.append((name, age))

    if unverified:
        warnings.append(
            f"UNVERIFIED PRICING ({len(unverified)} models): "
            f"{', '.join(unverified)}. These numbers have never been checked "
            f"against the vendor's pricing page — do not quote them to "
            f"stakeholders without verifying."
        )
    for name, age in stale:
        warnings.append(
            f"STALE PRICING: {name} last verified {age} days ago "
            f"(threshold {STALE_AFTER_DAYS}). Re-check {PRICING[name].source}."
        )
    return warnings


def warn_if_stale(model: Optional[str] = None, stream=sys.stderr) -> None:
    """Print staleness warnings for one model, or for the whole table.

    Scripts that price a single model should pass that model so users see one
    relevant warning instead of the full list.
    """
    if model is not None:
        p = lookup(model)
        if p.is_stale():
            age = p.age_days()
            when = f"{age} days ago" if age is not None else "never"
            print(
                f"Warning: pricing for {canonical_name(model)} was last verified "
                f"{when}. Re-check {p.source} before relying on this figure.",
                file=stream,
            )
        return
    for warning in staleness_warnings():
        print(f"Warning: {warning}", file=stream)


def list_models(provider: Optional[str] = None) -> List[str]:
    """Canonical model names, optionally filtered to one provider."""
    return sorted(
        name
        for name, p in PRICING.items()
        if provider is None or p.provider == provider
    )


def _fmt_row(name: str, p: ModelPrice) -> str:
    age = p.age_days()
    if age is None:
        verified = "UNVERIFIED"
    elif age > STALE_AFTER_DAYS:
        verified = f"{p.last_verified} (STALE, {age}d)"
    else:
        verified = f"{p.last_verified} ({age}d)"
    return (
        f"  {name:<36} {p.input_per_mtok:>8.3f} {p.output_per_mtok:>9.3f}  "
        f"{p.provider:<10} {verified}"
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Shared LLM pricing table for the toolkit (USD per 1M tokens).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  model_pricing.py --list
  model_pricing.py --list --provider anthropic
  model_pricing.py --check
  model_pricing.py --cost claude-opus-5 --input-tokens 1e6 --output-tokens 5e5
  model_pricing.py --cost claude-opus-5 --input-tokens 1e6 --output-tokens 5e5 --batch
        """,
    )
    parser.add_argument("--list", action="store_true", help="List all models and prices")
    parser.add_argument("--provider", help="Filter --list to one provider")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Report stale/unverified entries; exit 1 if any are found",
    )
    parser.add_argument("--cost", metavar="MODEL", help="Price a single request")
    parser.add_argument("--input-tokens", type=float, default=0.0)
    parser.add_argument("--output-tokens", type=float, default=0.0)
    parser.add_argument("--cached-input-tokens", type=float, default=0.0)
    parser.add_argument("--cache-write-tokens", type=float, default=0.0)
    parser.add_argument("--cache-ttl", choices=["5m", "1h"], default="5m")
    parser.add_argument("--batch", action="store_true", help="Apply the batch discount")
    parser.add_argument("--output", "-o", help="Write JSON results to file")
    args = parser.parse_args()

    if not (args.list or args.check or args.cost):
        parser.print_help()
        return 0

    result: Dict[str, object] = {}

    if args.list:
        names = list_models(args.provider)
        if not names:
            print(f"No models for provider '{args.provider}'.")
            return 1
        print(f"\n{'MODEL':<38}{'IN/MTok':>8}{'OUT/MTok':>10}  {'PROVIDER':<11}VERIFIED")
        print("-" * 92)
        for name in names:
            print(_fmt_row(name, PRICING[name]))
        print(
            f"\nCache read {CACHE_READ_MULTIPLIER:.2f}x input; cache write "
            f"{CACHE_WRITE_5M_MULTIPLIER:.2f}x (5m) / {CACHE_WRITE_1H_MULTIPLIER:.2f}x "
            f"(1h); batch {BATCH_DISCOUNT:.0%} off."
        )
        result["models"] = {n: asdict(PRICING[n]) for n in names}

    if args.cost:
        breakdown = cost(
            args.cost,
            args.input_tokens,
            args.output_tokens,
            args.cached_input_tokens,
            args.cache_write_tokens,
            args.cache_ttl,
            args.batch,
        )
        warn_if_stale(args.cost)
        print(f"\nCost for {breakdown['model']}:")
        print(f"  Input          ${breakdown['input_cost']:.6f}")
        print(f"  Output         ${breakdown['output_cost']:.6f}")
        if args.cached_input_tokens:
            print(f"  Cache read     ${breakdown['cache_read_cost']:.6f}")
        if args.cache_write_tokens:
            print(f"  Cache write    ${breakdown['cache_write_cost']:.6f}")
        if args.batch:
            print(f"  Batch discount -{BATCH_DISCOUNT:.0%}")
        print(f"  Total          ${breakdown['total_cost']:.6f}")
        result["cost"] = breakdown

    warnings = staleness_warnings()
    if args.check:
        if warnings:
            print("\nPricing table needs attention:\n")
            for w in warnings:
                print(f"  - {w}")
        else:
            print(f"\nAll {len(PRICING)} price entries verified within "
                  f"{STALE_AFTER_DAYS} days.")
        result["warnings"] = warnings

    if args.output:
        with open(args.output, "w") as f:
            json.dump(toolkit_io.envelope(result, "model_pricing"), f, indent=2)
        print(f"\nWrote {args.output}")

    return 1 if (args.check and warnings) else 0


if __name__ == "__main__":
    sys.exit(main())
