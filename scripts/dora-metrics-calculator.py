#!/usr/bin/env python3
"""
DORA Metrics Calculator

Calculate the four DORA (DevOps Research and Assessment) metrics that define
software delivery performance:

    1. Deployment Frequency      – How often code is deployed to production
    2. Lead Time for Changes     – Time from commit to production deploy
    3. Change Failure Rate       – % of deployments that cause a failure
    4. Mean Time to Recovery     – How long it takes to recover from failure

Classifies team as Elite / High / Medium / Low based on the 2023 DORA
benchmark thresholds.

Usage:
    # From CSV of deployments
    python dora-metrics-calculator.py --csv deployments.csv

    # Specify column names
    python dora-metrics-calculator.py --csv deploys.csv \\
        --deploy-date deployed_at --commit-date committed_at \\
        --failed is_failure --recovery-time recovery_hours

    # With incidents CSV for MTTR
    python dora-metrics-calculator.py --csv deployments.csv --incidents incidents.csv

    # Inline quick estimate
    python dora-metrics-calculator.py \\
        --deploys-per-week 12 \\
        --lead-time-hours 4.5 \\
        --failure-rate-pct 8 \\
        --mttr-hours 1.5

CSV format (deployments):
    deploy_id,deploy_date,commit_date,failed,recovery_hours
    d-101,2025-06-01 14:30,2025-06-01 10:00,false,
    d-102,2025-06-01 16:45,2025-06-01 09:15,true,1.5
    d-103,2025-06-02 09:00,2025-06-01 15:30,false,
    ...

    Required: deploy_date
    Optional: commit_date (for lead time), failed (for CFR), recovery_hours (for MTTR)

CSV format (incidents — alternative for MTTR):
    incident_id,started,resolved
    inc-1,2025-06-01 16:50,2025-06-01 18:20
    ...

Requirements:
    None (stdlib only). Optional: python-dateutil for flexible date parsing.
"""

import argparse
import csv
import json
import math
import sys
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Date parsing (matches cycle-lead-time-analyzer pattern)
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
        ("%Y-%m-%dT%H:%M", 16),
        ("%Y-%m-%d %H:%M", 16),
        ("%Y-%m-%d", 10),
        ("%Y/%m/%d", 10),
        ("%m/%d/%Y", 10),
    ]:
        try:
            return datetime.strptime(s[:trim], fmt)
        except ValueError:
            continue
    return None


# ---------------------------------------------------------------------------
# DORA benchmark thresholds (2023 State of DevOps Report)
# ---------------------------------------------------------------------------

DORA_BENCHMARKS = {
    "deployment_frequency": [
        ("Elite", "On-demand (multiple deploys per day)", lambda d: d >= 1.0),
        ("High", "Between once per day and once per week", lambda d: d >= 1 / 7),
        ("Medium", "Between once per week and once per month", lambda d: d >= 1 / 30),
        ("Low", "Less than once per month", lambda d: True),
    ],
    "lead_time_for_changes": [
        ("Elite", "Less than one hour", lambda h: h < 1),
        ("High", "Between one day and one week", lambda h: h < 24),
        ("Medium", "Between one week and one month", lambda h: h < 24 * 7),
        ("Low", "More than one month", lambda h: True),
    ],
    "change_failure_rate": [
        ("Elite", "0-5%", lambda p: p <= 5),
        ("High", "5-10%", lambda p: p <= 10),
        ("Medium", "10-15%", lambda p: p <= 15),
        ("Low", "More than 15%", lambda p: True),
    ],
    "mttr": [
        ("Elite", "Less than one hour", lambda h: h < 1),
        ("High", "Less than one day", lambda h: h < 24),
        ("Medium", "Between one day and one week", lambda h: h < 24 * 7),
        ("Low", "More than one week", lambda h: True),
    ],
}

TIER_EMOJI = {"Elite": "🟣", "High": "🟢", "Medium": "🟡", "Low": "🔴"}


def classify(metric_name: str, value: float) -> Tuple[str, str]:
    """Classify a metric value into a DORA tier. Returns (tier, description)."""
    for tier, desc, test in DORA_BENCHMARKS[metric_name]:
        if test(value):
            return tier, desc
    return "Low", ""


# ---------------------------------------------------------------------------
# Statistics helpers
# ---------------------------------------------------------------------------

def percentile(values: List[float], p: float) -> float:
    if not values:
        return 0.0
    s = sorted(values)
    n = len(s)
    idx = p / 100.0 * (n - 1)
    lo = int(idx)
    hi = min(lo + 1, n - 1)
    w = idx - lo
    return s[lo] * (1 - w) + s[hi] * w


def mean(values: List[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def median(values: List[float]) -> float:
    return percentile(values, 50)


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def _col(fieldnames: List[str], *aliases: str) -> Optional[str]:
    lower_map = {f.lower().strip(): f for f in fieldnames}
    for alias in aliases:
        if alias.lower().strip() in lower_map:
            return lower_map[alias.lower().strip()]
    return None


def _bool(val: str) -> bool:
    return val.strip().lower() in ("true", "1", "yes", "y", "failed", "failure")


def load_deployments(
    path: str,
    deploy_date_col: str = "deploy_date",
    commit_date_col: str = "commit_date",
    failed_col: str = "failed",
    recovery_col: str = "recovery_hours",
) -> List[Dict[str, Any]]:
    """Load deployment records from CSV."""
    deployments: List[Dict[str, Any]] = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fields = reader.fieldnames or []

        c_deploy = _col(fields, deploy_date_col, "deploy_date", "deployed_at", "deploy_time",
                        "deployed", "date", "timestamp")
        c_commit = _col(fields, commit_date_col, "commit_date", "committed_at", "commit_time",
                        "first_commit", "merged_at", "merge_date")
        c_failed = _col(fields, failed_col, "failed", "failure", "is_failure", "is_failed",
                        "rollback", "incident")
        c_recovery = _col(fields, recovery_col, "recovery_hours", "recovery_time",
                          "mttr_hours", "time_to_recover")
        c_id = _col(fields, "deploy_id", "id", "deployment_id", "name")

        for row in reader:
            deploy_dt = parse_date(row.get(c_deploy or "", ""))
            if not deploy_dt:
                continue

            commit_dt = parse_date(row.get(c_commit or "", "")) if c_commit else None
            failed = _bool(row.get(c_failed or "", "")) if c_failed else False

            recovery_hours: Optional[float] = None
            if c_recovery:
                raw = row.get(c_recovery, "").strip()
                if raw:
                    try:
                        recovery_hours = float(raw)
                    except ValueError:
                        pass

            lead_time_hours: Optional[float] = None
            if commit_dt and deploy_dt >= commit_dt:
                lead_time_hours = (deploy_dt - commit_dt).total_seconds() / 3600

            deployments.append({
                "id": row.get(c_id or "", str(len(deployments) + 1)).strip(),
                "deploy_date": deploy_dt,
                "commit_date": commit_dt,
                "lead_time_hours": lead_time_hours,
                "failed": failed,
                "recovery_hours": recovery_hours,
            })

    return deployments


def load_incidents(path: str) -> List[Dict[str, Any]]:
    """Load incidents from CSV for MTTR calculation."""
    incidents: List[Dict[str, Any]] = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fields = reader.fieldnames or []

        c_started = _col(fields, "started", "start_time", "detected", "opened", "created")
        c_resolved = _col(fields, "resolved", "end_time", "recovered", "closed", "fixed")
        c_id = _col(fields, "incident_id", "id", "name")

        for row in reader:
            started = parse_date(row.get(c_started or "", ""))
            resolved = parse_date(row.get(c_resolved or "", ""))
            if not started or not resolved:
                continue
            duration_hours = (resolved - started).total_seconds() / 3600
            if duration_hours < 0:
                continue

            incidents.append({
                "id": row.get(c_id or "", str(len(incidents) + 1)).strip(),
                "started": started,
                "resolved": resolved,
                "duration_hours": round(duration_hours, 2),
            })

    return incidents


# ---------------------------------------------------------------------------
# Metric computation
# ---------------------------------------------------------------------------

def compute_deployment_frequency(
    deployments: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Compute deployment frequency (deploys per day)."""
    if not deployments:
        return {"deploys_per_day": 0, "deploys_per_week": 0, "tier": "Low", "tier_desc": "No data"}

    dates = sorted(d["deploy_date"] for d in deployments)
    span_days = max((dates[-1] - dates[0]).total_seconds() / 86400, 1)
    total = len(deployments)
    per_day = total / span_days
    per_week = per_day * 7

    # Daily breakdown
    daily_counts: Dict[str, int] = defaultdict(int)
    for d in deployments:
        day_key = d["deploy_date"].strftime("%Y-%m-%d")
        daily_counts[day_key] += 1

    days_with_deploys = len(daily_counts)
    total_calendar_days = int(span_days) + 1
    pct_days_with_deploys = days_with_deploys / total_calendar_days * 100 if total_calendar_days > 0 else 0

    tier, tier_desc = classify("deployment_frequency", per_day)

    return {
        "total_deployments": total,
        "span_days": round(span_days, 1),
        "deploys_per_day": round(per_day, 2),
        "deploys_per_week": round(per_week, 1),
        "days_with_deploys": days_with_deploys,
        "total_calendar_days": total_calendar_days,
        "pct_days_with_deploys": round(pct_days_with_deploys, 1),
        "daily_counts": dict(sorted(daily_counts.items())[-14:]),
        "tier": tier,
        "tier_desc": tier_desc,
    }


def compute_lead_time(deployments: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Compute lead time for changes (commit to deploy)."""
    lead_times = [d["lead_time_hours"] for d in deployments if d["lead_time_hours"] is not None]

    if not lead_times:
        return {"available": False, "tier": "Unknown", "tier_desc": "No commit date data"}

    med = median(lead_times)
    tier, tier_desc = classify("lead_time_for_changes", med)

    return {
        "available": True,
        "n_with_data": len(lead_times),
        "mean_hours": round(mean(lead_times), 2),
        "median_hours": round(med, 2),
        "p90_hours": round(percentile(lead_times, 90), 2),
        "p95_hours": round(percentile(lead_times, 95), 2),
        "min_hours": round(min(lead_times), 2),
        "max_hours": round(max(lead_times), 2),
        "tier": tier,
        "tier_desc": tier_desc,
    }


def compute_change_failure_rate(deployments: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Compute change failure rate (% of deploys causing failures)."""
    total = len(deployments)
    if total == 0:
        return {"failure_rate_pct": 0, "tier": "Unknown", "tier_desc": "No data"}

    failures = sum(1 for d in deployments if d["failed"])
    rate = failures / total * 100

    tier, tier_desc = classify("change_failure_rate", rate)

    return {
        "total_deployments": total,
        "failed_deployments": failures,
        "successful_deployments": total - failures,
        "failure_rate_pct": round(rate, 1),
        "tier": tier,
        "tier_desc": tier_desc,
    }


def compute_mttr(
    deployments: List[Dict[str, Any]],
    incidents: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Compute mean time to recovery."""
    recovery_times: List[float] = []

    # From deployment recovery_hours
    for d in deployments:
        if d["failed"] and d["recovery_hours"] is not None:
            recovery_times.append(d["recovery_hours"])

    # From separate incidents CSV
    if incidents:
        for inc in incidents:
            recovery_times.append(inc["duration_hours"])

    if not recovery_times:
        return {"available": False, "tier": "Unknown", "tier_desc": "No recovery time data"}

    avg = mean(recovery_times)
    tier, tier_desc = classify("mttr", avg)

    return {
        "available": True,
        "n_incidents": len(recovery_times),
        "mean_hours": round(avg, 2),
        "median_hours": round(median(recovery_times), 2),
        "p90_hours": round(percentile(recovery_times, 90), 2),
        "min_hours": round(min(recovery_times), 2),
        "max_hours": round(max(recovery_times), 2),
        "tier": tier,
        "tier_desc": tier_desc,
    }


# ---------------------------------------------------------------------------
# Overall classification
# ---------------------------------------------------------------------------

TIER_RANK = {"Elite": 4, "High": 3, "Medium": 2, "Low": 1, "Unknown": 0}


def overall_classification(metrics: Dict[str, Dict]) -> Tuple[str, str]:
    """Determine overall DORA classification from the four metrics."""
    tiers = [m.get("tier", "Unknown") for m in metrics.values()]
    known = [t for t in tiers if t != "Unknown"]

    if not known:
        return "Unknown", "Insufficient data to classify"

    avg_rank = sum(TIER_RANK[t] for t in known) / len(known)

    if avg_rank >= 3.5:
        return "Elite", "Top-tier software delivery performance"
    elif avg_rank >= 2.5:
        return "High", "Strong delivery performance with room to optimize"
    elif avg_rank >= 1.5:
        return "Medium", "Moderate performance — focus on lead time and failure rate"
    else:
        return "Low", "Significant improvement opportunities across the board"


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def _bar(value: float, max_val: float, width: int = 25) -> str:
    if max_val <= 0:
        return "░" * width
    ratio = min(1.0, max(0.0, value / max_val))
    filled = int(ratio * width)
    return "█" * filled + "░" * (width - filled)


def _format_hours(h: float) -> str:
    if h < 1:
        return f"{h * 60:.0f} min"
    if h < 24:
        return f"{h:.1f} hours"
    if h < 24 * 7:
        return f"{h / 24:.1f} days"
    return f"{h / (24 * 7):.1f} weeks"


def _sparkline(daily_counts: Dict[str, int], width: int = 14) -> str:
    """Mini sparkline of recent daily deploy counts."""
    if not daily_counts:
        return ""
    blocks = " ▁▂▃▄▅▆▇█"
    vals = list(daily_counts.values())[-width:]
    mx = max(vals) if vals else 1
    return "".join(blocks[min(8, int(v / max(mx, 1) * 8))] for v in vals)


def print_report(
    df: Dict[str, Any],
    lt: Dict[str, Any],
    cfr: Dict[str, Any],
    mttr_data: Dict[str, Any],
    overall_tier: str,
    overall_desc: str,
) -> None:
    """Pretty-print DORA metrics report."""
    print("\n" + "=" * 78)
    print("📊 DORA METRICS CALCULATOR")
    print("=" * 78)

    # Overall classification
    emoji = TIER_EMOJI.get(overall_tier, "⚪")
    print(f"\n🏆 OVERALL CLASSIFICATION: {emoji} {overall_tier}")
    print(f"   {overall_desc}")

    # Metric summary table
    print(f"\n📐 METRIC SUMMARY:")
    print(f"   {'Metric':<28} {'Value':>16} {'Tier':>8}")
    print(f"   {'─'*28} {'─'*16} {'─'*8}")

    # Deployment Frequency
    df_val = f"{df['deploys_per_day']:.1f}/day ({df['deploys_per_week']:.0f}/wk)" if df["deploys_per_day"] > 0 else "—"
    df_emoji = TIER_EMOJI.get(df["tier"], "⚪")
    print(f"   {'Deployment Frequency':<28} {df_val:>16} {df_emoji} {df['tier']}")

    # Lead Time
    if lt.get("available"):
        lt_val = _format_hours(lt["median_hours"])
        lt_emoji = TIER_EMOJI.get(lt["tier"], "⚪")
        print(f"   {'Lead Time for Changes':<28} {lt_val:>16} {lt_emoji} {lt['tier']}")
    else:
        print(f"   {'Lead Time for Changes':<28} {'—':>16} {'⚪'} {'N/A'}")

    # Change Failure Rate
    cfr_val = f"{cfr['failure_rate_pct']:.1f}%"
    cfr_emoji = TIER_EMOJI.get(cfr["tier"], "⚪")
    print(f"   {'Change Failure Rate':<28} {cfr_val:>16} {cfr_emoji} {cfr['tier']}")

    # MTTR
    if mttr_data.get("available"):
        mttr_val = _format_hours(mttr_data["mean_hours"])
        mttr_emoji = TIER_EMOJI.get(mttr_data["tier"], "⚪")
        print(f"   {'Mean Time to Recovery':<28} {mttr_val:>16} {mttr_emoji} {mttr_data['tier']}")
    else:
        print(f"   {'Mean Time to Recovery':<28} {'—':>16} {'⚪'} {'N/A'}")

    # Deployment Frequency detail
    print(f"\n{'─'*78}")
    print(f"\n📦 DEPLOYMENT FREQUENCY:")
    print(f"   • Total deployments:       {df['total_deployments']}")
    print(f"   • Time span:               {df['span_days']:.0f} days")
    print(f"   • Deploys per day:          {df['deploys_per_day']:.2f}")
    print(f"   • Deploys per week:         {df['deploys_per_week']:.1f}")
    print(f"   • Days with ≥1 deploy:     {df['days_with_deploys']} / {df['total_calendar_days']} ({df['pct_days_with_deploys']:.0f}%)")
    if df.get("daily_counts"):
        spark = _sparkline(df["daily_counts"])
        print(f"   • Recent trend:             {spark}  (last {len(df['daily_counts'])} days)")

    # Lead Time detail
    if lt.get("available"):
        print(f"\n⏱️  LEAD TIME FOR CHANGES (commit → deploy):")
        print(f"   • Median:       {_format_hours(lt['median_hours'])}")
        print(f"   • Mean:         {_format_hours(lt['mean_hours'])}")
        print(f"   • p90:          {_format_hours(lt['p90_hours'])}")
        print(f"   • p95:          {_format_hours(lt['p95_hours'])}")
        print(f"   • Range:        {_format_hours(lt['min_hours'])} – {_format_hours(lt['max_hours'])}")
        print(f"   • Data points:  {lt['n_with_data']}")

    # Change Failure Rate detail
    print(f"\n🔥 CHANGE FAILURE RATE:")
    print(f"   • Total:       {cfr['total_deployments']} deployments")
    print(f"   • Failed:      {cfr['failed_deployments']}")
    print(f"   • Successful:  {cfr['successful_deployments']}")
    print(f"   • Failure rate: {cfr['failure_rate_pct']:.1f}%")
    bar = _bar(cfr["failure_rate_pct"], 30, 30)
    print(f"   • Gauge:        {bar}  ({cfr['failure_rate_pct']:.1f}% of 30%)")

    # MTTR detail
    if mttr_data.get("available"):
        print(f"\n🔧 MEAN TIME TO RECOVERY:")
        print(f"   • Mean:         {_format_hours(mttr_data['mean_hours'])}")
        print(f"   • Median:       {_format_hours(mttr_data['median_hours'])}")
        print(f"   • p90:          {_format_hours(mttr_data['p90_hours'])}")
        print(f"   • Range:        {_format_hours(mttr_data['min_hours'])} – {_format_hours(mttr_data['max_hours'])}")
        print(f"   • Incidents:    {mttr_data['n_incidents']}")

    # DORA benchmarks reference
    print(f"\n{'─'*78}")
    print(f"\n📚 DORA BENCHMARKS (2023 State of DevOps Report):")
    print(f"   {'Metric':<28} {'🟣 Elite':<18} {'🟢 High':<18} {'🟡 Medium':<18} {'🔴 Low'}")
    print(f"   {'─'*28} {'─'*18} {'─'*18} {'─'*18} {'─'*18}")
    print(f"   {'Deploy Frequency':<28} {'Multiple/day':<18} {'Daily-weekly':<18} {'Weekly-monthly':<18} {'< monthly'}")
    print(f"   {'Lead Time':<28} {'< 1 hour':<18} {'< 1 day':<18} {'< 1 week':<18} {'> 1 month'}")
    print(f"   {'Change Failure Rate':<28} {'0-5%':<18} {'5-10%':<18} {'10-15%':<18} {'> 15%'}")
    print(f"   {'MTTR':<28} {'< 1 hour':<18} {'< 1 day':<18} {'< 1 week':<18} {'> 1 week'}")

    # Recommendations
    tiers = {
        "Deployment Frequency": df["tier"],
        "Lead Time": lt.get("tier", "Unknown"),
        "Change Failure Rate": cfr["tier"],
        "MTTR": mttr_data.get("tier", "Unknown"),
    }
    weak = [name for name, tier in tiers.items() if tier in ("Low", "Medium")]
    if weak:
        print(f"\n💡 IMPROVEMENT OPPORTUNITIES:")
        for name in weak:
            tier = tiers[name]
            if name == "Deployment Frequency":
                print(f"   • {name} ({tier}): invest in CI/CD automation, reduce batch sizes, enable feature flags")
            elif name == "Lead Time":
                print(f"   • {name} ({tier}): automate testing, reduce PR review queues, enable trunk-based dev")
            elif name == "Change Failure Rate":
                print(f"   • {name} ({tier}): improve test coverage, add canary deploys, strengthen code review")
            elif name == "MTTR":
                print(f"   • {name} ({tier}): improve observability, runbooks, incident response automation")
    else:
        print(f"\n💡 All metrics at High or Elite — focus on sustaining and mentoring other teams.")

    print("\n" + "=" * 78)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Calculate the four DORA metrics for software delivery performance. "
                    "Classifies teams as Elite / High / Medium / Low.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --csv deployments.csv
  %(prog)s --csv deploys.csv --incidents incidents.csv
  %(prog)s --deploys-per-week 12 --lead-time-hours 4.5 --failure-rate-pct 8 --mttr-hours 1.5
  %(prog)s --csv deployments.csv --output dora-report.json
        """,
    )

    # CSV mode
    parser.add_argument("--csv", "-c", type=str, help="CSV file with deployment records")
    parser.add_argument("--incidents", type=str, help="Separate CSV of incidents (for MTTR)")
    parser.add_argument("--deploy-date", type=str, default="deploy_date", help="Deploy date column name")
    parser.add_argument("--commit-date", type=str, default="commit_date", help="Commit date column name")
    parser.add_argument("--failed", type=str, default="failed", help="Failure flag column name")
    parser.add_argument("--recovery-time", type=str, default="recovery_hours", help="Recovery hours column name")

    # Inline mode
    parser.add_argument("--deploys-per-week", type=float, help="Deploys per week (inline mode)")
    parser.add_argument("--lead-time-hours", type=float, help="Median lead time in hours (inline mode)")
    parser.add_argument("--failure-rate-pct", type=float, help="Change failure rate %% (inline mode)")
    parser.add_argument("--mttr-hours", type=float, help="Mean time to recovery in hours (inline mode)")

    parser.add_argument("--output", "-o", type=str, help="Write results to JSON file")
    args = parser.parse_args()

    if args.csv:
        # CSV mode
        try:
            deployments = load_deployments(
                args.csv,
                deploy_date_col=args.deploy_date,
                commit_date_col=args.commit_date,
                failed_col=args.failed,
                recovery_col=args.recovery_time,
            )
        except Exception as e:
            print(f"Error loading deployments CSV: {e}", file=sys.stderr)
            return 1

        if not deployments:
            print("Error: no valid deployments found. Check CSV columns.", file=sys.stderr)
            return 1

        incidents = None
        if args.incidents:
            try:
                incidents = load_incidents(args.incidents)
            except Exception as e:
                print(f"Error loading incidents CSV: {e}", file=sys.stderr)
                return 1

        df = compute_deployment_frequency(deployments)
        lt = compute_lead_time(deployments)
        cfr = compute_change_failure_rate(deployments)
        mttr_data = compute_mttr(deployments, incidents)

    elif args.deploys_per_week is not None or args.lead_time_hours is not None:
        # Inline mode
        dpw = args.deploys_per_week or 0
        dpd = dpw / 7

        df_tier, df_desc = classify("deployment_frequency", dpd)
        df = {
            "total_deployments": int(dpw),
            "span_days": 7,
            "deploys_per_day": round(dpd, 2),
            "deploys_per_week": round(dpw, 1),
            "days_with_deploys": min(7, int(dpw)),
            "total_calendar_days": 7,
            "pct_days_with_deploys": round(min(100, dpw / 7 * 100), 1),
            "daily_counts": {},
            "tier": df_tier,
            "tier_desc": df_desc,
        }

        lth = args.lead_time_hours
        if lth is not None:
            lt_tier, lt_desc = classify("lead_time_for_changes", lth)
            lt = {
                "available": True,
                "n_with_data": 1,
                "mean_hours": lth,
                "median_hours": lth,
                "p90_hours": lth,
                "p95_hours": lth,
                "min_hours": lth,
                "max_hours": lth,
                "tier": lt_tier,
                "tier_desc": lt_desc,
            }
        else:
            lt = {"available": False, "tier": "Unknown", "tier_desc": "Not provided"}

        fr = args.failure_rate_pct or 0
        cfr_tier, cfr_desc = classify("change_failure_rate", fr)
        cfr = {
            "total_deployments": int(dpw),
            "failed_deployments": int(dpw * fr / 100),
            "successful_deployments": int(dpw * (1 - fr / 100)),
            "failure_rate_pct": round(fr, 1),
            "tier": cfr_tier,
            "tier_desc": cfr_desc,
        }

        mh = args.mttr_hours
        if mh is not None:
            mttr_tier, mttr_desc = classify("mttr", mh)
            mttr_data = {
                "available": True,
                "n_incidents": 1,
                "mean_hours": mh,
                "median_hours": mh,
                "p90_hours": mh,
                "min_hours": mh,
                "max_hours": mh,
                "tier": mttr_tier,
                "tier_desc": mttr_desc,
            }
        else:
            mttr_data = {"available": False, "tier": "Unknown", "tier_desc": "Not provided"}
    else:
        print("Error: provide --csv or inline metrics (--deploys-per-week, etc.).", file=sys.stderr)
        parser.print_help(sys.stderr)
        return 1

    # Overall classification
    metrics = {
        "deployment_frequency": df,
        "lead_time": lt,
        "change_failure_rate": cfr,
        "mttr": mttr_data,
    }
    overall_tier, overall_desc = overall_classification(metrics)

    # Report
    print_report(df, lt, cfr, mttr_data, overall_tier, overall_desc)

    # JSON output
    if args.output:
        report = {
            "overall_tier": overall_tier,
            "overall_description": overall_desc,
            "deployment_frequency": {k: v for k, v in df.items() if k != "daily_counts"},
            "lead_time": lt,
            "change_failure_rate": cfr,
            "mttr": mttr_data,
        }
        with open(args.output, "w") as f:
            json.dump(report, f, indent=2, default=str)
        print(f"\n📁 Results saved to {args.output}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
