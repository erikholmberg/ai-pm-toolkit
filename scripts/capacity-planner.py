#!/usr/bin/env python3
"""
Capacity / Headcount Planner

Given a roadmap of initiatives with estimated effort, team size, and velocity,
model whether you can deliver on time or need to cut scope or add headcount.
Helps PMs make data-driven staffing and prioritization decisions.

Supports:
    - Initiative-level effort estimation
    - Team capacity modeling with availability factors
    - Overcommitment detection and gap analysis
    - Scenario comparison (cut scope vs. add headcount vs. slip timeline)
    - Quarter/sprint-level capacity breakdown

Usage:
    # Quick capacity check
    python capacity-planner.py \\
        --team-size 6 --velocity 40 --sprints 6 \\
        --initiative "Checkout redesign:120" \\
        --initiative "AI recommendations:80" \\
        --initiative "Mobile app:60" \\
        --initiative "Tech debt:40"

    Format: "Name:story_points"

    # With availability factor
    python capacity-planner.py \\
        --team-size 8 --velocity 45 --sprints 6 \\
        --availability 80 \\
        --initiative "Feature A:100:P0" \\
        --initiative "Feature B:80:P1" \\
        --initiative "Feature C:60:P1" \\
        --initiative "Feature D:40:P2"

    Format: "Name:points[:priority]"

    # From CSV
    python capacity-planner.py --team-size 8 --velocity 45 --sprints 6 --csv roadmap.csv

    # Scenario analysis: what if we add 2 engineers?
    python capacity-planner.py \\
        --team-size 6 --velocity 40 --sprints 6 \\
        --csv roadmap.csv \\
        --scenario-add-headcount 2 --scenario-cut-lowest

CSV format:
    initiative,points,priority,owner
    Checkout redesign,120,P0,Product
    AI recommendations,80,P1,ML Team
    Mobile app,60,P1,Mobile
    Tech debt,40,P2,Platform

    Required: initiative, points
    Optional: priority, owner

Requirements:
    None (stdlib only).
"""

import argparse
import csv
import json
import math
import sys
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Capacity modeling
# ---------------------------------------------------------------------------

def model_capacity(
    team_size: int,
    velocity_per_sprint: float,
    n_sprints: int,
    availability_pct: float = 100.0,
    initiatives: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Model team capacity against planned work."""
    effective_velocity = velocity_per_sprint * availability_pct / 100
    total_capacity = effective_velocity * n_sprints

    # Sort initiatives by priority
    priority_order = {"P0": 0, "P1": 1, "P2": 2, "P3": 3, "P4": 4}
    inits = sorted(initiatives or [], key=lambda x: priority_order.get(x.get("priority", "P2"), 9))

    total_demand = sum(i["points"] for i in inits)
    gap = total_demand - total_capacity
    utilization = total_demand / total_capacity * 100 if total_capacity > 0 else 0

    # Determine what fits
    cumulative = 0
    committed = []
    stretch = []
    cut = []

    for init in inits:
        cumulative += init["points"]
        init_result = {
            **init,
            "cumulative": cumulative,
            "fits": cumulative <= total_capacity,
        }
        if cumulative <= total_capacity:
            committed.append(init_result)
        elif cumulative <= total_capacity * 1.1:
            stretch.append(init_result)
        else:
            cut.append(init_result)

    # Sprint-level breakdown
    sprint_plan = []
    remaining_work = list(committed + stretch)
    for sprint_num in range(1, n_sprints + 1):
        sprint_capacity = effective_velocity
        sprint_items = []
        allocated = 0

        while remaining_work and allocated < sprint_capacity:
            item = remaining_work[0]
            can_do = min(item["points"], sprint_capacity - allocated)
            if can_do <= 0:
                break
            sprint_items.append({
                "name": item["name"],
                "points_this_sprint": round(can_do, 1),
                "is_partial": can_do < item["points"],
            })
            allocated += can_do
            item["points"] -= can_do
            if item["points"] <= 0:
                remaining_work.pop(0)

        sprint_plan.append({
            "sprint": sprint_num,
            "capacity": round(sprint_capacity, 1),
            "allocated": round(allocated, 1),
            "utilization_pct": round(allocated / sprint_capacity * 100, 1) if sprint_capacity > 0 else 0,
            "items": sprint_items,
        })

    # Health assessment
    if utilization <= 80:
        health = "🟢 Comfortable — room for unplanned work"
    elif utilization <= 100:
        health = "🟡 Tight — limited buffer for surprises"
    elif utilization <= 120:
        health = "🟠 Overcommitted — need to cut scope or add capacity"
    else:
        health = "🔴 Severely overcommitted — major re-planning needed"

    return {
        "team_size": team_size,
        "velocity_per_sprint": velocity_per_sprint,
        "effective_velocity": round(effective_velocity, 1),
        "availability_pct": availability_pct,
        "n_sprints": n_sprints,
        "total_capacity": round(total_capacity, 1),
        "total_demand": total_demand,
        "gap": round(gap, 1),
        "utilization_pct": round(utilization, 1),
        "health": health,
        "committed": committed,
        "stretch": stretch,
        "cut": cut,
        "sprint_plan": sprint_plan,
        "n_initiatives": len(inits),
        "n_committed": len(committed),
        "n_stretch": len(stretch),
        "n_cut": len(cut),
    }


def scenario_add_headcount(
    base: Dict[str, Any],
    additional: int,
    per_person_velocity: Optional[float] = None,
) -> Dict[str, Any]:
    """Model what happens if we add N engineers."""
    if per_person_velocity is None:
        per_person_velocity = base["velocity_per_sprint"] / base["team_size"]

    new_team = base["team_size"] + additional
    new_velocity = base["velocity_per_sprint"] + per_person_velocity * additional

    all_inits = []
    for group in [base["committed"], base["stretch"], base["cut"]]:
        for item in group:
            all_inits.append({
                "name": item["name"],
                "points": item.get("original_points", item["points"]),
                "priority": item.get("priority", "P2"),
            })

    return model_capacity(
        team_size=new_team,
        velocity_per_sprint=new_velocity,
        n_sprints=base["n_sprints"],
        availability_pct=base["availability_pct"],
        initiatives=all_inits,
    )


def scenario_cut_lowest(base: Dict[str, Any]) -> Dict[str, Any]:
    """Model what happens if we cut lowest-priority items that don't fit."""
    all_inits = []
    for item in base["committed"]:
        all_inits.append({
            "name": item["name"],
            "points": item.get("original_points", item["points"]),
            "priority": item.get("priority", "P2"),
        })
    for item in base["stretch"]:
        all_inits.append({
            "name": item["name"],
            "points": item.get("original_points", item["points"]),
            "priority": item.get("priority", "P2"),
        })

    return model_capacity(
        team_size=base["team_size"],
        velocity_per_sprint=base["velocity_per_sprint"],
        n_sprints=base["n_sprints"],
        availability_pct=base["availability_pct"],
        initiatives=all_inits,
    )


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def parse_initiative_string(s: str) -> Dict[str, Any]:
    """Parse 'Name:points[:priority]'."""
    parts = s.rsplit(":", 2)
    if len(parts) < 2:
        raise ValueError(f"Invalid initiative '{s}'. Format: Name:points[:priority]")

    name = parts[0].strip()
    try:
        points = float(parts[1].strip())
    except ValueError:
        raise ValueError(f"Invalid points in '{s}'")

    priority = parts[2].strip().upper() if len(parts) > 2 else "P1"
    return {"name": name, "points": points, "original_points": points, "priority": priority}


def _col(fieldnames: List[str], *aliases: str) -> Optional[str]:
    lower_map = {f.lower().strip(): f for f in fieldnames}
    for alias in aliases:
        if alias.lower().strip() in lower_map:
            return lower_map[alias.lower().strip()]
    return None


def load_csv(path: str) -> List[Dict[str, Any]]:
    """Load roadmap from CSV."""
    initiatives: List[Dict[str, Any]] = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fields = reader.fieldnames or []

        c_name = _col(fields, "initiative", "name", "feature", "project", "item")
        c_points = _col(fields, "points", "story_points", "effort", "estimate", "size")
        c_priority = _col(fields, "priority", "pri", "importance")
        c_owner = _col(fields, "owner", "team", "assignee")

        for row in reader:
            name = row.get(c_name or "initiative", "").strip()
            if not name:
                continue

            raw_points = row.get(c_points or "points", "0").strip().replace(",", "")
            try:
                points = float(raw_points)
            except ValueError:
                continue

            priority = row.get(c_priority or "priority", "P1").strip().upper()
            owner = row.get(c_owner or "owner", "").strip()

            initiatives.append({
                "name": name,
                "points": points,
                "original_points": points,
                "priority": priority,
                "owner": owner,
            })

    return initiatives


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def _bar(value: float, max_val: float, width: int = 25) -> str:
    if max_val <= 0:
        return "░" * width
    ratio = min(1.0, max(0.0, value / max_val))
    filled = int(ratio * width)
    return "█" * filled + "░" * (width - filled)


def _fmt_pts(n: float) -> str:
    if n == int(n):
        return f"{int(n)}"
    return f"{n:.1f}"


def print_report(
    result: Dict[str, Any],
    scenario_hc: Optional[Dict[str, Any]] = None,
    scenario_cut: Optional[Dict[str, Any]] = None,
    add_headcount: int = 0,
) -> None:
    """Pretty-print capacity plan."""
    print("\n" + "=" * 78)
    print("📊 CAPACITY / HEADCOUNT PLANNER")
    print("=" * 78)

    # Team overview
    print(f"\n   👥 TEAM:")
    print(f"   Team size:          {result['team_size']} engineers")
    print(f"   Velocity/sprint:    {_fmt_pts(result['velocity_per_sprint'])} points")
    if result["availability_pct"] < 100:
        print(f"   Availability:       {result['availability_pct']:.0f}%")
        print(f"   Effective velocity: {_fmt_pts(result['effective_velocity'])} points/sprint")
    print(f"   Sprints:            {result['n_sprints']}")

    # Capacity overview
    print(f"\n   📦 CAPACITY vs DEMAND:")
    capacity = result["total_capacity"]
    demand = result["total_demand"]
    print(f"   Total capacity:     {_fmt_pts(capacity)} points")
    print(f"   Total demand:       {_fmt_pts(demand)} points")

    if result["gap"] > 0:
        print(f"   Gap:                {_fmt_pts(result['gap'])} points OVER capacity")
    elif result["gap"] < 0:
        print(f"   Buffer:             {_fmt_pts(abs(result['gap']))} points remaining")
    else:
        print(f"   Gap:                Exact fit (no buffer)")

    bar_width = 35
    cap_bar = _bar(demand, max(capacity, demand), bar_width)
    print(f"\n   Utilization: {cap_bar} {result['utilization_pct']:.0f}%")
    print(f"   {result['health']}")

    # Initiative breakdown
    print(f"\n{'─'*78}")
    print(f"\n📋 INITIATIVE BREAKDOWN:\n")
    print(f"   {'#':<3} {'Initiative':<26} {'Points':>7} {'Pri':>4} {'Cum.':>7} {'Status'}")
    print(f"   {'─'*3} {'─'*26} {'─'*7} {'─'*4} {'─'*7} {'─'*12}")

    all_items = result["committed"] + result["stretch"] + result["cut"]
    for i, item in enumerate(all_items):
        if item in result["committed"]:
            status = "✅ Committed"
        elif item in result["stretch"]:
            status = "🟡 Stretch"
        else:
            status = "🔴 Cut"

        cum = item.get("cumulative", 0)
        print(
            f"   {i+1:<3} {item['name'][:26]:<26} "
            f"{_fmt_pts(item.get('original_points', item['points'])):>7} "
            f"{item.get('priority', ''):>4} "
            f"{_fmt_pts(cum):>7} "
            f"{status}"
        )

    # Capacity line
    print(f"   {'':>3} {'─'*26} {'─'*7} {'─'*4} {'─'*7}")
    print(f"   {'':>3} {'Capacity line':>26} {'':>7} {'':>4} {_fmt_pts(capacity):>7}")

    print(f"\n   Summary: {result['n_committed']} committed, {result['n_stretch']} stretch, {result['n_cut']} cut")

    # Visual capacity allocation
    print(f"\n   📊 DEMAND BREAKDOWN:")
    max_pts = max((item.get("original_points", item["points"]) for item in all_items), default=1)
    for item in all_items:
        pts = item.get("original_points", item["points"])
        bar = _bar(pts, max_pts, 20)
        fits = "✅" if item.get("fits", False) else "🔴"
        print(f"   {fits} {item['name'][:18]:<18} {bar} {_fmt_pts(pts)} pts")

    # Sprint plan
    if result["sprint_plan"]:
        print(f"\n{'─'*78}")
        print(f"\n📅 SPRINT-LEVEL PLAN:\n")

        for sp in result["sprint_plan"]:
            bar = _bar(sp["allocated"], sp["capacity"], 20)
            print(f"   Sprint {sp['sprint']:<3} {bar} {_fmt_pts(sp['allocated'])}/{_fmt_pts(sp['capacity'])} ({sp['utilization_pct']:.0f}%)")
            for item in sp["items"]:
                partial = " (partial)" if item["is_partial"] else ""
                print(f"            └─ {item['name'][:30]} ({_fmt_pts(item['points_this_sprint'])} pts{partial})")

    # Scenarios
    if scenario_hc or scenario_cut:
        print(f"\n{'─'*78}")
        print(f"\n🔮 SCENARIO ANALYSIS:\n")

        print(f"   {'Scenario':<30} {'Capacity':>10} {'Demand':>10} {'Util':>7} {'Fits'}")
        print(f"   {'─'*30} {'─'*10} {'─'*10} {'─'*7} {'─'*5}")

        print(
            f"   {'Current plan':<30} "
            f"{_fmt_pts(result['total_capacity']):>10} "
            f"{_fmt_pts(result['total_demand']):>10} "
            f"{result['utilization_pct']:>6.0f}% "
            f"{'🟢' if result['utilization_pct'] <= 100 else '🔴'}"
        )

        if scenario_hc:
            print(
                f"   {f'Add {add_headcount} engineer(s)':<30} "
                f"{_fmt_pts(scenario_hc['total_capacity']):>10} "
                f"{_fmt_pts(scenario_hc['total_demand']):>10} "
                f"{scenario_hc['utilization_pct']:>6.0f}% "
                f"{'🟢' if scenario_hc['utilization_pct'] <= 100 else '🔴'}"
            )

        if scenario_cut:
            print(
                f"   {'Cut lowest priority':<30} "
                f"{_fmt_pts(scenario_cut['total_capacity']):>10} "
                f"{_fmt_pts(scenario_cut['total_demand']):>10} "
                f"{scenario_cut['utilization_pct']:>6.0f}% "
                f"{'🟢' if scenario_cut['utilization_pct'] <= 100 else '🔴'}"
            )

    # Guidance
    print(f"\n{'─'*78}")
    print(f"\n💡 CAPACITY PLANNING TIPS:")
    print(f"   • Target 70-80% utilization — leave room for bugs and unplanned work")
    print(f"   • Velocity is a range, not a promise — plan for the pessimistic end")
    print(f"   • New hires take 2-3 sprints to reach full velocity")
    print(f"   • Cut scope before adding headcount — it's faster and cheaper")
    print(f"   • Re-estimate mid-quarter as you learn more about complexity")
    print("\n" + "=" * 78)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Model team capacity against planned initiatives. Detect overcommitment "
                    "and evaluate scope cuts vs. headcount increases.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --team-size 6 --velocity 40 --sprints 6 \\
           --initiative "Checkout:120:P0" --initiative "AI:80:P1" --initiative "Mobile:60:P1"
  %(prog)s --team-size 8 --velocity 45 --sprints 6 --csv roadmap.csv
  %(prog)s --team-size 6 --velocity 40 --sprints 6 --csv roadmap.csv --scenario-add-headcount 2
        """,
    )

    parser.add_argument("--team-size", type=int, required=True, help="Number of engineers")
    parser.add_argument("--velocity", type=float, required=True, help="Points per sprint")
    parser.add_argument("--sprints", type=int, required=True, help="Number of sprints in period")
    parser.add_argument("--availability", type=float, default=100,
                        help="Availability %% (default: 100 — adjust for PTO, meetings, etc.)")

    parser.add_argument("--initiative", type=str, action="append",
                        help="Initiative: 'Name:points[:priority]'")
    parser.add_argument("--csv", "-c", type=str, help="CSV file with roadmap")

    # Scenarios
    parser.add_argument("--scenario-add-headcount", type=int, default=0,
                        help="Model adding N engineers")
    parser.add_argument("--scenario-cut-lowest", action="store_true",
                        help="Model cutting lowest-priority items that don't fit")

    parser.add_argument("--output", "-o", type=str, help="Write JSON results to file")
    args = parser.parse_args()

    initiatives: List[Dict[str, Any]] = []

    if args.csv:
        try:
            initiatives = load_csv(args.csv)
        except Exception as e:
            print(f"Error loading CSV: {e}", file=sys.stderr)
            return 1

    if args.initiative:
        for i_str in args.initiative:
            try:
                initiatives.append(parse_initiative_string(i_str))
            except ValueError as e:
                print(f"Error: {e}", file=sys.stderr)
                return 1

    if not initiatives:
        print("Error: provide initiatives via --initiative or --csv.", file=sys.stderr)
        parser.print_help(sys.stderr)
        return 1

    # Base capacity model
    result = model_capacity(
        team_size=args.team_size,
        velocity_per_sprint=args.velocity,
        n_sprints=args.sprints,
        availability_pct=args.availability,
        initiatives=initiatives,
    )

    # Scenarios
    scenario_hc = None
    scenario_cut_result = None

    if args.scenario_add_headcount > 0:
        scenario_hc = scenario_add_headcount(result, args.scenario_add_headcount)

    if args.scenario_cut_lowest:
        scenario_cut_result = scenario_cut_lowest(result)

    # Report
    print_report(result, scenario_hc, scenario_cut_result, args.scenario_add_headcount)

    # JSON output
    if args.output:
        report = {"base": result}
        if scenario_hc:
            report["scenario_add_headcount"] = scenario_hc
        if scenario_cut_result:
            report["scenario_cut_scope"] = scenario_cut_result
        with open(args.output, "w") as f:
            json.dump(report, f, indent=2)
        print(f"\n📁 Results saved to {args.output}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
