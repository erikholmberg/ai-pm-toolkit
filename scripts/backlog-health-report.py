#!/usr/bin/env python3
"""
Backlog Health Report

Analyze a Jira (or similar) backlog CSV export: age distribution, estimation
coverage, counts by priority/type, stale items, and hygiene (missing description,
assignee, points). Use to answer "how healthy is our backlog?" before planning.

Usage:
    # Basic (auto-detect Jira-style columns)
    python backlog-health-report.py --csv backlog.csv

    # Stale = no update in 21 days
    python backlog-health-report.py --csv backlog.csv --stale-days 21

    # Custom column names
    python backlog-health-report.py --csv backlog.csv \\
        --points customfield_10016 --summary Summary

    # Markdown and JSON output
    python backlog-health-report.py --csv backlog.csv --markdown report.md --output report.json

CSV format (Jira export or similar):
    Key,Summary,Assignee,Priority,Issue Type,Status,Created,Updated,Story Points
    PROJ-101,Fix login bug,,High,Bug,To Do,2025-01-15,2025-02-01,
    PROJ-102,Add SSO,alice@co.com,Medium,Story,Backlog,2025-02-01,2025-02-10,5

    Common Jira columns: Key, Summary, Description, Assignee, Priority, Issue Type,
    Status, Created, Updated, Story Points (or customfield_10016). Header row required.

Requirements:
    None (stdlib only). Optional: python-dateutil for date parsing.
"""

import argparse
import csv
import json
import sys
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Date parsing
# ---------------------------------------------------------------------------

def parse_date(s: str) -> Optional[datetime]:
    if not s or not str(s).strip():
        return None
    s = str(s).strip()
    try:
        from dateutil import parser as date_parser
        return date_parser.parse(s)
    except ImportError:
        pass
    except Exception:
        pass
    for fmt, trim in [
        ("%Y-%m-%dT%H:%M:%S.%f%z", 26),
        ("%Y-%m-%dT%H:%M:%S%z", 25),
        ("%Y-%m-%dT%H:%M:%S", 19),
        ("%Y-%m-%d %H:%M:%S", 19),
        ("%Y-%m-%d", 10),
        ("%Y/%m/%d", 10),
        ("%d/%b/%y %H:%M", 12),
    ]:
        try:
            return datetime.strptime(s[:trim].strip(), fmt)
        except ValueError:
            continue
    return None


def _col(fieldnames: List[str], *aliases: str) -> Optional[str]:
    lower_map = {f.lower().strip(): f for f in fieldnames}
    for alias in aliases:
        key = alias.lower().strip()
        if key in lower_map:
            return lower_map[key]
    return None


# ---------------------------------------------------------------------------
# Load backlog
# ---------------------------------------------------------------------------

def load_backlog(
    path: str,
    id_col: str = "key",
    summary_col: str = "summary",
    description_col: str = "description",
    assignee_col: str = "assignee",
    priority_col: str = "priority",
    type_col: str = "issuetype",
    status_col: str = "status",
    created_col: str = "created",
    updated_col: str = "updated",
    points_col: str = "story points",
) -> List[Dict[str, Any]]:
    """Load backlog issues from CSV with flexible column names."""
    rows: List[Dict[str, Any]] = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fields = reader.fieldnames or []

        c_id = _col(fields, id_col, "key", "id", "issue key", "ticket_id")
        c_summary = _col(fields, summary_col, "summary", "title", "subject")
        c_desc = _col(fields, description_col, "description")
        c_assignee = _col(fields, assignee_col, "assignee", "assignee name")
        c_priority = _col(fields, priority_col, "priority", "pri")
        c_type = _col(fields, type_col, "issue type", "issuetype", "type", "issue type")
        c_status = _col(fields, status_col, "status", "state")
        c_created = _col(fields, created_col, "created", "created date", "createdate")
        c_updated = _col(fields, updated_col, "updated", "updated date", "updatedate", "last updated")
        c_points = _col(fields, points_col, "story points", "story point", "customfield_10016", "points", "estimate")

        for row in reader:
            key = (row.get(c_id or "key", "") or "").strip()
            if not key:
                key = f"row_{len(rows)+1}"

            raw_points = (row.get(c_points or "story points", "") or "").strip().replace(",", "")
            try:
                points = float(raw_points) if raw_points else None
            except ValueError:
                points = None

            created_dt = parse_date(row.get(c_created or "created", "") or "")
            updated_dt = parse_date(row.get(c_updated or "updated", "") or "")
            summary = (row.get(c_summary or "summary", "") or "").strip()
            description = (row.get(c_desc or "description", "") or "").strip()
            assignee = (row.get(c_assignee or "assignee", "") or "").strip()
            priority = (row.get(c_priority or "priority", "") or "").strip() or "—"
            issue_type = (row.get(c_type or "issuetype", "") or "").strip() or "—"
            status = (row.get(c_status or "status", "") or "").strip() or "—"

            rows.append({
                "id": key,
                "summary": summary,
                "description": description,
                "assignee": assignee,
                "priority": priority,
                "type": issue_type,
                "status": status,
                "created": created_dt,
                "updated": updated_dt,
                "points": points,
                "has_summary": bool(summary),
                "has_description": bool(description),
                "has_assignee": bool(assignee),
                "estimated": points is not None and points != 0,
            })

    return rows


# ---------------------------------------------------------------------------
# Analyze
# ---------------------------------------------------------------------------

def analyze_backlog(
    issues: List[Dict[str, Any]],
    stale_days: int = 14,
    as_of: Optional[datetime] = None,
) -> Dict[str, Any]:
    """Compute backlog health metrics."""
    if not issues:
        return {"total": 0, "error": "No issues loaded"}

    if as_of is None:
        as_of = datetime.now()

    total = len(issues)
    estimated = sum(1 for i in issues if i.get("estimated"))
    unestimated = total - estimated
    pct_estimated = round(estimated / total * 100, 1) if total else 0

    # Age buckets (days since created)
    age_buckets = {"0-7d": 0, "7-30d": 0, "30-90d": 0, "90d+": 0}
    for i in issues:
        c = i.get("created")
        if not c:
            continue
        days = (as_of - c).days
        if days <= 7:
            age_buckets["0-7d"] += 1
        elif days <= 30:
            age_buckets["7-30d"] += 1
        elif days <= 90:
            age_buckets["30-90d"] += 1
        else:
            age_buckets["90d+"] += 1

    # Stale (no update in N days)
    stale = []
    for i in issues:
        u = i.get("updated") or i.get("created")
        if not u:
            continue
        if (as_of - u).days >= stale_days:
            summary_short = (i.get("summary") or "—")[:50]
            stale.append({"id": i["id"], "summary": summary_short, "days_since_update": (as_of - u).days})

    # By priority
    by_priority: Dict[str, int] = defaultdict(int)
    for i in issues:
        by_priority[i.get("priority") or "—"] += 1
    by_priority = dict(sorted(by_priority.items(), key=lambda x: -x[1]))

    # By type
    by_type: Dict[str, int] = defaultdict(int)
    for i in issues:
        by_type[i.get("type") or "—"] += 1
    by_type = dict(sorted(by_type.items(), key=lambda x: -x[1]))

    # Hygiene
    missing_summary = [i["id"] for i in issues if not i.get("has_summary")]
    missing_description = [i["id"] for i in issues if not i.get("has_description")]
    missing_assignee = [i["id"] for i in issues if not i.get("has_assignee")]
    missing_points = [i["id"] for i in issues if not i.get("estimated")]

    total_points = sum(i.get("points") or 0 for i in issues)

    return {
        "total": total,
        "estimated": estimated,
        "unestimated": unestimated,
        "pct_estimated": pct_estimated,
        "total_points": round(total_points, 1),
        "age_buckets": age_buckets,
        "stale_days": stale_days,
        "stale_count": len(stale),
        "stale_sample": stale[:15],
        "by_priority": by_priority,
        "by_type": by_type,
        "hygiene": {
            "missing_summary": len(missing_summary),
            "missing_summary_ids": missing_summary[:20],
            "missing_description": len(missing_description),
            "missing_description_ids": missing_description[:20],
            "missing_assignee": len(missing_assignee),
            "missing_assignee_ids": missing_assignee[:20],
            "missing_points": len(missing_points),
        },
        "as_of": as_of.strftime("%Y-%m-%d"),
    }


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def print_report(result: Dict[str, Any]) -> None:
    """Pretty-print backlog health report."""
    if result.get("error"):
        print(f"\n   ⚠️  {result['error']}\n")
        return

    total = result["total"]
    print("\n" + "=" * 78)
    print("📋 BACKLOG HEALTH REPORT")
    print("=" * 78)

    print(f"\n   Total issues:   {total}")
    print(f"   Estimated:     {result['estimated']} ({result['pct_estimated']}%)  |  Unestimated: {result['unestimated']}")
    if result.get("total_points"):
        print(f"   Total points:  {result['total_points']:.0f}")
    print(f"   As of:         {result['as_of']}")

    # Age distribution
    print(f"\n{'─'*78}")
    print(f"\n   AGE (days since created):\n")
    buckets = result.get("age_buckets", {})
    max_b = max(buckets.values()) or 1
    for label in ["0-7d", "7-30d", "30-90d", "90d+"]:
        c = buckets.get(label, 0)
        bar = "█" * int(c / max_b * 25) + "░" * (25 - int(c / max_b * 25))
        print(f"   {label:<8} {bar} {c}")

    # Stale
    stale_count = result.get("stale_count", 0)
    print(f"\n{'─'*78}")
    print(f"\n   STALE (no update in {result.get('stale_days', 14)}+ days): {stale_count}\n")
    for s in result.get("stale_sample", [])[:8]:
        sm = (s.get("summary") or "—")[:44]
        print(f"   • {s['id']}  ({s['days_since_update']}d)  {sm}")
    if stale_count > 8:
        print(f"   ... and {stale_count - 8} more")

    # By priority / type
    print(f"\n{'─'*78}")
    print(f"\n   BY PRIORITY:          BY TYPE:\n")
    pri = result.get("by_priority", {})
    typ = result.get("by_type", {})
    max_pri = max(pri.values()) or 1
    max_typ = max(typ.values()) or 1
    keys_pri = list(pri.keys())[:8]
    keys_typ = list(typ.keys())[:8]
    for i in range(max(len(keys_pri), len(keys_typ))):
        p_k = keys_pri[i] if i < len(keys_pri) else ""
        p_v = pri.get(p_k, 0) if p_k else 0
        t_k = keys_typ[i] if i < len(keys_typ) else ""
        t_v = typ.get(t_k, 0) if t_k else 0
        bar_pri = "█" * int(p_v / max_pri * 12) + "░" * (12 - int(p_v / max_pri * 12)) if p_k else ""
        bar_typ = "█" * int(t_v / max_typ * 12) + "░" * (12 - int(t_v / max_typ * 12)) if t_k else ""
        print(f"   {p_k[:10]:<10} {bar_pri} {p_v:<4}   {t_k[:10]:<10} {bar_typ} {t_v}")

    # Hygiene
    h = result.get("hygiene", {})
    print(f"\n{'─'*78}")
    print(f"\n   HYGIENE (fix before planning):\n")
    print(f"   Missing summary:     {h.get('missing_summary', 0)}")
    print(f"   Missing description: {h.get('missing_description', 0)}")
    print(f"   No assignee:        {h.get('missing_assignee', 0)}")
    print(f"   Unestimated:        {h.get('missing_points', 0)}")
    if any([h.get("missing_summary"), h.get("missing_assignee")]):
        sample = (h.get("missing_summary_ids") or [])[:5]
        if sample:
            print(f"\n   Sample (missing summary or assignee): {', '.join(sample)}")

    print(f"\n{'─'*78}")
    print(f"\n   💡 Export from Jira: JQL e.g. project = X AND sprint = EMPTY ORDER BY rank")
    print(f"   Complements: sprint-velocity-tracker, capacity-planner, delivery-completion-forecaster")
    print("\n" + "=" * 78)


def generate_markdown(result: Dict[str, Any]) -> str:
    """Generate Markdown report."""
    if result.get("error"):
        return f"# Backlog Health Report\n\n**Error:** {result['error']}\n"

    lines = []
    lines.append("# Backlog Health Report")
    lines.append("")
    lines.append(f"**Total issues:** {result['total']}  ")
    lines.append(f"**Estimated:** {result['estimated']} ({result['pct_estimated']}%)  ")
    lines.append(f"**Total points:** {result.get('total_points', 0):.0f}  ")
    lines.append(f"**As of:** {result['as_of']}  ")
    lines.append("")

    lines.append("## Age (days since created)")
    lines.append("")
    for label, c in result.get("age_buckets", {}).items():
        lines.append(f"- **{label}:** {c}")
    lines.append("")

    lines.append("## Stale (no update in " + str(result.get("stale_days", 14)) + "+ days)")
    lines.append("")
    lines.append(f"**Count:** {result.get('stale_count', 0)}  ")
    for s in result.get("stale_sample", [])[:10]:
        lines.append(f"- {s['id']} ({s['days_since_update']}d) — {s['summary'][:60]}")
    lines.append("")

    lines.append("## By priority")
    lines.append("")
    for k, v in result.get("by_priority", {}).items():
        lines.append(f"- **{k}:** {v}")
    lines.append("")

    lines.append("## By type")
    lines.append("")
    for k, v in result.get("by_type", {}).items():
        lines.append(f"- **{k}:** {v}")
    lines.append("")

    lines.append("## Hygiene")
    lines.append("")
    h = result.get("hygiene", {})
    lines.append(f"- Missing summary: {h.get('missing_summary', 0)}")
    lines.append(f"- Missing description: {h.get('missing_description', 0)}")
    lines.append(f"- No assignee: {h.get('missing_assignee', 0)}")
    lines.append(f"- Unestimated: {h.get('missing_points', 0)}")
    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Backlog health report from Jira (or similar) CSV export: age, "
                    "estimation, priority/type, stale, hygiene.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --csv backlog.csv
  %(prog)s --csv backlog.csv --stale-days 21 --markdown report.md
  %(prog)s --csv backlog.csv --points customfield_10016
        """,
    )

    parser.add_argument("--csv", "-c", type=str, required=True, help="CSV export of backlog issues")
    parser.add_argument("--stale-days", type=int, default=14,
                        help="Consider stale if no update in this many days")
    parser.add_argument("--as-of", type=str, help="Reference date (YYYY-MM-DD). Default: today")
    parser.add_argument("--key", type=str, default="key", help="Issue key column name")
    parser.add_argument("--summary", type=str, default="summary", help="Summary/title column")
    parser.add_argument("--description", type=str, default="description", help="Description column")
    parser.add_argument("--assignee", type=str, default="assignee", help="Assignee column")
    parser.add_argument("--priority", type=str, default="priority", help="Priority column")
    parser.add_argument("--type", type=str, dest="type_col", default="issuetype",
                        help="Issue type column (e.g. issuetype)")
    parser.add_argument("--status", type=str, default="status", help="Status column")
    parser.add_argument("--created", type=str, default="created", help="Created date column")
    parser.add_argument("--updated", type=str, default="updated", help="Updated date column")
    parser.add_argument("--points", type=str, default="story points",
                        help="Story points column (e.g. customfield_10016)")
    parser.add_argument("--markdown", type=str, help="Write Markdown report to file")
    parser.add_argument("--output", "-o", type=str, help="Write JSON results to file")
    args = parser.parse_args()

    as_of_dt = parse_date(args.as_of) if args.as_of else None

    try:
        issues = load_backlog(
            args.csv,
            id_col=args.key,
            summary_col=args.summary,
            description_col=args.description,
            assignee_col=args.assignee,
            priority_col=args.priority,
            type_col=args.type_col,
            status_col=args.status,
            created_col=args.created,
            updated_col=args.updated,
            points_col=args.points,
        )
    except Exception as e:
        print(f"Error loading CSV: {e}", file=sys.stderr)
        return 1

    if not issues:
        print("No issues found in CSV.", file=sys.stderr)
        return 1

    result = analyze_backlog(issues, stale_days=args.stale_days, as_of=as_of_dt)
    print_report(result)

    if args.markdown:
        with open(args.markdown, "w", encoding="utf-8") as f:
            f.write(generate_markdown(result))
        print(f"\n📄 Markdown saved to {args.markdown}")

    if args.output and not result.get("error"):
        out = {k: v for k, v in result.items() if k != "error"}
        with open(args.output, "w") as f:
            json.dump(out, f, indent=2)
        print(f"\n📁 Results saved to {args.output}")

    return 0 if not result.get("error") else 1


if __name__ == "__main__":
    sys.exit(main())
