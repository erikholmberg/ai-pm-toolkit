#!/usr/bin/env python3
"""
Sprint Scope Checker

Check whether a draft sprint (CSV of candidate issues) fits team capacity.
Reports total points vs capacity, over/under, unestimated items, and
suggestions to add or remove work to hit a target. Use before committing
in Jira.

Usage:
    # Capacity 40 points, CSV of sprint candidates
    python sprint-scope-checker.py --csv sprint-candidates.csv --capacity 40

    # Target 38 (95% of capacity) to leave buffer
    python sprint-scope-checker.py --csv sprint-candidates.csv --capacity 40 --target 38

    # Custom story points column (Jira custom field)
    python sprint-scope-checker.py --csv sprint.csv --capacity 45 --points customfield_10016

    # Markdown and JSON output
    python sprint-scope-checker.py --csv sprint.csv --capacity 40 --markdown report.md --output report.json

CSV format (Jira export or similar):
    Key,Summary,Priority,Story Points,Assignee
    PROJ-101,Fix login bug,High,5,alice
    PROJ-102,Add SSO,Medium,8,bob
    PROJ-103,API docs,Low,,bob

    Required: Key, Story Points (or equivalent). Optional: Summary, Priority (for drop suggestions).

Requirements:
    None (stdlib only).
"""

import argparse
import csv
import json
import sys
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Column helper
# ---------------------------------------------------------------------------

def _col(fieldnames: List[str], *aliases: str) -> Optional[str]:
    lower_map = {f.lower().strip(): f for f in fieldnames}
    for alias in aliases:
        key = alias.lower().strip()
        if key in lower_map:
            return lower_map[key]
    return None


# Priority order for "what to drop first" (lowest first)
PRIORITY_ORDER = {"lowest": 0, "low": 1, "medium": 2, "high": 3, "highest": 4, "critical": 5}


def _priority_rank(p: str) -> int:
    return PRIORITY_ORDER.get(str(p).strip().lower(), 2)


# ---------------------------------------------------------------------------
# Load sprint candidates
# ---------------------------------------------------------------------------

def load_sprint_csv(
    path: str,
    id_col: str = "key",
    summary_col: str = "summary",
    points_col: str = "story points",
    priority_col: str = "priority",
) -> List[Dict[str, Any]]:
    """Load candidate issues from CSV."""
    rows: List[Dict[str, Any]] = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fields = reader.fieldnames or []

        c_id = _col(fields, id_col, "key", "id", "issue key")
        c_summary = _col(fields, summary_col, "summary", "title")
        c_points = _col(fields, points_col, "story points", "customfield_10016", "points", "estimate")
        c_priority = _col(fields, priority_col, "priority", "pri")

        for row in reader:
            key = (row.get(c_id or "key", "") or "").strip()
            if not key:
                key = f"row_{len(rows)+1}"

            raw_points = (row.get(c_points or "story points", "") or "").strip().replace(",", "")
            try:
                points = float(raw_points) if raw_points else None
            except ValueError:
                points = None

            if points is not None and points < 0:
                points = 0

            summary = (row.get(c_summary or "summary", "") or "").strip()
            priority = (row.get(c_priority or "priority", "") or "").strip() or "Medium"

            estimated = points is not None and (points > 0 or raw_points == "0")
            effective_points = (points or 0) if estimated else 0

            rows.append({
                "id": key,
                "summary": summary,
                "points": points,
                "effective_points": effective_points,
                "priority": priority,
                "estimated": estimated,
            })

    return rows


# ---------------------------------------------------------------------------
# Analyze scope
# ---------------------------------------------------------------------------

def check_scope(
    issues: List[Dict[str, Any]],
    capacity: float,
    target: Optional[float] = None,
) -> Dict[str, Any]:
    """Check sprint scope vs capacity; suggest add/remove to hit target."""
    if target is None:
        target = capacity

    total_points = sum(i["effective_points"] for i in issues)
    unestimated = [i for i in issues if not i["estimated"]]
    estimated_issues = [i for i in issues if i["estimated"]]

    gap = target - total_points  # positive = room for more, negative = over
    over = -gap if gap < 0 else 0
    under = gap if gap > 0 else 0

    # Suggestion: what to remove if over
    remove_suggestion: List[Dict[str, Any]] = []
    if over > 0 and estimated_issues:
        # Sort by priority (low first), then by points (small first) to minimize ticket count
        sorted_drop = sorted(
            estimated_issues,
            key=lambda x: (_priority_rank(x["priority"]), x["effective_points"]),
        )
        running = 0
        for i in sorted_drop:
            if running >= over:
                break
            remove_suggestion.append({
                "id": i["id"],
                "summary": (i.get("summary") or "—")[:50],
                "points": i["effective_points"],
                "priority": i.get("priority", "—"),
            })
            running += i["effective_points"]
    elif under > 0:
        remove_suggestion = []  # no drop suggestion

    utilization = round(total_points / capacity * 100, 1) if capacity > 0 else 0
    if utilization <= 85:
        health = "🟢 Under capacity — room for unplanned work"
    elif utilization <= 100:
        health = "🟡 At or near capacity"
    else:
        health = "🔴 Over capacity — consider moving items out"

    return {
        "total_issues": len(issues),
        "estimated_count": len(estimated_issues),
        "unestimated_count": len(unestimated),
        "unestimated_ids": [i["id"] for i in unestimated],
        "total_points": round(total_points, 1),
        "capacity": capacity,
        "target": target,
        "gap": round(gap, 1),
        "over": round(over, 1),
        "under": round(under, 1),
        "utilization_pct": utilization,
        "health": health,
        "remove_suggestion": remove_suggestion,
        "issues": issues,
    }


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def print_report(result: Dict[str, Any]) -> None:
    """Pretty-print sprint scope check."""
    if result.get("error"):
        print(f"\n   ⚠️  {result['error']}\n")
        return

    cap = result["capacity"]
    target = result["target"]
    total = result["total_points"]
    n = result["total_issues"]
    unest = result["unestimated_count"]

    print("\n" + "=" * 78)
    print("📌 SPRINT SCOPE CHECKER")
    print("=" * 78)

    print(f"\n   Capacity:      {cap:.0f} points")
    print(f"   Target:       {target:.0f} points")
    print(f"   Committed:    {total:.0f} points ({n} issues)")
    if unest > 0:
        print(f"   Unestimated:  {unest} issues — estimate before committing")
    print(f"   {result['health']}")

    bar_w = 35
    filled = min(35, int(total / cap * bar_w)) if cap > 0 else 0
    bar = "█" * filled + "░" * (bar_w - filled)
    print(f"\n   Utilization:   [{bar}] {result['utilization_pct']:.0f}%")

    gap = result["gap"]
    if gap > 0:
        print(f"\n   Room for:      {gap:.0f} more points (or reduce target)")
    elif gap < 0:
        print(f"\n   Over by:       {abs(gap):.0f} points — consider moving items out")

    if result.get("remove_suggestion"):
        print(f"\n{'─'*78}")
        print(f"\n   SUGGESTED REMOVALS (lowest priority / smallest first):\n")
        print(f"   {'Key':<14} {'Points':>7} {'Priority':<10} Summary")
        print(f"   {'─'*14} {'─'*7} {'─'*10} {'─'*36}")
        for r in result["remove_suggestion"][:10]:
            print(f"   {r['id']:<14} {r['points']:>7.0f} {r['priority']:<10} {r['summary'][:36]}")
        rem_pts = sum(r["points"] for r in result["remove_suggestion"])
        print(f"\n   Removing these would free ~{rem_pts:.0f} points")

    if result.get("unestimated_ids"):
        print(f"\n{'─'*78}")
        print(f"\n   UNESTIMATED (add story points before committing):\n")
        for uid in result["unestimated_ids"][:15]:
            print(f"   • {uid}")
        if len(result["unestimated_ids"]) > 15:
            print(f"   ... and {len(result['unestimated_ids']) - 15} more")

    print(f"\n{'─'*78}")
    print(f"\n   💡 Export from Jira: filter to sprint candidates, then Export CSV.")
    print(f"   Complements: capacity-planner, backlog-health-report, delivery-completion-forecaster")
    print("\n" + "=" * 78)


def generate_markdown(result: Dict[str, Any]) -> str:
    """Generate Markdown report."""
    if result.get("error"):
        return f"# Sprint Scope Check\n\n**Error:** {result['error']}\n"

    lines = []
    lines.append("# Sprint Scope Check")
    lines.append("")
    lines.append(f"**Capacity:** {result['capacity']:.0f} points  ")
    lines.append(f"**Target:** {result['target']:.0f} points  ")
    lines.append(f"**Committed:** {result['total_points']:.0f} points ({result['total_issues']} issues)  ")
    lines.append(f"**Status:** {result['health']}  ")
    lines.append("")

    if result.get("gap", 0) > 0:
        lines.append(f"Room for **{result['gap']:.0f}** more points.")
    elif result.get("gap", 0) < 0:
        lines.append(f"Over by **{abs(result['gap']):.0f}** points.")
    lines.append("")

    if result.get("remove_suggestion"):
        lines.append("## Suggested removals")
        lines.append("")
        for r in result["remove_suggestion"][:10]:
            lines.append(f"- **{r['id']}** ({r['points']:.0f} pts) — {r['summary']}")
        lines.append("")

    if result.get("unestimated_ids"):
        lines.append("## Unestimated issues")
        lines.append("")
        for uid in result["unestimated_ids"]:
            lines.append(f"- {uid}")
        lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Check if draft sprint (CSV) fits capacity. Over/under, "
                    "unestimated list, and suggestions to add or remove work.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --csv sprint-candidates.csv --capacity 40
  %(prog)s --csv sprint.csv --capacity 40 --target 38 --points customfield_10016
  %(prog)s --csv sprint.csv --capacity 45 --markdown report.md
        """,
    )

    parser.add_argument("--csv", "-c", type=str, required=True, help="CSV of sprint candidate issues")
    parser.add_argument("--capacity", type=float, required=True, help="Team capacity (story points per sprint)")
    parser.add_argument("--target", type=float, default=None,
                        help="Target commitment (default: capacity). e.g. 38 for 95%% buffer")
    parser.add_argument("--key", type=str, default="key", help="Issue key column")
    parser.add_argument("--summary", type=str, default="summary", help="Summary column")
    parser.add_argument("--points", type=str, default="story points",
                        help="Story points column (e.g. customfield_10016)")
    parser.add_argument("--priority", type=str, default="priority", help="Priority column")
    parser.add_argument("--markdown", type=str, help="Write Markdown report to file")
    parser.add_argument("--output", "-o", type=str, help="Write JSON results to file")
    args = parser.parse_args()

    try:
        issues = load_sprint_csv(
            args.csv,
            id_col=args.key,
            summary_col=args.summary,
            points_col=args.points,
            priority_col=args.priority,
        )
    except Exception as e:
        print(f"Error loading CSV: {e}", file=sys.stderr)
        return 1

    if not issues:
        print("No issues found in CSV.", file=sys.stderr)
        return 1

    target = args.target if args.target is not None else args.capacity
    result = check_scope(issues, capacity=args.capacity, target=target)
    print_report(result)

    if args.markdown:
        with open(args.markdown, "w", encoding="utf-8") as f:
            f.write(generate_markdown(result))
        print(f"\n📄 Markdown saved to {args.markdown}")

    if args.output and not result.get("error"):
        out = {k: v for k, v in result.items() if k != "issues"}
        out["unestimated_ids"] = result.get("unestimated_ids", [])
        out["remove_suggestion"] = result.get("remove_suggestion", [])
        with open(args.output, "w") as f:
            json.dump(out, f, indent=2)
        print(f"\n📁 Results saved to {args.output}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
