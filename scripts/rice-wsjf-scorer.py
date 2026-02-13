#!/usr/bin/env python3
"""
RICE / WSJF Prioritization Scorer

Batch-calculate RICE or WSJF scores from a CSV of features and output a ranked
backlog. Supports both frameworks, custom column mapping, sensitivity analysis,
and tier grouping (Quick Wins, Big Bets, etc.).

Frameworks:
    RICE  = (Reach × Impact × Confidence) / Effort
    WSJF  = Cost of Delay / Job Duration
           where Cost of Delay = User-Business Value + Time Criticality + Risk Reduction

Usage:
    # RICE scoring from CSV
    python rice-wsjf-scorer.py --csv features.csv --method rice
    python rice-wsjf-scorer.py --csv features.csv --method rice --output ranked.json

    # WSJF scoring from CSV
    python rice-wsjf-scorer.py --csv features.csv --method wsjf

    # Interactive mode (enter features manually)
    python rice-wsjf-scorer.py --method rice --interactive

    # Sensitivity analysis: what if confidence is off by ±20%?
    python rice-wsjf-scorer.py --csv features.csv --method rice --sensitivity

CSV format — RICE (header row required):
    feature,reach,impact,confidence,effort
    Dark mode,3000,0.5,100,1
    Slack notifications,2000,1,100,2
    Onboarding redesign,1500,3,80,4
    Advanced search,800,2,50,3

CSV format — WSJF (header row required):
    feature,user_business_value,time_criticality,risk_reduction,job_duration
    GDPR compliance,8,9,10,5
    Mobile app,7,3,2,8
    API v2,5,6,4,3

Requirements:
    None (stdlib only).
"""

import argparse
import csv
import json
import sys
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Scoring engines
# ---------------------------------------------------------------------------

def rice_score(reach: float, impact: float, confidence_pct: float, effort: float) -> float:
    """
    RICE = (Reach × Impact × Confidence) / Effort

    Args:
        reach: Users/customers affected per time period (number).
        impact: Effect on each user (0.25 | 0.5 | 1 | 2 | 3).
        confidence_pct: Confidence percentage (50, 80, 100).
        effort: Person-months to build (> 0).
    """
    if effort <= 0:
        return 0.0
    conf = confidence_pct / 100.0 if confidence_pct > 1 else confidence_pct
    return (reach * impact * conf) / effort


def wsjf_score(
    user_business_value: float,
    time_criticality: float,
    risk_reduction: float,
    job_duration: float,
) -> Tuple[float, float]:
    """
    WSJF = Cost of Delay / Job Duration

    Cost of Delay = User-Business Value + Time Criticality + Risk Reduction
    All components scored 1-10 (Fibonacci-friendly: 1, 2, 3, 5, 8, 13).
    Job Duration also 1-10.

    Returns:
        (cost_of_delay, wsjf)
    """
    cod = user_business_value + time_criticality + risk_reduction
    if job_duration <= 0:
        return cod, 0.0
    return cod, cod / job_duration


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
    val = str(raw).strip().rstrip("%")
    try:
        return float(val)
    except ValueError:
        return default


def load_rice_csv(path: str) -> List[Dict[str, Any]]:
    """Load features from a RICE-formatted CSV."""
    items: List[Dict[str, Any]] = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fields = reader.fieldnames or []
        c_feature = _col(fields, "feature", "name", "item", "title", "id")
        c_reach = _col(fields, "reach", "r")
        c_impact = _col(fields, "impact", "i")
        c_conf = _col(fields, "confidence", "conf", "c", "confidence_pct")
        c_effort = _col(fields, "effort", "e", "person_months")
        c_category = _col(fields, "category", "type", "group", "theme")

        for row in reader:
            name = row.get(c_feature or "feature", f"Item {len(items) + 1}").strip()
            reach = _float(row, c_reach)
            impact = _float(row, c_impact)
            conf = _float(row, c_conf, 100.0)
            effort = _float(row, c_effort, 1.0)
            category = row.get(c_category or "", "").strip() if c_category else ""

            score = rice_score(reach, impact, conf, effort)
            items.append({
                "feature": name,
                "reach": reach,
                "impact": impact,
                "confidence": conf,
                "effort": effort,
                "score": round(score, 1),
                "category": category,
            })
    return items


def load_wsjf_csv(path: str) -> List[Dict[str, Any]]:
    """Load features from a WSJF-formatted CSV."""
    items: List[Dict[str, Any]] = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fields = reader.fieldnames or []
        c_feature = _col(fields, "feature", "name", "item", "title", "id")
        c_ubv = _col(fields, "user_business_value", "ubv", "business_value", "value")
        c_tc = _col(fields, "time_criticality", "tc", "urgency")
        c_rr = _col(fields, "risk_reduction", "rr", "risk", "risk_reduction_opportunity")
        c_dur = _col(fields, "job_duration", "duration", "job_size", "size")
        c_category = _col(fields, "category", "type", "group", "theme")

        for row in reader:
            name = row.get(c_feature or "feature", f"Item {len(items) + 1}").strip()
            ubv = _float(row, c_ubv, 1.0)
            tc = _float(row, c_tc, 1.0)
            rr = _float(row, c_rr, 1.0)
            dur = _float(row, c_dur, 1.0)
            category = row.get(c_category or "", "").strip() if c_category else ""

            cod, score = wsjf_score(ubv, tc, rr, dur)
            items.append({
                "feature": name,
                "user_business_value": ubv,
                "time_criticality": tc,
                "risk_reduction": rr,
                "cost_of_delay": round(cod, 1),
                "job_duration": dur,
                "score": round(score, 2),
                "category": category,
            })
    return items


# ---------------------------------------------------------------------------
# Interactive mode
# ---------------------------------------------------------------------------

def interactive_rice() -> List[Dict[str, Any]]:
    """Prompt user for features interactively (RICE)."""
    items: List[Dict[str, Any]] = []
    print("\n📝 Enter features (empty name to finish):\n")
    while True:
        name = input("  Feature name: ").strip()
        if not name:
            break
        try:
            reach = float(input("    Reach (users affected):         "))
            impact = float(input("    Impact (0.25/0.5/1/2/3):        "))
            conf = float(input("    Confidence % (50/80/100):        "))
            effort = float(input("    Effort (person-months):          "))
        except (ValueError, EOFError):
            print("  ⚠️  Invalid input, skipping.\n")
            continue
        score = rice_score(reach, impact, conf, effort)
        items.append({
            "feature": name,
            "reach": reach,
            "impact": impact,
            "confidence": conf,
            "effort": effort,
            "score": round(score, 1),
            "category": "",
        })
        print(f"    → RICE Score: {score:,.1f}\n")
    return items


def interactive_wsjf() -> List[Dict[str, Any]]:
    """Prompt user for features interactively (WSJF)."""
    items: List[Dict[str, Any]] = []
    print("\n📝 Enter features (empty name to finish). Score each 1-10:\n")
    while True:
        name = input("  Feature name: ").strip()
        if not name:
            break
        try:
            ubv = float(input("    User-Business Value (1-10):       "))
            tc = float(input("    Time Criticality (1-10):          "))
            rr = float(input("    Risk Reduction / Opportunity (1-10): "))
            dur = float(input("    Job Duration (1-10):              "))
        except (ValueError, EOFError):
            print("  ⚠️  Invalid input, skipping.\n")
            continue
        cod, score = wsjf_score(ubv, tc, rr, dur)
        items.append({
            "feature": name,
            "user_business_value": ubv,
            "time_criticality": tc,
            "risk_reduction": rr,
            "cost_of_delay": round(cod, 1),
            "job_duration": dur,
            "score": round(score, 2),
            "category": "",
        })
        print(f"    → Cost of Delay: {cod:.1f}  |  WSJF: {score:.2f}\n")
    return items


# ---------------------------------------------------------------------------
# Sensitivity analysis
# ---------------------------------------------------------------------------

def sensitivity_rice(items: List[Dict[str, Any]], pct: float = 20.0) -> List[Dict[str, Any]]:
    """
    For each feature, recalculate score with confidence ± pct%.
    Shows how score ranking changes under uncertainty.
    """
    results = []
    for item in items:
        conf = item["confidence"]
        conf_lo = max(0, conf - pct)
        conf_hi = min(100, conf + pct)
        score_lo = rice_score(item["reach"], item["impact"], conf_lo, item["effort"])
        score_hi = rice_score(item["reach"], item["impact"], conf_hi, item["effort"])
        results.append({
            **item,
            "score_low": round(score_lo, 1),
            "score_high": round(score_hi, 1),
            "score_range": round(score_hi - score_lo, 1),
        })
    return results


def sensitivity_wsjf(items: List[Dict[str, Any]], swing: float = 2.0) -> List[Dict[str, Any]]:
    """
    For each feature, recalculate WSJF with ±swing on each CoD component.
    Shows the score band under estimation uncertainty.
    """
    results = []
    for item in items:
        ubv = item["user_business_value"]
        tc = item["time_criticality"]
        rr = item["risk_reduction"]
        dur = item["job_duration"]

        cod_lo = max(0, ubv - swing) + max(0, tc - swing) + max(0, rr - swing)
        cod_hi = (ubv + swing) + (tc + swing) + (rr + swing)
        score_lo = cod_lo / dur if dur > 0 else 0
        score_hi = cod_hi / dur if dur > 0 else 0

        results.append({
            **item,
            "score_low": round(score_lo, 2),
            "score_high": round(score_hi, 2),
            "score_range": round(score_hi - score_lo, 2),
        })
    return results


# ---------------------------------------------------------------------------
# Tier classification
# ---------------------------------------------------------------------------

def classify_rice_tier(item: Dict[str, Any]) -> str:
    """Classify into Impact/Effort quadrant."""
    high_score = item["score"] >= _median([i["score"] for i in [item]])  # placeholder
    # Use simple heuristics: high impact+reach vs effort
    value = item["reach"] * item["impact"] * (item["confidence"] / 100.0)
    if value >= 1000 and item["effort"] <= 2:
        return "🏆 Quick Win"
    elif value >= 1000 and item["effort"] > 2:
        return "🎯 Big Bet"
    elif value < 1000 and item["effort"] <= 2:
        return "🔧 Fill-In"
    else:
        return "⛔ Deprioritize"


def classify_items(items: List[Dict[str, Any]], method: str) -> List[Dict[str, Any]]:
    """Add tier classification to each item."""
    if not items:
        return items

    scores = sorted([i["score"] for i in items])
    median_score = scores[len(scores) // 2]

    if method == "rice":
        median_effort = sorted([i["effort"] for i in items])[len(items) // 2]
        for item in items:
            if item["score"] >= median_score and item["effort"] <= median_effort:
                item["tier"] = "🏆 Quick Win"
            elif item["score"] >= median_score and item["effort"] > median_effort:
                item["tier"] = "🎯 Big Bet"
            elif item["score"] < median_score and item["effort"] <= median_effort:
                item["tier"] = "🔧 Fill-In"
            else:
                item["tier"] = "⛔ Deprioritize"
    else:  # wsjf
        median_dur = sorted([i["job_duration"] for i in items])[len(items) // 2]
        for item in items:
            if item["score"] >= median_score and item["job_duration"] <= median_dur:
                item["tier"] = "🏆 Quick Win"
            elif item["score"] >= median_score and item["job_duration"] > median_dur:
                item["tier"] = "🎯 Big Bet"
            elif item["score"] < median_score and item["job_duration"] <= median_dur:
                item["tier"] = "🔧 Fill-In"
            else:
                item["tier"] = "⛔ Deprioritize"

    return items


def _median(values: List[float]) -> float:
    if not values:
        return 0.0
    s = sorted(values)
    n = len(s)
    if n % 2 == 1:
        return s[n // 2]
    return (s[n // 2 - 1] + s[n // 2]) / 2


# ---------------------------------------------------------------------------
# Report printing
# ---------------------------------------------------------------------------

def print_rice_report(
    items: List[Dict[str, Any]],
    sensitivity: bool = False,
) -> None:
    """Pretty-print RICE ranked backlog."""
    ranked = sorted(items, key=lambda x: -x["score"])

    print("\n" + "=" * 78)
    print("📊 RICE PRIORITIZATION SCORER")
    print("=" * 78)

    print(f"\n📋 RANKED BACKLOG ({len(ranked)} features):\n")

    # Table header
    print(f"   {'Rank':<5} {'Feature':<28} {'Reach':>7} {'Impact':>7} {'Conf':>6} {'Effort':>7} {'RICE':>9}  {'Tier'}")
    print(f"   {'─'*5} {'─'*28} {'─'*7} {'─'*7} {'─'*6} {'─'*7} {'─'*9}  {'─'*16}")

    for i, item in enumerate(ranked, 1):
        tier = item.get("tier", "")
        print(
            f"   {i:<5} {item['feature']:<28} {item['reach']:>7,.0f} {item['impact']:>7.2f} "
            f"{item['confidence']:>5.0f}% {item['effort']:>7.1f} {item['score']:>9,.1f}  {tier}"
        )

    # Category summary
    categories = set(i["category"] for i in ranked if i["category"])
    if categories:
        print(f"\n📂 BY CATEGORY:")
        for cat in sorted(categories):
            cat_items = [i for i in ranked if i["category"] == cat]
            avg_score = sum(i["score"] for i in cat_items) / len(cat_items)
            total_effort = sum(i["effort"] for i in cat_items)
            print(f"   • {cat}: {len(cat_items)} features, avg score {avg_score:,.1f}, total effort {total_effort:.1f}pm")

    # Tier summary
    tiers = {}
    for item in ranked:
        t = item.get("tier", "Unclassified")
        tiers.setdefault(t, []).append(item)
    if tiers:
        print(f"\n🏷️  TIER SUMMARY:")
        for tier_name in ["🏆 Quick Win", "🎯 Big Bet", "🔧 Fill-In", "⛔ Deprioritize"]:
            if tier_name in tiers:
                names = ", ".join(i["feature"] for i in tiers[tier_name])
                print(f"   {tier_name}: {names}")

    # Sensitivity
    if sensitivity:
        print(f"\n📐 SENSITIVITY (confidence ±20%):")
        for item in ranked:
            lo = item.get("score_low", item["score"])
            hi = item.get("score_high", item["score"])
            rng = item.get("score_range", 0)
            bar_len = min(40, max(1, int(rng / max(1, ranked[0].get("score_range", 1)) * 40)))
            bar = "░" * bar_len
            print(f"   {item['feature']:<28} {lo:>9,.1f} ← {item['score']:>9,.1f} → {hi:>9,.1f}  {bar}")

    print(f"\n💡 REFERENCE:")
    print(f"   • RICE = (Reach × Impact × Confidence) / Effort")
    print(f"   • Impact: 0.25 (minimal) → 3 (massive)")
    print(f"   • Confidence: 50% (gut) → 100% (validated)")
    print(f"   • Higher score = higher priority")
    print("\n" + "=" * 78)


def print_wsjf_report(
    items: List[Dict[str, Any]],
    sensitivity: bool = False,
) -> None:
    """Pretty-print WSJF ranked backlog."""
    ranked = sorted(items, key=lambda x: -x["score"])

    print("\n" + "=" * 78)
    print("📊 WSJF (WEIGHTED SHORTEST JOB FIRST) SCORER")
    print("=" * 78)

    print(f"\n📋 RANKED BACKLOG ({len(ranked)} features):\n")

    print(f"   {'Rank':<5} {'Feature':<24} {'UBV':>5} {'TC':>5} {'RR':>5} {'CoD':>6} {'Dur':>5} {'WSJF':>7}  {'Tier'}")
    print(f"   {'─'*5} {'─'*24} {'─'*5} {'─'*5} {'─'*5} {'─'*6} {'─'*5} {'─'*7}  {'─'*16}")

    for i, item in enumerate(ranked, 1):
        tier = item.get("tier", "")
        print(
            f"   {i:<5} {item['feature']:<24} {item['user_business_value']:>5.0f} "
            f"{item['time_criticality']:>5.0f} {item['risk_reduction']:>5.0f} "
            f"{item['cost_of_delay']:>6.1f} {item['job_duration']:>5.0f} "
            f"{item['score']:>7.2f}  {tier}"
        )

    # Category summary
    categories = set(i["category"] for i in ranked if i["category"])
    if categories:
        print(f"\n📂 BY CATEGORY:")
        for cat in sorted(categories):
            cat_items = [i for i in ranked if i["category"] == cat]
            avg_score = sum(i["score"] for i in cat_items) / len(cat_items)
            total_dur = sum(i["job_duration"] for i in cat_items)
            print(f"   • {cat}: {len(cat_items)} features, avg WSJF {avg_score:.2f}, total duration {total_dur:.0f}")

    # Tier summary
    tiers = {}
    for item in ranked:
        t = item.get("tier", "Unclassified")
        tiers.setdefault(t, []).append(item)
    if tiers:
        print(f"\n🏷️  TIER SUMMARY:")
        for tier_name in ["🏆 Quick Win", "🎯 Big Bet", "🔧 Fill-In", "⛔ Deprioritize"]:
            if tier_name in tiers:
                names = ", ".join(i["feature"] for i in tiers[tier_name])
                print(f"   {tier_name}: {names}")

    # Sensitivity
    if sensitivity:
        print(f"\n📐 SENSITIVITY (CoD components ±2):")
        for item in ranked:
            lo = item.get("score_low", item["score"])
            hi = item.get("score_high", item["score"])
            rng = item.get("score_range", 0)
            bar_len = min(40, max(1, int(rng / max(1, ranked[0].get("score_range", 1)) * 40)))
            bar = "░" * bar_len
            print(f"   {item['feature']:<24} {lo:>7.2f} ← {item['score']:>7.2f} → {hi:>7.2f}  {bar}")

    print(f"\n💡 REFERENCE:")
    print(f"   • WSJF = Cost of Delay / Job Duration")
    print(f"   • CoD  = User-Business Value + Time Criticality + Risk Reduction")
    print(f"   • All components scored 1-10 (use Fibonacci: 1, 2, 3, 5, 8, 13)")
    print(f"   • Higher WSJF = do first (highest economic value per unit of time)")
    print("\n" + "=" * 78)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Prioritize features using RICE or WSJF scoring. "
                    "Reads from CSV or interactive input; outputs a ranked backlog.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --csv features.csv --method rice
  %(prog)s --csv features.csv --method wsjf --sensitivity --output ranked.json
  %(prog)s --method rice --interactive
        """,
    )
    parser.add_argument(
        "--csv", "-c", type=str,
        help="CSV file with feature data (see docstring for format)",
    )
    parser.add_argument(
        "--method", "-m", type=str, default="rice",
        choices=["rice", "wsjf"],
        help="Scoring method: rice or wsjf (default: rice)",
    )
    parser.add_argument(
        "--interactive", "-i", action="store_true",
        help="Enter features interactively instead of CSV",
    )
    parser.add_argument(
        "--sensitivity", "-s", action="store_true",
        help="Run sensitivity analysis showing score ranges under uncertainty",
    )
    parser.add_argument(
        "--output", "-o", type=str,
        help="Write ranked results to JSON file",
    )
    args = parser.parse_args()

    if not args.csv and not args.interactive:
        print("Error: provide --csv or --interactive.", file=sys.stderr)
        parser.print_help(sys.stderr)
        return 1

    # Load items
    if args.interactive:
        items = interactive_rice() if args.method == "rice" else interactive_wsjf()
    else:
        try:
            if args.method == "rice":
                items = load_rice_csv(args.csv)
            else:
                items = load_wsjf_csv(args.csv)
        except Exception as e:
            print(f"Error loading CSV: {e}", file=sys.stderr)
            return 1

    if not items:
        print("Error: no valid features found.", file=sys.stderr)
        return 1

    # Classify tiers
    items = classify_items(items, args.method)

    # Sensitivity analysis
    if args.sensitivity:
        if args.method == "rice":
            items = sensitivity_rice(items)
        else:
            items = sensitivity_wsjf(items)

    # Print report
    if args.method == "rice":
        print_rice_report(items, sensitivity=args.sensitivity)
    else:
        print_wsjf_report(items, sensitivity=args.sensitivity)

    # JSON output
    if args.output:
        ranked = sorted(items, key=lambda x: -x["score"])
        report = {
            "method": args.method.upper(),
            "n_features": len(ranked),
            "ranked": ranked,
        }
        with open(args.output, "w") as f:
            json.dump(report, f, indent=2)
        print(f"\n📁 Ranked results saved to {args.output}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
