#!/usr/bin/env python3
"""
Agent Task Success Tracker

Track outcomes of AI agent (LLM agent / copilot) task runs: success rate,
escalation-to-human rate, failure rate, and steps-to-completion for
successes vs failures. PMs use this to spot which task categories an agent
handles reliably vs which need more guardrails, better tools, or a human
in the loop, before or after a wider rollout.

Reads a run log CSV (one row per agent run) and reports overall reliability,
a breakdown by category, and a trend over time if dates are present. Any
category or task below --target-success-rate is flagged for follow-up.

Usage:
    # From a run log
    python agent-task-success-tracker.py --csv runs.csv
    python agent-task-success-tracker.py --csv runs.csv --target-success-rate 0.9 --output report.json

    # Quick ad-hoc estimate without a CSV
    python agent-task-success-tracker.py --successes 340 --failures 45 --escalations 15 --avg-steps 6.2

CSV format (header row required):
    run_id,task,outcome,steps,duration_s,category,date
    r001,Reset user password,success,3,12.5,account_ops,2025-01-05
    r002,Summarize support thread,success,2,8.1,support,2025-01-05
    r003,Refund duplicate charge,escalated,5,40.2,billing,2025-01-06

    Required: task (or run_id), outcome (success|failure|escalated).
    Optional: steps, duration_s, category, date (enables trend + category views).

Requirements:
    None (stdlib only).
"""

import argparse
import csv
import json
import statistics
import sys
from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, List, Optional

# Shared result envelope (provenance + machine-readable chaining).
# See scripts/toolkit_io.py.
import toolkit_io

TOOL = "agent-task-success-tracker"


# ---------------------------------------------------------------------------
# Outcome normalization
# ---------------------------------------------------------------------------

OUTCOME_ALIASES = {
    "success": "success", "succeeded": "success", "ok": "success", "pass": "success", "passed": "success",
    "failure": "failure", "fail": "failure", "failed": "failure", "error": "failure",
    "escalated": "escalated", "escalation": "escalated", "handoff": "escalated", "human_handoff": "escalated",
}


def normalize_outcome(raw: str) -> Optional[str]:
    return OUTCOME_ALIASES.get((raw or "").strip().lower())


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def _col(fieldnames: List[str], *aliases: str) -> Optional[str]:
    lower_map = {f.lower().strip(): f for f in fieldnames}
    for alias in aliases:
        if alias.lower().strip() in lower_map:
            return lower_map[alias.lower().strip()]
    return None


def parse_date(s: str) -> Optional[datetime]:
    if not s or not str(s).strip():
        return None
    s = str(s).strip()
    for fmt, trim in [
        ("%Y-%m-%dT%H:%M:%S", 19),
        ("%Y-%m-%d %H:%M:%S", 19),
        ("%Y-%m-%d", 10),
        ("%Y/%m/%d", 10),
        ("%m/%d/%Y", 10),
    ]:
        try:
            return datetime.strptime(s[:trim].strip(), fmt)
        except ValueError:
            continue
    return None


def load_runs(path: str) -> List[Dict[str, Any]]:
    """Load agent run rows from CSV."""
    runs: List[Dict[str, Any]] = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fields = reader.fieldnames or []
        c_id = _col(fields, "run_id", "id", "run")
        c_task = _col(fields, "task", "task_name", "name")
        c_outcome = _col(fields, "outcome", "result", "status")
        c_steps = _col(fields, "steps", "num_steps", "steps_to_completion")
        c_duration = _col(fields, "duration_s", "duration", "duration_seconds", "latency_s")
        c_category = _col(fields, "category", "task_type", "type")
        c_date = _col(fields, "date", "created", "timestamp", "run_date")

        for i, row in enumerate(reader):
            outcome = normalize_outcome(row.get(c_outcome or "outcome", ""))
            if outcome is None:
                continue
            task = (row.get(c_task or "task", "") or "").strip()
            run_id = (row.get(c_id or "run_id", "") or "").strip() or f"run-{i + 1}"

            raw_steps = (row.get(c_steps or "steps", "") or "").strip()
            try:
                steps = float(raw_steps) if raw_steps else None
            except ValueError:
                steps = None

            raw_dur = (row.get(c_duration or "duration_s", "") or "").strip()
            try:
                duration = float(raw_dur) if raw_dur else None
            except ValueError:
                duration = None

            category = (row.get(c_category or "category", "") or "").strip() or "uncategorized"
            date_val = parse_date(row.get(c_date or "date", "")) if c_date else None

            runs.append({
                "run_id": run_id,
                "task": task or run_id,
                "outcome": outcome,
                "steps": steps,
                "duration_s": duration,
                "category": category,
                "date": date_val,
            })
    return runs


# ---------------------------------------------------------------------------
# Core calculations
# ---------------------------------------------------------------------------

def _rate_block(runs: List[Dict[str, Any]]) -> Dict[str, Any]:
    total = len(runs)
    successes = [r for r in runs if r["outcome"] == "success"]
    failures = [r for r in runs if r["outcome"] == "failure"]
    escalations = [r for r in runs if r["outcome"] == "escalated"]

    def steps_stats(rows: List[Dict[str, Any]]) -> Dict[str, Optional[float]]:
        vals = [r["steps"] for r in rows if r["steps"] is not None]
        if not vals:
            return {"avg": None, "median": None, "n": 0}
        return {"avg": round(statistics.mean(vals), 2), "median": round(statistics.median(vals), 2), "n": len(vals)}

    return {
        "total": total,
        "successes": len(successes),
        "failures": len(failures),
        "escalations": len(escalations),
        "success_rate": round(len(successes) / total, 4) if total else 0.0,
        "failure_rate": round(len(failures) / total, 4) if total else 0.0,
        "escalation_rate": round(len(escalations) / total, 4) if total else 0.0,
        "steps_success": steps_stats(successes),
        "steps_failure": steps_stats(failures),
    }


def analyze(runs: List[Dict[str, Any]], target_success_rate: float) -> Dict[str, Any]:
    """Compute overall stats, category breakdown, and trend over time."""
    overall = _rate_block(runs)

    by_category: Dict[str, Any] = {}
    cats = sorted({r["category"] for r in runs})
    for cat in cats:
        cat_runs = [r for r in runs if r["category"] == cat]
        block = _rate_block(cat_runs)
        block["flagged"] = block["success_rate"] < target_success_rate
        by_category[cat] = block

    # Trend by date (only if any date present)
    dated = [r for r in runs if r["date"] is not None]
    trend: List[Dict[str, Any]] = []
    if dated:
        by_day: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        for r in dated:
            by_day[r["date"].strftime("%Y-%m-%d")].append(r)
        for day in sorted(by_day):
            block = _rate_block(by_day[day])
            trend.append({"date": day, "total": block["total"], "success_rate": block["success_rate"]})

    # Worst tasks (need >=2 runs to be meaningful, else still show if only option)
    by_task: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for r in runs:
        by_task[r["task"]].append(r)
    task_rates = []
    for task, rows in by_task.items():
        block = _rate_block(rows)
        task_rates.append({"task": task, "total": block["total"], "success_rate": block["success_rate"]})
    task_rates.sort(key=lambda x: (x["success_rate"], -x["total"]))
    worst_tasks = [t for t in task_rates if t["success_rate"] < target_success_rate][:8]

    return {
        "overall": overall,
        "by_category": by_category,
        "trend": trend,
        "worst_tasks": worst_tasks,
        "target_success_rate": target_success_rate,
        "has_categories": len(cats) > 1 or (len(cats) == 1 and cats[0] != "uncategorized"),
        "has_dates": bool(dated),
    }


def adhoc_analyze(successes: int, failures: int, escalations: int, avg_steps: Optional[float], target_success_rate: float) -> Dict[str, Any]:
    """Build the same overall shape from summary counts (no per-run detail)."""
    total = successes + failures + escalations
    overall = {
        "total": total,
        "successes": successes,
        "failures": failures,
        "escalations": escalations,
        "success_rate": round(successes / total, 4) if total else 0.0,
        "failure_rate": round(failures / total, 4) if total else 0.0,
        "escalation_rate": round(escalations / total, 4) if total else 0.0,
        "steps_success": {"avg": avg_steps, "median": None, "n": None},
        "steps_failure": {"avg": None, "median": None, "n": None},
    }
    return {
        "overall": overall,
        "by_category": {},
        "trend": [],
        "worst_tasks": [],
        "target_success_rate": target_success_rate,
        "has_categories": False,
        "has_dates": False,
        "adhoc": True,
    }


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def _bar(value: float, width: int = 20) -> str:
    filled = int(max(0.0, min(1.0, value)) * width)
    return "█" * filled + "░" * (width - filled)


def _grade(rate: float, target: float) -> str:
    if rate >= target:
        return "🟢 On target"
    elif rate >= target - 0.1:
        return "🟡 Near target"
    else:
        return "🔴 Below target"


def print_report(result: Dict[str, Any]) -> None:
    print("\n" + "=" * 78)
    print("🤖 AGENT TASK SUCCESS TRACKER")
    print("=" * 78)

    o = result["overall"]
    target = result["target_success_rate"]

    print(f"\n📋 OVERVIEW:")
    print(f"   • Total runs:        {o['total']:,}")
    print(f"   • Successes:         {o['successes']:,}")
    print(f"   • Failures:          {o['failures']:,}")
    print(f"   • Escalated:         {o['escalations']:,}")
    print(f"   • Target success:    {target:.0%}")

    print(f"\n📈 OUTCOME RATES:")
    print(f"   Success     {_bar(o['success_rate'])} {o['success_rate']:>7.1%}  {_grade(o['success_rate'], target)}")
    print(f"   Failure     {_bar(o['failure_rate'])} {o['failure_rate']:>7.1%}")
    print(f"   Escalated   {_bar(o['escalation_rate'])} {o['escalation_rate']:>7.1%}")

    ss, sf = o["steps_success"], o["steps_failure"]
    if ss.get("avg") is not None or sf.get("avg") is not None:
        print(f"\n👣 STEPS TO COMPLETION:")
        print(f"   {'':<12} {'Avg':>8} {'Median':>8} {'n':>6}")
        if ss.get("avg") is not None:
            med = f"{ss['median']:.1f}" if ss.get("median") is not None else "—"
            n = ss.get("n") if ss.get("n") is not None else "—"
            print(f"   {'Success':<12} {ss['avg']:>8.1f} {med:>8} {str(n):>6}")
        if sf.get("avg") is not None:
            med = f"{sf['median']:.1f}" if sf.get("median") is not None else "—"
            n = sf.get("n") if sf.get("n") is not None else "—"
            print(f"   {'Failure':<12} {sf['avg']:>8.1f} {med:>8} {str(n):>6}")
        if ss.get("avg") is not None and sf.get("avg") is not None:
            if sf["avg"] > ss["avg"]:
                print(f"   💡 Failed runs take {sf['avg'] - ss['avg']:.1f} more steps on average — likely retry loops before giving up.")

    if result.get("has_categories") and result["by_category"]:
        print(f"\n📂 BY CATEGORY (sorted worst → best):")
        print(f"   {'Category':<20} {'Runs':>6} {'Success':>9} {'Escal.':>8} {'Fail':>7}  Grade")
        print(f"   {'─'*20} {'─'*6} {'─'*9} {'─'*8} {'─'*7}  {'─'*14}")
        cats_sorted = sorted(result["by_category"].items(), key=lambda kv: kv[1]["success_rate"])
        for cat, b in cats_sorted:
            print(
                f"   {cat[:20]:<20} {b['total']:>6} {b['success_rate']:>8.1%} "
                f"{b['escalation_rate']:>7.1%} {b['failure_rate']:>6.1%}  {_grade(b['success_rate'], target)}"
            )

    if result.get("worst_tasks"):
        print(f"\n⚠️  TASKS BELOW TARGET ({target:.0%}):")
        for t in result["worst_tasks"]:
            print(f"   • {t['task'][:50]:<50}  {t['success_rate']:>6.1%}  ({t['total']} run{'s' if t['total'] != 1 else ''})")

    if result.get("trend"):
        print(f"\n📅 TREND OVER TIME:")
        print(f"   {'Date':<12} {'Runs':>6}  Success rate")
        for t in result["trend"]:
            print(f"   {t['date']:<12} {t['total']:>6}  {_bar(t['success_rate'], 24)} {t['success_rate']:>6.1%}")

    print(f"\n💡 GUIDANCE:")
    if o["success_rate"] >= target:
        print(f"   • Overall success rate meets target ({target:.0%}). Monitor for drift as volume/task mix changes.")
    else:
        print(f"   • Overall success rate is below target. Prioritize the flagged categories/tasks above.")
    if o["escalation_rate"] > 0.15:
        print(f"   • Escalation rate is high ({o['escalation_rate']:.0%}) — consider this a signal to expand tool/context coverage, not just a safety net.")
    if o["failure_rate"] > 0.1:
        print(f"   • Failure rate above 10% — silent failures (no escalation, no success) are the riskiest outcome; verify they're logged and reviewed.")

    print("\n" + "=" * 78)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Track AI agent task outcomes: success rate, escalation rate, "
                    "failure rate, and steps-to-completion, from a run log or ad-hoc counts.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --csv runs.csv
  %(prog)s --csv runs.csv --target-success-rate 0.9 --output report.json
  %(prog)s --successes 340 --failures 45 --escalations 15 --avg-steps 6.2
        """,
    )
    parser.add_argument("--csv", "-c", type=str, help="CSV file with agent run log")
    parser.add_argument("--target-success-rate", type=float, default=0.85, help="Flag categories/tasks below this rate (default: 0.85)")

    adhoc = parser.add_argument_group("ad-hoc mode (no CSV)")
    adhoc.add_argument("--successes", type=int, help="Number of successful runs")
    adhoc.add_argument("--failures", type=int, help="Number of failed runs")
    adhoc.add_argument("--escalations", type=int, help="Number of escalated-to-human runs")
    adhoc.add_argument("--avg-steps", type=float, help="Average steps to completion (successes)")

    parser.add_argument("--output", "-o", type=str, help="Write report to JSON file")
    args = parser.parse_args()

    if args.csv:
        try:
            runs = load_runs(args.csv)
        except FileNotFoundError:
            print(f"Error: file not found: {args.csv}", file=sys.stderr)
            return 1
        except Exception as e:
            print(f"Error loading CSV: {e}", file=sys.stderr)
            return 1
        if not runs:
            print("Error: no valid runs found in CSV (need outcome column with success/failure/escalated).", file=sys.stderr)
            return 1
        result = analyze(runs, args.target_success_rate)
    elif args.successes is not None or args.failures is not None or args.escalations is not None:
        for flag, val in (("--successes", args.successes), ("--failures", args.failures), ("--escalations", args.escalations)):
            if val is not None and val < 0:
                print(f"Error: {flag} must be >= 0.", file=sys.stderr)
                return 1
        if args.avg_steps is not None and args.avg_steps < 0:
            print("Error: --avg-steps must be >= 0.", file=sys.stderr)
            return 1
        result = adhoc_analyze(
            successes=args.successes or 0,
            failures=args.failures or 0,
            escalations=args.escalations or 0,
            avg_steps=args.avg_steps,
            target_success_rate=args.target_success_rate,
        )
        if result["overall"]["total"] == 0:
            print("Error: ad-hoc mode requires at least one of --successes/--failures/--escalations > 0.", file=sys.stderr)
            return 1
    else:
        print("Error: provide --csv or ad-hoc counts (--successes/--failures/--escalations).", file=sys.stderr)
        parser.print_help(sys.stderr)
        return 1

    print_report(result)

    if args.output:
        with open(args.output, "w") as f:
            json.dump(toolkit_io.envelope(result, TOOL), f, indent=2, default=str)
        print(f"\n📁 Report saved to {args.output}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
