#!/usr/bin/env python3
"""
Dependency / Blocked-By Summary

Summarize initiative dependencies from CSV: who is blocked by whom, list of
blocked initiatives, and optional blocking view. Complements dependency-risk-mapper
and roadmap-timeline-summary for roadmap reviews.

Usage:
    # Basic (initiative, blocked_by)
    python dependency-blocked-summary.py --csv deps.csv

    # Show blocking view (initiatives that block others)
    python dependency-blocked-summary.py --csv deps.csv --blocking

    # Export
    python dependency-blocked-summary.py --csv deps.csv --markdown report.md --output report.json

CSV format:
    initiative,blocked_by
    API v2,Auth Service
    Dashboard,API v2
    API v2,Data Pipeline

    Or one row per initiative with comma-separated blockers:
    initiative,blocked_by
    API v2,"Auth Service,Data Pipeline"
    Dashboard,"API v2"

    Required: initiative (or name), blocked_by (or depends_on, blocker). Multiple rows per initiative = multiple blockers.
    Optional: owner.

Requirements:
    None (stdlib only).
"""

import argparse
import csv
import json
import sys
from collections import defaultdict
from typing import Any, Dict, List, Optional, Set


def _col(fieldnames: List[str], *aliases: str) -> Optional[str]:
    lower_map = {f.lower().strip(): f for f in fieldnames}
    for alias in aliases:
        if alias.lower().strip() in lower_map:
            return lower_map[alias.lower().strip()]
    return None


def load_dependencies(
    path: str,
    initiative_col: str = "initiative",
    blocked_by_col: str = "blocked_by",
    owner_col: str = "owner",
) -> List[Dict[str, Any]]:
    """Load deps: one row per (initiative, blocker) or blocked_by comma-sep."""
    rows: List[Dict[str, Any]] = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fields = reader.fieldnames or []
        c_init = _col(fields, initiative_col, "initiative", "name", "epic", "item", "downstream")
        c_blocked = _col(fields, blocked_by_col, "blocked_by", "depends_on", "blocker", "upstream")
        c_owner = _col(fields, owner_col, "owner", "assignee", "team")

        if not c_init or not c_blocked:
            raise ValueError(
                f"Required column(s) not found. Need initiative and blocked_by (or depends_on). "
                f"Columns in file: {list(fields)}"
            )

        for row in reader:
            initiative = (row.get(c_init, "") or "").strip()
            raw = (row.get(c_blocked, "") or "").strip()
            if not initiative:
                continue
            owner = (row.get(c_owner or "owner", "") or "").strip() or "—"
            if not raw:
                rows.append({"initiative": initiative, "blocker": None, "owner": owner})
                continue
            for part in raw.replace(";", ",").split(","):
                blocker = part.strip()
                if blocker:
                    rows.append({"initiative": initiative, "blocker": blocker, "owner": owner})
    return rows


def summarize(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Group by initiative: list of blockers. Compute blocked set and blocking set."""
    by_initiative: Dict[str, List[str]] = defaultdict(list)
    initiatives_with_owner: Dict[str, str] = {}
    for r in rows:
        init = r["initiative"]
        initiatives_with_owner[init] = r.get("owner", "—")
        if init not in by_initiative:
            by_initiative[init] = []
        if r.get("blocker"):
            by_initiative[init].append(r["blocker"])

    # Dedupe blocker lists
    for k in by_initiative:
        by_initiative[k] = list(dict.fromkeys(by_initiative[k]))

    blocked_initiatives = [i for i, bl in by_initiative.items() if bl]
    all_blockers: Set[str] = set()
    for bl in by_initiative.values():
        all_blockers.update(bl)
    blocking = sorted(all_blockers)

    return {
        "by_initiative": dict(by_initiative),
        "owner": initiatives_with_owner,
        "blocked_initiatives": blocked_initiatives,
        "blocking": blocking,
        "total_initiatives": len(by_initiative),
        "total_blocked": len(blocked_initiatives),
    }


def print_report(result: Dict[str, Any], show_blocking: bool) -> None:
    print("\n" + "=" * 70)
    print("🔗 DEPENDENCY / BLOCKED-BY SUMMARY")
    print("=" * 70)

    by_init = result.get("by_initiative", {})
    if not by_init:
        print("\n   No dependencies in CSV (need initiative, blocked_by).\n")
        return

    print(f"\n   Initiatives: {result['total_initiatives']}  |  Blocked: {result['total_blocked']}")

    print(f"\n   {'Initiative':<32} {'Blocked by':<28}")
    print("   " + "─" * 62)
    for init, blockers in sorted(by_init.items()):
        name = (init[:31] + "…") if len(init) > 32 else init
        if blockers:
            bl_str = ", ".join(blockers[:3])
            if len(blockers) > 3:
                bl_str += f" (+{len(blockers) - 3})"
            bl_str = (bl_str[:27] + "…") if len(bl_str) > 28 else bl_str
            print(f"   {name:<32} {bl_str:<28}")
        else:
            print(f"   {name:<32} —")

    if result.get("blocked_initiatives"):
        print(f"\n   Blocked initiatives ({len(result['blocked_initiatives'])}):")
        for i in result["blocked_initiatives"][:15]:
            print(f"      • {i}")
        if len(result["blocked_initiatives"]) > 15:
            print(f"      ... and {len(result['blocked_initiatives']) - 15} more")

    if show_blocking and result.get("blocking"):
        print(f"\n   Blocking (dependencies others wait on):")
        for b in result["blocking"][:15]:
            print(f"      • {b}")
        if len(result["blocking"]) > 15:
            print(f"      ... and {len(result['blocking']) - 15} more")

    print("\n   💡 Use with roadmap-timeline and dependency-risk-mapper for planning.\n")


def to_json_result(result: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "by_initiative": result.get("by_initiative", {}),
        "blocked_initiatives": result.get("blocked_initiatives", []),
        "blocking": result.get("blocking", []),
        "total_initiatives": result.get("total_initiatives", 0),
        "total_blocked": result.get("total_blocked", 0),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Summarize initiative dependencies: blocked by, blocking view.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--csv", "-c", required=True, help="Path to dependencies CSV (initiative, blocked_by)")
    parser.add_argument("--blocking", action="store_true", help="Show initiatives that block others")
    parser.add_argument("--markdown", metavar="FILE", help="Write Markdown report to FILE")
    parser.add_argument("--output", "-o", metavar="FILE", help="Write JSON result to FILE")
    args = parser.parse_args()

    try:
        rows = load_dependencies(args.csv)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    if not rows:
        print("No valid rows in CSV (need initiative, blocked_by).", file=sys.stderr)
        return 1

    result = summarize(rows)
    if not result.get("by_initiative"):
        print("No valid rows in CSV (need initiative, blocked_by).", file=sys.stderr)
        return 1

    print_report(result, args.blocking)

    if args.markdown and result.get("by_initiative"):
        with open(args.markdown, "w", encoding="utf-8") as f:
            f.write("# Dependency / Blocked-By Summary\n\n")
            f.write(f"- **Initiatives:** {result['total_initiatives']}  |  **Blocked:** {result['total_blocked']}\n\n")
            f.write("| Initiative | Blocked by |\n")
            f.write("|------------|------------|\n")
            for init, blockers in sorted(result["by_initiative"].items()):
                init_esc = init.replace("|", "\\|")
                bl_esc = ", ".join(blockers).replace("|", "\\|") if blockers else "—"
                f.write(f"| {init_esc} | {bl_esc} |\n")
        print(f"Wrote Markdown to {args.markdown}")

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(to_json_result(result), f, indent=2)
        print(f"Wrote JSON to {args.output}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
