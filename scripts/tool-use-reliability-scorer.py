#!/usr/bin/env python3
"""
Tool-Use Reliability Scorer

Score the reliability of individual tools/functions an AI agent calls
(web search, code execution, database queries, internal APIs, etc.) from a
call log. PMs use this to decide which tools need retries, timeouts,
fallbacks, or removal from an agent's toolset before they erode overall
task success.

Reads a CSV of tool calls and reports, per tool: call volume, success rate,
retry rate, timeout rate, and average latency — sorted worst to best so the
riskiest tools surface first.

Usage:
    python tool-use-reliability-scorer.py --csv tool_calls.csv
    python tool-use-reliability-scorer.py --csv tool_calls.csv --min-reliability 0.98
    python tool-use-reliability-scorer.py --csv tool_calls.csv --output report.json

CSV format (header row required):
    tool_name,status,retries,latency_ms
    web_search,success,0,820
    code_interpreter,error,1,1450
    database_query,timeout,2,5000

    Required: tool_name, status (success|error|timeout).
    Optional: retries, latency_ms.

Requirements:
    None (stdlib only).
"""

import argparse
import csv
import json
import statistics
import sys
from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Status normalization
# ---------------------------------------------------------------------------

STATUS_ALIASES = {
    "success": "success", "ok": "success", "succeeded": "success", "200": "success",
    "error": "error", "fail": "error", "failed": "error", "failure": "error", "exception": "error",
    "timeout": "timeout", "timed_out": "timeout", "timed out": "timeout",
}


def normalize_status(raw: str) -> Optional[str]:
    return STATUS_ALIASES.get((raw or "").strip().lower())


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def _col(fieldnames: List[str], *aliases: str) -> Optional[str]:
    lower_map = {f.lower().strip(): f for f in fieldnames}
    for alias in aliases:
        if alias.lower().strip() in lower_map:
            return lower_map[alias.lower().strip()]
    return None


def load_calls(path: str) -> Tuple[List[Dict[str, Any]], Dict[str, int]]:
    """Load tool call rows from CSV. Returns (calls, skip_reasons) so callers
    can warn about rows silently dropped for an unrecognized status — an
    empty CSV column value ("") is skipped without complaint, but a value
    that doesn't match a known status alias (e.g. "pending") is a data
    problem worth surfacing, not swallowing."""
    calls: List[Dict[str, Any]] = []
    skipped_no_tool = 0
    skipped_bad_status: Dict[str, int] = {}
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fields = reader.fieldnames or []
        c_tool = _col(fields, "tool_name", "tool", "function", "name")
        c_status = _col(fields, "status", "outcome", "result")
        c_retries = _col(fields, "retries", "retry_count", "num_retries")
        c_latency = _col(fields, "latency_ms", "latency", "duration_ms", "response_time_ms")

        for row in reader:
            tool = (row.get(c_tool or "tool_name", "") or "").strip()
            raw_status = (row.get(c_status or "status", "") or "").strip()
            status = normalize_status(raw_status)
            if not tool:
                skipped_no_tool += 1
                continue
            if status is None:
                if raw_status:
                    skipped_bad_status[raw_status] = skipped_bad_status.get(raw_status, 0) + 1
                else:
                    skipped_no_tool += 1
                continue

            raw_retries = (row.get(c_retries or "retries", "") or "").strip()
            try:
                retries = int(float(raw_retries)) if raw_retries else 0
            except ValueError:
                retries = 0

            raw_latency = (row.get(c_latency or "latency_ms", "") or "").strip()
            try:
                latency = float(raw_latency) if raw_latency else None
            except ValueError:
                latency = None

            calls.append({"tool": tool, "status": status, "retries": max(0, retries), "latency_ms": latency})
    return calls, {"no_tool_or_status": skipped_no_tool, **{f"unrecognized status '{k}'": v for k, v in skipped_bad_status.items()}}


# ---------------------------------------------------------------------------
# Core calculations
# ---------------------------------------------------------------------------

def score_tools(calls: List[Dict[str, Any]], min_reliability: float) -> List[Dict[str, Any]]:
    """Compute per-tool reliability stats, sorted worst to best."""
    by_tool: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for c in calls:
        by_tool[c["tool"]].append(c)

    results: List[Dict[str, Any]] = []
    for tool, rows in by_tool.items():
        n = len(rows)
        successes = sum(1 for r in rows if r["status"] == "success")
        errors = sum(1 for r in rows if r["status"] == "error")
        timeouts = sum(1 for r in rows if r["status"] == "timeout")
        retried = sum(1 for r in rows if r["retries"] > 0)
        total_retries = sum(r["retries"] for r in rows)
        latencies = [r["latency_ms"] for r in rows if r["latency_ms"] is not None]

        success_rate = successes / n if n else 0.0
        results.append({
            "tool": tool,
            "calls": n,
            "successes": successes,
            "errors": errors,
            "timeouts": timeouts,
            "success_rate": round(success_rate, 4),
            "error_rate": round(errors / n, 4) if n else 0.0,
            "timeout_rate": round(timeouts / n, 4) if n else 0.0,
            "retry_rate": round(retried / n, 4) if n else 0.0,
            "avg_retries": round(total_retries / n, 2) if n else 0.0,
            "avg_latency_ms": round(statistics.mean(latencies), 1) if latencies else None,
            "p95_latency_ms": round(sorted(latencies)[int(0.95 * (len(latencies) - 1))], 1) if len(latencies) >= 2 else (latencies[0] if latencies else None),
            "unreliable": success_rate < min_reliability,
        })

    results.sort(key=lambda r: r["success_rate"])
    return results


def summarize(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    total_calls = sum(r["calls"] for r in results)
    total_successes = sum(r["successes"] for r in results)
    unreliable = [r for r in results if r["unreliable"]]
    return {
        "total_tools": len(results),
        "total_calls": total_calls,
        "overall_success_rate": round(total_successes / total_calls, 4) if total_calls else 0.0,
        "unreliable_count": len(unreliable),
    }


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def _bar(value: float, width: int = 18) -> str:
    filled = int(max(0.0, min(1.0, value)) * width)
    return "█" * filled + "░" * (width - filled)


def _grade(rate: float, min_reliability: float) -> str:
    if rate >= min_reliability:
        return "🟢 Reliable"
    elif rate >= min_reliability - 0.1:
        return "🟡 Marginal"
    else:
        return "🔴 Unreliable"


def print_report(results: List[Dict[str, Any]], summary: Dict[str, Any], min_reliability: float) -> None:
    print("\n" + "=" * 78)
    print("🛠️  TOOL-USE RELIABILITY SCORER")
    print("=" * 78)

    print(f"\n📋 OVERVIEW:")
    print(f"   • Tools analyzed:       {summary['total_tools']}")
    print(f"   • Total calls:          {summary['total_calls']:,}")
    print(f"   • Overall success rate: {summary['overall_success_rate']:.1%}")
    print(f"   • Reliability threshold: {min_reliability:.0%}")
    print(f"   • Flagged unreliable:   {summary['unreliable_count']}")

    print(f"\n📈 PER-TOOL RELIABILITY (worst → best):\n")
    print(f"   {'Tool':<24} {'Calls':>6} {'Success':>9} {'Retry':>7} {'Timeout':>8} {'Avg lat.':>10}  Grade")
    print(f"   {'─'*24} {'─'*6} {'─'*9} {'─'*7} {'─'*8} {'─'*10}  {'─'*13}")
    for r in results:
        lat = f"{r['avg_latency_ms']:.0f}ms" if r["avg_latency_ms"] is not None else "—"
        print(
            f"   {r['tool'][:24]:<24} {r['calls']:>6} {r['success_rate']:>8.1%} "
            f"{r['retry_rate']:>6.1%} {r['timeout_rate']:>7.1%} {lat:>10}  {_grade(r['success_rate'], min_reliability)}"
        )

    print(f"\n📊 SUCCESS RATE DISTRIBUTION:")
    for r in results:
        print(f"   {r['tool'][:22]:<22} {_bar(r['success_rate'])} {r['success_rate']:>6.1%}")

    unreliable = [r for r in results if r["unreliable"]]
    if unreliable:
        print(f"\n⚠️  UNRELIABLE TOOLS (below {min_reliability:.0%} success rate) — consider guardrails or fallback:")
        for r in unreliable:
            reasons = []
            if r["timeout_rate"] > 0.1:
                reasons.append(f"high timeout rate ({r['timeout_rate']:.0%})")
            if r["retry_rate"] > 0.3:
                reasons.append(f"heavy retry usage ({r['retry_rate']:.0%} of calls)")
            if r["error_rate"] > 0.15:
                reasons.append(f"high error rate ({r['error_rate']:.0%})")
            reason_str = f" — {', '.join(reasons)}" if reasons else ""
            print(f"   🔴 {r['tool']}: {r['success_rate']:.1%} success over {r['calls']} calls{reason_str}")
            if r["timeout_rate"] > 0.1:
                print(f"      → Add a stricter timeout + fallback path or async retry queue")
            if r["error_rate"] > 0.15 and r["timeout_rate"] <= 0.1:
                print(f"      → Add input validation, wrap in try/except with a fallback tool, or gate behind a confirmation step")
    else:
        print(f"\n✅ All tools meet the {min_reliability:.0%} reliability threshold.")

    print(f"\n💡 GUIDANCE:")
    print(f"   • Tools with high retry rate but eventual success may be masking upstream flakiness — cheap to fix, easy to miss.")
    print(f"   • Timeout-heavy tools often benefit more from a shorter timeout + fast fallback than from more retries.")
    print(f"   • Re-run this after any guardrail change to confirm the fix moved the success rate, not just papered over symptoms.")

    print("\n" + "=" * 78)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Score reliability of individual tools an AI agent calls: success rate, "
                    "retry rate, timeout rate, and latency, from a tool call log.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --csv tool_calls.csv
  %(prog)s --csv tool_calls.csv --min-reliability 0.98
  %(prog)s --csv tool_calls.csv --output report.json
        """,
    )
    parser.add_argument("--csv", "-c", type=str, required=True, help="CSV file with tool call log")
    parser.add_argument("--min-reliability", type=float, default=0.95, help="Success rate threshold below which a tool is flagged unreliable (default: 0.95)")
    parser.add_argument("--output", "-o", type=str, help="Write report to JSON file")
    args = parser.parse_args()

    try:
        calls, skipped = load_calls(args.csv)
    except FileNotFoundError:
        print(f"Error: file not found: {args.csv}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error loading CSV: {e}", file=sys.stderr)
        return 1

    if not calls:
        print("Error: no valid tool calls found in CSV (need tool_name and status columns).", file=sys.stderr)
        return 1

    for reason, count in skipped.items():
        if count:
            print(f"Warning: skipped {count} row(s) — {reason}.", file=sys.stderr)

    results = score_tools(calls, args.min_reliability)
    summary = summarize(results)
    print_report(results, summary, args.min_reliability)

    if args.output:
        with open(args.output, "w") as f:
            json.dump({"summary": summary, "tools": results, "min_reliability": args.min_reliability}, f, indent=2)
        print(f"\n📁 Report saved to {args.output}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
