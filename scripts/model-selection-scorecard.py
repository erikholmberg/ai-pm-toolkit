#!/usr/bin/env python3
"""
Model selection scorecard (weighted MCDA)

Rank candidate models (or tiers) using explicit criteria scores and weights.
Optional sensitivity: bump one criterion's weight by +10% (renormalized) and
see if the ranking or winner changes.

Higher scores are always better on every criterion (invert latency/cost in the
CSV if needed, e.g. "latency_fit" 1–10 where 10 = meets SLO easily).

Usage:
    python model-selection-scorecard.py \\
        --scores scripts/samples/sample-model-selection-scores.csv \\
        --weights scripts/samples/sample-model-selection-weights.csv
    python model-selection-scorecard.py -s scores.csv -w weights.csv --json
    python model-selection-scorecard.py -s scores.csv -w weights.csv --no-sensitivity

CSV — scores (header row):
    model,quality,latency_fit,context,tooling,data_residency,vendor_risk
    gpt-4o,9,7,9,10,8,6

CSV — weights (header: criterion,weight):
    criterion,weight
    quality,0.25
    latency_fit,0.15

Weights are normalized to sum to 1 if they do not already.

Requirements:
    None (stdlib only).
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from typing import Any, Dict, List, Optional, Sequence, Tuple


def _col(fieldnames: Sequence[str], *aliases: str) -> Optional[str]:
    lower_map = {f.lower().strip(): f for f in fieldnames}
    for alias in aliases:
        key = alias.lower().strip()
        if key in lower_map:
            return lower_map[key]
    return None


def _float_cell(raw: str) -> float:
    s = str(raw).strip().rstrip("%")
    if not s:
        raise ValueError("empty")
    return float(s)


def load_weights(path: str) -> Dict[str, float]:
    """Returns lowercase criterion -> weight."""
    out: Dict[str, float] = {}
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            raise ValueError("weights CSV has no header")
        ccol = _col(reader.fieldnames, "criterion", "criteria", "name", "metric")
        wcol = _col(reader.fieldnames, "weight", "w", "importance")
        if not ccol or not wcol:
            raise ValueError("weights CSV needs criterion + weight columns")
        for row in reader:
            key = (row.get(ccol) or "").strip().lower()
            if not key:
                continue
            out[key] = _float_cell(row.get(wcol, ""))
    if not out:
        raise ValueError("no weight rows")
    s = sum(out.values())
    if s <= 0:
        raise ValueError("weights must sum to a positive value")
    return {k: v / s for k, v in out.items()}


def load_scores(path: str) -> Tuple[List[str], List[Dict[str, str]]]:
    """Field display order + rows as dicts (original keys)."""
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            raise ValueError("scores CSV has no header")
        fields = list(reader.fieldnames)
        rows = [dict(r) for r in reader]
    return fields, rows


def map_criteria_to_columns(
    fieldnames: Sequence[str],
    weights_lc: Dict[str, float],
) -> Dict[str, str]:
    """
    Map lowercase criterion name -> actual column name in scores CSV.
    Every weight key must match a column (case-insensitive), excluding model col.
    """
    lower_to_actual = {f.lower().strip(): f for f in fieldnames}
    model_col = _col(fieldnames, "model", "model_id", "name", "candidate")
    reserved = {model_col.lower()} if model_col else set()
    mapping: Dict[str, str] = {}
    for crit_lc in weights_lc:
        if crit_lc in reserved:
            raise ValueError(f'weight criterion "{crit_lc}" conflicts with model column')
        if crit_lc not in lower_to_actual:
            raise ValueError(
                f'weight criterion "{crit_lc}" has no matching column in scores CSV'
            )
        mapping[crit_lc] = lower_to_actual[crit_lc]
    return mapping


def weighted_total(
    row: Dict[str, str],
    weights_norm: Dict[str, float],
    crit_to_col: Dict[str, str],
) -> Tuple[float, Dict[str, float]]:
    contributions: Dict[str, float] = {}
    total = 0.0
    for crit_lc, w in weights_norm.items():
        col = crit_to_col[crit_lc]
        raw = row.get(col, "")
        score = _float_cell(raw)
        part = w * score
        contributions[crit_lc] = part
        total += part
    return total, contributions


def score_rows_for_weights(
    rows: List[Dict[str, str]],
    model_col: str,
    weights_norm: Dict[str, float],
    crit_to_col: Dict[str, str],
) -> List[Tuple[str, float, Dict[str, float]]]:
    """
    Score every row with a non-empty model name. Raises ValueError with row
    context if any required criterion cell is missing or invalid.
    """
    scored: List[Tuple[str, float, Dict[str, float]]] = []
    for row in rows:
        name = (row.get(model_col) or "").strip()
        if not name:
            continue
        try:
            total, contrib = weighted_total(row, weights_norm, crit_to_col)
        except ValueError as e:
            raise ValueError(f"row '{name}': {e}") from e
        scored.append((name, total, contrib))
    return scored


def rank_models(
    scored: List[Tuple[str, float, Dict[str, float]]],
) -> List[Tuple[str, float, Dict[str, float], int]]:
    """Sort by score desc, name asc; attach 1-based rank (ties get same rank? use dense rank)."""
    sorted_items = sorted(scored, key=lambda x: (-x[1], x[0].lower()))
    out: List[Tuple[str, float, Dict[str, float], int]] = []
    for i, (name, score, contrib) in enumerate(sorted_items, start=1):
        out.append((name, score, contrib, i))
    return out


def perturb_weights(weights_norm: Dict[str, float], bump_crit: str, bump: float) -> Dict[str, float]:
    """Multiply bump_crit's weight by (1+bump), renormalize."""
    w = dict(weights_norm)
    lc = bump_crit.lower()
    if lc not in w:
        raise KeyError(bump_crit)
    w[lc] *= 1.0 + bump
    s = sum(w.values())
    return {k: v / s for k, v in w.items()}


def ranking_names(
    rows: List[Dict[str, str]],
    model_col: str,
    weights_norm: Dict[str, float],
    crit_to_col: Dict[str, str],
) -> List[str]:
    scored = score_rows_for_weights(rows, model_col, weights_norm, crit_to_col)
    ranked = rank_models(scored)
    return [r[0] for r in ranked]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Weighted scorecard to rank models/options; optional weight sensitivity."
    )
    parser.add_argument(
        "--scores",
        "-s",
        required=True,
        help="CSV of models and numeric scores per criterion",
    )
    parser.add_argument(
        "--weights",
        "-w",
        required=True,
        help="CSV of criterion,weight",
    )
    parser.add_argument(
        "--bump",
        type=float,
        default=0.10,
        help="Relative bump to one criterion's weight in sensitivity (default: 0.10 = +10%%)",
    )
    parser.add_argument(
        "--no-sensitivity",
        action="store_true",
        help="Skip per-criterion weight bump analysis",
    )
    parser.add_argument("--json", action="store_true", help="Print JSON only (no tables)")
    args = parser.parse_args()

    try:
        weights_norm = load_weights(args.weights)
        fields, rows = load_scores(args.scores)
        model_col = _col(fields, "model", "model_id", "name", "candidate")
        if not model_col:
            print(
                "Error: scores CSV needs a model column (model, model_id, name, or candidate)",
                file=sys.stderr,
            )
            return 1
        crit_to_col = map_criteria_to_columns(fields, weights_norm)
    except (OSError, ValueError) as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    try:
        scored = score_rows_for_weights(rows, model_col, weights_norm, crit_to_col)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    if not scored:
        print("Error: no data rows with model names", file=sys.stderr)
        return 1

    ranked = rank_models(scored)
    baseline_order = [r[0] for r in ranked]
    winner = baseline_order[0]

    if args.json:
        payload: Dict[str, Any] = {
            "winner": winner,
            "ranking": [
                {
                    "rank": r[3],
                    "model": r[0],
                    "weighted_score": round(r[1], 4),
                    "contributions": {k: round(v, 4) for k, v in r[2].items()},
                }
                for r in ranked
            ],
            "weights": weights_norm,
        }
        if not args.no_sensitivity:
            sens = []
            try:
                for crit_lc in sorted(weights_norm.keys()):
                    try:
                        pw = perturb_weights(weights_norm, crit_lc, args.bump)
                    except KeyError:
                        continue
                    new_order = ranking_names(rows, model_col, pw, crit_to_col)
                    sens.append(
                        {
                            "bumped_criterion": crit_lc,
                            "relative_bump": args.bump,
                            "ranking": new_order,
                            "winner": new_order[0] if new_order else None,
                            "winner_changed": (new_order[0] if new_order else None) != winner,
                            "order_changed": new_order != baseline_order,
                        }
                    )
            except ValueError as e:
                print(f"Error: sensitivity: {e}", file=sys.stderr)
                return 1
            payload["sensitivity"] = sens
        print(json.dumps(payload, indent=2))
        return 0

    print("\n" + "=" * 64)
    print("MODEL SELECTION SCORECARD")
    print("=" * 64)
    print("\n📋 Weights (normalized):")
    for k in sorted(weights_norm.keys()):
        print(f"   • {k}: {weights_norm[k]:.3f}")

    print("\n📈 Weighted score (higher = better):")
    print(f"   {'Rank':<5} {'Model':<28} {'Score':>10}")
    print("   " + "-" * 46)
    for name, score, _, rank in ranked:
        print(f"   {rank:<5} {name:<28} {score:>10.3f}")
    print(f"\n   → Top pick: {winner}")

    if not args.no_sensitivity:
        pct = args.bump * 100
        print(f"\n🔁 Sensitivity (bump one criterion weight by +{pct:.0f}%, renormalize):")
        try:
            for crit_lc in sorted(weights_norm.keys()):
                pw = perturb_weights(weights_norm, crit_lc, args.bump)
                new_order = ranking_names(rows, model_col, pw, crit_to_col)
                new_winner = new_order[0] if new_order else None
                order_changed = new_order != baseline_order
                winner_changed = new_winner != winner
                if winner_changed:
                    status = f"winner → {new_winner}"
                elif order_changed:
                    status = "ranking shuffled (same winner)"
                else:
                    status = "no change"
                print(f"   • {crit_lc}: {status}")
        except ValueError as e:
            print(f"Error: sensitivity: {e}", file=sys.stderr)
            return 1

    print("\n📎 Tip: pair with multi-model-cost-comparator.py and eval runs for quality scores.")
    print("=" * 64)
    return 0


if __name__ == "__main__":
    sys.exit(main())
