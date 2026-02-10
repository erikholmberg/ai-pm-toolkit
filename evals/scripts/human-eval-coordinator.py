#!/usr/bin/env python3
"""
Human Eval Coordination Script

Generate evaluation task assignments across human raters, calculate inter-rater
reliability scores (Cohen's Kappa, Fleiss' Kappa, Krippendorff's Alpha), and
consolidate human evaluator results into a final dataset.

Bridges the gap between automated evals and real-world quality assessment.
Use this when you need human judgment on AI output quality, preference ranking,
or golden dataset creation.

Usage:
    # Generate task assignments for evaluators
    python human-eval-coordinator.py assign --tasks eval_tasks.json --raters 3 --overlap 2 --output assignments.json

    # Calculate inter-rater reliability from completed ratings
    python human-eval-coordinator.py reliability --ratings completed_ratings.json

    # Consolidate ratings into a final dataset (majority vote / average)
    python human-eval-coordinator.py consolidate --ratings completed_ratings.json --strategy majority --output final_ratings.json

    # Full report: reliability + consolidation + summary
    python human-eval-coordinator.py report --ratings completed_ratings.json --output report.json

Task JSON format (eval_tasks.json):
    [
        {"id": "task_001", "input": "Summarize this article...", "output": "The article discusses..."},
        {"id": "task_002", "input": "Translate this sentence...", "output": "La maison est..."}
    ]

Completed ratings JSON format (completed_ratings.json):
    [
        {"task_id": "task_001", "rater_id": "rater_A", "score": 4, "label": "good", "notes": "..."},
        {"task_id": "task_001", "rater_id": "rater_B", "score": 3, "label": "acceptable", "notes": "..."},
        {"task_id": "task_002", "rater_id": "rater_A", "score": 5, "label": "excellent", "notes": "..."}
    ]

Requirements:
    None (stdlib only). Optional: numpy, scipy for advanced statistics.
"""

import argparse
import csv
import json
import math
import random
import sys
from collections import Counter, defaultdict
from datetime import datetime
from itertools import combinations
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


# ───────────────────────────────────────────────────────────
#  Task Assignment
# ───────────────────────────────────────────────────────────


def generate_assignments(
    tasks: List[Dict],
    num_raters: int,
    overlap: int = 2,
    rater_names: Optional[List[str]] = None,
    seed: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Generate balanced task assignments ensuring each task is rated by `overlap` raters.

    Args:
        tasks: List of task dicts (each must have "id")
        num_raters: Total number of raters
        overlap: Number of raters per task (for inter-rater reliability)
        rater_names: Optional list of rater identifiers
        seed: Random seed for reproducibility

    Returns:
        Assignment dict with per-rater task lists and metadata
    """
    if overlap > num_raters:
        raise ValueError(f"overlap ({overlap}) cannot exceed num_raters ({num_raters})")
    if overlap < 1:
        raise ValueError("overlap must be >= 1")

    if seed is not None:
        random.seed(seed)

    raters = rater_names or [f"rater_{i+1:02d}" for i in range(num_raters)]
    if len(raters) < num_raters:
        raters.extend(f"rater_{i+1:02d}" for i in range(len(raters), num_raters))
    raters = raters[:num_raters]

    task_ids = [t["id"] for t in tasks]
    n_tasks = len(task_ids)

    # Round-robin assignment: distribute tasks so each rater gets roughly equal load
    # and each task gets exactly `overlap` raters
    assignments: Dict[str, List[str]] = {r: [] for r in raters}
    task_raters: Dict[str, List[str]] = {tid: [] for tid in task_ids}

    # Build assignment: for each task, pick `overlap` raters with fewest assignments
    for tid in task_ids:
        # Sort raters by current load, break ties randomly
        raters_sorted = sorted(raters, key=lambda r: (len(assignments[r]), random.random()))
        chosen = raters_sorted[:overlap]
        for r in chosen:
            assignments[r].append(tid)
            task_raters[tid].append(r)

    # Build per-rater task details
    task_by_id = {t["id"]: t for t in tasks}
    rater_assignments = {}
    for rater, tids in assignments.items():
        rater_assignments[rater] = [task_by_id[tid] for tid in tids]

    # Calculate stats
    loads = [len(v) for v in assignments.values()]
    stats = {
        "total_tasks": n_tasks,
        "total_raters": num_raters,
        "overlap_per_task": overlap,
        "total_ratings_needed": n_tasks * overlap,
        "tasks_per_rater_min": min(loads) if loads else 0,
        "tasks_per_rater_max": max(loads) if loads else 0,
        "tasks_per_rater_avg": sum(loads) / len(loads) if loads else 0,
        "seed": seed,
        "generated_at": datetime.now().isoformat(),
    }

    return {
        "metadata": stats,
        "rater_assignments": {r: tids for r, tids in assignments.items()},
        "task_raters": task_raters,
        "full_assignments": rater_assignments,
    }


# ───────────────────────────────────────────────────────────
#  Inter-Rater Reliability
# ───────────────────────────────────────────────────────────


def _build_rating_matrix(
    ratings: List[Dict],
    score_field: str = "score",
) -> Tuple[Dict[str, Dict[str, Any]], List[str], List[str]]:
    """
    Build a task_id → rater_id → score mapping.
    Returns (matrix, task_ids, rater_ids).
    """
    matrix: Dict[str, Dict[str, Any]] = defaultdict(dict)
    rater_set = set()
    for r in ratings:
        tid = r.get("task_id") or r.get("id")
        rid = r.get("rater_id") or r.get("rater")
        score = r.get(score_field)
        if tid and rid and score is not None:
            matrix[tid][rid] = score
            rater_set.add(rid)
    task_ids = sorted(matrix.keys())
    rater_ids = sorted(rater_set)
    return dict(matrix), task_ids, rater_ids


def cohens_kappa(
    ratings: List[Dict],
    rater_a: str,
    rater_b: str,
    score_field: str = "score",
) -> Optional[float]:
    """
    Cohen's Kappa for two raters on shared tasks (categorical agreement).
    Returns kappa value or None if insufficient data.
    """
    matrix, task_ids, _ = _build_rating_matrix(ratings, score_field)

    # Find shared tasks
    shared = [tid for tid in task_ids if rater_a in matrix[tid] and rater_b in matrix[tid]]
    if len(shared) < 2:
        return None

    scores_a = [matrix[tid][rater_a] for tid in shared]
    scores_b = [matrix[tid][rater_b] for tid in shared]

    # Treat scores as categorical labels
    labels = sorted(set(scores_a + scores_b))
    n = len(shared)

    # Observed agreement
    agree = sum(1 for a, b in zip(scores_a, scores_b) if a == b)
    p_o = agree / n

    # Expected agreement by chance
    p_e = 0.0
    for label in labels:
        p_a = sum(1 for s in scores_a if s == label) / n
        p_b = sum(1 for s in scores_b if s == label) / n
        p_e += p_a * p_b

    if p_e >= 1.0:
        return 1.0 if p_o >= 1.0 else 0.0
    return (p_o - p_e) / (1.0 - p_e)


def fleiss_kappa(
    ratings: List[Dict],
    score_field: str = "score",
) -> Optional[float]:
    """
    Fleiss' Kappa for multiple raters (categorical agreement).
    Works with any number of raters and handles missing assignments.
    Returns kappa value or None if insufficient data.
    """
    matrix, task_ids, rater_ids = _build_rating_matrix(ratings, score_field)

    if len(task_ids) < 2:
        return None

    # Collect all possible categories
    all_scores = []
    for tid in task_ids:
        all_scores.extend(matrix[tid].values())
    categories = sorted(set(all_scores))

    if len(categories) < 2:
        return None

    n_subjects = len(task_ids)
    cat_index = {c: i for i, c in enumerate(categories)}
    k = len(categories)

    # Build count matrix: for each task, count how many raters assigned each category
    count_matrix = []
    raters_per_task = []
    for tid in task_ids:
        counts = [0] * k
        n_raters = 0
        for rid, score in matrix[tid].items():
            if score in cat_index:
                counts[cat_index[score]] += 1
                n_raters += 1
        if n_raters >= 2:
            count_matrix.append(counts)
            raters_per_task.append(n_raters)

    if not count_matrix:
        return None

    N = len(count_matrix)

    # P_i for each subject
    P_i_list = []
    for i, counts in enumerate(count_matrix):
        n = raters_per_task[i]
        if n < 2:
            continue
        sum_sq = sum(c * c for c in counts)
        P_i = (sum_sq - n) / (n * (n - 1))
        P_i_list.append(P_i)

    if not P_i_list:
        return None

    P_bar = sum(P_i_list) / len(P_i_list)

    # P_e: proportion of all assignments in each category, squared
    total_assignments = sum(raters_per_task[:N])
    p_j = []
    for j in range(k):
        col_sum = sum(count_matrix[i][j] for i in range(N))
        p_j.append(col_sum / total_assignments if total_assignments > 0 else 0)

    P_e = sum(p * p for p in p_j)

    if P_e >= 1.0:
        return 1.0 if P_bar >= 1.0 else 0.0

    return (P_bar - P_e) / (1.0 - P_e)


def krippendorff_alpha(
    ratings: List[Dict],
    score_field: str = "score",
    level: str = "ordinal",
) -> Optional[float]:
    """
    Krippendorff's Alpha for inter-rater reliability.
    Supports nominal, ordinal, and interval/ratio data.
    Handles missing data naturally.

    Args:
        ratings: List of rating dicts
        score_field: Key for the score value
        level: Measurement level — "nominal", "ordinal", or "interval"

    Returns:
        Alpha value or None if insufficient data.
    """
    matrix, task_ids, rater_ids = _build_rating_matrix(ratings, score_field)

    # Build coincidence matrix (value pairs within each unit)
    all_values = set()
    for tid in task_ids:
        for v in matrix[tid].values():
            all_values.add(v)

    values = sorted(all_values)
    if len(values) < 2:
        return None

    val_index = {v: i for i, v in enumerate(values)}
    n_val = len(values)

    # Distance function
    def delta_sq(v1, v2):
        if level == "nominal":
            return 0.0 if v1 == v2 else 1.0
        elif level == "interval":
            return (v1 - v2) ** 2
        elif level == "ordinal":
            i1, i2 = val_index[v1], val_index[v2]
            low, high = min(i1, i2), max(i1, i2)
            # Sum of ranks between i1 and i2 inclusive
            rank_sum = sum(1 for _ in range(low, high + 1))
            return (rank_sum - 1) ** 2
        return (v1 - v2) ** 2  # default to interval

    # Observed disagreement (D_o)
    total_pairs = 0
    D_o = 0.0
    for tid in task_ids:
        rater_scores = list(matrix[tid].values())
        m = len(rater_scores)
        if m < 2:
            continue
        for i in range(m):
            for j in range(i + 1, m):
                D_o += delta_sq(rater_scores[i], rater_scores[j])
                total_pairs += 1

    if total_pairs == 0:
        return None

    D_o /= total_pairs

    # Expected disagreement (D_e)
    # Frequency of each value across all ratings
    freq = Counter()
    total_ratings = 0
    for tid in task_ids:
        for v in matrix[tid].values():
            freq[v] += 1
            total_ratings += 1

    D_e = 0.0
    total_e_pairs = 0
    for v1 in values:
        for v2 in values:
            if v1 <= v2:  # avoid double counting but include self
                n_pairs = freq[v1] * freq[v2] if v1 != v2 else freq[v1] * (freq[v1] - 1)
                d = delta_sq(v1, v2)
                D_e += n_pairs * d
                total_e_pairs += n_pairs

    if total_e_pairs == 0:
        return None

    D_e /= total_e_pairs

    if D_e == 0:
        return 1.0 if D_o == 0 else 0.0

    return 1.0 - (D_o / D_e)


def pairwise_agreement(
    ratings: List[Dict],
    score_field: str = "score",
) -> Dict[str, Any]:
    """
    Calculate pairwise percent agreement between all rater pairs.
    """
    matrix, task_ids, rater_ids = _build_rating_matrix(ratings, score_field)

    pairs = {}
    for ra, rb in combinations(rater_ids, 2):
        shared = [tid for tid in task_ids if ra in matrix[tid] and rb in matrix[tid]]
        if not shared:
            continue
        agree = sum(1 for tid in shared if matrix[tid][ra] == matrix[tid][rb])
        pct = 100.0 * agree / len(shared)
        pairs[f"{ra} × {rb}"] = {
            "shared_tasks": len(shared),
            "agreements": agree,
            "agreement_pct": round(pct, 1),
        }

    total_shared = sum(p["shared_tasks"] for p in pairs.values())
    total_agree = sum(p["agreements"] for p in pairs.values())
    overall_pct = 100.0 * total_agree / total_shared if total_shared > 0 else 0

    return {
        "pairwise": pairs,
        "overall_agreement_pct": round(overall_pct, 1),
    }


def compute_reliability(
    ratings: List[Dict],
    score_field: str = "score",
) -> Dict[str, Any]:
    """
    Compute all inter-rater reliability metrics.
    """
    matrix, task_ids, rater_ids = _build_rating_matrix(ratings, score_field)

    results: Dict[str, Any] = {
        "n_tasks": len(task_ids),
        "n_raters": len(rater_ids),
        "n_ratings": len(ratings),
        "rater_ids": rater_ids,
    }

    # Pairwise agreement
    agreement = pairwise_agreement(ratings, score_field)
    results["pairwise_agreement"] = agreement

    # Cohen's Kappa (pairwise)
    kappa_pairs = {}
    for ra, rb in combinations(rater_ids, 2):
        k = cohens_kappa(ratings, ra, rb, score_field)
        if k is not None:
            kappa_pairs[f"{ra} × {rb}"] = round(k, 4)
    results["cohens_kappa_pairwise"] = kappa_pairs
    if kappa_pairs:
        results["cohens_kappa_avg"] = round(
            sum(kappa_pairs.values()) / len(kappa_pairs), 4
        )

    # Fleiss' Kappa
    fk = fleiss_kappa(ratings, score_field)
    results["fleiss_kappa"] = round(fk, 4) if fk is not None else None

    # Krippendorff's Alpha
    for level in ["nominal", "ordinal", "interval"]:
        alpha = krippendorff_alpha(ratings, score_field, level)
        results[f"krippendorff_alpha_{level}"] = round(alpha, 4) if alpha is not None else None

    return results


# ───────────────────────────────────────────────────────────
#  Consolidation
# ───────────────────────────────────────────────────────────


def consolidate_ratings(
    ratings: List[Dict],
    strategy: str = "majority",
    score_field: str = "score",
    label_field: str = "label",
) -> List[Dict]:
    """
    Consolidate multiple rater scores into a single rating per task.

    Strategies:
        majority: Most common label/score wins (ties broken by highest score)
        average:  Average of numeric scores
        median:   Median of numeric scores
        min:      Minimum score (conservative)
        max:      Maximum score (optimistic)

    Returns:
        List of consolidated results per task.
    """
    matrix, task_ids, rater_ids = _build_rating_matrix(ratings, score_field)

    # Also collect labels
    label_matrix: Dict[str, Dict[str, str]] = defaultdict(dict)
    notes_matrix: Dict[str, Dict[str, str]] = defaultdict(dict)
    for r in ratings:
        tid = r.get("task_id") or r.get("id")
        rid = r.get("rater_id") or r.get("rater")
        if tid and rid:
            if label_field in r and r[label_field]:
                label_matrix[tid][rid] = r[label_field]
            if "notes" in r and r["notes"]:
                notes_matrix[tid][rid] = r["notes"]

    consolidated = []
    for tid in task_ids:
        scores = list(matrix[tid].values())
        raters = list(matrix[tid].keys())
        labels = list(label_matrix.get(tid, {}).values())
        notes = list(notes_matrix.get(tid, {}).values())

        if not scores:
            continue

        if strategy == "majority":
            score_counts = Counter(scores)
            max_count = score_counts.most_common(1)[0][1]
            tied_scores = [s for s, c in score_counts.items() if c == max_count]
            final_score = max(tied_scores)  # break ties by highest score
            if labels:
                label_counts = Counter(labels)
                max_label_count = label_counts.most_common(1)[0][1]
                tied_labels = [l for l, c in label_counts.items() if c == max_label_count]
                final_label = sorted(tied_labels)[0]  # break ties alphabetically
            else:
                final_label = None
        elif strategy == "average":
            final_score = round(sum(scores) / len(scores), 2)
            final_label = labels[0] if labels else None
        elif strategy == "median":
            sorted_scores = sorted(scores)
            n = len(sorted_scores)
            if n % 2 == 0:
                final_score = (sorted_scores[n // 2 - 1] + sorted_scores[n // 2]) / 2
            else:
                final_score = sorted_scores[n // 2]
            final_label = None
        elif strategy == "min":
            final_score = min(scores)
            final_label = None
        elif strategy == "max":
            final_score = max(scores)
            final_label = None
        else:
            raise ValueError(f"Unknown strategy: {strategy}")

        # Agreement for this task
        unique_scores = set(scores)
        agreement = len(scores) - len(unique_scores) + 1  # rough measure
        full_agreement = len(unique_scores) == 1

        consolidated.append({
            "task_id": tid,
            "final_score": final_score,
            "final_label": final_label,
            "strategy": strategy,
            "num_raters": len(scores),
            "individual_scores": scores,
            "individual_raters": raters,
            "score_range": [min(scores), max(scores)],
            "score_std": round(_std(scores), 3) if len(scores) > 1 else 0.0,
            "full_agreement": full_agreement,
            "notes": notes if notes else None,
        })

    return consolidated


def _std(values: List[float]) -> float:
    """Standard deviation (population)."""
    if len(values) < 2:
        return 0.0
    mean = sum(values) / len(values)
    variance = sum((x - mean) ** 2 for x in values) / len(values)
    return math.sqrt(variance)


# ───────────────────────────────────────────────────────────
#  Reporting
# ───────────────────────────────────────────────────────────


def print_assignment_report(result: Dict) -> None:
    """Print assignment summary."""
    meta = result["metadata"]

    print("\n" + "=" * 70)
    print("📊 HUMAN EVAL TASK ASSIGNMENTS")
    print("=" * 70)

    print(f"\n📋 OVERVIEW:")
    print(f"   • Total tasks:           {meta['total_tasks']}")
    print(f"   • Total raters:          {meta['total_raters']}")
    print(f"   • Overlap per task:      {meta['overlap_per_task']} raters")
    print(f"   • Total ratings needed:  {meta['total_ratings_needed']}")

    print(f"\n📈 WORKLOAD DISTRIBUTION:")
    print(f"   • Tasks per rater (min): {meta['tasks_per_rater_min']}")
    print(f"   • Tasks per rater (max): {meta['tasks_per_rater_max']}")
    print(f"   • Tasks per rater (avg): {meta['tasks_per_rater_avg']:.1f}")

    print(f"\n👥 RATER ASSIGNMENTS:")
    for rater, tids in result["rater_assignments"].items():
        print(f"   • {rater}: {len(tids)} tasks")

    print("\n" + "=" * 70)


def print_reliability_report(result: Dict) -> None:
    """Print inter-rater reliability report."""
    print("\n" + "=" * 70)
    print("📊 INTER-RATER RELIABILITY REPORT")
    print("=" * 70)

    print(f"\n📋 OVERVIEW:")
    print(f"   • Tasks rated:    {result['n_tasks']}")
    print(f"   • Raters:         {result['n_raters']} ({', '.join(result['rater_ids'])})")
    print(f"   • Total ratings:  {result['n_ratings']}")

    # Pairwise agreement
    agreement = result["pairwise_agreement"]
    print(f"\n🤝 PAIRWISE AGREEMENT:")
    print(f"   Overall: {agreement['overall_agreement_pct']}%")
    for pair, data in agreement["pairwise"].items():
        print(f"   • {pair}: {data['agreement_pct']}% ({data['agreements']}/{data['shared_tasks']} tasks)")

    # Cohen's Kappa
    if result.get("cohens_kappa_pairwise"):
        print(f"\n📐 COHEN'S KAPPA (pairwise):")
        for pair, k in result["cohens_kappa_pairwise"].items():
            label = _kappa_label(k)
            print(f"   • {pair}: {k:.4f} ({label})")
        if "cohens_kappa_avg" in result:
            label = _kappa_label(result["cohens_kappa_avg"])
            print(f"   Average: {result['cohens_kappa_avg']:.4f} ({label})")

    # Fleiss' Kappa
    if result.get("fleiss_kappa") is not None:
        label = _kappa_label(result["fleiss_kappa"])
        print(f"\n📐 FLEISS' KAPPA (multi-rater):")
        print(f"   κ = {result['fleiss_kappa']:.4f} ({label})")

    # Krippendorff's Alpha
    for level in ["nominal", "ordinal", "interval"]:
        key = f"krippendorff_alpha_{level}"
        if result.get(key) is not None:
            print(f"\n📐 KRIPPENDORFF'S ALPHA ({level}):")
            alpha = result[key]
            if alpha >= 0.8:
                quality = "good reliability"
            elif alpha >= 0.667:
                quality = "acceptable for tentative conclusions"
            else:
                quality = "insufficient — consider rater training or clearer guidelines"
            print(f"   α = {alpha:.4f} ({quality})")

    # Reference
    print(f"\n📐 KAPPA INTERPRETATION GUIDE:")
    print(f"   • < 0.00  Poor (worse than chance)")
    print(f"   • 0.00–0.20  Slight agreement")
    print(f"   • 0.21–0.40  Fair agreement")
    print(f"   • 0.41–0.60  Moderate agreement")
    print(f"   • 0.61–0.80  Substantial agreement")
    print(f"   • 0.81–1.00  Almost perfect agreement")

    print("\n" + "=" * 70)


def print_consolidation_report(consolidated: List[Dict]) -> None:
    """Print consolidation summary."""
    if not consolidated:
        print("No consolidated results.")
        return

    print("\n" + "=" * 70)
    print("📊 CONSOLIDATED RATINGS")
    print("=" * 70)

    n = len(consolidated)
    full_agree = sum(1 for c in consolidated if c["full_agreement"])
    avg_std = sum(c["score_std"] for c in consolidated) / n if n else 0
    scores = [c["final_score"] for c in consolidated]
    avg_score = sum(scores) / len(scores) if scores else 0

    print(f"\n📋 SUMMARY:")
    print(f"   • Tasks consolidated:    {n}")
    print(f"   • Strategy:              {consolidated[0]['strategy']}")
    print(f"   • Full agreement:        {full_agree}/{n} ({100*full_agree/n:.0f}%)")
    print(f"   • Avg score std dev:     {avg_std:.3f}")
    print(f"   • Avg final score:       {avg_score:.2f}")

    # Score distribution
    score_counts = Counter(c["final_score"] for c in consolidated)
    print(f"\n📈 SCORE DISTRIBUTION:")
    for score in sorted(score_counts.keys()):
        count = score_counts[score]
        bar_len = int(40 * count / n)
        bar = "█" * bar_len + "░" * (40 - bar_len)
        print(f"   {score:>5}: {count:>4} {bar} ({100*count/n:.0f}%)")

    # Disagreement flags
    high_disagreement = [c for c in consolidated if c["score_std"] > 1.0]
    if high_disagreement:
        print(f"\n⚠️  HIGH DISAGREEMENT TASKS ({len(high_disagreement)}):")
        for c in sorted(high_disagreement, key=lambda x: -x["score_std"])[:10]:
            print(f"   • {c['task_id']}: scores={c['individual_scores']} std={c['score_std']:.2f}")

    print("\n" + "=" * 70)


def _kappa_label(k: float) -> str:
    """Interpret kappa value per Landis & Koch (1977) scale."""
    if k < 0:
        return "poor"
    elif k <= 0.20:
        return "slight"
    elif k <= 0.40:
        return "fair"
    elif k <= 0.60:
        return "moderate"
    elif k <= 0.80:
        return "substantial"
    else:
        return "almost perfect"


# ───────────────────────────────────────────────────────────
#  CLI
# ───────────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(
        description="Coordinate human evaluations: assign tasks, measure reliability, consolidate ratings.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Commands:
  assign        Generate task assignments for raters
  reliability   Calculate inter-rater reliability (kappa, alpha)
  consolidate   Merge multiple ratings per task into final scores
  report        Full report: reliability + consolidation + summary

Examples:
  python human-eval-coordinator.py assign --tasks tasks.json --raters 5 --overlap 3
  python human-eval-coordinator.py reliability --ratings completed.json
  python human-eval-coordinator.py consolidate --ratings completed.json --strategy average
  python human-eval-coordinator.py report --ratings completed.json --output report.json
        """,
    )

    sub = parser.add_subparsers(dest="command", required=True)

    # assign
    assign_p = sub.add_parser("assign", help="Generate task assignments")
    assign_p.add_argument("--tasks", "-t", required=True, help="Tasks JSON file")
    assign_p.add_argument("--raters", "-r", type=int, required=True, help="Number of raters")
    assign_p.add_argument("--overlap", type=int, default=2, help="Raters per task (default: 2)")
    assign_p.add_argument("--rater-names", nargs="+", help="Custom rater identifiers")
    assign_p.add_argument("--seed", type=int, default=None, help="Random seed for reproducibility")
    assign_p.add_argument("--output", "-o", help="Output file (JSON)")

    # reliability
    rel_p = sub.add_parser("reliability", help="Calculate inter-rater reliability")
    rel_p.add_argument("--ratings", "-r", required=True, help="Completed ratings JSON")
    rel_p.add_argument("--score-field", default="score", help="Score field name (default: score)")
    rel_p.add_argument("--output", "-o", help="Output file (JSON)")

    # consolidate
    con_p = sub.add_parser("consolidate", help="Consolidate multiple ratings per task")
    con_p.add_argument("--ratings", "-r", required=True, help="Completed ratings JSON")
    con_p.add_argument(
        "--strategy", "-s", default="majority",
        choices=["majority", "average", "median", "min", "max"],
        help="Consolidation strategy (default: majority)",
    )
    con_p.add_argument("--score-field", default="score", help="Score field name")
    con_p.add_argument("--output", "-o", help="Output file (JSON)")

    # report
    rep_p = sub.add_parser("report", help="Full reliability + consolidation report")
    rep_p.add_argument("--ratings", "-r", required=True, help="Completed ratings JSON")
    rep_p.add_argument("--score-field", default="score", help="Score field name")
    rep_p.add_argument(
        "--strategy", "-s", default="majority",
        choices=["majority", "average", "median", "min", "max"],
        help="Consolidation strategy (default: majority)",
    )
    rep_p.add_argument("--output", "-o", help="Output full report JSON")

    args = parser.parse_args()

    # ── assign ──
    if args.command == "assign":
        try:
            with open(args.tasks) as f:
                tasks = json.load(f)
            if isinstance(tasks, dict) and "tasks" in tasks:
                tasks = tasks["tasks"]
        except Exception as e:
            print(f"Error loading tasks: {e}", file=sys.stderr)
            return 1

        result = generate_assignments(
            tasks, args.raters, args.overlap, args.rater_names, args.seed
        )
        print_assignment_report(result)

        if args.output:
            with open(args.output, "w") as f:
                json.dump(result, f, indent=2)
            print(f"Assignments saved to {args.output}")

    # ── reliability ──
    elif args.command == "reliability":
        try:
            with open(args.ratings) as f:
                ratings = json.load(f)
        except Exception as e:
            print(f"Error loading ratings: {e}", file=sys.stderr)
            return 1

        result = compute_reliability(ratings, args.score_field)
        print_reliability_report(result)

        if args.output:
            with open(args.output, "w") as f:
                json.dump(result, f, indent=2, default=str)
            print(f"Reliability report saved to {args.output}")

    # ── consolidate ──
    elif args.command == "consolidate":
        try:
            with open(args.ratings) as f:
                ratings = json.load(f)
        except Exception as e:
            print(f"Error loading ratings: {e}", file=sys.stderr)
            return 1

        consolidated = consolidate_ratings(ratings, args.strategy, args.score_field)
        print_consolidation_report(consolidated)

        if args.output:
            with open(args.output, "w") as f:
                json.dump(consolidated, f, indent=2)
            print(f"Consolidated ratings saved to {args.output}")

    # ── report ──
    elif args.command == "report":
        try:
            with open(args.ratings) as f:
                ratings = json.load(f)
        except Exception as e:
            print(f"Error loading ratings: {e}", file=sys.stderr)
            return 1

        reliability = compute_reliability(ratings, args.score_field)
        print_reliability_report(reliability)

        consolidated = consolidate_ratings(ratings, args.strategy, args.score_field)
        print_consolidation_report(consolidated)

        if args.output:
            report = {
                "generated_at": datetime.now().isoformat(),
                "reliability": reliability,
                "consolidated": consolidated,
            }
            with open(args.output, "w") as f:
                json.dump(report, f, indent=2, default=str)
            print(f"Full report saved to {args.output}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
