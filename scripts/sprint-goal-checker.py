#!/usr/bin/env python3
"""
Sprint Goal / Outcome Checker

Map completed work to sprint goals and report which goals were met, partial,
or missed. Use after sprint review to answer "did we meet our goals?"

Usage:
    # Goals CSV + completed issues CSV (e.g. sprint export with Key column)
    python sprint-goal-checker.py --goals goals.csv --completed done.csv

    # Inline done keys (comma-separated)
    python sprint-goal-checker.py --goals goals.csv --done-keys "PROJ-101,PROJ-102,PROJ-103"

    # Export
    python sprint-goal-checker.py --goals goals.csv --completed done.csv --markdown report.md --output report.json

Goals CSV format:
    goal,issue_keys
    Ship login fix,PROJ-101 PROJ-102
    Improve API docs,PROJ-103

    Required: goal (or goal_id), issue_keys (space or comma separated).
    Optional: description.

Completed CSV format (sprint export or similar):
    Key,Summary,Status
    PROJ-101,Fix login,Done
    PROJ-102,Add test,Done

    Any row in this file is considered "done"; Key (or id) column required.
    Alternatively use --done-keys "K1,K2,K3" instead of --completed.

Requirements:
    None (stdlib only).
"""

import argparse
import csv
import json
import re
import sys
from typing import Any, Dict, List, Optional, Set


# ---------------------------------------------------------------------------
# Column helper
# ---------------------------------------------------------------------------

def _col(fieldnames: List[str], *aliases: str) -> Optional[str]:
    lower_map = {f.lower().strip(): f for f in fieldnames}
    for alias in aliases:
        if alias.lower().strip() in lower_map:
            return lower_map[alias.lower().strip()]
    return None


def _parse_keys(raw: str) -> List[str]:
    """Parse comma- or space-separated issue keys; normalize and dedupe order."""
    if not raw or not str(raw).strip():
        return []
    # Split on comma or whitespace, strip, keep non-empty
    parts = re.split(r"[\s,]+", str(raw).strip())
    return [p.strip().upper() for p in parts if p.strip()]


# ---------------------------------------------------------------------------
# Load goals and completed set
# ---------------------------------------------------------------------------

def load_goals(path: str) -> List[Dict[str, Any]]:
    """Load goals CSV: goal (or goal_id), issue_keys."""
    rows: List[Dict[str, Any]] = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fields = reader.fieldnames or []

        c_goal = _col(fields, "goal", "goal_id", "objective", "name", "title")
        c_keys = _col(fields, "issue_keys", "keys", "issues", "linked_issues", "key")

        for row in reader:
            goal_text = (row.get(c_goal or "goal", "") or "").strip()
            raw_keys = row.get(c_keys or "issue_keys", "") or ""
            keys = _parse_keys(raw_keys)
            if not goal_text:
                goal_text = f"Goal {len(rows) + 1}"
            rows.append({"goal": goal_text, "issue_keys": keys})
    return rows


def load_completed_keys(path: str) -> Set[str]:
    """Load set of issue keys from a CSV (e.g. sprint export); all rows = done."""
    keys: Set[str] = set()
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fields = reader.fieldnames or []

        c_id = _col(fields, "key", "id", "issue key", "issue_key", "issue key")

        for row in reader:
            key = (row.get(c_id or "key", "") or "").strip()
            if key:
                keys.add(key.upper())
    return keys


def parse_done_keys(done_keys_str: str) -> Set[str]:
    """Parse --done-keys 'K1,K2,K3' into set of uppercase keys."""
    return {k.upper() for k in _parse_keys(done_keys_str)}


# ---------------------------------------------------------------------------
# Analyze goal outcome
# ---------------------------------------------------------------------------

def analyze_goals(
    goals: List[Dict[str, Any]],
    completed: Set[str],
) -> Dict[str, Any]:
    """For each goal, compute done count and status (met / partial / missed)."""
    results: List[Dict[str, Any]] = []
    met = 0
    partial = 0
    missed = 0

    for g in goals:
        keys = g["issue_keys"]
        total = len(keys)
        done_count = sum(1 for k in keys if k.upper() in completed) if keys else 0

        if total == 0:
            status = "missed"
            missed += 1
        elif done_count == total:
            status = "met"
            met += 1
        elif done_count > 0:
            status = "partial"
            partial += 1
        else:
            status = "missed"
            missed += 1

        results.append({
            "goal": g["goal"],
            "total_keys": total,
            "done_count": done_count,
            "status": status,
        })

    total_goals = len(goals)
    pct_met = round(met / total_goals * 100, 1) if total_goals else 0

    return {
        "goals": results,
        "goals_met": met,
        "goals_partial": partial,
        "goals_missed": missed,
        "total_goals": total_goals,
        "pct_met": pct_met,
        "completed_key_count": len(completed),
    }


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def print_report(result: Dict[str, Any]) -> None:
    """Pretty-print goal outcome report."""
    print("\n" + "=" * 70)
    print("🎯 SPRINT GOAL CHECKER")
    print("=" * 70)

    goals = result.get("goals", [])
    if not goals:
        print("\n   No goals to report.\n")
        return

    total = result["total_goals"]
    met = result["goals_met"]
    partial = result["goals_partial"]
    missed = result["goals_missed"]

    print(f"\n   Summary:  {met} met  |  {partial} partial  |  {missed} missed  ({total} goals)")
    print(f"   Goals met: {result['pct_met']:.0f}%")
    print(f"   Completed issues in set: {result['completed_key_count']}")

    print(f"\n   {'Goal':<36} {'Keys':>6} {'Done':>6}  Status")
    print("   " + "─" * 58)
    for r in goals:
        goal_short = (r["goal"][:35] + "…") if len(r["goal"]) > 35 else r["goal"]
        print(f"   {goal_short:<36} {r['total_keys']:>6} {r['done_count']:>6}  {r['status']}")

    print("\n   💡 met = all linked issues done; partial = some; missed = none.\n")


def to_json_result(result: Dict[str, Any]) -> Dict[str, Any]:
    """JSON-serializable result."""
    return {
        "goals": result.get("goals", []),
        "goals_met": result.get("goals_met", 0),
        "goals_partial": result.get("goals_partial", 0),
        "goals_missed": result.get("goals_missed", 0),
        "total_goals": result.get("total_goals", 0),
        "pct_met": result.get("pct_met", 0),
        "completed_key_count": result.get("completed_key_count", 0),
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Check sprint goals against completed work (met / partial / missed).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--goals", "-g", required=True, help="CSV of goals and issue_keys")
    parser.add_argument("--completed", "-c", help="CSV of completed issues (Key column = done)")
    parser.add_argument("--done-keys", type=str, metavar="K1,K2,...", help="Comma-separated list of done issue keys (alternative to --completed)")
    parser.add_argument("--markdown", metavar="FILE", help="Write Markdown report to FILE")
    parser.add_argument("--output", "-o", metavar="FILE", help="Write JSON result to FILE")
    args = parser.parse_args()

    goals = load_goals(args.goals)
    if not goals:
        print("No goals in CSV.", file=sys.stderr)
        return 1

    completed: Set[str] = set()
    if args.completed:
        completed = load_completed_keys(args.completed)
    if args.done_keys:
        completed |= parse_done_keys(args.done_keys)
    if not args.completed and not args.done_keys:
        print("Provide --completed CSV or --done-keys.", file=sys.stderr)
        return 1
    if not completed:
        print("No completed issues found. Ensure --completed CSV has data rows or provide --done-keys with at least one key.", file=sys.stderr)
        return 1

    result = analyze_goals(goals, completed)
    print_report(result)

    if args.markdown:
        with open(args.markdown, "w", encoding="utf-8") as f:
            f.write("# Sprint Goal Outcome\n\n")
            f.write(f"- **Goals met:** {result['goals_met']} / {result['total_goals']} ({result['pct_met']}%)\n")
            f.write(f"- **Partial:** {result['goals_partial']}  |  **Missed:** {result['goals_missed']}\n\n")
            f.write("| Goal | Keys | Done | Status |\n")
            f.write("|------|------|------|--------|\n")
            for r in result.get("goals", []):
                goal_esc = r["goal"].replace("|", "\\|")[:50]
                f.write(f"| {goal_esc} | {r['total_keys']} | {r['done_count']} | {r['status']} |\n")
        print(f"Wrote Markdown to {args.markdown}")

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(to_json_result(result), f, indent=2)
        print(f"Wrote JSON to {args.output}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
