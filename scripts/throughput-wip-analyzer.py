#!/usr/bin/env python3
"""
Throughput & WIP Analyzer

Compute throughput (completed items per week/sprint), WIP by state, and
flow efficiency from ticket/issue data. Complements cycle-lead-time-analyzer:
"how long" vs "how many" and "how much in progress."

Use for flow and WIP-limit discussions, sprint planning, and identifying
bottlenecks (high WIP, low throughput).

Usage:
    # Basic: CSV with id, state, completed (optional)
    python throughput-wip-analyzer.py --csv tickets.csv

    # Custom column names
    python throughput-wip-analyzer.py --csv tickets.csv \\
        --completed resolutiondate --state status --id key

    # Group throughput by week (default) or sprint
    python throughput-wip-analyzer.py --csv tickets.csv --period week
    python throughput-wip-analyzer.py --csv tickets.csv --period sprint --sprint-column sprint

    # Last N weeks only
    python throughput-wip-analyzer.py --csv tickets.csv --weeks 8

    # Output JSON
    python throughput-wip-analyzer.py --csv tickets.csv --output report.json

CSV format (header row required):
    id,state,created,started,completed,sprint
    PROJ-123,Done,2025-01-02,,2025-01-10,S1
    PROJ-124,In Progress,2025-01-05,2025-01-06,,S1
    PROJ-125,To Do,2025-01-08,,,

    Required: id. At least one of: completed (for throughput) or state (for WIP).
    Optional: state/status, created, started, completed, sprint (for --period sprint).

    - Rows with completed = empty count as WIP (current open work).
    - Throughput = count of rows with completed date, grouped by week or sprint.
    - WIP = count of rows with no completed date, grouped by state.

Requirements:
    None (stdlib only). Optional: python-dateutil for flexible date parsing.
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
# Load tickets
# ---------------------------------------------------------------------------

def load_tickets(
    path: str,
    id_col: str = "id",
    state_col: str = "state",
    completed_col: str = "completed",
    created_col: str = "created",
    started_col: str = "started",
    sprint_col: Optional[str] = None,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Load tickets from CSV. Returns (completed_list, wip_list).
    completed = has completed date; wip = no completed date (open).
    """
    completed: List[Dict[str, Any]] = []
    wip: List[Dict[str, Any]] = []

    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fields = reader.fieldnames or []

        c_id = _col(fields, "id", "key", "ticket_id", "issue_key")
        c_state = _col(fields, "state", "status", "stage")
        c_done = _col(fields, "completed", "done", "resolutiondate", "closed", "completed_at")
        c_created = _col(fields, "created", "created_at", "createdate")
        c_started = _col(fields, "started", "in_progress", "started_at")
        c_sprint = _col(fields, sprint_col or "sprint", "sprint_id", "cycle")

        for row in reader:
            tid = row.get(c_id or "id", "").strip() or str(len(completed) + len(wip) + 1)
            state = (row.get(c_state or "state", "") or "").strip() or "Unknown"
            done_str = (row.get(c_done or "completed", "") or "").strip()
            done_dt = parse_date(done_str) if done_str else None
            created_dt = parse_date(row.get(c_created or "created", "") or "") if c_created else None
            started_dt = parse_date(row.get(c_started or "started", "") or "") if c_started else None
            sprint = (row.get(c_sprint or "sprint", "") or "").strip() if c_sprint else None

            rec = {
                "id": tid,
                "state": state,
                "completed": done_dt,
                "created": created_dt,
                "started": started_dt,
                "sprint": sprint,
            }

            if done_dt:
                completed.append(rec)
            else:
                wip.append(rec)

    return completed, wip


# ---------------------------------------------------------------------------
# Throughput & WIP stats
# ---------------------------------------------------------------------------

def throughput_by_week(completed: List[Dict[str, Any]], weeks: Optional[int] = None) -> Dict[str, Any]:
    """Group completed tickets by ISO week. Optional: last N weeks only."""
    by_week: Dict[str, int] = defaultdict(int)
    for rec in completed:
        dt = rec.get("completed")
        if not dt:
            continue
        # ISO week: (year, week)
        iso = dt.isocalendar()
        key = f"{iso[0]}-W{iso[1]:02d}"
        by_week[key] += 1

    sorted_weeks = sorted(by_week.keys())
    if weeks and sorted_weeks:
        sorted_weeks = sorted_weeks[-weeks:]
        by_week = {k: by_week[k] for k in sorted_weeks if k in by_week}

    total = sum(by_week.values())
    avg_per_week = total / len(by_week) if by_week else 0
    return {
        "period_type": "week",
        "periods": sorted(by_week.keys()),
        "counts": dict(sorted(by_week.items())),
        "total": total,
        "avg_per_period": round(avg_per_week, 1),
        "min": min(by_week.values()) if by_week else 0,
        "max": max(by_week.values()) if by_week else 0,
    }


def throughput_by_sprint(completed: List[Dict[str, Any]], sprint_col_used: bool = True) -> Dict[str, Any]:
    """Group completed tickets by sprint label."""
    by_sprint: Dict[str, int] = defaultdict(int)
    for rec in completed:
        sprint = (rec.get("sprint") or "").strip() or "—"
        by_sprint[sprint] += 1

    sorted_sprints = sorted(by_sprint.keys(), key=lambda x: (x if x != "—" else "\uffff"))
    total = sum(by_sprint.values())
    n = len(by_sprint)
    avg_per_sprint = total / n if n else 0
    return {
        "period_type": "sprint",
        "periods": sorted_sprints,
        "counts": dict((k, by_sprint[k]) for k in sorted_sprints),
        "total": total,
        "avg_per_period": round(avg_per_sprint, 1),
        "min": min(by_sprint.values()) if by_sprint else 0,
        "max": max(by_sprint.values()) if by_sprint else 0,
    }


def wip_by_state(wip: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Count WIP tickets by state."""
    by_state: Dict[str, int] = defaultdict(int)
    for rec in wip:
        state = (rec.get("state") or "Unknown").strip() or "Unknown"
        by_state[state] += 1

    total = sum(by_state.values())
    return {
        "by_state": dict(sorted(by_state.items(), key=lambda x: -x[1])),
        "total": total,
        "states": list(by_state.keys()),
    }


def flow_efficiency(avg_throughput_per_period: float, wip_total: int) -> Optional[float]:
    """Flow efficiency = avg throughput / (avg throughput + WIP). Share of 'period load' that completes."""
    if avg_throughput_per_period <= 0 and wip_total <= 0:
        return None
    if avg_throughput_per_period + wip_total <= 0:
        return None
    return round(avg_throughput_per_period / (avg_throughput_per_period + wip_total) * 100, 1)


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def print_report(
    completed: List[Dict[str, Any]],
    wip: List[Dict[str, Any]],
    throughput: Dict[str, Any],
    wip_stats: Dict[str, Any],
    flow_eff: Optional[float],
    period_label: str,
) -> None:
    """Pretty-print throughput and WIP report."""
    print("\n" + "=" * 78)
    print("📈 THROUGHPUT & WIP ANALYZER")
    print("=" * 78)

    print(f"\n   Completed (throughput): {len(completed)} tickets")
    print(f"   WIP (open):             {len(wip)} tickets")
    if flow_eff is not None:
        print(f"   Flow efficiency:        {flow_eff}% (avg throughput / (avg throughput + WIP))")

    # Throughput
    print(f"\n{'─'*78}")
    print(f"\n   THROUGHPUT (by {period_label}):\n")
    print(f"   Total:   {throughput['total']}  |  Avg per {period_label}: {throughput['avg_per_period']}  |  Min: {throughput['min']}  Max: {throughput['max']}")

    if throughput.get("periods"):
        bar_w = 40
        max_c = max(throughput["counts"].values()) or 1
        print(f"\n   {'Period':<14} {'Count':>6} Bar")
        print(f"   {'─'*14} {'─'*6} {'─'*bar_w}")
        for p in throughput["periods"][-12:]:  # last 12 periods
            c = throughput["counts"].get(p, 0)
            filled = int(c / max_c * bar_w) if max_c else 0
            bar = "█" * filled + "░" * (bar_w - filled)
            print(f"   {p:<14} {c:>6} {bar}")

    # WIP by state
    if wip_stats["total"] > 0:
        print(f"\n{'─'*78}")
        print(f"\n   WIP BY STATE:\n")
        print(f"   {'State':<20} {'Count':>6} Bar")
        print(f"   {'─'*20} {'─'*6} {'─'*30}")
        max_wip = max(wip_stats["by_state"].values()) or 1
        for state, count in wip_stats["by_state"].items():
            filled = int(count / max_wip * 30) if max_wip else 0
            bar = "█" * filled + "░" * (30 - filled)
            print(f"   {state[:20]:<20} {count:>6} {bar}")
        print(f"\n   Total WIP: {wip_stats['total']}")

    print(f"\n{'─'*78}")
    print(f"\n   💡 Use with: cycle-lead-time-analyzer (how long), capacity-planner (capacity)")
    print(f"   Limit WIP to improve flow; track throughput trend over time.")
    print("\n" + "=" * 78)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Throughput (completed per period) and WIP by state. "
                    "Complements cycle-lead-time-analyzer for flow and WIP discussions.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --csv tickets.csv
  %(prog)s --csv tickets.csv --period sprint --sprint-column sprint --weeks 8
  %(prog)s --csv tickets.csv --output report.json
        """,
    )

    parser.add_argument("--csv", "-c", type=str, required=True, help="CSV file (id, state, completed)")
    parser.add_argument("--id", type=str, default="id", help="ID column name")
    parser.add_argument("--state", type=str, default="state", help="State/status column name")
    parser.add_argument("--completed", type=str, default="completed",
                        help="Completed/done date column name")
    parser.add_argument("--created", type=str, default="created", help="Created date column")
    parser.add_argument("--started", type=str, default="started", help="Started date column")
    parser.add_argument("--sprint-column", type=str, default="sprint",
                        help="Sprint column (for --period sprint)")

    parser.add_argument("--period", type=str, default="week", choices=["week", "sprint"],
                         help="Group throughput by week or sprint")
    parser.add_argument("--weeks", type=int, default=None,
                        help="Only include last N weeks (for period=week)")

    parser.add_argument("--output", "-o", type=str, help="Write JSON results to file")
    args = parser.parse_args()

    try:
        completed, wip = load_tickets(
            args.csv,
            id_col=args.id,
            state_col=args.state,
            completed_col=args.completed,
            created_col=args.created,
            started_col=args.started,
            sprint_col=args.sprint_column,
        )
    except Exception as e:
        print(f"Error loading CSV: {e}", file=sys.stderr)
        return 1

    if not completed and not wip:
        print("No tickets found (need id and either completed date or state).", file=sys.stderr)
        return 1

    # Throughput
    if args.period == "sprint":
        throughput = throughput_by_sprint(completed)
        period_label = "sprint"
    else:
        throughput = throughput_by_week(completed, weeks=args.weeks)
        period_label = "week"

    wip_stats = wip_by_state(wip)
    flow_eff = flow_efficiency(throughput["avg_per_period"], wip_stats["total"])

    # Build result for JSON
    result = {
        "throughput": throughput,
        "wip": wip_stats,
        "flow_efficiency_pct": flow_eff,
        "n_completed": len(completed),
        "n_wip": len(wip),
    }

    print_report(
        completed, wip, throughput, wip_stats, flow_eff, period_label,
    )

    if args.output:
        with open(args.output, "w") as f:
            json.dump(result, f, indent=2)
        print(f"\n📁 Results saved to {args.output}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
