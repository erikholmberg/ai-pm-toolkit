#!/usr/bin/env python3
"""
Agentic Cost Simulator

Estimate the cost and latency of a multi-step agentic workflow — an agent
that loops through think → call tool → observe → repeat — before you build
it. PMs use this to size the "agent tax" (how much more expensive/slower an
agent loop is than a single LLM call) and to see which lever (steps, retry
rate, sub-agent fanout) moves cost the most.

Models each task as a chain of LLM calls (one per agentic step), each
consuming input + output tokens, with an added multiplier for retried steps
and for optional parallel sub-agent fanout. Compares the result to a naive
single-call baseline handling the same task.

Usage:
    python agentic-cost-simulator.py
    python agentic-cost-simulator.py --steps-per-task 6 --tasks-per-month 50000
    python agentic-cost-simulator.py --steps-per-task 5 --retry-rate 0.15 \\
        --sub-agent-fanout 2 --tasks-per-month 20000 --output report.json
    python agentic-cost-simulator.py --input-cost-per-m 15 --output-cost-per-m 75  # pricier model

Requirements:
    None (stdlib only).
"""

import argparse
import json
import sys
from typing import Any, Dict

# Shared result envelope (provenance + machine-readable chaining).
# See scripts/toolkit_io.py.
import toolkit_io

TOOL = "agentic-cost-simulator"


# ---------------------------------------------------------------------------
# Assumptions (editable) — see docstring for how each is used
# ---------------------------------------------------------------------------

# ms of wall-clock time per agentic step (think + tool call + observe), rough
# planning estimate; override with --step-latency-ms.
DEFAULT_STEP_LATENCY_MS = 3000.0
# ms for a single non-agentic call handling the same task end-to-end.
DEFAULT_BASELINE_LATENCY_MS = 4000.0


# ---------------------------------------------------------------------------
# Core calculations
# ---------------------------------------------------------------------------

def call_cost(input_tokens: float, output_tokens: float, input_cost_per_m: float, output_cost_per_m: float) -> float:
    """USD cost of a single LLM call."""
    return (input_tokens / 1_000_000) * input_cost_per_m + (output_tokens / 1_000_000) * output_cost_per_m


def simulate(
    steps_per_task: float,
    input_tokens_per_step: float,
    output_tokens_per_step: float,
    retry_rate: float,
    sub_agent_fanout: float,
    tasks_per_month: int,
    input_cost_per_m: float,
    output_cost_per_m: float,
    step_latency_ms: float,
    baseline_input_tokens: float,
    baseline_output_tokens: float,
    baseline_latency_ms: float,
) -> Dict[str, Any]:
    """
    Simulate agentic workflow cost & latency vs a naive single-call baseline.

    Model:
      - Each task runs `steps_per_task` LLM calls (one per think/tool/observe loop).
      - `retry_rate` is the fraction of steps that need a retry (an extra call).
      - `sub_agent_fanout` is the average number of additional parallel sub-agent
        "copies" of the step chain a task spawns (0 = no sub-agents). Each fanned-out
        sub-agent runs its own step chain at the same token profile.
      - All calls share the same avg input/output token profile for simplicity;
        pass per-step estimates that already reflect your workflow's mix.
    """
    calls_per_task_before_fanout = steps_per_task * (1 + retry_rate)
    total_calls_per_task = calls_per_task_before_fanout * (1 + sub_agent_fanout)

    cost_per_call = call_cost(input_tokens_per_step, output_tokens_per_step, input_cost_per_m, output_cost_per_m)
    cost_per_task = cost_per_call * total_calls_per_task
    monthly_cost = cost_per_task * tasks_per_month

    # Cost attributable to retries: difference between with-retry and no-retry cost
    no_retry_calls_per_task = steps_per_task * (1 + sub_agent_fanout)
    no_retry_cost_per_task = cost_per_call * no_retry_calls_per_task
    retry_cost_per_task = cost_per_task - no_retry_cost_per_task
    retry_monthly_cost = retry_cost_per_task * tasks_per_month

    # Cost attributable to sub-agent fanout: difference vs fanout=0
    no_fanout_calls_per_task = steps_per_task * (1 + retry_rate)
    no_fanout_cost_per_task = cost_per_call * no_fanout_calls_per_task
    fanout_cost_per_task = cost_per_task - no_fanout_cost_per_task
    fanout_monthly_cost = fanout_cost_per_task * tasks_per_month

    # Sensitivity: cost of 1 more step per task
    marginal_step_cost_per_task = cost_per_call * (1 + retry_rate) * (1 + sub_agent_fanout)
    marginal_step_monthly_cost = marginal_step_cost_per_task * tasks_per_month

    # Latency
    latency_per_task_ms = total_calls_per_task * step_latency_ms
    if sub_agent_fanout > 0:
        # Sub-agents run in parallel, so wall-clock latency doesn't scale with
        # fanout the way cost does — only the primary chain's latency counts,
        # assuming sub-agents are awaited concurrently.
        latency_per_task_ms = calls_per_task_before_fanout * step_latency_ms

    # Baseline: single non-agentic call
    baseline_cost_per_task = call_cost(baseline_input_tokens, baseline_output_tokens, input_cost_per_m, output_cost_per_m)
    baseline_monthly_cost = baseline_cost_per_task * tasks_per_month

    agent_tax_cost = cost_per_task - baseline_cost_per_task
    agent_tax_multiple = (cost_per_task / baseline_cost_per_task) if baseline_cost_per_task > 0 else None
    agent_tax_latency_ms = latency_per_task_ms - baseline_latency_ms
    agent_tax_latency_multiple = (latency_per_task_ms / baseline_latency_ms) if baseline_latency_ms > 0 else None

    return {
        "inputs": {
            "steps_per_task": steps_per_task,
            "input_tokens_per_step": input_tokens_per_step,
            "output_tokens_per_step": output_tokens_per_step,
            "retry_rate": retry_rate,
            "sub_agent_fanout": sub_agent_fanout,
            "tasks_per_month": tasks_per_month,
            "input_cost_per_m": input_cost_per_m,
            "output_cost_per_m": output_cost_per_m,
        },
        "total_calls_per_task": round(total_calls_per_task, 2),
        "cost_per_call": round(cost_per_call, 6),
        "cost_per_task": round(cost_per_task, 4),
        "monthly_cost": round(monthly_cost, 2),
        "annual_cost": round(monthly_cost * 12, 2),
        "retry_cost_per_task": round(retry_cost_per_task, 4),
        "retry_monthly_cost": round(retry_monthly_cost, 2),
        "fanout_cost_per_task": round(fanout_cost_per_task, 4),
        "fanout_monthly_cost": round(fanout_monthly_cost, 2),
        "marginal_step_cost_per_task": round(marginal_step_cost_per_task, 4),
        "marginal_step_monthly_cost": round(marginal_step_monthly_cost, 2),
        "latency_per_task_ms": round(latency_per_task_ms, 0),
        "latency_per_task_s": round(latency_per_task_ms / 1000, 1),
        "baseline": {
            "input_tokens": baseline_input_tokens,
            "output_tokens": baseline_output_tokens,
            "cost_per_task": round(baseline_cost_per_task, 4),
            "monthly_cost": round(baseline_monthly_cost, 2),
            "latency_ms": baseline_latency_ms,
        },
        "agent_tax": {
            "cost_per_task": round(agent_tax_cost, 4),
            "cost_multiple": round(agent_tax_multiple, 1) if agent_tax_multiple is not None else None,
            "monthly_cost": round(monthly_cost - baseline_monthly_cost, 2),
            "latency_ms": round(agent_tax_latency_ms, 0),
            "latency_multiple": round(agent_tax_latency_multiple, 1) if agent_tax_latency_multiple is not None else None,
        },
    }


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def _fmt_usd(amount: float) -> str:
    if abs(amount) >= 1000:
        return f"${amount:,.2f}"
    elif abs(amount) >= 1:
        return f"${amount:.2f}"
    else:
        return f"${amount:.4f}"


def print_report(r: Dict[str, Any]) -> None:
    inp = r["inputs"]
    print("\n" + "=" * 78)
    print("🔁 AGENTIC COST SIMULATOR")
    print("=" * 78)

    print(f"\n📋 WORKFLOW ASSUMPTIONS:")
    print(f"   • Steps per task:          {inp['steps_per_task']:g}")
    print(f"   • Input tokens/step:       {inp['input_tokens_per_step']:,g}")
    print(f"   • Output tokens/step:      {inp['output_tokens_per_step']:,g}")
    print(f"   • Retry rate:              {inp['retry_rate']:.0%}")
    print(f"   • Sub-agent fanout:        {inp['sub_agent_fanout']:g}x")
    print(f"   • Tasks/month:             {inp['tasks_per_month']:,}")
    print(f"   • Price ($/1M in / out):   {_fmt_usd(inp['input_cost_per_m'])} / {_fmt_usd(inp['output_cost_per_m'])}")

    print(f"\n💰 COST PER TASK:")
    print(f"   • Effective calls/task:    {r['total_calls_per_task']:g}")
    print(f"   • Cost per call:           {_fmt_usd(r['cost_per_call'])}")
    print(f"   • Cost per task:           {_fmt_usd(r['cost_per_task'])}")

    print(f"\n📈 MONTHLY COST:")
    print(f"   • Monthly total:           {_fmt_usd(r['monthly_cost'])}")
    print(f"   • Annual total:            {_fmt_usd(r['annual_cost'])}")

    print(f"\n🔂 COST BREAKDOWN:")
    print(f"   • From retries:            {_fmt_usd(r['retry_monthly_cost'])}/mo  ({_fmt_usd(r['retry_cost_per_task'])}/task)")
    if inp["sub_agent_fanout"] > 0:
        print(f"   • From sub-agent fanout:   {_fmt_usd(r['fanout_monthly_cost'])}/mo  ({_fmt_usd(r['fanout_cost_per_task'])}/task)")

    print(f"\n📐 SENSITIVITY:")
    print(f"   • 1 more step/task costs:  {_fmt_usd(r['marginal_step_cost_per_task'])}/task → {_fmt_usd(r['marginal_step_monthly_cost'])}/mo")

    print(f"\n⚡ LATENCY (per task, wall-clock):")
    print(f"   • Agentic workflow:        ~{r['latency_per_task_ms']:.0f}ms ({r['latency_per_task_s']:.1f}s)")
    print(f"   • Naive baseline:          ~{r['baseline']['latency_ms']:.0f}ms ({r['baseline']['latency_ms']/1000:.1f}s)")

    print(f"\n⚖️  AGENT TAX (agentic workflow vs a single naive LLM call):")
    b = r["baseline"]
    at = r["agent_tax"]
    print(f"   {'':22} {'Naive call':>14} {'Agentic wf':>14} {'Tax':>14}")
    print(f"   {'─'*22} {'─'*14} {'─'*14} {'─'*14}")
    print(f"   {'Cost/task':<22} {_fmt_usd(b['cost_per_task']):>14} {_fmt_usd(r['cost_per_task']):>14} {_fmt_usd(at['cost_per_task']):>14}")
    print(f"   {'Cost/month':<22} {_fmt_usd(b['monthly_cost']):>14} {_fmt_usd(r['monthly_cost']):>14} {_fmt_usd(at['monthly_cost']):>14}")
    print(f"   {'Latency/task':<22} {b['latency_ms']:>12.0f}ms {r['latency_per_task_ms']:>12.0f}ms {at['latency_ms']:>12.0f}ms")
    if at["cost_multiple"] is not None:
        print(f"\n   💡 The agentic workflow costs ~{at['cost_multiple']:.1f}x a single naive call", end="")
        if at["latency_multiple"] is not None:
            print(f" and takes ~{at['latency_multiple']:.1f}x as long.")
        else:
            print(".")

    print(f"\n💡 GUIDANCE:")
    print(f"   • Retries and fanout both multiply cost linearly — cutting either is often cheaper than model downgrades.")
    print(f"   • If cost/latency here doesn't clear the bar, consider a router: cheap single-call path for simple tasks, agentic path only when needed.")
    print(f"   • Re-run with real steps_per_task and retry_rate from a pilot before committing to a budget.")

    print("\n" + "=" * 78)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Estimate cost & latency of a multi-step agentic (think/tool/observe loop) "
                    "workflow before building it, compared to a naive single-call baseline.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s
  %(prog)s --steps-per-task 6 --tasks-per-month 50000
  %(prog)s --steps-per-task 5 --retry-rate 0.15 --sub-agent-fanout 2 --tasks-per-month 20000
  %(prog)s --input-cost-per-m 15 --output-cost-per-m 75 --output report.json
        """,
    )
    parser.add_argument("--steps-per-task", type=float, default=4.0, help="Avg tool-call/LLM steps per task (default: 4)")
    parser.add_argument("--input-tokens-per-step", type=float, default=1500.0, help="Avg input tokens per step, incl. context/history (default: 1500)")
    parser.add_argument("--output-tokens-per-step", type=float, default=300.0, help="Avg output tokens per step (default: 300)")
    parser.add_argument("--retry-rate", type=float, default=0.1, help="Fraction of steps that get retried (default: 0.1)")
    parser.add_argument("--tasks-per-month", type=int, default=10000, help="Task volume per month (default: 10000)")
    parser.add_argument("--input-cost-per-m", type=float, default=3.00, help="USD per 1M input tokens (default: 3.00, Claude-Sonnet-ish)")
    parser.add_argument("--output-cost-per-m", type=float, default=15.00, help="USD per 1M output tokens (default: 15.00, Claude-Sonnet-ish)")
    parser.add_argument("--sub-agent-fanout", type=float, default=0.0, help="Avg number of parallel sub-agent chains spawned per task (default: 0)")
    parser.add_argument("--step-latency-ms", type=float, default=DEFAULT_STEP_LATENCY_MS, help=f"Wall-clock ms per agentic step (default: {DEFAULT_STEP_LATENCY_MS:.0f})")
    parser.add_argument("--baseline-input-tokens", type=float, default=1500.0, help="Input tokens for the naive single-call baseline (default: 1500)")
    parser.add_argument("--baseline-output-tokens", type=float, default=500.0, help="Output tokens for the naive single-call baseline (default: 500)")
    parser.add_argument("--baseline-latency-ms", type=float, default=DEFAULT_BASELINE_LATENCY_MS, help=f"Wall-clock ms for the naive single-call baseline (default: {DEFAULT_BASELINE_LATENCY_MS:.0f})")
    parser.add_argument("--output", "-o", type=str, help="Write report to JSON file")
    args = parser.parse_args()

    if args.steps_per_task <= 0:
        print("Error: --steps-per-task must be > 0.", file=sys.stderr)
        return 1
    if args.tasks_per_month < 0:
        print("Error: --tasks-per-month must be >= 0.", file=sys.stderr)
        return 1
    if not (0 <= args.retry_rate < 10):
        print("Error: --retry-rate must be >= 0 (fraction, e.g. 0.1 = 10%).", file=sys.stderr)
        return 1

    result = simulate(
        steps_per_task=args.steps_per_task,
        input_tokens_per_step=args.input_tokens_per_step,
        output_tokens_per_step=args.output_tokens_per_step,
        retry_rate=args.retry_rate,
        sub_agent_fanout=args.sub_agent_fanout,
        tasks_per_month=args.tasks_per_month,
        input_cost_per_m=args.input_cost_per_m,
        output_cost_per_m=args.output_cost_per_m,
        step_latency_ms=args.step_latency_ms,
        baseline_input_tokens=args.baseline_input_tokens,
        baseline_output_tokens=args.baseline_output_tokens,
        baseline_latency_ms=args.baseline_latency_ms,
    )

    print_report(result)

    if args.output:
        with open(args.output, "w") as f:
            json.dump(toolkit_io.envelope(result, TOOL), f, indent=2)
        print(f"\n📁 Report saved to {args.output}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
