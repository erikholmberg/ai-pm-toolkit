#!/usr/bin/env python3
"""
Incident Postmortem Generator

Structure blameless incident postmortems with timeline, root cause analysis,
impact metrics, contributing factors, and action items. Outputs terminal
reports or Markdown documents. Pairs with error-budget and DORA tools.

Usage:
    # Quick inline postmortem
    python incident-postmortem.py \\
        --title "Payment API outage" --severity P1 \\
        --date 2025-07-10 --duration 47 \\
        --detected-by monitoring --ttd 5 --ttm 12 --ttr 47 \\
        --impact "2,300 failed transactions" \\
        --impact "Estimated revenue loss: $18,400" \\
        --impact "412 support tickets" \\
        --root-cause "Database connection pool exhaustion under load spike" \\
        --contributing "No connection pool monitoring alerts" \\
        --contributing "Load test coverage didn't include payment flow" \\
        --timeline "10:00:Load spike begins" \\
        --timeline "10:05:Monitoring alert fires" \\
        --timeline "10:12:On-call begins investigation" \\
        --timeline "10:25:Root cause identified" \\
        --timeline "10:35:Connection pool limit increased" \\
        --timeline "10:47:Service fully recovered" \\
        --action "Add connection pool utilization alerts:Platform:P1:2025-07-17" \\
        --action "Include payment flow in load tests:QA:P2:2025-07-24" \\
        --action "Implement connection pool auto-scaling:Platform:P2:2025-08-07"

    # From JSON
    python incident-postmortem.py --json postmortem.json

    # Generate Markdown
    python incident-postmortem.py --json postmortem.json --markdown postmortem.md

    Format for --timeline: "HH:MM:Description"
    Format for --action: "Description:Owner:Priority:Due"

JSON format:
    {
      "title": "Payment API outage",
      "severity": "P1",
      "date": "2025-07-10",
      "duration_minutes": 47,
      "detected_by": "monitoring",
      "ttd_minutes": 5,
      "ttm_minutes": 12,
      "ttr_minutes": 47,
      "impact": {
        "users_affected": 2300,
        "revenue_loss": 18400,
        "support_tickets": 412,
        "description": ["2,300 failed transactions", "$18,400 revenue loss"]
      },
      "root_cause": "Database connection pool exhaustion under load spike",
      "contributing_factors": [
        "No connection pool monitoring alerts",
        "Load test coverage didn't include payment flow"
      ],
      "timeline": [
        {"time": "10:00", "event": "Load spike begins"},
        {"time": "10:05", "event": "Monitoring alert fires"},
        {"time": "10:47", "event": "Service fully recovered"}
      ],
      "action_items": [
        {
          "description": "Add connection pool alerts",
          "owner": "Platform",
          "priority": "P1",
          "due_date": "2025-07-17",
          "status": "open"
        }
      ],
      "lessons_learned": ["Need better observability for connection pools"],
      "what_went_well": ["Fast detection via monitoring", "Clear escalation path"]
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
# Postmortem model
# ---------------------------------------------------------------------------

SEVERITY_EMOJI = {"P0": "🔴", "P1": "🟠", "P2": "🟡", "P3": "🟢", "P4": "🔵"}
SEVERITY_LABELS = {
    "P0": "Critical — total service outage",
    "P1": "High — major feature impacted",
    "P2": "Medium — degraded experience",
    "P3": "Low — minor impact",
    "P4": "Informational",
}


def build_postmortem(
    title: str,
    severity: str = "P2",
    date: Optional[str] = None,
    duration_minutes: int = 0,
    detected_by: str = "",
    ttd_minutes: Optional[int] = None,
    ttm_minutes: Optional[int] = None,
    ttr_minutes: Optional[int] = None,
    impact: Optional[List[str]] = None,
    users_affected: Optional[int] = None,
    revenue_loss: Optional[float] = None,
    root_cause: str = "",
    contributing_factors: Optional[List[str]] = None,
    timeline: Optional[List[Dict[str, str]]] = None,
    action_items: Optional[List[Dict[str, str]]] = None,
    lessons_learned: Optional[List[str]] = None,
    what_went_well: Optional[List[str]] = None,
    owner: str = "",
) -> Dict[str, Any]:
    """Build a structured postmortem."""
    severity = severity.upper().strip()
    if severity not in SEVERITY_EMOJI:
        severity = "P2"

    if date is None:
        date = datetime.now().strftime("%Y-%m-%d")

    # Response metrics assessment
    response_metrics = {}
    if ttd_minutes is not None:
        if ttd_minutes <= 5:
            response_metrics["ttd"] = {"value": ttd_minutes, "grade": "🟢 Excellent", "label": "Time to Detect"}
        elif ttd_minutes <= 15:
            response_metrics["ttd"] = {"value": ttd_minutes, "grade": "🟡 Acceptable", "label": "Time to Detect"}
        else:
            response_metrics["ttd"] = {"value": ttd_minutes, "grade": "🔴 Slow", "label": "Time to Detect"}

    if ttm_minutes is not None:
        if ttm_minutes <= 15:
            response_metrics["ttm"] = {"value": ttm_minutes, "grade": "🟢 Excellent", "label": "Time to Mitigate"}
        elif ttm_minutes <= 30:
            response_metrics["ttm"] = {"value": ttm_minutes, "grade": "🟡 Acceptable", "label": "Time to Mitigate"}
        else:
            response_metrics["ttm"] = {"value": ttm_minutes, "grade": "🔴 Slow", "label": "Time to Mitigate"}

    if ttr_minutes is not None:
        if ttr_minutes <= 30:
            response_metrics["ttr"] = {"value": ttr_minutes, "grade": "🟢 Excellent", "label": "Time to Resolve"}
        elif ttr_minutes <= 60:
            response_metrics["ttr"] = {"value": ttr_minutes, "grade": "🟡 Acceptable", "label": "Time to Resolve"}
        else:
            response_metrics["ttr"] = {"value": ttr_minutes, "grade": "🔴 Slow", "label": "Time to Resolve"}

    # Completeness check
    sections = {
        "Root cause": bool(root_cause),
        "Impact": bool(impact),
        "Timeline": bool(timeline),
        "Action items": bool(action_items),
        "Contributing factors": bool(contributing_factors),
        "Lessons learned": bool(lessons_learned),
    }
    completeness = sum(1 for v in sections.values() if v)
    completeness_pct = completeness / len(sections) * 100

    return {
        "title": title,
        "severity": severity,
        "date": date,
        "owner": owner,
        "duration_minutes": duration_minutes,
        "detected_by": detected_by,
        "ttd_minutes": ttd_minutes,
        "ttm_minutes": ttm_minutes,
        "ttr_minutes": ttr_minutes,
        "response_metrics": response_metrics,
        "impact": impact or [],
        "users_affected": users_affected,
        "revenue_loss": revenue_loss,
        "root_cause": root_cause,
        "contributing_factors": contributing_factors or [],
        "timeline": timeline or [],
        "action_items": action_items or [],
        "lessons_learned": lessons_learned or [],
        "what_went_well": what_went_well or [],
        "completeness": sections,
        "completeness_pct": round(completeness_pct, 0),
    }


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def parse_timeline_entry(s: str) -> Dict[str, str]:
    """Parse 'HH:MM:Description'."""
    parts = s.split(":", 2)
    if len(parts) >= 3 and parts[0].strip().isdigit():
        return {"time": f"{parts[0].strip()}:{parts[1].strip()}", "event": parts[2].strip()}
    return {"time": "", "event": s.strip()}


def parse_action_item(s: str) -> Dict[str, str]:
    """Parse 'Description:Owner:Priority:Due'."""
    parts = s.rsplit(":", 3)
    if len(parts) >= 4:
        return {
            "description": parts[0].strip(),
            "owner": parts[1].strip(),
            "priority": parts[2].strip().upper(),
            "due_date": parts[3].strip(),
            "status": "open",
        }
    elif len(parts) >= 2:
        return {
            "description": parts[0].strip(),
            "owner": parts[1].strip() if len(parts) > 1 else "",
            "priority": parts[2].strip().upper() if len(parts) > 2 else "P2",
            "due_date": "",
            "status": "open",
        }
    return {"description": s.strip(), "owner": "", "priority": "P2", "due_date": "", "status": "open"}


def load_json(path: str) -> Dict[str, Any]:
    """Load postmortem from JSON."""
    with open(path, encoding="utf-8") as f:
        config = json.load(f)

    impact_list = config.get("impact", {})
    if isinstance(impact_list, dict):
        impact_list = impact_list.get("description", [])
    elif not isinstance(impact_list, list):
        impact_list = [str(impact_list)]

    timeline = []
    for t in config.get("timeline", []):
        if isinstance(t, dict):
            timeline.append({"time": t.get("time", ""), "event": t.get("event", "")})
        elif isinstance(t, str):
            timeline.append(parse_timeline_entry(t))

    actions = []
    for a in config.get("action_items", []):
        if isinstance(a, dict):
            actions.append({
                "description": a.get("description", ""),
                "owner": a.get("owner", ""),
                "priority": a.get("priority", "P2").upper(),
                "due_date": a.get("due_date", ""),
                "status": a.get("status", "open"),
            })
        elif isinstance(a, str):
            actions.append(parse_action_item(a))

    return build_postmortem(
        title=config.get("title", ""),
        severity=config.get("severity", "P2"),
        date=config.get("date"),
        duration_minutes=config.get("duration_minutes", 0),
        detected_by=config.get("detected_by", ""),
        ttd_minutes=config.get("ttd_minutes"),
        ttm_minutes=config.get("ttm_minutes"),
        ttr_minutes=config.get("ttr_minutes"),
        impact=impact_list,
        users_affected=config.get("impact", {}).get("users_affected") if isinstance(config.get("impact"), dict) else None,
        revenue_loss=config.get("impact", {}).get("revenue_loss") if isinstance(config.get("impact"), dict) else None,
        root_cause=config.get("root_cause", ""),
        contributing_factors=config.get("contributing_factors", []),
        timeline=timeline,
        action_items=actions,
        lessons_learned=config.get("lessons_learned", []),
        what_went_well=config.get("what_went_well", []),
        owner=config.get("owner", ""),
    )


# ---------------------------------------------------------------------------
# Markdown generation
# ---------------------------------------------------------------------------

def generate_markdown(pm: Dict[str, Any]) -> str:
    """Generate Markdown postmortem document."""
    lines = []
    sev_emoji = SEVERITY_EMOJI.get(pm["severity"], "⬜")

    lines.append(f"# {sev_emoji} Incident Postmortem: {pm['title']}")
    lines.append("")
    lines.append(f"**Date:** {pm['date']}  ")
    lines.append(f"**Severity:** {pm['severity']} — {SEVERITY_LABELS.get(pm['severity'], '')}  ")
    lines.append(f"**Duration:** {pm['duration_minutes']} minutes  ")
    if pm["owner"]:
        lines.append(f"**Owner:** {pm['owner']}  ")
    if pm["detected_by"]:
        lines.append(f"**Detected by:** {pm['detected_by']}  ")
    lines.append("")

    if pm["response_metrics"]:
        lines.append("## Response Metrics")
        lines.append("")
        lines.append("| Metric | Value | Grade |")
        lines.append("|--------|-------|-------|")
        for key, m in pm["response_metrics"].items():
            lines.append(f"| {m['label']} | {m['value']} min | {m['grade']} |")
        lines.append("")

    if pm["impact"]:
        lines.append("## Impact")
        lines.append("")
        for i in pm["impact"]:
            lines.append(f"- {i}")
        lines.append("")

    if pm["timeline"]:
        lines.append("## Timeline")
        lines.append("")
        lines.append("| Time | Event |")
        lines.append("|------|-------|")
        for t in pm["timeline"]:
            lines.append(f"| {t['time']} | {t['event']} |")
        lines.append("")

    lines.append("## Root Cause")
    lines.append("")
    lines.append(pm["root_cause"] or "_Not yet identified._")
    lines.append("")

    if pm["contributing_factors"]:
        lines.append("## Contributing Factors")
        lines.append("")
        for cf in pm["contributing_factors"]:
            lines.append(f"- {cf}")
        lines.append("")

    if pm["action_items"]:
        lines.append("## Action Items")
        lines.append("")
        lines.append("| Action | Owner | Priority | Due | Status |")
        lines.append("|--------|-------|----------|-----|--------|")
        for a in pm["action_items"]:
            status = a.get("status", "open")
            check = "✅" if status == "done" else "⬜"
            lines.append(f"| {a['description']} | {a['owner']} | {a['priority']} | {a['due_date']} | {check} {status} |")
        lines.append("")

    if pm["lessons_learned"]:
        lines.append("## Lessons Learned")
        lines.append("")
        for ll in pm["lessons_learned"]:
            lines.append(f"- {ll}")
        lines.append("")

    if pm["what_went_well"]:
        lines.append("## What Went Well")
        lines.append("")
        for w in pm["what_went_well"]:
            lines.append(f"- {w}")
        lines.append("")

    lines.append("---")
    lines.append(f"*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}*")
    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Terminal report
# ---------------------------------------------------------------------------

def print_report(pm: Dict[str, Any]) -> None:
    """Pretty-print incident postmortem."""
    sev_emoji = SEVERITY_EMOJI.get(pm["severity"], "⬜")
    sev_label = SEVERITY_LABELS.get(pm["severity"], "")

    print("\n" + "=" * 78)
    print("🚨 INCIDENT POSTMORTEM")
    print("=" * 78)

    print(f"\n   {sev_emoji} {pm['title'].upper()}")
    print(f"   Severity:     {pm['severity']} — {sev_label}")
    print(f"   Date:         {pm['date']}")
    print(f"   Duration:     {pm['duration_minutes']} minutes")
    if pm["owner"]:
        print(f"   Owner:        {pm['owner']}")
    if pm["detected_by"]:
        print(f"   Detected by:  {pm['detected_by']}")

    # Response metrics
    if pm["response_metrics"]:
        print(f"\n{'─'*78}")
        print(f"\n   ⏱️  RESPONSE METRICS:\n")
        for key, m in pm["response_metrics"].items():
            bar_max = 60
            bar_filled = min(15, int(m["value"] / bar_max * 15))
            bar = "█" * bar_filled + "░" * (15 - bar_filled)
            print(f"   {m['label']:<22} {bar} {m['value']:>3} min  {m['grade']}")

    # Impact
    if pm["impact"]:
        print(f"\n{'─'*78}")
        print(f"\n   💥 IMPACT:\n")
        for i in pm["impact"]:
            print(f"   • {i}")
        if pm["users_affected"]:
            print(f"\n   Users affected:  {pm['users_affected']:,}")
        if pm["revenue_loss"]:
            print(f"   Revenue loss:    ${pm['revenue_loss']:,.2f}")

    # Timeline
    if pm["timeline"]:
        print(f"\n{'─'*78}")
        print(f"\n   📅 TIMELINE:\n")
        for i, t in enumerate(pm["timeline"]):
            connector = "│" if i < len(pm["timeline"]) - 1 else "└"
            time_str = t["time"] if t["time"] else "     "
            print(f"   {time_str}  {connector}── {t['event']}")

    # Root cause
    print(f"\n{'─'*78}")
    print(f"\n   🔍 ROOT CAUSE:\n")
    if pm["root_cause"]:
        print(f"   {pm['root_cause']}")
    else:
        print(f"   ⚠️  Not yet identified")

    # Contributing factors
    if pm["contributing_factors"]:
        print(f"\n{'─'*78}")
        print(f"\n   🔗 CONTRIBUTING FACTORS:\n")
        for cf in pm["contributing_factors"]:
            print(f"   • {cf}")

    # Action items
    if pm["action_items"]:
        print(f"\n{'─'*78}")
        print(f"\n   ✅ ACTION ITEMS:\n")
        print(f"   {'#':<3} {'Action':<34} {'Owner':<12} {'Pri':>4} {'Due':>12} {'Status'}")
        print(f"   {'─'*3} {'─'*34} {'─'*12} {'─'*4} {'─'*12} {'─'*8}")

        for i, a in enumerate(pm["action_items"]):
            status_icon = "✅" if a.get("status") == "done" else "⬜"
            print(
                f"   {i+1:<3} {a['description'][:34]:<34} "
                f"{a['owner'][:12]:<12} "
                f"{a['priority']:>4} "
                f"{a['due_date']:>12} "
                f"{status_icon} {a.get('status', 'open')}"
            )

        open_count = sum(1 for a in pm["action_items"] if a.get("status", "open") != "done")
        done_count = len(pm["action_items"]) - open_count
        print(f"\n   Progress: {done_count}/{len(pm['action_items'])} complete")

    # Lessons learned
    if pm["lessons_learned"]:
        print(f"\n{'─'*78}")
        print(f"\n   📚 LESSONS LEARNED:\n")
        for ll in pm["lessons_learned"]:
            print(f"   • {ll}")

    # What went well
    if pm["what_went_well"]:
        print(f"\n{'─'*78}")
        print(f"\n   🌟 WHAT WENT WELL:\n")
        for w in pm["what_went_well"]:
            print(f"   • {w}")

    # Completeness
    print(f"\n{'─'*78}")
    print(f"\n   📋 POSTMORTEM COMPLETENESS: {pm['completeness_pct']:.0f}%\n")
    for section, has_it in pm["completeness"].items():
        icon = "✅" if has_it else "⬜"
        print(f"   {icon} {section}")

    if pm["completeness_pct"] < 100:
        missing = [s for s, v in pm["completeness"].items() if not v]
        print(f"\n   💡 Missing: {', '.join(missing)}")

    # Guidance
    print(f"\n{'─'*78}")
    print(f"\n💡 POSTMORTEM BEST PRACTICES:")
    print(f"   • Keep it blameless — focus on systems, not individuals")
    print(f"   • Every action item needs an owner, priority, and due date")
    print(f"   • Review action items weekly until all are closed")
    print(f"   • Share postmortem with the broader team within 48 hours")
    print(f"   • Track TTD/TTM/TTR trends across incidents to improve response")
    print("\n" + "=" * 78)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Generate structured blameless incident postmortems with timeline, "
                    "root cause, impact, and action items.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --title "API outage" --severity P1 --duration 47 --ttd 5 --ttm 12 --ttr 47 \\
           --root-cause "Connection pool exhaustion" \\
           --timeline "10:00:Load spike" --timeline "10:47:Recovered" \\
           --action "Add alerts:Platform:P1:2025-07-17"
  %(prog)s --json postmortem.json --markdown postmortem.md
        """,
    )

    parser.add_argument("--title", type=str, help="Incident title")
    parser.add_argument("--severity", type=str, default="P2",
                        choices=["P0", "P1", "P2", "P3", "P4"],
                        help="Severity level (default: P2)")
    parser.add_argument("--date", type=str, help="Incident date (YYYY-MM-DD)")
    parser.add_argument("--duration", type=int, default=0, help="Duration in minutes")
    parser.add_argument("--owner", type=str, default="", help="Postmortem owner")
    parser.add_argument("--detected-by", type=str, default="",
                        help="How detected (monitoring, user, engineer)")
    parser.add_argument("--ttd", type=int, help="Time to Detect (minutes)")
    parser.add_argument("--ttm", type=int, help="Time to Mitigate (minutes)")
    parser.add_argument("--ttr", type=int, help="Time to Resolve (minutes)")
    parser.add_argument("--impact", type=str, action="append", help="Impact description")
    parser.add_argument("--root-cause", type=str, default="", help="Root cause")
    parser.add_argument("--contributing", type=str, action="append", help="Contributing factor")
    parser.add_argument("--timeline", type=str, action="append",
                        help="Timeline entry: 'HH:MM:Description'")
    parser.add_argument("--action", type=str, action="append",
                        help="Action item: 'Description:Owner:Priority:Due'")
    parser.add_argument("--lesson", type=str, action="append", help="Lesson learned")
    parser.add_argument("--went-well", type=str, action="append", help="What went well")

    parser.add_argument("--json", "-j", type=str, help="JSON file with postmortem data")
    parser.add_argument("--markdown", type=str, help="Write Markdown output to file")
    parser.add_argument("--output", "-o", type=str, help="Write JSON results to file")
    args = parser.parse_args()

    pm = None

    if args.json:
        try:
            pm = load_json(args.json)
        except Exception as e:
            print(f"Error loading JSON: {e}", file=sys.stderr)
            return 1

    elif args.title:
        timeline = []
        if args.timeline:
            for t_str in args.timeline:
                timeline.append(parse_timeline_entry(t_str))

        actions = []
        if args.action:
            for a_str in args.action:
                actions.append(parse_action_item(a_str))

        pm = build_postmortem(
            title=args.title,
            severity=args.severity,
            date=args.date,
            duration_minutes=args.duration,
            detected_by=args.detected_by,
            ttd_minutes=args.ttd,
            ttm_minutes=args.ttm,
            ttr_minutes=args.ttr,
            impact=args.impact,
            root_cause=args.root_cause,
            contributing_factors=args.contributing,
            timeline=timeline,
            action_items=actions,
            lessons_learned=args.lesson,
            what_went_well=args.went_well,
            owner=args.owner,
        )
    else:
        print("Error: provide --title or --json.", file=sys.stderr)
        parser.print_help(sys.stderr)
        return 1

    # Report
    print_report(pm)

    # Markdown
    if args.markdown:
        md = generate_markdown(pm)
        with open(args.markdown, "w", encoding="utf-8") as f:
            f.write(md)
        print(f"\n📄 Markdown saved to {args.markdown}")

    # JSON output
    if args.output:
        with open(args.output, "w") as f:
            json.dump(pm, f, indent=2)
        print(f"\n📁 Results saved to {args.output}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
