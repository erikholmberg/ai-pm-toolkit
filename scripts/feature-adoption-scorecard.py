#!/usr/bin/env python3
"""
Feature Adoption Scorecard

Track and score feature adoption across multiple dimensions: activation rate,
DAU penetration, usage frequency, stickiness ratio, and depth-of-use. Goes
beyond funnel analysis into ongoing feature health monitoring.

Scores each feature on a 0-100 scale and grades adoption quality to help
PMs decide what to invest in, sunset, or redesign.

Usage:
    # Inline features
    python feature-adoption-scorecard.py \\
        --feature "AI Search:total=50000,activated=35000,dau=8000,wau=18000,mau=30000,avg_sessions=4.2" \\
        --feature "Dark Mode:total=50000,activated=42000,dau=20000,wau=35000,mau=40000,avg_sessions=12" \\
        --feature "Export PDF:total=50000,activated=5000,dau=800,wau=2500,mau=4000,avg_sessions=1.5"

    # From CSV
    python feature-adoption-scorecard.py --csv features.csv

    # From JSON
    python feature-adoption-scorecard.py --json features.json

    # With target benchmarks
    python feature-adoption-scorecard.py --csv features.csv --target-activation 70 --target-dau-pct 20

CSV format:
    feature,total_users,activated,dau,wau,mau,avg_sessions_per_week,target_dau
    AI Search,50000,35000,8000,18000,30000,4.2,10000
    Dark Mode,50000,42000,20000,35000,40000,12,
    Export PDF,50000,5000,800,2500,4000,1.5,

    Required: feature, total_users, activated
    Optional: dau, wau, mau, avg_sessions_per_week, target_dau

JSON format:
    {
      "total_users": 50000,
      "features": [
        {
          "name": "AI Search",
          "activated": 35000,
          "dau": 8000,
          "wau": 18000,
          "mau": 30000,
          "avg_sessions_per_week": 4.2
        }
      ]
    }

Requirements:
    None (stdlib only).
"""

import argparse
import csv
import json
import math
import sys
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Adoption scoring
# ---------------------------------------------------------------------------

def score_feature(
    name: str,
    total_users: int,
    activated: int,
    dau: int = 0,
    wau: int = 0,
    mau: int = 0,
    avg_sessions_per_week: float = 0,
    target_dau: Optional[int] = None,
    target_activation_pct: float = 70,
    target_dau_pct: float = 20,
) -> Dict[str, Any]:
    """Score a feature across adoption dimensions."""

    # Activation rate
    activation_pct = activated / total_users * 100 if total_users > 0 else 0
    activation_score = min(100, activation_pct / target_activation_pct * 100)

    # DAU penetration (% of total users)
    dau_pct = dau / total_users * 100 if total_users > 0 else 0
    dau_target = target_dau_pct
    dau_score = min(100, dau_pct / dau_target * 100) if dau_target > 0 else 0

    # Stickiness (DAU/MAU ratio) — how habit-forming
    stickiness = dau / mau * 100 if mau > 0 else 0
    stickiness_score = min(100, stickiness / 20 * 100)  # 20% DAU/MAU is good

    # Breadth (WAU/MAU) — weekly engagement breadth
    breadth = wau / mau * 100 if mau > 0 else 0
    breadth_score = min(100, breadth / 50 * 100)  # 50% WAU/MAU is good

    # Frequency (avg sessions per week)
    frequency_score = min(100, avg_sessions_per_week / 5 * 100) if avg_sessions_per_week > 0 else 0

    # Overall adoption score (weighted)
    weights = {
        "activation": 0.25,
        "dau_penetration": 0.25,
        "stickiness": 0.20,
        "breadth": 0.15,
        "frequency": 0.15,
    }
    scores = {
        "activation": activation_score,
        "dau_penetration": dau_score,
        "stickiness": stickiness_score,
        "breadth": breadth_score,
        "frequency": frequency_score,
    }
    overall = sum(scores[k] * weights[k] for k in weights)

    # Grade
    if overall >= 80:
        grade = "A"
        grade_label = "🟢 Strong adoption"
    elif overall >= 60:
        grade = "B"
        grade_label = "🟢 Good adoption"
    elif overall >= 40:
        grade = "C"
        grade_label = "🟡 Moderate — needs investment"
    elif overall >= 20:
        grade = "D"
        grade_label = "🟠 Weak — consider redesign"
    else:
        grade = "F"
        grade_label = "🔴 Poor — consider sunsetting"

    # Recommendation
    recommendations = []
    if activation_score < 50:
        recommendations.append("Low activation — improve discoverability and onboarding")
    if dau_score < 40 and activation_score >= 50:
        recommendations.append("Activated but not used daily — strengthen value prop")
    if stickiness < 10:
        recommendations.append("Low stickiness (DAU/MAU <10%) — feature isn't habit-forming")
    if avg_sessions_per_week < 2 and dau > 0:
        recommendations.append("Low frequency — consider triggers, notifications, or nudges")
    if breadth_score > 80 and stickiness < 15:
        recommendations.append("High breadth but low stickiness — users try but don't return daily")
    if overall >= 70 and not recommendations:
        recommendations.append("Strong feature — consider expanding scope or upselling")

    return {
        "name": name,
        "total_users": total_users,
        "activated": activated,
        "dau": dau,
        "wau": wau,
        "mau": mau,
        "avg_sessions_per_week": avg_sessions_per_week,
        "activation_pct": round(activation_pct, 1),
        "dau_pct": round(dau_pct, 1),
        "stickiness_pct": round(stickiness, 1),
        "breadth_pct": round(breadth, 1),
        "scores": {k: round(v, 1) for k, v in scores.items()},
        "overall_score": round(overall, 1),
        "grade": grade,
        "grade_label": grade_label,
        "recommendations": recommendations,
    }


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def parse_feature_string(s: str, default_total: int = 0) -> Dict[str, Any]:
    """Parse 'Name:key=val,key=val,...'."""
    parts = s.split(":", 1)
    if len(parts) < 2:
        raise ValueError(f"Invalid feature '{s}'. Format: 'Name:total=N,activated=M,...'")

    name = parts[0].strip()
    params: Dict[str, float] = {}
    for kv in parts[1].split(","):
        kv = kv.strip()
        if "=" in kv:
            k, v = kv.split("=", 1)
            try:
                params[k.strip().lower()] = float(v.strip())
            except ValueError:
                pass

    total = int(params.get("total", params.get("total_users", default_total)))
    activated = int(params.get("activated", 0))
    dau = int(params.get("dau", 0))
    wau = int(params.get("wau", 0))
    mau = int(params.get("mau", 0))
    avg_sessions = params.get("avg_sessions", params.get("avg_sessions_per_week", 0))

    return {
        "name": name,
        "total_users": total,
        "activated": activated,
        "dau": dau,
        "wau": wau,
        "mau": mau,
        "avg_sessions_per_week": avg_sessions,
    }


def _col(fieldnames: List[str], *aliases: str) -> Optional[str]:
    lower_map = {f.lower().strip(): f for f in fieldnames}
    for alias in aliases:
        if alias.lower().strip() in lower_map:
            return lower_map[alias.lower().strip()]
    return None


def load_csv(path: str) -> List[Dict[str, Any]]:
    """Load feature data from CSV."""
    features: List[Dict[str, Any]] = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fields = reader.fieldnames or []

        c_name = _col(fields, "feature", "name", "feature_name")
        c_total = _col(fields, "total_users", "total", "users", "base")
        c_activated = _col(fields, "activated", "activations", "adopted", "enabled")
        c_dau = _col(fields, "dau", "daily_active", "daily_users")
        c_wau = _col(fields, "wau", "weekly_active", "weekly_users")
        c_mau = _col(fields, "mau", "monthly_active", "monthly_users")
        c_freq = _col(fields, "avg_sessions_per_week", "avg_sessions", "frequency", "sessions")

        for row in reader:
            name = row.get(c_name or "feature", "").strip()
            if not name:
                continue

            def _num(col: Optional[str], default: float = 0) -> float:
                if not col:
                    return default
                raw = row.get(col, "").strip().replace(",", "")
                try:
                    return float(raw) if raw else default
                except ValueError:
                    return default

            features.append({
                "name": name,
                "total_users": int(_num(c_total)),
                "activated": int(_num(c_activated)),
                "dau": int(_num(c_dau)),
                "wau": int(_num(c_wau)),
                "mau": int(_num(c_mau)),
                "avg_sessions_per_week": _num(c_freq),
            })

    return features


def load_json(path: str) -> List[Dict[str, Any]]:
    """Load feature data from JSON."""
    with open(path, encoding="utf-8") as f:
        config = json.load(f)

    default_total = config.get("total_users", 0)
    features = []
    for feat in config.get("features", []):
        features.append({
            "name": feat.get("name", ""),
            "total_users": feat.get("total_users", default_total),
            "activated": feat.get("activated", 0),
            "dau": feat.get("dau", 0),
            "wau": feat.get("wau", 0),
            "mau": feat.get("mau", 0),
            "avg_sessions_per_week": feat.get("avg_sessions_per_week", 0),
        })

    return features


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def _bar(value: float, max_val: float, width: int = 20) -> str:
    if max_val <= 0:
        return "░" * width
    ratio = min(1.0, max(0.0, value / max_val))
    filled = int(ratio * width)
    return "█" * filled + "░" * (width - filled)


def _score_bar(score: float, width: int = 15) -> str:
    filled = int(score / 100 * width)
    return "█" * filled + "░" * (width - filled)


def _fmt_users(val: int) -> str:
    if val >= 1_000_000:
        return f"{val / 1_000_000:,.1f}M"
    elif val >= 1_000:
        return f"{val / 1_000:,.1f}K"
    else:
        return f"{val:,}"


def print_report(features: List[Dict[str, Any]]) -> None:
    """Pretty-print feature adoption scorecard."""
    print("\n" + "=" * 78)
    print("📊 FEATURE ADOPTION SCORECARD")
    print("=" * 78)

    # Summary table
    print(f"\n{'─'*78}")
    print(f"\n   {'Feature':<20} {'Score':>6} {'Grade':<3} {'Activation':>11} {'DAU %':>7} {'Sticky':>7}")
    print(f"   {'─'*20} {'─'*6} {'─'*3} {'─'*11} {'─'*7} {'─'*7}")

    features.sort(key=lambda x: -x["overall_score"])
    for feat in features:
        print(
            f"   {feat['name'][:20]:<20} "
            f"{feat['overall_score']:>5.0f}% "
            f" {feat['grade']:<2} "
            f"{feat['activation_pct']:>10.1f}% "
            f"{feat['dau_pct']:>6.1f}% "
            f"{feat['stickiness_pct']:>6.1f}%"
        )

    # Detailed per-feature view
    for feat in features:
        print(f"\n{'─'*78}")
        print(f"\n   🏷️  {feat['name'].upper()}  —  {feat['grade_label']}  (score: {feat['overall_score']:.0f}/100)\n")

        # User funnel
        print(f"   User base:     {_fmt_users(feat['total_users'])}")
        print(f"   Activated:     {_fmt_users(feat['activated'])} ({feat['activation_pct']:.1f}%)")
        if feat["mau"] > 0:
            print(f"   MAU:           {_fmt_users(feat['mau'])}")
        if feat["wau"] > 0:
            print(f"   WAU:           {_fmt_users(feat['wau'])}")
        if feat["dau"] > 0:
            print(f"   DAU:           {_fmt_users(feat['dau'])}")
        if feat["avg_sessions_per_week"] > 0:
            print(f"   Avg sessions:  {feat['avg_sessions_per_week']:.1f}/week")

        # Dimension scores
        print(f"\n   📊 DIMENSION SCORES:")
        scores = feat["scores"]
        dims = [
            ("Activation", scores["activation"]),
            ("DAU Penetration", scores["dau_penetration"]),
            ("Stickiness", scores["stickiness"]),
            ("Breadth", scores["breadth"]),
            ("Frequency", scores["frequency"]),
        ]
        max_score = 100
        for dim_name, dim_score in dims:
            bar = _score_bar(dim_score)
            print(f"   {dim_name:<18} {bar} {dim_score:.0f}%")

        # Engagement funnel visual
        if feat["total_users"] > 0:
            print(f"\n   🔻 ENGAGEMENT FUNNEL:")
            funnel = [
                ("Total users", feat["total_users"]),
                ("Activated", feat["activated"]),
            ]
            if feat["mau"] > 0:
                funnel.append(("MAU", feat["mau"]))
            if feat["wau"] > 0:
                funnel.append(("WAU", feat["wau"]))
            if feat["dau"] > 0:
                funnel.append(("DAU", feat["dau"]))

            for label, count in funnel:
                bar = _bar(count, feat["total_users"], 25)
                pct = count / feat["total_users"] * 100
                print(f"   {label:<14} {bar} {_fmt_users(count)} ({pct:.0f}%)")

        # Recommendations
        if feat["recommendations"]:
            print(f"\n   💡 RECOMMENDATIONS:")
            for rec in feat["recommendations"]:
                print(f"   • {rec}")

    # Portfolio view
    print(f"\n{'─'*78}")
    print(f"\n📋 PORTFOLIO SUMMARY:\n")

    grades = {"A": 0, "B": 0, "C": 0, "D": 0, "F": 0}
    for feat in features:
        grades[feat["grade"]] = grades.get(feat["grade"], 0) + 1

    for grade in ["A", "B", "C", "D", "F"]:
        count = grades[grade]
        if count > 0:
            names = [f["name"] for f in features if f["grade"] == grade]
            print(f"   {grade}: {count} feature{'s' if count > 1 else ''} — {', '.join(names)}")

    avg_score = sum(f["overall_score"] for f in features) / len(features) if features else 0
    print(f"\n   Portfolio average: {avg_score:.0f}/100")

    # Quadrant analysis
    print(f"\n   📐 ADOPTION QUADRANT:")
    print(f"   High activation + High DAU = Stars (invest more)")
    print(f"   High activation + Low DAU  = Sleepers (improve engagement)")
    print(f"   Low activation  + High DAU = Hidden Gems (improve discovery)")
    print(f"   Low activation  + Low DAU  = Candidates for sunset")

    median_act = sorted(f["activation_pct"] for f in features)[len(features) // 2] if features else 50
    median_dau = sorted(f["dau_pct"] for f in features)[len(features) // 2] if features else 10

    for feat in features:
        high_act = feat["activation_pct"] >= median_act
        high_dau = feat["dau_pct"] >= median_dau
        if high_act and high_dau:
            quad = "⭐ Star"
        elif high_act and not high_dau:
            quad = "😴 Sleeper"
        elif not high_act and high_dau:
            quad = "💎 Hidden Gem"
        else:
            quad = "🌅 Sunset candidate"
        print(f"   {quad:<20} {feat['name']}")

    # Guidance
    print(f"\n{'─'*78}")
    print(f"\n💡 ADOPTION BENCHMARKS:")
    print(f"   • Activation >70% = feature is discoverable and valuable")
    print(f"   • DAU/MAU >20% = strong daily habit")
    print(f"   • WAU/MAU >50% = good weekly engagement breadth")
    print(f"   • Avg sessions >5/week = power feature")
    print(f"   • Features scoring <20 for 2+ quarters = consider sunsetting")
    print("\n" + "=" * 78)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Score feature adoption across activation, DAU penetration, stickiness, "
                    "breadth, and frequency. Helps PMs prioritize feature investment.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --feature "AI Search:total=50000,activated=35000,dau=8000,wau=18000,mau=30000,avg_sessions=4.2"
  %(prog)s --csv features.csv
  %(prog)s --json features.json --target-activation 60
        """,
    )

    parser.add_argument("--feature", type=str, action="append",
                        help="Feature: 'Name:total=N,activated=M,dau=D,wau=W,mau=MAU,avg_sessions=F'")
    parser.add_argument("--csv", "-c", type=str, help="CSV file with feature data")
    parser.add_argument("--json", "-j", type=str, help="JSON file with feature data")
    parser.add_argument("--target-activation", type=float, default=70,
                        help="Target activation %% (default: 70)")
    parser.add_argument("--target-dau-pct", type=float, default=20,
                        help="Target DAU as %% of total users (default: 20)")
    parser.add_argument("--output", "-o", type=str, help="Write JSON results to file")
    args = parser.parse_args()

    raw_features: List[Dict[str, Any]] = []

    if args.csv:
        try:
            raw_features = load_csv(args.csv)
        except Exception as e:
            print(f"Error loading CSV: {e}", file=sys.stderr)
            return 1
    elif args.json:
        try:
            raw_features = load_json(args.json)
        except Exception as e:
            print(f"Error loading JSON: {e}", file=sys.stderr)
            return 1

    if args.feature:
        for f_str in args.feature:
            try:
                raw_features.append(parse_feature_string(f_str))
            except ValueError as e:
                print(f"Error: {e}", file=sys.stderr)
                return 1

    if not raw_features:
        print("Error: provide feature data via --feature, --csv, or --json.", file=sys.stderr)
        parser.print_help(sys.stderr)
        return 1

    # Score features
    scored = []
    for feat in raw_features:
        scored.append(score_feature(
            name=feat["name"],
            total_users=feat["total_users"],
            activated=feat["activated"],
            dau=feat["dau"],
            wau=feat["wau"],
            mau=feat["mau"],
            avg_sessions_per_week=feat["avg_sessions_per_week"],
            target_activation_pct=args.target_activation,
            target_dau_pct=args.target_dau_pct,
        ))

    # Report
    print_report(scored)

    # JSON output
    if args.output:
        with open(args.output, "w") as f:
            json.dump({"features": scored}, f, indent=2)
        print(f"\n📁 Results saved to {args.output}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
