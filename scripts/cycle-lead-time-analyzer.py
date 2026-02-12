#!/usr/bin/env python3
"""
Cycle Time / Lead Time Analyzer

Compute cycle time (started → done) and lead time (created → done) from ticket
timestamps. Reports percentiles (p50, p90, p95), throughput, and identifies
outliers. Complements velocity trend and capacity planning for flow analysis.

Usage:
    python cycle-lead-time-analyzer.py --csv tickets.csv
    python cycle-lead-time-analyzer.py --csv tickets.csv --created created --started in_progress --done resolutiondate
    python cycle-lead-time-analyzer.py --csv tickets.csv --group-by type
    python cycle-lead-time-analyzer.py --csv tickets.csv --period-days 14 --output report.json

CSV format (header row required):
    id,created,started,done,type
    PROJ-123,2025-01-02,2025-01-05,2025-01-10,Bug
    PROJ-124,2025-01-03,2025-01-04,2025-01-08,Feature
    ...

Required columns: created, done
Optional: started (for cycle time; if missing, cycle time = lead time)
Optional: type, assignee, sprint (for --group-by)

Requirements:
    None (stdlib only). Optional: python-dateutil for flexible date parsing.
"""

import argparse
import csv
import json
import sys
from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple


def parse_date(s: str) -> Optional[datetime]:
    """Parse date string. Tries dateutil first, then ISO and common formats."""
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
    # Stdlib fallbacks
    for fmt, trim in [
        ("%Y-%m-%dT%H:%M:%S", 19),
        ("%Y-%m-%d %H:%M:%S", 19),
        ("%Y-%m-%d", 10),
        ("%Y/%m/%d", 10),
        ("%m/%d/%Y", 10),
        ("%d/%m/%Y", 10),
    ]:
        try:
            return datetime.strptime(s[:trim], fmt)
        except ValueError:
            continue
    return None


def parse_date_safe(s: str) -> Optional[datetime]:
    """Parse with robust handling."""
    try:
        return parse_date(s)
    except Exception:
        return None


def load_tickets(
    path: str,
    created_col: str = "created",
    started_col: str = "started",
    done_col: str = "done",
    id_col: str = "id",
) -> List[Dict[str, Any]]:
    """Load tickets from CSV with parsed dates."""
    tickets: List[Dict[str, Any]] = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        # Normalize column names (case-insensitive match)
        if reader.fieldnames:
            col_map = {c.lower(): c for c in reader.fieldnames}
        else:
            col_map = {}

        def get_col(alias: str, fallbacks: List[str]) -> Optional[str]:
            for name in [alias] + fallbacks:
                key = name.lower()
                if key in col_map:
                    return col_map[key]
            return None

        created_key = get_col(created_col, ["created", "created_date", "createdate"])
        done_key = get_col(done_col, ["done", "resolutiondate", "completed", "closed"])
        started_key = get_col(started_col, ["started", "in_progress", "indev", "in development"])
        id_key = get_col(id_col, ["id", "key", "ticket_id"])

        for row in reader:
            created = parse_date_safe(row.get(created_key or "created", ""))
            done = parse_date_safe(row.get(done_key or "done", ""))
            started = parse_date_safe(row.get(started_key or "started", ""))

            if not created or not done:
                continue
            if done < created:
                continue

            tid = row.get(id_key or "id", str(len(tickets) + 1))
            lead_time_days = (done - created).total_seconds() / (24 * 3600)

            if started and created <= started <= done:
                cycle_time_days = (done - started).total_seconds() / (24 * 3600)
            else:
                cycle_time_days = lead_time_days

            tickets.append({
                "id": tid,
                "created": created,
                "started": started,
                "done": done,
                "lead_time_days": round(lead_time_days, 2),
                "cycle_time_days": round(cycle_time_days, 2),
                "row": {k: v for k, v in row.items()},
            })

    return tickets


def percentile(values: List[float], p: float) -> float:
    """Approximate percentile (linear interpolation)."""
    if not values:
        return 0.0
    sorted_v = sorted(values)
    n = len(sorted_v)
    idx = p / 100.0 * (n - 1)
    lo = int(idx)
    hi = min(lo + 1, n - 1)
    w = idx - lo
    return sorted_v[lo] * (1 - w) + sorted_v[hi] * w


def compute_stats(tickets: List[Dict], group_key: Optional[str] = None) -> Dict[str, Any]:
    """Compute cycle/lead time stats, optionally grouped."""
    if group_key:
        groups: Dict[str, List[Dict]] = defaultdict(list)
        key_lower = group_key.lower()
        for t in tickets:
            g = "Unknown"
            for k, v in t["row"].items():
                if k.lower() == key_lower:
                    g = str(v) if v else "Unknown"
                    break
            groups[g].append(t)
        return {
            "groups": {g: compute_stats(items, None) for g, items in groups.items()},
            "overall": compute_stats(tickets, None),
        }

    lead = [t["lead_time_days"] for t in tickets]
    cycle = [t["cycle_time_days"] for t in tickets]

    return {
        "n": len(tickets),
        "lead_time": {
            "mean": round(sum(lead) / len(lead), 2) if lead else 0,
            "median": round(percentile(lead, 50), 2) if lead else 0,
            "p90": round(percentile(lead, 90), 2) if lead else 0,
            "p95": round(percentile(lead, 95), 2) if lead else 0,
            "min": round(min(lead), 2) if lead else 0,
            "max": round(max(lead), 2) if lead else 0,
        },
        "cycle_time": {
            "mean": round(sum(cycle) / len(cycle), 2) if cycle else 0,
            "median": round(percentile(cycle, 50), 2) if cycle else 0,
            "p90": round(percentile(cycle, 90), 2) if cycle else 0,
            "p95": round(percentile(cycle, 95), 2) if cycle else 0,
            "min": round(min(cycle), 2) if cycle else 0,
            "max": round(max(cycle), 2) if cycle else 0,
        },
    }


def throughput(tickets: List[Dict], period_days: float) -> float:
    """Items completed per period (e.g. per 7 days)."""
    if not tickets or period_days <= 0:
        return 0.0
    return len(tickets) / period_days


def format_days(d: float) -> str:
    """Format days as human-readable."""
    if d < 1:
        return f"{d * 24:.0f}h"
    if d < 7:
        return f"{d:.1f}d"
    if d < 30:
        return f"{d / 7:.1f}w"
    return f"{d / 30:.1f}mo"


def print_report(
    tickets: List[Dict],
    stats: Dict,
    period_days: Optional[float] = None,
    group_by: Optional[str] = None,
) -> None:
    """Pretty-print analysis report."""
    n = stats.get("n") or stats["overall"]["n"]

    print("\n" + "=" * 70)
    print("📊 CYCLE TIME / LEAD TIME ANALYZER")
    print("=" * 70)

    print(f"\n📋 OVERVIEW:")
    print(f"   • Tickets analyzed:  {n}")
    if period_days:
        tp = throughput(tickets, period_days)
        period_str = f"{period_days:.1f} days" if period_days >= 1 else f"{period_days * 24:.1f} hours"
        print(f"   • Period:            {period_str}")
        print(f"   • Throughput:        {tp:.1f} items / {period_str} (~{tp * 7:.1f}/week)")

    if "groups" in stats:
        print(f"\n📐 BY {group_by.upper()}:")
        for gname, gstats in sorted(stats["groups"].items()):
            if gstats["n"] == 0:
                continue
            lt = gstats["lead_time"]
            ct = gstats["cycle_time"]
            print(f"\n   {gname} ({gstats['n']} items):")
            print(f"      Lead time:  median {format_days(lt['median'])}, p90 {format_days(lt['p90'])}, p95 {format_days(lt['p95'])}")
            print(f"      Cycle time: median {format_days(ct['median'])}, p90 {format_days(ct['p90'])}, p95 {format_days(ct['p95'])}")
        stats = stats["overall"]

    lt = stats["lead_time"]
    ct = stats["cycle_time"]

    print(f"\n📈 LEAD TIME (created → done):")
    print(f"   • Median (p50):   {format_days(lt['median'])}  ({lt['median']:.1f} days)")
    print(f"   • p90:            {format_days(lt['p90'])}  ({lt['p90']:.1f} days)")
    print(f"   • p95:            {format_days(lt['p95'])}  ({lt['p95']:.1f} days)")
    print(f"   • Mean:           {format_days(lt['mean'])}  ({lt['mean']:.1f} days)")
    print(f"   • Range:          {format_days(lt['min'])} – {format_days(lt['max'])}")

    print(f"\n📈 CYCLE TIME (started → done):")
    print(f"   • Median (p50):   {format_days(ct['median'])}  ({ct['median']:.1f} days)")
    print(f"   • p90:            {format_days(ct['p90'])}  ({ct['p90']:.1f} days)")
    print(f"   • p95:            {format_days(ct['p95'])}  ({ct['p95']:.1f} days)")
    print(f"   • Mean:           {format_days(ct['mean'])}  ({ct['mean']:.1f} days)")
    print(f"   • Range:          {format_days(ct['min'])} – {format_days(ct['max'])}")

    # Wait time (lead - cycle) if cycle differs from lead
    if n > 0:
        avg_wait = sum(t["lead_time_days"] - t["cycle_time_days"] for t in tickets) / n
        if avg_wait > 0.5:
            print(f"\n⏳ WAIT TIME (created → started):")
            print(f"   • Avg time in backlog: ~{format_days(avg_wait)} ({avg_wait:.1f} days)")

    # Outliers
    if lt["p95"] > 0:
        outliers = [t for t in tickets if t["lead_time_days"] > lt["p95"]]
        if outliers:
            print(f"\n⚠️  OUTLIERS (lead time > p95):")
            for t in sorted(outliers, key=lambda x: -x["lead_time_days"])[:5]:
                print(f"   • {t['id']}: {format_days(t['lead_time_days'])}  ({t['lead_time_days']:.0f} days)")

    print(f"\n💡 REFERENCE:")
    print(f"   • Lead time = total time from request to delivery")
    print(f"   • Cycle time = active work time (started to done)")
    print(f"   • Target: p50 cycle < 1 week, p95 < 2 weeks for most teams")
    print("\n" + "=" * 70)


def main():
    parser = argparse.ArgumentParser(
        description="Analyze cycle time and lead time from ticket timestamps."
    )
    parser.add_argument(
        "--csv", "-c", required=True,
        help="CSV file with created, done (and optionally started) dates",
    )
    parser.add_argument(
        "--created", default="created",
        help="Column name for created date (default: created)",
    )
    parser.add_argument(
        "--started", default="started",
        help="Column name for started/in-progress date (default: started)",
    )
    parser.add_argument(
        "--done", default="done",
        help="Column name for done/resolution date (default: done)",
    )
    parser.add_argument(
        "--group-by", "-g", type=str,
        help="Group analysis by column (e.g. type, assignee)",
    )
    parser.add_argument(
        "--period-days", "-p", type=float,
        help="Period span in days (for throughput calc). Default: date range of data.",
    )
    parser.add_argument(
        "--output", "-o", type=str,
        help="Write report JSON to file",
    )
    args = parser.parse_args()

    try:
        tickets = load_tickets(
            args.csv,
            created_col=args.created,
            started_col=args.started,
            done_col=args.done,
        )
    except Exception as e:
        print(f"Error loading CSV: {e}", file=sys.stderr)
        return 1

    if not tickets:
        print("Error: no valid tickets found. Check CSV columns (created, done).", file=sys.stderr)
        return 1

    # Infer period from data if not provided
    period_days = args.period_days
    if not period_days and tickets:
        min_d = min(t["created"] for t in tickets)
        max_d = max(t["done"] for t in tickets)
        delta = max_d - min_d
        actual_days = delta.total_seconds() / (24 * 3600)
        period_days = max(1 / 1440, actual_days)  # min 1 minute to avoid div-by-zero

    stats = compute_stats(tickets, args.group_by)

    # Build serializable stats for JSON (remove row data from tickets)
    tickets_out = [
        {k: (v.isoformat() if hasattr(v, "isoformat") else v) for k, v in t.items() if k != "row"}
        for t in tickets
    ]

    print_report(tickets, stats, period_days, args.group_by)

    if args.output:
        report = {
            "n_tickets": len(tickets),
            "period_days": period_days,
            "throughput_per_week": throughput(tickets, period_days or 1) * 7 if period_days else None,
            "stats": stats,
            "tickets": tickets_out,
        }
        with open(args.output, "w") as f:
            json.dump(report, f, indent=2)
        print(f"Report saved to {args.output}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
