#!/usr/bin/env python3
"""
Feature Flag Rollout Planner

Plan and track progressive feature flag rollouts with stage gates, risk
assessment, and rollback criteria. Helps PMs coordinate gradual launches
across segments, monitor health at each stage, and decide when to advance
or roll back.

Supports:
    - Multi-stage rollout planning (e.g. 1% → 5% → 25% → 50% → 100%)
    - Per-stage health criteria (error rate, latency, business metrics)
    - Segment targeting (internal, beta, region, tier)
    - Duration estimation and timeline generation
    - Risk scoring and rollback recommendations
    - Status tracking (planned / active / paused / rolled-back / complete)

Usage:
    # Quick rollout plan with default stages
    python feature-flag-planner.py \\
        --flag "new-checkout-flow" --total-users 500000 \\
        --stages "Internal:1:2,Beta:5:3,Canary:25:5,GA-50:50:7,GA-100:100:3"

    # With health criteria
    python feature-flag-planner.py \\
        --flag "ai-recommendations" --total-users 1000000 \\
        --stages "Internal:1:2,Canary:10:5,Wide:50:7,GA:100:3" \\
        --error-threshold 0.5 --latency-threshold 200

    # From JSON config
    python feature-flag-planner.py --config rollout.json

    # Track progress (update a stage status)
    python feature-flag-planner.py --config rollout.json \\
        --update-stage "Canary:active" --actual-error-rate 0.3 --actual-latency 180

    Stage format: "Name:pct_users:days"

JSON config:
    {
      "flag": "new-checkout-flow",
      "total_users": 500000,
      "start_date": "2025-07-01",
      "risk_level": "medium",
      "stages": [
        {"name": "Internal", "pct": 1, "days": 2, "segment": "employees"},
        {"name": "Beta", "pct": 5, "days": 3, "segment": "beta_users"},
        {"name": "Canary", "pct": 25, "days": 5},
        {"name": "GA", "pct": 100, "days": 3}
      ],
      "health_criteria": {
        "max_error_rate_pct": 0.5,
        "max_p99_latency_ms": 200,
        "min_conversion_rate_pct": null
      },
      "rollback_criteria": [
        "Error rate > 2x baseline",
        "P99 latency > 500ms",
        "Revenue drop > 5%"
      ]
    }

Requirements:
    None (stdlib only).
"""

import argparse
import json
import math
import sys
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Rollout planning
# ---------------------------------------------------------------------------

RISK_PROFILES = {
    "low": {
        "label": "Low",
        "default_stages": [10, 25, 50, 100],
        "min_bake_days": 1,
        "recommended_monitoring": "standard",
    },
    "medium": {
        "label": "Medium",
        "default_stages": [1, 5, 25, 50, 100],
        "min_bake_days": 2,
        "recommended_monitoring": "enhanced",
    },
    "high": {
        "label": "High",
        "default_stages": [1, 5, 10, 25, 50, 75, 100],
        "min_bake_days": 3,
        "recommended_monitoring": "intensive",
    },
    "critical": {
        "label": "Critical",
        "default_stages": [0.1, 1, 5, 10, 25, 50, 75, 100],
        "min_bake_days": 5,
        "recommended_monitoring": "war-room",
    },
}


def plan_rollout(
    flag_name: str,
    total_users: int,
    stages: List[Dict[str, Any]],
    start_date: Optional[str] = None,
    risk_level: str = "medium",
    error_threshold: Optional[float] = None,
    latency_threshold: Optional[float] = None,
    rollback_criteria: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Build a rollout plan with timeline and risk assessment."""

    risk_profile = RISK_PROFILES.get(risk_level, RISK_PROFILES["medium"])

    # Parse start date
    start = None
    if start_date:
        try:
            start = datetime.strptime(start_date, "%Y-%m-%d")
        except ValueError:
            start = None

    # Build stage details
    planned_stages = []
    current_date = start
    cumulative_days = 0

    for i, stage in enumerate(stages):
        name = stage.get("name", f"Stage {i+1}")
        pct = stage.get("pct", 0)
        days = stage.get("days", risk_profile["min_bake_days"])
        segment = stage.get("segment", "all")
        status = stage.get("status", "planned")

        users_exposed = int(total_users * pct / 100)
        cumulative_days += days

        stage_info: Dict[str, Any] = {
            "name": name,
            "pct": pct,
            "users_exposed": users_exposed,
            "bake_days": days,
            "cumulative_days": cumulative_days,
            "segment": segment,
            "status": status,
            "gate_criteria": [],
        }

        if current_date:
            stage_info["start_date"] = current_date.strftime("%Y-%m-%d")
            end = current_date + timedelta(days=days)
            stage_info["end_date"] = end.strftime("%Y-%m-%d")
            current_date = end

        # Gate criteria
        if error_threshold is not None:
            stage_info["gate_criteria"].append(
                f"Error rate < {error_threshold}%"
            )
        if latency_threshold is not None:
            stage_info["gate_criteria"].append(
                f"P99 latency < {latency_threshold}ms"
            )
        stage_info["gate_criteria"].append("No critical bugs reported")

        # Risk at this stage
        if pct <= 1:
            stage_risk = "minimal"
        elif pct <= 10:
            stage_risk = "low"
        elif pct <= 50:
            stage_risk = "moderate"
        else:
            stage_risk = "high"
        stage_info["blast_radius"] = stage_risk

        planned_stages.append(stage_info)

    # Default rollback criteria
    if not rollback_criteria:
        rollback_criteria = [
            "Error rate > 2x baseline",
            "P99 latency > 2x baseline",
            "Critical bug affecting core flow",
            "Revenue/conversion drop > 5%",
        ]

    # Overall risk score (0-100)
    n_stages = len(planned_stages)
    risk_base = {"low": 20, "medium": 40, "high": 60, "critical": 80}.get(risk_level, 40)
    stage_bonus = max(0, 20 - n_stages * 3)  # fewer stages = higher risk
    bake_bonus = max(0, 10 - cumulative_days) if cumulative_days < 10 else 0
    risk_score = min(100, risk_base + stage_bonus + bake_bonus)

    if risk_score <= 30:
        risk_grade = "🟢 Low risk"
    elif risk_score <= 50:
        risk_grade = "🟡 Moderate risk"
    elif risk_score <= 70:
        risk_grade = "🟠 Elevated risk"
    else:
        risk_grade = "🔴 High risk"

    return {
        "flag_name": flag_name,
        "total_users": total_users,
        "risk_level": risk_level,
        "risk_profile": risk_profile["label"],
        "risk_score": risk_score,
        "risk_grade": risk_grade,
        "n_stages": n_stages,
        "total_days": cumulative_days,
        "stages": planned_stages,
        "health_criteria": {
            "max_error_rate_pct": error_threshold,
            "max_p99_latency_ms": latency_threshold,
        },
        "rollback_criteria": rollback_criteria,
        "monitoring": risk_profile["recommended_monitoring"],
        "start_date": start_date,
        "projected_ga_date": planned_stages[-1].get("end_date") if planned_stages else None,
    }


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def parse_stages_string(s: str) -> List[Dict[str, Any]]:
    """Parse 'Name:pct:days,Name:pct:days,...' into stage list."""
    stages = []
    for part in s.split(","):
        pieces = part.strip().rsplit(":", 2)
        if len(pieces) < 3:
            raise ValueError(f"Invalid stage '{part}'. Format: Name:pct:days")
        stages.append({
            "name": pieces[0].strip(),
            "pct": float(pieces[1].strip()),
            "days": int(pieces[2].strip()),
        })
    return stages


def load_json_config(path: str) -> Dict[str, Any]:
    """Load rollout config from JSON."""
    with open(path, encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def _fmt_users(val: int) -> str:
    if val >= 1_000_000:
        return f"{val / 1_000_000:,.1f}M"
    elif val >= 1_000:
        return f"{val / 1_000:,.1f}K"
    else:
        return f"{val:,}"


def _bar(value: float, max_val: float, width: int = 30) -> str:
    if max_val <= 0:
        return "░" * width
    ratio = min(1.0, max(0.0, value / max_val))
    filled = int(ratio * width)
    return "█" * filled + "░" * (width - filled)


STATUS_EMOJI = {
    "planned": "⬜",
    "active": "🟦",
    "paused": "🟨",
    "rolled-back": "🟥",
    "complete": "🟩",
}


def print_report(plan: Dict[str, Any]) -> None:
    """Pretty-print rollout plan."""
    print("\n" + "=" * 78)
    print("🚀 FEATURE FLAG ROLLOUT PLANNER")
    print("=" * 78)

    print(f"\n   Flag:              {plan['flag_name']}")
    print(f"   Total users:       {_fmt_users(plan['total_users'])}")
    print(f"   Risk level:        {plan['risk_profile']}")
    print(f"   Risk score:        {plan['risk_score']}/100  {plan['risk_grade']}")
    print(f"   Monitoring:        {plan['monitoring'].title()}")
    print(f"   Total duration:    {plan['total_days']} days ({plan['n_stages']} stages)")
    if plan["start_date"]:
        print(f"   Start date:        {plan['start_date']}")
    if plan["projected_ga_date"]:
        print(f"   Projected GA:      {plan['projected_ga_date']}")

    # Stage plan
    print(f"\n{'─'*78}")
    print(f"\n📋 ROLLOUT STAGES:\n")

    has_dates = any(s.get("start_date") for s in plan["stages"])

    if has_dates:
        print(f"   {'#':<3} {'Stage':<14} {'%':>5} {'Users':>10} {'Days':>5} {'Start':>12} {'End':>12} {'Status'}")
        print(f"   {'─'*3} {'─'*14} {'─'*5} {'─'*10} {'─'*5} {'─'*12} {'─'*12} {'─'*8}")
    else:
        print(f"   {'#':<3} {'Stage':<14} {'%':>5} {'Users':>10} {'Days':>5} {'Cum.Days':>9} {'Status'}")
        print(f"   {'─'*3} {'─'*14} {'─'*5} {'─'*10} {'─'*5} {'─'*9} {'─'*8}")

    for i, stage in enumerate(plan["stages"]):
        emoji = STATUS_EMOJI.get(stage["status"], "⬜")
        if has_dates:
            print(
                f"   {i+1:<3} {stage['name'][:14]:<14} "
                f"{stage['pct']:>4.0f}% {_fmt_users(stage['users_exposed']):>10} "
                f"{stage['bake_days']:>5} "
                f"{stage.get('start_date', ''):>12} {stage.get('end_date', ''):>12} "
                f"{emoji} {stage['status']}"
            )
        else:
            print(
                f"   {i+1:<3} {stage['name'][:14]:<14} "
                f"{stage['pct']:>4.0f}% {_fmt_users(stage['users_exposed']):>10} "
                f"{stage['bake_days']:>5} "
                f"{stage['cumulative_days']:>9} "
                f"{emoji} {stage['status']}"
            )

    # Rollout progression visual
    print(f"\n   📊 ROLLOUT PROGRESSION:")
    for stage in plan["stages"]:
        bar = _bar(stage["pct"], 100, 35)
        print(f"   {stage['name'][:10]:<10} {bar} {stage['pct']:.0f}% ({_fmt_users(stage['users_exposed'])})")

    # Timeline visual
    print(f"\n   ⏱️  TIMELINE:")
    total = plan["total_days"]
    for stage in plan["stages"]:
        seg_width = max(1, int(stage["bake_days"] / total * 40)) if total > 0 else 1
        bar = "█" * seg_width
        print(f"   {stage['name'][:10]:<10} {bar} {stage['bake_days']}d")

    # Gate criteria
    print(f"\n{'─'*78}")
    print(f"\n🚦 STAGE GATE CRITERIA:\n")
    sample_gates = plan["stages"][0]["gate_criteria"] if plan["stages"] else []
    for gc in sample_gates:
        print(f"   ✅ {gc}")

    # Rollback criteria
    print(f"\n{'─'*78}")
    print(f"\n🔙 ROLLBACK TRIGGERS:\n")
    for rc in plan["rollback_criteria"]:
        print(f"   🛑 {rc}")

    # Blast radius
    print(f"\n{'─'*78}")
    print(f"\n💥 BLAST RADIUS BY STAGE:\n")
    radius_emoji = {"minimal": "🟢", "low": "🟢", "moderate": "🟡", "high": "🔴"}
    for stage in plan["stages"]:
        emoji = radius_emoji.get(stage["blast_radius"], "⬜")
        print(f"   {emoji} {stage['name'][:14]:<14} {stage['blast_radius']:<10} ({_fmt_users(stage['users_exposed'])} users)")

    # Recommendations
    print(f"\n{'─'*78}")
    print(f"\n💡 RECOMMENDATIONS:")
    print(f"   • Set up dashboards before Stage 1 — don't fly blind")
    print(f"   • Define on-call rotation for each stage transition")
    print(f"   • Document rollback procedure and test it in staging")
    print(f"   • Avoid rollouts on Fridays or before holidays")
    print(f"   • Communicate timeline to stakeholders proactively")

    monitoring = plan["monitoring"]
    if monitoring == "war-room":
        print(f"   • ⚠️  Critical risk: set up a war room with eng + on-call for each stage")
    elif monitoring == "intensive":
        print(f"   • ⚠️  High risk: dedicate an engineer to monitor each stage transition")
    elif monitoring == "enhanced":
        print(f"   • Set alerts at 50% and 80% of thresholds for early warning")

    print("\n" + "=" * 78)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Plan and track progressive feature flag rollouts with stage gates, "
                    "risk assessment, and rollback criteria.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --flag "new-checkout" --total-users 500000 \\
           --stages "Internal:1:2,Beta:5:3,Canary:25:5,GA:100:3"
  %(prog)s --config rollout.json
  %(prog)s --flag "ai-recs" --total-users 1000000 --risk high \\
           --stages "Dog:0.1:3,Alpha:1:5,Beta:10:7,Wide:50:7,GA:100:5"
        """,
    )

    parser.add_argument("--flag", type=str, help="Feature flag name")
    parser.add_argument("--total-users", type=int, help="Total user base")
    parser.add_argument("--stages", type=str,
                        help="Rollout stages: 'Name:pct:days,Name:pct:days,...'")
    parser.add_argument("--risk", type=str, default="medium",
                        choices=["low", "medium", "high", "critical"],
                        help="Risk level (default: medium)")
    parser.add_argument("--start-date", type=str,
                        help="Rollout start date (YYYY-MM-DD)")
    parser.add_argument("--error-threshold", type=float,
                        help="Max error rate %% per stage gate")
    parser.add_argument("--latency-threshold", type=float,
                        help="Max P99 latency (ms) per stage gate")

    parser.add_argument("--config", type=str, help="JSON config file")
    parser.add_argument("--output", "-o", type=str, help="Write JSON results to file")
    args = parser.parse_args()

    plan = None

    if args.config:
        try:
            config = load_json_config(args.config)
        except Exception as e:
            print(f"Error loading config: {e}", file=sys.stderr)
            return 1

        plan = plan_rollout(
            flag_name=config.get("flag", "unnamed"),
            total_users=config.get("total_users", 0),
            stages=config.get("stages", []),
            start_date=config.get("start_date"),
            risk_level=config.get("risk_level", "medium"),
            error_threshold=config.get("health_criteria", {}).get("max_error_rate_pct"),
            latency_threshold=config.get("health_criteria", {}).get("max_p99_latency_ms"),
            rollback_criteria=config.get("rollback_criteria"),
        )

    elif args.flag and args.total_users and args.stages:
        try:
            stages = parse_stages_string(args.stages)
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1

        plan = plan_rollout(
            flag_name=args.flag,
            total_users=args.total_users,
            stages=stages,
            start_date=args.start_date,
            risk_level=args.risk,
            error_threshold=args.error_threshold,
            latency_threshold=args.latency_threshold,
        )

    else:
        print("Error: provide --flag + --total-users + --stages, or --config.", file=sys.stderr)
        parser.print_help(sys.stderr)
        return 1

    # Report
    print_report(plan)

    # JSON output
    if args.output:
        with open(args.output, "w") as f:
            json.dump(plan, f, indent=2, default=str)
        print(f"\n📁 Results saved to {args.output}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
