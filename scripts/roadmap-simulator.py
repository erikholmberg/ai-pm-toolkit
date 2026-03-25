#!/usr/bin/env python3
"""
Roadmap Simulator

Runs simple scenario simulations under capacity and dependency risk.
"""

import argparse
import csv
import json
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List


@dataclass
class Initiative:
    id: str
    effort_points: float
    impact_score: float
    dependency_risk: float  # 0..1


def load_initiatives(path: str) -> List[Initiative]:
    rows: List[Initiative] = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(
                Initiative(
                    id=(row.get("id") or "").strip(),
                    effort_points=float(row.get("effort_points") or 0),
                    impact_score=float(row.get("impact_score") or 0),
                    dependency_risk=float(row.get("dependency_risk") or 0),
                )
            )
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description="Simulate roadmap outcomes by scenario.")
    parser.add_argument("--csv", required=True, help="Roadmap initiatives CSV")
    parser.add_argument("--capacity-points", type=float, required=True, help="Available delivery capacity")
    parser.add_argument("--iterations", type=int, default=500, help="Simulation runs")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--output", help="Write JSON simulation report")
    args = parser.parse_args()

    random.seed(args.seed)
    initiatives = load_initiatives(args.csv)

    success_counts: Dict[str, int] = {item.id: 0 for item in initiatives}
    portfolio_value_samples: List[float] = []

    for _ in range(args.iterations):
        remaining_capacity = args.capacity_points
        shipped: List[Initiative] = []
        ordered = sorted(initiatives, key=lambda x: (x.impact_score / max(1, x.effort_points)), reverse=True)

        for item in ordered:
            if item.effort_points > remaining_capacity:
                continue
            # Dependency risk reduces probability of successful shipment.
            if random.random() > item.dependency_risk:
                shipped.append(item)
                remaining_capacity -= item.effort_points
                success_counts[item.id] += 1

        portfolio_value_samples.append(sum(x.impact_score for x in shipped))

    probabilities = [
        {"id": k, "ship_probability_pct": round((v / args.iterations) * 100, 2)}
        for k, v in success_counts.items()
    ]
    probabilities.sort(key=lambda x: x["ship_probability_pct"], reverse=True)

    avg_value = sum(portfolio_value_samples) / max(1, len(portfolio_value_samples))
    p90_value = sorted(portfolio_value_samples)[int(0.9 * (len(portfolio_value_samples) - 1))]

    report = {
        "iterations": args.iterations,
        "capacity_points": args.capacity_points,
        "avg_portfolio_impact": round(avg_value, 2),
        "p90_portfolio_impact": round(p90_value, 2),
        "initiative_ship_probabilities": probabilities,
    }

    print("\n=== Roadmap Scenario Simulation ===")
    print(f"Iterations:             {args.iterations}")
    print(f"Average portfolio value {report['avg_portfolio_impact']}")
    print(f"P90 portfolio value:    {report['p90_portfolio_impact']}")
    print("Top probable initiatives:")
    for item in probabilities[:5]:
        print(f"- {item['id']}: {item['ship_probability_pct']}%")

    if args.output:
        Path(args.output).write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"\nSaved simulation report: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
