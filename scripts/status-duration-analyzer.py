#!/usr/bin/env python3
"""
Status Duration Analyzer

Compute how long issues spend in each status (To Do, In Progress, In Review,
Done, etc.) from status history or transition data. Surfaces bottlenecks and
flow issues for retros and process improvement.

Usage:
    # Transition log: one row per status change (issue entered status at date)
    python status-duration-analyzer.py --csv transitions.csv

    # Status spans: one row per stay (from_date, to_date per status)
    python status-duration-analyzer.py --csv spans.csv --spans

    # Use a specific "as of" date for open-ended stays (default: today)
    python status-duration-analyzer.py --csv transitions.csv --as-of 2025-02-14

    # Group by issue type
    python status-duration-analyzer.py --csv transitions.csv --group-by type

    # Chart and export
    python status-duration-analyzer.py --csv transitions.csv --chart --markdown report.md --output report.json

CSV format (transition log, default):
    issue_id,status,changed_at
    PROJ-101,To Do,2025-01-02
    PROJ-101,In Progress,2025-01-05
    PROJ-101,Done,2025-01-10

    Each row = "issue entered this status at this time". Durations are inferred
    between consecutive transitions; last status uses --as-of (or today).

CSV format (spans, --spans):
    issue_id,status,from_date,to_date
    PROJ-101,In Progress,2025-01-05,2025-01-08

    to_date can be empty for current status; then --as-of is used.

Requirements:
    None (stdlib only).
"""

import argparse
import csv
import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Date parsing
# ---------------------------------------------------------------------------

def parse_date(s: str) -> Optional[datetime]:
    if not s or not s.strip():
        return None
    s = s.strip()[:32]
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
# Load data
# ---------------------------------------------------------------------------

def load_transitions(
    path: str,
    id_col: str = "issue_id",
    status_col: str = "status",
    date_col: str = "changed_at",
    type_col: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Load transition log: each row = issue entered status at date."""
    rows: List[Dict[str, Any]] = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fields = reader.fieldnames or []

        c_id = _col(fields, id_col, "issue_id", "id", "key", "issue_key", "issue key")
        c_status = _col(fields, status_col, "status", "to_status", "state", "to_state")
        c_date = _col(fields, date_col, "changed_at", "created", "date", "timestamp", "entered_at")
        c_type = _col(fields, type_col or "type", "issue type", "issuetype", "type") if type_col is not False else None

        for row in reader:
            issue_id = (row.get(c_id or "issue_id", "") or "").strip()
            status = (row.get(c_status or "status", "") or "").strip()
            raw_date = (row.get(c_date or "changed_at", "") or "").strip()
            dt = parse_date(raw_date)
            if not issue_id or not status or not dt:
                continue
            rec: Dict[str, Any] = {"issue_id": issue_id, "status": status, "changed_at": dt}
            if c_type:
                rec["type"] = (row.get(c_type, "") or "").strip() or "—"
            rows.append(rec)

    rows.sort(key=lambda r: (r["issue_id"], r["changed_at"]))
    return rows


def load_spans(
    path: str,
    id_col: str = "issue_id",
    status_col: str = "status",
    from_col: str = "from_date",
    to_col: str = "to_date",
    type_col: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Load status spans: each row = issue was in status from from_date to to_date."""
    rows: List[Dict[str, Any]] = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fields = reader.fieldnames or []

        c_id = _col(fields, id_col, "issue_id", "id", "key", "issue_key")
        c_status = _col(fields, status_col, "status", "state")
        c_from = _col(fields, from_col, "from_date", "from", "start", "start_date")
        c_to = _col(fields, to_col, "to_date", "to", "end", "end_date", "left_at")
        c_type = _col(fields, type_col or "type", "issue type", "issuetype") if type_col is not False else None

        for row in reader:
            issue_id = (row.get(c_id or "issue_id", "") or "").strip()
            status = (row.get(c_status or "status", "") or "").strip()
            from_dt = parse_date((row.get(c_from or "from_date", "") or "").strip())
            to_str = (row.get(c_to or "to_date", "") or "").strip()
            to_dt = parse_date(to_str) if to_str else None
            if not issue_id or not status or not from_dt:
                continue
            rec: Dict[str, Any] = {
                "issue_id": issue_id,
                "status": status,
                "from_date": from_dt,
                "to_date": to_dt,
            }
            if c_type:
                rec["type"] = (row.get(c_type, "") or "").strip() or "—"
            rows.append(rec)
    return rows


# ---------------------------------------------------------------------------
# Compute durations
# ---------------------------------------------------------------------------

# Terminal statuses: treat last stay as 0 days (we don't count "still in Done" time)
TERMINAL_STATUSES = {"done", "closed", "resolved", "complete", "cancelled"}


def transitions_to_durations(
    transitions: List[Dict[str, Any]],
    as_of: datetime,
) -> List[Dict[str, Any]]:
    """Convert transition log to list of (issue_id, status, duration_days, type?)."""
    durations: List[Dict[str, Any]] = []
    i = 0
    while i < len(transitions):
        issue_id = transitions[i]["issue_id"]
        issue_type = transitions[i].get("type", "—")
        j = i
        while j < len(transitions) and transitions[j]["issue_id"] == issue_id:
            entered = transitions[j]["changed_at"]
            status = transitions[j]["status"]
            is_last = j + 1 >= len(transitions) or transitions[j + 1]["issue_id"] != issue_id
            if not is_last:
                left = transitions[j + 1]["changed_at"]
            elif is_last and status.lower().strip() in TERMINAL_STATUSES:
                left = entered  # 0 days for terminal status when it's the last
            else:
                left = as_of
            days = (left - entered).total_seconds() / (24 * 3600)
            if days < 0:
                days = 0
            durations.append({
                "issue_id": issue_id,
                "status": status,
                "duration_days": round(days, 2),
                "type": issue_type,
            })
            j += 1
        i = j
    return durations


def spans_to_durations(
    spans: List[Dict[str, Any]],
    as_of: datetime,
) -> List[Dict[str, Any]]:
    """Convert span rows to list of (issue_id, status, duration_days, type?)."""
    durations: List[Dict[str, Any]] = []
    for s in spans:
        to_dt = s.get("to_date") or as_of
        days = (to_dt - s["from_date"]).total_seconds() / (24 * 3600)
        if days < 0:
            days = 0
        durations.append({
            "issue_id": s["issue_id"],
            "status": s["status"],
            "duration_days": round(days, 2),
            "type": s.get("type", "—"),
        })
    return durations


def aggregate_by_status(
    durations: List[Dict[str, Any]],
    group_by_type: bool = False,
) -> Dict[str, Any]:
    """Aggregate durations by status (and optionally by type)."""
    by_status: Dict[str, List[float]] = defaultdict(list)
    by_type_status: Dict[str, Dict[str, List[float]]] = defaultdict(lambda: defaultdict(list))

    for d in durations:
        status = d["status"]
        days = d["duration_days"]
        by_status[status].append(days)
        if group_by_type:
            t = d.get("type", "—")
            by_type_status[t][status].append(days)

    def stats(days_list: List[float]) -> Dict[str, Any]:
        if not days_list:
            return {"count": 0, "total_days": 0, "mean_days": 0, "median_days": 0}
        n = len(days_list)
        total = sum(days_list)
        mean = total / n
        sorted_d = sorted(days_list)
        median = sorted_d[n // 2] if n % 2 == 1 else (sorted_d[n // 2 - 1] + sorted_d[n // 2]) / 2
        return {
            "count": n,
            "total_days": round(total, 1),
            "mean_days": round(mean, 1),
            "median_days": round(median, 1),
        }

    status_stats = {status: stats(days_list) for status, days_list in sorted(by_status.items())}
    type_status_stats: Dict[str, Dict[str, Dict[str, Any]]] = {}
    if group_by_type:
        for t, status_dict in sorted(by_type_status.items()):
            type_status_stats[t] = {status: stats(days_list) for status, days_list in sorted(status_dict.items())}

    return {
        "by_status": status_stats,
        "by_type": type_status_stats if group_by_type else {},
        "total_stays": len(durations),
        "unique_issues": len({d["issue_id"] for d in durations}),
    }


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def _bar(value: float, max_val: float, width: int = 20) -> str:
    if max_val <= 0:
        return "░" * width
    ratio = min(1.0, max(0.0, value / max_val))
    filled = int(ratio * width)
    return "█" * filled + "░" * (width - filled)


def print_report(result: Dict[str, Any], chart: bool = False, group_by_type: bool = False) -> None:
    """Pretty-print status duration report."""
    print("\n" + "=" * 70)
    print("⏱️  STATUS DURATION ANALYZER")
    print("=" * 70)

    total_stays = result.get("total_stays", 0)
    unique = result.get("unique_issues", 0)
    print(f"\n   Stays: {total_stays}  |  Unique issues: {unique}")

    by_status = result.get("by_status", {})
    if not by_status:
        print("\n   No status duration data.")
        return

    print(f"\n   {'Status':<20} {'Stays':>8} {'Total days':>12} {'Mean':>10} {'Median':>10}")
    print("   " + "─" * 64)
    max_mean = max(s["mean_days"] for s in by_status.values()) if by_status else 1
    for status, s in sorted(by_status.items(), key=lambda x: -x[1]["total_days"]):
        print(f"   {status[:19]:<20} {s['count']:>8} {s['total_days']:>12.1f} {s['mean_days']:>10.1f} {s['median_days']:>10.1f}")

    if chart and by_status:
        print(f"\n   Mean days by status:")
        for status, s in sorted(by_status.items(), key=lambda x: -x[1]["mean_days"]):
            bar = _bar(s["mean_days"], max_mean, 25)
            print(f"   {status[:18]:<19} {bar} {s['mean_days']:.1f}d")

    if group_by_type and result.get("by_type"):
        print(f"\n   By type:")
        for t, stats in sorted(result["by_type"].items()):
            if not stats:
                continue
            print(f"\n   {t}:")
            for status, s in sorted(stats.items(), key=lambda x: -x[1]["total_days"]):
                print(f"      {status[:16]:<17} {s['count']:>6} stays  mean {s['mean_days']:.1f}d  median {s['median_days']:.1f}d")

    print("\n   💡 Use to spot bottlenecks (long mean in one status) and balance flow.\n")


def to_json_result(result: Dict[str, Any]) -> Dict[str, Any]:
    """JSON-serializable result (no datetime)."""
    return {
        "by_status": result.get("by_status", {}),
        "by_type": result.get("by_type", {}),
        "total_stays": result.get("total_stays", 0),
        "unique_issues": result.get("unique_issues", 0),
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Analyze how long issues spend in each status.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--csv", "-c", required=True, help="Path to transitions or spans CSV")
    parser.add_argument(
        "--spans",
        action="store_true",
        help="CSV has status spans (from_date, to_date) instead of transition log",
    )
    parser.add_argument(
        "--as-of",
        type=str,
        default=None,
        metavar="DATE",
        help="End date for open-ended stays (default: today)",
    )
    parser.add_argument("--group-by", type=str, default=None, metavar="COL", help="Group results by column (e.g. type)")
    parser.add_argument("--chart", action="store_true", help="Print bar chart of mean days by status")
    parser.add_argument("--markdown", metavar="FILE", help="Write Markdown report to FILE")
    parser.add_argument("--output", "-o", metavar="FILE", help="Write JSON result to FILE")
    args = parser.parse_args()

    as_of = datetime.now().replace(hour=23, minute=59, second=59, microsecond=0)
    if args.as_of:
        parsed = parse_date(args.as_of)
        if parsed:
            as_of = parsed.replace(hour=23, minute=59, second=59, microsecond=0)
        else:
            print(f"Invalid --as-of date: {args.as_of}", file=sys.stderr)
            return 1

    if args.spans:
        spans = load_spans(args.csv, type_col=args.group_by or False)
        if not spans:
            print("No valid span rows in CSV.", file=sys.stderr)
            return 1
        durations = spans_to_durations(spans, as_of)
    else:
        transitions = load_transitions(args.csv, type_col=args.group_by or False)
        if not transitions:
            print("No valid transition rows in CSV.", file=sys.stderr)
            return 1
        durations = transitions_to_durations(transitions, as_of)

    if not durations:
        print("No durations computed.", file=sys.stderr)
        return 1

    result = aggregate_by_status(durations, group_by_type=bool(args.group_by))
    print_report(result, chart=args.chart, group_by_type=bool(args.group_by))

    if args.markdown:
        with open(args.markdown, "w", encoding="utf-8") as f:
            f.write("# Status Duration Report\n\n")
            f.write(f"- **Total stays:** {result['total_stays']}\n")
            f.write(f"- **Unique issues:** {result['unique_issues']}\n\n")
            f.write("| Status | Stays | Total days | Mean (days) | Median (days) |\n")
            f.write("|--------|------|------------|--------------|----------------|\n")
            for status, s in sorted(result.get("by_status", {}).items(), key=lambda x: -x[1]["total_days"]):
                f.write(f"| {status} | {s['count']} | {s['total_days']} | {s['mean_days']} | {s['median_days']} |\n")
        print(f"Wrote Markdown to {args.markdown}")

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(to_json_result(result), f, indent=2)
        print(f"Wrote JSON to {args.output}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
