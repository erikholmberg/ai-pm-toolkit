#!/usr/bin/env python3
"""
Competitive Feature Matrix

Build a feature-level competitive analysis from a CSV of competitors × features.
Outputs gap analysis, parity scores, differentiation map, and identifies where
you lead, match, or trail the market.

Usage:
    # From CSV
    python competitive-feature-matrix.py --csv features.csv --us "Acme AI"

    # Specify scoring mode
    python competitive-feature-matrix.py --csv features.csv --us "Acme AI" --scoring binary

    # Export as Markdown
    python competitive-feature-matrix.py --csv features.csv --us "Acme AI" --markdown report.md

CSV format (header row required):
    feature,category,Acme AI,Competitor A,Competitor B,Competitor C
    SSO / SAML,Security,3,3,2,0
    Custom Dashboards,Analytics,2,3,3,1
    API Access,Platform,3,2,1,3
    Multi-language,AI,3,1,0,2
    ...

    First column: feature name
    Optional second column: category (for grouping)
    Remaining columns: one per competitor (including your product)

Scoring modes:
    numeric  (default): 0-3 scale (0=none, 1=basic, 2=good, 3=best-in-class)
    binary:             0/1 (has it or not)
    text:               values like "yes","no","partial","planned" (auto-mapped to 0-3)

Requirements:
    None (stdlib only).
"""

import argparse
import csv
import json
import sys
from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Text-to-score mapping
# ---------------------------------------------------------------------------

TEXT_SCORE_MAP = {
    # Positive
    "yes": 3, "y": 3, "true": 3, "full": 3, "complete": 3, "best": 3, "advanced": 3,
    "good": 2, "partial": 2, "basic": 2, "limited": 2, "moderate": 2,
    "planned": 1, "beta": 1, "alpha": 1, "preview": 1, "roadmap": 1, "upcoming": 1,
    # Negative
    "no": 0, "n": 0, "false": 0, "none": 0, "missing": 0, "n/a": 0, "na": 0, "": 0, "-": 0,
}

SCORE_LABELS = {0: "None", 1: "Basic", 2: "Good", 3: "Best"}
SCORE_EMOJI = {0: "⬜", 1: "🟨", 2: "🟩", 3: "🟢"}


def text_to_score(val: str) -> int:
    """Convert text or numeric value to 0-3 score."""
    val = val.strip().lower()
    if val in TEXT_SCORE_MAP:
        return TEXT_SCORE_MAP[val]
    try:
        n = float(val)
        return max(0, min(3, int(round(n))))
    except ValueError:
        return 0


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_csv(path: str, scoring: str = "numeric") -> Tuple[List[Dict[str, Any]], List[str], Optional[str]]:
    """
    Load feature matrix from CSV.
    Returns (features_list, competitor_names, category_column_name).
    """
    features: List[Dict[str, Any]] = []
    competitors: List[str] = []
    category_col: Optional[str] = None

    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fields = reader.fieldnames or []

        if not fields:
            raise ValueError("CSV has no headers")

        feature_col = fields[0]

        # Detect category column
        if len(fields) > 2 and fields[1].lower().strip() in (
            "category", "group", "area", "type", "domain", "pillar"
        ):
            category_col = fields[1]
            competitors = fields[2:]
        else:
            competitors = fields[1:]

        for row in reader:
            feature_name = row.get(feature_col, "").strip()
            if not feature_name:
                continue

            category = row.get(category_col, "General").strip() if category_col else "General"
            scores: Dict[str, int] = {}

            for comp in competitors:
                raw = row.get(comp, "").strip()
                if scoring == "binary":
                    scores[comp] = 1 if text_to_score(raw) > 0 else 0
                else:
                    scores[comp] = text_to_score(raw)

            features.append({
                "feature": feature_name,
                "category": category,
                "scores": scores,
            })

    return features, competitors, category_col


# ---------------------------------------------------------------------------
# Analysis
# ---------------------------------------------------------------------------

def analyze_matrix(
    features: List[Dict[str, Any]],
    competitors: List[str],
    us: str,
) -> Dict[str, Any]:
    """Analyze the competitive matrix and produce insights."""
    if us not in competitors:
        close = [c for c in competitors if us.lower() in c.lower()]
        if close:
            us = close[0]
        else:
            raise ValueError(f"'{us}' not found in competitors: {', '.join(competitors)}")

    others = [c for c in competitors if c != us]
    max_score = 3

    # Per-feature analysis
    feature_analysis: List[Dict[str, Any]] = []
    for f in features:
        our_score = f["scores"].get(us, 0)
        other_scores = [f["scores"].get(c, 0) for c in others]
        market_max = max(other_scores) if other_scores else 0
        market_avg = sum(other_scores) / len(other_scores) if other_scores else 0

        if our_score > market_max:
            position = "Lead"
        elif our_score == market_max and our_score > 0:
            position = "Parity"
        elif our_score > 0:
            position = "Trail"
        else:
            position = "Gap"

        gap = our_score - market_max

        feature_analysis.append({
            "feature": f["feature"],
            "category": f["category"],
            "our_score": our_score,
            "market_max": market_max,
            "market_avg": round(market_avg, 1),
            "gap": gap,
            "position": position,
            "scores": f["scores"],
        })

    # Category-level analysis
    categories: Dict[str, List[Dict]] = defaultdict(list)
    for fa in feature_analysis:
        categories[fa["category"]].append(fa)

    category_analysis: Dict[str, Dict[str, Any]] = {}
    for cat, cat_features in categories.items():
        our_total = sum(f["our_score"] for f in cat_features)
        our_max_possible = len(cat_features) * max_score
        our_pct = our_total / our_max_possible * 100 if our_max_possible > 0 else 0

        category_analysis[cat] = {
            "n_features": len(cat_features),
            "our_score": our_total,
            "max_possible": our_max_possible,
            "our_pct": round(our_pct, 1),
            "leads": sum(1 for f in cat_features if f["position"] == "Lead"),
            "parity": sum(1 for f in cat_features if f["position"] == "Parity"),
            "trails": sum(1 for f in cat_features if f["position"] == "Trail"),
            "gaps": sum(1 for f in cat_features if f["position"] == "Gap"),
        }

    # Competitor parity scores (% of features where we match or exceed)
    competitor_parity: Dict[str, Dict[str, Any]] = {}
    for comp in others:
        wins = sum(1 for f in feature_analysis if f["scores"].get(us, 0) > f["scores"].get(comp, 0))
        ties = sum(1 for f in feature_analysis if f["scores"].get(us, 0) == f["scores"].get(comp, 0))
        losses = sum(1 for f in feature_analysis if f["scores"].get(us, 0) < f["scores"].get(comp, 0))
        total = len(feature_analysis)

        competitor_parity[comp] = {
            "wins": wins,
            "ties": ties,
            "losses": losses,
            "win_rate": round(wins / total * 100, 1) if total > 0 else 0,
            "parity_rate": round((wins + ties) / total * 100, 1) if total > 0 else 0,
        }

    # Overall stats
    total_features = len(feature_analysis)
    positions = defaultdict(int)
    for fa in feature_analysis:
        positions[fa["position"]] += 1

    # Our total score vs competitors
    our_total = sum(fa["our_score"] for fa in feature_analysis)
    competitor_totals = {}
    for comp in others:
        competitor_totals[comp] = sum(fa["scores"].get(comp, 0) for fa in feature_analysis)

    return {
        "us": us,
        "competitors": others,
        "total_features": total_features,
        "our_total_score": our_total,
        "max_possible_score": total_features * max_score,
        "our_coverage_pct": round(our_total / (total_features * max_score) * 100, 1) if total_features > 0 else 0,
        "competitor_totals": competitor_totals,
        "positions": dict(positions),
        "feature_analysis": feature_analysis,
        "category_analysis": category_analysis,
        "competitor_parity": competitor_parity,
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


def _heatmap_row(scores: Dict[str, int], competitors: List[str]) -> str:
    """Render a row of emoji scores."""
    return " ".join(SCORE_EMOJI.get(scores.get(c, 0), "⬜") for c in competitors)


def print_report(analysis: Dict[str, Any]) -> None:
    """Pretty-print competitive analysis."""
    us = analysis["us"]
    others = analysis["competitors"]
    all_comps = [us] + others
    fa_list = analysis["feature_analysis"]

    print("\n" + "=" * 78)
    print("🏁 COMPETITIVE FEATURE MATRIX")
    print("=" * 78)

    # Overview
    print(f"\n📋 OVERVIEW:")
    print(f"   • Your product:     {us}")
    print(f"   • Competitors:      {', '.join(others)}")
    print(f"   • Features scored:  {analysis['total_features']}")
    print(f"   • Your coverage:    {analysis['our_coverage_pct']:.0f}% ({analysis['our_total_score']}/{analysis['max_possible_score']})")

    # Position summary
    pos = analysis["positions"]
    total = analysis["total_features"]
    print(f"\n📊 COMPETITIVE POSITION:")
    for position, emoji in [("Lead", "🟢"), ("Parity", "🟡"), ("Trail", "🟠"), ("Gap", "🔴")]:
        count = pos.get(position, 0)
        pct = count / total * 100 if total > 0 else 0
        bar = _bar(count, total, 20)
        print(f"   {emoji} {position:<8} {count:>3} ({pct:>4.0f}%)  {bar}")

    # Score leaderboard
    print(f"\n🏆 TOTAL SCORE LEADERBOARD:")
    all_scores = {us: analysis["our_total_score"]}
    all_scores.update(analysis["competitor_totals"])
    ranked = sorted(all_scores.items(), key=lambda x: -x[1])
    max_score = ranked[0][1] if ranked else 1
    our_rank = next(i + 1 for i, (name, _) in enumerate(ranked) if name == us)

    for rank, (name, score) in enumerate(ranked, 1):
        pct = score / analysis["max_possible_score"] * 100 if analysis["max_possible_score"] > 0 else 0
        bar = _bar(score, max_score, 25)
        marker = " ← you" if name == us else ""
        medal = "🥇" if rank == 1 else "🥈" if rank == 2 else "🥉" if rank == 3 else f" {rank}."
        print(f"   {medal} {name[:18]:<18} {bar} {score:>4} ({pct:.0f}%){marker}")

    # Head-to-head parity
    print(f"\n🤝 HEAD-TO-HEAD vs. {us}:")
    print(f"   {'Competitor':<20} {'Wins':>6} {'Ties':>6} {'Loss':>6} {'Parity%':>8}")
    print(f"   {'─'*20} {'─'*6} {'─'*6} {'─'*6} {'─'*8}")
    for comp, p in analysis["competitor_parity"].items():
        print(f"   {comp[:20]:<20} {p['wins']:>6} {p['ties']:>6} {p['losses']:>6} {p['parity_rate']:>7.0f}%")

    # Category breakdown
    if len(analysis["category_analysis"]) > 1:
        print(f"\n📂 CATEGORY BREAKDOWN:")
        print(f"   {'Category':<20} {'Score':>8} {'Lead':>5} {'Par':>5} {'Trail':>5} {'Gap':>5}")
        print(f"   {'─'*20} {'─'*8} {'─'*5} {'─'*5} {'─'*5} {'─'*5}")
        for cat, ca in sorted(analysis["category_analysis"].items()):
            score_str = f"{ca['our_score']}/{ca['max_possible']} ({ca['our_pct']:.0f}%)"
            print(f"   {cat[:20]:<20} {score_str:>8} {ca['leads']:>5} {ca['parity']:>5} {ca['trails']:>5} {ca['gaps']:>5}")

    # Feature heatmap
    # Truncate competitor names for header
    short_names = [c[:10] for c in all_comps]
    header = "   " + f"{'Feature':<24} " + " ".join(f"{s:^4}" for s in short_names) + "  Position"
    sep = "   " + "─" * 24 + " " + " ".join("─" * 4 for _ in all_comps) + "  ─────────"

    print(f"\n🗺️  FEATURE HEATMAP:")
    print(header)
    print(sep)

    current_cat = None
    for fa in sorted(fa_list, key=lambda x: (x["category"], -x["our_score"])):
        if fa["category"] != current_cat:
            if current_cat is not None:
                print()
            current_cat = fa["category"]
            if len(analysis["category_analysis"]) > 1:
                print(f"   [{current_cat}]")

        emojis = " ".join(
            f"{SCORE_EMOJI.get(fa['scores'].get(c, 0), '⬜'):^4}" for c in all_comps
        )
        pos_emoji = {"Lead": "🟢", "Parity": "🟡", "Trail": "🟠", "Gap": "🔴"}.get(fa["position"], "⚪")
        print(f"   {fa['feature'][:24]:<24} {emojis}  {pos_emoji} {fa['position']}")

    print(f"\n   Legend: ⬜ None  🟨 Basic  🟩 Good  🟢 Best-in-class")

    # Biggest gaps (where we trail the most)
    gaps = sorted([f for f in fa_list if f["gap"] < 0], key=lambda x: x["gap"])
    if gaps:
        print(f"\n🔴 BIGGEST GAPS (where you trail the market):")
        for f in gaps[:8]:
            leaders = [c for c in others if f["scores"].get(c, 0) == f["market_max"]]
            leader_str = ", ".join(leaders[:2])
            print(f"   • {f['feature']}: you={f['our_score']}, market best={f['market_max']} ({leader_str})")

    # Differentiators (where we lead)
    leads = sorted([f for f in fa_list if f["position"] == "Lead"], key=lambda x: -x["gap"])
    if leads:
        print(f"\n🟢 DIFFERENTIATORS (where you lead):")
        for f in leads[:8]:
            print(f"   • {f['feature']}: you={f['our_score']}, market best={f['market_max']}")

    # Recommendations
    print(f"\n💡 STRATEGIC RECOMMENDATIONS:")
    if gaps:
        critical_gaps = [f for f in gaps if f["market_max"] == 3 and f["our_score"] == 0]
        if critical_gaps:
            names = ", ".join(f["feature"] for f in critical_gaps[:3])
            print(f"   • 🔴 Critical gaps (competitor best, you have nothing): {names}")

        table_stakes = [f for f in fa_list if f["position"] in ("Trail", "Gap") and
                        sum(1 for c in others if f["scores"].get(c, 0) >= 2) >= len(others) * 0.5]
        if table_stakes:
            names = ", ".join(f["feature"] for f in table_stakes[:3])
            print(f"   • 🟡 Table stakes to close (most competitors have these): {names}")

    if leads:
        print(f"   • 🟢 Protect and promote your {len(leads)} differentiator{'s' if len(leads) > 1 else ''}")

    parity_features = [f for f in fa_list if f["position"] == "Parity"]
    if parity_features:
        invest_candidates = [f for f in parity_features if f["our_score"] < 3]
        if invest_candidates:
            names = ", ".join(f["feature"] for f in invest_candidates[:3])
            print(f"   • 🟡 Parity features to invest in for differentiation: {names}")

    print(f"\n   Your rank: #{our_rank} of {len(all_comps)} competitors")
    print("\n" + "=" * 78)


# ---------------------------------------------------------------------------
# Markdown export
# ---------------------------------------------------------------------------

def generate_markdown(analysis: Dict[str, Any]) -> str:
    """Generate a Markdown report."""
    us = analysis["us"]
    others = analysis["competitors"]
    all_comps = [us] + others
    fa_list = analysis["feature_analysis"]
    lines: List[str] = []

    lines.append(f"# Competitive Feature Matrix: {us}")
    lines.append(f"\n**Competitors:** {', '.join(others)}")
    lines.append(f"**Features scored:** {analysis['total_features']}")
    lines.append(f"**Your coverage:** {analysis['our_coverage_pct']:.0f}%\n")

    # Position summary
    lines.append("## Competitive Position\n")
    pos = analysis["positions"]
    total = analysis["total_features"]
    for position in ["Lead", "Parity", "Trail", "Gap"]:
        count = pos.get(position, 0)
        pct = count / total * 100 if total > 0 else 0
        lines.append(f"- **{position}:** {count} ({pct:.0f}%)")

    # Feature table
    lines.append("\n## Feature Heatmap\n")
    header = "| Feature | " + " | ".join(all_comps) + " | Position |"
    sep = "|---|" + "|".join("---" for _ in all_comps) + "|---|"
    lines.append(header)
    lines.append(sep)

    for fa in sorted(fa_list, key=lambda x: (x["category"], -x["our_score"])):
        scores = " | ".join(str(fa["scores"].get(c, 0)) for c in all_comps)
        lines.append(f"| {fa['feature']} | {scores} | {fa['position']} |")

    # Gaps
    gaps = sorted([f for f in fa_list if f["gap"] < 0], key=lambda x: x["gap"])
    if gaps:
        lines.append("\n## Biggest Gaps\n")
        for f in gaps[:10]:
            leaders = [c for c in others if f["scores"].get(c, 0) == f["market_max"]]
            lines.append(f"- **{f['feature']}**: you={f['our_score']}, best={f['market_max']} ({', '.join(leaders[:2])})")

    leads = [f for f in fa_list if f["position"] == "Lead"]
    if leads:
        lines.append("\n## Differentiators\n")
        for f in leads:
            lines.append(f"- **{f['feature']}**: you={f['our_score']}, market best={f['market_max']}")

    lines.append(f"\n---\n*Generated by competitive-feature-matrix.py*\n")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Build a competitive feature matrix from CSV. Outputs gap analysis, "
                    "parity scores, and strategic recommendations.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --csv features.csv --us "Acme AI"
  %(prog)s --csv features.csv --us "Acme AI" --scoring binary
  %(prog)s --csv features.csv --us "Acme AI" --markdown report.md
  %(prog)s --csv features.csv --us "Acme AI" --output analysis.json
        """,
    )
    parser.add_argument("--csv", "-c", type=str, required=True, help="CSV file with feature matrix")
    parser.add_argument("--us", "-u", type=str, required=True, help="Your product's column name in the CSV")
    parser.add_argument("--scoring", "-s", type=str, default="numeric",
                        choices=["numeric", "binary", "text"],
                        help="Scoring mode: numeric (0-3), binary (0/1), text (auto-mapped). Default: numeric")
    parser.add_argument("--markdown", type=str, help="Export Markdown report to file")
    parser.add_argument("--output", "-o", type=str, help="Write JSON results to file")
    args = parser.parse_args()

    try:
        features, competitors, category_col = load_csv(args.csv, args.scoring)
    except Exception as e:
        print(f"Error loading CSV: {e}", file=sys.stderr)
        return 1

    if not features:
        print("Error: no valid features found in CSV.", file=sys.stderr)
        return 1

    try:
        analysis = analyze_matrix(features, competitors, args.us)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    # Terminal report
    print_report(analysis)

    # Markdown export
    if args.markdown:
        md = generate_markdown(analysis)
        with open(args.markdown, "w", encoding="utf-8") as f:
            f.write(md)
        print(f"\n📄 Markdown report saved to {args.markdown}")

    # JSON output
    if args.output:
        output = {
            "us": analysis["us"],
            "competitors": analysis["competitors"],
            "total_features": analysis["total_features"],
            "our_coverage_pct": analysis["our_coverage_pct"],
            "positions": analysis["positions"],
            "category_analysis": analysis["category_analysis"],
            "competitor_parity": analysis["competitor_parity"],
            "feature_analysis": analysis["feature_analysis"],
        }
        with open(args.output, "w") as f:
            json.dump(output, f, indent=2)
        print(f"\n📁 JSON results saved to {args.output}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
