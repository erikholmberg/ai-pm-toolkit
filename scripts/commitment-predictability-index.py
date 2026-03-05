#!/usr/bin/env python3
"""
Commitment Predictability Index

Measure how predictably the team delivers on sprint commitments. Uses sprint
history (committed vs completed points) to compute a 0–100 index combining
accuracy (mean completion rate) and consistency (low variance in that rate).
Helps set realistic commitments and spot predictability trends.

Usage:
    # From CSV (same format as velocity tracker)
    python commitment-predictability-index.py --csv velocity.csv

    # Inline sprint data
    python commitment-predictability-index.py \\
        --sprint "S1:34:40" --sprint "S2:38:42" --sprint "S3:36:38" --sprint "S4:41:45"

    # With within-threshold hit rate (pct of sprints within 15% of commitment)
    python commitment-predictability-index.py --csv velocity.csv --tolerance 15

    # Export
    python commitment-predictability-index.py --csv velocity.csv --markdown report.md --output report.json

CSV format (same as sprint-velocity-tracker):
    sprint,completed,committed,carry_over
    Sprint 1,34,40,6
    Sprint 2,38,42,4

    Required: sprint, completed, committed (for predictability; committed=0 sprints are skipped).
    Optional: carry_over.

Index formula:
    - Per-sprint ratio = completed / committed.
    - Mean accuracy = mean(ratio) × 100.
    - Consistency = 1 - min(CV of ratios, 1); CV = std/mean.
    - Index = min(100, mean_accuracy × consistency). High = accurate and stable.

Requirements:
    None (stdlib only).
"""

import argparse
import csv
import json
import math
import sys
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Analysis
# ---------------------------------------------------------------------------

def analyze_sprint(label: str, completed: float, committed: float) -> Dict[str, Any]:
    """Per-sprint completion ratio (for predictability)."""
    ratio = (completed / committed) if committed > 0 else None
    accuracy_pct = (ratio * 100) if ratio is not None else None
    return {
        "label": label,
        "completed": completed,
        "committed": committed,
        "ratio": ratio,
        "accuracy_pct": round(accuracy_pct, 1) if accuracy_pct is not None else None,
    }


def compute_predictability_index(
    sprints: List[Dict[str, Any]],
    tolerance_pct: float = 15,
) -> Dict[str, Any]:
    """
    Compute commitment predictability index from sprint history.
    Only sprints with committed > 0 are used.
    """
    with_commitment = [s for s in sprints if s.get("committed", 0) > 0]
    if not with_commitment:
        return {
            "error": "No sprints with committed > 0",
            "sprints_analyzed": 0,
            "index": None,
            "mean_accuracy_pct": None,
            "cv_pct": None,
            "hit_rate_pct": None,
            "level": None,
        }

    ratios = [s["ratio"] for s in with_commitment if s.get("ratio") is not None]
    if not ratios:
        return {
            "error": "No valid completion ratios",
            "sprints_analyzed": len(with_commitment),
            "index": None,
            "mean_accuracy_pct": None,
            "cv_pct": None,
            "hit_rate_pct": None,
            "level": None,
        }

    n = len(ratios)
    mean_ratio = sum(ratios) / n
    mean_accuracy_pct = mean_ratio * 100
    var = sum((r - mean_ratio) ** 2 for r in ratios) / max(n - 1, 1)
    std_ratio = math.sqrt(var)
    cv_ratio = (std_ratio / mean_ratio) if mean_ratio > 0 else 0
    cv_pct = cv_ratio * 100
    consistency = max(0.0, 1.0 - min(cv_ratio, 1.0))
    index = min(100.0, mean_accuracy_pct * consistency)

    # Hit rate: % of sprints where completion was within tolerance_pct of commitment
    hit_count = sum(
        1 for s in with_commitment
        if s.get("accuracy_pct") is not None
        and abs(s["accuracy_pct"] - 100) <= tolerance_pct
    )
    hit_rate_pct = (hit_count / n * 100) if n else 0

    if index >= 70:
        level = "high"
        level_label = "🟢 High predictability"
    elif index >= 40:
        level = "medium"
        level_label = "🟡 Medium predictability"
    else:
        level = "low"
        level_label = "🔴 Low predictability"

    return {
        "sprints_analyzed": n,
        "sprints": with_commitment,
        "index": round(index, 1),
        "mean_accuracy_pct": round(mean_accuracy_pct, 1),
        "cv_pct": round(cv_pct, 1),
        "consistency": round(consistency, 3),
        "hit_rate_pct": round(hit_rate_pct, 1),
        "tolerance_pct": tolerance_pct,
        "level": level,
        "level_label": level_label,
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


def parse_sprint_string(s: str) -> Dict[str, Any]:
    """Parse 'Label:completed:committed' or 'Label:completed:committed:carry_over'."""
    parts = s.split(":")
    if len(parts) < 3:
        raise ValueError(f"Invalid sprint '{s}'. Use Label:completed:committed")
    try:
        label = parts[0].strip()
        completed = float(parts[1].strip())
        committed = float(parts[2].strip())
    except (ValueError, IndexError) as e:
        raise ValueError(f"Invalid numbers in '{s}': {e}")
    return analyze_sprint(label, completed, committed)


def load_csv(path: str) -> List[Dict[str, Any]]:
    """Load sprint data from CSV (same columns as velocity tracker)."""
    sprints: List[Dict[str, Any]] = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fields = reader.fieldnames or []

        c_label = _col(fields, "sprint", "name", "label", "iteration")
        c_completed = _col(fields, "completed", "done", "velocity", "points_done", "actual")
        c_committed = _col(fields, "committed", "planned", "points_planned", "target", "scope")

        for row in reader:
            label = (row.get(c_label or "sprint", "") or "").strip()
            if not label:
                continue
            raw_c = (row.get(c_completed or "completed", "") or "").strip().replace(",", "")
            raw_m = (row.get(c_committed or "committed", "") or "").strip().replace(",", "")
            try:
                completed = float(raw_c) if raw_c else 0
                committed = float(raw_m) if raw_m else 0
            except ValueError:
                continue
            sprints.append(analyze_sprint(label, completed, committed))
    return sprints


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def print_report(result: Dict[str, Any], tolerance_pct: float) -> None:
    """Pretty-print predictability index report."""
    print("\n" + "=" * 70)
    print("🎯 COMMITMENT PREDICTABILITY INDEX")
    print("=" * 70)

    if result.get("error"):
        print(f"\n   ⚠️  {result['error']}\n")
        return

    n = result["sprints_analyzed"]
    index = result["index"]
    mean_acc = result["mean_accuracy_pct"]
    cv = result["cv_pct"]
    hit = result["hit_rate_pct"]

    print(f"\n   Sprints analyzed:  {n} (with committed > 0)")
    print(f"\n   Index:            {index:.1f} / 100   {result['level_label']}")
    print(f"   Mean accuracy:   {mean_acc:.1f}% (completed/committed)")
    print(f"   Consistency:     CV = {cv:.1f}% (lower = more stable)")
    print(f"   Hit rate:        {hit:.0f}% of sprints within ±{tolerance_pct:.0f}% of commitment")

    print(f"\n   {'Sprint':<14} {'Done':>6} {'Plan':>6} {'Accuracy':>9}")
    print("   " + "─" * 38)
    for s in result.get("sprints", []):
        acc = s.get("accuracy_pct")
        acc_str = f"{acc:.0f}%" if acc is not None else "—"
        print(f"   {s['label'][:13]:<14} {s['completed']:>6.0f} {s['committed']:>6.0f} {acc_str:>9}")

    print(f"\n   💡 Higher index = more accurate and consistent commitments.")
    print("      Use to set sprint scope and communicate delivery confidence.\n")


def to_json_result(result: Dict[str, Any]) -> Dict[str, Any]:
    """JSON-serializable result; drop full sprint list if large, keep summary."""
    out = {
        "sprints_analyzed": result.get("sprints_analyzed", 0),
        "index": result.get("index"),
        "mean_accuracy_pct": result.get("mean_accuracy_pct"),
        "cv_pct": result.get("cv_pct"),
        "hit_rate_pct": result.get("hit_rate_pct"),
        "tolerance_pct": result.get("tolerance_pct"),
        "level": result.get("level"),
    }
    if result.get("sprints"):
        out["sprints"] = [
            {"label": s["label"], "completed": s["completed"], "committed": s["committed"], "accuracy_pct": s.get("accuracy_pct")}
            for s in result["sprints"]
        ]
    return out


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Compute commitment predictability index from sprint history.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--csv", help="Path to sprint CSV (sprint, completed, committed)")
    parser.add_argument(
        "--sprint",
        action="append",
        dest="sprints",
        metavar="LABEL:DONE:PLAN",
        help="Inline sprint: Label:completed:committed (repeatable)",
    )
    parser.add_argument(
        "--tolerance",
        type=float,
        default=15,
        help="Tolerance for hit rate: pct of sprints within ±N pct of commitment (default: 15)",
    )
    parser.add_argument("--markdown", metavar="FILE", help="Write Markdown report to FILE")
    parser.add_argument("--output", "-o", metavar="FILE", help="Write JSON result to FILE")
    args = parser.parse_args()

    sprints: List[Dict[str, Any]] = []

    if args.csv:
        sprints = load_csv(args.csv)
    if args.sprints:
        for s in args.sprints:
            try:
                sprints.append(parse_sprint_string(s))
            except ValueError as e:
                print(str(e), file=sys.stderr)
                return 1

    if not sprints:
        print("No sprint data. Use --csv or --sprint.", file=sys.stderr)
        return 1

    result = compute_predictability_index(sprints, tolerance_pct=args.tolerance)
    print_report(result, args.tolerance)

    if args.markdown and not result.get("error"):
        with open(args.markdown, "w", encoding="utf-8") as f:
            f.write("# Commitment Predictability Index\n\n")
            f.write(f"- **Index:** {result.get('index')} / 100\n")
            f.write(f"- **Level:** {result.get('level', '').replace('_', ' ').title()}\n")
            f.write(f"- **Mean accuracy:** {result.get('mean_accuracy_pct')}%\n")
            f.write(f"- **Hit rate (within ±{args.tolerance:.0f}%):** {result.get('hit_rate_pct')}%\n\n")
            f.write("| Sprint | Done | Plan | Accuracy |\n")
            f.write("|--------|------|------|----------|\n")
            for s in result.get("sprints", []):
                acc = s.get("accuracy_pct")
                acc_str = f"{acc:.0f}%" if acc is not None else "—"
                f.write(f"| {s['label']} | {s['completed']} | {s['committed']} | {acc_str} |\n")
        print(f"Wrote Markdown to {args.markdown}")

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(to_json_result(result), f, indent=2)
        print(f"Wrote JSON to {args.output}")

    return 0 if not result.get("error") else 1


if __name__ == "__main__":
    sys.exit(main())
