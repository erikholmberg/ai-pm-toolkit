#!/usr/bin/env python3
"""
Prompt Cache ROI

Whether prompt caching is actually paying for itself — measured from real
usage, or projected before you turn it on.

prompt-cost-optimizer.py already accepts `--cache-hit-rate`, but it takes that
number as a given and treats a cache hit as free. Neither is true. The hit rate
is a *consequence* of your traffic pattern and the cache TTL, and caching is not
free on either side: a write costs 1.25x the input rate (2x at the 1h TTL) and a
read still costs 0.10x. Cache a prefix that gets reused twice an hour on a 5m
TTL and you pay the write premium over and over for nothing.

So this makes the hit rate an output:

  * With `--csv` (an `llm_usage` export from connectors/), it reports what
    caching *actually* saved or cost you, per model and feature, from the
    cache_write and cache_read token counts your gateway already reports.
  * Without one, it projects the hit rate from request rate, TTL, and how many
    conversations run concurrently — then solves for the traffic level where
    caching starts paying.

It also flags the two failure modes that cost real money and are invisible on a
bill: high-volume features with caching off, and features writing far more than
they read.

Usage:
    # Measured, from a gateway export
    python prompt-cache-roi.py --csv usage.csv
    python prompt-cache-roi.py --csv usage.csv --prefix-tokens 4000   # size the opportunity

    # Projected, before turning caching on
    python prompt-cache-roi.py --prefix-tokens 4000 --requests-per-day 20000
    python prompt-cache-roi.py --prefix-tokens 12000 --requests-per-day 800 --ttl 1h
    python prompt-cache-roi.py --prefix-tokens 4000 --requests-per-day 20000 --concurrency 40

    python prompt-cache-roi.py --csv usage.csv --markdown report.md --output roi.json

CSV format: the `llm_usage` contract (see connectors/datasets.py)
    date,model,feature,requests,input_tokens,output_tokens,cached_input_tokens,cache_write_tokens,cost_usd

    Required: model. Everything else defaults to 0. Produce one with:
        python connectors/fetch.py gateway llm_usage --provider litellm --out usage.csv

Requirements:
    None (stdlib only).
"""

import argparse
import math
import sys
from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple

import csv_columns
import model_pricing
import toolkit_io

TOOL = "prompt-cache-roi"

TTL_SECONDS = {"5m": 300, "1h": 3600}


# --------------------------------------------------------------------------
# Cache economics
# --------------------------------------------------------------------------


def write_multiplier(ttl: str) -> float:
    return (
        model_pricing.CACHE_WRITE_1H_MULTIPLIER
        if ttl == "1h"
        else model_pricing.CACHE_WRITE_5M_MULTIPLIER
    )


def breakeven_reads_per_write(ttl: str) -> float:
    """Reads needed per write before caching is cheaper than not caching.

    A write costs (write_mult - 1) extra versus plain input; each read saves
    (1 - read_mult). Break even where the two balance. Derived from the
    multipliers rather than hardcoded so it stays correct if pricing moves —
    model_pricing.CACHE_BREAKEVEN_REQUESTS carries the rounded version.
    """
    extra = write_multiplier(ttl) - 1.0
    saved = 1.0 - model_pricing.CACHE_READ_MULTIPLIER
    return extra / saved


def predict_hit_rate(
    requests_per_day: float, ttl: str, concurrency: int = 1
) -> float:
    """Expected share of requests that hit a warm cache.

    Models arrivals per concurrent stream as Poisson: a stream re-writes the
    cache whenever the gap since its last request exceeds the TTL, which
    happens with probability e^(-T/mean_gap). Concurrency matters and is the
    part people miss — 40 simultaneous conversations each keep their own cache
    entry, so each one sees 1/40th of the traffic and goes cold far more often
    than the aggregate rate suggests.

    Assumes reads refresh the TTL (a sliding window), which is how Anthropic's
    cache behaves.
    """
    if requests_per_day <= 0 or concurrency < 1:
        return 0.0
    per_stream = requests_per_day / concurrency
    if per_stream <= 1:
        return 0.0
    mean_gap = 86400.0 / per_stream
    miss_probability = math.exp(-TTL_SECONDS[ttl] / mean_gap)
    # The first request of each stream is always a write.
    writes = 1 + (per_stream - 1) * miss_probability
    return max(0.0, 1.0 - writes / per_stream)


def rate_for(model: str) -> Optional[float]:
    """Input price per token, or None if the model isn't priced."""
    try:
        return model_pricing.lookup(model).input_per_mtok / 1_000_000
    except Exception:
        return None


def economics(
    model: str,
    uncached_input: float,
    cached_input: float,
    cache_written: float,
    ttl: str = "5m",
) -> Optional[Dict[str, float]]:
    """Cost with caching versus the same tokens with caching off.

    The comparison holds token volume fixed: every token currently billed as a
    cache read or write would have been a plain input token without caching.
    That is the only apples-to-apples baseline — comparing against "input
    tokens only" would credit caching for tokens it never touched.
    """
    rate = rate_for(model)
    if rate is None:
        return None
    equivalent_input = uncached_input + cached_input + cache_written
    without = equivalent_input * rate
    with_cache = (
        uncached_input * rate
        + cached_input * rate * model_pricing.CACHE_READ_MULTIPLIER
        + cache_written * rate * write_multiplier(ttl)
    )
    cacheable = cached_input + cache_written
    return {
        "without_cache_usd": without,
        "with_cache_usd": with_cache,
        "savings_usd": without - with_cache,
        "savings_pct": ((without - with_cache) / without * 100) if without else 0.0,
        "hit_rate": (cached_input / cacheable) if cacheable else 0.0,
        "reads_per_write": (cached_input / cache_written) if cache_written else 0.0,
    }


# --------------------------------------------------------------------------
# Measured mode
# --------------------------------------------------------------------------


def load_usage(path: str) -> Tuple[Dict[Tuple[str, str], Dict[str, float]], List[str]]:
    warnings: List[str] = []
    fields = ("requests", "input_tokens", "output_tokens", "cached_input_tokens",
              "cache_write_tokens", "cost_usd")
    grouped: Dict[Tuple[str, str], Dict[str, float]] = defaultdict(
        lambda: {f: 0.0 for f in fields}
    )
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv_columns.DictReader(f)
        headers = reader.fieldnames or []
        if not csv_columns.resolve(headers, "model", "model_name", "model_id"):
            raise SystemExit(
                f"Error: no model column. CSV has: {', '.join(headers) or '(empty)'}"
            )
        if not csv_columns.resolve(
            headers, "cached_input_tokens", "cache_read_tokens", "cache_write_tokens"
        ):
            warnings.append(
                "no cache token columns found — every feature will read as "
                "'caching off'. If your gateway does report them, check the "
                "export rather than trusting the zeros."
            )
        for row in reader:
            model = str(row.first("model", "model_name", "model_id", default="")).strip()
            if not model:
                continue
            feature = (
                str(row.first("feature", "tag", "app", "project", default="")).strip()
                or "—"
            )
            bucket = grouped[(model, feature)]
            for field in fields:
                bucket[field] += _number(row.get(field, 0))
    if not grouped:
        raise SystemExit("Error: no usable rows (need a model column).")
    return dict(grouped), warnings


def _number(raw: Any) -> float:
    text = str(raw or "").strip().replace(",", "").replace("$", "")
    if not text:
        return 0.0
    try:
        return float(text)
    except ValueError:
        return 0.0


def analyze_measured(
    grouped: Dict[Tuple[str, str], Dict[str, float]],
    ttl: str,
    assumed_prefix: Optional[int],
) -> Dict[str, Any]:
    rows: List[Dict[str, Any]] = []
    unpriced: List[str] = []

    for (model, feature), totals in grouped.items():
        econ = economics(
            model,
            totals["input_tokens"],
            totals["cached_input_tokens"],
            totals["cache_write_tokens"],
            ttl,
        )
        entry: Dict[str, Any] = {
            "model": model,
            "feature": feature,
            "requests": totals["requests"],
            "input_tokens": totals["input_tokens"],
            "cached_input_tokens": totals["cached_input_tokens"],
            "cache_write_tokens": totals["cache_write_tokens"],
            "billed_usd": totals["cost_usd"],
            "caching_on": totals["cached_input_tokens"] + totals["cache_write_tokens"] > 0,
        }
        if econ is None:
            unpriced.append(model)
            entry["verdict"] = "unpriced"
        else:
            entry.update(econ)
            entry["verdict"] = _verdict(entry, ttl, assumed_prefix)
        rows.append(entry)

    rows.sort(key=lambda r: -(r.get("savings_usd") or 0.0))
    priced = [r for r in rows if r["verdict"] != "unpriced"]

    return {
        "ttl": ttl,
        "breakeven_reads_per_write": breakeven_reads_per_write(ttl),
        "rows": rows,
        "totals": {
            "savings_usd": sum(r.get("savings_usd", 0.0) for r in priced),
            "without_cache_usd": sum(r.get("without_cache_usd", 0.0) for r in priced),
            "with_cache_usd": sum(r.get("with_cache_usd", 0.0) for r in priced),
        },
        "unpriced_models": sorted(set(unpriced)),
        "opportunities": _opportunities(rows, ttl, assumed_prefix),
    }


def _verdict(entry: Dict[str, Any], ttl: str, assumed_prefix: Optional[int]) -> str:
    if not entry["caching_on"]:
        return "off"
    if entry["reads_per_write"] < breakeven_reads_per_write(ttl):
        # Paying the write premium more often than the reads repay it.
        return "losing"
    if entry["savings_pct"] < 5:
        return "marginal"
    return "paying"


def _opportunities(
    rows: List[Dict[str, Any]], ttl: str, assumed_prefix: Optional[int]
) -> List[Dict[str, Any]]:
    """Features where caching is off, sized if a prefix estimate was given."""
    out = []
    for row in rows:
        if row["caching_on"] or row["verdict"] == "unpriced":
            continue
        if row["requests"] < 1:
            continue
        rate = rate_for(row["model"])
        if rate is None:
            continue
        item: Dict[str, Any] = {
            "model": row["model"],
            "feature": row["feature"],
            "requests": row["requests"],
            "input_tokens": row["input_tokens"],
        }
        prefix = assumed_prefix
        if prefix:
            # Assume the prefix repeats on every request and would hit at the
            # rate this traffic implies. Explicitly an estimate: nothing here
            # knows which part of a prompt is actually a stable prefix.
            hit = predict_hit_rate(row["requests"], ttl)
            avg_input = row["input_tokens"] / row["requests"]
            # Cap at the tokens that actually exist. Without this, a prefix
            # larger than the average request invents volume and reports
            # savings exceeding the entire bill for that feature.
            cacheable = min(prefix * row["requests"], row["input_tokens"])
            if prefix > avg_input:
                item["prefix_exceeds_avg_input"] = True
                item["avg_input_tokens"] = avg_input
            econ = economics(
                row["model"],
                max(0.0, row["input_tokens"] - cacheable),
                cacheable * hit,
                cacheable * (1 - hit),
                ttl,
            )
            if econ:
                item["assumed_prefix_tokens"] = prefix
                item["projected_hit_rate"] = hit
                item["projected_savings_usd"] = econ["savings_usd"]
        out.append(item)
    out.sort(key=lambda r: -(r.get("projected_savings_usd") or r["requests"]))
    return out


# --------------------------------------------------------------------------
# Projection mode
# --------------------------------------------------------------------------


def analyze_projection(
    model: str,
    prefix_tokens: int,
    requests_per_day: float,
    other_input_tokens: int,
    ttl: str,
    concurrency: int,
) -> Dict[str, Any]:
    hit = predict_hit_rate(requests_per_day, ttl, concurrency)
    cacheable = prefix_tokens * requests_per_day
    econ = economics(
        model,
        other_input_tokens * requests_per_day,
        cacheable * hit,
        cacheable * (1 - hit),
        ttl,
    )
    if econ is None:
        raise SystemExit(
            f"Error: no price on file for {model!r}. "
            f"Run `python model_pricing.py --check` to see known models."
        )

    curve = []
    for rate in _sweep(requests_per_day):
        h = predict_hit_rate(rate, ttl, concurrency)
        e = economics(
            model,
            other_input_tokens * rate,
            prefix_tokens * rate * h,
            prefix_tokens * rate * (1 - h),
            ttl,
        )
        curve.append(
            {
                "requests_per_day": rate,
                "hit_rate": h,
                "daily_savings_usd": e["savings_usd"] if e else 0.0,
            }
        )

    return {
        "mode": "projection",
        "model": model,
        "ttl": ttl,
        "concurrency": concurrency,
        "prefix_tokens": prefix_tokens,
        "requests_per_day": requests_per_day,
        "predicted_hit_rate": hit,
        "daily": econ,
        "monthly_savings_usd": econ["savings_usd"] * 30,
        "breakeven_reads_per_write": breakeven_reads_per_write(ttl),
        "breakeven_requests_per_day": _breakeven_rate(
            model, prefix_tokens, other_input_tokens, ttl, concurrency
        ),
        "curve": curve,
    }


def _sweep(anchor: float) -> List[float]:
    base = [100, 500, 1_000, 5_000, 10_000, 50_000, 100_000, 500_000]
    return sorted(set(base + [anchor]))


def _breakeven_rate(
    model: str, prefix_tokens: int, other: int, ttl: str, concurrency: int
) -> Optional[float]:
    """Lowest requests/day at which caching stops losing money.

    Bisection rather than algebra: the hit rate is exponential in the request
    rate, so savings has no clean closed form.
    """
    def savings(rate: float) -> float:
        h = predict_hit_rate(rate, ttl, concurrency)
        e = economics(
            model, other * rate, prefix_tokens * rate * h, prefix_tokens * rate * (1 - h), ttl
        )
        return e["savings_usd"] if e else 0.0

    low, high = 1.0, 5_000_000.0
    if savings(high) <= 0:
        return None
    if savings(low) > 0:
        return low
    for _ in range(60):
        mid = (low + high) / 2
        if savings(mid) > 0:
            high = mid
        else:
            low = mid
    return round(high)


# --------------------------------------------------------------------------
# Output
# --------------------------------------------------------------------------


def usd(value: float) -> str:
    if abs(value) >= 1000:
        return f"${value:,.0f}"
    if abs(value) >= 1:
        return f"${value:,.2f}"
    return f"${value:.4f}"


def tokens(value: float) -> str:
    for limit, suffix in ((1e9, "B"), (1e6, "M"), (1e3, "K")):
        if abs(value) >= limit:
            return f"{value / limit:.1f}{suffix}"
    return f"{value:.0f}"


VERDICT_LABEL = {
    "paying": "✅ paying",
    "marginal": "➖ marginal",
    "losing": "🔴 losing",
    "off": "⚪ off",
    "unpriced": "❓ unpriced",
}


def print_measured(report: Dict[str, Any], warnings: List[str]) -> None:
    print("=" * 78)
    print("🗄️  PROMPT CACHE ROI  (measured)")
    print("=" * 78)
    print()
    totals = report["totals"]
    print(f"   TTL assumed:      {report['ttl']}")
    print(f"   Break-even:       {report['breakeven_reads_per_write']:.2f} reads per write")
    print()
    print(f"   Without caching:  {usd(totals['without_cache_usd'])}")
    print(f"   With caching:     {usd(totals['with_cache_usd'])}")
    saved = totals["savings_usd"]
    label = "Net saved:" if saved >= 0 else "Net LOST:"
    print(f"   {label:<18}{usd(abs(saved))}", end="")
    if totals["without_cache_usd"]:
        print(f"  ({saved / totals['without_cache_usd'] * 100:+.1f}%)")
    else:
        print()

    print()
    print("─" * 78)
    print()
    print(f"   {'Feature / model':<34}{'Hit':>7}{'R/W':>7}{'Savings':>12}  Verdict")
    print("   " + "─" * 72)
    for row in report["rows"]:
        label = f"{row['feature']} · {row['model']}"[:33]
        if row["verdict"] == "unpriced":
            print(f"   {label:<34}{'—':>7}{'—':>7}{'—':>12}  {VERDICT_LABEL['unpriced']}")
            continue
        if not row["caching_on"]:
            print(f"   {label:<34}{'off':>7}{'—':>7}{'—':>12}  {VERDICT_LABEL['off']}")
            continue
        print(
            f"   {label:<34}{row['hit_rate'] * 100:>6.0f}%{row['reads_per_write']:>7.1f}"
            f"{usd(row['savings_usd']):>12}  {VERDICT_LABEL[row['verdict']]}"
        )

    losing = [r for r in report["rows"] if r["verdict"] == "losing"]
    if losing:
        print()
        print("   🔴 PAYING THE WRITE PREMIUM FOR NOTHING:")
        print()
        for row in losing:
            print(
                f"      {row['feature']} · {row['model']}: "
                f"{row['reads_per_write']:.1f} reads per write, below the "
                f"{report['breakeven_reads_per_write']:.2f} break-even."
            )
            print(
                f"        Costing {usd(-row['savings_usd'])} more than not caching. "
                f"Either raise reuse (longer TTL, fewer cache breakpoints) or "
                f"turn caching off here."
            )

    opportunities = report["opportunities"]
    if opportunities:
        print()
        print("   ⚪ CACHING OFF ON BILLABLE TRAFFIC:")
        print()
        for item in opportunities[:8]:
            line = (
                f"      {item['feature']} · {item['model']}: "
                f"{item['requests']:,.0f} requests, "
                f"{tokens(item['input_tokens'])} input tokens"
            )
            if "projected_savings_usd" in item:
                line += (
                    f"\n        ~{usd(item['projected_savings_usd'])} if a "
                    f"{item['assumed_prefix_tokens']:,}-token prefix were cached "
                    f"({item['projected_hit_rate'] * 100:.0f}% projected hit rate)"
                )
            if item.get("prefix_exceeds_avg_input"):
                line += (
                    f"\n        ⚠️  --prefix-tokens "
                    f"{item['assumed_prefix_tokens']:,} exceeds this feature's "
                    f"{item['avg_input_tokens']:,.0f}-token average request; "
                    f"capped at observed volume, so treat as an upper bound"
                )
            print(line)
        if not any("projected_savings_usd" in i for i in opportunities):
            print()
            print("      Re-run with --prefix-tokens N to size these.")

    if report["unpriced_models"]:
        print()
        print(f"   ❓ No price on file: {', '.join(report['unpriced_models'])}")

    for warning in warnings:
        print(f"\n   ⚠️  {warning}")
    print()


def print_projection(report: Dict[str, Any]) -> None:
    print("=" * 78)
    print("🗄️  PROMPT CACHE ROI  (projected)")
    print("=" * 78)
    print()
    print(f"   Model:            {report['model']}")
    print(f"   Cacheable prefix: {report['prefix_tokens']:,} tokens")
    print(f"   Traffic:          {report['requests_per_day']:,.0f} requests/day", end="")
    if report["concurrency"] > 1:
        print(f"  across {report['concurrency']} concurrent streams")
    else:
        print()
    print(f"   TTL:              {report['ttl']}")
    print()
    hit = report["predicted_hit_rate"]
    bar = int(round(hit * 30))
    print(f"   Predicted hit rate:  {hit * 100:.1f}%  [{'█' * bar}{'░' * (30 - bar)}]")
    print()
    daily = report["daily"]
    print(f"   Daily without cache: {usd(daily['without_cache_usd'])}")
    print(f"   Daily with cache:    {usd(daily['with_cache_usd'])}")
    print(
        f"   Daily savings:       {usd(daily['savings_usd'])} "
        f"({daily['savings_pct']:+.1f}%)"
    )
    print(f"   Monthly savings:     {usd(report['monthly_savings_usd'])}")

    print()
    print("─" * 78)
    print()
    breakeven = report["breakeven_requests_per_day"]
    if breakeven is None:
        print("   ⚠️  Caching never pays at this prefix size and concurrency.")
    elif breakeven <= report["requests_per_day"]:
        print(
            f"   ✅ Break-even at {breakeven:,.0f} requests/day — you are "
            f"{report['requests_per_day'] / breakeven:.1f}x above it."
        )
    else:
        print(
            f"   🔴 Break-even at {breakeven:,.0f} requests/day — "
            f"{breakeven / max(report['requests_per_day'], 1):.1f}x your current "
            f"traffic. Caching loses money until then."
        )
    print(
        f"      ({report['breakeven_reads_per_write']:.2f} reads per write at "
        f"the {report['ttl']} TTL.)"
    )

    print()
    print("   SENSITIVITY:")
    print()
    print(f"   {'Requests/day':>14}{'Hit rate':>11}{'Daily savings':>16}")
    print("   " + "─" * 41)
    for point in report["curve"]:
        marker = "  ←" if point["requests_per_day"] == report["requests_per_day"] else ""
        print(
            f"   {point['requests_per_day']:>14,.0f}{point['hit_rate'] * 100:>10.0f}%"
            f"{usd(point['daily_savings_usd']):>16}{marker}"
        )
    print()


def to_markdown(report: Dict[str, Any]) -> str:
    if report.get("mode") == "projection":
        daily = report["daily"]
        return "\n".join(
            [
                "# Prompt Cache ROI (projected)",
                "",
                f"- **Model:** {report['model']}",
                f"- **Prefix:** {report['prefix_tokens']:,} tokens",
                f"- **Traffic:** {report['requests_per_day']:,.0f} requests/day "
                f"({report['concurrency']} concurrent)",
                f"- **TTL:** {report['ttl']}",
                "",
                f"**Predicted hit rate:** {report['predicted_hit_rate'] * 100:.1f}%",
                "",
                f"Daily savings {usd(daily['savings_usd'])} "
                f"({daily['savings_pct']:+.1f}%); monthly "
                f"{usd(report['monthly_savings_usd'])}.",
                "",
                f"Break-even at "
                f"{report['breakeven_requests_per_day'] or float('nan'):,.0f} "
                f"requests/day.",
            ]
        ) + "\n"

    lines = [
        "# Prompt Cache ROI (measured)",
        "",
        f"Net {usd(report['totals']['savings_usd'])} versus not caching "
        f"({report['ttl']} TTL, break-even "
        f"{report['breakeven_reads_per_write']:.2f} reads/write).",
        "",
        "| Feature | Model | Hit rate | Reads/write | Savings | Verdict |",
        "|---|---|---:|---:|---:|---|",
    ]
    for row in report["rows"]:
        if row["verdict"] in ("unpriced", "off"):
            lines.append(
                f"| {row['feature']} | {row['model']} | — | — | — | "
                f"{row['verdict']} |"
            )
            continue
        lines.append(
            f"| {row['feature']} | {row['model']} | {row['hit_rate'] * 100:.0f}% | "
            f"{row['reads_per_write']:.1f} | {usd(row['savings_usd'])} | "
            f"{row['verdict']} |"
        )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Measure or project the ROI of prompt caching.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  prompt-cache-roi.py --csv usage.csv\n"
            "  prompt-cache-roi.py --prefix-tokens 4000 --requests-per-day 20000\n"
        ),
    )
    parser.add_argument("--csv", "-c", help="llm_usage CSV (measured mode)")
    parser.add_argument(
        "--prefix-tokens",
        type=int,
        help="Cacheable prefix size. Required for projection; optional with "
        "--csv to size the caching-off opportunities.",
    )
    parser.add_argument(
        "--requests-per-day", type=float, help="Traffic for projection mode"
    )
    parser.add_argument(
        "--other-input-tokens",
        type=int,
        default=0,
        help="Non-cacheable input tokens per request (default: 0)",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=1,
        help="Concurrent conversations, each holding its own cache entry "
        "(default: 1). Raising this lowers the hit rate.",
    )
    parser.add_argument(
        "--model", default="claude-sonnet-5", help="Model for projection mode"
    )
    parser.add_argument(
        "--ttl", default="5m", choices=["5m", "1h"], help="Cache TTL (default: 5m)"
    )
    parser.add_argument("--markdown", help="Write a Markdown report")
    parser.add_argument("--output", help="Write JSON results")
    args = parser.parse_args()

    if args.csv:
        grouped, warnings = load_usage(args.csv)
        report = analyze_measured(grouped, args.ttl, args.prefix_tokens)
        report["mode"] = "measured"
        print_measured(report, warnings)
    else:
        if not args.prefix_tokens or not args.requests_per_day:
            parser.error(
                "projection mode needs --prefix-tokens and --requests-per-day "
                "(or pass --csv for measured mode)"
            )
        warnings = []
        report = analyze_projection(
            args.model,
            args.prefix_tokens,
            args.requests_per_day,
            args.other_input_tokens,
            args.ttl,
            max(1, args.concurrency),
        )
        print_projection(report)

    if args.markdown:
        with open(args.markdown, "w", encoding="utf-8") as f:
            f.write(to_markdown(report))
        print(f"   📝 Markdown → {args.markdown}")
    if args.output:
        toolkit_io.write(args.output, report, TOOL, warnings=warnings or None)
        print(f"   💾 JSON → {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
