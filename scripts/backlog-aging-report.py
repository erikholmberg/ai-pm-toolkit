#!/usr/bin/env python3
"""
Backlog Aging Report

Report how old backlog items are: age distribution by band (e.g. 0–30d, 31–90d,
91–180d, 181+d), count and story points per band, and the oldest items. Use for
backlog grooming and surfacing stale work. Complements backlog-health-report
(which adds estimation, priority mix, and stale-by-update).

Usage:
    # Basic (created date required)
    python backlog-aging-report.py --csv backlog.csv

    # Oldest 15 items; as-of date
    python backlog-aging-report.py --csv backlog.csv --oldest 15 --as-of 2025-02-14

    # Custom created column
    python backlog-aging-report.py --csv backlog.csv --created Created

    # Export
    python backlog-aging-report.py --csv backlog.csv --markdown report.md --output report.json

CSV format (Jira export or similar):
    Key,Summary,Priority,Created,Story Points
    PROJ-101,Fix login bug,High,2024-11-01,5
    PROJ-102,Add SSO,Medium,2025-01-15,8

    Required: id/key, created date.
    Optional: summary, priority, story points (for points-by-band and oldest list).

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


# Default age bands: (label, max_days_inclusive). Last band is open-ended.
DEFAULT_BANDS = [
    ("0-30d", 30),
    ("31-90d", 90),
    ("91-180d", 180),
    ("181+d", None),  # None = no upper bound
]


# ---------------------------------------------------------------------------
# Date parsing
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Load backlog
# ---------------------------------------------------------------------------

def load_backlog(
    path: str,
    id_col: str = "key",
    created_col: str = "created",
    summary_col: str = "summary",
    priority_col: str = "priority",
    points_col: str = "story points",
) -> List[Dict[str, Any]]:
    """Load backlog from CSV; require id and created; optional summary, priority, points."""
    rows: List[Dict[str, Any]] = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fields = reader.fieldnames or []

        c_id = _col(fields, id_col, "key", "id", "issue key", "issue_key")
        c_created = _col(fields, created_col, "created", "created date", "createdate", "created_at")
        c_summary = _col(fields, summary_col, "summary", "title", "subject")
        c_priority = _col(fields, priority_col, "priority", "pri")
        c_points = _col(fields, points_col, "story points", "customfield_10016", "points", "estimate")

        for row in reader:
            key = (row.get(c_id or "key", "") or "").strip()
            raw_created = (row.get(c_created or "created", "") or "").strip()
            created_dt = parse_date(raw_created)
            if not key or not created_dt:
                continue

            raw_points = (row.get(c_points or "story points", "") or "").strip().replace(",", "")
            try:
                points = float(raw_points) if raw_points else 0
            except ValueError:
                points = 0
            if points < 0:
                points = 0

            summary = (row.get(c_summary or "summary", "") or "").strip()
            priority = (row.get(c_priority or "priority", "") or "").strip() or "—"

            rows.append({
                "id": key,
                "created": created_dt,
                "summary": summary,
                "priority": priority,
                "points": points,
            })

    return rows


# ---------------------------------------------------------------------------
# Aging analysis
# ---------------------------------------------------------------------------

def assign_band(days: int, bands: List[Tuple[str, Optional[int]]]) -> str:
    """Return band label for given age in days."""
    for label, max_d in bands:
        if max_d is None:
            return label
        if days <= max_d:
            return label
    return bands[-1][0] if bands else "—"


def analyze_aging(
    issues: List[Dict[str, Any]],
    as_of: datetime,
    bands: List[Tuple[str, Optional[int]]],
    oldest_n: int,
) -> Dict[str, Any]:
    """Compute age distribution and oldest items."""
    if not issues:
        return {"total": 0, "error": "No issues with valid created date"}

    by_band_count: Dict[str, int] = defaultdict(int)
    by_band_points: Dict[str, float] = defaultdict(float)
    with_age: List[Dict[str, Any]] = []

    for i in issues:
        created = i["created"]
        days = (as_of - created).days
        if days < 0:
            days = 0
        band = assign_band(days, bands)
        by_band_count[band] += 1
        by_band_points[band] += i.get("points", 0) or 0
        with_age.append({
            **i,
            "age_days": days,
            "band": band,
        })

    # Oldest first
    with_age.sort(key=lambda x: -x["age_days"])
    oldest = with_age[:oldest_n]
    oldest_out = [
        {
            "id": x["id"],
            "age_days": x["age_days"],
            "summary": (x.get("summary") or "—")[:50],
            "priority": x.get("priority", "—"),
            "points": x.get("points", 0),
        }
        for x in oldest
    ]

    total_points = sum(i.get("points", 0) or 0 for i in issues)
    band_list = [
        {"band": label, "count": by_band_count[label], "points": round(by_band_points[label], 1)}
        for label, _ in bands
    ]

    return {
        "total": len(issues),
        "total_points": round(total_points, 1),
        "as_of": as_of.strftime("%Y-%m-%d"),
        "bands": band_list,
        "oldest": oldest_out,
        "oldest_n": oldest_n,
    }


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def _bar(value: float, max_val: float, width: int = 22) -> str:
    if max_val <= 0:
        return "░" * width
    ratio = min(1.0, max(0.0, value / max_val))
    filled = int(ratio * width)
    return "█" * filled + "░" * (width - filled)


def print_report(result: Dict[str, Any]) -> None:
    """Pretty-print backlog aging report."""
    print("\n" + "=" * 70)
    print("📅 BACKLOG AGING REPORT")
    print("=" * 70)

    if result.get("error"):
        print(f"\n   ⚠️  {result['error']}\n")
        return

    total = result["total"]
    total_pts = result.get("total_points", 0)
    print(f"\n   Total items:   {total}")
    print(f"   Total points: {total_pts:.0f}")
    print(f"   As of:        {result['as_of']}")

    print(f"\n   {'Band':<12} {'Count':>8} {'Points':>10}  Distribution")
    print("   " + "─" * 56)
    max_count = max(b["count"] for b in result["bands"]) or 1
    for b in result["bands"]:
        bar = _bar(b["count"], max_count, 20)
        print(f"   {b['band']:<12} {b['count']:>8} {b['points']:>10.0f}  {bar}")

    oldest = result.get("oldest", [])
    if oldest:
        print(f"\n   Oldest {len(oldest)} items (by created date):")
        print(f"   {'Id':<14} {'Age':>6} {'Pts':>5}  {'Priority':<8}  Summary")
        print("   " + "─" * 70)
        for o in oldest:
            print(f"   {o['id']:<14} {o['age_days']:>5}d {o['points']:>5.0f}  {o['priority']:<8}  {o['summary'][:36]}")

    print("\n   💡 Use to prioritize grooming: tackle oldest or high-point bands first.\n")


def to_json_result(result: Dict[str, Any]) -> Dict[str, Any]:
    """JSON-serializable result."""
    return {
        "total": result.get("total", 0),
        "total_points": result.get("total_points", 0),
        "as_of": result.get("as_of"),
        "bands": result.get("bands", []),
        "oldest": result.get("oldest", []),
        "oldest_n": result.get("oldest_n", 10),
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Report backlog age distribution and oldest items.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--csv", "-c", required=True, help="Path to backlog CSV (key, created required)")
    parser.add_argument("--created", default="created", help="Created date column name")
    parser.add_argument("--as-of", type=str, default=None, metavar="DATE", help="Reference date (default: today)")
    parser.add_argument("--oldest", type=int, default=10, help="Number of oldest items to list (default: 10)")
    parser.add_argument("--markdown", metavar="FILE", help="Write Markdown report to FILE")
    parser.add_argument("--output", "-o", metavar="FILE", help="Write JSON result to FILE")
    args = parser.parse_args()

    as_of = datetime.now()
    if args.as_of:
        parsed = parse_date(args.as_of)
        if parsed:
            as_of = parsed
        else:
            print(f"Invalid --as-of date: {args.as_of}", file=sys.stderr)
            return 1

    issues = load_backlog(args.csv, created_col=args.created)
    if not issues:
        print("No issues with valid created date in CSV.", file=sys.stderr)
        return 1

    result = analyze_aging(issues, as_of, DEFAULT_BANDS, max(1, args.oldest))
    print_report(result)

    if args.markdown and not result.get("error"):
        with open(args.markdown, "w", encoding="utf-8") as f:
            f.write("# Backlog Aging Report\n\n")
            f.write(f"- **Total items:** {result['total']}\n")
            f.write(f"- **Total points:** {result.get('total_points', 0)}\n")
            f.write(f"- **As of:** {result['as_of']}\n\n")
            f.write("| Band | Count | Points |\n")
            f.write("|------|-------|--------|\n")
            for b in result.get("bands", []):
                f.write(f"| {b['band']} | {b['count']} | {b['points']} |\n")
            f.write("\n## Oldest items\n\n")
            f.write("| Id | Age (days) | Points | Priority | Summary |\n")
            f.write("|----|------------|--------|----------|--------|\n")
            for o in result.get("oldest", []):
                summary_raw = (o.get("summary") or "—")[:40]
                summary_esc = summary_raw.replace("|", "\\|")
                f.write(f"| {o['id']} | {o['age_days']} | {o['points']} | {o['priority']} | {summary_esc} |\n")
        print(f"Wrote Markdown to {args.markdown}")

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(to_json_result(result), f, indent=2)
        print(f"Wrote JSON to {args.output}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
