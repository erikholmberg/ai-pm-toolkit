#!/usr/bin/env python3
"""
Retro Action Item Tracker

Track sprint retrospective action items with completion rate, aging (e.g. open
>2 sprints), and breakdown by owner. Complements incident-postmortem (incident
actions); this is for continuous improvement from retros.

Outputs a "retro follow-through" score so teams can see whether they close
the loop on what they committed to in retros.

Usage:
    # From CSV
    python retro-action-tracker.py --csv retro-actions.csv

    # With reference date for aging (default: today)
    python retro-action-tracker.py --csv retro-actions.csv --as-of 2025-08-15

    # With current sprint for "sprints open" aging
    python retro-action-tracker.py --csv retro-actions.csv --current-sprint S8

    # Markdown report
    python retro-action-tracker.py --csv retro-actions.csv --markdown report.md

    # JSON output
    python retro-action-tracker.py --csv retro-actions.csv --output report.json

CSV format (header row required):
    id,description,owner,created,sprint_created,status,priority
    1,Add integration tests for checkout,Eng,2025-07-01,S5,open,P1
    2,Document API auth flow,Platform,2025-07-15,S6,done,P2
    3,Reduce standup to 10 min,Team,2025-08-01,S7,open,P1

    Required: description, status (open/done). Optional: owner, created, sprint_created, priority.
    created = date (YYYY-MM-DD) for days-old aging; sprint_created = sprint label for sprints-open.

JSON format:
    {
      "items": [
        {"description": "Add integration tests", "owner": "Eng", "sprint_created": "S5", "status": "open"},
        {"description": "Document API auth", "owner": "Platform", "sprint_created": "S6", "status": "done"}
      ],
      "current_sprint": "S8"
    }

Requirements:
    None (stdlib only). Optional: python-dateutil for date parsing.
"""

import argparse
import csv
import json
import re
import sys
from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Date parsing
# ---------------------------------------------------------------------------

def parse_date(s: str) -> Optional[datetime]:
    if not s or not s.strip():
        return None
    s = s.strip()
    try:
        from dateutil import parser as date_parser
        return date_parser.parse(s)
    except ImportError:
        pass
    except Exception:
        pass
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


def _sprint_order(s: str) -> Tuple[int, int]:
    """Extract numeric parts from sprint label for ordering (e.g. S5 -> 5, S7 -> 7)."""
    if not s or not isinstance(s, str):
        return (0, 0)
    s = s.strip()
    nums = re.findall(r"\d+", s)
    if nums:
        return (int(nums[0]), len(s))
    return (0, 0)


def sprints_between(sprint_created: Optional[str], current_sprint: Optional[str]) -> Optional[int]:
    """Approximate number of sprints between created and current. None if we can't compute."""
    if not sprint_created or not current_sprint:
        return None
    a = _sprint_order(sprint_created)
    b = _sprint_order(current_sprint)
    if a[0] == 0 or b[0] == 0:
        return None
    return max(0, b[0] - a[0])


# ---------------------------------------------------------------------------
# Load and analyze
# ---------------------------------------------------------------------------

def _col(fieldnames: List[str], *aliases: str) -> Optional[str]:
    lower_map = {f.lower().strip(): f for f in fieldnames}
    for alias in aliases:
        if alias.lower().strip() in lower_map:
            return lower_map[alias.lower().strip()]
    return None


def load_csv(
    path: str,
    as_of_date: Optional[datetime] = None,
    current_sprint: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Load retro action items from CSV and enrich with aging."""
    items: List[Dict[str, Any]] = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fields = reader.fieldnames or []

        c_id = _col(fields, "id", "key", "action_id")
        c_desc = _col(fields, "description", "action", "item", "title")
        c_owner = _col(fields, "owner", "assignee", "responsible")
        c_created = _col(fields, "created", "created_at", "date", "created_date")
        c_sprint = _col(fields, "sprint_created", "sprint", "retro_sprint", "cycle")
        c_status = _col(fields, "status", "state", "resolution")
        c_priority = _col(fields, "priority", "pri")

        for row in reader:
            desc = (row.get(c_desc or "description", "") or "").strip()
            if not desc:
                continue

            status_raw = (row.get(c_status or "status", "") or "").strip().lower()
            status = "done" if status_raw in ("done", "closed", "complete", "completed", "resolved", "1", "yes") else "open"

            created_str = (row.get(c_created or "created", "") or "").strip()
            created_dt = parse_date(created_str) if created_str else None
            sprint_created = (row.get(c_sprint or "sprint_created", "") or "").strip() or None
            owner = (row.get(c_owner or "owner", "") or "").strip() or "Unassigned"
            priority = (row.get(c_priority or "priority", "") or "").strip().upper() or None

            # Aging
            days_open: Optional[int] = None
            if created_dt and status == "open":
                ref = as_of_date or datetime.now()
                delta = (ref - created_dt).days
                days_open = max(0, delta)

            sprints_open: Optional[int] = None
            if sprint_created and current_sprint and status == "open":
                sprints_open = sprints_between(sprint_created, current_sprint)

            items.append({
                "id": (row.get(c_id or "id", "") or "").strip() or str(len(items) + 1),
                "description": desc,
                "owner": owner,
                "created": created_dt,
                "created_str": created_str or "",
                "sprint_created": sprint_created,
                "status": status,
                "priority": priority,
                "days_open": days_open,
                "sprints_open": sprints_open,
            })

    return items


def load_json(
    path: str,
    as_of_date: Optional[datetime] = None,
    current_sprint: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Load retro action items from JSON."""
    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    raw = data.get("items", data) if isinstance(data, dict) else data
    if not isinstance(raw, list):
        raw = [data]

    current_sprint = current_sprint or (data.get("current_sprint") if isinstance(data, dict) else None)
    items: List[Dict[str, Any]] = []

    for i, row in enumerate(raw):
        if isinstance(row, str):
            row = {"description": row, "status": "open"}
        desc = (row.get("description", row.get("action", "")) or "").strip()
        if not desc:
            continue

        status_raw = (row.get("status", row.get("state", "open")) or "open").lower()
        status = "done" if status_raw in ("done", "closed", "complete", "completed", "resolved", "1", "yes") else "open"

        created_str = row.get("created", row.get("created_at", "")) or ""
        created_dt = parse_date(created_str) if created_str else None
        sprint_created = (row.get("sprint_created", row.get("sprint", "")) or "").strip() or None
        owner = (row.get("owner", row.get("assignee", "")) or "").strip() or "Unassigned"
        priority = (row.get("priority", "") or "").strip().upper() or None

        days_open = None
        if created_dt and status == "open":
            ref = as_of_date or datetime.now()
            days_open = max(0, (ref - created_dt).days)

        sprints_open = None
        if sprint_created and current_sprint and status == "open":
            sprints_open = sprints_between(sprint_created, current_sprint)

        items.append({
            "id": str(row.get("id", i + 1)),
            "description": desc,
            "owner": owner,
            "created": created_dt,
            "created_str": created_str,
            "sprint_created": sprint_created,
            "status": status,
            "priority": priority,
            "days_open": days_open,
            "sprints_open": sprints_open,
        })

    return items


def analyze(items: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Compute completion rate, aging stats, by-owner breakdown, follow-through score."""
    total = len(items)
    open_items = [i for i in items if i["status"] == "open"]
    done_items = [i for i in items if i["status"] == "done"]
    n_open = len(open_items)
    n_done = len(done_items)
    completion_pct = round(n_done / total * 100, 1) if total else 0

    # Follow-through score and label
    if completion_pct >= 80:
        follow_through = "🟢 Strong"
        follow_through_note = "Most retro actions are being closed."
    elif completion_pct >= 50:
        follow_through = "🟡 Mixed"
        follow_through_note = "About half of retro actions are closed. Review open items."
    else:
        follow_through = "🔴 Weak"
        follow_through_note = "Many retro actions remain open. Prioritize or close the loop."

    # By owner
    by_owner: Dict[str, Dict[str, int]] = defaultdict(lambda: {"open": 0, "done": 0})
    for i in items:
        by_owner[i["owner"]]["open" if i["status"] == "open" else "done"] += 1
    by_owner = dict(sorted(by_owner.items(), key=lambda x: -(x[1]["open"] + x[1]["done"])))

    # Aging: open items
    open_days = [i["days_open"] for i in open_items if i.get("days_open") is not None]
    open_sprints = [i["sprints_open"] for i in open_items if i.get("sprints_open") is not None]
    max_days_open = max(open_days) if open_days else None
    max_sprints_open = max(open_sprints) if open_sprints else None
    stale_count_days = sum(1 for d in open_days if d and d > 14)  # >2 weeks
    stale_count_sprints = sum(1 for s in open_sprints if s and s >= 2)  # 2+ sprints

    return {
        "total": total,
        "n_open": n_open,
        "n_done": n_done,
        "completion_pct": completion_pct,
        "follow_through": follow_through,
        "follow_through_note": follow_through_note,
        "by_owner": by_owner,
        "open_items": open_items,
        "done_items": done_items,
        "max_days_open": max_days_open,
        "max_sprints_open": max_sprints_open,
        "stale_count_days": stale_count_days,
        "stale_count_sprints": stale_count_sprints,
        "has_sprint_aging": bool(open_sprints),
        "has_date_aging": bool(open_days),
    }


# ---------------------------------------------------------------------------
# Markdown
# ---------------------------------------------------------------------------

def generate_markdown(result: Dict[str, Any]) -> str:
    """Generate Markdown report."""
    lines = []
    lines.append("# Retro Action Item Tracker")
    lines.append("")
    lines.append(f"**Completion:** {result['n_done']}/{result['total']} ({result['completion_pct']:.0f}%)  ")
    lines.append(f"**Follow-through:** {result['follow_through']}  ")
    lines.append("")
    lines.append("## By owner")
    lines.append("")
    lines.append("| Owner | Open | Done | Total |")
    lines.append("|-------|------|------|-------|")
    for owner, counts in result["by_owner"].items():
        lines.append(f"| {owner} | {counts['open']} | {counts['done']} | {counts['open'] + counts['done']} |")
    lines.append("")

    if result["open_items"]:
        lines.append("## Open items")
        lines.append("")
        for i in result["open_items"]:
            age = ""
            if i.get("sprints_open") is not None:
                age = f" ({i['sprints_open']} sprint(s) open)"
            elif i.get("days_open") is not None:
                age = f" ({i['days_open']} days open)"
            lines.append(f"- [ ] **{i['description']}** — {i['owner']}{age}")
        lines.append("")

    lines.append("---")
    lines.append("*Close the loop: review open items in the next retro.*")
    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Terminal report
# ---------------------------------------------------------------------------

def print_report(result: Dict[str, Any]) -> None:
    """Pretty-print retro action tracker report."""
    print("\n" + "=" * 78)
    print("🔄 RETRO ACTION ITEM TRACKER")
    print("=" * 78)

    total = result["total"]
    n_done = result["n_done"]
    n_open = result["n_open"]
    pct = result["completion_pct"]

    bar_w = 30
    filled = int(pct / 100 * bar_w) if total else 0
    bar = "█" * filled + "░" * (bar_w - filled)
    print(f"\n   Completion: [{bar}] {n_done}/{total} ({pct:.0f}%)")
    print(f"   Follow-through: {result['follow_through']}")
    print(f"   {result['follow_through_note']}")

    # Aging summary
    if result["stale_count_days"] or result["stale_count_sprints"]:
        print(f"\n   Aging: ", end="")
        if result["stale_count_sprints"]:
            print(f"{result['stale_count_sprints']} item(s) open 2+ sprints", end="")
        if result["stale_count_days"] and result["stale_count_sprints"]:
            print(" | ", end="")
        if result["stale_count_days"]:
            print(f"{result['stale_count_days']} item(s) open >14 days", end="")
        print()

    # By owner
    print(f"\n{'─'*78}")
    print(f"\n   BY OWNER:\n")
    print(f"   {'Owner':<20} {'Open':>6} {'Done':>6} {'Total':>6}")
    print(f"   {'─'*20} {'─'*6} {'─'*6} {'─'*6}")
    for owner, counts in result["by_owner"].items():
        print(f"   {owner[:20]:<20} {counts['open']:>6} {counts['done']:>6} {counts['open']+counts['done']:>6}")

    # Open items (with aging)
    if result["open_items"]:
        print(f"\n{'─'*78}")
        print(f"\n   OPEN ITEMS (prioritize in next retro):\n")
        print(f"   {'#':<3} {'Description':<36} {'Owner':<12} {'Age'}")
        print(f"   {'─'*3} {'─'*36} {'─'*12} {'─'*10}")

        for i, item in enumerate(result["open_items"][:20], 1):
            age = ""
            if item.get("sprints_open") is not None:
                age = f"{item['sprints_open']} sprint(s)"
            elif item.get("days_open") is not None:
                age = f"{item['days_open']} days"
            print(f"   {i:<3} {item['description'][:36]:<36} {item['owner'][:12]:<12} {age}")

        if len(result["open_items"]) > 20:
            print(f"   ... and {len(result['open_items']) - 20} more")

    print(f"\n{'─'*78}")
    print(f"\n   💡 Review open items every retro; assign owners; close or drop stale items.")
    print(f"   Complements: incident-postmortem (incident actions), space-team-health (retro input)")
    print("\n" + "=" * 78)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Track sprint retro action items: completion rate, aging, by owner. "
                    "Retro follow-through score.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --csv retro-actions.csv
  %(prog)s --csv retro-actions.csv --current-sprint S8 --as-of 2025-08-15
  %(prog)s --csv retro-actions.csv --markdown report.md --output report.json
        """,
    )

    parser.add_argument("--csv", "-c", type=str, help="CSV file of action items")
    parser.add_argument("--json", "-j", type=str, help="JSON file of action items")
    parser.add_argument("--as-of", type=str, help="Reference date for aging (YYYY-MM-DD)")
    parser.add_argument("--current-sprint", type=str, help="Current sprint label (for sprints-open aging)")

    parser.add_argument("--markdown", type=str, help="Write Markdown report to file")
    parser.add_argument("--output", "-o", type=str, help="Write JSON results to file")
    args = parser.parse_args()

    as_of_dt = parse_date(args.as_of) if args.as_of else None

    items: List[Dict[str, Any]] = []
    if args.csv:
        try:
            items = load_csv(args.csv, as_of_date=as_of_dt, current_sprint=args.current_sprint)
        except Exception as e:
            print(f"Error loading CSV: {e}", file=sys.stderr)
            return 1
    elif args.json:
        try:
            items = load_json(args.json, as_of_date=as_of_dt, current_sprint=args.current_sprint)
        except Exception as e:
            print(f"Error loading JSON: {e}", file=sys.stderr)
            return 1
    else:
        print("Error: provide --csv or --json.", file=sys.stderr)
        parser.print_help(sys.stderr)
        return 1

    if not items:
        print("No action items found.", file=sys.stderr)
        return 1

    result = analyze(items)

    print_report(result)

    if args.markdown:
        with open(args.markdown, "w", encoding="utf-8") as f:
            f.write(generate_markdown(result))
        print(f"\n📄 Markdown saved to {args.markdown}")

    if args.output:
        # JSON-serializable result (no datetime objects)
        out = {
            "total": result["total"],
            "n_open": result["n_open"],
            "n_done": result["n_done"],
            "completion_pct": result["completion_pct"],
            "follow_through": result["follow_through"],
            "by_owner": result["by_owner"],
            "open_items": [
                {
                    "id": i["id"],
                    "description": i["description"],
                    "owner": i["owner"],
                    "sprint_created": i.get("sprint_created"),
                    "days_open": i.get("days_open"),
                    "sprints_open": i.get("sprints_open"),
                    "priority": i.get("priority"),
                }
                for i in result["open_items"]
            ],
            "stale_count_days": result["stale_count_days"],
            "stale_count_sprints": result["stale_count_sprints"],
        }
        with open(args.output, "w") as f:
            json.dump(out, f, indent=2)
        print(f"\n📁 Results saved to {args.output}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
