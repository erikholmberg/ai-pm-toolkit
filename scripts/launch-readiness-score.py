#!/usr/bin/env python3
"""
Launch Readiness Score

Score a launch checklist from CSV: % complete by area and overall, plus go/no-go.
Complements launch-checklist (which generates checklists); this script scores
progress from an exported checklist.

Usage:
    # Basic (area, item, done columns)
    python launch-readiness-score.py --csv checklist.csv

    # Go threshold: require 100%% in every area (default: overall >= 95%%)
    python launch-readiness-score.py --csv checklist.csv --go-threshold 100 --per-area

    # Export
    python launch-readiness-score.py --csv checklist.csv --markdown report.md --output report.json

CSV format:
    area,item,done
    QA,Smoke tests passed,yes
    Security,Pen test signed off,1
    Docs,Runbook updated,

    Required: area (or category), item (or task/description), done (or status/complete).
    Done: yes/true/1/done/complete/y = done; anything else or empty = not done.

Requirements:
    None (stdlib only).
"""

import argparse
import csv
import json
import sys
from collections import defaultdict
from typing import Any, Dict, List, Optional


def _col(fieldnames: list, *aliases: str) -> Optional[str]:
    lower_map = {f.lower().strip(): f for f in fieldnames}
    for alias in aliases:
        if alias.lower().strip() in lower_map:
            return lower_map[alias.lower().strip()]
    return None


DONE_VALUES = {"yes", "y", "true", "1", "done", "complete", "x", "✓", "ok"}


def is_done(val: str) -> bool:
    if not val or not str(val).strip():
        return False
    return str(val).strip().lower() in DONE_VALUES


def load_checklist(
    path: str,
    area_col: str = "area",
    item_col: str = "item",
    done_col: str = "done",
) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fields = reader.fieldnames or []
        c_area = _col(fields, area_col, "area", "category", "section", "group")
        c_item = _col(fields, item_col, "item", "task", "description", "check")
        c_done = _col(fields, done_col, "done", "status", "complete", "ok")

        for row in reader:
            area = (row.get(c_area or "area", "") or "").strip()
            item = (row.get(c_item or "item", "") or "").strip()
            if not area or not item:
                continue
            done = is_done((row.get(c_done or "done", "") or "").strip())
            rows.append({"area": area, "item": item, "done": done})
    return rows


def compute_score(items: List[Dict[str, Any]], go_threshold_pct: float, require_per_area: bool) -> Dict[str, Any]:
    by_area: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for r in items:
        by_area[r["area"]].append(r)

    area_stats = {}
    for area, area_items in sorted(by_area.items()):
        done = sum(1 for r in area_items if r["done"])
        total = len(area_items)
        pct = (100.0 * done / total) if total else 0
        area_stats[area] = {"done": done, "total": total, "pct": round(pct, 1)}

    total_done = sum(1 for r in items if r["done"])
    total_items = len(items)
    overall_pct = (100.0 * total_done / total_items) if total_items else 0

    if require_per_area:
        go = all(s["pct"] >= go_threshold_pct for s in area_stats.values()) if area_stats else False
    else:
        go = overall_pct >= go_threshold_pct

    return {
        "by_area": area_stats,
        "total_done": total_done,
        "total_items": total_items,
        "overall_pct": round(overall_pct, 1),
        "go_threshold_pct": go_threshold_pct,
        "require_per_area": require_per_area,
        "go": go,
    }


def print_report(result: Dict[str, Any]) -> None:
    print("\n" + "=" * 70)
    print("🚀 LAUNCH READINESS SCORE")
    print("=" * 70)

    if not result.get("by_area"):
        print("\n   No checklist items in CSV (need area, item, done).\n")
        return

    total = result["total_items"]
    done = result["total_done"]
    overall = result["overall_pct"]
    print(f"\n   Overall: {done}/{total} ({overall}%)")
    print(f"   Go threshold: {result['go_threshold_pct']}%" + (" (per area)" if result.get("require_per_area") else ""))
    print(f"\n   {'Area':<20} {'Done':>6} {'Total':>6}  {'%':>6}")
    print("   " + "─" * 44)
    for area, s in result["by_area"].items():
        print(f"   {area:<20} {s['done']:>6} {s['total']:>6}  {s['pct']:>5.1f}%")

    status = "🟢 GO" if result["go"] else "🔴 NO-GO"
    print(f"\n   Verdict: {status}")
    print("\n   💡 Use with launch checklist exports for go/no-go decisions.\n")


def to_json_result(result: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "by_area": result.get("by_area", {}),
        "total_done": result.get("total_done", 0),
        "total_items": result.get("total_items", 0),
        "overall_pct": result.get("overall_pct", 0),
        "go_threshold_pct": result.get("go_threshold_pct", 95),
        "require_per_area": result.get("require_per_area", False),
        "go": result.get("go", False),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Score launch checklist: % by area, overall, go/no-go.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--csv", "-c", required=True, help="Path to checklist CSV (area, item, done)")
    parser.add_argument("--go-threshold", type=float, default=95, metavar="PCT", help="Overall %% for GO (default: 95)")
    parser.add_argument("--per-area", action="store_true", help="Require threshold in every area for GO")
    parser.add_argument("--markdown", metavar="FILE", help="Write Markdown report to FILE")
    parser.add_argument("--output", "-o", metavar="FILE", help="Write JSON result to FILE")
    args = parser.parse_args()

    items = load_checklist(args.csv)
    if not items:
        print("No valid rows in CSV (need area, item, done).", file=sys.stderr)
        return 1

    result = compute_score(items, max(0, min(100, args.go_threshold)), args.per_area)
    print_report(result)

    if args.markdown and result.get("by_area"):
        with open(args.markdown, "w", encoding="utf-8") as f:
            f.write("# Launch Readiness Score\n\n")
            f.write(f"- **Overall:** {result['total_done']}/{result['total_items']} ({result['overall_pct']}%)\n")
            f.write(f"- **Go threshold:** {result['go_threshold_pct']}%\n")
            f.write(f"- **Verdict:** {'GO' if result['go'] else 'NO-GO'}\n\n")
            f.write("| Area | Done | Total | % |\n")
            f.write("|------|------|-------|---|\n")
            for area, s in result["by_area"].items():
                f.write(f"| {area} | {s['done']} | {s['total']} | {s['pct']:.1f}% |\n")
        print(f"Wrote Markdown to {args.markdown}")

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(to_json_result(result), f, indent=2)
        print(f"Wrote JSON to {args.output}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
