#!/usr/bin/env python3
"""
LLM Usage Summary

Report what you actually spent on inference, from a usage export.

Every other cost tool in this toolkit is an estimator: you tell
ai-unit-economics-calculator.py that a request averages 800 input tokens and it
projects a bill. Nothing read the real numbers back. So the assumptions were
never checked against production, and a prompt that quietly grew to 3,000
tokens showed up as a budget surprise rather than a metric.

This closes that loop. It summarizes actual spend by model, feature, and day,
and then prints the flags — measured, not guessed — to feed the estimators for
the next forecast.

It also re-derives cost from scripts/model_pricing.py and compares against what
the provider billed. A consistent gap is information: gateway markup, a
negotiated rate, batch discounts, or toolkit pricing that has gone stale.

Usage:
    python llm-usage-summary.py --csv usage.csv
    python llm-usage-summary.py --csv usage.csv --group-by feature
    python llm-usage-summary.py --csv usage.csv --days 30 --markdown report.md
    python llm-usage-summary.py --csv usage.csv --output summary.json

    # Produced by the gateway connector:
    python connectors/fetch.py gateway llm_usage --provider litellm --out usage.csv

CSV format (header row required):
    date,model,feature,requests,input_tokens,output_tokens,cached_input_tokens,cache_write_tokens,cost_usd
    2026-08-01,claude-sonnet-5,chat,12400,9920000,3100000,4200000,180000,48.21

    Required: date, model. Everything else defaults to 0.
    Header names are flexible: prompt_tokens, completion_tokens, cache_read_tokens,
    spend, and calls all resolve to the right column.

Requirements:
    None (stdlib only).
"""

import argparse
import json
import sys
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import csv_columns
import model_pricing
import toolkit_io

TOOL = "llm-usage-summary"

NUMERIC = (
    "requests",
    "input_tokens",
    "output_tokens",
    "cached_input_tokens",
    "cache_write_tokens",
    "reasoning_tokens",
    "cost_usd",
)


def parse_date(raw: str) -> Optional[datetime]:
    text = (raw or "").strip()
    if not text:
        return None
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y/%m/%d"):
        try:
            return datetime.strptime(text[: len(fmt) + 2].strip(), fmt)
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(text.replace("Z", ""))
    except ValueError:
        return None


def number(raw: Any) -> float:
    text = str(raw or "").strip().replace(",", "").replace("$", "")
    if not text:
        return 0.0
    try:
        return float(text)
    except ValueError:
        return 0.0


def load_rows(path: str, days: Optional[int]) -> Tuple[List[Dict[str, Any]], List[str]]:
    warnings: List[str] = []
    rows: List[Dict[str, Any]] = []
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv_columns.DictReader(f)
        fields = reader.fieldnames or []
        if not csv_columns.resolve(fields, "date", "day", "period", "timestamp"):
            raise SystemExit(
                f"Error: no date column found. CSV has: {', '.join(fields) or '(empty)'}"
            )
        if not csv_columns.resolve(fields, "model", "model_name", "model_id"):
            raise SystemExit(
                f"Error: no model column found. CSV has: {', '.join(fields) or '(empty)'}"
            )
        for raw in reader:
            when = parse_date(raw.first("date", "day", "period", "timestamp", default=""))
            model = str(raw.first("model", "model_name", "model_id", default="")).strip()
            if not when or not model:
                continue
            row: Dict[str, Any] = {
                "date": when,
                "model": model,
                "feature": str(
                    raw.first("feature", "tag", "app", "project", "team", default="")
                ).strip()
                or "—",
                "provider": str(raw.first("provider", "vendor", default="")).strip(),
            }
            for key in NUMERIC:
                row[key] = number(raw.get(key, 0))
            # A gateway that reports only totals still gives a usable summary;
            # treating a missing request count as zero would make every
            # per-request number infinite instead.
            rows.append(row)

    if not rows:
        raise SystemExit("Error: no usable rows (need a parseable date and a model).")

    if days:
        latest = max(r["date"] for r in rows)
        cutoff = latest - timedelta(days=days)
        kept = [r for r in rows if r["date"] > cutoff]
        if len(kept) < len(rows):
            warnings.append(
                f"--days {days}: kept {len(kept)} of {len(rows)} rows "
                f"(since {cutoff.date()})"
            )
        rows = kept or rows
    return rows, warnings


def aggregate(rows: List[Dict[str, Any]], key: str) -> Dict[str, Dict[str, float]]:
    out: Dict[str, Dict[str, float]] = defaultdict(
        lambda: {k: 0.0 for k in NUMERIC}
    )
    for row in rows:
        bucket = out[row[key]]
        for field in NUMERIC:
            bucket[field] += row[field]
    return dict(out)


def rederive_cost(
    by_model: Dict[str, Dict[str, float]]
) -> Tuple[Dict[str, Optional[float]], List[str]]:
    """Price each model's tokens with the toolkit's own table.

    Unknown models come back as None rather than 0 — a model this toolkit has
    no price for must not silently contribute nothing to the comparison and
    make the gap look smaller than it is.
    """
    derived: Dict[str, Optional[float]] = {}
    notes: List[str] = []
    for model, totals in by_model.items():
        try:
            result = model_pricing.cost(
                model,
                input_tokens=totals["input_tokens"],
                output_tokens=totals["output_tokens"],
                cached_input_tokens=totals["cached_input_tokens"],
                cache_write_tokens=totals["cache_write_tokens"],
            )
            derived[model] = result["total_cost"]
        except Exception as exc:  # unknown model, or no price on file
            derived[model] = None
            notes.append(f"{model}: {exc}")
    return derived, notes


def fmt_usd(value: float) -> str:
    if value >= 1000:
        return f"${value:,.0f}"
    if value >= 1:
        return f"${value:,.2f}"
    return f"${value:.4f}"


def fmt_tokens(value: float) -> str:
    for limit, suffix in ((1e9, "B"), (1e6, "M"), (1e3, "K")):
        if value >= limit:
            return f"{value / limit:.1f}{suffix}"
    return f"{value:.0f}"


def build_report(rows: List[Dict[str, Any]], group_by: str) -> Dict[str, Any]:
    totals = {k: sum(r[k] for r in rows) for k in NUMERIC}
    dates = sorted({r["date"].date() for r in rows})
    span_days = max(1, (dates[-1] - dates[0]).days + 1)

    by_model = aggregate(rows, "model")
    by_group = aggregate(rows, group_by)
    derived, price_notes = rederive_cost(by_model)

    billed_known = sum(
        by_model[m]["cost_usd"] for m, v in derived.items() if v is not None
    )
    derived_known = sum(v for v in derived.values() if v is not None)

    total_in = totals["input_tokens"] + totals["cached_input_tokens"]
    reqs = totals["requests"]

    daily: Dict[str, Dict[str, float]] = defaultdict(
        lambda: {k: 0.0 for k in NUMERIC}
    )
    for row in rows:
        bucket = daily[row["date"].date().isoformat()]
        for field in NUMERIC:
            bucket[field] += row[field]

    return {
        "period": {
            "start": dates[0].isoformat(),
            "end": dates[-1].isoformat(),
            "days": span_days,
        },
        "totals": totals,
        "per_request": {
            "input_tokens": (total_in / reqs) if reqs else None,
            "output_tokens": (totals["output_tokens"] / reqs) if reqs else None,
            "cost_usd": (totals["cost_usd"] / reqs) if reqs else None,
        },
        "run_rate": {
            "daily_usd": totals["cost_usd"] / span_days,
            "monthly_usd": totals["cost_usd"] / span_days * 30,
            "requests_per_month": (reqs / span_days * 30) if reqs else None,
        },
        "cache": {
            "cached_input_tokens": totals["cached_input_tokens"],
            "cache_write_tokens": totals["cache_write_tokens"],
            "hit_rate": (totals["cached_input_tokens"] / total_in) if total_in else None,
        },
        "by_model": by_model,
        "by_group": by_group,
        "group_by": group_by,
        "daily": dict(sorted(daily.items())),
        "cost_check": {
            "billed_usd": billed_known,
            "derived_usd": derived_known,
            "delta_usd": billed_known - derived_known,
            "delta_pct": (
                (billed_known - derived_known) / derived_known * 100
                if derived_known
                else None
            ),
            "unpriced_models": [m for m, v in derived.items() if v is None],
            "notes": price_notes,
        },
    }


def print_report(report: Dict[str, Any], warnings: List[str]) -> None:
    totals = report["totals"]
    period = report["period"]
    group_by = report["group_by"]

    print("=" * 78)
    print("💸 LLM USAGE SUMMARY")
    print("=" * 78)
    print()
    print(f"   Period:        {period['start']} → {period['end']}  ({period['days']}d)")
    print(f"   Total spend:   {fmt_usd(totals['cost_usd'])}")
    if totals["requests"]:
        print(f"   Requests:      {totals['requests']:,.0f}")
    print(
        f"   Tokens:        {fmt_tokens(totals['input_tokens'])} in  /  "
        f"{fmt_tokens(totals['output_tokens'])} out"
        + (
            f"  /  {fmt_tokens(totals['cached_input_tokens'])} cached"
            if totals["cached_input_tokens"]
            else ""
        )
    )
    rate = report["run_rate"]
    print(
        f"   Run rate:      {fmt_usd(rate['daily_usd'])}/day  →  "
        f"{fmt_usd(rate['monthly_usd'])}/month"
    )

    print()
    print("─" * 78)
    print()
    print("   BY MODEL:")
    print()
    print(f"   {'Model':<30}{'Spend':>12}{'Share':>8}{'Reqs':>10}{'$/req':>11}")
    print("   " + "─" * 71)
    total_cost = totals["cost_usd"] or 1
    for model, vals in sorted(
        report["by_model"].items(), key=lambda kv: -kv[1]["cost_usd"]
    ):
        share = vals["cost_usd"] / total_cost * 100
        per_req = fmt_usd(vals["cost_usd"] / vals["requests"]) if vals["requests"] else "—"
        print(
            f"   {model[:29]:<30}{fmt_usd(vals['cost_usd']):>12}{share:>7.1f}%"
            f"{vals['requests']:>10,.0f}{per_req:>11}"
        )

    if len(report["by_group"]) > 1 or group_by != "feature":
        print()
        print(f"   BY {group_by.upper()}:")
        print()
        print(f"   {group_by.title():<30}{'Spend':>12}{'Share':>8}{'Reqs':>10}")
        print("   " + "─" * 60)
        for name, vals in sorted(
            report["by_group"].items(), key=lambda kv: -kv[1]["cost_usd"]
        ):
            share = vals["cost_usd"] / total_cost * 100
            print(
                f"   {str(name)[:29]:<30}{fmt_usd(vals['cost_usd']):>12}"
                f"{share:>7.1f}%{vals['requests']:>10,.0f}"
            )

    cache = report["cache"]
    if cache["hit_rate"] is not None:
        print()
        print("─" * 78)
        print()
        bar = int(round(cache["hit_rate"] * 30))
        print(
            f"   CACHE:  hit rate {cache['hit_rate'] * 100:.1f}%  "
            f"[{'█' * bar}{'░' * (30 - bar)}]"
        )
        print(
            f"           {fmt_tokens(cache['cached_input_tokens'])} read  /  "
            f"{fmt_tokens(cache['cache_write_tokens'])} written"
        )

    check = report["cost_check"]
    if check["delta_pct"] is not None:
        print()
        print("─" * 78)
        print()
        print("   BILLED vs MODEL_PRICING:")
        print(f"      Billed:   {fmt_usd(check['billed_usd'])}")
        print(f"      Derived:  {fmt_usd(check['derived_usd'])}")
        delta = check["delta_pct"]
        marker = "✅" if abs(delta) < 5 else ("⚠️ " if abs(delta) < 25 else "🔴")
        print(
            f"      Delta:    {fmt_usd(check['delta_usd'])}  ({delta:+.1f}%)  {marker}"
        )
        if abs(delta) >= 5:
            print(
                "      A persistent gap usually means gateway markup, a negotiated\n"
                "      rate, batch discounts, or stale pricing in model_pricing.py."
            )
    if check["unpriced_models"]:
        print(
            f"      Not priced: {', '.join(check['unpriced_models'])} "
            f"(excluded from both sides)"
        )

    per_req = report["per_request"]
    if per_req["input_tokens"]:
        print()
        print("─" * 78)
        print()
        print("   MEASURED INPUTS FOR THE ESTIMATORS:")
        print()
        # Highest spend among models model_pricing knows: recommending the
        # top spender is useless if the estimator can't price it, which is
        # exactly what happens on a model newer than the pricing table.
        unpriced = set(report["cost_check"]["unpriced_models"])
        ranked = sorted(report["by_model"].items(), key=lambda kv: -kv[1]["cost_usd"])
        priced = [m for m, _ in ranked if m not in unpriced]
        top_model = priced[0] if priced else ranked[0][0]
        if ranked and ranked[0][0] in unpriced:
            print(
                f"      (Top spender {ranked[0][0]} has no entry in model_pricing.py,\n"
                f"       so this uses {top_model} instead.)\n"
            )
        print(
            f"      python ai-unit-economics-calculator.py \\\n"
            f"          --model {top_model} \\\n"
            f"          --input-tokens {per_req['input_tokens']:.0f} \\\n"
            f"          --output-tokens {per_req['output_tokens']:.0f} \\\n"
            f"          --requests-per-month {report['run_rate']['requests_per_month']:.0f}"
        )
        print()
        print("      Those are measured from this file, not assumed.")

    for warning in warnings:
        print(f"\n   ⚠️  {warning}")
    print()


def to_markdown(report: Dict[str, Any]) -> str:
    totals = report["totals"]
    lines = [
        "# LLM Usage Summary",
        "",
        f"**Period:** {report['period']['start']} → {report['period']['end']} "
        f"({report['period']['days']} days)",
        "",
        f"- **Total spend:** {fmt_usd(totals['cost_usd'])}",
        f"- **Run rate:** {fmt_usd(report['run_rate']['monthly_usd'])}/month",
        f"- **Requests:** {totals['requests']:,.0f}",
        f"- **Tokens:** {fmt_tokens(totals['input_tokens'])} in / "
        f"{fmt_tokens(totals['output_tokens'])} out",
        "",
        "## By model",
        "",
        "| Model | Spend | Share | Requests |",
        "|---|---:|---:|---:|",
    ]
    total_cost = totals["cost_usd"] or 1
    for model, vals in sorted(
        report["by_model"].items(), key=lambda kv: -kv[1]["cost_usd"]
    ):
        lines.append(
            f"| {model} | {fmt_usd(vals['cost_usd'])} | "
            f"{vals['cost_usd'] / total_cost * 100:.1f}% | {vals['requests']:,.0f} |"
        )
    check = report["cost_check"]
    if check["delta_pct"] is not None:
        lines += [
            "",
            "## Billed vs model_pricing",
            "",
            f"Billed {fmt_usd(check['billed_usd'])} against a derived "
            f"{fmt_usd(check['derived_usd'])} — a delta of "
            f"{fmt_usd(check['delta_usd'])} ({check['delta_pct']:+.1f}%).",
        ]
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Summarize actual LLM spend and token usage from a usage export.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Example: llm-usage-summary.py --csv usage.csv --group-by feature",
    )
    parser.add_argument("--csv", "-c", required=True, help="Usage CSV")
    parser.add_argument(
        "--group-by",
        default="feature",
        choices=["feature", "provider", "model"],
        help="Second breakdown dimension (default: feature)",
    )
    parser.add_argument("--days", type=int, help="Only the last N days of the file")
    parser.add_argument("--markdown", help="Write a Markdown report")
    parser.add_argument("--output", help="Write JSON results")
    args = parser.parse_args()

    rows, warnings = load_rows(args.csv, args.days)
    report = build_report(rows, args.group_by)
    print_report(report, warnings)

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
