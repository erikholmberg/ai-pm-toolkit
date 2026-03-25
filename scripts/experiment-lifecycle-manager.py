#!/usr/bin/env python3
"""
Experiment Lifecycle Manager

Registers experiment hypotheses, tracks guardrails, and recommends ship/iterate/stop.
"""

import argparse
import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, List


@dataclass
class Guardrail:
    metric: str
    direction: str  # "max" or "min"
    threshold: float
    observed: float

    def passed(self) -> bool:
        if self.direction == "max":
            return self.observed <= self.threshold
        return self.observed >= self.threshold


@dataclass
class ExperimentDecision:
    experiment_id: str
    hypothesis: str
    primary_metric: str
    baseline: float
    variant: float
    minimum_lift_pct: float
    observed_lift_pct: float
    significance_p_value: float
    guardrails: List[Dict[str, Any]]
    decision: str
    rationale: List[str]


def parse_guardrail(raw: str) -> Guardrail:
    # format: metric:direction:threshold:observed
    parts = raw.split(":")
    if len(parts) != 4:
        raise ValueError(f"Invalid guardrail format: {raw}")
    metric, direction, threshold, observed = parts
    if direction not in {"max", "min"}:
        raise ValueError(f"Guardrail direction must be max|min: {raw}")
    return Guardrail(metric=metric, direction=direction, threshold=float(threshold), observed=float(observed))


def decide(
    experiment_id: str,
    hypothesis: str,
    primary_metric: str,
    baseline: float,
    variant: float,
    minimum_lift_pct: float,
    significance_p_value: float,
    alpha: float,
    guardrails: List[Guardrail],
) -> ExperimentDecision:
    observed_lift_pct = ((variant - baseline) / baseline) * 100 if baseline else 0.0
    rationale: List[str] = []
    all_guardrails_pass = all(g.passed() for g in guardrails)

    if significance_p_value > alpha:
        rationale.append(
            f"Primary metric is not statistically significant (p={significance_p_value:.4f} > {alpha:.4f})."
        )
    else:
        rationale.append(f"Primary metric is statistically significant (p={significance_p_value:.4f}).")

    if observed_lift_pct < minimum_lift_pct:
        rationale.append(
            f"Observed lift {observed_lift_pct:.2f}% is below minimum actionable lift {minimum_lift_pct:.2f}%."
        )
    else:
        rationale.append(
            f"Observed lift {observed_lift_pct:.2f}% meets/exceeds minimum actionable lift {minimum_lift_pct:.2f}%."
        )

    if all_guardrails_pass:
        rationale.append("All guardrail metrics passed.")
    else:
        failed = [g.metric for g in guardrails if not g.passed()]
        rationale.append(f"Guardrail failures detected: {', '.join(failed)}.")

    if significance_p_value <= alpha and observed_lift_pct >= minimum_lift_pct and all_guardrails_pass:
        decision = "ship"
    elif not all_guardrails_pass:
        decision = "stop"
    else:
        decision = "iterate"

    return ExperimentDecision(
        experiment_id=experiment_id,
        hypothesis=hypothesis,
        primary_metric=primary_metric,
        baseline=baseline,
        variant=variant,
        minimum_lift_pct=minimum_lift_pct,
        observed_lift_pct=observed_lift_pct,
        significance_p_value=significance_p_value,
        guardrails=[
            {
                "metric": g.metric,
                "direction": g.direction,
                "threshold": g.threshold,
                "observed": g.observed,
                "passed": g.passed(),
            }
            for g in guardrails
        ],
        decision=decision,
        rationale=rationale,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Manage experiment decision lifecycle.")
    parser.add_argument("--experiment-id", required=True, help="Experiment artifact ID")
    parser.add_argument("--hypothesis", required=True, help="Hypothesis statement")
    parser.add_argument("--primary-metric", required=True, help="Primary metric name")
    parser.add_argument("--baseline", type=float, required=True, help="Baseline metric value")
    parser.add_argument("--variant", type=float, required=True, help="Variant metric value")
    parser.add_argument("--minimum-lift-pct", type=float, default=2.0, help="Minimum actionable lift")
    parser.add_argument("--p-value", type=float, required=True, help="Observed p-value")
    parser.add_argument("--alpha", type=float, default=0.05, help="Significance threshold")
    parser.add_argument(
        "--guardrail",
        action="append",
        default=[],
        help="Guardrail as metric:direction:threshold:observed (repeatable)",
    )
    parser.add_argument("--output", help="Write decision memo JSON")
    args = parser.parse_args()

    guardrails = [parse_guardrail(raw) for raw in args.guardrail]
    decision = decide(
        experiment_id=args.experiment_id,
        hypothesis=args.hypothesis,
        primary_metric=args.primary_metric,
        baseline=args.baseline,
        variant=args.variant,
        minimum_lift_pct=args.minimum_lift_pct,
        significance_p_value=args.p_value,
        alpha=args.alpha,
        guardrails=guardrails,
    )

    print("\n=== Experiment Lifecycle Decision ===")
    print(f"Experiment: {decision.experiment_id}")
    print(f"Decision:   {decision.decision.upper()}")
    print(f"Lift:       {decision.observed_lift_pct:.2f}%")
    print("Rationale:")
    for line in decision.rationale:
        print(f"- {line}")

    payload = asdict(decision)
    if args.output:
        Path(args.output).write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print(f"\nSaved decision memo: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
