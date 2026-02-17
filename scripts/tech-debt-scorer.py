#!/usr/bin/env python3
"""
Tech Debt Scorer

Score, rank, and prioritize technical debt items by business impact, engineering
cost, and risk. Helps PMs make data-driven decisions about when to pay down
tech debt versus shipping features.

Each item is scored on three dimensions (1-5 scale):
    - Business Impact:  how much the debt hurts users, revenue, or velocity
    - Engineering Cost:  effort to fix (1=trivial, 5=multi-sprint epic)
    - Risk / Urgency:    likelihood of causing an incident or blocking work

A composite priority score is computed:
    priority = (impact × impact_weight + risk × risk_weight) / cost

Higher priority = fix first (high value, low cost).

Usage:
    # From CSV
    python tech-debt-scorer.py --csv debt.csv

    # Inline items
    python tech-debt-scorer.py \\
        --item "Monolith DB queries:4:3:3" \\
        --item "Legacy auth system:5:4:5" \\
        --item "Flaky CI pipeline:3:2:4" \\
        --item "No rate limiting:4:2:5"

    # Custom weights
    python tech-debt-scorer.py --csv debt.csv --impact-weight 2 --risk-weight 3

    # Format: --item "Title:impact:cost:risk"

CSV format:
    title,category,impact,cost,risk,owner,notes
    Monolith DB queries,Performance,4,3,3,backend,Slows dashboard by 2s
    Legacy auth system,Security,5,4,5,platform,No MFA support
    Flaky CI pipeline,DevEx,3,2,4,infra,3-4 failures/week
    No rate limiting,Security,4,2,5,backend,API abuse risk
    Hardcoded configs,Maintainability,2,1,2,backend,Blocks multi-region
    Manual deploys,DevEx,3,3,3,devops,No CD pipeline
    ...

    Required: title, impact, cost, risk
    Optional: category, owner, notes, ticket

Requirements:
    None (stdlib only).
"""

import argparse
import csv
import json
import math
import sys
from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------

def compute_priority(
    impact: float,
    cost: float,
    risk: float,
    impact_weight: float = 2.0,
    risk_weight: float = 1.5,
) -> float:
    """
    Priority = (impact × w_impact + risk × w_risk) / cost.
    Higher = fix sooner.
    """
    if cost <= 0:
        cost = 1
    numerator = impact * impact_weight + risk * risk_weight
    return round(numerator / cost, 2)


def classify_priority(score: float) -> Tuple[str, str]:
    """Classify a priority score into a tier."""
    if score >= 5.0:
        return "Critical", "🔴"
    elif score >= 3.5:
        return "High", "🟠"
    elif score >= 2.0:
        return "Medium", "🟡"
    else:
        return "Low", "🟢"


def classify_cost(cost: int) -> str:
    """Human-readable cost label."""
    labels = {1: "Trivial (<1d)", 2: "Small (1-3d)", 3: "Medium (1-2w)", 4: "Large (sprint)", 5: "XL (multi-sprint)"}
    return labels.get(cost, f"Level {cost}")


def effort_bucket(items: List[Dict]) -> Dict[str, List[Dict]]:
    """Group items into effort buckets for sprint planning."""
    buckets = {"Quick wins (≤2d)": [], "Sprint-sized (1-2w)": [], "Epics (>2w)": []}
    for item in items:
        if item["cost"] <= 2:
            buckets["Quick wins (≤2d)"].append(item)
        elif item["cost"] <= 3:
            buckets["Sprint-sized (1-2w)"].append(item)
        else:
            buckets["Epics (>2w)"].append(item)
    return buckets


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def _col(fieldnames: List[str], *aliases: str) -> Optional[str]:
    lower_map = {f.lower().strip(): f for f in fieldnames}
    for alias in aliases:
        if alias.lower().strip() in lower_map:
            return lower_map[alias.lower().strip()]
    return None


def _int_val(row: Dict, col: Optional[str], default: int = 0) -> int:
    if not col:
        return default
    raw = row.get(col, "")
    if not raw or not str(raw).strip():
        return default
    try:
        return max(1, min(5, int(float(str(raw).strip()))))
    except ValueError:
        return default


def load_csv(path: str) -> List[Dict[str, Any]]:
    """Load tech debt items from CSV."""
    items: List[Dict[str, Any]] = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fields = reader.fieldnames or []

        c_title = _col(fields, "title", "name", "summary", "item", "description", "debt")
        c_category = _col(fields, "category", "type", "area", "domain", "pillar")
        c_impact = _col(fields, "impact", "business_impact", "severity")
        c_cost = _col(fields, "cost", "effort", "engineering_cost", "size")
        c_risk = _col(fields, "risk", "urgency", "risk_urgency", "probability")
        c_owner = _col(fields, "owner", "team", "assignee", "responsible")
        c_notes = _col(fields, "notes", "details", "context", "description")
        c_ticket = _col(fields, "ticket", "jira", "issue", "id", "key")

        for row in reader:
            title = row.get(c_title or "title", "").strip()
            if not title:
                continue

            items.append({
                "title": title,
                "category": row.get(c_category or "", "").strip() or "General",
                "impact": _int_val(row, c_impact, 3),
                "cost": _int_val(row, c_cost, 3),
                "risk": _int_val(row, c_risk, 3),
                "owner": row.get(c_owner or "", "").strip() or None,
                "notes": row.get(c_notes or "", "").strip() or None,
                "ticket": row.get(c_ticket or "", "").strip() or None,
            })

    return items


def parse_inline_item(s: str) -> Dict[str, Any]:
    """Parse 'Title:impact:cost:risk' into item dict."""
    parts = s.rsplit(":", 3)
    if len(parts) < 4:
        raise ValueError(f"Invalid item '{s}'. Format: Title:impact:cost:risk")
    return {
        "title": parts[0].strip(),
        "category": "General",
        "impact": max(1, min(5, int(parts[1].strip()))),
        "cost": max(1, min(5, int(parts[2].strip()))),
        "risk": max(1, min(5, int(parts[3].strip()))),
        "owner": None,
        "notes": None,
        "ticket": None,
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


def _score_dots(score: int, max_score: int = 5) -> str:
    return "●" * score + "○" * (max_score - score)


def print_report(
    items: List[Dict[str, Any]],
    impact_weight: float,
    risk_weight: float,
) -> None:
    """Pretty-print tech debt analysis."""
    print("\n" + "=" * 78)
    print("🔧 TECH DEBT SCORER")
    print("=" * 78)

    print(f"\n📋 OVERVIEW:")
    print(f"   • Items scored:       {len(items)}")
    print(f"   • Impact weight:      {impact_weight:.1f}×")
    print(f"   • Risk weight:        {risk_weight:.1f}×")
    print(f"   • Formula:            priority = (impact × {impact_weight:.1f} + risk × {risk_weight:.1f}) / cost")

    # Compute scores and sort
    for item in items:
        item["priority"] = compute_priority(
            item["impact"], item["cost"], item["risk"], impact_weight, risk_weight
        )
        tier, emoji = classify_priority(item["priority"])
        item["tier"] = tier
        item["tier_emoji"] = emoji

    ranked = sorted(items, key=lambda x: -x["priority"])

    # Tier summary
    tier_counts = defaultdict(int)
    for item in ranked:
        tier_counts[item["tier"]] += 1

    print(f"\n📊 PRIORITY DISTRIBUTION:")
    for tier, emoji in [("Critical", "🔴"), ("High", "🟠"), ("Medium", "🟡"), ("Low", "🟢")]:
        count = tier_counts.get(tier, 0)
        bar = _bar(count, len(items), 15)
        print(f"   {emoji} {tier:<10} {count:>3}  {bar}")

    # Ranked table
    max_priority = ranked[0]["priority"] if ranked else 1
    print(f"\n🏆 RANKED BACKLOG (highest priority first):\n")
    print(f"   {'#':>3} {'Item':<28} {'Impact':>6} {'Cost':>6} {'Risk':>6} {'Score':>7} {'Tier'}")
    print(f"   {'─'*3} {'─'*28} {'─'*6} {'─'*6} {'─'*6} {'─'*7} {'─'*10}")

    for i, item in enumerate(ranked, 1):
        title = item["title"][:28]
        impact_str = _score_dots(item["impact"])
        cost_str = _score_dots(item["cost"])
        risk_str = _score_dots(item["risk"])
        print(f"   {i:>3} {title:<28} {item['impact']:>6} {item['cost']:>6} {item['risk']:>6} {item['priority']:>7.2f} {item['tier_emoji']} {item['tier']}")

    # Detail cards for top items
    print(f"\n{'─'*78}")
    print(f"\n📌 TOP PRIORITY ITEMS:\n")
    for i, item in enumerate(ranked[:5], 1):
        tier_emoji = item["tier_emoji"]
        print(f"   {tier_emoji} #{i}: {item['title']}")
        print(f"      Impact: {_score_dots(item['impact'])} ({item['impact']}/5)   "
              f"Cost: {_score_dots(item['cost'])} ({classify_cost(item['cost'])})   "
              f"Risk: {_score_dots(item['risk'])} ({item['risk']}/5)")
        print(f"      Priority: {item['priority']:.2f} ({item['tier']})")
        if item.get("category") and item["category"] != "General":
            print(f"      Category: {item['category']}")
        if item.get("owner"):
            print(f"      Owner: {item['owner']}")
        if item.get("notes"):
            print(f"      Notes: {item['notes']}")
        if item.get("ticket"):
            print(f"      Ticket: {item['ticket']}")
        print()

    # Category summary
    categories: Dict[str, List[Dict]] = defaultdict(list)
    for item in ranked:
        categories[item["category"]].append(item)

    if len(categories) > 1:
        print(f"{'─'*78}")
        print(f"\n📂 BY CATEGORY:")
        for cat, cat_items in sorted(categories.items(), key=lambda x: -max(i["priority"] for i in x[1])):
            avg_priority = sum(i["priority"] for i in cat_items) / len(cat_items)
            top_tier = cat_items[0]["tier_emoji"] if cat_items else ""
            print(f"   • {cat}: {len(cat_items)} items (avg priority: {avg_priority:.2f}) {top_tier}")

    # Owner summary
    owners: Dict[str, List[Dict]] = defaultdict(list)
    for item in ranked:
        if item.get("owner"):
            owners[item["owner"]].append(item)

    if owners:
        print(f"\n👥 BY OWNER:")
        for owner, owner_items in sorted(owners.items(), key=lambda x: -sum(i["priority"] for i in x[1])):
            total_cost = sum(i["cost"] for i in owner_items)
            critical = sum(1 for i in owner_items if i["tier"] in ("Critical", "High"))
            print(f"   • {owner}: {len(owner_items)} items ({critical} critical/high, total effort: {total_cost})")

    # Effort buckets
    buckets = effort_bucket(ranked)
    print(f"\n📦 EFFORT BUCKETS:")
    for bucket_name, bucket_items in buckets.items():
        if bucket_items:
            names = ", ".join(i["title"][:20] for i in sorted(bucket_items, key=lambda x: -x["priority"])[:3])
            more = f" +{len(bucket_items) - 3} more" if len(bucket_items) > 3 else ""
            print(f"   • {bucket_name}: {len(bucket_items)} items")
            print(f"     Top: {names}{more}")

    # Quick wins recommendation
    quick_wins = [i for i in ranked if i["cost"] <= 2 and i["priority"] >= 3.0]
    if quick_wins:
        print(f"\n⚡ RECOMMENDED QUICK WINS (high priority, low effort):")
        for item in quick_wins[:5]:
            print(f"   • {item['tier_emoji']} {item['title']} (priority: {item['priority']:.2f}, cost: {classify_cost(item['cost'])})")

    # Total effort
    total_effort = sum(i["cost"] for i in items)
    avg_effort = total_effort / len(items) if items else 0
    print(f"\n💡 PLANNING NOTES:")
    print(f"   • Total effort score: {total_effort} (avg {avg_effort:.1f} per item)")
    print(f"   • Recommendation: dedicate 15-20% of sprint capacity to tech debt")
    print(f"   • Start with quick wins to build momentum, then tackle critical items")
    print(f"   • Re-score quarterly as business context changes")
    print("\n" + "=" * 78)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Score and rank technical debt items by business impact, engineering cost, "
                    "and risk to help PMs prioritize paydown alongside feature work.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --csv debt.csv
  %(prog)s --item "Monolith DB:4:3:3" --item "Legacy auth:5:4:5" --item "Flaky CI:3:2:4"
  %(prog)s --csv debt.csv --impact-weight 3 --risk-weight 2
  %(prog)s --csv debt.csv --output debt-report.json

Inline item format: "Title:impact:cost:risk" (each 1-5)
    impact = business impact (user pain, revenue, velocity)
    cost = engineering effort to fix (1=trivial, 5=multi-sprint)
    risk = urgency / incident likelihood (1=low, 5=imminent)
        """,
    )
    parser.add_argument("--csv", "-c", type=str, help="CSV file with tech debt items")
    parser.add_argument("--item", "-i", type=str, action="append",
                        help="Inline item: 'Title:impact:cost:risk'")
    parser.add_argument("--impact-weight", type=float, default=2.0,
                        help="Weight for business impact in priority formula (default: 2.0)")
    parser.add_argument("--risk-weight", type=float, default=1.5,
                        help="Weight for risk/urgency in priority formula (default: 1.5)")
    parser.add_argument("--output", "-o", type=str, help="Write JSON results to file")
    args = parser.parse_args()

    items: List[Dict[str, Any]] = []

    if args.csv:
        try:
            items = load_csv(args.csv)
        except Exception as e:
            print(f"Error loading CSV: {e}", file=sys.stderr)
            return 1
    elif args.item:
        try:
            items = [parse_inline_item(s) for s in args.item]
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1
    else:
        print("Error: provide --csv or --item.", file=sys.stderr)
        parser.print_help(sys.stderr)
        return 1

    if not items:
        print("Error: no valid items found.", file=sys.stderr)
        return 1

    # Report
    print_report(items, args.impact_weight, args.risk_weight)

    # JSON output
    if args.output:
        for item in items:
            item["priority"] = compute_priority(
                item["impact"], item["cost"], item["risk"],
                args.impact_weight, args.risk_weight,
            )
            tier, _ = classify_priority(item["priority"])
            item["tier"] = tier
        ranked = sorted(items, key=lambda x: -x["priority"])

        report = {
            "n_items": len(ranked),
            "weights": {"impact": args.impact_weight, "risk": args.risk_weight},
            "items": [{k: v for k, v in i.items() if k not in ("tier_emoji",)} for i in ranked],
        }
        with open(args.output, "w") as f:
            json.dump(report, f, indent=2)
        print(f"\n📁 Results saved to {args.output}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
