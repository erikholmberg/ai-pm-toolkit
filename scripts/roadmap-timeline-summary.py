#!/usr/bin/env python3
"""
Roadmap Timeline Summary

Turn a CSV of initiatives (epic, start, end, owner) into a "what ships when"
one-pager: sorted timeline, overlaps, and optional quarter view. For exec
updates and planning reviews.

Usage:
    # Basic
    python roadmap-timeline-summary.py --csv roadmap.csv

    # Show overlaps and quarter view
    python roadmap-timeline-summary.py --csv roadmap.csv --overlaps --by-quarter

    # Export
    python roadmap-timeline-summary.py --csv roadmap.csv --markdown report.md --output report.json

CSV format:
    initiative,start,end,owner
    SSO rollout,2025-03-01,2025-04-15,Platform
    API v2,2025-02-15,2025-05-01,Backend

    Required: initiative (or epic/title/name), start, end.
    Optional: owner. Dates: YYYY-MM-DD or similar.

Requirements:
    None (stdlib only).
"""

import argparse
import csv
import json
import sys
from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple


def parse_date(s: str) -> Optional[datetime]:
    if not s or not str(s).strip():
        return None
    s = str(s).strip()[:32]
    for fmt, trim in [
        ("%Y-%m-%dT%H:%M:%S", 19),
        ("%Y-%m-%d %H:%M:%S", 19),
        ("%Y-%m-%d", 10),
        ("%Y/%m/%d", 10),
        ("%m/%d/%Y", 10),
        ("%d/%m/%Y", 10),
    ]:
        try:
            return datetime.strptime(s[:trim].strip(), fmt)
        except ValueError:
            continue
    return None


def _col(fieldnames: List[str], *aliases: str) -> Optional[str]:
    lower_map = {f.lower().strip(): f for f in fieldnames}
    for alias in aliases:
        if alias.lower().strip() in lower_map:
            return lower_map[alias.lower().strip()]
    return None


def load_initiatives(
    path: str,
    initiative_col: str = "initiative",
    start_col: str = "start",
    end_col: str = "end",
    owner_col: str = "owner",
) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fields = reader.fieldnames or []
        c_init = _col(fields, initiative_col, "initiative", "epic", "title", "name", "item")
        c_start = _col(fields, start_col, "start", "start_date", "begin", "from")
        c_end = _col(fields, end_col, "end", "end_date", "due", "to")
        c_owner = _col(fields, owner_col, "owner", "assignee", "team", "responsible")

        for row in reader:
            name = (row.get(c_init or "initiative", "") or "").strip()
            if not name:
                continue
            start_dt = parse_date((row.get(c_start or "start", "") or "").strip())
            end_dt = parse_date((row.get(c_end or "end", "") or "").strip())
            if not start_dt or not end_dt:
                continue
            if end_dt < start_dt:
                end_dt, start_dt = start_dt, end_dt
            owner = (row.get(c_owner or "owner", "") or "").strip() or "—"
            rows.append({
                "initiative": name,
                "start": start_dt,
                "end": end_dt,
                "start_str": start_dt.strftime("%Y-%m-%d"),
                "end_str": end_dt.strftime("%Y-%m-%d"),
                "owner": owner,
            })
    rows.sort(key=lambda r: (r["start"], r["initiative"]))
    return rows


def find_overlaps(initiatives: List[Dict[str, Any]]) -> List[Tuple[Dict[str, Any], Dict[str, Any]]]:
    """Pairs of initiatives with overlapping [start, end] ranges."""
    overlaps: List[Tuple[Dict[str, Any], Dict[str, Any]]] = []
    for i, a in enumerate(initiatives):
        for b in initiatives[i + 1:]:
            if a["end"] >= b["start"] and b["end"] >= a["start"]:
                overlaps.append((a, b))
    return overlaps


def summarize_timeline(
    initiatives: List[Dict[str, Any]],
    by_quarter: bool,
) -> Dict[str, Any]:
    overlaps = find_overlaps(initiatives)
    by_q: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for r in initiatives:
        q = f"{r['start'].year}-Q{(r['start'].month - 1) // 3 + 1}"
        by_q[q].append(r)
    return {
        "initiatives": initiatives,
        "total": len(initiatives),
        "overlaps": overlaps,
        "by_quarter": dict(sorted(by_q.items())) if by_quarter else {},
    }


def print_report(result: Dict[str, Any], show_overlaps: bool, by_quarter: bool) -> None:
    print("\n" + "=" * 70)
    print("🗓️  ROADMAP TIMELINE SUMMARY")
    print("=" * 70)

    initiatives = result.get("initiatives", [])
    if not initiatives:
        print("\n   No initiatives in CSV (need initiative, start, end).\n")
        return

    print(f"\n   Total: {len(initiatives)} initiatives")
    print(f"\n   {'Initiative':<36} {'Start':<12} {'End':<12}  Owner")
    print("   " + "─" * 72)
    for r in initiatives:
        name = (r["initiative"][:35] + "…") if len(r["initiative"]) > 36 else r["initiative"]
        print(f"   {name:<36} {r['start_str']:<12} {r['end_str']:<12}  {r['owner']}")

    overlaps = result.get("overlaps", [])
    if show_overlaps and overlaps:
        print(f"\n   ⚠️  Overlaps ({len(overlaps)}):")
        for a, b in overlaps:
            print(f"      • {a['initiative'][:30]} ↔ {b['initiative'][:30]}")

    if by_quarter and result.get("by_quarter"):
        print("\n   By quarter:")
        for q, items in result["by_quarter"].items():
            names = ", ".join(i["initiative"][:25] for i in items[:3])
            if len(items) > 3:
                names += f" (+{len(items) - 3} more)"
            print(f"      {q}: {names}")

    print("\n   💡 Use for exec updates and planning reviews.\n")


def to_json_result(result: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "total": result.get("total", 0),
        "initiatives": [
            {
                "initiative": r["initiative"],
                "start": r["start_str"],
                "end": r["end_str"],
                "owner": r["owner"],
            }
            for r in result.get("initiatives", [])
        ],
        "overlaps": [
            (a["initiative"], b["initiative"])
            for a, b in result.get("overlaps", [])
        ],
        "by_quarter": {
            q: [i["initiative"] for i in items]
            for q, items in result.get("by_quarter", {}).items()
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Roadmap timeline: what ships when, overlaps, optional quarter view.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--csv", "-c", required=True, help="Path to roadmap CSV (initiative, start, end, owner)")
    parser.add_argument("--overlaps", action="store_true", help="Print overlapping initiatives")
    parser.add_argument("--by-quarter", action="store_true", help="Group by quarter")
    parser.add_argument("--markdown", metavar="FILE", help="Write Markdown report to FILE")
    parser.add_argument("--output", "-o", metavar="FILE", help="Write JSON result to FILE")
    args = parser.parse_args()

    initiatives = load_initiatives(args.csv)
    if not initiatives:
        print("No valid rows in CSV (need initiative, start, end).", file=sys.stderr)
        return 1

    result = summarize_timeline(initiatives, args.by_quarter)
    print_report(result, args.overlaps, args.by_quarter)

    if args.markdown and result.get("initiatives"):
        with open(args.markdown, "w", encoding="utf-8") as f:
            f.write("# Roadmap Timeline Summary\n\n")
            f.write(f"**Total:** {result['total']} initiatives\n\n")
            f.write("| Initiative | Start | End | Owner |\n")
            f.write("|------------|-------|-----|-------|\n")
            for r in result["initiatives"]:
                name_esc = r["initiative"].replace("|", "\\|")
                f.write(f"| {name_esc} | {r['start_str']} | {r['end_str']} | {r['owner']} |\n")
            if result.get("overlaps"):
                f.write("\n## Overlaps\n\n")
                for a, b in result["overlaps"]:
                    f.write(f"- {a['initiative']} ↔ {b['initiative']}\n")
            if result.get("by_quarter"):
                f.write("\n## By quarter\n\n")
                for q, items in result["by_quarter"].items():
                    f.write(f"**{q}:** " + ", ".join(i["initiative"] for i in items) + "\n\n")
        print(f"Wrote Markdown to {args.markdown}")

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(to_json_result(result), f, indent=2)
        print(f"Wrote JSON to {args.output}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
