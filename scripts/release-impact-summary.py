#!/usr/bin/env python3
"""
Release Impact Summary

Turn a list of shipped items (CSV) into a one-pager summary: "X features, Y fixes,
Z improvements" and optional bullet list by type. For release notes, stakeholder
updates, or launch comms. Complements release-notes-generator (full notes from
git/CSV); this script is for a short impact snapshot.

Usage:
    # Basic (feature/title, type columns)
    python release-impact-summary.py --csv shipped.csv

    # With version and date; bullets by type
    python release-impact-summary.py --csv shipped.csv --version "v2.1.0" --date 2025-06-15 --bullets

    # Export
    python release-impact-summary.py --csv shipped.csv --markdown summary.md --output summary.json

CSV format:
    feature,type,reach
    Add SSO support,feature,All users
    Fix login timeout,fix,
    Improve dashboard load,improvement,Web

    Required: feature (or title/name), type (feature|fix|improvement|chore|other).
    Optional: reach, segment, description.

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
# Column helper and type normalization
# ---------------------------------------------------------------------------

def _col(fieldnames: List[str], *aliases: str) -> Optional[str]:
    lower_map = {f.lower().strip(): f for f in fieldnames}
    for alias in aliases:
        if alias.lower().strip() in lower_map:
            return lower_map[alias.lower().strip()]
    return None


# Normalize type/category to canonical labels
TYPE_MAP = {
    "feature": "feature", "feat": "feature", "features": "feature", "new": "feature",
    "fix": "fix", "bug": "fix", "bugfix": "fix", "fixes": "fix", "bug fix": "fix",
    "improvement": "improvement", "improve": "improvement", "improvements": "improvement",
    "perf": "improvement", "performance": "improvement", "enhancement": "improvement",
    "chore": "chore", "chores": "chore", "maintenance": "chore", "docs": "chore",
    "refactor": "improvement", "other": "other",
}


def normalize_type(val: str) -> str:
    """Normalize type/category to feature|fix|improvement|chore|other."""
    if not val or not str(val).strip():
        return "other"
    s = str(val).strip().lower()
    return TYPE_MAP.get(s, "other")


# ---------------------------------------------------------------------------
# Load shipped items
# ---------------------------------------------------------------------------

def load_shipped(
    path: str,
    feature_col: str = "feature",
    type_col: str = "type",
    reach_col: str = "reach",
) -> List[Dict[str, Any]]:
    """Load shipped items from CSV."""
    rows: List[Dict[str, Any]] = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fields = reader.fieldnames or []

        c_feat = _col(fields, feature_col, "feature", "title", "name", "item", "description")
        c_type = _col(fields, type_col, "type", "category", "kind")
        c_reach = _col(fields, reach_col, "reach", "segment", "audience")

        for row in reader:
            title = (row.get(c_feat or "feature", "") or "").strip()
            if not title:
                continue
            raw_type = (row.get(c_type or "type", "") or "").strip()
            typ = normalize_type(raw_type)
            reach = (row.get(c_reach or "reach", "") or "").strip()
            rows.append({
                "feature": title,
                "type": typ,
                "reach": reach or None,
            })

    return rows


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

def summarize_impact(items: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Group by type; build one-liner and by_type lists."""
    by_type: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for item in items:
        by_type[item["type"]].append(item)

    # Order: feature, fix, improvement, chore, other
    order = ("feature", "fix", "improvement", "chore", "other")
    counts = {t: len(by_type[t]) for t in order if by_type[t]}
    for t in by_type:
        if t not in counts:
            counts[t] = len(by_type[t])

    parts = []
    if counts.get("feature"):
        parts.append(f"{counts['feature']} feature{'s' if counts['feature'] != 1 else ''}")
    if counts.get("fix"):
        parts.append(f"{counts['fix']} fix{'es' if counts['fix'] != 1 else ''}")
    if counts.get("improvement"):
        parts.append(f"{counts['improvement']} improvement{'s' if counts['improvement'] != 1 else ''}")
    if counts.get("chore"):
        parts.append(f"{counts['chore']} chore{'s' if counts['chore'] != 1 else ''}")
    if counts.get("other"):
        parts.append(f"{counts['other']} other")

    one_liner = ", ".join(parts) if parts else "No items"
    total = len(items)

    return {
        "total": total,
        "by_type": dict(by_type),
        "counts": counts,
        "one_liner": one_liner,
        "order": order,
    }


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def print_report(result: Dict[str, Any], version: Optional[str], date: Optional[str], bullets: bool) -> None:
    """Pretty-print release impact summary."""
    print("\n" + "=" * 70)
    print("📦 RELEASE IMPACT SUMMARY")
    print("=" * 70)

    if version or date:
        header = []
        if version:
            header.append(version)
        if date:
            header.append(date)
        print(f"\n   {'  '.join(header)}")

    total = result["total"]
    print(f"\n   Total: {total} items")
    print(f"   Summary: {result['one_liner']}")

    if bullets and result.get("by_type"):
        print("\n   By type:")
        for typ in result["order"]:
            items = result["by_type"].get(typ, [])
            if not items:
                continue
            label = typ.capitalize() + "s" if typ != "fix" else "Fixes"
            print(f"\n   {label} ({len(items)}):")
            for it in items:
                reach = f"  [{it['reach']}]" if it.get("reach") else ""
                print(f"      • {it['feature']}{reach}")

    print("\n   💡 Use for release notes or stakeholder one-pagers.\n")


def to_json_result(result: Dict[str, Any]) -> Dict[str, Any]:
    """JSON-serializable result."""
    return {
        "total": result.get("total", 0),
        "counts": result.get("counts", {}),
        "one_liner": result.get("one_liner", ""),
        "by_type": {
            k: [{"feature": i["feature"], "reach": i.get("reach")} for i in v]
            for k, v in result.get("by_type", {}).items()
        },
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description="One-pager release impact: X features, Y fixes, Z improvements from CSV.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--csv", "-c", required=True, help="Path to shipped items CSV")
    parser.add_argument("--version", "-v", type=str, default=None, help="Version label (e.g. v2.1.0)")
    parser.add_argument("--date", "-d", type=str, default=None, help="Release date (e.g. 2025-06-15)")
    parser.add_argument("--bullets", "-b", action="store_true", help="Print bullet list by type")
    parser.add_argument("--markdown", metavar="FILE", help="Write Markdown summary to FILE")
    parser.add_argument("--output", "-o", metavar="FILE", help="Write JSON result to FILE")
    args = parser.parse_args()

    items = load_shipped(args.csv)
    if not items:
        print("No items in CSV (need feature/title column).", file=sys.stderr)
        return 1

    result = summarize_impact(items)
    print_report(result, args.version, args.date, args.bullets)

    if args.markdown:
        with open(args.markdown, "w", encoding="utf-8") as f:
            if args.version or args.date:
                f.write("# Release impact")
                if args.version:
                    f.write(f" — {args.version}")
                if args.date:
                    f.write(f" ({args.date})")
                f.write("\n\n")
            f.write(f"**Summary:** {result['one_liner']}\n\n")
            f.write(f"*Total: {result['total']} items*\n\n")
            if result.get("by_type"):
                for typ in result["order"]:
                    list_items = result["by_type"].get(typ, [])
                    if not list_items:
                        continue
                    label = typ.capitalize() + "s" if typ != "fix" else "Fixes"
                    f.write(f"## {label}\n\n")
                    for it in list_items:
                        reach = f" *({it['reach']})*" if it.get("reach") else ""
                        f.write(f"- {it['feature']}{reach}\n")
                    f.write("\n")
        print(f"Wrote Markdown to {args.markdown}")

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(to_json_result(result), f, indent=2)
        print(f"Wrote JSON to {args.output}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
