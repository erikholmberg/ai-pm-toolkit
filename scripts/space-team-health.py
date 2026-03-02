#!/usr/bin/env python3
"""
SPACE Team Health Scorecard

Turn the SPACE framework into a repeatable team health check. Input scores for
Satisfaction, Performance, Activity, Communication, and Efficiency; get
overall health, weakest dimension, traffic lights, and focus-area suggestions.

Aligns with frameworks/space-framework.md. Use after retros, pulse surveys,
or when combining signals from velocity, cycle time, and DORA tools.

Usage:
    # Quick check (scores 1–5, default scale)
    python space-team-health.py --team "Platform Team" \\
        --satisfaction 4 --performance 3 --activity 4 --communication 3 --efficiency 4

    # 0–100 scale
    python space-team-health.py --team "Product Eng" --scale 100 \\
        --satisfaction 82 --performance 70 --activity 75 --communication 65 --efficiency 72

    # With notes per dimension
    python space-team-health.py --team "ML Team" \\
        --satisfaction 4 --performance 4 --activity 3 --communication 3 --efficiency 3 \\
        --note satisfaction "Survey: 8/10 enjoy work" \\
        --note efficiency "Cycle time up; WIP high"

    # From CSV (multiple teams or time points)
    python space-team-health.py --csv space-scores.csv

    # From JSON
    python space-team-health.py --json space.json

    # Markdown report
    python space-team-health.py --json space.json --markdown report.md

Scale:
    Default 1–5 (framework template). Use --scale 100 for 0–100.
    Green ≥80% equivalent, Yellow 60–79%, Red <60%.

CSV format:
    team,date,satisfaction,performance,activity,communication,efficiency,notes
    Platform Team,2025-08-01,4,3,4,3,4,"S: good. P: velocity dip."
    The generic "notes" column is used only for the satisfaction dimension when
    note_satisfaction is not present. Optional columns: note_satisfaction,
    note_performance, note_activity, note_communication, note_efficiency.

JSON format:
    {
      "team": "Platform Team",
      "date": "2025-08-01",
      "period": "Last 4 sprints",
      "scale": "1-5",
      "dimensions": {
        "satisfaction": 4,
        "performance": 3,
        "activity": 4,
        "communication": 3,
        "efficiency": 4
      },
      "notes": {
        "satisfaction": "Survey: 8/10",
        "efficiency": "Cycle time up; WIP high"
      }
    }

Requirements:
    None (stdlib only).
"""

import argparse
import csv
import json
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# SPACE dimensions and focus suggestions (from framework)
# ---------------------------------------------------------------------------

DIMENSIONS = [
    "satisfaction",
    "performance",
    "activity",
    "communication",
    "efficiency",
]

DIMENSION_LABELS = {
    "satisfaction": "Satisfaction",
    "performance": "Performance",
    "activity": "Activity",
    "communication": "Communication",
    "efficiency": "Efficiency",
}

DIMENSION_DESCRIPTIONS = {
    "satisfaction": "Well-being, sense of efficacy, fulfillment",
    "performance": "Outcomes & results — delivery, quality, user impact",
    "activity": "Counts of actions — commits, PRs, deployments, reviews",
    "communication": "Coordination & information flow",
    "efficiency": "Flow & focus — cycle time, WIP, focus time",
}

FOCUS_SUGGESTIONS = {
    "satisfaction": [
        "Include satisfaction in retro discussions; don't celebrate velocity at the cost of sustainability.",
        "Address workload and scope creep explicitly; protect focus time and discourage always-on culture.",
    ],
    "performance": [
        "Set realistic targets informed by capacity; celebrate outcomes (shipped, adopted) not just output (points).",
        "Investigate drops before increasing pressure; pair performance with satisfaction to avoid burnout risk.",
    ],
    "activity": [
        "Use activity to detect disengagement or bottleneck in reviews; don't optimize for activity alone.",
        "If activity is high but performance is flat, look at efficiency and focus.",
    ],
    "communication": [
        "Reduce meetings that don't create decisions or alignment; make dependencies explicit.",
        "Document decisions; create async-first defaults where possible.",
    ],
    "efficiency": [
        "Limit WIP; finish before starting; batch meetings and protect focus blocks.",
        "Reduce approval bottlenecks and unnecessary gates; use capacity planning to avoid overcommitment.",
    ],
}


def score_to_pct(value: float, scale_1_5: bool) -> float:
    """Normalize score to 0–100."""
    if scale_1_5:
        if value < 1 or value > 5:
            return max(0.0, min(100.0, value * 20.0))  # fallback
        return (value - 1) / 4 * 100  # 1→0, 5→100
    return max(0.0, min(100.0, float(value)))


def pct_to_health(pct: float) -> Tuple[str, str]:
    """Return (health_key, display_label). Green ≥80, Yellow 60–79, Red <60."""
    if pct >= 80:
        return "green", "🟢 Green"
    if pct >= 60:
        return "yellow", "🟡 Yellow"
    return "red", "🔴 Red"


def assess_dimension(name: str, raw_value: float, scale_1_5: bool) -> Dict[str, Any]:
    """Assess one SPACE dimension."""
    pct = score_to_pct(raw_value, scale_1_5)
    health_key, health_label = pct_to_health(pct)
    return {
        "name": name,
        "raw_value": raw_value,
        "pct": round(pct, 1),
        "health": health_key,
        "health_label": health_label,
        "description": DIMENSION_DESCRIPTIONS.get(name, ""),
    }


def build_scorecard(
    team: str,
    dimensions_raw: Dict[str, float],
    scale_1_5: bool = True,
    notes: Optional[Dict[str, str]] = None,
    date: Optional[str] = None,
    period: Optional[str] = None,
) -> Dict[str, Any]:
    """Build full SPACE scorecard."""
    if not date:
        date = datetime.now().strftime("%Y-%m-%d")

    assessed = {}
    for dim in DIMENSIONS:
        raw = dimensions_raw.get(dim)
        if raw is None:
            continue
        assessed[dim] = assess_dimension(dim, float(raw), scale_1_5)
        if notes and dim in notes and notes[dim]:
            assessed[dim]["note"] = notes[dim]

    if not assessed:
        return {
            "team": team,
            "date": date,
            "period": period,
            "scale": "1-5" if scale_1_5 else "0-100",
            "dimensions": {},
            "overall_pct": 0.0,
            "overall_health": "red",
            "overall_label": "🔴 Red",
            "weakest_dimension": None,
            "focus_suggestions": [],
            "error": "No dimension scores provided",
        }

    pcts = [a["pct"] for a in assessed.values()]
    overall_pct = sum(pcts) / len(pcts)
    overall_health, overall_label = pct_to_health(overall_pct)

    # Weakest dimension
    weakest_dim = min(assessed.keys(), key=lambda d: assessed[d]["pct"])
    weakest = assessed[weakest_dim]

    # Focus suggestions for weakest (and any red)
    focus = []
    seen = set()
    for dim in [weakest_dim] + [d for d in assessed if assessed[d]["health"] == "red" and d != weakest_dim]:
        if dim in seen:
            continue
        seen.add(dim)
        for suggestion in FOCUS_SUGGESTIONS.get(dim, []):
            focus.append({"dimension": dim, "suggestion": suggestion})

    return {
        "team": team,
        "date": date,
        "period": period,
        "scale": "1-5" if scale_1_5 else "0-100",
        "dimensions": assessed,
        "overall_pct": round(overall_pct, 1),
        "overall_health": overall_health,
        "overall_label": overall_label,
        "weakest_dimension": weakest_dim,
        "weakest_label": DIMENSION_LABELS.get(weakest_dim, weakest_dim),
        "weakest_pct": weakest["pct"],
        "focus_suggestions": focus,
        "red_count": sum(1 for a in assessed.values() if a["health"] == "red"),
        "yellow_count": sum(1 for a in assessed.values() if a["health"] == "yellow"),
        "green_count": sum(1 for a in assessed.values() if a["health"] == "green"),
    }


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def _col(fieldnames: List[str], *aliases: str) -> Optional[str]:
    lower_map = {f.lower().strip(): f for f in fieldnames}
    for alias in aliases:
        if alias.lower().strip() in lower_map:
            return lower_map[alias.lower().strip()]
    return None


def load_csv(path: str) -> List[Dict[str, Any]]:
    """Load one or more scorecards from CSV."""
    rows: List[Dict[str, Any]] = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fields = reader.fieldnames or []

        c_team = _col(fields, "team", "name", "team_name")
        c_date = _col(fields, "date", "assessment_date")
        c_sat = _col(fields, "satisfaction", "s")
        c_perf = _col(fields, "performance", "p")
        c_act = _col(fields, "activity", "a")
        c_comm = _col(fields, "communication", "c")
        c_eff = _col(fields, "efficiency", "e")
        c_notes = _col(fields, "notes", "note")
        c_note_sat = _col(fields, "note_satisfaction", "notes_satisfaction")
        c_note_perf = _col(fields, "note_performance", "notes_performance")
        c_note_act = _col(fields, "note_activity", "notes_activity")
        c_note_comm = _col(fields, "note_communication", "notes_communication")
        c_note_eff = _col(fields, "note_efficiency", "notes_efficiency")

        for row in reader:
            team = row.get(c_team or "team", "").strip()
            if not team:
                continue

            dims = {}
            if c_sat and row.get(c_sat, "").strip():
                try:
                    dims["satisfaction"] = float(row[c_sat].strip())
                except ValueError:
                    pass
            if c_perf and row.get(c_perf, "").strip():
                try:
                    dims["performance"] = float(row[c_perf].strip())
                except ValueError:
                    pass
            if c_act and row.get(c_act, "").strip():
                try:
                    dims["activity"] = float(row[c_act].strip())
                except ValueError:
                    pass
            if c_comm and row.get(c_comm, "").strip():
                try:
                    dims["communication"] = float(row[c_comm].strip())
                except ValueError:
                    pass
            if c_eff and row.get(c_eff, "").strip():
                try:
                    dims["efficiency"] = float(row[c_eff].strip())
                except ValueError:
                    pass

            if not dims:
                continue

            notes = {}
            for dim, c_note in [
                ("satisfaction", c_note_sat or c_notes),
                ("performance", c_note_perf),
                ("activity", c_note_act),
                ("communication", c_note_comm),
                ("efficiency", c_note_eff),
            ]:
                if c_note and row.get(c_note, "").strip():
                    notes[dim] = row[c_note].strip()

            sc = build_scorecard(
                team=team,
                dimensions_raw=dims,
                scale_1_5=True,
                notes=notes if notes else None,
                date=row.get(c_date or "date", "").strip() or None,
            )
            rows.append(sc)

    return rows


def load_json(path: str) -> Dict[str, Any]:
    """Load single scorecard from JSON."""
    with open(path, encoding="utf-8") as f:
        config = json.load(f)

    dims = config.get("dimensions", {})
    if not dims:
        dims = {
            "satisfaction": config.get("satisfaction"),
            "performance": config.get("performance"),
            "activity": config.get("activity"),
            "communication": config.get("communication"),
            "efficiency": config.get("efficiency"),
        }
    dims = {k: v for k, v in dims.items() if v is not None}

    scale = config.get("scale", "1-5")
    scale_1_5 = str(scale).lower() in ("1-5", "1_5", "5")

    return build_scorecard(
        team=config.get("team", "Team"),
        dimensions_raw=dims,
        scale_1_5=scale_1_5,
        notes=config.get("notes"),
        date=config.get("date"),
        period=config.get("period"),
    )


# ---------------------------------------------------------------------------
# Markdown
# ---------------------------------------------------------------------------

def generate_markdown(card: Dict[str, Any]) -> str:
    """Generate Markdown scorecard."""
    if card.get("error"):
        return f"# SPACE Team Health: {card.get('team', 'Team')}\n\n**Error:** {card['error']}\n"
    lines = []
    lines.append(f"# SPACE Team Health: {card['team']}")
    lines.append("")
    lines.append(f"**Date:** {card['date']}  ")
    if card.get("period"):
        lines.append(f"**Period:** {card['period']}  ")
    lines.append(f"**Overall:** {card['overall_label']} ({card['overall_pct']:.0f}%)  ")
    lines.append(f"**Focus area:** {card.get('weakest_label', '—')}  ")
    lines.append("")

    lines.append("## Dimensions")
    lines.append("")
    lines.append("| Dimension | Score | % | Health |")
    lines.append("|------------|-------|---|--------|")
    for dim in DIMENSIONS:
        if dim not in card["dimensions"]:
            continue
        d = card["dimensions"][dim]
        raw = d["raw_value"]
        scale = card.get("scale", "1-5")
        raw_str = f"{raw:.1f}" if scale == "0-100" else f"{int(raw)}/5"
        lines.append(f"| {DIMENSION_LABELS[dim]} | {raw_str} | {d['pct']:.0f}% | {d['health_label']} |")
    lines.append("")

    if card.get("focus_suggestions"):
        lines.append("## Focus suggestions")
        lines.append("")
        for fs in card["focus_suggestions"]:
            lines.append(f"- **{DIMENSION_LABELS.get(fs['dimension'], fs['dimension'])}:** {fs['suggestion']}")
        lines.append("")

    lines.append("---")
    lines.append(f"*SPACE framework — see frameworks/space-framework.md*")
    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Terminal report
# ---------------------------------------------------------------------------

def print_report(card: Dict[str, Any]) -> None:
    """Pretty-print one scorecard."""
    if card.get("error"):
        print(f"\n   ⚠️  {card['error']}\n")
        return

    print("\n" + "=" * 78)
    print("📊 SPACE TEAM HEALTH SCORECARD")
    print("=" * 78)

    print(f"\n   Team:   {card['team']}")
    print(f"   Date:   {card['date']}")
    if card.get("period"):
        print(f"   Period: {card['period']}")
    print(f"   Scale:  {card['scale']}")

    # Overall
    bar_w = 30
    filled = int(card["overall_pct"] / 100 * bar_w)
    bar = "█" * filled + "░" * (bar_w - filled)
    print(f"\n   Overall: [{bar}] {card['overall_pct']:.0f}%  {card['overall_label']}")

    # Summary counts
    print(f"\n   Summary: {card.get('green_count', 0)} green, {card.get('yellow_count', 0)} yellow, {card.get('red_count', 0)} red")
    print(f"   Focus area: {card['weakest_label']} ({card['weakest_pct']:.0f}%)")

    # Dimensions
    print(f"\n{'─'*78}")
    print(f"\n   DIMENSIONS:\n")
    print(f"   {'Dimension':<18} {'Score':>8} {'%':>6} {'Health':<14} Description")
    print(f"   {'─'*18} {'─'*8} {'─'*6} {'─'*14} {'─'*24}")

    scale = card.get("scale", "1-5")
    for dim in DIMENSIONS:
        if dim not in card["dimensions"]:
            continue
        d = card["dimensions"][dim]
        raw = d["raw_value"]
        raw_str = f"{raw:.0f}" if scale == "0-100" else f"{raw:.1f}/5"
        desc = (d["description"] or "")[:24]
        print(f"   {DIMENSION_LABELS[dim]:<18} {raw_str:>8} {d['pct']:>5.0f}% {d['health_label']:<14} {desc}")

    # Notes
    for dim in DIMENSIONS:
        if dim in card["dimensions"] and card["dimensions"][dim].get("note"):
            print(f"\n   Note ({DIMENSION_LABELS[dim]}): {card['dimensions'][dim]['note']}")

    # Focus suggestions
    if card.get("focus_suggestions"):
        print(f"\n{'─'*78}")
        print(f"\n   💡 FOCUS SUGGESTIONS (from SPACE framework):\n")
        for fs in card["focus_suggestions"]:
            print(f"   • {fs['suggestion']}")

    print(f"\n{'─'*78}")
    print(f"\n   Use with: velocity-trend-analyzer, cycle-lead-time-analyzer, dora-metrics-calculator")
    print(f"   Framework: frameworks/space-framework.md")
    print("\n" + "=" * 78)


def print_multi_report(cards: List[Dict[str, Any]]) -> None:
    """Print summary when multiple scorecards (e.g. from CSV)."""
    print("\n" + "=" * 78)
    print("📊 SPACE TEAM HEALTH — MULTIPLE ASSESSMENTS")
    print("=" * 78)
    print(f"\n   Total: {len(cards)} scorecard(s)\n")

    for i, card in enumerate(cards):
        if card.get("error"):
            print(f"   [{i+1}] {card.get('team', '?')}: Error — {card.get('error', '')}")
            continue
        overall = card["overall_label"]
        focus = card["weakest_label"]
        print(f"   [{i+1}] {card['team']} ({card['date']}): {overall} {card['overall_pct']:.0f}% — Focus: {focus}")

    print("\n" + "=" * 78)

    # If only one with data, print full report
    valid = [c for c in cards if not c.get("error") and c.get("dimensions")]
    if len(valid) == 1:
        print_report(valid[0])
    elif len(valid) > 1:
        print("\n   Use --output to export all; or run with a single team/JSON for full report.\n")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="SPACE team health scorecard — Satisfaction, Performance, "
                    "Activity, Communication, Efficiency. Repeatable check with focus suggestions.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --team "Platform" --satisfaction 4 --performance 3 --activity 4 --communication 3 --efficiency 4
  %(prog)s --team "Eng" --scale 100 --satisfaction 82 --performance 70 --activity 75 --communication 65 --efficiency 72
  %(prog)s --csv scores.csv
  %(prog)s --json space.json --markdown report.md
        """,
    )

    parser.add_argument("--team", type=str, default="Team", help="Team name")
    parser.add_argument("--date", type=str, help="Assessment date (YYYY-MM-DD)")
    parser.add_argument("--period", type=str, help="Period (e.g. 'Last 4 sprints')")
    parser.add_argument("--scale", type=str, default="1-5", choices=["1-5", "100"],
                        help="Score scale: 1-5 (default) or 100 (0-100)")

    parser.add_argument("--satisfaction", type=float, help="Satisfaction score")
    parser.add_argument("--performance", type=float, help="Performance score")
    parser.add_argument("--activity", type=float, help="Activity score")
    parser.add_argument("--communication", type=float, help="Communication score")
    parser.add_argument("--efficiency", type=float, help="Efficiency score")

    parser.add_argument("--note", type=str, action="append", nargs=2, metavar=("DIM", "TEXT"),
                        help="Note for dimension: --note satisfaction 'Survey 8/10'")

    parser.add_argument("--csv", "-c", type=str, help="CSV file (multiple rows)")
    parser.add_argument("--json", "-j", type=str, help="JSON file (single scorecard)")
    parser.add_argument("--markdown", type=str, help="Write Markdown to file")
    parser.add_argument("--output", "-o", type=str, help="Write JSON results to file")
    args = parser.parse_args()

    cards: List[Dict[str, Any]] = []
    single: Optional[Dict[str, Any]] = None

    if args.json:
        try:
            single = load_json(args.json)
            cards = [single]
        except Exception as e:
            print(f"Error loading JSON: {e}", file=sys.stderr)
            return 1

    elif args.csv:
        try:
            cards = load_csv(args.csv)
            if len(cards) == 1:
                single = cards[0]
            else:
                single = None
        except Exception as e:
            print(f"Error loading CSV: {e}", file=sys.stderr)
            return 1

    elif any([args.satisfaction is not None, args.performance is not None, args.activity is not None,
              args.communication is not None, args.efficiency is not None]):
        scale_1_5 = args.scale == "1-5"
        dims = {}
        if args.satisfaction is not None:
            dims["satisfaction"] = args.satisfaction
        if args.performance is not None:
            dims["performance"] = args.performance
        if args.activity is not None:
            dims["activity"] = args.activity
        if args.communication is not None:
            dims["communication"] = args.communication
        if args.efficiency is not None:
            dims["efficiency"] = args.efficiency

        notes = None
        if args.note:
            notes = {}
            for dim, text in args.note:
                dim_lower = dim.lower().strip()
                if dim_lower in DIMENSIONS:
                    notes[dim_lower] = text

        single = build_scorecard(
            team=args.team,
            dimensions_raw=dims,
            scale_1_5=scale_1_5,
            notes=notes,
            date=args.date,
            period=args.period,
        )
        cards = [single]
    else:
        print("Error: provide dimension scores (--satisfaction ...), or --csv, or --json.", file=sys.stderr)
        parser.print_help(sys.stderr)
        return 1

    # Report
    if len(cards) > 1:
        print_multi_report(cards)
        if single:
            print_report(single)
    else:
        print_report(cards[0])

    # Markdown
    if args.markdown and cards and not cards[0].get("error"):
        md = generate_markdown(cards[0])
        with open(args.markdown, "w", encoding="utf-8") as f:
            f.write(md)
        print(f"\n📄 Markdown saved to {args.markdown}")

    # JSON output
    if args.output:
        with open(args.output, "w") as f:
            if len(cards) == 1:
                json.dump(cards[0], f, indent=2)
            else:
                json.dump({"scorecards": cards}, f, indent=2)
        print(f"\n📁 Results saved to {args.output}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
