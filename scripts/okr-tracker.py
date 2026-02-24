#!/usr/bin/env python3
"""
OKR Progress Tracker

Track Objectives and Key Results with progress scoring, health assessment,
confidence ratings, and trend analysis. Helps PMs keep OKRs on track
mid-cycle and prepare for reviews.

Scoring follows Google's 0.0–1.0 scale:
    0.0–0.3  = Off track (red)
    0.3–0.7  = Making progress (yellow)
    0.7–1.0  = On track / achieved (green)

Usage:
    # Inline OKRs
    python okr-tracker.py \\
        --objective "Improve user activation" \\
        --kr "Increase onboarding completion from 45% to 70%:current=58" \\
        --kr "Reduce time-to-value from 14d to 7d:current=10" \\
        --kr "Grow weekly active users by 30%:current=18"

    # From JSON
    python okr-tracker.py --json okrs.json

    # From CSV
    python okr-tracker.py --csv okrs.csv

    # With timeline context
    python okr-tracker.py --json okrs.json --cycle-days 90 --elapsed-days 45

JSON format:
    {
      "cycle": "Q1 2025",
      "cycle_days": 90,
      "elapsed_days": 45,
      "objectives": [
        {
          "name": "Improve user activation",
          "owner": "Product",
          "key_results": [
            {
              "name": "Increase onboarding completion from 45% to 70%",
              "start": 45, "target": 70, "current": 58,
              "confidence": 0.7, "unit": "%"
            },
            {
              "name": "Reduce time-to-value from 14d to 7d",
              "start": 14, "target": 7, "current": 10,
              "confidence": 0.5, "unit": "days"
            }
          ]
        }
      ]
    }

CSV format:
    objective,key_result,start,target,current,confidence,owner,unit
    Improve activation,Onboarding completion 45→70%,45,70,58,0.7,Product,%
    Improve activation,Time-to-value 14d→7d,14,7,10,0.5,Product,days
    Grow revenue,Expand ARPU $50→$65,50,65,55,0.6,Growth,$

Requirements:
    None (stdlib only).
"""

import argparse
import csv
import json
import sys
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# OKR scoring
# ---------------------------------------------------------------------------

def score_kr(
    start: float,
    target: float,
    current: float,
) -> float:
    """
    Score a key result on Google's 0.0–1.0 scale.
    Handles both increasing and decreasing targets.
    """
    total_delta = target - start
    if total_delta == 0:
        return 1.0 if current == target else 0.0

    progress = (current - start) / total_delta
    return max(0.0, min(1.0, progress))


def assess_kr(
    name: str,
    start: float,
    target: float,
    current: float,
    confidence: Optional[float] = None,
    unit: str = "",
    cycle_days: Optional[int] = None,
    elapsed_days: Optional[int] = None,
) -> Dict[str, Any]:
    """Assess a single key result."""
    score = score_kr(start, target, current)
    remaining = target - current
    total_delta = target - start

    # Direction
    increasing = target > start

    # Health
    if score >= 0.7:
        health = "on_track"
        health_label = "🟢 On track"
    elif score >= 0.3:
        health = "at_risk"
        health_label = "🟡 At risk"
    else:
        health = "off_track"
        health_label = "🔴 Off track"

    # Pace check (are we on schedule given elapsed time?)
    pace_assessment = None
    if cycle_days and elapsed_days and cycle_days > 0:
        time_pct = elapsed_days / cycle_days
        if time_pct > 0:
            pace_ratio = score / time_pct
            if pace_ratio >= 0.9:
                pace_assessment = "🟢 Ahead of pace"
            elif pace_ratio >= 0.7:
                pace_assessment = "🟡 Slightly behind"
            else:
                pace_assessment = "🔴 Behind pace"

    return {
        "name": name,
        "start": start,
        "target": target,
        "current": current,
        "remaining": round(remaining, 2),
        "unit": unit,
        "score": round(score, 2),
        "score_pct": round(score * 100, 1),
        "health": health,
        "health_label": health_label,
        "confidence": confidence,
        "increasing": increasing,
        "pace_assessment": pace_assessment,
    }


def assess_objective(
    name: str,
    key_results: List[Dict[str, Any]],
    owner: str = "",
) -> Dict[str, Any]:
    """Assess an objective from its key results."""
    if not key_results:
        return {"name": name, "owner": owner, "score": 0, "key_results": [], "health": "off_track"}

    scores = [kr["score"] for kr in key_results]
    avg_score = sum(scores) / len(scores)

    confidences = [kr["confidence"] for kr in key_results if kr["confidence"] is not None]
    avg_confidence = sum(confidences) / len(confidences) if confidences else None

    if avg_score >= 0.7:
        health = "on_track"
        health_label = "🟢 On track"
    elif avg_score >= 0.3:
        health = "at_risk"
        health_label = "🟡 At risk"
    else:
        health = "off_track"
        health_label = "🔴 Off track"

    # Count KR statuses
    on_track = sum(1 for kr in key_results if kr["health"] == "on_track")
    at_risk = sum(1 for kr in key_results if kr["health"] == "at_risk")
    off_track = sum(1 for kr in key_results if kr["health"] == "off_track")

    return {
        "name": name,
        "owner": owner,
        "score": round(avg_score, 2),
        "score_pct": round(avg_score * 100, 1),
        "health": health,
        "health_label": health_label,
        "avg_confidence": round(avg_confidence, 2) if avg_confidence is not None else None,
        "n_key_results": len(key_results),
        "on_track": on_track,
        "at_risk": at_risk,
        "off_track": off_track,
        "key_results": key_results,
    }


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def parse_kr_string(s: str) -> Dict[str, Any]:
    """
    Parse 'KR description:current=N' or 'KR description:start=A,target=B,current=C'.
    Tries to extract start/target from the description (e.g. 'from 45% to 70%').
    """
    parts = s.rsplit(":", 1)
    if len(parts) < 2:
        raise ValueError(f"Invalid KR '{s}'. Format: 'Description:current=N'")

    name = parts[0].strip()
    params_str = parts[1].strip()

    params: Dict[str, float] = {}
    for kv in params_str.split(","):
        kv = kv.strip()
        if "=" in kv:
            k, v = kv.split("=", 1)
            try:
                params[k.strip().lower()] = float(v.strip().rstrip("%"))
            except ValueError:
                pass

    current = params.get("current", 0)
    start = params.get("start")
    target = params.get("target")
    confidence = params.get("confidence")

    # Try extracting from description
    if start is None or target is None:
        import re
        match = re.search(r'from\s+([\d.]+)\S*\s+to\s+([\d.]+)', name, re.IGNORECASE)
        if match:
            if start is None:
                start = float(match.group(1))
            if target is None:
                target = float(match.group(2))
        else:
            match = re.search(r'by\s+([\d.]+)', name, re.IGNORECASE)
            if match:
                if start is None:
                    start = 0
                if target is None:
                    target = float(match.group(1))

    if start is None:
        start = 0
    if target is None:
        raise ValueError(f"Cannot determine target for KR '{name}'. Use 'start=X,target=Y,current=Z'")

    return {
        "name": name,
        "start": start,
        "target": target,
        "current": current,
        "confidence": confidence,
    }


def _col(fieldnames: List[str], *aliases: str) -> Optional[str]:
    lower_map = {f.lower().strip(): f for f in fieldnames}
    for alias in aliases:
        if alias.lower().strip() in lower_map:
            return lower_map[alias.lower().strip()]
    return None


def load_csv(
    path: str,
    cycle_days: Optional[int] = None,
    elapsed_days: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """Load OKRs from CSV. Returns list of objective assessments."""
    objectives_map: Dict[str, Dict[str, Any]] = {}

    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fields = reader.fieldnames or []

        c_obj = _col(fields, "objective", "obj", "goal")
        c_kr = _col(fields, "key_result", "kr", "result", "metric")
        c_start = _col(fields, "start", "baseline", "from", "initial")
        c_target = _col(fields, "target", "goal", "to", "end")
        c_current = _col(fields, "current", "actual", "progress", "value")
        c_confidence = _col(fields, "confidence", "conf")
        c_owner = _col(fields, "owner", "team", "responsible")
        c_unit = _col(fields, "unit", "units", "measure")

        for row in reader:
            obj_name = row.get(c_obj or "objective", "").strip()
            kr_name = row.get(c_kr or "key_result", "").strip()
            if not obj_name or not kr_name:
                continue

            def _num(col: Optional[str], default: Optional[float] = None) -> Optional[float]:
                if not col:
                    return default
                raw = row.get(col, "").strip().rstrip("%").replace(",", "").replace("$", "")
                try:
                    return float(raw) if raw else default
                except ValueError:
                    return default

            start = _num(c_start, 0)
            target = _num(c_target)
            current = _num(c_current, 0)
            confidence = _num(c_confidence)
            owner = row.get(c_owner or "owner", "").strip()
            unit = row.get(c_unit or "unit", "").strip()

            if target is None:
                continue

            kr = assess_kr(kr_name, start, target, current, confidence, unit, cycle_days, elapsed_days)

            if obj_name not in objectives_map:
                objectives_map[obj_name] = {"name": obj_name, "owner": owner, "krs": []}
            objectives_map[obj_name]["krs"].append(kr)

    results = []
    for obj_data in objectives_map.values():
        results.append(assess_objective(obj_data["name"], obj_data["krs"], obj_data["owner"]))

    return results


def load_json(
    path: str,
    cycle_days: Optional[int] = None,
    elapsed_days: Optional[int] = None,
) -> Tuple[List[Dict[str, Any]], Optional[str], Optional[int], Optional[int]]:
    """Load OKRs from JSON."""
    with open(path, encoding="utf-8") as f:
        config = json.load(f)

    cycle = config.get("cycle")
    cd = config.get("cycle_days", cycle_days)
    ed = config.get("elapsed_days", elapsed_days)

    results = []
    for obj in config.get("objectives", []):
        krs = []
        for kr_data in obj.get("key_results", []):
            kr = assess_kr(
                kr_data.get("name", ""),
                kr_data.get("start", 0),
                kr_data.get("target", 0),
                kr_data.get("current", 0),
                kr_data.get("confidence"),
                kr_data.get("unit", ""),
                cd, ed,
            )
            krs.append(kr)
        results.append(assess_objective(
            obj.get("name", "Unnamed"),
            krs,
            obj.get("owner", ""),
        ))

    return results, cycle, cd, ed


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def _bar(value: float, max_val: float, width: int = 25) -> str:
    if max_val <= 0:
        return "░" * width
    ratio = min(1.0, max(0.0, value / max_val))
    filled = int(ratio * width)
    return "█" * filled + "░" * (width - filled)


def _score_bar(score: float, width: int = 20) -> str:
    filled = int(score * width)
    return "█" * filled + "░" * (width - filled)


def print_report(
    objectives: List[Dict[str, Any]],
    cycle: Optional[str] = None,
    cycle_days: Optional[int] = None,
    elapsed_days: Optional[int] = None,
) -> None:
    """Pretty-print OKR progress report."""
    print("\n" + "=" * 78)
    print("🎯 OKR PROGRESS TRACKER")
    print("=" * 78)

    if cycle:
        print(f"\n   Cycle: {cycle}")
    if cycle_days and elapsed_days:
        time_pct = elapsed_days / cycle_days * 100
        remaining = cycle_days - elapsed_days
        print(f"   Timeline: Day {elapsed_days}/{cycle_days} ({time_pct:.0f}% elapsed, {remaining} days left)")
        print(f"   Progress: {_score_bar(elapsed_days / cycle_days, 30)} {time_pct:.0f}%")

    # Overall summary
    all_scores = [obj["score"] for obj in objectives]
    overall = sum(all_scores) / len(all_scores) if all_scores else 0
    total_krs = sum(obj["n_key_results"] for obj in objectives)
    total_on = sum(obj["on_track"] for obj in objectives)
    total_risk = sum(obj["at_risk"] for obj in objectives)
    total_off = sum(obj["off_track"] for obj in objectives)

    print(f"\n{'─'*78}")
    print(f"\n📊 OVERALL SUMMARY:\n")
    print(f"   Objectives:     {len(objectives)}")
    print(f"   Key Results:    {total_krs}")
    print(f"   Overall score:  {overall:.2f}  ({overall*100:.0f}%)")
    print(f"   Health: 🟢 {total_on}  🟡 {total_risk}  🔴 {total_off}")

    # Per objective
    for obj in objectives:
        print(f"\n{'─'*78}")
        owner_str = f"  [{obj['owner']}]" if obj["owner"] else ""
        print(f"\n   🏁 {obj['name'].upper()}{owner_str}")
        print(f"   Score: {_score_bar(obj['score'])} {obj['score_pct']:.0f}%  {obj['health_label']}")
        if obj["avg_confidence"] is not None:
            conf_pct = obj["avg_confidence"] * 100
            print(f"   Confidence: {conf_pct:.0f}%")

        # Key results
        print(f"\n   {'Key Result':<40} {'Progress':>10} {'Score':>6} {'Health'}")
        print(f"   {'─'*40} {'─'*10} {'─'*6} {'─'*12}")

        for kr in obj["key_results"]:
            direction = "↑" if kr["increasing"] else "↓"
            unit = kr["unit"]

            if kr["increasing"]:
                progress_str = f"{kr['current']}{unit}/{kr['target']}{unit}"
            else:
                progress_str = f"{kr['current']}{unit}→{kr['target']}{unit}"

            print(
                f"   {kr['name'][:40]:<40} "
                f"{progress_str:>10} "
                f"{kr['score_pct']:>5.0f}% "
                f"{kr['health_label']}"
            )

        # KR detail bars
        print(f"\n   Progress bars:")
        for kr in obj["key_results"]:
            bar = _score_bar(kr["score"], 25)
            conf_str = ""
            if kr["confidence"] is not None:
                conf_str = f" (conf: {kr['confidence']*100:.0f}%)"
            pace_str = f"  {kr['pace_assessment']}" if kr.get("pace_assessment") else ""
            print(f"   {kr['name'][:28]:<28} {bar} {kr['score_pct']:.0f}%{conf_str}{pace_str}")

    # Score distribution
    print(f"\n{'─'*78}")
    print(f"\n📈 SCORE DISTRIBUTION:\n")

    all_kr_scores = []
    for obj in objectives:
        for kr in obj["key_results"]:
            all_kr_scores.append(kr["score"])

    if all_kr_scores:
        green = sum(1 for s in all_kr_scores if s >= 0.7)
        yellow = sum(1 for s in all_kr_scores if 0.3 <= s < 0.7)
        red = sum(1 for s in all_kr_scores if s < 0.3)
        total = len(all_kr_scores)

        print(f"   🟢 On track (≥70%):      {green:>3} ({green/total*100:.0f}%)")
        print(f"   🟡 At risk (30-70%):      {yellow:>3} ({yellow/total*100:.0f}%)")
        print(f"   🔴 Off track (<30%):      {red:>3} ({red/total*100:.0f}%)")

    # Action items
    at_risk_krs = []
    off_track_krs = []
    for obj in objectives:
        for kr in obj["key_results"]:
            if kr["health"] == "off_track":
                off_track_krs.append((obj["name"], kr))
            elif kr["health"] == "at_risk":
                at_risk_krs.append((obj["name"], kr))

    if off_track_krs or at_risk_krs:
        print(f"\n{'─'*78}")
        print(f"\n⚡ ACTION ITEMS:\n")
        for obj_name, kr in off_track_krs:
            print(f"   🔴 [{obj_name}] '{kr['name']}' — {kr['score_pct']:.0f}% complete, needs intervention")
        for obj_name, kr in at_risk_krs:
            print(f"   🟡 [{obj_name}] '{kr['name']}' — {kr['score_pct']:.0f}% complete, monitor closely")

    # Guidance
    print(f"\n{'─'*78}")
    print(f"\n💡 OKR BEST PRACTICES:")
    print(f"   • Target 0.7 score — consistently hitting 1.0 means goals aren't ambitious enough")
    print(f"   • Update KRs weekly; review objectives monthly")
    print(f"   • 3-5 KRs per objective keeps focus sharp")
    print(f"   • If a KR is off track at 50% elapsed, escalate or re-scope")
    print(f"   • Separate committed OKRs (must-do) from aspirational OKRs (stretch)")
    print("\n" + "=" * 78)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Track OKR progress with scoring, health assessment, and trend analysis. "
                    "Helps PMs keep objectives on track mid-cycle.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --objective "Improve activation" \\
           --kr "Onboarding completion from 45%% to 70%%:current=58" \\
           --kr "Reduce time-to-value from 14d to 7d:current=10"
  %(prog)s --json okrs.json --cycle-days 90 --elapsed-days 45
  %(prog)s --csv okrs.csv
        """,
    )

    parser.add_argument("--objective", type=str, help="Objective name (for inline mode)")
    parser.add_argument("--owner", type=str, default="", help="Objective owner")
    parser.add_argument("--kr", type=str, action="append",
                        help="Key result: 'Description:current=N' or 'Description:start=A,target=B,current=C'")

    parser.add_argument("--json", "-j", type=str, help="JSON file with OKR data")
    parser.add_argument("--csv", "-c", type=str, help="CSV file with OKR data")

    parser.add_argument("--cycle", type=str, help="Cycle name (e.g. 'Q1 2025')")
    parser.add_argument("--cycle-days", type=int, help="Total days in cycle")
    parser.add_argument("--elapsed-days", type=int, help="Days elapsed in cycle")

    parser.add_argument("--output", "-o", type=str, help="Write JSON results to file")
    args = parser.parse_args()

    objectives: List[Dict[str, Any]] = []
    cycle = args.cycle
    cycle_days = args.cycle_days
    elapsed_days = args.elapsed_days

    if args.json:
        try:
            objectives, cycle_j, cd_j, ed_j = load_json(args.json, cycle_days, elapsed_days)
            if cycle_j and not cycle:
                cycle = cycle_j
            if cd_j and not cycle_days:
                cycle_days = cd_j
            if ed_j and not elapsed_days:
                elapsed_days = ed_j
        except Exception as e:
            print(f"Error loading JSON: {e}", file=sys.stderr)
            return 1

    elif args.csv:
        try:
            objectives = load_csv(args.csv, cycle_days, elapsed_days)
        except Exception as e:
            print(f"Error loading CSV: {e}", file=sys.stderr)
            return 1

    elif args.objective and args.kr:
        krs = []
        for kr_str in args.kr:
            try:
                kr_data = parse_kr_string(kr_str)
            except ValueError as e:
                print(f"Error: {e}", file=sys.stderr)
                return 1
            kr = assess_kr(
                kr_data["name"], kr_data["start"], kr_data["target"],
                kr_data["current"], kr_data.get("confidence"),
                "", cycle_days, elapsed_days,
            )
            krs.append(kr)
        objectives.append(assess_objective(args.objective, krs, args.owner))

    else:
        print("Error: provide --objective + --kr, --json, or --csv.", file=sys.stderr)
        parser.print_help(sys.stderr)
        return 1

    # Report
    print_report(objectives, cycle, cycle_days, elapsed_days)

    # JSON output
    if args.output:
        report = {
            "cycle": cycle,
            "cycle_days": cycle_days,
            "elapsed_days": elapsed_days,
            "objectives": objectives,
        }
        with open(args.output, "w") as f:
            json.dump(report, f, indent=2)
        print(f"\n📁 Results saved to {args.output}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
