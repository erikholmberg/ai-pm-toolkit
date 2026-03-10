#!/usr/bin/env python3
"""
Incident Rate Trend

Report incident counts per week or month, MTTR (mean time to resolve), and a
simple trend from an incidents CSV. Use for retros, SLA discussions, and
tracking reliability over time. Complements incident-postmortem and
sla-uptime-calculator.

Usage:
    # Counts per week (default); MTTR when duration column present
    python incident-rate-trend.py --csv incidents.csv

    # Per month; last 12 weeks only
    python incident-rate-trend.py --csv incidents.csv --period month --weeks 12

    # Group by severity
    python incident-rate-trend.py --csv incidents.csv --group-by severity

    # Chart and export
    python incident-rate-trend.py --csv incidents.csv --chart --markdown report.md --output report.json

CSV format:
    date,severity,duration_minutes
    2025-01-15,P1,45
    2025-01-22,P2,120
    2025-01-28,P1,

    Required: date.
    Optional: severity, duration_minutes (or duration_hours for MTTR).

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
# Load incidents
# ---------------------------------------------------------------------------

def load_incidents(
    path: str,
    date_col: str = "date",
    duration_col: str = "duration_minutes",
    severity_col: str = "severity",
) -> List[Dict[str, Any]]:
    """Load incidents from CSV. duration in minutes (or hours if column name has hours)."""
    rows: List[Dict[str, Any]] = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fields = reader.fieldnames or []

        c_date = _col(fields, date_col, "date", "timestamp", "created", "occurred")
        c_duration = _col(fields, duration_col, "duration_minutes", "duration_hours", "duration", "minutes", "mttr")
        c_severity = _col(fields, severity_col, "severity", "priority", "priority_level", "sev")

        for row in reader:
            raw_date = (row.get(c_date or "date", "") or "").strip()
            dt = parse_date(raw_date)
            if not dt:
                continue

            raw_dur = (row.get(c_duration or "duration_minutes", "") or "").strip().replace(",", "")
            duration_min: Optional[float] = None
            if raw_dur:
                try:
                    val = float(raw_dur)
                    # If column was duration_hours, convert to minutes
                    if c_duration and "hour" in (c_duration or "").lower():
                        val = val * 60
                    duration_min = val
                except ValueError:
                    pass

            severity = (row.get(c_severity or "severity", "") or "").strip() or "—"

            rows.append({
                "date": dt,
                "duration_minutes": duration_min,
                "severity": severity,
            })

    rows.sort(key=lambda r: r["date"])
    return rows


# ---------------------------------------------------------------------------
# Analysis
# ---------------------------------------------------------------------------

def group_by_period(
    incidents: List[Dict[str, Any]],
    period: str,
    weeks_limit: Optional[int],
) -> Dict[str, Any]:
    """Group incidents by week or month. Optional: last N weeks only."""
    by_key: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for inc in incidents:
        dt = inc["date"]
        if period == "month":
            key = dt.strftime("%Y-%m")
        else:
            iso = dt.isocalendar()
            key = f"{iso[0]}-W{iso[1]:02d}"
        by_key[key].append(inc)

    sorted_keys = sorted(by_key.keys())
    if weeks_limit and period == "week" and sorted_keys:
        sorted_keys = sorted_keys[-weeks_limit:]
        by_key = {k: by_key[k] for k in sorted_keys if k in by_key}
    elif weeks_limit and period == "month" and sorted_keys:
        sorted_keys = sorted_keys[-weeks_limit:]
        by_key = {k: by_key[k] for k in sorted_keys if k in by_key}

    counts = {k: len(by_key[k]) for k in sorted_keys}
    total = sum(counts.values())
    n_periods = len(counts)
    avg_per_period = total / n_periods if n_periods else 0

    # MTTR: mean duration in minutes (only incidents in filtered range, with duration)
    filtered_incidents = [inc for k in sorted_keys for inc in by_key[k]]
    durations = [inc["duration_minutes"] for inc in filtered_incidents if inc.get("duration_minutes") is not None]
    mttr_min = sum(durations) / len(durations) if durations else None

    # Trend: first half vs second half avg rate
    trend_delta: Optional[float] = None
    if n_periods >= 4:
        mid = n_periods // 2
        first_avg = sum(counts[k] for k in sorted_keys[:mid]) / mid if mid else 0
        second_avg = sum(counts[k] for k in sorted_keys[mid:]) / (n_periods - mid) if (n_periods - mid) else 0
        trend_delta = second_avg - first_avg

    return {
        "period": period,
        "periods": sorted_keys,
        "counts": counts,
        "total": total,
        "avg_per_period": round(avg_per_period, 1),
        "min_count": min(counts.values()) if counts else 0,
        "max_count": max(counts.values()) if counts else 0,
        "mttr_minutes": round(mttr_min, 1) if mttr_min is not None else None,
        "mttr_with_count": len(durations),
        "trend_delta": round(trend_delta, 1) if trend_delta is not None else None,
    }


def group_by_severity(incidents: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """Count and MTTR per severity."""
    by_sev: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for inc in incidents:
        by_sev[inc["severity"]].append(inc)

    out = {}
    for sev, incs in sorted(by_sev.items(), key=lambda x: -len(x[1])):
        durations = [i["duration_minutes"] for i in incs if i.get("duration_minutes") is not None]
        mttr = sum(durations) / len(durations) if durations else None
        out[sev] = {
            "count": len(incs),
            "mttr_minutes": round(mttr, 1) if mttr is not None else None,
        }
    return out


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def _bar(value: float, max_val: float, width: int = 20) -> str:
    if max_val <= 0:
        return "░" * width
    ratio = min(1.0, max(0.0, value / max_val))
    filled = int(ratio * width)
    return "█" * filled + "░" * (width - filled)


def _format_mttr(minutes: Optional[float]) -> str:
    if minutes is None:
        return "—"
    if minutes < 60:
        return f"{minutes:.0f}m"
    h = minutes / 60
    if h < 24:
        return f"{h:.1f}h"
    return f"{h / 24:.1f}d"


def print_report(result: Dict[str, Any], by_severity: Dict[str, Dict[str, Any]], chart: bool) -> None:
    """Pretty-print incident rate trend."""
    print("\n" + "=" * 70)
    print("📊 INCIDENT RATE TREND")
    print("=" * 70)

    total = result["total"]
    period = result["period"]
    print(f"\n   Period:       {period}")
    print(f"   Total:       {total} incidents")
    print(f"   Avg/period:  {result['avg_per_period']:.1f}")
    print(f"   Range:       {result['min_count']} – {result['max_count']} per period")
    mttr = result.get("mttr_minutes")
    if mttr is not None:
        print(f"   MTTR:        {_format_mttr(mttr)} (from {result.get('mttr_with_count', 0)} with duration)")
    if result.get("trend_delta") is not None:
        d = result["trend_delta"]
        direction = "↑" if d > 0 else "↓" if d < 0 else "→"
        print(f"   Trend:       {direction} {abs(d):.1f} incidents/period (2nd half vs 1st half)")

    print(f"\n   {'Period':<14} {'Count':>8}")
    print("   " + "─" * 24)
    for p in result["periods"]:
        print(f"   {p:<14} {result['counts'][p]:>8}")

    if chart and result["periods"]:
        max_c = max(result["counts"].values()) or 1
        print(f"\n   Count by period:")
        for p in result["periods"]:
            bar = _bar(result["counts"][p], max_c, 25)
            print(f"   {p:<12} {bar} {result['counts'][p]}")

    if by_severity:
        print(f"\n   By severity:")
        for sev, stats in by_severity.items():
            mttr_str = _format_mttr(stats.get("mttr_minutes"))
            print(f"      {sev:<12} {stats['count']:>6} incidents  MTTR {mttr_str}")

    print("\n   💡 Use for retros and SLA/reliability discussions.\n")


def to_json_result(result: Dict[str, Any], by_severity: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    """JSON-serializable (no datetime)."""
    out = {
        "period": result["period"],
        "periods": result["periods"],
        "counts": result["counts"],
        "total": result["total"],
        "avg_per_period": result["avg_per_period"],
        "mttr_minutes": result.get("mttr_minutes"),
        "trend_delta": result.get("trend_delta"),
    }
    if by_severity:
        out["by_severity"] = by_severity
    return out


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Report incident rate and MTTR trend from CSV.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--csv", "-c", required=True, help="Path to incidents CSV (date required)")
    parser.add_argument("--period", "-p", choices=["week", "month"], default="week", help="Group by week (default) or month")
    parser.add_argument("--weeks", "-w", type=int, default=None, metavar="N", help="Limit to last N periods")
    parser.add_argument("--group-by", type=str, default=None, metavar="COL", help="Also group by column (e.g. severity)")
    parser.add_argument("--chart", action="store_true", help="Print bar chart of counts by period")
    parser.add_argument("--markdown", metavar="FILE", help="Write Markdown report to FILE")
    parser.add_argument("--output", "-o", metavar="FILE", help="Write JSON result to FILE")
    args = parser.parse_args()

    incidents = load_incidents(args.csv)
    if not incidents:
        print("No incidents with valid date in CSV.", file=sys.stderr)
        return 1

    result = group_by_period(incidents, args.period, args.weeks)
    by_severity = {}
    if args.group_by and args.group_by.lower() in ("severity", "priority", "sev"):
        by_severity = group_by_severity(incidents)

    print_report(result, by_severity, args.chart)

    if args.markdown:
        with open(args.markdown, "w", encoding="utf-8") as f:
            f.write("# Incident Rate Trend\n\n")
            f.write(f"- **Total incidents:** {result['total']}\n")
            f.write(f"- **Avg per {result['period']}:** {result['avg_per_period']}\n")
            if result.get("mttr_minutes") is not None:
                f.write(f"- **MTTR:** {_format_mttr(result['mttr_minutes'])}\n")
            f.write("\n| Period | Count |\n")
            f.write("|--------|-------|\n")
            for p in result["periods"]:
                f.write(f"| {p} | {result['counts'][p]} |\n")
        print(f"Wrote Markdown to {args.markdown}")

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(to_json_result(result, by_severity), f, indent=2)
        print(f"Wrote JSON to {args.output}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
