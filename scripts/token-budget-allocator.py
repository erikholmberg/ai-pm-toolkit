#!/usr/bin/env python3
"""
Token Budget Allocator

Given a per-request or monthly token budget, allocate across prompt components:
system prompt, retrieval context, user input, output reserve, and safety margin.
Helps AI PMs optimize context window usage as models and costs scale.

Produces a breakdown showing how many tokens each component gets, identifies
bottlenecks, and suggests optimization strategies when the budget is tight.

Usage:
    # Quick allocation for a single request
    python token-budget-allocator.py \\
        --context-window 128000 --max-output 4096 \\
        --system-prompt 1500 --avg-user-input 500 \\
        --rag-chunks 5 --chunk-size 800

    # With cost estimation
    python token-budget-allocator.py \\
        --context-window 128000 --max-output 4096 \\
        --system-prompt 2000 --avg-user-input 300 \\
        --rag-chunks 8 --chunk-size 600 \\
        --input-cost 3.00 --output-cost 15.00 \\
        --monthly-requests 100000

    # From a JSON config (multiple features/endpoints)
    python token-budget-allocator.py --config allocation.json

    # Custom components
    python token-budget-allocator.py \\
        --context-window 32000 --max-output 2048 \\
        --component "System prompt:1200" \\
        --component "Few-shot examples:2400" \\
        --component "User query:500" \\
        --component "RAG context:8000" \\
        --component "Tool definitions:3000"

JSON config format:
    {
      "context_window": 128000,
      "max_output": 4096,
      "input_cost_per_1m": 3.00,
      "output_cost_per_1m": 15.00,
      "monthly_requests": 100000,
      "features": [
        {
          "name": "Chat Assistant",
          "system_prompt": 1500,
          "avg_user_input": 400,
          "rag_chunks": 5,
          "chunk_size": 800,
          "max_output": 2048
        },
        {
          "name": "Document Summarizer",
          "system_prompt": 800,
          "avg_user_input": 8000,
          "rag_chunks": 0,
          "chunk_size": 0,
          "max_output": 4096
        }
      ]
    }

Requirements:
    None (stdlib only).
"""

import argparse
import json
import sys
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Token allocation
# ---------------------------------------------------------------------------

SAFETY_MARGIN_PCT = 5  # reserve 5% for tokenizer variance


def allocate_budget(
    context_window: int,
    max_output: int,
    components: List[Dict[str, Any]],
    safety_margin_pct: float = SAFETY_MARGIN_PCT,
) -> Dict[str, Any]:
    """
    Allocate a token budget across components.

    The context window is split:
        context_window = input_tokens + output_tokens
        input_tokens = sum(components) + safety_margin
        remaining = input_tokens - sum(fixed_components)  → available for flexible components
    """
    safety_tokens = int(context_window * safety_margin_pct / 100)
    input_budget = context_window - max_output - safety_tokens

    total_requested = sum(c["tokens"] for c in components)
    over_budget = total_requested > input_budget
    utilization_pct = total_requested / input_budget * 100 if input_budget > 0 else 0
    remaining = input_budget - total_requested

    # Classify each component
    allocated = []
    for c in components:
        pct_of_input = c["tokens"] / input_budget * 100 if input_budget > 0 else 0
        pct_of_window = c["tokens"] / context_window * 100 if context_window > 0 else 0
        allocated.append({
            **c,
            "pct_of_input": round(pct_of_input, 1),
            "pct_of_window": round(pct_of_window, 1),
        })

    return {
        "context_window": context_window,
        "max_output": max_output,
        "safety_margin_tokens": safety_tokens,
        "safety_margin_pct": safety_margin_pct,
        "input_budget": input_budget,
        "total_requested": total_requested,
        "remaining": remaining,
        "over_budget": over_budget,
        "utilization_pct": round(utilization_pct, 1),
        "components": allocated,
    }


def estimate_cost(
    total_input_tokens: int,
    total_output_tokens: int,
    input_cost_per_1m: float,
    output_cost_per_1m: float,
    monthly_requests: int,
) -> Dict[str, Any]:
    """Estimate monthly cost."""
    input_cost_per_req = total_input_tokens * input_cost_per_1m / 1_000_000
    output_cost_per_req = total_output_tokens * output_cost_per_1m / 1_000_000
    cost_per_req = input_cost_per_req + output_cost_per_req
    monthly_cost = cost_per_req * monthly_requests

    return {
        "input_tokens_per_req": total_input_tokens,
        "output_tokens_per_req": total_output_tokens,
        "input_cost_per_req": round(input_cost_per_req, 6),
        "output_cost_per_req": round(output_cost_per_req, 6),
        "cost_per_request": round(cost_per_req, 6),
        "monthly_requests": monthly_requests,
        "monthly_cost": round(monthly_cost, 2),
        "annual_cost": round(monthly_cost * 12, 2),
        "input_cost_per_1m": input_cost_per_1m,
        "output_cost_per_1m": output_cost_per_1m,
    }


def suggest_optimizations(allocation: Dict[str, Any]) -> List[str]:
    """Generate optimization suggestions based on allocation."""
    suggestions = []
    components = allocation["components"]

    if allocation["over_budget"]:
        suggestions.append(f"🔴 Over budget by {abs(allocation['remaining']):,} tokens — must reduce input components")

    # Find the biggest component
    if components:
        biggest = max(components, key=lambda c: c["tokens"])
        if biggest["pct_of_input"] > 60:
            suggestions.append(
                f"🟡 '{biggest['name']}' uses {biggest['pct_of_input']:.0f}% of input budget — "
                f"consider trimming or chunking"
            )

    # RAG-specific suggestions
    rag_components = [c for c in components if "rag" in c["name"].lower() or "context" in c["name"].lower() or "retrieval" in c["name"].lower()]
    for c in rag_components:
        if c["tokens"] > allocation["input_budget"] * 0.5:
            suggestions.append(
                f"🟡 RAG context uses {c['pct_of_input']:.0f}% of budget — consider reducing chunks or using "
                f"reranking to select fewer, higher-quality passages"
            )

    if allocation["utilization_pct"] > 90 and not allocation["over_budget"]:
        suggestions.append("🟡 >90% utilization — little headroom for longer user inputs or edge cases")

    if allocation["utilization_pct"] < 40:
        suggestions.append("🟢 <40% utilization — room to add more context, few-shot examples, or tool definitions")

    if allocation["max_output"] < 1024:
        suggestions.append("🟡 Output budget is small (<1K tokens) — may truncate longer responses")

    if allocation["safety_margin_pct"] < 3:
        suggestions.append("🟡 Safety margin is tight — increase to 5% to avoid tokenizer overflows")

    if not suggestions:
        suggestions.append("🟢 Allocation looks healthy — good balance across components")

    return suggestions


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def _bar(value: float, max_val: float, width: int = 30) -> str:
    if max_val <= 0:
        return "░" * width
    ratio = min(1.0, max(0.0, value / max_val))
    filled = int(ratio * width)
    return "█" * filled + "░" * (width - filled)


def _fmt_tokens(n: int) -> str:
    if abs(n) >= 1_000_000:
        return f"{n / 1_000_000:,.1f}M"
    elif abs(n) >= 1_000:
        return f"{n / 1_000:,.1f}K"
    else:
        return f"{n:,}"


def _fmt_money(val: float) -> str:
    if abs(val) >= 1_000_000:
        return f"${val / 1_000_000:,.1f}M"
    elif abs(val) >= 1_000:
        return f"${val / 1_000:,.1f}K"
    else:
        return f"${val:,.2f}"


def print_report(
    allocations: List[Tuple[str, Dict[str, Any]]],
    costs: Optional[List[Tuple[str, Dict[str, Any]]]] = None,
) -> None:
    """Pretty-print token budget allocation."""
    print("\n" + "=" * 78)
    print("🎯 TOKEN BUDGET ALLOCATOR")
    print("=" * 78)

    for name, alloc in allocations:
        cw = alloc["context_window"]

        print(f"\n{'─'*78}")
        if name:
            print(f"\n📋 {name.upper()}")
        print(f"\n   Context window:     {_fmt_tokens(cw)} tokens")
        print(f"   Max output:         {_fmt_tokens(alloc['max_output'])} tokens")
        print(f"   Safety margin:      {_fmt_tokens(alloc['safety_margin_tokens'])} ({alloc['safety_margin_pct']:.0f}%)")
        print(f"   Input budget:       {_fmt_tokens(alloc['input_budget'])} tokens")
        print(f"   Requested:          {_fmt_tokens(alloc['total_requested'])} tokens")

        status = "🔴 OVER BUDGET" if alloc["over_budget"] else "🟢 Within budget"
        print(f"   Status:             {status}")
        if alloc["remaining"] >= 0:
            print(f"   Remaining:          {_fmt_tokens(alloc['remaining'])} tokens")
        else:
            print(f"   Over by:            {_fmt_tokens(abs(alloc['remaining']))} tokens")

        # Component breakdown
        print(f"\n   📊 COMPONENT BREAKDOWN:\n")
        print(f"   {'Component':<24} {'Tokens':>8} {'% Input':>8} {'% Window':>9}")
        print(f"   {'─'*24} {'─'*8} {'─'*8} {'─'*9}")

        for c in alloc["components"]:
            print(f"   {c['name'][:24]:<24} {c['tokens']:>8,} {c['pct_of_input']:>7.1f}% {c['pct_of_window']:>8.1f}%")

        print(f"   {'─'*24} {'─'*8} {'─'*8} {'─'*9}")
        print(f"   {'Total input':<24} {alloc['total_requested']:>8,} {alloc['utilization_pct']:>7.1f}%")
        print(f"   {'+ Output reserve':<24} {alloc['max_output']:>8,}")
        print(f"   {'+ Safety margin':<24} {alloc['safety_margin_tokens']:>8,}")
        total_all = alloc['total_requested'] + alloc['max_output'] + alloc['safety_margin_tokens']
        print(f"   {'= Total':<24} {total_all:>8,}")

        # Visual allocation
        print(f"\n   🗺️  CONTEXT WINDOW MAP:")
        segments = []
        for c in alloc["components"]:
            segments.append((c["name"][:12], c["tokens"]))
        segments.append(("Output", alloc["max_output"]))
        segments.append(("Safety", alloc["safety_margin_tokens"]))
        if alloc["remaining"] > 0:
            segments.append(("Free", alloc["remaining"]))

        bar_width = 60
        bar_parts = []
        labels = []
        chars = "█▓▒░"
        for i, (seg_name, seg_tokens) in enumerate(segments):
            ratio = seg_tokens / cw if cw > 0 else 0
            seg_width = max(1, int(ratio * bar_width)) if seg_tokens > 0 else 0
            char = chars[i % len(chars)]
            bar_parts.append(char * seg_width)
            if seg_width >= 3:
                labels.append(f"   {char} {seg_name} ({_fmt_tokens(seg_tokens)})")

        bar_str = "".join(bar_parts)[:bar_width]
        bar_str += "·" * max(0, bar_width - len(bar_str))
        print(f"   [{bar_str}]")
        for label in labels:
            print(label)

        # Optimization suggestions
        suggestions = suggest_optimizations(alloc)
        if suggestions:
            print(f"\n   💡 SUGGESTIONS:")
            for s in suggestions:
                print(f"   {s}")

    # Cost estimation
    if costs:
        print(f"\n{'─'*78}")
        print(f"\n💰 COST ESTIMATION:\n")
        print(f"   {'Feature':<22} {'In Tok':>8} {'Out Tok':>8} {'$/Req':>10} {'Monthly':>12}")
        print(f"   {'─'*22} {'─'*8} {'─'*8} {'─'*10} {'─'*12}")

        total_monthly = 0
        for name, cost in costs:
            in_tok = _fmt_tokens(cost["input_tokens_per_req"])
            out_tok = _fmt_tokens(cost["output_tokens_per_req"])
            per_req = f"${cost['cost_per_request']:.4f}"
            monthly = _fmt_money(cost["monthly_cost"])
            print(f"   {(name or 'Default')[:22]:<22} {in_tok:>8} {out_tok:>8} {per_req:>10} {monthly:>12}")
            total_monthly += cost["monthly_cost"]

        if len(costs) > 1:
            print(f"   {'─'*22} {'─'*8} {'─'*8} {'─'*10} {'─'*12}")
            print(f"   {'TOTAL':<22} {'':>8} {'':>8} {'':>10} {_fmt_money(total_monthly):>12}")

        print(f"\n   Annual projection: {_fmt_money(total_monthly * 12)}")

        # Cost optimization tips
        if total_monthly > 1000:
            print(f"\n   💡 Cost optimization tips:")
            for name, cost in costs:
                if cost["input_tokens_per_req"] > 10000:
                    print(f"   • {name or 'Default'}: high input tokens — consider shorter system prompts or fewer RAG chunks")
                if cost["output_cost_per_req"] > cost["input_cost_per_req"] * 2:
                    print(f"   • {name or 'Default'}: output-dominated cost — consider constraining max_tokens")

    print(f"\n{'─'*78}")
    print(f"\n💡 GENERAL TIPS:")
    print(f"   • Keep system prompts under 2K tokens for most use cases")
    print(f"   • RAG: 3-5 chunks of 500-800 tokens is usually sufficient")
    print(f"   • Reserve 5% safety margin for tokenizer variance")
    print(f"   • Monitor actual token usage and adjust allocations quarterly")
    print(f"   • Consider prompt caching to reduce costs for repeated system prompts")
    print("\n" + "=" * 78)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Allocate token budget across prompt components. Helps AI PMs "
                    "optimize context window usage and estimate costs.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --context-window 128000 --max-output 4096 \\
           --system-prompt 1500 --avg-user-input 500 \\
           --rag-chunks 5 --chunk-size 800
  %(prog)s --context-window 128000 --max-output 4096 \\
           --component "System:1500" --component "RAG:4000" --component "User:500"
  %(prog)s --config allocation.json
        """,
    )

    parser.add_argument("--context-window", type=int, help="Total context window size in tokens")
    parser.add_argument("--max-output", type=int, default=4096, help="Max output tokens (default: 4096)")
    parser.add_argument("--system-prompt", type=int, help="System prompt token count")
    parser.add_argument("--avg-user-input", type=int, help="Average user input tokens")
    parser.add_argument("--rag-chunks", type=int, help="Number of RAG context chunks")
    parser.add_argument("--chunk-size", type=int, default=600, help="Tokens per RAG chunk (default: 600)")
    parser.add_argument("--few-shot", type=int, help="Few-shot examples token count")
    parser.add_argument("--tool-defs", type=int, help="Tool/function definitions token count")
    parser.add_argument("--component", type=str, action="append", help="Custom component: 'Name:tokens'")
    parser.add_argument("--safety-margin", type=float, default=SAFETY_MARGIN_PCT,
                        help=f"Safety margin %% (default: {SAFETY_MARGIN_PCT})")

    # Cost
    parser.add_argument("--input-cost", type=float, help="Input cost per 1M tokens (USD)")
    parser.add_argument("--output-cost", type=float, help="Output cost per 1M tokens (USD)")
    parser.add_argument("--monthly-requests", type=int, help="Monthly request volume")

    # Config
    parser.add_argument("--config", type=str, help="JSON config file for multi-feature allocation")
    parser.add_argument("--output", "-o", type=str, help="Write JSON results to file")

    args = parser.parse_args()

    allocations: List[Tuple[str, Dict[str, Any]]] = []
    cost_estimates: List[Tuple[str, Dict[str, Any]]] = []

    if args.config:
        try:
            with open(args.config, encoding="utf-8") as f:
                config = json.load(f)
        except Exception as e:
            print(f"Error loading config: {e}", file=sys.stderr)
            return 1

        cw = config.get("context_window", args.context_window or 128000)
        input_cost = config.get("input_cost_per_1m", args.input_cost)
        output_cost = config.get("output_cost_per_1m", args.output_cost)
        monthly_req = config.get("monthly_requests", args.monthly_requests)

        for feature in config.get("features", []):
            fname = feature.get("name", "Unnamed")
            mo = feature.get("max_output", config.get("max_output", 4096))
            components = []

            if feature.get("system_prompt"):
                components.append({"name": "System prompt", "tokens": feature["system_prompt"]})
            if feature.get("avg_user_input"):
                components.append({"name": "User input", "tokens": feature["avg_user_input"]})
            if feature.get("rag_chunks") and feature.get("chunk_size"):
                rag_tokens = feature["rag_chunks"] * feature["chunk_size"]
                components.append({"name": f"RAG ({feature['rag_chunks']} chunks)", "tokens": rag_tokens})
            if feature.get("few_shot"):
                components.append({"name": "Few-shot examples", "tokens": feature["few_shot"]})
            if feature.get("tool_defs"):
                components.append({"name": "Tool definitions", "tokens": feature["tool_defs"]})

            for extra in feature.get("components", []):
                components.append({"name": extra["name"], "tokens": extra["tokens"]})

            alloc = allocate_budget(cw, mo, components, args.safety_margin)
            allocations.append((fname, alloc))

            if input_cost and output_cost and monthly_req:
                feature_reqs = monthly_req // max(len(config.get("features", [1])), 1)
                cost = estimate_cost(alloc["total_requested"], mo, input_cost, output_cost, feature_reqs)
                cost_estimates.append((fname, cost))

    elif args.context_window:
        components = []

        if args.system_prompt:
            components.append({"name": "System prompt", "tokens": args.system_prompt})
        if args.avg_user_input:
            components.append({"name": "User input", "tokens": args.avg_user_input})
        if args.rag_chunks:
            rag_tokens = args.rag_chunks * args.chunk_size
            components.append({"name": f"RAG ({args.rag_chunks} chunks)", "tokens": rag_tokens})
        if args.few_shot:
            components.append({"name": "Few-shot examples", "tokens": args.few_shot})
        if args.tool_defs:
            components.append({"name": "Tool definitions", "tokens": args.tool_defs})

        if args.component:
            for comp_str in args.component:
                parts = comp_str.rsplit(":", 1)
                if len(parts) != 2:
                    print(f"Error: invalid component '{comp_str}'. Format: 'Name:tokens'", file=sys.stderr)
                    return 1
                components.append({"name": parts[0].strip(), "tokens": int(parts[1].strip())})

        if not components:
            print("Error: provide at least one component (--system-prompt, --component, etc.).", file=sys.stderr)
            return 1

        alloc = allocate_budget(args.context_window, args.max_output, components, args.safety_margin)
        allocations.append(("", alloc))

        if args.input_cost and args.output_cost and args.monthly_requests:
            cost = estimate_cost(
                alloc["total_requested"], args.max_output,
                args.input_cost, args.output_cost, args.monthly_requests,
            )
            cost_estimates.append(("", cost))
    else:
        print("Error: provide --context-window or --config.", file=sys.stderr)
        parser.print_help(sys.stderr)
        return 1

    # Report
    print_report(allocations, cost_estimates if cost_estimates else None)

    # JSON output
    if args.output:
        report = {
            "allocations": [{
                "name": name,
                **{k: v for k, v in alloc.items()},
            } for name, alloc in allocations],
        }
        if cost_estimates:
            report["costs"] = [{
                "name": name,
                **cost,
            } for name, cost in cost_estimates]
        with open(args.output, "w") as f:
            json.dump(report, f, indent=2)
        print(f"\n📁 Results saved to {args.output}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
