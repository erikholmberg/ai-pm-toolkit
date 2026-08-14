#!/usr/bin/env python3
"""
Guardrail Effectiveness Analyzer

Evaluate an AI safety/content guardrail's precision and recall from a
labeled dataset of actual violations vs. what the guardrail flagged. Helps
a PM decide whether a guardrail is too loose (missing real violations —
usually the worse failure mode) or too tight (blocking legitimate content —
a UX-friction risk), overall and broken down by violation category.

Usage:
    python guardrail-effectiveness-analyzer.py --csv guardrail_labels.csv
    python guardrail-effectiveness-analyzer.py --csv guardrail_labels.csv --max-fn-rate 0.05
    python guardrail-effectiveness-analyzer.py --csv guardrail_labels.csv --output report.json

CSV format (header row required):
    case_id,actual_violation,guardrail_flagged,category
    c001,yes,yes,pii
    c002,no,no,off_topic
    c003,yes,no,jailbreak
    c004,no,yes,toxicity

    Required columns (fuzzy-matched): case_id (or id), actual_violation (or
    actual, ground_truth, is_violation), guardrail_flagged (or flagged,
    predicted, guardrail_result). Optional: category (or type, class).
    Values: yes/y/true/1/violation = positive; anything else = negative.

Requirements:
    None (stdlib only).
"""

import argparse
import csv
import json
import sys
from collections import defaultdict
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Thresholds (documented constants, overridable via CLI)
# ---------------------------------------------------------------------------

DEFAULT_MAX_FN_RATE = 0.10   # missed violations above this rate need tuning
DEFAULT_MAX_FP_RATE = 0.20   # over-blocking above this rate is a UX-friction risk

POSITIVE_VALUES = {"yes", "y", "true", "1", "violation", "flagged", "positive"}


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
        c_id = _col(fields, "case_id", "id", "case")
        c_actual = _col(fields, "actual_violation", "actual", "ground_truth", "is_violation", "true_label")
        c_flagged = _col(fields, "guardrail_flagged", "flagged", "predicted", "guardrail_result", "prediction")
        c_category = _col(fields, "category", "type", "class", "violation_type")

        if not c_actual or not c_flagged:
            raise ValueError(
                "CSV must have an actual_violation column and a guardrail_flagged column."
            )

        for i, row in enumerate(reader):
            actual_raw = row.get(c_actual, "")
            flagged_raw = row.get(c_flagged, "")
            if actual_raw is None or flagged_raw is None or (str(actual_raw).strip() == "" and str(flagged_raw).strip() == ""):
                continue
            rows.append({
                "case_id": (row.get(c_id, "") or "").strip() or f"case_{i + 1}",
                "actual": is_positive(actual_raw),
                "flagged": is_positive(flagged_raw),
                "category": (row.get(c_category, "") or "").strip() or "uncategorized",
            })
    return rows


# ---------------------------------------------------------------------------
# Core calculations
# ---------------------------------------------------------------------------

def confusion_matrix(rows: List[Dict[str, Any]]) -> Dict[str, int]:
    tp = sum(1 for r in rows if r["actual"] and r["flagged"])
    fp = sum(1 for r in rows if not r["actual"] and r["flagged"])
    fn = sum(1 for r in rows if r["actual"] and not r["flagged"])
    tn = sum(1 for r in rows if not r["actual"] and not r["flagged"])
    return {"tp": tp, "fp": fp, "fn": fn, "tn": tn}


def metrics_from_confusion(cm: Dict[str, int]) -> Dict[str, Optional[float]]:
    """
    Ratio metrics are None (not 0.0) when their denominator is zero — e.g. recall
    is undefined, not "bad," when a sample has no real violations to catch. This
    avoids reporting a false "0% recall" alarm on a clean-only sample.
    """
    tp, fp, fn, tn = cm["tp"], cm["fp"], cm["fn"], cm["tn"]
    precision = tp / (tp + fp) if (tp + fp) else None
    recall = tp / (tp + fn) if (tp + fn) else None
    f1 = (
        2 * precision * recall / (precision + recall)
        if (precision is not None and recall is not None and (precision + recall))
        else None
    )
    fpr = fp / (fp + tn) if (fp + tn) else None
    fnr = fn / (fn + tp) if (fn + tp) else None
    accuracy = (tp + tn) / (tp + fp + fn + tn) if (tp + fp + fn + tn) else None
    return {
        "precision": round(precision, 4) if precision is not None else None,
        "recall": round(recall, 4) if recall is not None else None,
        "f1": round(f1, 4) if f1 is not None else None,
        "false_positive_rate": round(fpr, 4) if fpr is not None else None,
        "false_negative_rate": round(fnr, 4) if fnr is not None else None,
        "accuracy": round(accuracy, 4) if accuracy is not None else None,
    }


def analyze(rows: List[Dict[str, Any]], max_fn_rate: float, max_fp_rate: float) -> Dict[str, Any]:
    overall_cm = confusion_matrix(rows)
    overall_metrics = metrics_from_confusion(overall_cm)

    by_category: Dict[str, Dict[str, Any]] = {}
    grouped: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for r in rows:
        grouped[r["category"]].append(r)

    for cat, cat_rows in sorted(grouped.items()):
        cm = confusion_matrix(cat_rows)
        metrics = metrics_from_confusion(cm)
        fnr, fpr = metrics["false_negative_rate"], metrics["false_positive_rate"]
        needs_tuning = fnr is not None and fnr > max_fn_rate
        ux_friction_risk = fpr is not None and fpr > max_fp_rate
        by_category[cat] = {
            "n": len(cat_rows),
            "confusion_matrix": cm,
            **metrics,
            "needs_tuning_missed_violations": needs_tuning,
            "ux_friction_risk_over_blocking": ux_friction_risk,
        }

    return {
        "n": len(rows),
        "overall": {"confusion_matrix": overall_cm, **overall_metrics},
        "by_category": by_category,
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


def print_report(result: Dict[str, Any], max_fn_rate: float, max_fp_rate: float) -> None:
    print("\n" + "=" * 78)
    print("📊 GUARDRAIL EFFECTIVENESS ANALYZER")
    print("=" * 78)

    n = result["n"]
    ov = result["overall"]
    cm = ov["confusion_matrix"]

    print(f"\n📋 OVERVIEW:")
    print(f"   • Labeled cases:     {n}")
    print(f"   • Precision:         {_pct(ov['precision']):>6}  {_bar(ov['precision'])}")
    print(f"   • Recall:            {_pct(ov['recall']):>6}  {_bar(ov['recall'])}")
    print(f"   • F1:                {_pct(ov['f1'])}")
    print(f"   • Accuracy:          {_pct(ov['accuracy'])}")
    print(f"   • False positive rate: {_pct(ov['false_positive_rate'])}")
    print(f"   • False negative rate: {_pct(ov['false_negative_rate'])}")
    if cm["tp"] + cm["fn"] == 0:
        print(f"   ℹ️  No real violations in this sample — precision/recall/F1 are N/A, not 0%.")
    if cm["fp"] + cm["tn"] == 0:
        print(f"   ℹ️  No clean cases in this sample — false-positive rate is N/A, not 0%.")

    print(f"\n🔢 CONFUSION MATRIX (rows=actual, cols=guardrail):")
    print(f"   {'':16} {'flagged':>10} {'not flagged':>13}")
    print(f"   {'violation':16} {cm['tp']:>10} {cm['fn']:>13}")
    print(f"   {'no violation':16} {cm['fp']:>10} {cm['tn']:>13}")

    if result["by_category"] and len(result["by_category"]) > 1:
        print(f"\n📈 BY CATEGORY:")
        print(f"   {'Category':<18} {'N':>5} {'Prec':>7} {'Recall':>7} {'FPR':>7} {'FNR':>7}  {'Flags'}")
        print(f"   {'─'*18} {'─'*5} {'─'*7} {'─'*7} {'─'*7} {'─'*7}  {'─'*20}")
        for cat, s in result["by_category"].items():
            flags = []
            if s["needs_tuning_missed_violations"]:
                flags.append("🔴 misses violations")
            if s["ux_friction_risk_over_blocking"]:
                flags.append("🟡 over-blocks")
            flag_str = ", ".join(flags) if flags else "🟢 OK"
            print(
                f"   {cat:<18} {s['n']:>5} {_pct(s['precision']):>6} {_pct(s['recall']):>6} "
                f"{_pct(s['false_positive_rate']):>6} {_pct(s['false_negative_rate']):>6}  {flag_str}"
            )

    tuning_needed = [c for c, s in result["by_category"].items() if s["needs_tuning_missed_violations"]]
    friction_risk = [c for c, s in result["by_category"].items() if s["ux_friction_risk_over_blocking"]]

    print(f"\n⚠️  ATTENTION NEEDED:")
    if tuning_needed:
        print(f"   🔴 Categories missing too many real violations (FN rate > {max_fn_rate:.0%}):")
        for c in tuning_needed:
            fnr = result["by_category"][c]["false_negative_rate"]
            print(f"      • {c} — FN rate {fnr:.1%} — tighten detection for this category")
    else:
        print(f"   🟢 No category exceeds the {max_fn_rate:.0%} false-negative threshold.")

    if friction_risk:
        print(f"\n   🟡 Categories over-blocking legit content (FP rate > {max_fp_rate:.0%}):")
        for c in friction_risk:
            fpr = result["by_category"][c]["false_positive_rate"]
            print(f"      • {c} — FP rate {fpr:.1%} — likely UX friction, consider loosening")
    else:
        print(f"\n   🟢 No category exceeds the {max_fp_rate:.0%} false-positive threshold.")

    print(f"\n💡 PLAIN-LANGUAGE SUMMARY (for non-technical stakeholders):")
    if ov["recall"] is None:
        print(f"   This sample has no labeled real violations, so recall can't be measured — "
              f"it tells you about false positives only, not whether real threats get through.")
    else:
        print(f"   Out of {n} labeled cases, the guardrail correctly caught "
              f"{cm['tp']} of {cm['tp'] + cm['fn']} real violations ({ov['recall']:.0%} recall).")
    if ov["false_positive_rate"] is None:
        print(f"   This sample has no labeled clean cases, so the false-positive rate can't be measured.")
    else:
        print(f"   It incorrectly flagged {cm['fp']} of {cm['fp'] + cm['tn']} clean cases as violations "
              f"({ov['false_positive_rate']:.0%} false-positive rate).")
    if ov["recall"] is not None and ov["recall"] < 0.8:
        print(f"   ⚠️  Recall is below 80% — meaningful risk content is getting through undetected.")
    if ov["false_positive_rate"] is not None and ov["false_positive_rate"] > max_fp_rate:
        print(f"   ⚠️  False-positive rate is above the {max_fp_rate:.0%} comfort threshold — users may see "
              f"legitimate requests blocked, which erodes trust in the product.")
    print(f"   Rule of thumb used here: missed violations (false negatives) are treated as worse than "
          f"over-blocking (false positives), since safety misses carry more downside than user friction.")

    print("\n" + "=" * 78)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Evaluate a guardrail's precision/recall from labeled actual-vs-flagged data, "
                    "overall and by category, and flag categories needing tuning.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --csv guardrail_labels.csv
  %(prog)s --csv guardrail_labels.csv --max-fn-rate 0.05
  %(prog)s --csv guardrail_labels.csv --output report.json
        """,
    )
    parser.add_argument("--csv", "-c", required=True, help="CSV with case_id, actual_violation, guardrail_flagged, category")
    parser.add_argument(
        "--max-fn-rate", type=float, default=DEFAULT_MAX_FN_RATE,
        help=f"Flag categories above this false-negative rate as needing tuning (default: {DEFAULT_MAX_FN_RATE})",
    )
    parser.add_argument(
        "--max-fp-rate", type=float, default=DEFAULT_MAX_FP_RATE,
        help=f"Flag categories above this false-positive rate as a UX-friction risk (default: {DEFAULT_MAX_FP_RATE})",
    )
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

    result = analyze(rows, args.max_fn_rate, args.max_fp_rate)
    print_report(result, args.max_fn_rate, args.max_fp_rate)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2)
        print(f"\n📁 Report saved to {args.output}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
