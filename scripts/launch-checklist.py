#!/usr/bin/env python3
"""
Launch Checklist Generator

Generate customizable pre-launch checklists based on feature type (backend,
frontend, ML, infra, full-stack) with ownership assignments and status
tracking. Reduces launch-day surprises by ensuring nothing falls through
the cracks.

Includes standard items across categories: engineering, QA, monitoring,
security, documentation, rollout, comms, and rollback planning.

Usage:
    # Generate checklist for a feature type
    python launch-checklist.py --name "AI Recommendations v2" --type ml

    # Multiple types (full-stack + ML)
    python launch-checklist.py --name "Smart Search" --type frontend --type backend --type ml

    # With custom items
    python launch-checklist.py --name "Payment Gateway" --type backend \\
        --item "PCI compliance review:Security:P0" \\
        --item "Stripe webhook testing:QA:P1" \\
        --item "Fraud detection rules updated:Payments:P1"

    # From JSON (with status tracking)
    python launch-checklist.py --json checklist.json

    # Generate Markdown
    python launch-checklist.py --name "Feature X" --type full-stack --markdown checklist.md

    Format for --item: "Description:Owner:Priority"

JSON format:
    {
      "name": "AI Recommendations v2",
      "types": ["backend", "ml"],
      "target_date": "2025-08-01",
      "owner": "Product Team",
      "custom_items": [
        {"description": "Model accuracy validated", "owner": "Data Science", "priority": "P0"}
      ],
      "overrides": {
        "skip_categories": ["comms"]
      }
    }

Requirements:
    None (stdlib only).
"""

import argparse
import json
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Checklist templates
# ---------------------------------------------------------------------------

CATEGORIES = {
    "engineering": "🔧 Engineering",
    "qa": "🧪 QA & Testing",
    "monitoring": "📊 Monitoring & Observability",
    "security": "🔒 Security",
    "docs": "📝 Documentation",
    "rollout": "🚀 Rollout & Deployment",
    "comms": "📣 Communication",
    "rollback": "🔙 Rollback Plan",
    "data": "📦 Data & ML",
    "ux": "🎨 UX & Accessibility",
}

CHECKLISTS: Dict[str, List[Dict[str, Any]]] = {
    "backend": [
        {"description": "API endpoints tested with integration tests", "category": "qa", "priority": "P0"},
        {"description": "Database migrations tested on staging", "category": "engineering", "priority": "P0"},
        {"description": "Load testing completed for expected traffic", "category": "qa", "priority": "P1"},
        {"description": "Error handling and retry logic verified", "category": "engineering", "priority": "P1"},
        {"description": "Rate limiting configured", "category": "security", "priority": "P1"},
        {"description": "API versioning strategy confirmed", "category": "engineering", "priority": "P2"},
        {"description": "Logging and structured traces added", "category": "monitoring", "priority": "P1"},
        {"description": "Alerts configured for error rate and latency", "category": "monitoring", "priority": "P0"},
        {"description": "Health check endpoint verified", "category": "monitoring", "priority": "P1"},
        {"description": "Backward compatibility with existing clients", "category": "engineering", "priority": "P0"},
        {"description": "Secrets and credentials stored securely", "category": "security", "priority": "P0"},
        {"description": "API documentation updated", "category": "docs", "priority": "P1"},
        {"description": "Rollback procedure documented and tested", "category": "rollback", "priority": "P0"},
        {"description": "Feature flag configured for gradual rollout", "category": "rollout", "priority": "P1"},
        {"description": "Deployment runbook created", "category": "rollout", "priority": "P1"},
    ],
    "frontend": [
        {"description": "Cross-browser testing completed", "category": "qa", "priority": "P0"},
        {"description": "Mobile responsive design verified", "category": "qa", "priority": "P0"},
        {"description": "Accessibility audit passed (WCAG 2.1 AA)", "category": "ux", "priority": "P1"},
        {"description": "Performance budget met (LCP, FID, CLS)", "category": "qa", "priority": "P1"},
        {"description": "Error boundaries and fallback UI in place", "category": "engineering", "priority": "P1"},
        {"description": "Analytics events instrumented", "category": "monitoring", "priority": "P1"},
        {"description": "Feature flag / toggle wired up", "category": "rollout", "priority": "P1"},
        {"description": "Screenshot / visual regression tests pass", "category": "qa", "priority": "P2"},
        {"description": "Copy reviewed and approved", "category": "comms", "priority": "P1"},
        {"description": "Dark mode / theme support verified", "category": "ux", "priority": "P2"},
        {"description": "Loading states and skeleton screens added", "category": "ux", "priority": "P2"},
        {"description": "Client-side error tracking configured", "category": "monitoring", "priority": "P1"},
        {"description": "CDN and caching strategy confirmed", "category": "engineering", "priority": "P2"},
    ],
    "ml": [
        {"description": "Model accuracy meets acceptance threshold", "category": "data", "priority": "P0"},
        {"description": "Bias and fairness evaluation completed", "category": "data", "priority": "P0"},
        {"description": "Model inference latency within SLA", "category": "data", "priority": "P0"},
        {"description": "Fallback behavior when model unavailable", "category": "engineering", "priority": "P0"},
        {"description": "A/B test or shadow mode configured", "category": "data", "priority": "P1"},
        {"description": "Data pipeline health checks in place", "category": "data", "priority": "P1"},
        {"description": "Model versioning and rollback procedure", "category": "rollback", "priority": "P0"},
        {"description": "Input validation and guardrails active", "category": "security", "priority": "P0"},
        {"description": "Token/compute cost estimated and budgeted", "category": "data", "priority": "P1"},
        {"description": "Model monitoring dashboard live", "category": "monitoring", "priority": "P1"},
        {"description": "Drift detection configured", "category": "data", "priority": "P2"},
        {"description": "PII/sensitive data handling reviewed", "category": "security", "priority": "P0"},
        {"description": "Human review / escalation path defined", "category": "data", "priority": "P1"},
    ],
    "infra": [
        {"description": "Infrastructure provisioned via IaC", "category": "engineering", "priority": "P0"},
        {"description": "Auto-scaling policies configured and tested", "category": "engineering", "priority": "P0"},
        {"description": "Disaster recovery plan documented", "category": "rollback", "priority": "P0"},
        {"description": "Network security groups / firewall rules reviewed", "category": "security", "priority": "P0"},
        {"description": "SSL/TLS certificates valid and auto-renewing", "category": "security", "priority": "P0"},
        {"description": "Backup and restore procedures tested", "category": "rollback", "priority": "P0"},
        {"description": "Resource utilization alerts configured", "category": "monitoring", "priority": "P1"},
        {"description": "Cost estimates reviewed and approved", "category": "engineering", "priority": "P1"},
        {"description": "DNS and routing changes planned", "category": "engineering", "priority": "P1"},
        {"description": "Runbook for on-call created", "category": "docs", "priority": "P1"},
    ],
}

COMMON_ITEMS = [
    {"description": "Stakeholders notified of launch date", "category": "comms", "priority": "P1"},
    {"description": "Support team briefed and FAQ prepared", "category": "comms", "priority": "P1"},
    {"description": "Release notes drafted", "category": "docs", "priority": "P2"},
    {"description": "Rollback criteria defined", "category": "rollback", "priority": "P0"},
    {"description": "On-call engineer assigned for launch window", "category": "rollout", "priority": "P0"},
    {"description": "Go/no-go meeting scheduled", "category": "rollout", "priority": "P1"},
]


def generate_checklist(
    name: str,
    types: List[str],
    custom_items: Optional[List[Dict[str, Any]]] = None,
    target_date: Optional[str] = None,
    owner: str = "",
    skip_categories: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Generate a launch checklist."""
    skip = set(skip_categories or [])
    items: List[Dict[str, Any]] = []
    seen_descriptions = set()

    # Add type-specific items
    for feature_type in types:
        type_items = CHECKLISTS.get(feature_type, [])
        for item in type_items:
            if item["category"] not in skip and item["description"] not in seen_descriptions:
                items.append({
                    **item,
                    "source": feature_type,
                    "status": "pending",
                    "assignee": "",
                })
                seen_descriptions.add(item["description"])

    # Add common items
    for item in COMMON_ITEMS:
        if item["category"] not in skip and item["description"] not in seen_descriptions:
            items.append({
                **item,
                "source": "common",
                "status": "pending",
                "assignee": "",
            })
            seen_descriptions.add(item["description"])

    # Add custom items
    for ci in (custom_items or []):
        items.append({
            "description": ci.get("description", ""),
            "category": ci.get("category", "engineering"),
            "priority": ci.get("priority", "P1"),
            "source": "custom",
            "status": ci.get("status", "pending"),
            "assignee": ci.get("owner", ci.get("assignee", "")),
        })

    # Sort by priority then category
    priority_order = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}
    items.sort(key=lambda x: (priority_order.get(x["priority"], 9), x["category"]))

    # Stats
    total = len(items)
    by_priority = {}
    by_category = {}
    for item in items:
        by_priority[item["priority"]] = by_priority.get(item["priority"], 0) + 1
        by_category[item["category"]] = by_category.get(item["category"], 0) + 1

    done = sum(1 for i in items if i["status"] == "done")
    completion_pct = done / total * 100 if total > 0 else 0

    p0_done = sum(1 for i in items if i["priority"] == "P0" and i["status"] == "done")
    p0_total = by_priority.get("P0", 0)
    p0_ready = p0_done == p0_total and p0_total > 0

    if completion_pct >= 100:
        readiness = "🟢 Ready to launch"
    elif p0_ready and completion_pct >= 80:
        readiness = "🟢 All P0s done — ready with minor items remaining"
    elif p0_ready:
        readiness = "🟡 P0s done but significant items remaining"
    elif completion_pct >= 50:
        readiness = "🟡 In progress"
    else:
        readiness = "🔴 Not ready"

    return {
        "name": name,
        "types": types,
        "target_date": target_date,
        "owner": owner,
        "items": items,
        "total": total,
        "done": done,
        "completion_pct": round(completion_pct, 1),
        "by_priority": by_priority,
        "by_category": by_category,
        "p0_ready": p0_ready,
        "readiness": readiness,
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def parse_item_string(s: str) -> Dict[str, Any]:
    """Parse 'Description:Owner:Priority'."""
    parts = s.rsplit(":", 2)
    desc = parts[0].strip()
    owner = parts[1].strip() if len(parts) > 1 else ""
    priority = parts[2].strip().upper() if len(parts) > 2 else "P1"
    return {"description": desc, "owner": owner, "priority": priority}


def load_json(path: str) -> Dict[str, Any]:
    """Load checklist config from JSON."""
    with open(path, encoding="utf-8") as f:
        config = json.load(f)

    types = config.get("types", [])
    custom = config.get("custom_items", [])
    overrides = config.get("overrides", {})

    checklist = generate_checklist(
        name=config.get("name", ""),
        types=types,
        custom_items=custom,
        target_date=config.get("target_date"),
        owner=config.get("owner", ""),
        skip_categories=overrides.get("skip_categories"),
    )

    # Apply status from JSON items if present
    existing = {item["description"]: item for item in config.get("items", [])}
    for item in checklist["items"]:
        if item["description"] in existing:
            saved = existing[item["description"]]
            item["status"] = saved.get("status", "pending")
            item["assignee"] = saved.get("assignee", item.get("assignee", ""))

    # Recalculate stats
    done = sum(1 for i in checklist["items"] if i["status"] == "done")
    checklist["done"] = done
    checklist["completion_pct"] = round(done / checklist["total"] * 100, 1) if checklist["total"] > 0 else 0

    return checklist


# ---------------------------------------------------------------------------
# Markdown generation
# ---------------------------------------------------------------------------

def generate_markdown(cl: Dict[str, Any]) -> str:
    """Generate Markdown checklist."""
    lines = []
    lines.append(f"# 🚀 Launch Checklist: {cl['name']}")
    lines.append("")
    if cl["target_date"]:
        lines.append(f"**Target date:** {cl['target_date']}  ")
    if cl["owner"]:
        lines.append(f"**Owner:** {cl['owner']}  ")
    lines.append(f"**Types:** {', '.join(cl['types'])}  ")
    lines.append(f"**Progress:** {cl['done']}/{cl['total']} ({cl['completion_pct']:.0f}%)  ")
    lines.append(f"**Readiness:** {cl['readiness']}  ")
    lines.append("")

    # Group by category
    by_cat: Dict[str, List[Dict[str, Any]]] = {}
    for item in cl["items"]:
        cat = item["category"]
        if cat not in by_cat:
            by_cat[cat] = []
        by_cat[cat].append(item)

    for cat, cat_items in by_cat.items():
        cat_label = CATEGORIES.get(cat, cat.capitalize())
        lines.append(f"## {cat_label}")
        lines.append("")
        for item in cat_items:
            check = "x" if item["status"] == "done" else " "
            assignee = f" @{item['assignee']}" if item.get("assignee") else ""
            lines.append(f"- [{check}] **[{item['priority']}]** {item['description']}{assignee}")
        lines.append("")

    lines.append("---")
    lines.append(f"*Generated: {cl['generated_at']}*")
    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Terminal report
# ---------------------------------------------------------------------------

def print_report(cl: Dict[str, Any]) -> None:
    """Pretty-print launch checklist."""
    print("\n" + "=" * 78)
    print("🚀 LAUNCH CHECKLIST")
    print("=" * 78)

    print(f"\n   Feature:    {cl['name']}")
    print(f"   Types:      {', '.join(cl['types'])}")
    if cl["target_date"]:
        print(f"   Target:     {cl['target_date']}")
    if cl["owner"]:
        print(f"   Owner:      {cl['owner']}")

    # Progress
    bar_width = 30
    filled = int(cl["completion_pct"] / 100 * bar_width)
    bar = "█" * filled + "░" * (bar_width - filled)
    print(f"\n   Progress:   [{bar}] {cl['done']}/{cl['total']} ({cl['completion_pct']:.0f}%)")
    print(f"   Readiness:  {cl['readiness']}")

    # Priority breakdown
    print(f"\n   By priority:")
    for pri in ["P0", "P1", "P2", "P3"]:
        count = cl["by_priority"].get(pri, 0)
        if count > 0:
            done_p = sum(1 for i in cl["items"] if i["priority"] == pri and i["status"] == "done")
            emoji = "✅" if done_p == count else "⬜"
            print(f"   {emoji} {pri}: {done_p}/{count}")

    # Items grouped by category
    by_cat: Dict[str, List[Dict[str, Any]]] = {}
    for item in cl["items"]:
        cat = item["category"]
        if cat not in by_cat:
            by_cat[cat] = []
        by_cat[cat].append(item)

    for cat, cat_items in by_cat.items():
        cat_label = CATEGORIES.get(cat, cat.capitalize())
        done_cat = sum(1 for i in cat_items if i["status"] == "done")
        print(f"\n{'─'*78}")
        print(f"\n   {cat_label} ({done_cat}/{len(cat_items)}):\n")

        for item in cat_items:
            icon = "✅" if item["status"] == "done" else "⬜"
            assignee = f" [{item['assignee']}]" if item.get("assignee") else ""
            print(f"   {icon} [{item['priority']}] {item['description']}{assignee}")

    # Guidance
    print(f"\n{'─'*78}")
    print(f"\n💡 LAUNCH TIPS:")
    print(f"   • Complete all P0 items before launch — no exceptions")
    print(f"   • Assign owners to every item for accountability")
    print(f"   • Run the checklist in a go/no-go meeting 24h before launch")
    print(f"   • Don't launch on Fridays unless you have weekend coverage")
    print(f"   • Have a rollback plan rehearsed before you ship")
    print("\n" + "=" * 78)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Generate pre-launch checklists by feature type with ownership "
                    "and status tracking. Reduces launch-day surprises.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --name "AI Recs v2" --type ml --type backend
  %(prog)s --name "Payment Gateway" --type backend --item "PCI review:Security:P0"
  %(prog)s --json checklist.json --markdown checklist.md
        """,
    )

    parser.add_argument("--name", type=str, help="Feature name")
    parser.add_argument("--type", type=str, action="append",
                        choices=["backend", "frontend", "ml", "infra", "full-stack"],
                        help="Feature type (can specify multiple)")
    parser.add_argument("--item", type=str, action="append",
                        help="Custom item: 'Description:Owner:Priority'")
    parser.add_argument("--target-date", type=str, help="Target launch date")
    parser.add_argument("--owner", type=str, default="", help="Feature owner")

    parser.add_argument("--json", "-j", type=str, help="JSON config file")
    parser.add_argument("--markdown", type=str, help="Write Markdown checklist to file")
    parser.add_argument("--output", "-o", type=str, help="Write JSON results to file")
    args = parser.parse_args()

    cl = None

    if args.json:
        try:
            cl = load_json(args.json)
        except Exception as e:
            print(f"Error loading JSON: {e}", file=sys.stderr)
            return 1

    elif args.name and args.type:
        types = args.type
        if "full-stack" in types:
            types = [t for t in types if t != "full-stack"]
            types = list(set(types + ["backend", "frontend"]))

        custom = []
        if args.item:
            for i_str in args.item:
                custom.append(parse_item_string(i_str))

        cl = generate_checklist(
            name=args.name,
            types=types,
            custom_items=custom,
            target_date=args.target_date,
            owner=args.owner,
        )
    else:
        print("Error: provide --name + --type, or --json.", file=sys.stderr)
        parser.print_help(sys.stderr)
        return 1

    # Report
    print_report(cl)

    # Markdown
    if args.markdown:
        md = generate_markdown(cl)
        with open(args.markdown, "w", encoding="utf-8") as f:
            f.write(md)
        print(f"\n📄 Markdown saved to {args.markdown}")

    # JSON output
    if args.output:
        with open(args.output, "w") as f:
            json.dump(cl, f, indent=2)
        print(f"\n📁 Results saved to {args.output}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
