#!/usr/bin/env python3
"""
Eval Cost Calculator

Estimate the cost of running LLM evaluations (tokens × model price).
Supports per-run estimates and batch planning.

Usage:
    python eval-cost-calculator.py --cases 500 --avg-input 200 --avg-output 300
    python eval-cost-calculator.py --results results.json
    python eval-cost-calculator.py --interactive

Requirements:
    None (stdlib only)
"""

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional, List, Any

# Approximate USD per 1M tokens (input / output) - update as needed
DEFAULT_PRICING: Dict[str, Dict[str, float]] = {
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


@dataclass
class CostEstimate:
    """Cost estimate for an eval run."""
    model: str
    num_cases: int
    total_input_tokens: int
    total_output_tokens: int
    input_cost_usd: float
    output_cost_usd: float
    total_cost_usd: float
    cost_per_case_usd: float


def get_pricing(model: str) -> Dict[str, float]:
    """Get pricing for model (per 1M tokens). Uses first key match if full name not found."""
    model_lower = model.lower()
    for key, val in DEFAULT_PRICING.items():
        if key.lower() in model_lower or model_lower in key.lower():
            return val
    # Default to sonnet-like if unknown
    return {"input": 3.0, "output": 15.0}


def estimate_cost(
    num_cases: int,
    avg_input_tokens: int,
    avg_output_tokens: int,
    model: str
) -> CostEstimate:
    """
    Estimate total and per-case cost for an eval run.
    """
    pricing = get_pricing(model)
    total_input = num_cases * avg_input_tokens
    total_output = num_cases * avg_output_tokens
    input_cost = (total_input / 1_000_000) * pricing["input"]
    output_cost = (total_output / 1_000_000) * pricing["output"]
    total_cost = input_cost + output_cost
    cost_per_case = total_cost / num_cases if num_cases else 0.0
    return CostEstimate(
        model=model,
        num_cases=num_cases,
        total_input_tokens=total_input,
        total_output_tokens=total_output,
        input_cost_usd=round(input_cost, 4),
        output_cost_usd=round(output_cost, 4),
        total_cost_usd=round(total_cost, 4),
        cost_per_case_usd=round(cost_per_case, 4)
    )


def estimate_from_results(results_path: str, model: Optional[str] = None) -> Optional[CostEstimate]:
    """
    Compute cost from an existing results JSON that has tokens_used (and optionally
    input/output breakdown). If model not provided, try to read from results.
    """
    with open(results_path, "r") as f:
        data = json.load(f)
    if isinstance(data, list):
        items = data
    elif isinstance(data, dict) and "per_case" in data:
        items = data["per_case"]
    elif isinstance(data, dict) and "results" in data:
        items = data["results"]
    else:
        items = data if isinstance(data, list) else []
    if not items:
        return None
    total_input = 0
    total_output = 0
    for r in items:
        if isinstance(r, dict):
            # Some results have tokens_used only
            total = r.get("tokens_used", 0) or r.get("tokens", 0)
            inp = r.get("input_tokens", total // 2)
            out = r.get("output_tokens", total - inp)
            total_input += inp
            total_output += out
    model_name = model or (items[0].get("judge_model") if items and isinstance(items[0], dict) else "claude-3-sonnet-20240229")
    pricing = get_pricing(model_name)
    input_cost = (total_input / 1_000_000) * pricing["input"]
    output_cost = (total_output / 1_000_000) * pricing["output"]
    total_cost = input_cost + output_cost
    return CostEstimate(
        model=model_name,
        num_cases=len(items),
        total_input_tokens=total_input,
        total_output_tokens=total_output,
        input_cost_usd=round(input_cost, 4),
        output_cost_usd=round(output_cost, 4),
        total_cost_usd=round(total_cost, 4),
        cost_per_case_usd=round(total_cost / len(items), 4) if items else 0.0
    )


def print_estimate(est: CostEstimate):
    """Print a formatted cost estimate."""
    print("\n" + "=" * 55)
    print("EVAL COST ESTIMATE")
    print("=" * 55)
    print(f"  Model:              {est.model}")
    print(f"  Number of cases:    {est.num_cases:,}")
    print(f"  Input tokens:      {est.total_input_tokens:,}")
    print(f"  Output tokens:     {est.total_output_tokens:,}")
    print(f"  Input cost:        ${est.input_cost_usd:.4f}")
    print(f"  Output cost:       ${est.output_cost_usd:.4f}")
    print(f"  Total cost:        ${est.total_cost_usd:.4f}")
    print(f"  Cost per case:     ${est.cost_per_case_usd:.4f}")
    print("=" * 55 + "\n")


def interactive():
    """Interactive mode."""
    print("\nEval Cost Calculator")
    print("-" * 40)
    try:
        num = int(input("Number of test cases: ").strip())
        avg_in = int(input("Average input tokens per case (e.g. 500): ").strip())
        avg_out = int(input("Average output tokens per case (e.g. 300): ").strip())
        model = input("Model name (default: claude-3-sonnet-20240229): ").strip() or "claude-3-sonnet-20240229"
    except (ValueError, EOFError):
        print("Invalid input.")
        return
    est = estimate_cost(num, avg_in, avg_out, model)
    print_estimate(est)


def main():
    parser = argparse.ArgumentParser(description="Estimate eval cost (tokens × model price)")
    parser.add_argument("--cases", "-n", type=int, help="Number of test cases")
    parser.add_argument("--avg-input", "-i", type=int, default=500, help="Avg input tokens per case")
    parser.add_argument("--avg-output", "-o", type=int, default=400, help="Avg output tokens per case")
    parser.add_argument("--model", "-m", default="claude-3-sonnet-20240229", help="Model name")
    parser.add_argument("--results", "-r", help="Path to results JSON to compute actual cost")
    parser.add_argument("--interactive", action="store_true", help="Interactive mode")
    parser.add_argument("--list-models", action="store_true", help="List known models and pricing")
    args = parser.parse_args()

    if args.list_models:
        print("Known models (USD per 1M tokens, input / output):")
        for name, p in DEFAULT_PRICING.items():
            print(f"  {name}: ${p['input']} / ${p['output']}")
        return 0

    if args.interactive:
        interactive()
        return 0

    if args.results:
        est = estimate_from_results(args.results, args.model)
        if est:
            print_estimate(est)
        else:
            print("Could not compute cost from results file.")
        return 0

    if args.cases is None:
        parser.print_help()
        return 0

    est = estimate_cost(args.cases, args.avg_input, args.avg_output, args.model)
    print_estimate(est)
    return 0


if __name__ == "__main__":
    exit(main())