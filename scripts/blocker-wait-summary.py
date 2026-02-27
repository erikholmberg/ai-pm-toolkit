#!/usr/bin/env python3
"""
Blocker / Wait Time Summary

Summarize wait time (created → started) and optional blocker reasons from
ticket data. Complements cycle-lead-time-analyzer: use it for retros and
prioritization when "why did this sit in backlog?" matters.

Wait time = time from ticket created until work started (in progress).
When started is missing, wait is inferred as lead_time (all time is "wait").

Usage:
    # From CSV (created, started, done — same columns as cycle-lead-time-analyzer)
    python blocker-wait-summary.py --csv tickets.csv

    # With blocker reason column
    python blocker-wait-summary.py --csv tickets.csv --blocker blocker_reason

    # Custom column names
    python blocker-wait-summary.py --csv tickets.csv \\
        --created created_at --started in_progress --done resolutiondate

    # Last N weeks (by completed date)
    python blocker-wait-summary.py --csv tickets.csv --weeks 8

    # Group by type for wait breakdown
    python blocker-wait-summary.py --csv tickets.csv --group-by type

    # JSON output
    python blocker-wait-summary.py --csv tickets.csv --output report.json

CSV format (header row required):
    id,created,started,done,type,blocker_reason
    PROJ-101,2025-01-02,2025-01-08,2025-01-12,Bug,
    PROJ-102,2025-01-03,2025-01-10,2025-01-15,Feature,Waiting on API
    PROJ-103,2025-01-05,2025-01-05,2025-01-09,Chore,Design review

    Required: created, done. Optional: started (if missing, wait = lead time), blocker_reason, type.

Requirements:
    None (stdlib only). Optional: python-dateutil for date parsing.
"""

import argparse
import csv
import json
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


def _col(fieldnames: List[str], *aliases: str) -> Optional[str]:
    lower_map = {f.lower().strip(): f for f in fieldnames}
    for alias in aliases:
        if alias.lower().strip() in lower_map:
            return lower_map[alias.lower().strip()]
    return None


# ---------------------------------------------------------------------------
# Load tickets and compute wait
# ---------------------------------------------------------------------------

def load_tickets(
    path: str,
    created_col: str = "created",
    started_col: str = "started",
    done_col: str = "done",
    id_col: str = "id",
    blocker_col: Optional[str] = None,
    group_by_col: Optional[str] = None,
    weeks: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """Load tickets and compute wait_days = max(0, started - created). If no started, wait = lead (all wait)."""
    tickets: List[Dict[str, Any]] = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fields = reader.fieldnames or []

        c_created = _col(fields, created_col, "created", "created_at", "createdate", "created_date")
        c_started = _col(fields, started_col, "started", "in_progress", "indev", "started_at")
        c_done = _col(fields, done_col, "done", "resolutiondate", "completed", "closed", "completed_at")
        c_id = _col(fields, id_col, "id", "key", "ticket_id", "issue_key")
        c_blocker = _col(fields, blocker_col or "blocker", "blocker_reason", "blocked_reason", "wait_reason") if blocker_col else _col(fields, "blocker_reason", "blocker", "blocked_reason")
        c_group = _col(fields, group_by_col or "type", "type", "issue_type", "category", "team") if group_by_col else _col(fields, "type", "issue_type", "category")

        for row in reader:
            created = parse_date(row.get(c_created or "created", "") or "")
            done = parse_date(row.get(c_done or "done", "") or "")
            started = parse_date(row.get(c_started or "started", "") or "")

            if not created or not done or done < created:
                continue

            lead_days = (done - created).total_seconds() / (24 * 3600)
            if started and created <= started <= done:
                wait_days = (started - created).total_seconds() / (24 * 3600)
                cycle_days = (done - started).total_seconds() / (24 * 3600)
            else:
                wait_days = lead_days
                cycle_days = 0.0

            blocker_reason = (row.get(c_blocker or "blocker_reason", "") or "").strip() if c_blocker else None
            if not blocker_reason:
                blocker_reason = "—"
            group_val = (row.get(c_group or "type", "") or "").strip() if c_group else "—"

            tickets.append({
                "id": (row.get(c_id or "id", "") or "").strip() or str(len(tickets) + 1),
                "created": created,
                "started": started,
                "done": done,
                "lead_time_days": round(lead_days, 2),
                "wait_days": round(wait_days, 2),
                "cycle_time_days": round(cycle_days, 2),
                "wait_pct": round(wait_days / lead_days * 100, 1) if lead_days else 0,
                "blocker_reason": blocker_reason,
                "group": group_val,
            })

    # If --weeks filter: only include tickets completed in last N weeks
    if weeks and tickets:
        now = datetime.now()
        cutoff = now.replace(hour=0, minute=0, second=0, microsecond=0)
        from datetime import timedelta
        cutoff = cutoff - timedelta(days=weeks * 7)
        tickets = [t for t in tickets if t["done"] and t["done"] >= cutoff]

    return tickets


def percentile(values: List[float], p: float) -> float:
    if not values:
        return 0.0
    sorted_v = sorted(values)
    n = len(sorted_v)
    idx = p / 100.0 * (n - 1)
    lo = int(idx)
    hi = min(lo + 1, n - 1)
    w = idx - lo
    return round(sorted_v[lo] * (1 - w) + sorted_v[hi] * w, 2)


def analyze(
    tickets: List[Dict[str, Any]],
    group_by: Optional[str] = None,
) -> Dict[str, Any]:
    """Compute wait-time stats, % of lead in wait, optional blocker and group breakdown."""
    if not tickets:
        return {"n": 0, "error": "No tickets"}

    wait_list = [t["wait_days"] for t in tickets]
    lead_list = [t["lead_time_days"] for t in tickets]
    total_lead = sum(lead_list)
    total_wait = sum(wait_list)
    n = len(tickets)
    avg_wait = total_wait / n if n else 0
    wait_pct_of_lead = (total_wait / total_lead * 100) if total_lead else 0

    # By blocker reason
    by_blocker: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for t in tickets:
        key = (t.get("blocker_reason") or "—").strip() or "—"
        by_blocker[key].append(t)

    blocker_stats = []
    for reason, items in by_blocker.items():
        if reason == "—":
            continue
        w_total = sum(i["wait_days"] for i in items)
        l_total = sum(i["lead_time_days"] for i in items)
        blocker_stats.append({
            "reason": reason,
            "count": len(items),
            "total_wait_days": round(w_total, 1),
            "avg_wait_days": round(w_total / len(items), 1),
            "wait_pct_of_lead": round(w_total / l_total * 100, 1) if l_total else 0,
        })
    blocker_stats.sort(key=lambda x: -x["total_wait_days"])

    # By group (type/category)
    by_group: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for t in tickets:
        key = (t.get("group") or "—").strip() or "—"
        by_group[key].append(t)

    group_stats = []
    for grp, items in by_group.items():
        w_total = sum(i["wait_days"] for i in items)
        l_total = sum(i["lead_time_days"] for i in items)
        group_stats.append({
            "group": grp,
            "count": len(items),
            "total_wait_days": round(w_total, 1),
            "avg_wait_days": round(w_total / len(items), 1),
            "wait_pct_of_lead": round(w_total / l_total * 100, 1) if l_total else 0,
        })
    group_stats.sort(key=lambda x: -x["total_wait_days"])

    # Wait by completed week (trend)
    by_week: Dict[str, List[float]] = defaultdict(list)
    for t in tickets:
        d = t.get("done")
        if d:
            iso = d.isocalendar()
            key = f"{iso[0]}-W{iso[1]:02d}"
            by_week[key].append(t["wait_days"])
    trend = []
    for week in sorted(by_week.keys())[-12:]:
        vals = by_week[week]
        trend.append({"week": week, "avg_wait_days": round(sum(vals) / len(vals), 1), "count": len(vals)})

    return {
        "n": n,
        "total_wait_days": round(total_wait, 1),
        "total_lead_days": round(total_lead, 1),
        "avg_wait_days": round(avg_wait, 1),
        "wait_pct_of_lead": round(wait_pct_of_lead, 1),
        "wait": {
            "min": round(min(wait_list), 1) if wait_list else 0,
            "max": round(max(wait_list), 1) if wait_list else 0,
            "median": percentile(wait_list, 50),
            "p90": percentile(wait_list, 90),
            "p95": percentile(wait_list, 95),
        },
        "by_blocker": blocker_stats,
        "by_group": group_stats,
        "trend": trend,
    }


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def print_report(result: Dict[str, Any]) -> None:
    """Pretty-print blocker/wait summary."""
    if result.get("error"):
        print(f"\n   ⚠️  {result['error']}\n")
        return

    print("\n" + "=" * 78)
    print("⏳ BLOCKER / WAIT TIME SUMMARY")
    print("=" * 78)

    n = result["n"]
    print(f"\n   Tickets: {n}")
    print(f"   Total wait:    {result['total_wait_days']:.1f} days (time from created → started)")
    print(f"   Total lead:    {result['total_lead_days']:.1f} days")
    print(f"   Wait as % of lead: {result['wait_pct_of_lead']:.0f}%")
    print(f"   Avg wait per ticket: {result['avg_wait_days']:.1f} days")

    w = result.get("wait", {})
    print(f"\n   Wait distribution:  min {w.get('min', 0):.1f}  median {w.get('median', 0):.1f}  p90 {w.get('p90', 0):.1f}  p95 {w.get('p95', 0):.1f}  max {w.get('max', 0):.1f} days")

    # Bar: wait % of lead
    bar_w = 35
    pct = min(100, result["wait_pct_of_lead"])
    filled = int(pct / 100 * bar_w)
    bar = "█" * filled + "░" * (bar_w - filled)
    print(f"\n   Wait % of lead: [{bar}] {result['wait_pct_of_lead']:.0f}%")

    if result.get("by_blocker"):
        print(f"\n{'─'*78}")
        print(f"\n   TOP BLOCKERS (by total wait):\n")
        print(f"   {'Reason':<28} {'Count':>6} {'Total wait':>10} {'Avg wait':>10} {'% of lead'}")
        print(f"   {'─'*28} {'─'*6} {'─'*10} {'─'*10} {'─'*8}")
        for b in result["by_blocker"][:10]:
            print(f"   {b['reason'][:28]:<28} {b['count']:>6} {b['total_wait_days']:>10.1f} {b['avg_wait_days']:>10.1f} {b['wait_pct_of_lead']:>7.0f}%")

    if result.get("by_group"):
        print(f"\n{'─'*78}")
        print(f"\n   WAIT BY GROUP:\n")
        print(f"   {'Group':<20} {'Count':>6} {'Total wait':>10} {'Avg wait':>10} {'% of lead'}")
        print(f"   {'─'*20} {'─'*6} {'─'*10} {'─'*10} {'─'*8}")
        for g in result["by_group"]:
            print(f"   {g['group'][:20]:<20} {g['count']:>6} {g['total_wait_days']:>10.1f} {g['avg_wait_days']:>10.1f} {g['wait_pct_of_lead']:>7.0f}%")

    if result.get("trend"):
        print(f"\n{'─'*78}")
        print(f"\n   WAIT TREND (avg wait by completed week):\n")
        for t in result["trend"][-8:]:
            bar_w = 25
            mx = max(x["avg_wait_days"] for x in result["trend"]) or 1
            filled = int(t["avg_wait_days"] / mx * bar_w)
            bar = "█" * filled + "░" * (bar_w - filled)
            print(f"   {t['week']:<10} {bar} {t['avg_wait_days']:.1f} days (n={t['count']})")

    print(f"\n{'─'*78}")
    print(f"\n   💡 Reduce wait: limit WIP, unblock dependencies, clarify priorities.")
    print(f"   Complements: cycle-lead-time-analyzer, throughput-wip-analyzer, retro-action-tracker")
    print("\n" + "=" * 78)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Blocker / wait time summary from ticket created→started→done. "
                    "Complements cycle-lead-time-analyzer for retros and prioritization.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --csv tickets.csv
  %(prog)s --csv tickets.csv --blocker blocker_reason --group-by type --weeks 8
  %(prog)s --csv tickets.csv --output report.json
        """,
    )

    parser.add_argument("--csv", "-c", type=str, required=True, help="CSV file (created, started, done)")
    parser.add_argument("--created", type=str, default="created", help="Created date column")
    parser.add_argument("--started", type=str, default="started", help="Started / in-progress date column")
    parser.add_argument("--done", type=str, default="done", help="Done / completed date column")
    parser.add_argument("--id", type=str, default="id", help="ID column")
    parser.add_argument("--blocker", type=str, default=None, help="Blocker reason column (optional)")
    parser.add_argument("--group-by", type=str, default=None, help="Group wait by column (e.g. type)")
    parser.add_argument("--weeks", type=int, default=None, help="Only tickets completed in last N weeks")

    parser.add_argument("--output", "-o", type=str, help="Write JSON results to file")
    args = parser.parse_args()

    try:
        tickets = load_tickets(
            args.csv,
            created_col=args.created,
            started_col=args.started,
            done_col=args.done,
            id_col=args.id,
            blocker_col=args.blocker,
            group_by_col=args.group_by,
            weeks=args.weeks,
        )
    except Exception as e:
        print(f"Error loading CSV: {e}", file=sys.stderr)
        return 1

    if not tickets:
        print("No tickets found (need created and done dates).", file=sys.stderr)
        return 1

    result = analyze(tickets, group_by=args.group_by)

    print_report(result)

    if args.output:
        out = {k: v for k, v in result.items() if k != "error"}
        with open(args.output, "w") as f:
            json.dump(out, f, indent=2)
        print(f"\n📁 Results saved to {args.output}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
