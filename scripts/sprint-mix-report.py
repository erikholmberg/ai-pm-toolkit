#!/usr/bin/env python3
"""
Sprint Mix Report

Break down a sprint (or backlog) by type, priority, assignee, or custom column.
Reports count and story points per group with percentages. Use to check
balance (e.g. bugs vs features, load per person).

Usage:
    # By issue type (default)
    python sprint-mix-report.py --csv sprint.csv

    # By priority or assignee
    python sprint-mix-report.py --csv sprint.csv --group-by priority
    python sprint-mix-report.py --csv sprint.csv --group-by assignee

    # Custom column (e.g. component, team)
    python sprint-mix-report.py --csv sprint.csv --group-by component

    # Export
    python sprint-mix-report.py --csv sprint.csv --markdown report.md --output report.json

CSV format (Jira export or similar):
    Key,Summary,Issue Type,Story Points,Priority,Assignee
    PROJ-101,Fix login bug,Bug,5,High,alice
    PROJ-102,Add SSO,Story,8,Medium,bob
    PROJ-103,API docs,Task,3,Low,bob

    Required: at least Key (or id). Optional: Story Points, Issue Type, Priority, Assignee.
    Use --group-by to choose which column drives the mix (default: type).

Requirements:
    None (stdlib only).
"""

import argparse
import csv
import json
import sys
from collections import defaultdict
from typing import Any, Dict, List, Optional


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


# ---------------------------------------------------------------------------
# Load sprint CSV
# ---------------------------------------------------------------------------

def load_sprint_csv(
    path: str,
    id_col: str = "key",
    points_col: str = "story points",
) -> List[Dict[str, Any]]:
    """Load sprint issues from CSV; normalize points and group value."""
    rows: List[Dict[str, Any]] = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fields = reader.fieldnames or []

        c_id = _col(fields, id_col, "key", "id", "issue key")
        c_points = _col(
            fields,
            points_col,
            "story points",
            "customfield_10016",
            "points",
            "estimate",
        )
        # Group columns (resolved per --group-by in main)
        c_type = _col(fields, "issue type", "type", "issuetype", "issue type")
        c_priority = _col(fields, "priority", "pri")
        c_assignee = _col(fields, "assignee", "owner")
        c_component = _col(fields, "component", "components")

        for row in reader:
            key = (row.get(c_id or "key", "") or "").strip()
            if not key:
                key = f"row_{len(rows) + 1}"

            raw_points = (row.get(c_points or "story points", "") or "").strip().replace(",", "")
            try:
                points = float(raw_points) if raw_points else None
            except ValueError:
                points = None
            if points is not None and points < 0:
                points = 0
            effective_points = (points or 0) if (points is not None and raw_points != "") else 0

            rows.append({
                "id": key,
                "points": points,
                "effective_points": effective_points,
                "type": (row.get(c_type or "issue type", "") or "").strip() or "—",
                "priority": (row.get(c_priority or "priority", "") or "").strip() or "—",
                "assignee": (row.get(c_assignee or "assignee", "") or "").strip() or "Unassigned",
                "component": (row.get(c_component or "component", "") or "").strip() or "—",
                "raw": row,
            })

    return rows


def get_group_value(issue: Dict[str, Any], group_by: str, fieldnames: List[str]) -> str:
    """Resolve group label for an issue from group_by (type, priority, assignee, or custom)."""
    if group_by.lower() in ("type", "issue type", "issuetype"):
        return issue.get("type", "—") or "—"
    if group_by.lower() in ("priority", "pri"):
        return issue.get("priority", "—") or "—"
    if group_by.lower() in ("assignee", "owner"):
        return issue.get("assignee", "Unassigned") or "Unassigned"
    if group_by.lower() in ("component", "components"):
        return issue.get("component", "—") or "—"
    # Custom column from raw row
    raw = issue.get("raw", {})
    col = _col(fieldnames, group_by)
    if col and col in raw:
        return (raw.get(col) or "").strip() or "—"
    return "—"


# ---------------------------------------------------------------------------
# Mix analysis
# ---------------------------------------------------------------------------

def compute_mix(
    issues: List[Dict[str, Any]],
    group_by: str,
    fieldnames: List[str],
) -> Dict[str, Any]:
    """Aggregate by group: count, points, and percentages."""
    groups: Dict[str, Dict[str, Any]] = defaultdict(lambda: {"count": 0, "points": 0.0})
    for i in issues:
        label = get_group_value(i, group_by, fieldnames)
        groups[label]["count"] += 1
        groups[label]["points"] += i.get("effective_points", 0) or 0

    total_count = len(issues)
    total_points = sum(i.get("effective_points", 0) or 0 for i in issues)

    mix = []
    for label, g in sorted(groups.items()):
        pct_count = round(g["count"] / total_count * 100, 1) if total_count else 0
        pct_points = round(g["points"] / total_points * 100, 1) if total_points else 0
        mix.append({
            "label": label,
            "count": g["count"],
            "points": round(g["points"], 1),
            "pct_count": pct_count,
            "pct_points": pct_points,
        })

    return {
        "group_by": group_by,
        "total_issues": total_count,
        "total_points": round(total_points, 1),
        "mix": mix,
    }


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def _bar(pct: float, width: int = 20) -> str:
    if pct <= 0:
        return "░" * width
    filled = min(width, max(0, int(round(pct / 100 * width))))
    return "█" * filled + "░" * (width - filled)


def print_report(result: Dict[str, Any], chart: bool = False) -> None:
    """Pretty-print sprint mix."""
    print("\n" + "=" * 70)
    print("📊 SPRINT MIX REPORT")
    print("=" * 70)

    total_n = result["total_issues"]
    total_pts = result["total_points"]
    group_by = result["group_by"]
    mix = result.get("mix", [])

    print(f"\n   Group by:     {group_by}")
    print(f"   Total:        {total_n} issues, {total_pts:.0f} points")
    print(f"\n   {'Group':<18} {'Count':>6} {'Points':>8} {'%Count':>8} {'%Pts':>8}")
    print("   " + "─" * 54)
    for row in mix:
        print(f"   {row['label'][:17]:<18} {row['count']:>6} {row['points']:>8.1f} {row['pct_count']:>7.1f}% {row['pct_points']:>7.1f}%")

    if chart and mix:
        print(f"\n   Mix by points:")
        max_pts = max(r["points"] for r in mix) or 1
        for row in mix:
            bar = _bar(row["pct_points"], 25)
            print(f"   {row['label'][:14]:<15} {bar} {row['pct_points']:.0f}%")

    print()


def to_json_result(result: Dict[str, Any]) -> Dict[str, Any]:
    """JSON-serializable result."""
    return {
        "group_by": result["group_by"],
        "total_issues": result["total_issues"],
        "total_points": result["total_points"],
        "mix": result.get("mix", []),
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Report sprint mix by type, priority, assignee, or custom column.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--csv", "-c", required=True, help="Path to sprint CSV (e.g. Jira export)")
    parser.add_argument(
        "--group-by", "-g",
        default="type",
        help="Column to group by: type (default), priority, assignee, or column name",
    )
    parser.add_argument("--points", default="story points", help="Story points column name")
    parser.add_argument("--chart", action="store_true", help="Print bar chart by points %%")
    parser.add_argument("--markdown", metavar="FILE", help="Write Markdown report to FILE")
    parser.add_argument("--output", "-o", metavar="FILE", help="Write JSON result to FILE")
    args = parser.parse_args()

    # Need fieldnames for custom group-by
    fieldnames: List[str] = []
    with open(args.csv, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames or [])

    issues = load_sprint_csv(args.csv, points_col=args.points)
    if not issues:
        print("No issues in CSV.", file=sys.stderr)
        return 1

    result = compute_mix(issues, args.group_by, fieldnames)
    print_report(result, chart=args.chart)

    if args.markdown:
        with open(args.markdown, "w", encoding="utf-8") as f:
            f.write("# Sprint Mix Report\n\n")
            f.write(f"- **Group by:** {result['group_by']}\n")
            f.write(f"- **Total:** {result['total_issues']} issues, {result['total_points']} points\n\n")
            f.write("| Group | Count | Points | % Count | % Points |\n")
            f.write("|-------|-------|--------|---------|----------|\n")
            for row in result.get("mix", []):
                f.write(f"| {row['label']} | {row['count']} | {row['points']} | {row['pct_count']}% | {row['pct_points']}% |\n")
        print(f"Wrote Markdown to {args.markdown}")

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(to_json_result(result), f, indent=2)
        print(f"Wrote JSON to {args.output}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
