#!/usr/bin/env python3
"""
Dependency Risk Mapper

Map cross-team, cross-service, or cross-feature dependencies for a project,
score risk, identify the critical path, and flag blockers. Essential for
program-level PM work where inter-team coordination is the primary risk.

Features:
    - Dependency graph with status tracking (on-track, at-risk, blocked)
    - Critical path identification
    - Risk scoring per dependency and overall project
    - Team load analysis (who is most depended upon)
    - Timeline estimation with dependency chains

Usage:
    # Inline dependencies
    python dependency-risk-mapper.py \\
        --dep "Auth Service:Platform:on-track:2025-07-15:API contract for auth" \\
        --dep "Payment Gateway:Billing:at-risk:2025-07-20:Stripe integration" \\
        --dep "ML Model v2:Data Science:blocked:2025-08-01:Recommendation engine" \\
        --dep "Design System:Design:on-track:2025-07-10:Component library update" \\
        --dep "Payment Gateway->Auth Service" \\
        --dep "ML Model v2->Auth Service"

    Format for dependencies:
        "Name:Team:Status:Due:Description"
    Format for links (dependency chains):
        "Downstream->Upstream"  (Downstream depends on Upstream)

    # From CSV
    python dependency-risk-mapper.py --csv deps.csv

    # From JSON
    python dependency-risk-mapper.py --json deps.json

CSV format:
    name,team,status,due_date,description,depends_on
    Auth Service,Platform,on-track,2025-07-15,API contract,
    Payment Gateway,Billing,at-risk,2025-07-20,Stripe integration,Auth Service
    ML Model v2,Data Science,blocked,2025-08-01,Rec engine,Auth Service

JSON format:
    {
      "project": "Checkout Redesign",
      "dependencies": [
        {
          "name": "Auth Service",
          "team": "Platform",
          "status": "on-track",
          "due_date": "2025-07-15",
          "description": "API contract for auth",
          "depends_on": []
        },
        {
          "name": "Payment Gateway",
          "team": "Billing",
          "status": "at-risk",
          "due_date": "2025-07-20",
          "description": "Stripe integration",
          "depends_on": ["Auth Service"]
        }
      ]
    }

Requirements:
    None (stdlib only).
"""

import argparse
import csv
import json
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple


# ---------------------------------------------------------------------------
# Dependency model
# ---------------------------------------------------------------------------

VALID_STATUSES = {"on-track", "at-risk", "blocked", "complete", "not-started"}
STATUS_EMOJI = {
    "on-track": "🟢",
    "at-risk": "🟡",
    "blocked": "🔴",
    "complete": "✅",
    "not-started": "⬜",
}
STATUS_RISK = {
    "on-track": 0,
    "complete": 0,
    "not-started": 1,
    "at-risk": 2,
    "blocked": 3,
}


def build_dependency_graph(
    deps: List[Dict[str, Any]],
    links: List[Tuple[str, str]],
) -> Dict[str, Any]:
    """
    Build dependency graph.

    deps: list of dependency nodes
    links: list of (downstream, upstream) tuples — downstream depends on upstream
    """
    nodes: Dict[str, Dict[str, Any]] = {}
    for d in deps:
        name = d["name"]
        nodes[name] = {
            **d,
            "upstream": [],    # things this depends on
            "downstream": [],  # things that depend on this
        }

    # Add links from inline depends_on
    for d in deps:
        for upstream in d.get("depends_on", []):
            upstream = upstream.strip()
            if upstream and upstream in nodes:
                if upstream not in nodes[d["name"]]["upstream"]:
                    nodes[d["name"]]["upstream"].append(upstream)
                if d["name"] not in nodes[upstream]["downstream"]:
                    nodes[upstream]["downstream"].append(d["name"])

    # Add explicit links
    for downstream, upstream in links:
        if downstream in nodes and upstream in nodes:
            if upstream not in nodes[downstream]["upstream"]:
                nodes[downstream]["upstream"].append(upstream)
            if downstream not in nodes[upstream]["downstream"]:
                nodes[upstream]["downstream"].append(downstream)

    return nodes


def analyze_risks(nodes: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    """Analyze dependency risks."""
    n = len(nodes)
    if n == 0:
        return {"error": "No dependencies"}

    # Risk per node
    node_risks = []
    for name, node in nodes.items():
        base_risk = STATUS_RISK.get(node["status"], 1)

        # Amplify risk if downstream items depend on this
        fan_out = len(node["downstream"])
        amplified_risk = base_risk * (1 + fan_out * 0.3)

        # Check if any upstream is blocked/at-risk (cascade risk)
        cascade_risk = 0
        for up in node["upstream"]:
            if up in nodes:
                up_status = nodes[up]["status"]
                if up_status == "blocked":
                    cascade_risk = max(cascade_risk, 3)
                elif up_status == "at-risk":
                    cascade_risk = max(cascade_risk, 1.5)

        total_risk = amplified_risk + cascade_risk

        node_risks.append({
            "name": name,
            "status": node["status"],
            "base_risk": base_risk,
            "fan_out": fan_out,
            "cascade_risk": round(cascade_risk, 1),
            "total_risk": round(total_risk, 1),
        })

    node_risks.sort(key=lambda x: -x["total_risk"])

    # Overall project risk
    statuses = [n["status"] for n in nodes.values()]
    blocked = sum(1 for s in statuses if s == "blocked")
    at_risk = sum(1 for s in statuses if s == "at-risk")
    on_track = sum(1 for s in statuses if s == "on-track")
    complete = sum(1 for s in statuses if s == "complete")
    not_started = sum(1 for s in statuses if s == "not-started")

    risk_score = (blocked * 30 + at_risk * 15 + not_started * 5) / max(n, 1)
    risk_score = min(100, risk_score)

    if risk_score <= 10:
        risk_grade = "🟢 Low risk"
    elif risk_score <= 30:
        risk_grade = "🟡 Moderate risk"
    elif risk_score <= 60:
        risk_grade = "🟠 Elevated risk"
    else:
        risk_grade = "🔴 High risk"

    # Team load
    team_load: Dict[str, Dict[str, int]] = {}
    for name, node in nodes.items():
        team = node.get("team", "Unassigned")
        if team not in team_load:
            team_load[team] = {"owns": 0, "depended_on": 0, "blocked": 0, "at_risk": 0}
        team_load[team]["owns"] += 1
        team_load[team]["depended_on"] += len(node["downstream"])
        if node["status"] == "blocked":
            team_load[team]["blocked"] += 1
        elif node["status"] == "at-risk":
            team_load[team]["at_risk"] += 1

    # Critical path (longest chain through blocked/at-risk)
    critical_path = _find_critical_path(nodes)

    return {
        "total_deps": n,
        "blocked": blocked,
        "at_risk": at_risk,
        "on_track": on_track,
        "complete": complete,
        "not_started": not_started,
        "risk_score": round(risk_score, 1),
        "risk_grade": risk_grade,
        "node_risks": node_risks,
        "team_load": team_load,
        "critical_path": critical_path,
    }


def _find_critical_path(nodes: Dict[str, Dict[str, Any]]) -> List[str]:
    """Find the longest dependency chain (simplified critical path)."""
    memo: Dict[str, List[str]] = {}

    def _longest(name: str, visited: Set[str]) -> List[str]:
        if name in memo:
            return memo[name]
        if name in visited:
            return [name]

        visited.add(name)
        node = nodes.get(name)
        if not node or not node["downstream"]:
            memo[name] = [name]
            return [name]

        best = []
        for down in node["downstream"]:
            if down in nodes:
                path = _longest(down, visited)
                if len(path) > len(best):
                    best = path

        result = [name] + best
        memo[name] = result
        visited.discard(name)
        return result

    # Find roots (no upstream dependencies)
    roots = [name for name, node in nodes.items() if not node["upstream"]]
    if not roots:
        roots = list(nodes.keys())

    longest = []
    for root in roots:
        path = _longest(root, set())
        if len(path) > len(longest):
            longest = path

    return longest


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def parse_dep_string(s: str) -> Optional[Dict[str, Any]]:
    """Parse 'Name:Team:Status:Due:Description' or 'Down->Up' link."""
    if "->" in s:
        return None  # link, not a dep node
    parts = s.split(":")
    if len(parts) < 2:
        raise ValueError(f"Invalid dependency '{s}'. Format: Name:Team[:Status:Due:Description]")

    return {
        "name": parts[0].strip(),
        "team": parts[1].strip() if len(parts) > 1 else "",
        "status": parts[2].strip().lower() if len(parts) > 2 else "not-started",
        "due_date": parts[3].strip() if len(parts) > 3 else "",
        "description": parts[4].strip() if len(parts) > 4 else "",
        "depends_on": [],
    }


def parse_link_string(s: str) -> Optional[Tuple[str, str]]:
    """Parse 'Downstream->Upstream'."""
    if "->" not in s:
        return None
    parts = s.split("->")
    if len(parts) != 2:
        return None
    return (parts[0].strip(), parts[1].strip())


def _col(fieldnames: List[str], *aliases: str) -> Optional[str]:
    lower_map = {f.lower().strip(): f for f in fieldnames}
    for alias in aliases:
        if alias.lower().strip() in lower_map:
            return lower_map[alias.lower().strip()]
    return None


def load_csv(path: str) -> Tuple[List[Dict[str, Any]], List[Tuple[str, str]]]:
    """Load dependencies from CSV."""
    deps: List[Dict[str, Any]] = []
    links: List[Tuple[str, str]] = []

    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fields = reader.fieldnames or []

        c_name = _col(fields, "name", "dependency", "component", "service")
        c_team = _col(fields, "team", "owner", "group")
        c_status = _col(fields, "status", "state")
        c_due = _col(fields, "due_date", "due", "deadline", "eta")
        c_desc = _col(fields, "description", "desc", "notes")
        c_depends = _col(fields, "depends_on", "upstream", "blocked_by", "requires")

        for row in reader:
            name = row.get(c_name or "name", "").strip()
            if not name:
                continue

            depends_on = []
            dep_raw = row.get(c_depends or "depends_on", "").strip()
            if dep_raw:
                depends_on = [d.strip() for d in dep_raw.split(";") if d.strip()]

            deps.append({
                "name": name,
                "team": row.get(c_team or "team", "").strip(),
                "status": row.get(c_status or "status", "not-started").strip().lower(),
                "due_date": row.get(c_due or "due_date", "").strip(),
                "description": row.get(c_desc or "description", "").strip(),
                "depends_on": depends_on,
            })

    return deps, links


def load_json(path: str) -> Tuple[List[Dict[str, Any]], List[Tuple[str, str]], str]:
    """Load dependencies from JSON."""
    with open(path, encoding="utf-8") as f:
        config = json.load(f)

    project = config.get("project", "")
    deps = []
    links = []

    for d in config.get("dependencies", []):
        deps.append({
            "name": d.get("name", ""),
            "team": d.get("team", ""),
            "status": d.get("status", "not-started").lower(),
            "due_date": d.get("due_date", ""),
            "description": d.get("description", ""),
            "depends_on": d.get("depends_on", []),
        })

    for link in config.get("links", []):
        if isinstance(link, dict):
            links.append((link.get("from", ""), link.get("to", "")))
        elif isinstance(link, str) and "->" in link:
            parsed = parse_link_string(link)
            if parsed:
                links.append(parsed)

    return deps, links, project


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def _bar(value: float, max_val: float, width: int = 20) -> str:
    if max_val <= 0:
        return "░" * width
    ratio = min(1.0, max(0.0, value / max_val))
    filled = int(ratio * width)
    return "█" * filled + "░" * (width - filled)


def print_report(
    nodes: Dict[str, Dict[str, Any]],
    analysis: Dict[str, Any],
    project: str = "",
) -> None:
    """Pretty-print dependency risk map."""
    print("\n" + "=" * 78)
    print("🗺️  DEPENDENCY RISK MAPPER")
    print("=" * 78)

    if project:
        print(f"\n   Project: {project}")

    # Overview
    print(f"\n   📊 OVERVIEW:")
    print(f"   Total dependencies: {analysis['total_deps']}")
    print(f"   Risk score:         {analysis['risk_score']:.0f}/100  {analysis['risk_grade']}")
    print(f"\n   Status breakdown:")
    print(f"   ✅ Complete:      {analysis['complete']}")
    print(f"   🟢 On track:      {analysis['on_track']}")
    print(f"   🟡 At risk:       {analysis['at_risk']}")
    print(f"   🔴 Blocked:       {analysis['blocked']}")
    print(f"   ⬜ Not started:   {analysis['not_started']}")

    # Dependency list
    print(f"\n{'─'*78}")
    print(f"\n📋 DEPENDENCY MAP:\n")

    print(f"   {'Dependency':<22} {'Team':<14} {'Status':<12} {'Due':>12} {'Fan-out':>8}")
    print(f"   {'─'*22} {'─'*14} {'─'*12} {'─'*12} {'─'*8}")

    for name in sorted(nodes.keys()):
        node = nodes[name]
        emoji = STATUS_EMOJI.get(node["status"], "⬜")
        due = node.get("due_date", "—") or "—"
        fan = len(node["downstream"])
        print(
            f"   {name[:22]:<22} "
            f"{node.get('team', '')[:14]:<14} "
            f"{emoji} {node['status']:<9} "
            f"{due:>12} "
            f"{fan:>8}"
        )

    # Dependency chains
    print(f"\n   🔗 DEPENDENCY CHAINS:")
    for name, node in nodes.items():
        if node["upstream"]:
            for up in node["upstream"]:
                up_emoji = STATUS_EMOJI.get(nodes[up]["status"], "⬜") if up in nodes else "⬜"
                my_emoji = STATUS_EMOJI.get(node["status"], "⬜")
                print(f"   {my_emoji} {name} ← depends on ← {up_emoji} {up}")

    # Critical path
    if analysis["critical_path"]:
        print(f"\n{'─'*78}")
        print(f"\n🛤️  CRITICAL PATH ({len(analysis['critical_path'])} items):\n")
        path = analysis["critical_path"]
        for i, name in enumerate(path):
            node = nodes.get(name, {})
            emoji = STATUS_EMOJI.get(node.get("status", ""), "⬜")
            connector = "   →  " if i > 0 else "      "
            due = node.get("due_date", "") or ""
            due_str = f"  (due: {due})" if due else ""
            print(f"   {connector}{emoji} {name}{due_str}")

    # Risk ranking
    print(f"\n{'─'*78}")
    print(f"\n⚠️  RISK RANKING:\n")
    max_risk = analysis["node_risks"][0]["total_risk"] if analysis["node_risks"] else 1
    print(f"   {'Dependency':<22} {'Base':>5} {'Fan':>4} {'Cascade':>8} {'Total':>6}")
    print(f"   {'─'*22} {'─'*5} {'─'*4} {'─'*8} {'─'*6}")

    for nr in analysis["node_risks"]:
        bar = _bar(nr["total_risk"], max_risk, 15)
        print(
            f"   {nr['name'][:22]:<22} "
            f"{nr['base_risk']:>5} "
            f"{nr['fan_out']:>4} "
            f"{nr['cascade_risk']:>8.1f} "
            f"{nr['total_risk']:>6.1f}  {bar}"
        )

    # Team load
    print(f"\n{'─'*78}")
    print(f"\n👥 TEAM LOAD:\n")
    print(f"   {'Team':<16} {'Owns':>5} {'Depended On':>12} {'Blocked':>8} {'At Risk':>8}")
    print(f"   {'─'*16} {'─'*5} {'─'*12} {'─'*8} {'─'*8}")

    for team, load in sorted(analysis["team_load"].items(), key=lambda x: -x[1]["depended_on"]):
        flag = " ⚠️" if load["blocked"] > 0 else ""
        print(
            f"   {team[:16]:<16} "
            f"{load['owns']:>5} "
            f"{load['depended_on']:>12} "
            f"{load['blocked']:>8} "
            f"{load['at_risk']:>8}{flag}"
        )

    # Action items
    blocked_nodes = [n for n in nodes.values() if n["status"] == "blocked"]
    at_risk_nodes = [n for n in nodes.values() if n["status"] == "at-risk"]

    if blocked_nodes or at_risk_nodes:
        print(f"\n{'─'*78}")
        print(f"\n⚡ ACTION ITEMS:\n")
        for node in blocked_nodes:
            downstream_count = len(node["downstream"])
            impact = f" (blocking {downstream_count} downstream)" if downstream_count > 0 else ""
            print(f"   🔴 UNBLOCK: '{node['name']}' ({node.get('team', '?')}){impact}")
            if node.get("description"):
                print(f"      → {node['description']}")
        for node in at_risk_nodes:
            print(f"   🟡 MONITOR: '{node['name']}' ({node.get('team', '?')})")
            if node.get("due_date"):
                print(f"      → Due: {node['due_date']}")

    # Guidance
    print(f"\n{'─'*78}")
    print(f"\n💡 DEPENDENCY MANAGEMENT TIPS:")
    print(f"   • Unblock red items first — they cascade to downstream deps")
    print(f"   • Teams with high 'depended on' count are single points of failure")
    print(f"   • Review critical path weekly — it determines your ship date")
    print(f"   • Consider parallel workstreams to reduce critical path length")
    print(f"   • Establish API contracts early to decouple teams")
    print("\n" + "=" * 78)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Map cross-team dependencies, score risk, and identify the critical path.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --dep "Auth:Platform:on-track:2025-07-15:API" \\
           --dep "Payments:Billing:blocked:2025-07-20:Stripe" \\
           --dep "Payments->Auth"
  %(prog)s --csv deps.csv
  %(prog)s --json deps.json
        """,
    )

    parser.add_argument("--dep", type=str, action="append",
                        help="Dependency: 'Name:Team:Status:Due:Desc' or link: 'Down->Up'")
    parser.add_argument("--project", type=str, default="", help="Project name")
    parser.add_argument("--csv", "-c", type=str, help="CSV file with dependencies")
    parser.add_argument("--json", "-j", type=str, help="JSON file with dependencies")
    parser.add_argument("--output", "-o", type=str, help="Write JSON results to file")
    args = parser.parse_args()

    deps: List[Dict[str, Any]] = []
    links: List[Tuple[str, str]] = []
    project = args.project

    if args.json:
        try:
            deps, links, proj = load_json(args.json)
            if proj and not project:
                project = proj
        except Exception as e:
            print(f"Error loading JSON: {e}", file=sys.stderr)
            return 1

    elif args.csv:
        try:
            deps, links = load_csv(args.csv)
        except Exception as e:
            print(f"Error loading CSV: {e}", file=sys.stderr)
            return 1

    elif args.dep:
        for d_str in args.dep:
            link = parse_link_string(d_str)
            if link:
                links.append(link)
            else:
                try:
                    dep = parse_dep_string(d_str)
                    if dep:
                        deps.append(dep)
                except ValueError as e:
                    print(f"Error: {e}", file=sys.stderr)
                    return 1

    else:
        print("Error: provide dependencies via --dep, --csv, or --json.", file=sys.stderr)
        parser.print_help(sys.stderr)
        return 1

    if not deps:
        print("Error: no dependency nodes found.", file=sys.stderr)
        return 1

    # Build graph
    nodes = build_dependency_graph(deps, links)

    # Analyze
    analysis = analyze_risks(nodes)

    # Report
    print_report(nodes, analysis, project)

    # JSON output
    if args.output:
        serializable_nodes = {}
        for name, node in nodes.items():
            serializable_nodes[name] = {
                k: v for k, v in node.items()
            }
        report = {
            "project": project,
            "nodes": serializable_nodes,
            "analysis": analysis,
        }
        with open(args.output, "w") as f:
            json.dump(report, f, indent=2, default=str)
        print(f"\n📁 Results saved to {args.output}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
