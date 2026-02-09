#!/usr/bin/env python3
"""
NPS / CSAT Summary Calculator

Compute Net Promoter Score from promoter/detractor counts and CSAT average and
distribution from scores. Fits customer insights and feedback reporting.

NPS: Promoters (9–10) - Detractors (0–6); Passives (7–8) not in numerator.
CSAT: Typically 1–5 scale; report mean, distribution, and % satisfied (e.g. 4+).

Usage:
    python nps-csat-summary.py nps --promoters 40 --passives 30 --detractors 30
    python nps-csat-summary.py csat --scores 5 4 5 3 4 5 4 4 5 3
    python nps-csat-summary.py csat --counts "1:2 2:5 3:10 4:25 5:58" --satisfied-threshold 4

Requirements:
    None (stdlib only).
"""

import argparse
import sys
from typing import Dict, List, Optional


def nps_from_counts(promoters: int, passives: int, detractors: int) -> Optional[float]:
    """
    NPS = 100 * (promoters - detractors) / total.
    Returns None if total is 0.
    """
    total = promoters + passives + detractors
    if total == 0:
        return None
    return 100.0 * (promoters - detractors) / total


def nps_from_scores(scores: List[int]) -> Optional[float]:
    """NPS from a list of 0–10 scores. 9–10 promoter, 7–8 passive, 0–6 detractor."""
    if not scores:
        return None
    promoters = sum(1 for s in scores if s >= 9)
    passives = sum(1 for s in scores if 7 <= s <= 8)
    detractors = sum(1 for s in scores if s <= 6)
    return nps_from_counts(promoters, passives, detractors)


def csat_summary(
    scores: List[float],
    scale_high: float = 5.0,
    satisfied_threshold: Optional[float] = None,
) -> dict:
    """
    CSAT summary: count, mean, distribution (buckets), % at or above threshold.
    If satisfied_threshold is None, use scale_high - 1 (e.g. 4 for 1–5 scale).
    """
    if not scores:
        return {
            "n": 0,
            "mean": 0.0,
            "distribution": {},
            "pct_satisfied": None,
        }
    n = len(scores)
    mean = sum(scores) / n
    dist: Dict[int, int] = {}
    for s in scores:
        k = int(round(s))
        dist[k] = dist.get(k, 0) + 1
    threshold = satisfied_threshold if satisfied_threshold is not None else (scale_high - 1)
    satisfied = sum(1 for s in scores if s >= threshold)
    pct_satisfied = 100.0 * satisfied / n if n else None
    return {
        "n": n,
        "mean": mean,
        "distribution": dict(sorted(dist.items())),
        "pct_satisfied": pct_satisfied,
        "threshold": threshold,
    }


def parse_count_pairs(s: str) -> List[float]:
    """Parse e.g. '1:2 2:5 3:10 4:25 5:58' into list of scores (repeated by count)."""
    out: List[float] = []
    for part in s.split():
        if ":" in part:
            score_str, count_str = part.split(":", 1)
            try:
                score = float(score_str.strip())
                count = int(count_str.strip())
                for _ in range(max(0, count)):
                    out.append(score)
            except ValueError:
                continue
    return out


def main():
    parser = argparse.ArgumentParser(
        description="NPS from counts or scores; CSAT mean and distribution."
    )
    sub = parser.add_subparsers(dest="command", required=True, help="nps | csat")

    # NPS
    nps_parser = sub.add_parser("nps", help="Net Promoter Score")
    nps_parser.add_argument("--promoters", "-P", type=int, default=0, help="Count 9–10")
    nps_parser.add_argument("--passives", type=int, default=0, help="Count 7–8")
    nps_parser.add_argument("--detractors", "-D", type=int, default=0, help="Count 0–6")
    nps_parser.add_argument(
        "--scores",
        type=int,
        nargs="*",
        help="Raw 0–10 scores (alternative to P/passives/D)",
    )

    # CSAT
    csat_parser = sub.add_parser("csat", help="CSAT summary")
    csat_parser.add_argument(
        "--scores",
        type=float,
        nargs="*",
        help="Raw scores (e.g. 1–5)",
    )
    csat_parser.add_argument(
        "--counts",
        type=str,
        help="Score:count pairs, e.g. '1:2 2:5 3:10 4:25 5:58'",
    )
    csat_parser.add_argument(
        "--satisfied-threshold",
        type=float,
        default=None,
        help="Score >= this counts as satisfied (default: 4 for 1–5 scale)",
    )
    csat_parser.add_argument(
        "--scale-high",
        type=float,
        default=5.0,
        help="High end of scale (default: 5)",
    )

    args = parser.parse_args()

    if args.command == "nps":
        if args.scores is not None and len(args.scores) > 0:
            nps = nps_from_scores(args.scores)
            total = len(args.scores)
            promoters = sum(1 for s in args.scores if s >= 9)
            passives = sum(1 for s in args.scores if 7 <= s <= 8)
            detractors = sum(1 for s in args.scores if s <= 6)
        else:
            total = args.promoters + args.passives + args.detractors
            nps = nps_from_counts(args.promoters, args.passives, args.detractors)
            promoters, passives, detractors = args.promoters, args.passives, args.detractors

        if total == 0:
            print("Error: no responses (provide --promoters/--passives/--detractors or --scores)", file=sys.stderr)
            return 1
        if nps is None:
            return 1

        print("\n" + "=" * 60)
        print("NPS SUMMARY")
        print("=" * 60)
        print(f"\n  Total responses:  {total:,}")
        print(f"  Promoters (9–10): {promoters:,}  ({100 * promoters / total:.1f}%)")
        print(f"  Passives (7–8):   {passives:,}  ({100 * passives / total:.1f}%)")
        print(f"  Detractors (0–6): {detractors:,}  ({100 * detractors / total:.1f}%)")
        print(f"\n  NPS:              {nps:+.1f}")
        print("=" * 60)
        return 0

    if args.command == "csat":
        scores: List[float] = []
        if args.scores is not None:
            scores = list(args.scores)
        if args.counts:
            scores.extend(parse_count_pairs(args.counts))
        if not scores:
            print("Error: provide --scores or --counts for CSAT", file=sys.stderr)
            return 1

        summary = csat_summary(scores, args.scale_high, args.satisfied_threshold)
        print("\n" + "=" * 60)
        print("CSAT SUMMARY")
        print("=" * 60)
        print(f"\n  Responses:   {summary['n']:,}")
        print(f"  Mean:        {summary['mean']:.2f}")
        print(f"  Distribution:")
        for score, count in summary["distribution"].items():
            pct = 100 * count / summary["n"]
            print(f"    {score}: {count:,} ({pct:.1f}%)")
        if summary["pct_satisfied"] is not None:
            print(f"\n  % satisfied (score >= {summary['threshold']}): {summary['pct_satisfied']:.1f}%")
        print("=" * 60)
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
