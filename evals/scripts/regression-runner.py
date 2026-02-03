#!/usr/bin/env python3
"""
Regression Test Runner for LLM Evals

Compare new eval results against a baseline and flag regressions.

Usage:
    python regression-runner.py --baseline baseline.json --new new.json
    python regression-runner.py --baseline baseline.json --new new.json --threshold 0.05

Requirements:
    None (stdlib only)
"""

import argparse
import json
import sys
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List, Optional, Any


@dataclass
class RegressionResult:
    """Single case regression: same id, different scores."""
    test_case_id: str
    baseline_score: float
    new_score: float
    delta: float
    delta_pct: float
    is_regression: bool
    metric_name: str


def load_results(path: str) -> List[Dict[str, Any]]:
    """Load results from JSON. Expect list of dicts with test_case_id and scores."""
    with open(path, "r") as f:
        data = json.load(f)
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        if "per_case" in data:
            return data["per_case"]
        if "results" in data:
            return data["results"]
    return []


def get_score(row: Dict[str, Any], metric: str) -> Optional[float]:
    """Extract numeric score from a result row. Handles scores dict or top-level keys."""
    if isinstance(row.get("scores"), dict):
        return row["scores"].get(metric) or row["scores"].get("overall")
    return row.get(metric) or row.get("overall_score") or row.get("score")


def build_by_id(results: List[Dict[str, Any]], metric: str = "overall") -> Dict[str, Dict[str, Any]]:
    """Index results by test_case_id and normalize score field."""
    by_id = {}
    for r in results:
        rid = r.get("test_case_id") or r.get("id") or r.get("test_case_id")
        if rid is None:
            continue
        score = get_score(r, metric)
        if score is not None:
            by_id[str(rid)] = {"score": float(score), "row": r}
    return by_id


def compare_results(
    baseline_path: str,
    new_path: str,
    metric: str = "overall",
    threshold_pct: float = 5.0,
    threshold_abs: Optional[float] = None
) -> Dict[str, Any]:
    """
    Compare baseline vs new results. Flag regressions where new score drops by more than threshold.
    threshold_pct: regression if (baseline - new) / baseline > threshold_pct/100 (when baseline > 0)
    threshold_abs: regression if baseline - new > threshold_abs
    """
    baseline_list = load_results(baseline_path)
    new_list = load_results(new_path)
    baseline_by_id = build_by_id(baseline_list, metric)
    new_by_id = build_by_id(new_list, metric)

    all_ids = set(baseline_by_id) | set(new_by_id)
    regressions: List[RegressionResult] = []
    improvements: List[RegressionResult] = []
    missing_baseline: List[str] = []
    missing_new: List[str] = []

    for tid in all_ids:
        b = baseline_by_id.get(tid)
        n = new_by_id.get(tid)
        if not b:
            missing_baseline.append(tid)
            continue
        if not n:
            missing_new.append(tid)
            continue
        base_score = b["score"]
        new_score = n["score"]
        delta = new_score - base_score
        delta_pct = (delta / base_score * 100) if base_score else 0.0

        is_regression = False
        if threshold_abs is not None:
            is_regression = delta < -threshold_abs
        else:
            is_regression = delta_pct < -threshold_pct

        r = RegressionResult(
            test_case_id=tid,
            baseline_score=base_score,
            new_score=new_score,
            delta=delta,
            delta_pct=delta_pct,
            is_regression=is_regression,
            metric_name=metric
        )
        if is_regression:
            regressions.append(r)
        elif delta > 0:
            improvements.append(r)

    baseline_avg = sum(b["score"] for b in baseline_by_id.values()) / len(baseline_by_id) if baseline_by_id else 0
    new_avg = sum(n["score"] for n in new_by_id.values()) / len(new_by_id) if new_by_id else 0
    overall_delta_pct = ((new_avg - baseline_avg) / baseline_avg * 100) if baseline_avg else 0

    return {
        "summary": {
            "baseline_path": baseline_path,
            "new_path": new_path,
            "metric": metric,
            "baseline_cases": len(baseline_by_id),
            "new_cases": len(new_by_id),
            "baseline_avg_score": round(baseline_avg, 4),
            "new_avg_score": round(new_avg, 4),
            "overall_delta_pct": round(overall_delta_pct, 2),
            "regression_count": len(regressions),
            "improvement_count": len(improvements),
            "missing_in_baseline": len(missing_baseline),
            "missing_in_new": len(missing_new),
        },
        "regressions": [asdict(r) for r in regressions],
        "improvements": [asdict(r) for r in improvements],
        "missing_baseline_ids": missing_baseline,
        "missing_new_ids": missing_new,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Compare eval results to baseline and flag regressions"
    )
    parser.add_argument("--baseline", "-b", required=True, help="Path to baseline results JSON")
    parser.add_argument("--new", "-n", required=True, help="Path to new results JSON")
    parser.add_argument("--metric", "-m", default="overall", help="Score key to compare (e.g. overall, accuracy)")
    parser.add_argument("--threshold", "-t", type=float, default=5.0,
                       help="Regression if score drops by this many percent (default 5)")
    parser.add_argument("--threshold-abs", type=float, default=None,
                       help="Alternatively: regression if score drops by this much in absolute terms")
    parser.add_argument("--output", "-o", help="Write comparison JSON here")
    parser.add_argument("--fail-on-regression", action="store_true",
                       help="Exit with code 1 if any regression found")
    args = parser.parse_args()

    if not Path(args.baseline).exists():
        print(f"Baseline file not found: {args.baseline}", file=sys.stderr)
        sys.exit(2)
    if not Path(args.new).exists():
        print(f"New results file not found: {args.new}", file=sys.stderr)
        sys.exit(2)

    result = compare_results(
        args.baseline,
        args.new,
        metric=args.metric,
        threshold_pct=args.threshold,
        threshold_abs=args.threshold_abs
    )

    if args.output:
        with open(args.output, "w") as f:
            json.dump(result, f, indent=2)
        print(f"Wrote comparison to {args.output}")

    summary = result["summary"]
    print("\n" + "=" * 55)
    print("REGRESSION CHECK")
    print("=" * 55)
    print(f"  Baseline avg ({summary['metric']}): {summary['baseline_avg_score']}")
    print(f"  New avg ({summary['metric']}):      {summary['new_avg_score']}")
    print(f"  Overall delta:                      {summary['overall_delta_pct']}%")
    print(f"  Regressions:                       {summary['regression_count']}")
    print(f"  Improvements:                      {summary['improvement_count']}")
    if summary["regression_count"]:
        print("\n  Regressions (first 10):")
        for r in result["regressions"][:10]:
            print(f"    - {r['test_case_id']}: {r['baseline_score']} -> {r['new_score']} ({r['delta_pct']:.1f}%)")
    print("=" * 55 + "\n")

    if args.fail_on_regression and summary["regression_count"] > 0:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()