#!/usr/bin/env python3
"""
Decision Log / ADR Generator

Record, track, and generate Architecture Decision Records (ADRs) or product
decisions with structured context, options considered, rationale, trade-offs,
and consequences. Outputs Markdown or terminal reports.

Helps PMs maintain institutional memory, onboard new team members, and
revisit past decisions with full context.

Usage:
    # Quick inline decision
    python decision-log.py \\
        --title "Use PostgreSQL over DynamoDB" \\
        --status accepted \\
        --context "Need a primary datastore for user profiles and billing" \\
        --option "PostgreSQL:Strong consistency, mature ecosystem, team expertise:Higher ops burden" \\
        --option "DynamoDB:Serverless, auto-scaling:Eventual consistency, vendor lock-in" \\
        --option "MongoDB:Flexible schema, good for prototyping:Weaker transactions" \\
        --decision "PostgreSQL" \\
        --rationale "Team has deep Postgres expertise; strong consistency is critical for billing" \\
        --consequence "Must manage connection pooling and backups" \\
        --consequence "Schema migrations need careful planning" \\
        --owner "Platform Team" --date 2025-06-15

    # From JSON (batch / import)
    python decision-log.py --json decisions.json

    # From CSV
    python decision-log.py --csv decisions.csv

    # Generate Markdown ADR files
    python decision-log.py --json decisions.json --markdown-dir docs/adrs

JSON format:
    {
      "decisions": [
        {
          "id": "ADR-001",
          "title": "Use PostgreSQL over DynamoDB",
          "status": "accepted",
          "date": "2025-06-15",
          "owner": "Platform Team",
          "context": "Need a primary datastore for user profiles and billing",
          "options": [
            {
              "name": "PostgreSQL",
              "pros": ["Strong consistency", "Mature ecosystem"],
              "cons": ["Higher ops burden"]
            },
            {
              "name": "DynamoDB",
              "pros": ["Serverless", "Auto-scaling"],
              "cons": ["Eventual consistency", "Vendor lock-in"]
            }
          ],
          "decision": "PostgreSQL",
          "rationale": "Team expertise + billing requires strong consistency",
          "consequences": [
            "Must manage connection pooling",
            "Schema migrations need planning"
          ],
          "tags": ["infrastructure", "database"]
        }
      ]
    }

CSV format:
    id,title,status,date,owner,context,decision,rationale,consequences,tags
    ADR-001,Use PostgreSQL,accepted,2025-06-15,Platform,Need datastore...,PostgreSQL,Team expertise...,Pooling;Migrations,infra;db

Requirements:
    None (stdlib only).
"""

import argparse
import csv
import json
import os
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Decision model
# ---------------------------------------------------------------------------

VALID_STATUSES = {"proposed", "accepted", "deprecated", "superseded", "rejected"}
STATUS_EMOJI = {
    "proposed": "🟡",
    "accepted": "🟢",
    "deprecated": "🟠",
    "superseded": "🔵",
    "rejected": "🔴",
}


def build_decision(
    title: str,
    status: str = "proposed",
    date: Optional[str] = None,
    decision_id: Optional[str] = None,
    owner: str = "",
    context: str = "",
    options: Optional[List[Dict[str, Any]]] = None,
    decision: str = "",
    rationale: str = "",
    consequences: Optional[List[str]] = None,
    tags: Optional[List[str]] = None,
    superseded_by: Optional[str] = None,
) -> Dict[str, Any]:
    """Build a structured decision record."""
    status = status.lower().strip()
    if status not in VALID_STATUSES:
        status = "proposed"

    if date is None:
        date = datetime.now().strftime("%Y-%m-%d")

    return {
        "id": decision_id or "",
        "title": title,
        "status": status,
        "date": date,
        "owner": owner,
        "context": context,
        "options": options or [],
        "decision": decision,
        "rationale": rationale,
        "consequences": consequences or [],
        "tags": tags or [],
        "superseded_by": superseded_by,
    }


def validate_decisions(decisions: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Validate a set of decisions and flag issues."""
    issues: List[str] = []
    warnings: List[str] = []

    for d in decisions:
        if not d["title"]:
            issues.append(f"Decision '{d['id'] or '?'}' has no title")
        if not d["context"]:
            warnings.append(f"'{d['title']}' — no context documented")
        if not d["rationale"] and d["status"] == "accepted":
            warnings.append(f"'{d['title']}' — accepted but no rationale recorded")
        if not d["options"] and d["status"] == "accepted":
            warnings.append(f"'{d['title']}' — no alternatives documented")
        if not d["consequences"]:
            warnings.append(f"'{d['title']}' — no consequences listed")

    # Check for superseded chains
    ids = {d["id"] for d in decisions if d["id"]}
    for d in decisions:
        if d["superseded_by"] and d["superseded_by"] not in ids:
            warnings.append(f"'{d['title']}' superseded by '{d['superseded_by']}' which is not in the log")

    status_counts = {}
    for d in decisions:
        status_counts[d["status"]] = status_counts.get(d["status"], 0) + 1

    tag_counts: Dict[str, int] = {}
    for d in decisions:
        for t in d["tags"]:
            tag_counts[t] = tag_counts.get(t, 0) + 1

    return {
        "total": len(decisions),
        "status_counts": status_counts,
        "tag_counts": tag_counts,
        "issues": issues,
        "warnings": warnings,
    }


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def parse_option_string(s: str) -> Dict[str, Any]:
    """Parse 'Name:pro1,pro2:con1,con2' into an option dict."""
    parts = s.split(":")
    name = parts[0].strip()
    pros = [p.strip() for p in parts[1].split(",") if p.strip()] if len(parts) > 1 else []
    cons = [c.strip() for c in parts[2].split(",") if c.strip()] if len(parts) > 2 else []
    return {"name": name, "pros": pros, "cons": cons}


def _col(fieldnames: List[str], *aliases: str) -> Optional[str]:
    lower_map = {f.lower().strip(): f for f in fieldnames}
    for alias in aliases:
        if alias.lower().strip() in lower_map:
            return lower_map[alias.lower().strip()]
    return None


def load_csv(path: str) -> List[Dict[str, Any]]:
    """Load decisions from CSV."""
    decisions: List[Dict[str, Any]] = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fields = reader.fieldnames or []

        c_id = _col(fields, "id", "adr_id", "decision_id", "number")
        c_title = _col(fields, "title", "name", "decision_title")
        c_status = _col(fields, "status", "state")
        c_date = _col(fields, "date", "decided_date", "created")
        c_owner = _col(fields, "owner", "team", "decider", "author")
        c_context = _col(fields, "context", "background", "problem")
        c_decision = _col(fields, "decision", "chosen", "selected")
        c_rationale = _col(fields, "rationale", "reason", "justification", "why")
        c_consequences = _col(fields, "consequences", "impacts", "tradeoffs")
        c_tags = _col(fields, "tags", "categories", "labels")

        for row in reader:
            title = row.get(c_title or "title", "").strip()
            if not title:
                continue

            cons_raw = row.get(c_consequences or "consequences", "")
            cons_list = [c.strip() for c in cons_raw.split(";") if c.strip()]

            tags_raw = row.get(c_tags or "tags", "")
            tags_list = [t.strip() for t in tags_raw.split(";") if t.strip()]

            decisions.append(build_decision(
                title=title,
                status=row.get(c_status or "status", "proposed").strip(),
                date=row.get(c_date or "date", "").strip() or None,
                decision_id=row.get(c_id or "id", "").strip(),
                owner=row.get(c_owner or "owner", "").strip(),
                context=row.get(c_context or "context", "").strip(),
                decision=row.get(c_decision or "decision", "").strip(),
                rationale=row.get(c_rationale or "rationale", "").strip(),
                consequences=cons_list,
                tags=tags_list,
            ))

    return decisions


def load_json(path: str) -> List[Dict[str, Any]]:
    """Load decisions from JSON."""
    with open(path, encoding="utf-8") as f:
        config = json.load(f)

    decisions = []
    for d in config.get("decisions", []):
        decisions.append(build_decision(
            title=d.get("title", ""),
            status=d.get("status", "proposed"),
            date=d.get("date"),
            decision_id=d.get("id"),
            owner=d.get("owner", ""),
            context=d.get("context", ""),
            options=d.get("options", []),
            decision=d.get("decision", ""),
            rationale=d.get("rationale", ""),
            consequences=d.get("consequences", []),
            tags=d.get("tags", []),
            superseded_by=d.get("superseded_by"),
        ))

    return decisions


# ---------------------------------------------------------------------------
# Markdown ADR generation
# ---------------------------------------------------------------------------

def generate_markdown(d: Dict[str, Any]) -> str:
    """Generate a Markdown ADR from a decision record."""
    lines = []
    id_str = f"{d['id']}: " if d["id"] else ""
    lines.append(f"# {id_str}{d['title']}")
    lines.append("")
    lines.append(f"**Status:** {d['status'].capitalize()}  ")
    lines.append(f"**Date:** {d['date']}  ")
    if d["owner"]:
        lines.append(f"**Owner:** {d['owner']}  ")
    if d["tags"]:
        lines.append(f"**Tags:** {', '.join(d['tags'])}  ")
    if d["superseded_by"]:
        lines.append(f"**Superseded by:** {d['superseded_by']}  ")
    lines.append("")

    lines.append("## Context")
    lines.append("")
    lines.append(d["context"] or "_No context documented._")
    lines.append("")

    if d["options"]:
        lines.append("## Options Considered")
        lines.append("")
        for opt in d["options"]:
            lines.append(f"### {opt['name']}")
            lines.append("")
            if opt.get("pros"):
                lines.append("**Pros:**")
                for p in opt["pros"]:
                    lines.append(f"- {p}")
                lines.append("")
            if opt.get("cons"):
                lines.append("**Cons:**")
                for c in opt["cons"]:
                    lines.append(f"- {c}")
                lines.append("")

    lines.append("## Decision")
    lines.append("")
    lines.append(d["decision"] or "_No decision recorded._")
    lines.append("")

    lines.append("## Rationale")
    lines.append("")
    lines.append(d["rationale"] or "_No rationale documented._")
    lines.append("")

    if d["consequences"]:
        lines.append("## Consequences")
        lines.append("")
        for c in d["consequences"]:
            lines.append(f"- {c}")
        lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def print_report(
    decisions: List[Dict[str, Any]],
    validation: Dict[str, Any],
) -> None:
    """Pretty-print decision log."""
    print("\n" + "=" * 78)
    print("📝 DECISION LOG / ADR GENERATOR")
    print("=" * 78)

    # Summary
    print(f"\n   📊 SUMMARY:")
    print(f"   Total decisions: {validation['total']}")
    for status, count in sorted(validation["status_counts"].items()):
        emoji = STATUS_EMOJI.get(status, "⬜")
        print(f"   {emoji} {status.capitalize():<14} {count}")

    if validation["tag_counts"]:
        print(f"\n   Tags: {', '.join(f'{t} ({c})' for t, c in sorted(validation['tag_counts'].items(), key=lambda x: -x[1]))}")

    # Decision list
    print(f"\n{'─'*78}")
    print(f"\n📋 DECISION LOG:\n")

    for i, d in enumerate(decisions):
        emoji = STATUS_EMOJI.get(d["status"], "⬜")
        id_str = f"[{d['id']}] " if d["id"] else ""
        print(f"   {emoji} {id_str}{d['title']}")
        print(f"      Status: {d['status'].capitalize()}  |  Date: {d['date']}  |  Owner: {d['owner'] or '—'}")

        if d["context"]:
            ctx = d["context"][:80] + "..." if len(d["context"]) > 80 else d["context"]
            print(f"      Context: {ctx}")

        # Options (brief)
        if d["options"]:
            opt_names = [o["name"] for o in d["options"]]
            chosen = d["decision"]
            opt_display = []
            for name in opt_names:
                if name.lower() == chosen.lower():
                    opt_display.append(f"✅ {name}")
                else:
                    opt_display.append(f"  {name}")
            print(f"      Options: {' | '.join(opt_display)}")
        elif d["decision"]:
            print(f"      Decision: {d['decision']}")

        if d["rationale"]:
            rat = d["rationale"][:80] + "..." if len(d["rationale"]) > 80 else d["rationale"]
            print(f"      Rationale: {rat}")

        if d["consequences"]:
            print(f"      Consequences:")
            for c in d["consequences"][:3]:
                print(f"        → {c}")
            if len(d["consequences"]) > 3:
                print(f"        ... +{len(d['consequences']) - 3} more")

        if d["tags"]:
            print(f"      Tags: {', '.join(d['tags'])}")

        if d["superseded_by"]:
            print(f"      ⚠️  Superseded by: {d['superseded_by']}")

        print()

    # Detailed option comparison for decisions with options
    decisions_with_opts = [d for d in decisions if d["options"]]
    if decisions_with_opts:
        print(f"{'─'*78}")
        print(f"\n📐 OPTION COMPARISONS:\n")

        for d in decisions_with_opts:
            id_str = f"[{d['id']}] " if d["id"] else ""
            print(f"   {id_str}{d['title']}:")
            print(f"   {'Option':<20} {'Pros':>5} {'Cons':>5} {'Chosen'}")
            print(f"   {'─'*20} {'─'*5} {'─'*5} {'─'*8}")

            for opt in d["options"]:
                chosen = "  ✅" if opt["name"].lower() == d["decision"].lower() else ""
                print(f"   {opt['name'][:20]:<20} {len(opt.get('pros', [])):>5} {len(opt.get('cons', [])):>5} {chosen}")

            print()

    # Validation
    if validation["issues"] or validation["warnings"]:
        print(f"{'─'*78}")
        print(f"\n⚠️  VALIDATION:\n")
        for issue in validation["issues"]:
            print(f"   🔴 {issue}")
        for warn in validation["warnings"]:
            print(f"   🟡 {warn}")

    # Guidance
    print(f"{'─'*78}")
    print(f"\n💡 ADR BEST PRACTICES:")
    print(f"   • Always document context — future-you won't remember why")
    print(f"   • List at least 2 alternatives considered, even if obvious")
    print(f"   • Record consequences — what are the trade-offs you're accepting?")
    print(f"   • Use 'superseded' status instead of deleting old decisions")
    print(f"   • Review and update ADRs quarterly — are consequences playing out?")
    print(f"   • Tag decisions for easy filtering (infra, product, security, etc.)")
    print("\n" + "=" * 78)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Record and track Architecture Decision Records (ADRs) with context, "
                    "options, rationale, and consequences.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --title "Use Postgres" --status accepted --context "Need a DB" \\
           --option "Postgres:Mature,Strong consistency:Ops burden" \\
           --option "DynamoDB:Serverless:Vendor lock-in" \\
           --decision "Postgres" --rationale "Team expertise"
  %(prog)s --json decisions.json
  %(prog)s --csv decisions.csv --markdown-dir docs/adrs
        """,
    )

    # Inline
    parser.add_argument("--title", type=str, help="Decision title")
    parser.add_argument("--status", type=str, default="proposed",
                        choices=list(VALID_STATUSES),
                        help="Decision status (default: proposed)")
    parser.add_argument("--date", type=str, help="Decision date (YYYY-MM-DD)")
    parser.add_argument("--id", type=str, help="Decision ID (e.g. ADR-001)")
    parser.add_argument("--owner", type=str, default="", help="Decision owner / team")
    parser.add_argument("--context", type=str, default="", help="Problem context")
    parser.add_argument("--option", type=str, action="append",
                        help="Option: 'Name:pro1,pro2:con1,con2'")
    parser.add_argument("--decision", type=str, default="", help="Chosen option")
    parser.add_argument("--rationale", type=str, default="", help="Why this option was chosen")
    parser.add_argument("--consequence", type=str, action="append",
                        help="Consequence / trade-off accepted")
    parser.add_argument("--tag", type=str, action="append", help="Tag / category")

    # Batch
    parser.add_argument("--json", "-j", type=str, help="JSON file with decisions")
    parser.add_argument("--csv", "-c", type=str, help="CSV file with decisions")

    # Output
    parser.add_argument("--markdown-dir", type=str,
                        help="Generate Markdown ADR files in this directory")
    parser.add_argument("--output", "-o", type=str, help="Write JSON results to file")
    args = parser.parse_args()

    decisions: List[Dict[str, Any]] = []

    if args.json:
        try:
            decisions = load_json(args.json)
        except Exception as e:
            print(f"Error loading JSON: {e}", file=sys.stderr)
            return 1

    elif args.csv:
        try:
            decisions = load_csv(args.csv)
        except Exception as e:
            print(f"Error loading CSV: {e}", file=sys.stderr)
            return 1

    elif args.title:
        options = []
        if args.option:
            for opt_str in args.option:
                options.append(parse_option_string(opt_str))

        decisions.append(build_decision(
            title=args.title,
            status=args.status,
            date=args.date,
            decision_id=args.id,
            owner=args.owner,
            context=args.context,
            options=options,
            decision=args.decision,
            rationale=args.rationale,
            consequences=args.consequence or [],
            tags=args.tag or [],
        ))

    else:
        print("Error: provide --title, --json, or --csv.", file=sys.stderr)
        parser.print_help(sys.stderr)
        return 1

    # Validate
    validation = validate_decisions(decisions)

    # Report
    print_report(decisions, validation)

    # Generate markdown ADR files
    if args.markdown_dir:
        os.makedirs(args.markdown_dir, exist_ok=True)
        for i, d in enumerate(decisions):
            filename = d["id"].lower().replace(" ", "-") if d["id"] else f"adr-{i+1:03d}"
            filename = filename.replace("/", "-") + ".md"
            filepath = os.path.join(args.markdown_dir, filename)
            md = generate_markdown(d)
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(md)
            print(f"   📄 Written: {filepath}")

    # JSON output
    if args.output:
        report = {
            "decisions": decisions,
            "validation": validation,
        }
        with open(args.output, "w") as f:
            json.dump(report, f, indent=2)
        print(f"\n📁 Results saved to {args.output}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
