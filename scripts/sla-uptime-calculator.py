#!/usr/bin/env python3
"""
SLA / Uptime Calculator

Given downtime incidents and an SLA target, calculate actual uptime percentage,
error budget remaining, and SLA breach risk. Complements latency-slo-calculator.py
which converts targets into budgets; this tool works backwards from actual
incidents to report status.

Usage:
    python sla-uptime-calculator.py --sla 99.9 --incidents 45 120 15
    python sla-uptime-calculator.py --sla 99.95 --incidents 10 5 3 --period-days 7
    python sla-uptime-calculator.py --sla 99.9 --csv incidents.csv
    python sla-uptime-calculator.py --sla 99.9 --incidents 120 60 --period-days 30 --forecast-days 90

CSV format (header row required):
    date,duration_minutes,description
    2025-01-15,45,API gateway timeout
    2025-01-22,120,Database failover
    ...

Requirements:
    None (stdlib only).
"""

import argparse
import csv
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple


# Approximate constants
MINUTES_PER_DAY = 24 * 60
DEFAULT_PERIOD_DAYS = 30.44  # average month


def parse_incidents_csv(path: str) -> List[Dict]:
    """Load incidents from CSV. Returns list of {date, duration_minutes, description}."""
    incidents: List[Dict] = []
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            duration = float(row.get("duration_minutes", 0))
            date_str = row.get("date", "")
            desc = row.get("description", "")
            incidents.append({
                "date": date_str,
                "duration_minutes": duration,
                "description": desc,
            })
    return incidents


def compute_uptime(
    total_downtime_minutes: float,
    period_minutes: float,
) -> float:
    """Actual uptime percentage."""
    if period_minutes <= 0:
        return 100.0
    uptime = (period_minutes - total_downtime_minutes) / period_minutes
    return max(0.0, min(100.0, uptime * 100.0))


def error_budget_total(sla_pct: float, period_minutes: float) -> float:
    """Total error budget in minutes for the period."""
    return period_minutes * (1.0 - sla_pct / 100.0)


def error_budget_remaining(
    sla_pct: float,
    total_downtime_minutes: float,
    period_minutes: float,
) -> float:
    """Remaining error budget in minutes."""
    budget = error_budget_total(sla_pct, period_minutes)
    return budget - total_downtime_minutes


def burn_rate(
    total_downtime_minutes: float,
    elapsed_days: float,
    sla_pct: float,
    period_days: float,
) -> Optional[float]:
    """
    Burn rate: ratio of actual error consumption rate to allowed rate.
    >1.0 means consuming budget faster than allowed.
    """
    if elapsed_days <= 0 or period_days <= 0:
        return None
    actual_rate = total_downtime_minutes / elapsed_days  # min/day consumed
    budget = error_budget_total(sla_pct, period_days * MINUTES_PER_DAY)
    allowed_rate = budget / period_days  # min/day allowed
    if allowed_rate <= 0:
        return None
    return actual_rate / allowed_rate


def forecast_breach(
    total_downtime_minutes: float,
    elapsed_days: float,
    sla_pct: float,
    period_days: float,
    forecast_days: float,
) -> Dict:
    """
    Forecast whether SLA will be breached by end of forecast period.
    Uses current burn rate to project.
    """
    if elapsed_days <= 0:
        return {"breached": False, "projected_downtime": 0, "projected_uptime": 100.0}

    daily_downtime = total_downtime_minutes / elapsed_days
    projected_downtime = daily_downtime * forecast_days
    forecast_minutes = forecast_days * MINUTES_PER_DAY
    projected_uptime = compute_uptime(projected_downtime, forecast_minutes)
    breached = projected_uptime < sla_pct

    budget = error_budget_total(sla_pct, forecast_minutes)
    days_until_breach = None
    if daily_downtime > 0:
        remaining = budget - total_downtime_minutes
        if remaining > 0:
            days_until_breach = remaining / daily_downtime
        else:
            days_until_breach = 0  # already breached

    return {
        "breached": breached,
        "projected_downtime": projected_downtime,
        "projected_uptime": projected_uptime,
        "days_until_breach": days_until_breach,
    }


def format_duration(minutes: float) -> str:
    """Format minutes as human-readable duration."""
    if minutes < 1:
        return f"{minutes * 60:.0f}s"
    if minutes < 60:
        return f"{minutes:.1f}m"
    hours = minutes / 60
    if hours < 24:
        return f"{hours:.1f}h"
    days = hours / 24
    return f"{days:.1f}d"


def main():
    parser = argparse.ArgumentParser(
        description="Calculate actual uptime, error budget remaining, and SLA breach risk from incidents."
    )
    parser.add_argument(
        "--sla", "-s", type=float, required=True,
        help="SLA target (e.g. 99.9 for 99.9%% uptime)",
    )
    parser.add_argument(
        "--incidents", "-i", type=float, nargs="+",
        help="Downtime durations in minutes (e.g. 45 120 15)",
    )
    parser.add_argument(
        "--csv", type=str,
        help="CSV file with columns: date, duration_minutes, description",
    )
    parser.add_argument(
        "--period-days", "-p", type=float, default=DEFAULT_PERIOD_DAYS,
        help=f"Reporting period in days (default: {DEFAULT_PERIOD_DAYS:.1f} = ~1 month)",
    )
    parser.add_argument(
        "--elapsed-days", type=float, default=None,
        help="Days elapsed in current period (default: same as --period-days)",
    )
    parser.add_argument(
        "--forecast-days", type=float, default=None,
        help="Days to forecast ahead for breach risk (e.g. 90 for quarter)",
    )
    args = parser.parse_args()

    if not (0 < args.sla <= 100):
        print("Error: --sla must be in (0, 100]", file=sys.stderr)
        return 1

    # Collect incidents
    incident_durations: List[float] = []
    incident_details: List[Dict] = []

    if args.csv:
        try:
            incident_details = parse_incidents_csv(args.csv)
            incident_durations = [inc["duration_minutes"] for inc in incident_details]
        except Exception as e:
            print(f"Error reading CSV: {e}", file=sys.stderr)
            return 1
    elif args.incidents:
        incident_durations = list(args.incidents)
    else:
        parser.print_help()
        print("\nExample: --sla 99.9 --incidents 45 120 15", file=sys.stderr)
        return 0

    period_days = args.period_days
    elapsed_days = args.elapsed_days if args.elapsed_days is not None else period_days
    period_minutes = period_days * MINUTES_PER_DAY
    total_downtime = sum(incident_durations)
    actual_uptime = compute_uptime(total_downtime, period_minutes)
    budget_total = error_budget_total(args.sla, period_minutes)
    budget_remaining = error_budget_remaining(args.sla, total_downtime, period_minutes)
    budget_used_pct = (total_downtime / budget_total * 100) if budget_total > 0 else 0
    rate = burn_rate(total_downtime, elapsed_days, args.sla, period_days)

    sla_met = actual_uptime >= args.sla

    # Report
    print("\n" + "=" * 70)
    print("📊 SLA / UPTIME CALCULATOR")
    print("=" * 70)

    print(f"\n📋 INPUTS:")
    print(f"   • SLA target:        {args.sla}%")
    print(f"   • Period:            {period_days:.1f} days ({period_minutes:,.0f} minutes)")
    print(f"   • Incidents:         {len(incident_durations)}")
    print(f"   • Total downtime:    {format_duration(total_downtime)} ({total_downtime:.1f} minutes)")

    # Individual incidents (if from CSV with details)
    if incident_details:
        print(f"\n📝 INCIDENTS:")
        for inc in sorted(incident_details, key=lambda x: -x["duration_minutes"]):
            date = inc["date"] if inc["date"] else "—"
            desc = inc["description"] if inc["description"] else "—"
            print(f"   • {date}  {format_duration(inc['duration_minutes']):>6}  {desc}")

    status_icon = "✅" if sla_met else "❌"
    print(f"\n{status_icon} UPTIME STATUS:")
    print(f"   • Actual uptime:     {actual_uptime:.4f}%")
    print(f"   • SLA target:        {args.sla}%")
    print(f"   • Status:            {'MET' if sla_met else 'BREACHED'}")

    budget_icon = "🟢" if budget_remaining > 0 else "🔴"
    print(f"\n{budget_icon} ERROR BUDGET:")
    print(f"   • Total budget:      {format_duration(budget_total)} ({budget_total:.1f} minutes)")
    print(f"   • Used:              {format_duration(total_downtime)} ({budget_used_pct:.1f}%)")
    if budget_remaining >= 0:
        print(f"   • Remaining:         {format_duration(budget_remaining)} ({budget_remaining:.1f} minutes)")
    else:
        print(f"   • Overspent:         {format_duration(abs(budget_remaining))} ({abs(budget_remaining):.1f} minutes over budget)")

    # Budget bar
    bar_used = min(40, int(40 * budget_used_pct / 100))
    bar_remaining = 40 - bar_used
    print(f"   • Budget bar:        [{'█' * bar_used}{'░' * bar_remaining}] {budget_used_pct:.0f}%")

    if rate is not None:
        rate_icon = "🟢" if rate <= 1.0 else ("🟡" if rate <= 2.0 else "🔴")
        print(f"\n{rate_icon} BURN RATE:")
        print(f"   • Current burn rate: {rate:.2f}x")
        if rate > 1.0:
            print(f"   • ⚠️  Consuming budget {rate:.1f}x faster than allowed")
        else:
            print(f"   • Budget consumption is within safe limits")

    # Forecast
    if args.forecast_days:
        fc = forecast_breach(total_downtime, elapsed_days, args.sla, period_days, args.forecast_days)
        fc_icon = "🔴" if fc["breached"] else "🟢"
        print(f"\n{fc_icon} FORECAST ({args.forecast_days:.0f}-day projection):")
        print(f"   • Projected downtime:  {format_duration(fc['projected_downtime'])}")
        print(f"   • Projected uptime:    {fc['projected_uptime']:.4f}%")
        print(f"   • SLA breach:          {'YES — action needed' if fc['breached'] else 'No — on track'}")
        if fc.get("days_until_breach") is not None:
            if fc["days_until_breach"] <= 0:
                print(f"   • ⚠️  Budget already exhausted")
            else:
                print(f"   • Days until budget exhausted: {fc['days_until_breach']:.0f}")

    print("\n" + "=" * 70)
    return 0


if __name__ == "__main__":
    sys.exit(main())
