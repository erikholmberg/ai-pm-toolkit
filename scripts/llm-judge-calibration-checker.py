#!/usr/bin/env python3
"""
LLM-Judge Calibration Checker

Measure how well an LLM-as-judge's scores agree with human labels, so a PM
can decide whether the judge is trustworthy enough to use as a proxy for
human review (e.g. for regression gating in CI, or for scaling up eval
coverage without scaling up human raters).

Auto-detects whether the label scale is binary/categorical (0/1, true/false,
pass/fail, yes/no) or continuous/ordinal (e.g. 1-5, 0-1 float), and applies
the appropriate agreement statistic: Cohen's kappa for binary/categorical,
Pearson correlation + mean absolute error for continuous. Also reports
systematic bias (is the judge on average harsher or more lenient than
humans) and a plain-language calibration verdict.

Usage:
    python llm-judge-calibration-checker.py --csv judge_vs_human.csv
    python llm-judge-calibration-checker.py --csv judge_vs_human.csv --output report.json
    python llm-judge-calibration-checker.py --csv judge_vs_human.csv --scale binary

CSV format (header row required):
    case_id,human_score,judge_score
    c001,1,1
    c002,0,1
    c003,4,3
    c004,pass,pass

    Required columns (fuzzy-matched): case_id (or id), human_score (or human,
    human_label, ground_truth), judge_score (or judge, llm_score, ai_score).

Requirements:
    None (stdlib only).
"""

import argparse
import csv
import json
import sys
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Calibration verdict thresholds (documented constants)
# ---------------------------------------------------------------------------

KAPPA_WELL_CALIBRATED = 0.60      # "substantial agreement" (Landis & Koch)
KAPPA_MODERATE = 0.40

PEARSON_WELL_CALIBRATED = 0.75
PEARSON_MODERATE = 0.50

# Bias is considered "material" if it exceeds this fraction of the observed
# score range (e.g. on a 0-1 scale, 0.15 = judge is off by 15 points on avg).
MATERIAL_BIAS_FRACTION = 0.15

BINARY_TRUE = {"1", "true", "yes", "y", "pass", "passed", "flagged", "violation", "positive"}
BINARY_FALSE = {"0", "false", "no", "n", "fail", "failed", "not_flagged", "no_violation", "negative"}


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def _col(fieldnames: List[str], *aliases: str) -> Optional[str]:
    lower_map = {f.lower().strip(): f for f in fieldnames}
    for alias in aliases:
        if alias.lower().strip() in lower_map:
            return lower_map[alias.lower().strip()]
    return None


def load_csv(path: str) -> List[Dict[str, str]]:
    """Load case_id/human_score/judge_score rows from CSV."""
    rows: List[Dict[str, str]] = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fields = reader.fieldnames or []
        c_id = _col(fields, "case_id", "id", "case", "name")
        c_human = _col(fields, "human_score", "human", "human_label", "ground_truth", "reference_score", "label")
        c_judge = _col(fields, "judge_score", "judge", "llm_score", "ai_score", "model_score", "predicted_score")

        if not c_human or not c_judge:
            raise ValueError(
                "CSV must have a human score column (human_score/human/human_label/ground_truth) "
                "and a judge score column (judge_score/judge/llm_score/ai_score)."
            )

        for i, row in enumerate(reader):
            human_raw = (row.get(c_human, "") or "").strip()
            judge_raw = (row.get(c_judge, "") or "").strip()
            if not human_raw or not judge_raw:
                continue
            rows.append({
                "case_id": (row.get(c_id, "") or "").strip() or f"case_{i + 1}",
                "human_raw": human_raw,
                "judge_raw": judge_raw,
            })
    return rows


# ---------------------------------------------------------------------------
# Scale detection & normalization
# ---------------------------------------------------------------------------

def detect_scale(rows: List[Dict[str, str]]) -> str:
    """Return 'binary' if every value maps to a binary label, else 'continuous'."""
    for r in rows:
        for raw in (r["human_raw"], r["judge_raw"]):
            v = raw.strip().lower()
            if v not in BINARY_TRUE and v not in BINARY_FALSE:
                return "continuous"
    return "binary" if rows else "continuous"


def to_binary(raw: str) -> Optional[int]:
    v = raw.strip().lower()
    if v in BINARY_TRUE:
        return 1
    if v in BINARY_FALSE:
        return 0
    return None


def to_float(raw: str) -> Optional[float]:
    try:
        return float(raw)
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# Agreement statistics
# ---------------------------------------------------------------------------

def cohens_kappa(pairs: List[Tuple[int, int]]) -> float:
    """Cohen's kappa for two binary raters."""
    n = len(pairs)
    if n == 0:
        return 0.0
    po = sum(1 for h, j in pairs if h == j) / n

    human_pos = sum(1 for h, _ in pairs if h == 1) / n
    judge_pos = sum(1 for _, j in pairs if j == 1) / n
    pe = human_pos * judge_pos + (1 - human_pos) * (1 - judge_pos)

    if pe >= 1.0:
        return 1.0
    return (po - pe) / (1 - pe)


def pearson_r(xs: List[float], ys: List[float]) -> Optional[float]:
    """None (not 0.0) when undefined — e.g. every human score in the sample is
    identical, so there's no variance to correlate against."""
    n = len(xs)
    if n < 2:
        return None
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n
    cov = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    var_x = sum((x - mean_x) ** 2 for x in xs)
    var_y = sum((y - mean_y) ** 2 for y in ys)
    denom = (var_x * var_y) ** 0.5
    if denom == 0:
        return None
    return cov / denom


def analyze_binary(rows: List[Dict[str, str]]) -> Dict[str, Any]:
    pairs: List[Tuple[int, int]] = []
    skipped = 0
    for r in rows:
        h = to_binary(r["human_raw"])
        j = to_binary(r["judge_raw"])
        if h is None or j is None:
            skipped += 1
            continue
        pairs.append((h, j))

    n = len(pairs)
    exact_agree = sum(1 for h, j in pairs if h == j)
    agreement_rate = exact_agree / n if n else 0.0
    kappa = cohens_kappa(pairs)

    tp = sum(1 for h, j in pairs if h == 1 and j == 1)
    fp = sum(1 for h, j in pairs if h == 0 and j == 1)
    fn = sum(1 for h, j in pairs if h == 1 and j == 0)
    tn = sum(1 for h, j in pairs if h == 0 and j == 0)

    human_mean = sum(h for h, _ in pairs) / n if n else 0.0
    judge_mean = sum(j for _, j in pairs) / n if n else 0.0
    bias = judge_mean - human_mean

    return {
        "n": n,
        "skipped": skipped,
        "exact_agreement_rate": round(agreement_rate, 4),
        "cohens_kappa": round(kappa, 4),
        "confusion_matrix": {"tp": tp, "fp": fp, "fn": fn, "tn": tn},
        "human_mean": round(human_mean, 4),
        "judge_mean": round(judge_mean, 4),
        "bias": round(bias, 4),
        "bias_direction": _bias_direction(bias, 1.0),
    }


def analyze_continuous(rows: List[Dict[str, str]]) -> Dict[str, Any]:
    xs: List[float] = []
    ys: List[float] = []
    skipped = 0
    for r in rows:
        h = to_float(r["human_raw"])
        j = to_float(r["judge_raw"])
        if h is None or j is None:
            skipped += 1
            continue
        xs.append(h)
        ys.append(j)

    n = len(xs)
    exact_agree = sum(1 for h, j in zip(xs, ys) if h == j)
    agreement_rate = exact_agree / n if n else 0.0

    r_val = pearson_r(xs, ys)
    mae = sum(abs(h - j) for h, j in zip(xs, ys)) / n if n else 0.0

    human_mean = sum(xs) / n if n else 0.0
    judge_mean = sum(ys) / n if n else 0.0
    bias = judge_mean - human_mean

    value_range = (max(xs + ys) - min(xs + ys)) if xs and ys else 1.0
    value_range = value_range or 1.0

    return {
        "n": n,
        "skipped": skipped,
        "exact_agreement_rate": round(agreement_rate, 4),
        "pearson_r": round(r_val, 4) if r_val is not None else None,
        "mean_absolute_error": round(mae, 4),
        "human_mean": round(human_mean, 4),
        "judge_mean": round(judge_mean, 4),
        "bias": round(bias, 4),
        "bias_direction": _bias_direction(bias, value_range),
        "value_range": round(value_range, 4),
    }


def _bias_direction(bias: float, value_range: float) -> str:
    if value_range <= 0:
        value_range = 1.0
    frac = abs(bias) / value_range
    if frac < MATERIAL_BIAS_FRACTION * 0.3:
        return "negligible"
    return "judge scores HIGHER than humans" if bias > 0 else "judge scores LOWER than humans"


def calibration_verdict(scale: str, stats: Dict[str, Any]) -> Tuple[str, str]:
    """Return (icon+label, explanation)."""
    material_bias = False
    if scale == "binary":
        agree_metric = stats["cohens_kappa"]
        well, moderate = KAPPA_WELL_CALIBRATED, KAPPA_MODERATE
        metric_name = "Cohen's kappa"
        material_bias = abs(stats["bias"]) >= MATERIAL_BIAS_FRACTION
    else:
        agree_metric = stats["pearson_r"]
        well, moderate = PEARSON_WELL_CALIBRATED, PEARSON_MODERATE
        metric_name = "Pearson r"
        rng = stats.get("value_range", 1.0) or 1.0
        material_bias = (abs(stats["bias"]) / rng) >= MATERIAL_BIAS_FRACTION

    if agree_metric is None:
        return (
            "🟡 Correlation undefined — sample has no score variance",
            f"{metric_name} needs variation in both raters' scores to compute; this sample's scores were "
            f"constant. Check mean absolute error and bias instead, or add cases with a wider score spread.",
        )

    if agree_metric >= well and not material_bias:
        return (
            "🟢 Well-calibrated — safe to use judge for regression gating",
            f"{metric_name} = {agree_metric:.2f} (≥ {well}) with no material systematic bias.",
        )
    elif agree_metric >= moderate:
        return (
            "🟡 Moderate agreement — spot-check disagreements before trusting fully",
            f"{metric_name} = {agree_metric:.2f} (between {moderate} and {well})"
            + (" and bias is material." if material_bias else "."),
        )
    else:
        return (
            "🔴 Poor agreement — do not gate releases on this judge alone",
            f"{metric_name} = {agree_metric:.2f} (< {moderate}). Judge and human raters diverge too often "
            "to trust unsupervised.",
        )


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def _bar(value: float, width: int = 20) -> str:
    value = max(0.0, min(1.0, value))
    filled = int(value * width)
    return "█" * filled + "░" * (width - filled)


def worst_disagreements(rows: List[Dict[str, str]], scale: str, top_n: int = 5) -> List[Dict[str, Any]]:
    scored: List[Dict[str, Any]] = []
    for r in rows:
        if scale == "binary":
            h, j = to_binary(r["human_raw"]), to_binary(r["judge_raw"])
            if h is None or j is None:
                continue
            diff = abs(h - j)
        else:
            h, j = to_float(r["human_raw"]), to_float(r["judge_raw"])
            if h is None or j is None:
                continue
            diff = abs(h - j)
        if diff > 0:
            scored.append({"case_id": r["case_id"], "human": h, "judge": j, "diff": diff})
    scored.sort(key=lambda x: -x["diff"])
    return scored[:top_n]


def print_report(scale: str, stats: Dict[str, Any], rows: List[Dict[str, str]]) -> None:
    print("\n" + "=" * 78)
    print("📊 LLM-JUDGE CALIBRATION CHECKER")
    print("=" * 78)

    print(f"\n📋 OVERVIEW:")
    print(f"   • Cases compared:    {stats['n']}")
    if stats.get("skipped"):
        print(f"   • Skipped (unparseable): {stats['skipped']}")
    print(f"   • Detected scale:    {scale.upper()}")
    print(f"   • Exact agreement:   {stats['exact_agreement_rate']:.1%}  {_bar(stats['exact_agreement_rate'])}")

    print(f"\n📈 AGREEMENT STATISTICS:")
    if scale == "binary":
        print(f"   • Cohen's kappa:     {stats['cohens_kappa']:.3f}  {_bar((stats['cohens_kappa'] + 1) / 2)}")
        cm = stats["confusion_matrix"]
        print(f"\n   Confusion matrix (rows=human, cols=judge):")
        print(f"   {'':14} {'judge=1':>10} {'judge=0':>10}")
        print(f"   {'human=1':14} {cm['tp']:>10} {cm['fn']:>10}")
        print(f"   {'human=0':14} {cm['fp']:>10} {cm['tn']:>10}")
    else:
        r_val = stats["pearson_r"]
        if r_val is None:
            print(f"   • Pearson r:         N/A (no score variance in this sample)")
        else:
            print(f"   • Pearson r:         {r_val:.3f}  {_bar((r_val + 1) / 2)}")
        print(f"   • Mean abs. error:   {stats['mean_absolute_error']:.3f}")
        print(f"   • Value range seen:  {stats['value_range']:.2f}")

    print(f"\n⚖️  SYSTEMATIC BIAS:")
    print(f"   • Human mean score:  {stats['human_mean']:.3f}")
    print(f"   • Judge mean score:  {stats['judge_mean']:.3f}")
    sign = "+" if stats["bias"] >= 0 else ""
    print(f"   • Bias (judge-human):{sign}{stats['bias']:.3f}")
    print(f"   • Direction:         {stats['bias_direction']}")

    worst = worst_disagreements(rows, scale)
    if worst:
        print(f"\n⚠️  LARGEST DISAGREEMENTS:")
        print(f"   {'Case':<16} {'Human':>8} {'Judge':>8} {'Diff':>8}")
        print(f"   {'─'*16} {'─'*8} {'─'*8} {'─'*8}")
        for w in worst:
            print(f"   {w['case_id']:<16} {w['human']:>8} {w['judge']:>8} {w['diff']:>8}")

    label, explanation = calibration_verdict(scale, stats)
    print(f"\n💡 VERDICT: {label}")
    print(f"   {explanation}")

    print(f"\n📎 THRESHOLDS USED:")
    if scale == "binary":
        print(f"   • Well-calibrated:   kappa ≥ {KAPPA_WELL_CALIBRATED}")
        print(f"   • Moderate:          {KAPPA_MODERATE} ≤ kappa < {KAPPA_WELL_CALIBRATED}")
        print(f"   • Poor:              kappa < {KAPPA_MODERATE}")
    else:
        print(f"   • Well-calibrated:   Pearson r ≥ {PEARSON_WELL_CALIBRATED}")
        print(f"   • Moderate:          {PEARSON_MODERATE} ≤ r < {PEARSON_WELL_CALIBRATED}")
        print(f"   • Poor:              r < {PEARSON_MODERATE}")
    print(f"   • Material bias:     |bias| ≥ {MATERIAL_BIAS_FRACTION:.0%} of observed score range")

    print("\n" + "=" * 78)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Measure agreement between an LLM-as-judge and human labels to decide "
                    "whether the judge can be trusted as a human proxy.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --csv judge_vs_human.csv
  %(prog)s --csv judge_vs_human.csv --output report.json
  %(prog)s --csv judge_vs_human.csv --scale binary
        """,
    )
    parser.add_argument("--csv", "-c", required=True, help="CSV with case_id, human_score, judge_score columns")
    parser.add_argument(
        "--scale", choices=["auto", "binary", "continuous"], default="auto",
        help="Force scale detection instead of auto-detecting (default: auto)",
    )
    parser.add_argument("--output", "-o", type=str, help="Write report to JSON file")
    args = parser.parse_args()

    try:
        rows = load_csv(args.csv)
    except Exception as e:
        print(f"Error loading CSV: {e}", file=sys.stderr)
        return 1

    if not rows:
        print("Error: no valid case_id/human_score/judge_score rows found in CSV.", file=sys.stderr)
        return 1

    scale = args.scale if args.scale != "auto" else detect_scale(rows)
    stats = analyze_binary(rows) if scale == "binary" else analyze_continuous(rows)

    if stats["n"] == 0:
        print("Error: no rows could be parsed under the detected/selected scale.", file=sys.stderr)
        return 1

    print_report(scale, stats, rows)

    if args.output:
        label, explanation = calibration_verdict(scale, stats)
        report = {
            "scale": scale,
            "stats": stats,
            "verdict": label,
            "verdict_explanation": explanation,
            "worst_disagreements": worst_disagreements(rows, scale, top_n=10),
        }
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)
        print(f"\n📁 Report saved to {args.output}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
