#!/usr/bin/env python3
"""
Bias / Fairness Scorecard

Given a CSV of model predictions labeled by demographic group, compute
standard group-fairness metrics and flag disparities a PM should raise
before launch: selection-rate disparity (the "four-fifths rule" used in EEOC
adverse-impact analysis) and, if ground truth is available, true/false
positive rate gaps across groups (equal opportunity / equalized odds).

This is a statistical first pass, not a fairness determination — see the
caveats in the report output before using this to sign off a launch.

Metrics:
    - Selection rate per group      — % of group given a positive prediction
    - Disparate impact ratio        — group's selection rate ÷ reference
                                       group's selection rate (four-fifths
                                       rule: flag if < 0.8)
    - True positive rate (recall)   — per group, if ground truth present
    - False positive rate           — per group, if ground truth present
    - Equal opportunity gap         — TPR(group) − TPR(reference)
    - Equalized odds gap            — max(|TPR gap|, |FPR gap|)

Usage:
    python bias-fairness-scorecard.py --csv predictions.csv
    python bias-fairness-scorecard.py --csv predictions.csv --reference-group male
    python bias-fairness-scorecard.py --csv predictions.csv --di-threshold 0.8 --tpr-gap-threshold 0.1
    python bias-fairness-scorecard.py --csv predictions.csv --output scorecard.json

CSV format:
    id,group,predicted,actual
    u001,female,approved,approved
    u002,male,approved,denied
    u003,female,denied,denied
    u004,male,approved,approved

    Required columns (fuzzy-matched): group (or segment, demographic,
    cohort), predicted (or prediction, decision, outcome, flagged).
    Optional: actual (or ground_truth, label, true_label) — unlocks TPR/FPR
    gap metrics; without it, only selection-rate disparity is computed.
    Values: yes/y/true/1/approved/positive/flagged = positive outcome;
    anything else = negative.

Requirements:
    None (stdlib only).
"""

import argparse
import csv
import json
import sys
from collections import defaultdict
from typing import Any, Dict, List, Optional

# Shared result envelope (provenance + machine-readable chaining).
# See scripts/toolkit_io.py.
import toolkit_io

TOOL = "bias-fairness-scorecard"

# EEOC Uniform Guidelines four-fifths rule: a selection rate below 80% of the
# reference group's is treated as evidence of adverse impact.
DEFAULT_DI_THRESHOLD = 0.8
# TPR/FPR gap beyond this (10 percentage points) is flagged for review.
DEFAULT_TPR_GAP_THRESHOLD = 0.10

POSITIVE_VALUES = {
    "yes", "y", "true", "1", "positive", "approved", "approve", "flagged",
    "hired", "accepted", "granted", "pass", "passed",
}


def is_positive(val: str) -> bool:
    return str(val).strip().lower() in POSITIVE_VALUES


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
    rows: List[Dict[str, Any]] = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fields = reader.fieldnames or []
        c_id = _col(fields, "id", "case_id", "record_id")
        c_group = _col(fields, "group", "segment", "demographic", "cohort", "protected_group")
        c_pred = _col(fields, "predicted", "prediction", "decision", "outcome", "flagged", "model_output")
        c_actual = _col(fields, "actual", "ground_truth", "label", "true_label", "actual_outcome")

        if not c_group:
            raise ValueError(f"No group column found. CSV has: {', '.join(fields)}")
        if not c_pred:
            raise ValueError(f"No predicted/decision column found. CSV has: {', '.join(fields)}")

        for i, row in enumerate(reader):
            group = (row.get(c_group, "") or "").strip()
            pred_raw = row.get(c_pred, "")
            if not group or pred_raw is None or str(pred_raw).strip() == "":
                continue
            entry = {
                "id": (row.get(c_id, "") or "").strip() or f"row_{i + 1}",
                "group": group,
                "predicted": is_positive(pred_raw),
                "actual": None,
            }
            if c_actual:
                actual_raw = row.get(c_actual, "")
                if actual_raw is not None and str(actual_raw).strip() != "":
                    entry["actual"] = is_positive(actual_raw)
            rows.append(entry)
    return rows


# ---------------------------------------------------------------------------
# Core calculations
# ---------------------------------------------------------------------------

def group_stats(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    n = len(rows)
    n_pos = sum(1 for r in rows if r["predicted"])
    stats: Dict[str, Any] = {
        "n": n,
        "n_positive_predictions": n_pos,
        "selection_rate": round(n_pos / n, 4) if n else None,
    }

    labeled = [r for r in rows if r["actual"] is not None]
    if labeled:
        tp = sum(1 for r in labeled if r["actual"] and r["predicted"])
        fp = sum(1 for r in labeled if not r["actual"] and r["predicted"])
        fn = sum(1 for r in labeled if r["actual"] and not r["predicted"])
        tn = sum(1 for r in labeled if not r["actual"] and not r["predicted"])
        stats["n_labeled"] = len(labeled)
        stats["tpr"] = round(tp / (tp + fn), 4) if (tp + fn) else None
        stats["fpr"] = round(fp / (fp + tn), 4) if (fp + tn) else None
        stats["precision"] = round(tp / (tp + fp), 4) if (tp + fp) else None
        stats["accuracy"] = round((tp + tn) / len(labeled), 4) if labeled else None
    else:
        stats["n_labeled"] = 0
        stats["tpr"] = None
        stats["fpr"] = None
        stats["precision"] = None
        stats["accuracy"] = None

    return stats


def analyze(
    rows: List[Dict[str, Any]],
    reference_group: Optional[str],
    di_threshold: float,
    tpr_gap_threshold: float,
) -> Dict[str, Any]:
    grouped: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for r in rows:
        grouped[r["group"]].append(r)

    by_group = {g: group_stats(g_rows) for g, g_rows in grouped.items()}

    # Default reference group: the largest by n (usually the majority/best-
    # represented group). Callers should override with --reference-group
    # when the analytically "correct" comparison group isn't the biggest one.
    requested_group_missing = bool(reference_group) and reference_group not in by_group
    if reference_group and reference_group in by_group:
        ref = reference_group
        ref_explicit = True
    else:
        ref = max(by_group, key=lambda g: by_group[g]["n"])
        ref_explicit = False

    ref_rate = by_group[ref]["selection_rate"]
    ref_tpr = by_group[ref]["tpr"]
    ref_fpr = by_group[ref]["fpr"]

    has_ground_truth = any(s["n_labeled"] > 0 for s in by_group.values())

    for g, s in by_group.items():
        s["is_reference"] = (g == ref)
        s["disparate_impact_ratio"] = (
            round(s["selection_rate"] / ref_rate, 4)
            if ref_rate not in (None, 0) and s["selection_rate"] is not None
            else None
        )
        s["adverse_impact_flag"] = (
            s["disparate_impact_ratio"] is not None
            and not s["is_reference"]
            and s["disparate_impact_ratio"] < di_threshold
        )

        if s["tpr"] is not None and ref_tpr is not None:
            s["equal_opportunity_gap"] = round(s["tpr"] - ref_tpr, 4)
        else:
            s["equal_opportunity_gap"] = None

        if s["fpr"] is not None and ref_fpr is not None:
            fpr_gap = s["fpr"] - ref_fpr
        else:
            fpr_gap = None

        if s["equal_opportunity_gap"] is not None or fpr_gap is not None:
            candidates = [abs(x) for x in (s["equal_opportunity_gap"], fpr_gap) if x is not None]
            s["equalized_odds_gap"] = round(max(candidates), 4) if candidates else None
        else:
            s["equalized_odds_gap"] = None

        s["tpr_gap_flag"] = (
            s["equal_opportunity_gap"] is not None
            and not s["is_reference"]
            and abs(s["equal_opportunity_gap"]) > tpr_gap_threshold
        )

    flagged_di = sorted(g for g, s in by_group.items() if s["adverse_impact_flag"])
    flagged_tpr = sorted(g for g, s in by_group.items() if s["tpr_gap_flag"])

    if not flagged_di and not flagged_tpr:
        verdict = "🟢 No disparities flagged at current thresholds"
    elif flagged_di and flagged_tpr:
        verdict = "🔴 Both selection-rate and outcome-quality disparities flagged — review before launch"
    elif flagged_di:
        verdict = "🟠 Selection-rate disparity flagged (four-fifths rule)"
    else:
        verdict = "🟠 Outcome-quality (TPR) gap flagged between groups"

    return {
        "n": len(rows),
        "n_groups": len(by_group),
        "reference_group": ref,
        "reference_group_explicit": ref_explicit,
        "requested_reference_group_found": not requested_group_missing,
        "has_ground_truth": has_ground_truth,
        "di_threshold": di_threshold,
        "tpr_gap_threshold": tpr_gap_threshold,
        "by_group": dict(sorted(by_group.items(), key=lambda kv: kv[1]["n"], reverse=True)),
        "flagged_disparate_impact": flagged_di,
        "flagged_tpr_gap": flagged_tpr,
        "verdict": verdict,
    }


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def _bar(value: Optional[float], width: int = 20) -> str:
    if value is None:
        return " " * width
    value = max(0.0, min(1.0, value))
    filled = int(value * width)
    return "█" * filled + "░" * (width - filled)


def _pct(value: Optional[float]) -> str:
    return "N/A" if value is None else f"{value:.1%}"


def print_report(r: Dict[str, Any]) -> None:
    print("\n" + "=" * 78)
    print("⚖️  BIAS / FAIRNESS SCORECARD")
    print("=" * 78)

    print(f"\n📋 OVERVIEW:")
    print(f"   • Records:           {r['n']}")
    print(f"   • Groups:            {r['n_groups']}")
    ref_source = "requested" if r["reference_group_explicit"] else "largest group by count"
    print(f"   • Reference group:   {r['reference_group']} ({ref_source}; other groups compare against this)")
    if not r["requested_reference_group_found"]:
        print(f"   ⚠️  Requested --reference-group not found in data — fell back to largest group.")
    if not r["has_ground_truth"]:
        print(f"   ℹ️  No ground-truth/actual column found — only selection-rate disparity is measured. "
              f"Add an 'actual' column to unlock TPR/FPR gap metrics.")

    print(f"\n📊 SELECTION RATE BY GROUP (four-fifths rule, threshold {r['di_threshold']:.0%}):")
    print(f"   {'Group':<20} {'N':>6} {'Sel. rate':>10} {'DI ratio':>9}  {'Flag'}")
    print(f"   {'─'*20} {'─'*6} {'─'*10} {'─'*9}  {'─'*20}")
    for g, s in r["by_group"].items():
        ref_note = " (ref)" if s["is_reference"] else ""
        di = f"{s['disparate_impact_ratio']:.2f}" if s["disparate_impact_ratio"] is not None else "—"
        flag = "🔴 adverse impact" if s["adverse_impact_flag"] else ("—" if not s["is_reference"] else "")
        print(f"   {g[:20]+ref_note:<20} {s['n']:>6} {_pct(s['selection_rate']):>10} {di:>9}  {flag}")

    if r["has_ground_truth"]:
        print(f"\n🎯 OUTCOME QUALITY BY GROUP (equal opportunity, threshold ±{r['tpr_gap_threshold']:.0%}):")
        print(f"   {'Group':<20} {'TPR':>7} {'FPR':>7} {'TPR gap':>9} {'Eq.odds gap':>12}  {'Flag'}")
        print(f"   {'─'*20} {'─'*7} {'─'*7} {'─'*9} {'─'*12}  {'─'*20}")
        for g, s in r["by_group"].items():
            if s["n_labeled"] == 0:
                continue
            ref_note = " (ref)" if s["is_reference"] else ""
            gap = f"{s['equal_opportunity_gap']:+.1%}" if s["equal_opportunity_gap"] is not None else "—"
            eo_gap = f"{s['equalized_odds_gap']:.1%}" if s["equalized_odds_gap"] is not None else "—"
            flag = "🔴 TPR gap" if s["tpr_gap_flag"] else ("—" if not s["is_reference"] else "")
            print(f"   {g[:20]+ref_note:<20} {_pct(s['tpr']):>7} {_pct(s['fpr']):>7} {gap:>9} {eo_gap:>12}  {flag}")

    print(f"\n🏁 VERDICT: {r['verdict']}")

    if r["flagged_disparate_impact"]:
        print(f"\n   Selection-rate disparity (below {r['di_threshold']:.0%} of reference group's rate):")
        for g in r["flagged_disparate_impact"]:
            s = r["by_group"][g]
            print(f"      • {g}: {_pct(s['selection_rate'])} vs {r['reference_group']}'s "
                  f"{_pct(r['by_group'][r['reference_group']]['selection_rate'])} (ratio {s['disparate_impact_ratio']:.2f})")

    if r["flagged_tpr_gap"]:
        print(f"\n   True-positive-rate gap (worse outcomes for real positives in this group):")
        for g in r["flagged_tpr_gap"]:
            s = r["by_group"][g]
            print(f"      • {g}: TPR {_pct(s['tpr'])} vs {r['reference_group']}'s "
                  f"{_pct(r['by_group'][r['reference_group']]['tpr'])} (gap {s['equal_opportunity_gap']:+.1%})")

    print(f"\n💡 CAVEATS (read before using this to sign off a launch):")
    print(f"   • This is a statistical first pass, not a legal or ethical determination —")
    print(f"     loop in legal/compliance before treating any flag as a go/no-go signal.")
    print(f"   • Fairness metrics can conflict with each other (demographic parity and equal")
    print(f"     opportunity are provably incompatible except in special cases) — picking which")
    print(f"     metric matters most is a policy decision, not a statistical one.")
    print(f"   • Small group sizes produce noisy rates — treat flags on groups under ~30 records")
    print(f"     as a prompt to collect more data, not a confirmed finding.")
    print(f"   • The reference group is just a comparison baseline, not a definition of \"correct\" —")
    print(f"     re-run with --reference-group to check against a different baseline.")

    print("\n" + "=" * 78)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Compute group-fairness metrics (selection-rate disparity / four-fifths rule, "
                    "and TPR/FPR gaps if ground truth is present) from labeled prediction data.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --csv predictions.csv
  %(prog)s --csv predictions.csv --reference-group male
  %(prog)s --csv predictions.csv --di-threshold 0.8 --tpr-gap-threshold 0.1
  %(prog)s --csv predictions.csv --output scorecard.json
        """,
    )
    parser.add_argument("--csv", "-c", required=True, help="CSV with group, predicted, and optional actual columns")
    parser.add_argument("--reference-group", type=str, default=None,
                         help="Group to compare others against (default: largest group by count)")
    parser.add_argument("--di-threshold", type=float, default=DEFAULT_DI_THRESHOLD,
                         help=f"Four-fifths rule threshold for disparate impact ratio (default: {DEFAULT_DI_THRESHOLD})")
    parser.add_argument("--tpr-gap-threshold", type=float, default=DEFAULT_TPR_GAP_THRESHOLD,
                         help=f"Flag TPR gaps larger than this (default: {DEFAULT_TPR_GAP_THRESHOLD})")
    parser.add_argument("--output", "-o", type=str, help="Write report to JSON file")
    args = parser.parse_args()

    try:
        rows = load_csv(args.csv)
    except Exception as e:
        print(f"Error loading CSV: {e}", file=sys.stderr)
        return 1

    if not rows:
        print("Error: no valid rows found in CSV.", file=sys.stderr)
        return 1

    n_groups = len({r["group"] for r in rows})
    if n_groups < 2:
        print("Error: need at least 2 distinct groups to compute disparity metrics.", file=sys.stderr)
        return 1

    result = analyze(rows, args.reference_group, args.di_threshold, args.tpr_gap_threshold)
    print_report(result)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(toolkit_io.envelope(result, TOOL), f, indent=2)
        print(f"\n📁 Scorecard saved to {args.output}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
