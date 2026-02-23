#!/usr/bin/env python3
"""
Stakeholder RACI Matrix Generator

Generate and validate RACI (Responsible, Accountable, Consulted, Informed)
matrices for projects. Detects common anti-patterns:
    - Tasks with no Accountable owner
    - Tasks with multiple Accountable owners
    - Stakeholders overloaded with R/A roles
    - Stakeholders with no involvement
    - Gaps (tasks with no assignments)

Usage:
    # Inline assignments
    python raci-matrix.py \\
        --task "Design specs" --assign "Design specs:PM:A,Eng Lead:R,Designer:R,QA:I" \\
        --task "Implementation" --assign "Implementation:Eng Lead:A,Dev Team:R,PM:I,QA:C" \\
        --task "Testing" --assign "Testing:QA:A,QA:R,Dev Team:C,PM:I" \\
        --task "Launch" --assign "Launch:PM:A,Eng Lead:R,Marketing:R,QA:I"

    # From CSV
    python raci-matrix.py --csv raci.csv

    # From JSON
    python raci-matrix.py --json raci.json

CSV format (matrix-style — stakeholders as columns):
    task,PM,Eng Lead,Designer,QA,Marketing
    Design specs,A,R,R,I,
    Implementation,I,A,,C,
    Testing,I,,C,A/R,
    Launch,A,R,,I,R

    Cell values: R, A, C, I, or combinations like A/R

JSON format:
    {
      "stakeholders": ["PM", "Eng Lead", "Designer", "QA", "Marketing"],
      "tasks": [
        {
          "name": "Design specs",
          "assignments": {"PM": "A", "Eng Lead": "R", "Designer": "R", "QA": "I"}
        },
        {
          "name": "Implementation",
          "assignments": {"Eng Lead": "A", "Dev Team": "R", "PM": "I", "QA": "C"}
        }
      ]
    }

Requirements:
    None (stdlib only).
"""

import argparse
import csv
import json
import sys
from typing import Any, Dict, List, Optional, Set, Tuple


# ---------------------------------------------------------------------------
# RACI model
# ---------------------------------------------------------------------------

VALID_ROLES = {"R", "A", "C", "I"}
ROLE_NAMES = {"R": "Responsible", "A": "Accountable", "C": "Consulted", "I": "Informed"}
ROLE_EMOJI = {"R": "🔨", "A": "👤", "C": "💬", "I": "📩"}


def build_matrix(
    tasks: List[str],
    assignments: Dict[str, Dict[str, str]],
) -> Dict[str, Any]:
    """
    Build a RACI matrix from tasks and assignments.

    assignments: {task_name: {stakeholder: role_string}}
    role_string can be "R", "A", "C", "I", "A/R", etc.
    """
    all_stakeholders: Set[str] = set()
    matrix: List[Dict[str, Any]] = []

    for task in tasks:
        task_assigns = assignments.get(task, {})
        all_stakeholders.update(task_assigns.keys())

        roles_parsed: Dict[str, List[str]] = {}
        for stakeholder, role_str in task_assigns.items():
            roles = [r.strip().upper() for r in role_str.replace("/", ",").split(",") if r.strip()]
            valid = [r for r in roles if r in VALID_ROLES]
            if valid:
                roles_parsed[stakeholder] = valid

        matrix.append({
            "task": task,
            "assignments": roles_parsed,
        })

    stakeholders = sorted(all_stakeholders)

    return {
        "tasks": [m["task"] for m in matrix],
        "stakeholders": stakeholders,
        "matrix": matrix,
    }


def validate_matrix(data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate a RACI matrix and report issues."""
    issues: List[Dict[str, str]] = []
    warnings: List[Dict[str, str]] = []
    matrix = data["matrix"]
    stakeholders = data["stakeholders"]

    # Per-task validation
    for row in matrix:
        task = row["task"]
        assigns = row["assignments"]

        # Find A and R counts
        accountable = [s for s, roles in assigns.items() if "A" in roles]
        responsible = [s for s, roles in assigns.items() if "R" in roles]

        if len(accountable) == 0:
            issues.append({"type": "no_accountable", "task": task,
                           "message": f"'{task}' has no Accountable owner"})
        elif len(accountable) > 1:
            issues.append({"type": "multi_accountable", "task": task,
                           "message": f"'{task}' has {len(accountable)} Accountable owners: {', '.join(accountable)}"})

        if len(responsible) == 0 and len(accountable) > 0:
            warnings.append({"type": "no_responsible", "task": task,
                             "message": f"'{task}' has no Responsible — A owner may be overloaded"})

        if not assigns:
            issues.append({"type": "unassigned", "task": task,
                           "message": f"'{task}' has no assignments at all"})

    # Per-stakeholder analysis
    stakeholder_load: Dict[str, Dict[str, int]] = {}
    for s in stakeholders:
        stakeholder_load[s] = {"R": 0, "A": 0, "C": 0, "I": 0, "total": 0}

    for row in matrix:
        for s, roles in row["assignments"].items():
            if s not in stakeholder_load:
                stakeholder_load[s] = {"R": 0, "A": 0, "C": 0, "I": 0, "total": 0}
            for role in roles:
                stakeholder_load[s][role] += 1
            stakeholder_load[s]["total"] += 1

    n_tasks = len(matrix)

    # Overloaded stakeholders
    for s, load in stakeholder_load.items():
        ra_count = load["R"] + load["A"]
        if ra_count > n_tasks * 0.7 and n_tasks >= 3:
            warnings.append({"type": "overloaded", "stakeholder": s,
                             "message": f"'{s}' is R or A on {ra_count}/{n_tasks} tasks — potential bottleneck"})

    # Uninvolved stakeholders
    for s in stakeholders:
        if stakeholder_load.get(s, {}).get("total", 0) == 0:
            warnings.append({"type": "uninvolved", "stakeholder": s,
                             "message": f"'{s}' has no assignments — should they be on this project?"})

    # Summary
    total_cells = len(matrix) * len(stakeholders)
    filled_cells = sum(len(row["assignments"]) for row in matrix)
    density = filled_cells / total_cells * 100 if total_cells > 0 else 0

    score = 100
    score -= len(issues) * 15
    score -= len(warnings) * 5
    score = max(0, min(100, score))

    if score >= 80:
        grade = "🟢 Well-structured"
    elif score >= 60:
        grade = "🟡 Needs improvement"
    else:
        grade = "🔴 Significant issues"

    return {
        "issues": issues,
        "warnings": warnings,
        "n_issues": len(issues),
        "n_warnings": len(warnings),
        "stakeholder_load": stakeholder_load,
        "density_pct": round(density, 1),
        "score": score,
        "grade": grade,
    }


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def parse_assign_string(s: str) -> Tuple[str, str, str]:
    """Parse 'Task:Stakeholder:Role' or 'Task:Stakeholder:Role,...'."""
    parts = s.split(":")
    if len(parts) < 3:
        raise ValueError(
            f"Invalid assignment '{s}'. Format: Task:Stakeholder:Role"
        )
    task = parts[0].strip()
    # Remaining parts: pairs of stakeholder:role separated by commas
    rest = ":".join(parts[1:])
    pairs = []
    for pair in rest.split(","):
        pair = pair.strip()
        if ":" in pair:
            st, role = pair.rsplit(":", 1)
            pairs.append((st.strip(), role.strip()))
        elif len(pairs) > 0:
            # Might be continuation
            pass

    return task, pairs


def load_csv_matrix(path: str) -> Dict[str, Any]:
    """Load RACI from matrix-style CSV (stakeholders as columns)."""
    tasks: List[str] = []
    assignments: Dict[str, Dict[str, str]] = {}

    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fields = reader.fieldnames or []

        # First column is the task name
        task_col = fields[0] if fields else "task"
        stakeholder_cols = [f for f in fields[1:] if f.strip()]

        for row in reader:
            task = row.get(task_col, "").strip()
            if not task:
                continue

            tasks.append(task)
            task_assigns: Dict[str, str] = {}

            for col in stakeholder_cols:
                val = row.get(col, "").strip().upper()
                if val:
                    task_assigns[col] = val

            assignments[task] = task_assigns

    return build_matrix(tasks, assignments)


def load_json(path: str) -> Dict[str, Any]:
    """Load RACI from JSON."""
    with open(path, encoding="utf-8") as f:
        config = json.load(f)

    tasks: List[str] = []
    assignments: Dict[str, Dict[str, str]] = {}

    for t in config.get("tasks", []):
        name = t.get("name", "")
        if not name:
            continue
        tasks.append(name)
        assigns = t.get("assignments", {})
        assignments[name] = {k: v.upper() for k, v in assigns.items()}

    return build_matrix(tasks, assignments)


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def _role_cell(roles: List[str]) -> str:
    """Format role list for display."""
    if not roles:
        return "·"
    return "/".join(roles)


def print_report(
    data: Dict[str, Any],
    validation: Dict[str, Any],
) -> None:
    """Pretty-print RACI matrix and validation."""
    print("\n" + "=" * 78)
    print("📋 STAKEHOLDER RACI MATRIX")
    print("=" * 78)

    matrix = data["matrix"]
    stakeholders = data["stakeholders"]

    # Matrix display
    print(f"\n{'─'*78}")
    print(f"\n   Legend: R=Responsible  A=Accountable  C=Consulted  I=Informed\n")

    # Determine column widths
    task_width = max(16, max((len(m["task"]) for m in matrix), default=16))
    task_width = min(task_width, 24)
    col_width = max(5, max((len(s) for s in stakeholders), default=5))
    col_width = min(col_width, 12)

    # Header
    header = f"   {'Task':<{task_width}}"
    for s in stakeholders:
        header += f" {s[:col_width]:^{col_width}}"
    print(header)
    div = f"   {'─'*task_width}"
    for _ in stakeholders:
        div += f" {'─'*col_width}"
    print(div)

    # Rows
    for row in matrix:
        line = f"   {row['task'][:task_width]:<{task_width}}"
        for s in stakeholders:
            roles = row["assignments"].get(s, [])
            cell = _role_cell(roles)
            line += f" {cell:^{col_width}}"
        print(line)

    # Stakeholder load
    print(f"\n{'─'*78}")
    print(f"\n📊 STAKEHOLDER LOAD:\n")
    print(f"   {'Stakeholder':<{max(16, col_width)}} {'R':>4} {'A':>4} {'C':>4} {'I':>4} {'Total':>6}")
    print(f"   {'─'*max(16, col_width)} {'─'*4} {'─'*4} {'─'*4} {'─'*4} {'─'*6}")

    load = validation["stakeholder_load"]
    max_total = max((l["total"] for l in load.values()), default=1)
    for s in stakeholders:
        sl = load.get(s, {"R": 0, "A": 0, "C": 0, "I": 0, "total": 0})
        bar_width = 15
        bar_filled = int(sl["total"] / max_total * bar_width) if max_total > 0 else 0
        bar = "█" * bar_filled + "░" * (bar_width - bar_filled)
        print(f"   {s[:max(16, col_width)]:<{max(16, col_width)}} {sl['R']:>4} {sl['A']:>4} {sl['C']:>4} {sl['I']:>4} {sl['total']:>6}  {bar}")

    # Validation results
    print(f"\n{'─'*78}")
    print(f"\n✅ VALIDATION RESULTS:\n")
    print(f"   Score:     {validation['score']}/100  {validation['grade']}")
    print(f"   Density:   {validation['density_pct']:.0f}% of matrix cells filled")
    print(f"   Issues:    {validation['n_issues']}")
    print(f"   Warnings:  {validation['n_warnings']}")

    if validation["issues"]:
        print(f"\n   🔴 ISSUES (must fix):")
        for issue in validation["issues"]:
            print(f"   • {issue['message']}")

    if validation["warnings"]:
        print(f"\n   🟡 WARNINGS (review):")
        for warn in validation["warnings"]:
            print(f"   • {warn['message']}")

    if not validation["issues"] and not validation["warnings"]:
        print(f"\n   🟢 No issues found — matrix looks good!")

    # Role distribution
    print(f"\n{'─'*78}")
    print(f"\n📈 ROLE DISTRIBUTION:\n")

    role_totals = {"R": 0, "A": 0, "C": 0, "I": 0}
    for row in matrix:
        for s, roles in row["assignments"].items():
            for role in roles:
                if role in role_totals:
                    role_totals[role] += 1

    grand_total = sum(role_totals.values())
    max_role = max(role_totals.values()) if role_totals else 1
    for role in ["R", "A", "C", "I"]:
        count = role_totals[role]
        pct = count / grand_total * 100 if grand_total > 0 else 0
        bar_width = 25
        bar_filled = int(count / max_role * bar_width) if max_role > 0 else 0
        bar = "█" * bar_filled + "░" * (bar_width - bar_filled)
        print(f"   {ROLE_EMOJI[role]} {ROLE_NAMES[role]:<14} {bar} {count:>3} ({pct:.0f}%)")

    # Guidance
    print(f"\n{'─'*78}")
    print(f"\n💡 RACI BEST PRACTICES:")
    print(f"   • Every task needs exactly ONE Accountable owner")
    print(f"   • The A person makes the final call — R does the work")
    print(f"   • Minimize C/I to reduce communication overhead")
    print(f"   • If someone is R on >70% of tasks, they're a bottleneck")
    print(f"   • Review and update RACI at each project phase change")
    print(f"   • Consider DACI (Driver instead of Responsible) for decisions")
    print("\n" + "=" * 78)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Generate and validate RACI matrices. Detect anti-patterns "
                    "like missing accountability, overloaded stakeholders, and gaps.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --csv raci.csv
  %(prog)s --json raci.json
  %(prog)s --assign "Design:PM:A,Eng:R,QA:I" --assign "Build:Eng:A,Dev:R,PM:I"
        """,
    )

    parser.add_argument("--csv", "-c", type=str, help="CSV file (matrix-style: stakeholders as columns)")
    parser.add_argument("--json", "-j", type=str, help="JSON config file")
    parser.add_argument("--assign", type=str, action="append",
                        help="Assignment: 'Task:Stakeholder:Role,Stakeholder:Role,...'")
    parser.add_argument("--output", "-o", type=str, help="Write JSON results to file")
    args = parser.parse_args()

    data = None

    if args.csv:
        try:
            data = load_csv_matrix(args.csv)
        except Exception as e:
            print(f"Error loading CSV: {e}", file=sys.stderr)
            return 1

    elif args.json:
        try:
            data = load_json(args.json)
        except Exception as e:
            print(f"Error loading JSON: {e}", file=sys.stderr)
            return 1

    elif args.assign:
        tasks: List[str] = []
        assignments: Dict[str, Dict[str, str]] = {}

        for a_str in args.assign:
            try:
                task, pairs = parse_assign_string(a_str)
            except ValueError as e:
                print(f"Error: {e}", file=sys.stderr)
                return 1

            if task not in tasks:
                tasks.append(task)
            if task not in assignments:
                assignments[task] = {}
            for stakeholder, role in pairs:
                assignments[task][stakeholder] = role

        data = build_matrix(tasks, assignments)

    else:
        print("Error: provide input via --csv, --json, or --assign.", file=sys.stderr)
        parser.print_help(sys.stderr)
        return 1

    # Validate
    validation = validate_matrix(data)

    # Report
    print_report(data, validation)

    # JSON output
    if args.output:
        report = {
            "matrix": data,
            "validation": validation,
        }
        with open(args.output, "w") as f:
            json.dump(report, f, indent=2, default=str)
        print(f"\n📁 Results saved to {args.output}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
