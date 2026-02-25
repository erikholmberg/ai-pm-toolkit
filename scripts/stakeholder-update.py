#!/usr/bin/env python3
"""
Stakeholder Update Generator

Generate structured weekly or monthly stakeholder updates from metrics,
OKR progress, milestones, blockers, and upcoming work. Outputs formatted
terminal reports or Markdown suitable for email/Slack/Confluence.

Complements exec-summary-generator with a recurring, template-driven format
designed for regular cadence updates rather than one-off summaries.

Usage:
    # Quick update from inline data
    python stakeholder-update.py \\
        --project "Checkout Redesign" --period "Week of Jul 7" \\
        --status green \\
        --highlight "Shipped new payment flow to 25% of users" \\
        --highlight "Error rate stable at 0.12%" \\
        --metric "Conversion rate:3.2%:3.5%:up" \\
        --metric "Cart abandonment:68%:65%:down" \\
        --risk "Payment provider latency spikes during peak hours" \\
        --blocker "Design review for mobile checkout delayed 3 days" \\
        --next "Expand rollout to 50%" \\
        --next "A/B test new CTA copy"

    # From JSON
    python stakeholder-update.py --json update.json

    # Generate Markdown
    python stakeholder-update.py --json update.json --markdown update.md

    Format for --metric: "Name:current:target:direction"
    direction: up (higher is better) or down (lower is better)

JSON format:
    {
      "project": "Checkout Redesign",
      "period": "Week of Jul 7, 2025",
      "author": "Jane PM",
      "overall_status": "green",
      "summary": "On track for Q3 launch. Payment flow shipped to 25%.",
      "highlights": [
        "Shipped new payment flow to 25% of users",
        "Error rate stable at 0.12%"
      ],
      "metrics": [
        {"name": "Conversion rate", "current": "3.2%", "target": "3.5%", "direction": "up"},
        {"name": "Cart abandonment", "current": "68%", "target": "65%", "direction": "down"}
      ],
      "okrs": [
        {"objective": "Improve checkout conversion", "score": 0.55, "status": "on-track"}
      ],
      "milestones": [
        {"name": "Payment flow GA", "date": "2025-07-21", "status": "on-track"},
        {"name": "Mobile checkout", "date": "2025-08-04", "status": "at-risk"}
      ],
      "risks": ["Payment provider latency during peak"],
      "blockers": ["Design review delayed 3 days"],
      "next_actions": ["Expand rollout to 50%", "A/B test CTA copy"],
      "asks": ["Need design review by Wed", "Budget approval for load testing"]
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
# Update model
# ---------------------------------------------------------------------------

STATUS_EMOJI = {
    "green": "🟢",
    "yellow": "🟡",
    "red": "🔴",
    "blue": "🔵",
}

STATUS_LABELS = {
    "green": "On Track",
    "yellow": "At Risk",
    "red": "Off Track / Blocked",
    "blue": "Complete",
}


def build_update(
    project: str,
    period: str = "",
    author: str = "",
    overall_status: str = "green",
    summary: str = "",
    highlights: Optional[List[str]] = None,
    metrics: Optional[List[Dict[str, str]]] = None,
    okrs: Optional[List[Dict[str, Any]]] = None,
    milestones: Optional[List[Dict[str, Any]]] = None,
    risks: Optional[List[str]] = None,
    blockers: Optional[List[str]] = None,
    next_actions: Optional[List[str]] = None,
    asks: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Build a structured stakeholder update."""
    if not period:
        period = datetime.now().strftime("Week of %b %d, %Y")

    overall_status = overall_status.lower().strip()
    if overall_status not in STATUS_EMOJI:
        overall_status = "green"

    # Assess each metric
    assessed_metrics = []
    for m in (metrics or []):
        name = m.get("name", "")
        current = m.get("current", "")
        target = m.get("target", "")
        direction = m.get("direction", "up").lower()

        # Try to determine health
        health = "neutral"
        try:
            cur_val = float(current.strip().rstrip("%").replace(",", "").replace("$", ""))
            tgt_val = float(target.strip().rstrip("%").replace(",", "").replace("$", ""))
            if direction == "up":
                ratio = cur_val / tgt_val if tgt_val != 0 else 1
            else:
                ratio = tgt_val / cur_val if cur_val != 0 else 1

            if ratio >= 0.9:
                health = "good"
            elif ratio >= 0.7:
                health = "warning"
            else:
                health = "poor"
        except (ValueError, ZeroDivisionError):
            pass

        assessed_metrics.append({
            "name": name,
            "current": current,
            "target": target,
            "direction": direction,
            "health": health,
        })

    return {
        "project": project,
        "period": period,
        "author": author,
        "overall_status": overall_status,
        "summary": summary,
        "highlights": highlights or [],
        "metrics": assessed_metrics,
        "okrs": okrs or [],
        "milestones": milestones or [],
        "risks": risks or [],
        "blockers": blockers or [],
        "next_actions": next_actions or [],
        "asks": asks or [],
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def parse_metric_string(s: str) -> Dict[str, str]:
    """Parse 'Name:current:target:direction'."""
    parts = s.split(":")
    if len(parts) < 3:
        raise ValueError(f"Invalid metric '{s}'. Format: Name:current:target[:direction]")
    return {
        "name": parts[0].strip(),
        "current": parts[1].strip(),
        "target": parts[2].strip(),
        "direction": parts[3].strip().lower() if len(parts) > 3 else "up",
    }


def load_json(path: str) -> Dict[str, Any]:
    """Load update from JSON."""
    with open(path, encoding="utf-8") as f:
        config = json.load(f)

    return build_update(
        project=config.get("project", ""),
        period=config.get("period", ""),
        author=config.get("author", ""),
        overall_status=config.get("overall_status", "green"),
        summary=config.get("summary", ""),
        highlights=config.get("highlights"),
        metrics=config.get("metrics"),
        okrs=config.get("okrs"),
        milestones=config.get("milestones"),
        risks=config.get("risks"),
        blockers=config.get("blockers"),
        next_actions=config.get("next_actions"),
        asks=config.get("asks"),
    )


# ---------------------------------------------------------------------------
# Markdown generation
# ---------------------------------------------------------------------------

def generate_markdown(update: Dict[str, Any]) -> str:
    """Generate Markdown stakeholder update."""
    lines = []
    emoji = STATUS_EMOJI.get(update["overall_status"], "⬜")
    label = STATUS_LABELS.get(update["overall_status"], "Unknown")

    lines.append(f"# {emoji} {update['project']} — Status Update")
    lines.append("")
    lines.append(f"**Period:** {update['period']}  ")
    if update["author"]:
        lines.append(f"**Author:** {update['author']}  ")
    lines.append(f"**Status:** {emoji} {label}  ")
    lines.append("")

    if update["summary"]:
        lines.append(f"> {update['summary']}")
        lines.append("")

    if update["highlights"]:
        lines.append("## ✅ Highlights")
        lines.append("")
        for h in update["highlights"]:
            lines.append(f"- {h}")
        lines.append("")

    if update["metrics"]:
        lines.append("## 📊 Key Metrics")
        lines.append("")
        lines.append("| Metric | Current | Target | Status |")
        lines.append("|--------|---------|--------|--------|")
        for m in update["metrics"]:
            health_emoji = {"good": "🟢", "warning": "🟡", "poor": "🔴"}.get(m["health"], "⬜")
            arrow = "↑" if m["direction"] == "up" else "↓"
            lines.append(f"| {m['name']} | {m['current']} | {m['target']} {arrow} | {health_emoji} |")
        lines.append("")

    if update["okrs"]:
        lines.append("## 🎯 OKR Progress")
        lines.append("")
        for okr in update["okrs"]:
            score = okr.get("score", 0)
            pct = int(score * 100) if isinstance(score, float) and score <= 1 else score
            status = okr.get("status", "")
            lines.append(f"- **{okr.get('objective', '')}**: {pct}% — {status}")
        lines.append("")

    if update["milestones"]:
        lines.append("## 📅 Milestones")
        lines.append("")
        lines.append("| Milestone | Date | Status |")
        lines.append("|-----------|------|--------|")
        for ms in update["milestones"]:
            ms_emoji = STATUS_EMOJI.get(ms.get("status", ""), "⬜")
            lines.append(f"| {ms.get('name', '')} | {ms.get('date', '')} | {ms_emoji} {ms.get('status', '')} |")
        lines.append("")

    if update["blockers"]:
        lines.append("## 🚫 Blockers")
        lines.append("")
        for b in update["blockers"]:
            lines.append(f"- 🔴 {b}")
        lines.append("")

    if update["risks"]:
        lines.append("## ⚠️ Risks")
        lines.append("")
        for r in update["risks"]:
            lines.append(f"- 🟡 {r}")
        lines.append("")

    if update["next_actions"]:
        lines.append("## ➡️ Next Actions")
        lines.append("")
        for a in update["next_actions"]:
            lines.append(f"- [ ] {a}")
        lines.append("")

    if update["asks"]:
        lines.append("## 🙏 Asks / Decisions Needed")
        lines.append("")
        for ask in update["asks"]:
            lines.append(f"- **{ask}**")
        lines.append("")

    lines.append(f"---")
    lines.append(f"*Generated: {update['generated_at']}*")
    lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Terminal report
# ---------------------------------------------------------------------------

def print_report(update: Dict[str, Any]) -> None:
    """Pretty-print stakeholder update."""
    emoji = STATUS_EMOJI.get(update["overall_status"], "⬜")
    label = STATUS_LABELS.get(update["overall_status"], "Unknown")

    print("\n" + "=" * 78)
    print(f"📬 STAKEHOLDER UPDATE")
    print("=" * 78)

    print(f"\n   {emoji} {update['project'].upper()}")
    print(f"   Period:  {update['period']}")
    if update["author"]:
        print(f"   Author:  {update['author']}")
    print(f"   Status:  {emoji} {label}")

    if update["summary"]:
        print(f"\n   💬 {update['summary']}")

    # Highlights
    if update["highlights"]:
        print(f"\n{'─'*78}")
        print(f"\n   ✅ HIGHLIGHTS:\n")
        for h in update["highlights"]:
            print(f"   • {h}")

    # Metrics
    if update["metrics"]:
        print(f"\n{'─'*78}")
        print(f"\n   📊 KEY METRICS:\n")
        print(f"   {'Metric':<24} {'Current':>10} {'Target':>10} {'Status'}")
        print(f"   {'─'*24} {'─'*10} {'─'*10} {'─'*8}")

        for m in update["metrics"]:
            health_emoji = {"good": "🟢", "warning": "🟡", "poor": "🔴"}.get(m["health"], "⬜")
            arrow = "↑" if m["direction"] == "up" else "↓"
            print(f"   {m['name'][:24]:<24} {m['current']:>10} {m['target']:>10} {arrow} {health_emoji}")

    # OKRs
    if update["okrs"]:
        print(f"\n{'─'*78}")
        print(f"\n   🎯 OKR PROGRESS:\n")

        for okr in update["okrs"]:
            score = okr.get("score", 0)
            pct = int(score * 100) if isinstance(score, float) and score <= 1 else int(score)
            status = okr.get("status", "")
            status_emoji = STATUS_EMOJI.get(status.replace(" ", "-"), "⬜")

            bar_width = 20
            filled = int(pct / 100 * bar_width)
            bar = "█" * filled + "░" * (bar_width - filled)
            print(f"   {okr.get('objective', '')[:40]:<40}")
            print(f"   {bar} {pct}%  {status_emoji} {status}")

    # Milestones
    if update["milestones"]:
        print(f"\n{'─'*78}")
        print(f"\n   📅 MILESTONES:\n")
        print(f"   {'Milestone':<30} {'Date':>12} {'Status'}")
        print(f"   {'─'*30} {'─'*12} {'─'*12}")

        for ms in update["milestones"]:
            ms_emoji = STATUS_EMOJI.get(ms.get("status", "").replace(" ", "-"), "⬜")
            print(f"   {ms.get('name', '')[:30]:<30} {ms.get('date', ''):>12} {ms_emoji} {ms.get('status', '')}")

    # Blockers
    if update["blockers"]:
        print(f"\n{'─'*78}")
        print(f"\n   🚫 BLOCKERS:\n")
        for b in update["blockers"]:
            print(f"   🔴 {b}")

    # Risks
    if update["risks"]:
        print(f"\n{'─'*78}")
        print(f"\n   ⚠️  RISKS:\n")
        for r in update["risks"]:
            print(f"   🟡 {r}")

    # Next actions
    if update["next_actions"]:
        print(f"\n{'─'*78}")
        print(f"\n   ➡️  NEXT ACTIONS:\n")
        for a in update["next_actions"]:
            print(f"   ☐ {a}")

    # Asks
    if update["asks"]:
        print(f"\n{'─'*78}")
        print(f"\n   🙏 ASKS / DECISIONS NEEDED:\n")
        for ask in update["asks"]:
            print(f"   ❗ {ask}")

    # Completeness check
    print(f"\n{'─'*78}")
    sections = {
        "Highlights": bool(update["highlights"]),
        "Metrics": bool(update["metrics"]),
        "Risks": bool(update["risks"]),
        "Next actions": bool(update["next_actions"]),
    }
    filled = sum(1 for v in sections.values() if v)
    total = len(sections)

    print(f"\n   📋 UPDATE COMPLETENESS: {filled}/{total} sections")
    for section, has_it in sections.items():
        emoji = "✅" if has_it else "⬜"
        print(f"   {emoji} {section}")

    if filled < total:
        missing = [s for s, v in sections.items() if not v]
        print(f"\n   💡 Consider adding: {', '.join(missing)}")

    print("\n" + "=" * 78)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Generate structured stakeholder updates with metrics, OKRs, "
                    "milestones, blockers, and next actions.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --project "Checkout Redesign" --period "Week of Jul 7" --status green \\
           --highlight "Shipped payment flow to 25%%" \\
           --metric "Conversion:3.2%%:3.5%%:up" \\
           --risk "Latency spikes during peak" \\
           --next "Expand rollout to 50%%"
  %(prog)s --json update.json --markdown update.md
        """,
    )

    parser.add_argument("--project", type=str, help="Project name")
    parser.add_argument("--period", type=str, default="", help="Reporting period")
    parser.add_argument("--author", type=str, default="", help="Update author")
    parser.add_argument("--status", type=str, default="green",
                        choices=["green", "yellow", "red", "blue"],
                        help="Overall status (default: green)")
    parser.add_argument("--summary", type=str, default="", help="Brief summary")

    parser.add_argument("--highlight", type=str, action="append", help="Key highlight")
    parser.add_argument("--metric", type=str, action="append",
                        help="Metric: 'Name:current:target[:direction]'")
    parser.add_argument("--risk", type=str, action="append", help="Risk item")
    parser.add_argument("--blocker", type=str, action="append", help="Blocker")
    parser.add_argument("--next", type=str, action="append", help="Next action")
    parser.add_argument("--ask", type=str, action="append", help="Ask / decision needed")

    parser.add_argument("--json", "-j", type=str, help="JSON file with update data")
    parser.add_argument("--markdown", type=str, help="Write Markdown output to file")
    parser.add_argument("--output", "-o", type=str, help="Write JSON results to file")
    args = parser.parse_args()

    update = None

    if args.json:
        try:
            update = load_json(args.json)
        except Exception as e:
            print(f"Error loading JSON: {e}", file=sys.stderr)
            return 1

    elif args.project:
        metrics = []
        if args.metric:
            for m_str in args.metric:
                try:
                    metrics.append(parse_metric_string(m_str))
                except ValueError as e:
                    print(f"Error: {e}", file=sys.stderr)
                    return 1

        update = build_update(
            project=args.project,
            period=args.period,
            author=args.author,
            overall_status=args.status,
            summary=args.summary,
            highlights=args.highlight,
            metrics=metrics,
            risks=args.risk,
            blockers=args.blocker,
            next_actions=args.next,
            asks=args.ask,
        )

    else:
        print("Error: provide --project or --json.", file=sys.stderr)
        parser.print_help(sys.stderr)
        return 1

    # Terminal report
    print_report(update)

    # Markdown output
    if args.markdown:
        md = generate_markdown(update)
        with open(args.markdown, "w", encoding="utf-8") as f:
            f.write(md)
        print(f"\n📄 Markdown saved to {args.markdown}")

    # JSON output
    if args.output:
        with open(args.output, "w") as f:
            json.dump(update, f, indent=2)
        print(f"\n📁 Results saved to {args.output}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
