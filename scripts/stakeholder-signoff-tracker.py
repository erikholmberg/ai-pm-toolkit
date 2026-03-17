#!/usr/bin/env python3
"""
Stakeholder Sign-Off Tracker

Track approval status from CSV: % signed off, who's pending. For launch or
milestone sign-off.

Usage:
    # Basic (deliverable, stakeholder, status)
    python stakeholder-signoff-tracker.py --csv signoffs.csv

    # Show pending list; group by deliverable
    python stakeholder-signoff-tracker.py --csv signoffs.csv --pending --group-by deliverable

    # Export
    python stakeholder-signoff-tracker.py --csv signoffs.csv --markdown report.md --output report.json

CSV format:
    deliverable,stakeholder,status
    Launch checklist,Engineering,approved
    Launch checklist,Legal,pending
    Security review,Security,approved

    Required: deliverable (or item), stakeholder (or owner), status.
    Status: approved/yes/done/signed/1 = approved; anything else = pending.

Requirements:
    None (stdlib only).
"""

import argparse
import csv
import json
import sys
from collections import defaultdict
from typing import Any, Dict, List, Optional


def _col(fieldnames: List[str], *aliases: str) -> Optional[str]:
    lower_map = {f.lower().strip(): f for f in fieldnames}
    for alias in aliases:
        if alias.lower().strip() in lower_map:
            return lower_map[alias.lower().strip()]
    return None


APPROVED_VALUES = {"yes", "y", "true", "1", "approved", "approve", "done", "complete", "signed", "ok", "x", "✓"}


def is_approved(val: str) -> bool:
    if not val or not str(val).strip():
        return False
    return str(val).strip().lower() in APPROVED_VALUES


def load_signoffs(
    path: str,
    deliverable_col: str = "deliverable",
    stakeholder_col: str = "stakeholder",
    status_col: str = "status",
) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fields = reader.fieldnames or []
        c_del = _col(fields, deliverable_col, "deliverable", "item", "artifact", "workstream")
        c_stake = _col(fields, stakeholder_col, "stakeholder", "owner", "reviewer", "approver", "role")
        c_status = _col(fields, status_col, "status", "state", "approved", "signed")

        if not c_del or not c_stake or not c_status:
            raise ValueError(
                f"Required column(s) not found. Need deliverable, stakeholder, status. "
                f"Columns in file: {list(fields)}"
            )

        for row in reader:
            deliverable = (row.get(c_del, "") or "").strip()
            stakeholder = (row.get(c_stake, "") or "").strip()
            if not deliverable or not stakeholder:
                continue
            approved = is_approved((row.get(c_status, "") or "").strip())
            rows.append({
                "deliverable": deliverable,
                "stakeholder": stakeholder,
                "approved": approved,
            })
    return rows


def summarize(items: List[Dict[str, Any]], group_by_deliverable: bool) -> Dict[str, Any]:
    total = len(items)
    approved_count = sum(1 for r in items if r["approved"])
    pct = (100.0 * approved_count / total) if total else 0
    pending = [r for r in items if not r["approved"]]

    by_deliverable: Dict[str, Dict[str, Any]] = {}
    if group_by_deliverable:
        by_del: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        for r in items:
            by_del[r["deliverable"]].append(r)
        for deliv, del_items in sorted(by_del.items()):
            a = sum(1 for x in del_items if x["approved"])
            t = len(del_items)
            by_deliverable[deliv] = {
                "approved": a,
                "total": t,
                "pct": round(100.0 * a / t, 1) if t else 0,
                "pending": [x["stakeholder"] for x in del_items if not x["approved"]],
            }

    return {
        "total": total,
        "approved": approved_count,
        "pct": round(pct, 1),
        "pending": pending,
        "pending_count": len(pending),
        "by_deliverable": by_deliverable,
    }


def print_report(result: Dict[str, Any], show_pending: bool) -> None:
    print("\n" + "=" * 70)
    print("✍️  STAKEHOLDER SIGN-OFF TRACKER")
    print("=" * 70)

    total = result["total"]
    if total == 0:
        print("\n   No sign-off rows in CSV (need deliverable, stakeholder, status).\n")
        return

    print(f"\n   Total:      {total} sign-offs")
    print(f"   Approved:   {result['approved']} ({result['pct']}%)")
    print(f"   Pending:   {result['pending_count']}")

    if result.get("by_deliverable"):
        print(f"\n   By deliverable:")
        print(f"   {'Deliverable':<28} {'Done':>6} {'Total':>6}  {'%':>6}")
        print("   " + "─" * 50)
        for deliv, s in result["by_deliverable"].items():
            name = (deliv[:27] + "…") if len(deliv) > 28 else deliv
            print(f"   {name:<28} {s['approved']:>6} {s['total']:>6}  {s['pct']:>5.1f}%")

    if show_pending and result.get("pending"):
        print(f"\n   Pending ({len(result['pending'])}):")
        for r in result["pending"][:25]:
            del_short = (r["deliverable"][:30] + "…") if len(r["deliverable"]) > 31 else r["deliverable"]
            print(f"      • {r['stakeholder']:<16} ← {del_short}")
        if len(result["pending"]) > 25:
            print(f"      ... and {len(result['pending']) - 25} more")

    print("\n   💡 Use for launch and milestone sign-off.\n")


def to_json_result(result: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "total": result.get("total", 0),
        "approved": result.get("approved", 0),
        "pct": result.get("pct", 0),
        "pending_count": result.get("pending_count", 0),
        "pending": [{"deliverable": r["deliverable"], "stakeholder": r["stakeholder"]} for r in result.get("pending", [])],
        "by_deliverable": result.get("by_deliverable", {}),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Track stakeholder sign-offs: % approved, who's pending.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--csv", "-c", required=True, help="Path to sign-offs CSV (deliverable, stakeholder, status)")
    parser.add_argument("--group-by", type=str, default=None, metavar="COL", help="Group by deliverable")
    parser.add_argument("--pending", action="store_true", help="Print list of pending sign-offs")
    parser.add_argument("--markdown", metavar="FILE", help="Write Markdown report to FILE")
    parser.add_argument("--output", "-o", metavar="FILE", help="Write JSON result to FILE")
    args = parser.parse_args()

    try:
        items = load_signoffs(args.csv)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    if not items:
        print("No valid rows in CSV (need deliverable, stakeholder, status).", file=sys.stderr)
        return 1

    result = summarize(items, group_by_deliverable=args.group_by is not None)
    print_report(result, args.pending)

    if args.markdown and result.get("total"):
        with open(args.markdown, "w", encoding="utf-8") as f:
            f.write("# Stakeholder Sign-Off Tracker\n\n")
            f.write(f"- **Total:** {result['total']}  |  **Approved:** {result['approved']} ({result['pct']}%)  |  **Pending:** {result['pending_count']}\n\n")
            if result.get("by_deliverable"):
                f.write("| Deliverable | Done | Total | % |\n")
                f.write("|-------------|------|-------|---|\n")
                for deliv, s in result["by_deliverable"].items():
                    del_esc = deliv.replace("|", "\\|")
                    f.write(f"| {del_esc} | {s['approved']} | {s['total']} | {s['pct']:.1f}% |\n")
                f.write("\n")
            f.write("## Pending\n\n")
            for r in result.get("pending", []):
                del_esc = r["deliverable"].replace("|", "\\|")
                f.write(f"- **{r['stakeholder']}** — {del_esc}\n")
        print(f"Wrote Markdown to {args.markdown}")

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(to_json_result(result), f, indent=2)
        print(f"Wrote JSON to {args.output}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
