#!/usr/bin/env python3
"""
Model Migration Cost Estimator

Estimate the total cost of switching from one LLM to another: token cost delta,
latency impact, prompt rewriting effort, re-evaluation effort, and transition
risk. Helps PMs make informed build/switch decisions.

Produces a side-by-side comparison and a migration cost summary covering both
ongoing savings/costs and one-time migration investment.

Usage:
    python model-migration-estimator.py \\
        --from claude-3-opus --to claude-3-5-sonnet \\
        --monthly-requests 100000 --avg-input-tokens 800 --avg-output-tokens 400

    python model-migration-estimator.py \\
        --from gpt-4-turbo --to gpt-4o \\
        --monthly-requests 500000 --avg-input-tokens 1200 --avg-output-tokens 600 \\
        --prompts 15 --eval-cases 200 --output report.json

    python model-migration-estimator.py --list-models

Requirements:
    None (stdlib only).
"""

import argparse
import json
import sys
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Model catalog — USD per 1M tokens (input, output), avg latency ms/1K tokens
# Verify at provider pricing pages. Latencies are rough estimates for planning.
# ---------------------------------------------------------------------------

MODEL_CATALOG: Dict[str, Dict[str, Any]] = {
    # Anthropic
    "claude-3-opus": {
        "provider": "Anthropic",
        "input_per_m": 15.00,
        "output_per_m": 75.00,
        "latency_ms_per_1k": 60,
        "context_window": 200000,
    },
    "claude-3-5-sonnet": {
        "provider": "Anthropic",
        "input_per_m": 3.00,
        "output_per_m": 15.00,
        "latency_ms_per_1k": 35,
        "context_window": 200000,
    },
    "claude-3-5-haiku": {
        "provider": "Anthropic",
        "input_per_m": 0.80,
        "output_per_m": 4.00,
        "latency_ms_per_1k": 15,
        "context_window": 200000,
    },
    "claude-3-haiku": {
        "provider": "Anthropic",
        "input_per_m": 0.25,
        "output_per_m": 1.25,
        "latency_ms_per_1k": 12,
        "context_window": 200000,
    },
    # OpenAI
    "gpt-4o": {
        "provider": "OpenAI",
        "input_per_m": 2.50,
        "output_per_m": 10.00,
        "latency_ms_per_1k": 30,
        "context_window": 128000,
    },
    "gpt-4o-mini": {
        "provider": "OpenAI",
        "input_per_m": 0.15,
        "output_per_m": 0.60,
        "latency_ms_per_1k": 12,
        "context_window": 128000,
    },
    "gpt-4-turbo": {
        "provider": "OpenAI",
        "input_per_m": 10.00,
        "output_per_m": 30.00,
        "latency_ms_per_1k": 40,
        "context_window": 128000,
    },
    "gpt-4": {
        "provider": "OpenAI",
        "input_per_m": 30.00,
        "output_per_m": 60.00,
        "latency_ms_per_1k": 50,
        "context_window": 8192,
    },
    "gpt-3.5-turbo": {
        "provider": "OpenAI",
        "input_per_m": 0.50,
        "output_per_m": 1.50,
        "latency_ms_per_1k": 10,
        "context_window": 16385,
    },
    # AWS Bedrock
    "bedrock.claude-3-5-sonnet": {
        "provider": "AWS Bedrock",
        "input_per_m": 3.00,
        "output_per_m": 15.00,
        "latency_ms_per_1k": 40,
        "context_window": 200000,
    },
    "bedrock.claude-3-haiku": {
        "provider": "AWS Bedrock",
        "input_per_m": 0.25,
        "output_per_m": 1.25,
        "latency_ms_per_1k": 15,
        "context_window": 200000,
    },
    "bedrock.titan-text-express": {
        "provider": "AWS Bedrock",
        "input_per_m": 0.80,
        "output_per_m": 3.20,
        "latency_ms_per_1k": 20,
        "context_window": 8192,
    },
    "bedrock.mistral-large": {
        "provider": "AWS Bedrock",
        "input_per_m": 4.00,
        "output_per_m": 12.00,
        "latency_ms_per_1k": 35,
        "context_window": 32768,
    },
    # Google
    "gemini-1.5-pro": {
        "provider": "Google",
        "input_per_m": 1.25,
        "output_per_m": 5.00,
        "latency_ms_per_1k": 30,
        "context_window": 2000000,
    },
    "gemini-1.5-flash": {
        "provider": "Google",
        "input_per_m": 0.075,
        "output_per_m": 0.30,
        "latency_ms_per_1k": 10,
        "context_window": 1000000,
    },
}


# ---------------------------------------------------------------------------
# Cost calculations
# ---------------------------------------------------------------------------

def monthly_token_cost(
    model: Dict[str, Any],
    monthly_requests: int,
    avg_input_tokens: int,
    avg_output_tokens: int,
) -> Dict[str, float]:
    """Calculate monthly API cost for a model."""
    total_input = monthly_requests * avg_input_tokens
    total_output = monthly_requests * avg_output_tokens

    input_cost = (total_input / 1_000_000) * model["input_per_m"]
    output_cost = (total_output / 1_000_000) * model["output_per_m"]
    total = input_cost + output_cost

    return {
        "total_input_tokens": total_input,
        "total_output_tokens": total_output,
        "input_cost": round(input_cost, 2),
        "output_cost": round(output_cost, 2),
        "total_monthly": round(total, 2),
        "cost_per_request": round(total / monthly_requests, 6) if monthly_requests > 0 else 0,
    }


def latency_estimate(
    model: Dict[str, Any],
    avg_input_tokens: int,
    avg_output_tokens: int,
) -> Dict[str, float]:
    """Estimate per-request latency."""
    total_tokens = avg_input_tokens + avg_output_tokens
    est_ms = (total_tokens / 1000) * model["latency_ms_per_1k"]
    return {
        "estimated_ms": round(est_ms, 0),
        "estimated_seconds": round(est_ms / 1000, 2),
    }


def migration_effort(
    n_prompts: int,
    hours_per_prompt: float,
    n_eval_cases: int,
    hours_per_eval_run: float,
    eng_hourly_rate: float,
    cross_provider: bool,
) -> Dict[str, Any]:
    """Estimate one-time migration effort and cost."""
    # Prompt rewriting
    prompt_hours = n_prompts * hours_per_prompt
    prompt_cost = prompt_hours * eng_hourly_rate

    # Evaluation runs (assume 2 full runs: baseline + validation)
    eval_hours = 2 * hours_per_eval_run
    eval_cost = eval_hours * eng_hourly_rate

    # Integration work (API changes, SDK updates, error handling)
    if cross_provider:
        integration_hours = max(8, n_prompts * 0.5)  # SDK swap, auth, error handling
    else:
        integration_hours = max(2, n_prompts * 0.2)  # Same provider, just model string
    integration_cost = integration_hours * eng_hourly_rate

    # Testing & QA
    qa_hours = max(4, n_prompts * 0.3)
    qa_cost = qa_hours * eng_hourly_rate

    total_hours = prompt_hours + eval_hours + integration_hours + qa_hours
    total_cost = prompt_cost + eval_cost + integration_cost + qa_cost

    return {
        "prompt_rewriting": {"hours": round(prompt_hours, 1), "cost": round(prompt_cost, 2)},
        "evaluation": {"hours": round(eval_hours, 1), "cost": round(eval_cost, 2)},
        "integration": {"hours": round(integration_hours, 1), "cost": round(integration_cost, 2)},
        "qa_testing": {"hours": round(qa_hours, 1), "cost": round(qa_cost, 2)},
        "total_hours": round(total_hours, 1),
        "total_cost": round(total_cost, 2),
        "total_days": round(total_hours / 8, 1),
    }


def payback_months(monthly_savings: float, migration_cost: float) -> Optional[float]:
    """Months until migration cost is recouped from monthly savings."""
    if monthly_savings <= 0:
        return None
    return migration_cost / monthly_savings


# ---------------------------------------------------------------------------
# Risk assessment
# ---------------------------------------------------------------------------

def assess_risk(
    from_model: Dict[str, Any],
    to_model: Dict[str, Any],
    from_name: str,
    to_name: str,
    cross_provider: bool,
) -> List[Dict[str, str]]:
    """Flag migration risks."""
    risks: List[Dict[str, str]] = []

    # Context window regression
    if to_model["context_window"] < from_model["context_window"]:
        ratio = to_model["context_window"] / from_model["context_window"]
        risks.append({
            "severity": "HIGH" if ratio < 0.5 else "MEDIUM",
            "risk": f"Context window shrinks from {from_model['context_window']:,} → {to_model['context_window']:,} tokens",
            "mitigation": "Check max input sizes in production; may need chunking strategy",
        })

    # Cross-provider
    if cross_provider:
        risks.append({
            "severity": "MEDIUM",
            "risk": f"Cross-provider migration ({from_model['provider']} → {to_model['provider']})",
            "mitigation": "SDK change, different auth, different error codes, different rate limits",
        })

    # Capability downgrade (higher-tier to lower-tier based on price)
    from_cost = from_model["input_per_m"] + from_model["output_per_m"]
    to_cost = to_model["input_per_m"] + to_model["output_per_m"]
    if to_cost < from_cost * 0.3:
        risks.append({
            "severity": "HIGH",
            "risk": "Significant capability downgrade likely (>70% cost reduction)",
            "mitigation": "Run thorough eval suite; expect quality regression on complex tasks",
        })
    elif to_cost < from_cost * 0.6:
        risks.append({
            "severity": "MEDIUM",
            "risk": "Possible capability change (40-70% cost reduction)",
            "mitigation": "Run eval suite; monitor quality metrics post-migration",
        })

    # Latency change
    from_lat = from_model["latency_ms_per_1k"]
    to_lat = to_model["latency_ms_per_1k"]
    if to_lat > from_lat * 1.5:
        risks.append({
            "severity": "MEDIUM",
            "risk": f"Latency increase (~{to_lat - from_lat:.0f}ms/1K tokens)",
            "mitigation": "Check SLAs; consider streaming or async patterns",
        })

    if not risks:
        risks.append({
            "severity": "LOW",
            "risk": "No major risks identified",
            "mitigation": "Standard eval and testing should suffice",
        })

    return risks


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def _fmt_usd(amount: float) -> str:
    if amount >= 1000:
        return f"${amount:,.2f}"
    elif amount >= 1:
        return f"${amount:.2f}"
    else:
        return f"${amount:.4f}"


def print_report(
    from_name: str,
    to_name: str,
    from_model: Dict[str, Any],
    to_model: Dict[str, Any],
    from_cost: Dict[str, float],
    to_cost: Dict[str, float],
    from_latency: Dict[str, float],
    to_latency: Dict[str, float],
    effort: Dict[str, Any],
    risks: List[Dict[str, str]],
    monthly_requests: int,
    avg_input_tokens: int,
    avg_output_tokens: int,
) -> None:
    """Pretty-print migration analysis."""
    monthly_delta = to_cost["total_monthly"] - from_cost["total_monthly"]
    monthly_savings = -monthly_delta  # positive = saving money
    annual_delta = monthly_delta * 12
    annual_savings = -annual_delta
    pct_change = (monthly_delta / from_cost["total_monthly"] * 100) if from_cost["total_monthly"] > 0 else 0

    pb = payback_months(monthly_savings, effort["total_cost"])

    print("\n" + "=" * 78)
    print("📊 MODEL MIGRATION COST ESTIMATOR")
    print("=" * 78)

    print(f"\n📋 MIGRATION: {from_name} → {to_name}")
    print(f"   {from_model['provider']} → {to_model['provider']}")

    # Traffic profile
    print(f"\n📈 TRAFFIC PROFILE:")
    print(f"   • Monthly requests:   {monthly_requests:,}")
    print(f"   • Avg input tokens:   {avg_input_tokens:,}")
    print(f"   • Avg output tokens:  {avg_output_tokens:,}")
    print(f"   • Monthly tokens:     {from_cost['total_input_tokens'] + from_cost['total_output_tokens']:,}")

    # Side-by-side cost comparison
    print(f"\n💰 MONTHLY COST COMPARISON:")
    print(f"   {'':28} {'Current':>14} {'Target':>14} {'Delta':>14}")
    print(f"   {'':28} {from_name:>14} {to_name:>14}")
    print(f"   {'─'*28} {'─'*14} {'─'*14} {'─'*14}")
    print(f"   {'Input cost ($/1M tokens)':28} {_fmt_usd(from_model['input_per_m']):>14} {_fmt_usd(to_model['input_per_m']):>14}")
    print(f"   {'Output cost ($/1M tokens)':28} {_fmt_usd(from_model['output_per_m']):>14} {_fmt_usd(to_model['output_per_m']):>14}")
    print(f"   {'Monthly input cost':28} {_fmt_usd(from_cost['input_cost']):>14} {_fmt_usd(to_cost['input_cost']):>14} {_fmt_usd(to_cost['input_cost'] - from_cost['input_cost']):>14}")
    print(f"   {'Monthly output cost':28} {_fmt_usd(from_cost['output_cost']):>14} {_fmt_usd(to_cost['output_cost']):>14} {_fmt_usd(to_cost['output_cost'] - from_cost['output_cost']):>14}")
    print(f"   {'─'*28} {'─'*14} {'─'*14} {'─'*14}")
    print(f"   {'MONTHLY TOTAL':28} {_fmt_usd(from_cost['total_monthly']):>14} {_fmt_usd(to_cost['total_monthly']):>14} {_fmt_usd(monthly_delta):>14}")
    print(f"   {'ANNUAL TOTAL':28} {_fmt_usd(from_cost['total_monthly'] * 12):>14} {_fmt_usd(to_cost['total_monthly'] * 12):>14} {_fmt_usd(annual_delta):>14}")
    print(f"   {'Cost per request':28} {_fmt_usd(from_cost['cost_per_request']):>14} {_fmt_usd(to_cost['cost_per_request']):>14}")

    if monthly_savings > 0:
        print(f"\n   ✅ Migration SAVES {_fmt_usd(monthly_savings)}/month ({abs(pct_change):.0f}% reduction)")
        print(f"      Annual savings: {_fmt_usd(annual_savings)}")
    elif monthly_savings < 0:
        print(f"\n   ⚠️  Migration COSTS {_fmt_usd(-monthly_savings)}/month MORE ({abs(pct_change):.0f}% increase)")
        print(f"      Annual increase: {_fmt_usd(-annual_savings)}")
    else:
        print(f"\n   ➡️  No cost difference")

    # Latency comparison
    print(f"\n⚡ LATENCY ESTIMATE (per request):")
    lat_delta = to_latency["estimated_ms"] - from_latency["estimated_ms"]
    lat_pct = (lat_delta / from_latency["estimated_ms"] * 100) if from_latency["estimated_ms"] > 0 else 0
    print(f"   • Current ({from_name}):  ~{from_latency['estimated_ms']:.0f}ms ({from_latency['estimated_seconds']:.1f}s)")
    print(f"   • Target ({to_name}):   ~{to_latency['estimated_ms']:.0f}ms ({to_latency['estimated_seconds']:.1f}s)")
    if lat_delta < 0:
        print(f"   • ✅ {abs(lat_delta):.0f}ms faster ({abs(lat_pct):.0f}% improvement)")
    elif lat_delta > 0:
        print(f"   • ⚠️  {lat_delta:.0f}ms slower ({lat_pct:.0f}% regression)")
    else:
        print(f"   • ➡️  Similar latency")

    # Context window
    print(f"\n📐 CONTEXT WINDOW:")
    print(f"   • Current: {from_model['context_window']:,} tokens")
    print(f"   • Target:  {to_model['context_window']:,} tokens")

    # Migration effort
    print(f"\n🔧 ONE-TIME MIGRATION EFFORT:")
    print(f"   {'Task':<24} {'Hours':>8} {'Cost':>12}")
    print(f"   {'─'*24} {'─'*8} {'─'*12}")
    print(f"   {'Prompt rewriting':<24} {effort['prompt_rewriting']['hours']:>7.1f}h {_fmt_usd(effort['prompt_rewriting']['cost']):>12}")
    print(f"   {'Evaluation runs':<24} {effort['evaluation']['hours']:>7.1f}h {_fmt_usd(effort['evaluation']['cost']):>12}")
    print(f"   {'Integration / SDK':<24} {effort['integration']['hours']:>7.1f}h {_fmt_usd(effort['integration']['cost']):>12}")
    print(f"   {'QA & testing':<24} {effort['qa_testing']['hours']:>7.1f}h {_fmt_usd(effort['qa_testing']['cost']):>12}")
    print(f"   {'─'*24} {'─'*8} {'─'*12}")
    print(f"   {'TOTAL':<24} {effort['total_hours']:>7.1f}h {_fmt_usd(effort['total_cost']):>12}")
    print(f"   {'':24} (~{effort['total_days']:.0f} dev-days)")

    # Payback
    print(f"\n⏱️  PAYBACK:")
    if monthly_savings > 0 and pb is not None:
        print(f"   • Migration cost:      {_fmt_usd(effort['total_cost'])}")
        print(f"   • Monthly savings:     {_fmt_usd(monthly_savings)}")
        print(f"   • Payback period:      ~{pb:.1f} months")
        if pb <= 3:
            print(f"   • ✅ Fast payback — strong case for migration")
        elif pb <= 12:
            print(f"   • 🟡 Moderate payback — worth doing if quality holds")
        else:
            print(f"   • ⚠️  Long payback — reconsider unless quality improvement justifies it")
    elif monthly_savings <= 0:
        print(f"   • No cost savings. Migration only justified by quality/latency improvement.")
    else:
        print(f"   • Unable to calculate payback.")

    # Risks
    print(f"\n⚠️  RISK ASSESSMENT:")
    for risk in risks:
        severity_icon = {"HIGH": "🔴", "MEDIUM": "🟡", "LOW": "🟢"}.get(risk["severity"], "⚪")
        print(f"   {severity_icon} [{risk['severity']}] {risk['risk']}")
        print(f"      → {risk['mitigation']}")

    # Decision summary
    print(f"\n📋 DECISION SUMMARY:")
    pros: List[str] = []
    cons: List[str] = []
    if monthly_savings > 0:
        pros.append(f"Saves {_fmt_usd(annual_savings)}/year")
    elif monthly_savings < 0:
        cons.append(f"Costs {_fmt_usd(-annual_savings)}/year more")
    if lat_delta < 0:
        pros.append(f"{abs(lat_delta):.0f}ms faster per request")
    elif lat_delta > 0:
        cons.append(f"{lat_delta:.0f}ms slower per request")
    if to_model["context_window"] > from_model["context_window"]:
        pros.append("Larger context window")
    elif to_model["context_window"] < from_model["context_window"]:
        cons.append("Smaller context window")

    high_risks = sum(1 for r in risks if r["severity"] == "HIGH")
    if high_risks:
        cons.append(f"{high_risks} high-severity risk(s)")

    if pros:
        print(f"   ✅ Pros: {'; '.join(pros)}")
    if cons:
        print(f"   ❌ Cons: {'; '.join(cons)}")

    print("\n" + "=" * 78)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def resolve_model(name: str) -> Optional[str]:
    """Resolve model name with fuzzy matching."""
    lower = name.lower().strip()
    if lower in MODEL_CATALOG:
        return lower
    # Try partial match
    for key in MODEL_CATALOG:
        if lower in key or key.endswith(lower):
            return key
    # Try without provider prefix
    for key in MODEL_CATALOG:
        if key.split(".")[-1] == lower:
            return key
    return None


def main():
    parser = argparse.ArgumentParser(
        description="Estimate total cost of migrating from one LLM to another: "
                    "token cost delta, latency impact, prompt rewriting, re-evaluation, and risk.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --from claude-3-opus --to claude-3-5-sonnet \\
           --monthly-requests 100000 --avg-input-tokens 800 --avg-output-tokens 400

  %(prog)s --from gpt-4-turbo --to gpt-4o \\
           --monthly-requests 500000 --avg-input-tokens 1200 --avg-output-tokens 600 \\
           --prompts 15 --eval-cases 200

  %(prog)s --list-models
        """,
    )
    parser.add_argument("--from", dest="from_model", type=str, help="Current model name")
    parser.add_argument("--to", dest="to_model", type=str, help="Target model name")
    parser.add_argument("--monthly-requests", "-r", type=int, default=100000, help="Monthly request volume (default: 100000)")
    parser.add_argument("--avg-input-tokens", "-i", type=int, default=500, help="Average input tokens per request (default: 500)")
    parser.add_argument("--avg-output-tokens", "-o", type=int, default=300, help="Average output tokens per request (default: 300)")
    parser.add_argument("--prompts", "-p", type=int, default=5, help="Number of distinct prompts to rewrite (default: 5)")
    parser.add_argument("--hours-per-prompt", type=float, default=2.0, help="Hours to rewrite + test each prompt (default: 2.0)")
    parser.add_argument("--eval-cases", type=int, default=100, help="Number of eval test cases (default: 100)")
    parser.add_argument("--hours-per-eval", type=float, default=4.0, help="Hours per full eval run (default: 4.0)")
    parser.add_argument("--eng-rate", type=float, default=100.0, help="Engineering hourly rate in USD (default: 100)")
    parser.add_argument("--list-models", action="store_true", help="List known models and exit")
    parser.add_argument("--output", type=str, help="Write report to JSON file")
    args = parser.parse_args()

    if args.list_models:
        print("\n📋 KNOWN MODELS (USD per 1M tokens: input / output)\n")
        current_provider = ""
        for name, info in sorted(MODEL_CATALOG.items(), key=lambda x: (x[1]["provider"], x[1]["input_per_m"])):
            if info["provider"] != current_provider:
                current_provider = info["provider"]
                print(f"\n  {current_provider}:")
            ctx = f"{info['context_window']:,}".rjust(10)
            print(f"    {name:<28}  in: ${info['input_per_m']:<8.2f}  out: ${info['output_per_m']:<8.2f}  ctx: {ctx}  ~{info['latency_ms_per_1k']}ms/1K tok")
        print("\n  Verify current pricing at provider pricing pages.")
        print()
        return 0

    if not args.from_model or not args.to_model:
        print("Error: --from and --to are required.", file=sys.stderr)
        parser.print_help(sys.stderr)
        return 1

    from_key = resolve_model(args.from_model)
    to_key = resolve_model(args.to_model)

    if not from_key:
        print(f"Error: unknown model '{args.from_model}'. Use --list-models to see available models.", file=sys.stderr)
        return 1
    if not to_key:
        print(f"Error: unknown model '{args.to_model}'. Use --list-models to see available models.", file=sys.stderr)
        return 1

    from_info = MODEL_CATALOG[from_key]
    to_info = MODEL_CATALOG[to_key]
    cross_provider = from_info["provider"] != to_info["provider"]

    # Calculate costs
    from_cost = monthly_token_cost(from_info, args.monthly_requests, args.avg_input_tokens, args.avg_output_tokens)
    to_cost_data = monthly_token_cost(to_info, args.monthly_requests, args.avg_input_tokens, args.avg_output_tokens)

    # Latency
    from_latency = latency_estimate(from_info, args.avg_input_tokens, args.avg_output_tokens)
    to_latency = latency_estimate(to_info, args.avg_input_tokens, args.avg_output_tokens)

    # Migration effort
    effort = migration_effort(
        n_prompts=args.prompts,
        hours_per_prompt=args.hours_per_prompt,
        n_eval_cases=args.eval_cases,
        hours_per_eval_run=args.hours_per_eval,
        eng_hourly_rate=args.eng_rate,
        cross_provider=cross_provider,
    )

    # Risks
    risks = assess_risk(from_info, to_info, from_key, to_key, cross_provider)

    # Print report
    print_report(
        from_name=from_key,
        to_name=to_key,
        from_model=from_info,
        to_model=to_info,
        from_cost=from_cost,
        to_cost=to_cost_data,
        from_latency=from_latency,
        to_latency=to_latency,
        effort=effort,
        risks=risks,
        monthly_requests=args.monthly_requests,
        avg_input_tokens=args.avg_input_tokens,
        avg_output_tokens=args.avg_output_tokens,
    )

    # JSON output
    if args.output:
        monthly_delta = to_cost_data["total_monthly"] - from_cost["total_monthly"]
        report = {
            "migration": {"from": from_key, "to": to_key},
            "traffic": {
                "monthly_requests": args.monthly_requests,
                "avg_input_tokens": args.avg_input_tokens,
                "avg_output_tokens": args.avg_output_tokens,
            },
            "from_cost": from_cost,
            "to_cost": to_cost_data,
            "monthly_delta": round(monthly_delta, 2),
            "annual_delta": round(monthly_delta * 12, 2),
            "from_latency": from_latency,
            "to_latency": to_latency,
            "effort": effort,
            "risks": risks,
        }
        pb = payback_months(-monthly_delta, effort["total_cost"])
        if pb is not None:
            report["payback_months"] = round(pb, 1)
        with open(args.output, "w") as f:
            json.dump(report, f, indent=2)
        print(f"\n📁 Report saved to {args.output}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
