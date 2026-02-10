#!/usr/bin/env python3
"""
Churn Risk Calculator

Score user cohorts by churn risk using usage drop-off, feature adoption, and
support ticket frequency. Produces a weighted risk score (0–100) for each cohort
so PMs can prioritize retention efforts.

AI products often see high early churn when the "magic" doesn't land; this
calculator helps quantify that risk by cohort.

Usage:
    python churn-risk-calculator.py --cohort "New Users" --usage-drop 40 --adoption 25 --tickets 12
    python churn-risk-calculator.py --csv cohort_data.csv
    python churn-risk-calculator.py --cohort "Power" --usage-drop 5 --adoption 80 --tickets 1 --cohort "Casual" --usage-drop 35 --adoption 30 --tickets 8

CSV format (header row required):
    cohort,usage_drop_pct,feature_adoption_pct,tickets_per_100_users

Requirements:
    None (stdlib only). Optional: pandas for CSV mode.
"""

import argparse
import csv
import sys
from dataclasses import dataclass
from typing import List, Optional, Tuple


# Default weights for composite risk score (sum to 1.0)
DEFAULT_WEIGHTS = {
    "usage_drop": 0.45,
    "adoption": 0.30,
    "tickets": 0.25,
}

# Thresholds for risk labels
RISK_THRESHOLDS = [
    (70, "CRITICAL"),
    (50, "HIGH"),
    (30, "MEDIUM"),
    (0, "LOW"),
]


@dataclass
class CohortMetrics:
    """Metrics for a single user cohort."""
    name: str
    usage_drop_pct: float        # % decrease in usage (e.g. 40 = 40% drop)
    feature_adoption_pct: float  # % of users who adopted key feature(s)
    tickets_per_100_users: float # support tickets per 100 users in period


@dataclass
class CohortRisk:
    """Risk assessment for a cohort."""
    cohort: CohortMetrics
    usage_score: float       # 0–100 risk from usage drop
    adoption_score: float    # 0–100 risk from low adoption
    ticket_score: float      # 0–100 risk from ticket volume
    composite_score: float   # weighted 0–100
    label: str               # LOW / MEDIUM / HIGH / CRITICAL


def clamp(value: float, lo: float = 0.0, hi: float = 100.0) -> float:
    """Clamp value to [lo, hi]."""
    return max(lo, min(hi, value))


def usage_drop_risk(drop_pct: float) -> float:
    """
    Convert usage drop % to risk score (0–100).
    0% drop -> 0 risk; 50%+ drop -> 100 risk. Linear.
    """
    return clamp(drop_pct * 2.0)


def adoption_risk(adoption_pct: float) -> float:
    """
    Convert feature adoption % to risk score (0–100).
    100% adoption -> 0 risk; 0% adoption -> 100 risk. Inverse linear.
    """
    return clamp(100.0 - adoption_pct)


def ticket_risk(tickets_per_100: float) -> float:
    """
    Convert support ticket rate to risk score (0–100).
    0 tickets -> 0 risk; 20+ tickets per 100 users -> 100 risk. Linear.
    """
    return clamp(tickets_per_100 * 5.0)


def risk_label(score: float) -> str:
    """Return human-readable risk label for a composite score."""
    for threshold, label in RISK_THRESHOLDS:
        if score >= threshold:
            return label
    return "LOW"


def assess_cohort(
    cohort: CohortMetrics,
    weights: Optional[dict] = None,
) -> CohortRisk:
    """Compute risk scores for a cohort."""
    w = weights or DEFAULT_WEIGHTS
    u = usage_drop_risk(cohort.usage_drop_pct)
    a = adoption_risk(cohort.feature_adoption_pct)
    t = ticket_risk(cohort.tickets_per_100_users)
    composite = (w["usage_drop"] * u + w["adoption"] * a + w["tickets"] * t)
    composite = clamp(composite)
    return CohortRisk(
        cohort=cohort,
        usage_score=round(u, 1),
        adoption_score=round(a, 1),
        ticket_score=round(t, 1),
        composite_score=round(composite, 1),
        label=risk_label(composite),
    )


def load_csv(path: str) -> List[CohortMetrics]:
    """Load cohort data from CSV file."""
    cohorts: List[CohortMetrics] = []
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            cohorts.append(CohortMetrics(
                name=row["cohort"].strip(),
                usage_drop_pct=float(row["usage_drop_pct"]),
                feature_adoption_pct=float(row["feature_adoption_pct"]),
                tickets_per_100_users=float(row["tickets_per_100_users"]),
            ))
    return cohorts


def print_report(results: List[CohortRisk]) -> None:
    """Pretty-print risk assessment."""
    print("\n" + "=" * 70)
    print("📊 CHURN RISK ASSESSMENT")
    print("=" * 70)

    # Sort by composite score descending (highest risk first)
    results = sorted(results, key=lambda r: r.composite_score, reverse=True)

    for r in results:
        c = r.cohort
        label_icon = {
            "CRITICAL": "🔴",
            "HIGH": "🟠",
            "MEDIUM": "🟡",
            "LOW": "🟢",
        }.get(r.label, "⚪")

        print(f"\n{label_icon} {c.name}  —  {r.label} RISK ({r.composite_score}/100)")
        print(f"   ├─ Usage drop:        {c.usage_drop_pct:.1f}%  → risk {r.usage_score}/100")
        print(f"   ├─ Feature adoption:  {c.feature_adoption_pct:.1f}%  → risk {r.adoption_score}/100")
        print(f"   └─ Tickets/100 users: {c.tickets_per_100_users:.1f}  → risk {r.ticket_score}/100")

    # Summary
    print("\n" + "-" * 70)
    print("📋 SUMMARY:")
    for label_name in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]:
        count = sum(1 for r in results if r.label == label_name)
        if count > 0:
            print(f"   • {label_name}: {count} cohort(s)")

    avg = sum(r.composite_score for r in results) / len(results) if results else 0
    print(f"\n   Average risk score: {avg:.1f}/100")
    print("\n📐 WEIGHTS: usage_drop={w[usage_drop]:.0%}, adoption={w[adoption]:.0%}, tickets={w[tickets]:.0%}".format(
        w=DEFAULT_WEIGHTS
    ))
    print("=" * 70)


def main():
    parser = argparse.ArgumentParser(
        description="Score cohorts by churn risk using usage, adoption, and support metrics."
    )
    parser.add_argument(
        "--csv",
        type=str,
        help="CSV file with columns: cohort, usage_drop_pct, feature_adoption_pct, tickets_per_100_users",
    )
    parser.add_argument(
        "--cohort",
        type=str,
        action="append",
        help="Cohort name (repeat --cohort ... --usage-drop ... for multiple cohorts)",
    )
    parser.add_argument(
        "--usage-drop",
        type=float,
        action="append",
        help="Usage drop %% for cohort (e.g. 40 = 40%% decline)",
    )
    parser.add_argument(
        "--adoption",
        type=float,
        action="append",
        help="Feature adoption %% for cohort",
    )
    parser.add_argument(
        "--tickets",
        type=float,
        action="append",
        help="Support tickets per 100 users for cohort",
    )
    parser.add_argument(
        "--weight-usage",
        type=float,
        default=DEFAULT_WEIGHTS["usage_drop"],
        help=f"Weight for usage drop risk (default: {DEFAULT_WEIGHTS['usage_drop']})",
    )
    parser.add_argument(
        "--weight-adoption",
        type=float,
        default=DEFAULT_WEIGHTS["adoption"],
        help=f"Weight for adoption risk (default: {DEFAULT_WEIGHTS['adoption']})",
    )
    parser.add_argument(
        "--weight-tickets",
        type=float,
        default=DEFAULT_WEIGHTS["tickets"],
        help=f"Weight for ticket risk (default: {DEFAULT_WEIGHTS['tickets']})",
    )
    args = parser.parse_args()

    weights = {
        "usage_drop": args.weight_usage,
        "adoption": args.weight_adoption,
        "tickets": args.weight_tickets,
    }
    # Normalize weights
    total_w = sum(weights.values())
    if total_w > 0:
        weights = {k: v / total_w for k, v in weights.items()}

    cohorts: List[CohortMetrics] = []

    if args.csv:
        try:
            cohorts = load_csv(args.csv)
        except Exception as e:
            print(f"Error reading CSV: {e}", file=sys.stderr)
            return 1
    elif args.cohort:
        drops = args.usage_drop or []
        adoptions = args.adoption or []
        tickets = args.tickets or []
        for i, name in enumerate(args.cohort):
            cohorts.append(CohortMetrics(
                name=name,
                usage_drop_pct=drops[i] if i < len(drops) else 0.0,
                feature_adoption_pct=adoptions[i] if i < len(adoptions) else 0.0,
                tickets_per_100_users=tickets[i] if i < len(tickets) else 0.0,
            ))
    else:
        parser.print_help()
        print("\nExample: --cohort 'New Users' --usage-drop 40 --adoption 25 --tickets 12", file=sys.stderr)
        return 0

    if not cohorts:
        print("Error: no cohort data provided.", file=sys.stderr)
        return 1

    results = [assess_cohort(c, weights) for c in cohorts]
    print_report(results)
    return 0


if __name__ == "__main__":
    sys.exit(main())
