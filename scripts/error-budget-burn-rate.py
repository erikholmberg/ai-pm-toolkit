#!/usr/bin/env python3
"""
Error Budget Burn Rate Calculator

Track how fast your SLA error budget is being consumed over time and project
when it will exhaust. Complements sla-uptime-calculator.py with a forward-
looking, time-series view that helps PMs decide when to freeze deploys or
shift focus to reliability.

Computes:
    - Current error budget consumption (% used)
    - Burn rate (actual vs. allowed consumption speed)
    - Multi-window burn rates (1h, 6h, 1d, 3d — per Google SRE practices)
    - Projected budget exhaustion date
    - Alert recommendations (page / ticket / OK thresholds)

Usage:
    # From inline incidents and period info
    python error-budget-burn-rate.py --sla 99.9 --period-days 30 \\
        --elapsed-days 15 --downtime-minutes 20

    # From CSV of daily or hourly error/downtime data
    python error-budget-burn-rate.py --sla 99.9 --period-days 30 --csv errors.csv

    # From incidents CSV
    python error-budget-burn-rate.py --sla 99.95 --period-days 30 --incidents incidents.csv

    # Multi-window analysis (SRE-style)
    python error-budget-burn-rate.py --sla 99.9 --period-days 30 --csv errors.csv --multi-window

CSV format (daily/hourly error data):
    date,downtime_minutes
    2025-06-01,0
    2025-06-02,5
    2025-06-03,0
    2025-06-04,12
    ...

    Or: date,errors,total_requests (computes error rate)

Incidents CSV format:
    date,duration_minutes,description
    2025-06-02,5,API timeout
    2025-06-04,12,DB failover
    ...

Requirements:
    None (stdlib only).
"""

import argparse
import csv
import json
import math
import sys
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MINUTES_PER_DAY = 24 * 60
MINUTES_PER_HOUR = 60


# ---------------------------------------------------------------------------
# Core calculations
# ---------------------------------------------------------------------------

def error_budget_total(sla_pct: float, period_minutes: float) -> float:
    """Total error budget in minutes for the period."""
    return period_minutes * (1.0 - sla_pct / 100.0)


def burn_rate(
    consumed_minutes: float,
    elapsed_minutes: float,
    budget_minutes: float,
    period_minutes: float,
) -> float:
    """
    Burn rate: ratio of actual consumption rate to ideal (uniform) rate.

    burn_rate = 1.0 → consuming exactly on pace
    burn_rate > 1.0 → consuming faster than allowed
    burn_rate < 1.0 → consuming slower than allowed

    Formula: (consumed / elapsed) / (budget / period)
    """
    if elapsed_minutes <= 0 or budget_minutes <= 0 or period_minutes <= 0:
        return 0.0
    actual_rate = consumed_minutes / elapsed_minutes
    ideal_rate = budget_minutes / period_minutes
    return actual_rate / ideal_rate


def time_to_exhaustion(
    remaining_minutes: float,
    burn_rate_per_minute: float,
) -> Optional[float]:
    """Minutes until budget is exhausted at current burn rate. None if rate <= 0."""
    if burn_rate_per_minute <= 0:
        return None
    return remaining_minutes / burn_rate_per_minute


def projected_consumption(
    consumed_minutes: float,
    elapsed_minutes: float,
    period_minutes: float,
) -> float:
    """Project total consumption at end of period given current rate."""
    if elapsed_minutes <= 0:
        return consumed_minutes
    rate = consumed_minutes / elapsed_minutes
    return rate * period_minutes


# ---------------------------------------------------------------------------
# Multi-window burn rates (Google SRE pattern)
# ---------------------------------------------------------------------------

def multi_window_burn_rates(
    timeseries: List[Dict[str, Any]],
    budget_minutes: float,
    period_minutes: float,
    windows_minutes: Optional[List[Tuple[str, int]]] = None,
) -> List[Dict[str, Any]]:
    """
    Compute burn rates over multiple lookback windows.

    Default windows (Google SRE recommended):
        - 5 min  (fast burn detection)
        - 1 hour (short window)
        - 6 hours (medium window)
        - 1 day  (long window)
        - 3 days (trend window)
    """
    if windows_minutes is None:
        windows_minutes = [
            ("5m", 5),
            ("1h", 60),
            ("6h", 360),
            ("1d", MINUTES_PER_DAY),
            ("3d", 3 * MINUTES_PER_DAY),
        ]

    total_minutes_in_ts = sum(entry.get("downtime_minutes", 0) for entry in timeseries)
    total_elapsed = len(timeseries) * MINUTES_PER_DAY if timeseries else 0

    results = []
    for label, window_mins in windows_minutes:
        # Get entries that fall within the window (from the end of the timeseries)
        entries_needed = max(1, math.ceil(window_mins / MINUTES_PER_DAY))
        window_entries = timeseries[-entries_needed:] if timeseries else []
        window_consumed = sum(e.get("downtime_minutes", 0) for e in window_entries)
        actual_window_mins = len(window_entries) * MINUTES_PER_DAY

        rate = burn_rate(window_consumed, actual_window_mins, budget_minutes, period_minutes)

        # Alert level based on burn rate
        if rate >= 14.4:
            alert = "PAGE"
            alert_emoji = "🔴"
        elif rate >= 6.0:
            alert = "PAGE"
            alert_emoji = "🟠"
        elif rate >= 3.0:
            alert = "TICKET"
            alert_emoji = "🟡"
        elif rate >= 1.0:
            alert = "WARN"
            alert_emoji = "🟡"
        else:
            alert = "OK"
            alert_emoji = "🟢"

        results.append({
            "window": label,
            "window_minutes": window_mins,
            "consumed_minutes": round(window_consumed, 2),
            "burn_rate": round(rate, 2),
            "alert_level": alert,
            "alert_emoji": alert_emoji,
        })

    return results


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def _col(fieldnames: List[str], *aliases: str) -> Optional[str]:
    lower_map = {f.lower().strip(): f for f in fieldnames}
    for alias in aliases:
        if alias.lower().strip() in lower_map:
            return lower_map[alias.lower().strip()]
    return None


def load_timeseries_csv(path: str) -> List[Dict[str, Any]]:
    """Load daily/hourly error data from CSV."""
    entries: List[Dict[str, Any]] = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fields = reader.fieldnames or []

        c_date = _col(fields, "date", "timestamp", "time", "day", "datetime")
        c_downtime = _col(fields, "downtime_minutes", "downtime", "error_minutes", "outage_minutes")
        c_errors = _col(fields, "errors", "error_count", "failures")
        c_total = _col(fields, "total_requests", "total", "requests", "traffic")

        for row in reader:
            date_str = row.get(c_date or "date", "").strip()
            downtime = 0.0

            if c_downtime:
                raw = row.get(c_downtime, "").strip()
                if raw:
                    try:
                        downtime = float(raw)
                    except ValueError:
                        pass
            elif c_errors and c_total:
                try:
                    errors = float(row.get(c_errors, "0").strip())
                    total = float(row.get(c_total, "1").strip())
                    if total > 0:
                        error_rate = errors / total
                        downtime = error_rate * MINUTES_PER_DAY
                except ValueError:
                    pass

            entries.append({
                "date": date_str,
                "downtime_minutes": round(downtime, 2),
            })

    return entries


def load_incidents_csv(path: str) -> List[Dict[str, Any]]:
    """Load incidents and convert to daily downtime series."""
    daily: Dict[str, float] = {}
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fields = reader.fieldnames or []

        c_date = _col(fields, "date", "timestamp", "time", "started")
        c_duration = _col(fields, "duration_minutes", "downtime_minutes", "duration", "minutes")

        for row in reader:
            date_str = row.get(c_date or "date", "").strip()[:10]
            raw = row.get(c_duration or "duration_minutes", "0").strip()
            try:
                duration = float(raw)
            except ValueError:
                duration = 0

            if date_str:
                daily[date_str] = daily.get(date_str, 0) + duration

    entries = [{"date": d, "downtime_minutes": round(m, 2)} for d, m in sorted(daily.items())]
    return entries


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def _bar(value: float, max_val: float, width: int = 30) -> str:
    if max_val <= 0:
        return "░" * width
    ratio = min(1.0, max(0.0, value / max_val))
    filled = int(ratio * width)
    return "█" * filled + "░" * (width - filled)


def _fmt_duration(minutes: float) -> str:
    if minutes < 1:
        return f"{minutes * 60:.0f}s"
    if minutes < 60:
        return f"{minutes:.1f}m"
    hours = minutes / 60
    if hours < 24:
        return f"{hours:.1f}h"
    days = hours / 24
    return f"{days:.1f}d"


def _sparkline(values: List[float]) -> str:
    if not values:
        return ""
    blocks = " ▁▂▃▄▅▆▇█"
    mx = max(values) if values else 1
    if mx == 0:
        return "▁" * len(values)
    return "".join(blocks[min(8, int(v / mx * 8))] for v in values)


def print_report(
    sla_pct: float,
    period_days: float,
    elapsed_days: float,
    total_downtime: float,
    budget_total_mins: float,
    budget_remaining: float,
    current_burn_rate: float,
    projected_total: float,
    exhaustion_days: Optional[float],
    multi_window: Optional[List[Dict[str, Any]]],
    timeseries: Optional[List[Dict[str, Any]]],
) -> None:
    """Pretty-print error budget burn rate analysis."""
    budget_used_pct = (total_downtime / budget_total_mins * 100) if budget_total_mins > 0 else 0
    period_elapsed_pct = (elapsed_days / period_days * 100) if period_days > 0 else 0
    projected_pct = (projected_total / budget_total_mins * 100) if budget_total_mins > 0 else 0
    remaining_days = period_days - elapsed_days

    print("\n" + "=" * 78)
    print("🔥 ERROR BUDGET BURN RATE CALCULATOR")
    print("=" * 78)

    # Status
    if budget_remaining <= 0:
        status_emoji = "🔴"
        status = "BUDGET EXHAUSTED"
    elif current_burn_rate >= 3.0:
        status_emoji = "🔴"
        status = "CRITICAL — burning too fast"
    elif current_burn_rate >= 1.5:
        status_emoji = "🟠"
        status = "WARNING — above ideal pace"
    elif current_burn_rate >= 1.0:
        status_emoji = "🟡"
        status = "CAUTION — slightly above pace"
    else:
        status_emoji = "🟢"
        status = "HEALTHY — within budget"

    print(f"\n{status_emoji} STATUS: {status}")

    # Overview
    print(f"\n📋 BUDGET OVERVIEW:")
    print(f"   • SLA target:           {sla_pct}%")
    print(f"   • Period:               {period_days:.0f} days ({period_days * MINUTES_PER_DAY:,.0f} min)")
    print(f"   • Elapsed:              {elapsed_days:.1f} days ({period_elapsed_pct:.0f}% of period)")
    print(f"   • Remaining:            {remaining_days:.1f} days")

    print(f"\n📊 ERROR BUDGET:")
    print(f"   • Total budget:         {_fmt_duration(budget_total_mins)} ({budget_total_mins:.1f} min)")
    print(f"   • Consumed:             {_fmt_duration(total_downtime)} ({budget_used_pct:.1f}%)")
    if budget_remaining > 0:
        print(f"   • Remaining:            {_fmt_duration(budget_remaining)} ({100 - budget_used_pct:.1f}%)")
    else:
        print(f"   • Overspent:            {_fmt_duration(abs(budget_remaining))} ({abs(budget_remaining):.1f} min over)")

    # Budget bar
    bar = _bar(budget_used_pct, 100, 40)
    elapsed_marker_pos = int(min(39, period_elapsed_pct / 100 * 40))
    marker_bar = list("─" * 40)
    marker_bar[elapsed_marker_pos] = "▼"
    print(f"\n   Budget:   [{bar}] {budget_used_pct:.1f}%")
    print(f"   Time:      {''.join(marker_bar)}  {period_elapsed_pct:.0f}% elapsed")

    if budget_used_pct > period_elapsed_pct:
        print(f"   ⚠️  Budget consumption ({budget_used_pct:.1f}%) ahead of time elapsed ({period_elapsed_pct:.0f}%)")
    else:
        print(f"   ✅ Budget consumption ({budget_used_pct:.1f}%) behind time elapsed ({period_elapsed_pct:.0f}%)")

    # Burn rate
    print(f"\n🔥 BURN RATE:")
    print(f"   • Current rate:         {current_burn_rate:.2f}x")
    if current_burn_rate > 1:
        print(f"   • Consuming budget {current_burn_rate:.1f}× faster than ideal pace")
    elif current_burn_rate > 0:
        print(f"   • Consuming budget at {current_burn_rate:.1f}× the ideal pace (within budget)")
    else:
        print(f"   • No budget consumed yet")

    rate_bar = _bar(min(current_burn_rate, 5), 5, 30)
    print(f"   • Rate:  [{rate_bar}]")
    print(f"             0x     1x     2x     3x     4x    5x+")

    # Projection
    print(f"\n📈 PROJECTION:")
    print(f"   • At current rate, will consume {_fmt_duration(projected_total)} by end of period")
    print(f"   • Projected budget usage: {projected_pct:.1f}%")
    if projected_pct > 100:
        print(f"   • ⚠️  Projected to EXCEED budget by {_fmt_duration(projected_total - budget_total_mins)}")
    else:
        print(f"   • ✅ Projected to finish within budget")

    if exhaustion_days is not None and budget_remaining > 0:
        if exhaustion_days <= remaining_days:
            print(f"   • ⚠️  Budget exhaustion in {exhaustion_days:.1f} days (before period ends)")
        else:
            print(f"   • Budget would last {exhaustion_days:.1f} days at current rate (period has {remaining_days:.1f} left)")
    elif budget_remaining <= 0:
        print(f"   • ❌ Budget already exhausted")

    # Multi-window analysis
    if multi_window:
        print(f"\n{'─'*78}")
        print(f"\n🪟 MULTI-WINDOW BURN RATES (SRE-style):\n")
        print(f"   {'Window':>8} {'Consumed':>10} {'Burn Rate':>12} {'Alert'}")
        print(f"   {'─'*8} {'─'*10} {'─'*12} {'─'*8}")

        for mw in multi_window:
            consumed = _fmt_duration(mw["consumed_minutes"])
            rate_str = f"{mw['burn_rate']:.2f}x"
            print(f"   {mw['window']:>8} {consumed:>10} {rate_str:>12} {mw['alert_emoji']} {mw['alert_level']}")

        print(f"\n   Alert thresholds (Google SRE guidelines):")
        print(f"   • ≥14.4x → PAGE (budget gone in <5% of window)")
        print(f"   • ≥6.0x  → PAGE (budget gone in <17% of window)")
        print(f"   • ≥3.0x  → TICKET (budget gone in <33% of window)")
        print(f"   • ≥1.0x  → WARN (above ideal pace)")
        print(f"   • <1.0x  → OK")

    # Daily consumption sparkline
    if timeseries and len(timeseries) > 1:
        daily_vals = [e["downtime_minutes"] for e in timeseries]
        spark = _sparkline(daily_vals)
        max_day = max(daily_vals)
        incident_days = sum(1 for v in daily_vals if v > 0)
        print(f"\n📅 DAILY DOWNTIME (last {len(daily_vals)} days):")
        print(f"   {spark}")
        print(f"   • Days with incidents: {incident_days}/{len(daily_vals)}")
        print(f"   • Worst day: {_fmt_duration(max_day)}")
        print(f"   • Avg/day: {_fmt_duration(sum(daily_vals) / len(daily_vals))}")

    # Recommendations
    print(f"\n{'─'*78}")
    print(f"\n💡 RECOMMENDATIONS:")
    if budget_remaining <= 0:
        print(f"   🔴 Budget exhausted — consider deploy freeze and incident review")
        print(f"   🔴 Prioritize reliability work over new features this period")
    elif current_burn_rate >= 3.0:
        print(f"   🟠 Burning fast — investigate recent incidents, consider slowing deploys")
        print(f"   🟠 Run a reliability review and identify top error sources")
    elif current_burn_rate >= 1.5:
        print(f"   🟡 Above pace — monitor closely, review recent changes for regressions")
    elif current_burn_rate >= 1.0:
        print(f"   🟡 Slightly above pace — keep monitoring, no action needed yet")
    else:
        print(f"   🟢 Within budget — safe to continue normal development velocity")
        headroom = budget_remaining - (remaining_days * MINUTES_PER_DAY * (1 - sla_pct / 100))
        if headroom > 0:
            print(f"   🟢 Budget headroom: {_fmt_duration(headroom)} above ideal pace")

    print(f"\n   General guidelines:")
    print(f"   • >50% budget used in first half → shift to reliability")
    print(f"   • Burn rate >2x sustained → escalate to engineering leadership")
    print(f"   • Use multi-window rates to distinguish spikes from trends")
    print("\n" + "=" * 78)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Track SLA error budget consumption rate and project exhaustion. "
                    "Complements sla-uptime-calculator with a forward-looking, time-series view.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --sla 99.9 --period-days 30 --elapsed-days 15 --downtime-minutes 20
  %(prog)s --sla 99.9 --period-days 30 --csv daily_errors.csv
  %(prog)s --sla 99.95 --period-days 30 --incidents incidents.csv --multi-window
  %(prog)s --sla 99.9 --period-days 30 --csv errors.csv --output budget.json
        """,
    )
    parser.add_argument("--sla", "-s", type=float, required=True, help="SLA target (e.g. 99.9)")
    parser.add_argument("--period-days", "-p", type=float, required=True, help="SLA period in days (e.g. 30)")
    parser.add_argument("--elapsed-days", "-e", type=float, help="Days elapsed in current period")
    parser.add_argument("--downtime-minutes", "-d", type=float, help="Total downtime in minutes (inline mode)")
    parser.add_argument("--csv", "-c", type=str, help="CSV of daily downtime data")
    parser.add_argument("--incidents", type=str, help="CSV of incidents (date, duration_minutes)")
    parser.add_argument("--multi-window", action="store_true", help="Show multi-window burn rates")
    parser.add_argument("--output", "-o", type=str, help="Write JSON results to file")
    args = parser.parse_args()

    if not (0 < args.sla <= 100):
        print("Error: --sla must be in (0, 100].", file=sys.stderr)
        return 1

    period_minutes = args.period_days * MINUTES_PER_DAY
    budget_mins = error_budget_total(args.sla, period_minutes)

    timeseries: Optional[List[Dict[str, Any]]] = None
    total_downtime = 0.0
    elapsed_days = args.elapsed_days

    if args.csv:
        try:
            timeseries = load_timeseries_csv(args.csv)
        except Exception as e:
            print(f"Error loading CSV: {e}", file=sys.stderr)
            return 1
        total_downtime = sum(e["downtime_minutes"] for e in timeseries)
        if elapsed_days is None:
            elapsed_days = len(timeseries)
    elif args.incidents:
        try:
            timeseries = load_incidents_csv(args.incidents)
        except Exception as e:
            print(f"Error loading incidents CSV: {e}", file=sys.stderr)
            return 1
        total_downtime = sum(e["downtime_minutes"] for e in timeseries)
        if elapsed_days is None:
            elapsed_days = len(timeseries)
    elif args.downtime_minutes is not None:
        total_downtime = args.downtime_minutes
        if elapsed_days is None:
            print("Error: --elapsed-days required with --downtime-minutes.", file=sys.stderr)
            return 1
    else:
        print("Error: provide --csv, --incidents, or --downtime-minutes.", file=sys.stderr)
        parser.print_help(sys.stderr)
        return 1

    if elapsed_days is None or elapsed_days <= 0:
        print("Error: elapsed days must be > 0.", file=sys.stderr)
        return 1

    elapsed_minutes = elapsed_days * MINUTES_PER_DAY
    budget_remaining = budget_mins - total_downtime
    current_rate = burn_rate(total_downtime, elapsed_minutes, budget_mins, period_minutes)
    projected = projected_consumption(total_downtime, elapsed_minutes, period_minutes)

    # Time to exhaustion
    if total_downtime > 0 and elapsed_minutes > 0:
        consumption_rate_per_minute = total_downtime / elapsed_minutes
        exhaust_mins = time_to_exhaustion(budget_remaining, consumption_rate_per_minute)
        exhaustion_days = exhaust_mins / MINUTES_PER_DAY if exhaust_mins is not None else None
    else:
        exhaustion_days = None

    # Multi-window
    multi_window = None
    if args.multi_window and timeseries:
        multi_window = multi_window_burn_rates(timeseries, budget_mins, period_minutes)

    # Report
    print_report(
        sla_pct=args.sla,
        period_days=args.period_days,
        elapsed_days=elapsed_days,
        total_downtime=total_downtime,
        budget_total_mins=budget_mins,
        budget_remaining=budget_remaining,
        current_burn_rate=current_rate,
        projected_total=projected,
        exhaustion_days=exhaustion_days,
        multi_window=multi_window,
        timeseries=timeseries,
    )

    # JSON output
    if args.output:
        report = {
            "sla_pct": args.sla,
            "period_days": args.period_days,
            "elapsed_days": elapsed_days,
            "budget_total_minutes": round(budget_mins, 2),
            "budget_consumed_minutes": round(total_downtime, 2),
            "budget_remaining_minutes": round(budget_remaining, 2),
            "budget_used_pct": round(total_downtime / budget_mins * 100, 2) if budget_mins > 0 else 0,
            "burn_rate": round(current_rate, 2),
            "projected_total_minutes": round(projected, 2),
            "exhaustion_days": round(exhaustion_days, 1) if exhaustion_days else None,
        }
        if multi_window:
            report["multi_window_rates"] = multi_window

        with open(args.output, "w") as f:
            json.dump(report, f, indent=2)
        print(f"\n📁 Results saved to {args.output}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
