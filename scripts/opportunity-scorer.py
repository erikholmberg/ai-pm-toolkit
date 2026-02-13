#!/usr/bin/env python3
"""
Opportunity Scoring Calculator

Identify underserved customer needs using the Ulwick Opportunity Score
(Outcome-Driven Innovation) and the Importance-Satisfaction gap framework.
Reads survey data from CSV, scores each outcome/need, ranks them, and
highlights the biggest opportunities.

Frameworks:
    Opportunity Score = Importance + max(Importance - Satisfaction, 0)
        - Score > 15: Over-served (potential to cut)
        - Score 12-15: Appropriately served
        - Score 10-12: Opportunity zone
        - Score > 12 with Imp > Sat: Underserved — best opportunities

    Gap Score = Importance - Satisfaction
        - Positive gap = underserved need (opportunity)
        - Negative gap = over-served need (cut or simplify)
        - Zero = appropriately served

Usage:
    python opportunity-scorer.py --csv needs.csv
    python opportunity-scorer.py --csv needs.csv --threshold 12 --output report.json
    python opportunity-scorer.py --interactive
    python opportunity-scorer.py --csv needs.csv --sort gap

CSV format (header row required):
    need,importance,satisfaction
    "Minimize time to find relevant results",9.2,4.1
    "Reduce false positives in alerts",8.5,7.8
    "Quickly understand why a recommendation was made",7.8,3.2
    "Ensure data is up to date",9.0,8.5

    Columns:
        need          — Description of the customer outcome/need
        importance    — Average importance rating (1-10 scale)
        satisfaction  — Average satisfaction rating (1-10 scale)
        category      — (Optional) Theme/group for the need
        n_respondents — (Optional) Number of respondents (for confidence)

Requirements:
    None (stdlib only).
"""

import argparse
import csv
import json
import sys
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Scoring engine
# ---------------------------------------------------------------------------

def opportunity_score(importance: float, satisfaction: float) -> float:
    """
    Ulwick Opportunity Score = Importance + max(Importance - Satisfaction, 0)

    Range: importance (when satisfied) to 2 × importance (when fully unmet).
    Max theoretical = 20 (importance=10, satisfaction=0).
    """
    gap = importance - satisfaction
    return importance + max(gap, 0)


def gap_score(importance: float, satisfaction: float) -> float:
    """Simple gap: Importance - Satisfaction."""
    return importance - satisfaction


def classify_opportunity(opp_score: float, importance: float, satisfaction: float) -> str:
    """Classify the opportunity zone."""
    gap = importance - satisfaction
    if gap > 2 and importance >= 7:
        return "🔴 Underserved"
    elif gap > 0 and importance >= 7:
        return "🟡 Opportunity"
    elif gap <= 0 and importance >= 7:
        return "🟢 Well-served"
    elif gap < -2:
        return "🔵 Over-served"
    elif importance < 5:
        return "⚪ Low priority"
    else:
        return "🟢 Adequate"


# ---------------------------------------------------------------------------
# CSV loading
# ---------------------------------------------------------------------------

def _col(fieldnames: List[str], *aliases: str) -> Optional[str]:
    """Find the first matching column name (case-insensitive)."""
    lower_map = {f.lower().strip(): f for f in fieldnames}
    for alias in aliases:
        key = alias.lower().strip()
        if key in lower_map:
            return lower_map[key]
    return None


def _float(row: Dict, col: Optional[str], default: float = 0.0) -> float:
    if not col:
        return default
    raw = row.get(col, "")
    if not raw or not str(raw).strip():
        return default
    try:
        return float(str(raw).strip())
    except ValueError:
        return default


def load_csv(path: str) -> List[Dict[str, Any]]:
    """Load customer needs from CSV and compute scores."""
    items: List[Dict[str, Any]] = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fields = reader.fieldnames or []
        c_need = _col(fields, "need", "outcome", "job", "name", "feature", "item")
        c_imp = _col(fields, "importance", "imp", "important", "importance_avg")
        c_sat = _col(fields, "satisfaction", "sat", "satisfaction_avg", "current_satisfaction")
        c_cat = _col(fields, "category", "theme", "group", "type")
        c_n = _col(fields, "n_respondents", "n", "respondents", "sample_size")

        for row in reader:
            name = row.get(c_need or "need", f"Need {len(items) + 1}").strip()
            imp = _float(row, c_imp)
            sat = _float(row, c_sat)
            category = row.get(c_cat or "", "").strip() if c_cat else ""
            n_resp = int(_float(row, c_n)) if c_n else None

            if imp <= 0:
                continue

            opp = opportunity_score(imp, sat)
            gap = gap_score(imp, sat)
            zone = classify_opportunity(opp, imp, sat)

            items.append({
                "need": name,
                "importance": round(imp, 2),
                "satisfaction": round(sat, 2),
                "gap": round(gap, 2),
                "opportunity_score": round(opp, 2),
                "zone": zone,
                "category": category,
                "n_respondents": n_resp,
            })

    return items


# ---------------------------------------------------------------------------
# Interactive mode
# ---------------------------------------------------------------------------

def interactive() -> List[Dict[str, Any]]:
    """Prompt user for needs interactively."""
    items: List[Dict[str, Any]] = []
    print("\n📝 Enter customer needs/outcomes (empty name to finish).")
    print("   Rate importance and satisfaction on 1-10 scale.\n")
    while True:
        name = input("  Need/outcome: ").strip()
        if not name:
            break
        try:
            imp = float(input("    Importance (1-10):    "))
            sat = float(input("    Satisfaction (1-10):  "))
        except (ValueError, EOFError):
            print("  ⚠️  Invalid input, skipping.\n")
            continue
        opp = opportunity_score(imp, sat)
        gap = gap_score(imp, sat)
        zone = classify_opportunity(opp, imp, sat)
        items.append({
            "need": name,
            "importance": round(imp, 2),
            "satisfaction": round(sat, 2),
            "gap": round(gap, 2),
            "opportunity_score": round(opp, 2),
            "zone": zone,
            "category": "",
            "n_respondents": None,
        })
        print(f"    → Opportunity Score: {opp:.1f}  |  Gap: {gap:+.1f}  |  {zone}\n")
    return items


# ---------------------------------------------------------------------------
# Visualization helpers (ASCII)
# ---------------------------------------------------------------------------

def _bar(value: float, max_val: float, width: int = 30, fill: str = "█", empty: str = "░") -> str:
    """Render a simple ASCII bar."""
    if max_val <= 0:
        return empty * width
    ratio = min(1.0, max(0.0, value / max_val))
    filled = int(ratio * width)
    return fill * filled + empty * (width - filled)


def _dot_plot(importance: float, satisfaction: float, width: int = 20) -> str:
    """
    Render a 1-10 scale showing importance (I) and satisfaction (S) positions.
    Helps visualize the gap at a glance.
    """
    scale = ["·"] * width
    imp_pos = min(width - 1, max(0, int((importance / 10.0) * (width - 1))))
    sat_pos = min(width - 1, max(0, int((satisfaction / 10.0) * (width - 1))))
    # Mark positions (importance first, satisfaction overwrites if same)
    if imp_pos == sat_pos:
        scale[imp_pos] = "●"
    else:
        scale[min(imp_pos, sat_pos)] = "S" if sat_pos < imp_pos else "I"
        scale[max(imp_pos, sat_pos)] = "I" if sat_pos < imp_pos else "S"
        # Fill gap with dashes
        for k in range(min(imp_pos, sat_pos) + 1, max(imp_pos, sat_pos)):
            scale[k] = "─"
    return "".join(scale)


# ---------------------------------------------------------------------------
# Report printing
# ---------------------------------------------------------------------------

def print_report(
    items: List[Dict[str, Any]],
    sort_key: str = "opportunity_score",
    threshold: float = 0.0,
) -> None:
    """Pretty-print the opportunity analysis."""
    ranked = sorted(items, key=lambda x: -x[sort_key])

    print("\n" + "=" * 78)
    print("📊 OPPORTUNITY SCORING CALCULATOR")
    print("=" * 78)

    # Summary stats
    underserved = [i for i in items if "Underserved" in i["zone"]]
    opportunities = [i for i in items if "Opportunity" in i["zone"]]
    overserved = [i for i in items if "Over-served" in i["zone"]]

    print(f"\n📋 OVERVIEW:")
    print(f"   • Needs analyzed:     {len(items)}")
    print(f"   • 🔴 Underserved:     {len(underserved)}")
    print(f"   • 🟡 Opportunity:     {len(opportunities)}")
    print(f"   • 🔵 Over-served:     {len(overserved)}")

    if items:
        avg_gap = sum(i["gap"] for i in items) / len(items)
        avg_imp = sum(i["importance"] for i in items) / len(items)
        print(f"   • Avg importance:     {avg_imp:.1f}")
        print(f"   • Avg gap:            {avg_gap:+.1f}")

    # Ranked table
    sort_label = "Opp Score" if sort_key == "opportunity_score" else "Gap"
    print(f"\n📈 RANKED BY {sort_label.upper()} ({len(ranked)} needs):\n")

    print(f"   {'#':<4} {'Need':<36} {'Imp':>5} {'Sat':>5} {'Gap':>6} {'Score':>6}  {'Zone'}")
    print(f"   {'─'*4} {'─'*36} {'─'*5} {'─'*5} {'─'*6} {'─'*6}  {'─'*14}")

    for i, item in enumerate(ranked, 1):
        gap_str = f"{item['gap']:+.1f}"
        print(
            f"   {i:<4} {item['need'][:36]:<36} {item['importance']:>5.1f} "
            f"{item['satisfaction']:>5.1f} {gap_str:>6} {item['opportunity_score']:>6.1f}  {item['zone']}"
        )

    # Gap visualization
    print(f"\n📐 GAP VISUALIZATION (I=Importance, S=Satisfaction):\n")
    print(f"   {'Need':<32}  {'1':·<10}{'5':·<10}{'10'}")
    for item in ranked[:15]:  # top 15
        dot = _dot_plot(item["importance"], item["satisfaction"])
        print(f"   {item['need'][:32]:<32}  {dot}  gap {item['gap']:+.1f}")

    # Top opportunities
    top_opps = [i for i in ranked if i["gap"] > 0 and i["importance"] >= 7]
    if top_opps:
        print(f"\n🎯 TOP OPPORTUNITIES (high importance, positive gap):")
        for item in top_opps[:5]:
            bar = _bar(item["gap"], 10, width=20)
            print(f"   • {item['need'][:40]:<40}  gap {item['gap']:+.1f}  {bar}")

    # Over-served (simplification candidates)
    if overserved:
        print(f"\n✂️  SIMPLIFICATION CANDIDATES (over-served):")
        for item in sorted(overserved, key=lambda x: x["gap"]):
            print(f"   • {item['need'][:40]:<40}  gap {item['gap']:+.1f}  (consider simplifying)")

    # Category summary
    categories = set(i["category"] for i in items if i["category"])
    if categories:
        print(f"\n📂 BY CATEGORY:")
        for cat in sorted(categories):
            cat_items = [i for i in items if i["category"] == cat]
            avg_opp = sum(i["opportunity_score"] for i in cat_items) / len(cat_items)
            avg_g = sum(i["gap"] for i in cat_items) / len(cat_items)
            n_under = sum(1 for i in cat_items if "Underserved" in i["zone"])
            print(f"   • {cat}: {len(cat_items)} needs, avg opp {avg_opp:.1f}, avg gap {avg_g:+.1f}, {n_under} underserved")

    # Threshold filter
    if threshold > 0:
        above = [i for i in ranked if i["opportunity_score"] >= threshold]
        print(f"\n🔍 ABOVE THRESHOLD ({threshold:.0f}): {len(above)} of {len(ranked)} needs")
        for item in above:
            print(f"   • {item['need'][:40]}  (score {item['opportunity_score']:.1f})")

    print(f"\n💡 REFERENCE:")
    print(f"   • Opportunity Score = Importance + max(Importance − Satisfaction, 0)")
    print(f"   • Range: {1:.0f} (low importance, satisfied) → 20 (high importance, unmet)")
    print(f"   • Focus on: high importance + large positive gap")
    print(f"   • Simplify: low importance OR large negative gap (over-served)")
    print(f"   • Data source: customer surveys (rate importance & satisfaction 1-10)")
    print("\n" + "=" * 78)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Score customer needs/outcomes using the Ulwick Opportunity Score "
                    "to find underserved opportunities and over-served areas to simplify.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --csv needs.csv
  %(prog)s --csv needs.csv --sort gap --threshold 12 --output report.json
  %(prog)s --interactive
        """,
    )
    parser.add_argument(
        "--csv", "-c", type=str,
        help="CSV file with need, importance, satisfaction columns",
    )
    parser.add_argument(
        "--interactive", "-i", action="store_true",
        help="Enter needs interactively",
    )
    parser.add_argument(
        "--sort", "-s", type=str, default="opportunity_score",
        choices=["opportunity_score", "gap", "importance"],
        help="Sort results by: opportunity_score (default), gap, or importance",
    )
    parser.add_argument(
        "--threshold", "-t", type=float, default=0.0,
        help="Only highlight needs with opportunity score >= threshold",
    )
    parser.add_argument(
        "--output", "-o", type=str,
        help="Write results to JSON file",
    )
    args = parser.parse_args()

    if not args.csv and not args.interactive:
        print("Error: provide --csv or --interactive.", file=sys.stderr)
        parser.print_help(sys.stderr)
        return 1

    # Load items
    if args.interactive:
        items = interactive()
    else:
        try:
            items = load_csv(args.csv)
        except Exception as e:
            print(f"Error loading CSV: {e}", file=sys.stderr)
            return 1

    if not items:
        print("Error: no valid needs found. Check CSV columns (need, importance, satisfaction).", file=sys.stderr)
        return 1

    # Print report
    print_report(items, sort_key=args.sort, threshold=args.threshold)

    # JSON output
    if args.output:
        ranked = sorted(items, key=lambda x: -x[args.sort])
        report = {
            "n_needs": len(ranked),
            "sort_by": args.sort,
            "summary": {
                "underserved": sum(1 for i in ranked if "Underserved" in i["zone"]),
                "opportunity": sum(1 for i in ranked if "Opportunity" in i["zone"]),
                "well_served": sum(1 for i in ranked if "Well-served" in i["zone"] or "Adequate" in i["zone"]),
                "over_served": sum(1 for i in ranked if "Over-served" in i["zone"]),
            },
            "needs": ranked,
        }
        with open(args.output, "w") as f:
            json.dump(report, f, indent=2)
        print(f"\n📁 Results saved to {args.output}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
