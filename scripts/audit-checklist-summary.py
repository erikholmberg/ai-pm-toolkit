#!/usr/bin/env python3
"""
Audit Checklist Summary

Score an audit or compliance checklist from CSV: % complete by domain and overall,
plus list of open items. For SOC2, ISO, or internal control prep.

Usage:
    # Basic (control_id, description, status)
    python audit-checklist-summary.py --csv controls.csv

    # Group by domain; show open items
    python audit-checklist-summary.py --csv controls.csv --group-by domain --open

    # Export
    python audit-checklist-summary.py --csv controls.csv --markdown report.md --output report.json

CSV format:
    control_id,description,status,evidence,domain
    CC6.1,Access reviews performed,complete,link-to-doc,Access
    CC6.2,Log retention configured,pending,,Access

    Required: control_id (or id), description, status.
    Status: complete/done/yes/1/met = complete; anything else = open.
    Optional: evidence, domain (or category) for --group-by.

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


COMPLETE_VALUES = {"yes", "y", "true", "1", "done", "complete", "met", "x", "✓", "ok", "passed"}


def is_complete(val: str) -> bool:
    if not val or not str(val).strip():
        return False
    return str(val).strip().lower() in COMPLETE_VALUES


def load_controls(
    path: str,
    id_col: str = "control_id",
    description_col: str = "description",
    status_col: str = "status",
    evidence_col: str = "evidence",
    domain_col: str = "domain",
) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fields = reader.fieldnames or []
        c_id = _col(fields, id_col, "control_id", "id", "control", "ref", "number")
        c_desc = _col(fields, description_col, "description", "desc", "requirement", "item")
        c_status = _col(fields, status_col, "status", "state", "complete", "done")
        c_evidence = _col(fields, evidence_col, "evidence", "evidence_link", "doc", "link")
        c_domain = _col(fields, domain_col, "domain", "category", "area", "control_type")

        for row in reader:
            ctrl_id = (row.get(c_id or "control_id", "") or "").strip()
            desc = (row.get(c_desc or "description", "") or "").strip()
            if not ctrl_id and not desc:
                continue
            if not ctrl_id:
                ctrl_id = f"Control {len(rows) + 1}"
            complete = is_complete((row.get(c_status or "status", "") or "").strip())
            evidence = (row.get(c_evidence or "evidence", "") or "").strip() or ""
            domain = (row.get(c_domain or "domain", "") or "").strip() or "—"
            rows.append({
                "control_id": ctrl_id,
                "description": desc or ctrl_id,
                "complete": complete,
                "evidence": evidence,
                "domain": domain,
            })
    return rows


def summarize_controls(
    controls: List[Dict[str, Any]],
    group_by_domain: bool,
) -> Dict[str, Any]:
    by_domain: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for r in controls:
        by_domain[r["domain"]].append(r)

    domain_stats = {}
    for domain, items in sorted(by_domain.items()):
        done = sum(1 for r in items if r["complete"])
        total = len(items)
        pct = (100.0 * done / total) if total else 0
        domain_stats[domain] = {"done": done, "total": total, "pct": round(pct, 1)}

    total_done = sum(1 for r in controls if r["complete"])
    total_items = len(controls)
    overall_pct = (100.0 * total_done / total_items) if total_items else 0
    open_items = [r for r in controls if not r["complete"]]

    return {
        "by_domain": domain_stats if group_by_domain else {},
        "total_done": total_done,
        "total_items": total_items,
        "overall_pct": round(overall_pct, 1),
        "open_items": open_items,
        "open_count": len(open_items),
    }


def print_report(result: Dict[str, Any], show_open: bool) -> None:
    print("\n" + "=" * 70)
    print("📋 AUDIT CHECKLIST SUMMARY")
    print("=" * 70)

    if not result.get("total_items") and not result.get("by_domain"):
        print("\n   No controls in CSV (need control_id, description, status).\n")
        return

    total = result["total_items"]
    done = result["total_done"]
    overall = result["overall_pct"]
    print(f"\n   Overall: {done}/{total} ({overall}%) complete")
    print(f"   Open:    {result['open_count']} controls")

    if result.get("by_domain"):
        print(f"\n   {'Domain':<20} {'Done':>6} {'Total':>6}  {'%':>6}")
        print("   " + "─" * 44)
        for domain, s in result["by_domain"].items():
            print(f"   {domain:<20} {s['done']:>6} {s['total']:>6}  {s['pct']:>5.1f}%")

    if show_open and result.get("open_items"):
        print(f"\n   Open items ({len(result['open_items'])}):")
        for r in result["open_items"][:20]:
            desc_short = (r["description"][:48] + "…") if len(r["description"]) > 49 else r["description"]
            print(f"      • [{r['control_id']}] {desc_short}")
        if len(result["open_items"]) > 20:
            print(f"      ... and {len(result['open_items']) - 20} more")

    print("\n   💡 Use for SOC2/audit prep and compliance tracking.\n")


def to_json_result(result: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "by_domain": result.get("by_domain", {}),
        "total_done": result.get("total_done", 0),
        "total_items": result.get("total_items", 0),
        "overall_pct": result.get("overall_pct", 0),
        "open_count": result.get("open_count", 0),
        "open_items": [
            {"control_id": r["control_id"], "description": r["description"], "evidence": r.get("evidence", "")}
            for r in result.get("open_items", [])
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Score audit/compliance checklist: % complete, open items.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--csv", "-c", required=True, help="Path to controls CSV (control_id, description, status)")
    parser.add_argument("--group-by", type=str, default=None, metavar="COL", help="Group by domain/category (enables by-domain stats)")
    parser.add_argument("--open", action="store_true", help="Print list of open items")
    parser.add_argument("--markdown", metavar="FILE", help="Write Markdown report to FILE")
    parser.add_argument("--output", "-o", metavar="FILE", help="Write JSON result to FILE")
    args = parser.parse_args()

    controls = load_controls(args.csv)
    if not controls:
        print("No valid rows in CSV (need control_id, description, status).", file=sys.stderr)
        return 1

    result = summarize_controls(controls, group_by_domain=args.group_by is not None)
    print_report(result, args.open)

    if args.markdown and result.get("total_items"):
        with open(args.markdown, "w", encoding="utf-8") as f:
            f.write("# Audit Checklist Summary\n\n")
            f.write(f"- **Overall:** {result['total_done']}/{result['total_items']} ({result['overall_pct']}%) complete\n")
            f.write(f"- **Open:** {result['open_count']} controls\n\n")
            if result.get("by_domain"):
                f.write("| Domain | Done | Total | % |\n")
                f.write("|--------|------|-------|---|\n")
                for domain, s in result["by_domain"].items():
                    f.write(f"| {domain} | {s['done']} | {s['total']} | {s['pct']:.1f}% |\n")
                f.write("\n")
            f.write("## Open items\n\n")
            for r in result.get("open_items", []):
                desc_esc = r["description"].replace("|", "\\|")
                f.write(f"- **{r['control_id']}** {desc_esc}\n")
        print(f"Wrote Markdown to {args.markdown}")

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(to_json_result(result), f, indent=2)
        print(f"Wrote JSON to {args.output}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
