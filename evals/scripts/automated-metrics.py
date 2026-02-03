#!/usr/bin/env python3
"""
Automated Metric Calculators for LLM Evaluation

Compute BLEU, ROUGE, exact match, and related metrics for reference-based evaluation.

Usage:
    python automated-metrics.py --input results.json --output metrics.json
    python automated-metrics.py --input test_cases.json --reference-field expected_output

Requirements:
    pip install nltk rouge-score
    python -c "import nltk; nltk.download('punkt')"
"""

import argparse
import json
import re
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import List, Dict, Optional, Any

# Optional imports
try:
    from nltk.tokenize import word_tokenize
    from nltk.translate.bleu_score import sentence_bleu, SmoothingFunction
    NLTK_AVAILABLE = True
except ImportError:
    NLTK_AVAILABLE = False

try:
    from rouge_score import rouge_scorer
    ROUGE_AVAILABLE = True
except ImportError:
    ROUGE_AVAILABLE = False


@dataclass
class MetricResult:
    """Result of computing metrics for a single case."""
    id: str
    exact_match: float
    contains_reference: float
    bleu: Optional[float] = None
    rouge_1: Optional[float] = None
    rouge_2: Optional[float] = None
    rouge_l: Optional[float] = None
    length_ratio: Optional[float] = None


def exact_match(prediction: str, reference: str, normalize: bool = True) -> float:
    """
    Score 1.0 if prediction matches reference exactly (after optional normalization).
    """
    if not reference:
        return 0.0
    pred = prediction.strip()
    ref = reference.strip()
    if normalize:
        pred = re.sub(r'\s+', ' ', pred).strip().lower()
        ref = re.sub(r'\s+', ' ', ref).strip().lower()
    return 1.0 if pred == ref else 0.0


def contains_reference(prediction: str, reference: str) -> float:
    """
    Score 1.0 if prediction contains the reference string (case-insensitive).
    """
    if not reference:
        return 0.0
    return 1.0 if reference.strip().lower() in prediction.strip().lower() else 0.0


def normalize_for_bleu(text: str) -> List[str]:
    """Tokenize for BLEU (word-level)."""
    if not NLTK_AVAILABLE:
        return text.split()
    try:
        return word_tokenize(text.lower())
    except Exception:
        return text.split()


def compute_bleu(prediction: str, reference: str) -> Optional[float]:
    """
    Compute BLEU score (capped at 1.0). Returns None if nltk not available.
    """
    if not NLTK_AVAILABLE or not reference:
        return None
    pred_tokens = normalize_for_bleu(prediction)
    ref_tokens = normalize_for_bleu(reference)
    if not ref_tokens:
        return None
    smoothing = SmoothingFunction()
    try:
        score = sentence_bleu(
            [ref_tokens],
            pred_tokens,
            weights=(0.25, 0.25, 0.25, 0.25),
            smoothing_function=smoothing.method1
        )
        return min(1.0, float(score))
    except Exception:
        return None


def compute_rouge(prediction: str, reference: str) -> Dict[str, Optional[float]]:
    """
    Compute ROUGE-1, ROUGE-2, ROUGE-L F1. Returns dict with None values if rouge_score not available.
    """
    result = {"rouge_1": None, "rouge_2": None, "rouge_l": None}
    if not ROUGE_AVAILABLE or not reference:
        return result
    try:
        scorer = rouge_scorer.RougeScorer(["rouge1", "rouge2", "rougeL"], use_stemmer=False)
        scores = scorer.score(reference, prediction)
        result["rouge_1"] = scores["rouge1"].fmeasure
        result["rouge_2"] = scores["rouge2"].fmeasure
        result["rouge_l"] = scores["rougeL"].fmeasure
    except Exception:
        pass
    return result


def length_ratio(prediction: str, reference: str) -> Optional[float]:
    """
    Ratio of prediction length to reference length (by word count). Clamped to [0, 2].
    """
    if not reference:
        return None
    pred_words = len(prediction.split())
    ref_words = len(reference.split())
    if ref_words == 0:
        return None
    ratio = pred_words / ref_words
    return min(2.0, max(0.0, ratio))


def compute_metrics(
    case_id: str,
    prediction: str,
    reference: Optional[str],
    include_bleu: bool = True,
    include_rouge: bool = True
) -> MetricResult:
    """
    Compute all metrics for a single prediction/reference pair.
    """
    ref = reference or ""
    em = exact_match(prediction, ref)
    contains = contains_reference(prediction, ref)

    bleu_val = compute_bleu(prediction, ref) if include_bleu else None
    rouge_vals = compute_rouge(prediction, ref) if include_rouge else {}
    len_ratio = length_ratio(prediction, ref) if ref else None

    return MetricResult(
        id=case_id,
        exact_match=em,
        contains_reference=contains,
        bleu=bleu_val,
        rouge_1=rouge_vals.get("rouge_1"),
        rouge_2=rouge_vals.get("rouge_2"),
        rouge_l=rouge_vals.get("rouge_l"),
        length_ratio=len_ratio
    )


def load_cases(filepath: str, prediction_field: str = "output", reference_field: str = "expected_output") -> List[Dict]:
    """Load test cases from JSON. Each item must have id, prediction_field, and optionally reference_field."""
    with open(filepath, "r") as f:
        data = json.load(f)
    if isinstance(data, list):
        return data
    if isinstance(data, dict) and "test_cases" in data:
        return data["test_cases"]
    if isinstance(data, dict) and "cases" in data:
        return data["cases"]
    raise ValueError("JSON must be a list of cases or dict with 'test_cases' or 'cases'")


def run_metrics(
    input_path: str,
    prediction_field: str = "output",
    reference_field: str = "expected_output",
    include_bleu: bool = True,
    include_rouge: bool = True
) -> List[MetricResult]:
    """
    Load cases from input_path and compute metrics for each.
    """
    cases = load_cases(input_path, prediction_field, reference_field)
    results = []
    for c in cases:
        case_id = c.get("id", str(len(results)))
        pred = c.get(prediction_field, "")
        ref = c.get(reference_field)
        r = compute_metrics(case_id, pred, ref, include_bleu, include_rouge)
        results.append(r)
    return results


def aggregate_metrics(results: List[MetricResult]) -> Dict[str, Any]:
    """Compute mean (and count) for each metric across results."""
    if not results:
        return {}
    agg = {}
    for key in ["exact_match", "contains_reference", "bleu", "rouge_1", "rouge_2", "rouge_l", "length_ratio"]:
        vals = [getattr(r, key) for r in results if getattr(r, key) is not None]
        if vals:
            agg[key] = {"mean": sum(vals) / len(vals), "count": len(vals)}
        else:
            agg[key] = {"mean": None, "count": 0}
    agg["total_cases"] = len(results)
    return agg


def main():
    parser = argparse.ArgumentParser(
        description="Compute BLEU, ROUGE, exact match and related metrics for eval outputs"
    )
    parser.add_argument("--input", "-i", required=True, help="Input JSON: list of {id, output, expected_output}")
    parser.add_argument("--output", "-o", help="Output JSON for per-case and aggregate metrics")
    parser.add_argument("--prediction-field", default="output", help="Field name for model output")
    parser.add_argument("--reference-field", default="expected_output", help="Field name for reference")
    parser.add_argument("--no-bleu", action="store_true", help="Skip BLEU (e.g. if nltk not installed)")
    parser.add_argument("--no-rouge", action="store_true", help="Skip ROUGE")
    args = parser.parse_args()

    if not NLTK_AVAILABLE and not args.no_bleu:
        print("Warning: nltk not installed. BLEU will be skipped. pip install nltk && python -c \"import nltk; nltk.download('punkt')\"")
    if not ROUGE_AVAILABLE and not args.no_rouge:
        print("Warning: rouge-score not installed. ROUGE will be skipped. pip install rouge-score")

    results = run_metrics(
        args.input,
        prediction_field=args.prediction_field,
        reference_field=args.reference_field,
        include_bleu=not args.no_bleu,
        include_rouge=not args.no_rouge
    )
    aggregate = aggregate_metrics(results)

    if args.output:
        out = {
            "per_case": [asdict(r) for r in results],
            "aggregate": aggregate
        }
        with open(args.output, "w") as f:
            json.dump(out, f, indent=2)
        print(f"Wrote {len(results)} results and aggregate to {args.output}")
    else:
        print(json.dumps({"aggregate": aggregate}, indent=2))

    return 0


if __name__ == "__main__":
    exit(main())
