#!/usr/bin/env python3
"""
Latency / SLO Calculator

Convert availability targets (e.g. 99.9% uptime) into error budgets: allowed
downtime per month and, with request volume, allowed failed requests. Optionally
summarize latency targets (p50/p99) for stakeholder reports.
Aligns with evals/metrics/ai-product-metrics.md (latency, availability, error rate).

Usage:
    python latency-slo-calculator.py --availability 99.9
    python latency-slo-calculator.py --availability 99.95 --requests-per-month 10e6
    python latency-slo-calculator.py --availability 99.9 --p50-ms 800 --p99-ms 2500
"""

import argparse
import math
import sys
from typing import Optional, Tuple


# Approximate days per month for downtime
DAYS_PER_MONTH = 30.44
MINUTES_PER_MONTH = DAYS_PER_MONTH * 24 * 60
SECONDS_PER_MONTH = MINUTES_PER_MONTH * 60


def availability_to_nines(availability_pct: float) -> float:
    """e.g. 99.9 -> 3.0 nines."""
    if availability_pct >= 100 or availability_pct <= 0:
        return 0.0
    # nines = -log10(1 - availability_pct/100)
    p = 1.0 - (availability_pct / 100.0)
    if p <= 0:
        return 10.0  # effectively 100%
    return -math.log10(p)


def downtime_per_month_minutes(availability_pct: float) -> float:
    """Allowed downtime in minutes per month for given availability."""
    if availability_pct >= 100:
        return 0.0
    if availability_pct <= 0:
        return MINUTES_PER_MONTH
    uptime_ratio = availability_pct / 100.0
    return (1.0 - uptime_ratio) * MINUTES_PER_MONTH


def allowed_failed_requests(
    requests_per_month: float,
    availability_pct: float,
) -> float:
    """Max failed requests per month to stay within availability (if each failure = 1 request)."""
    if requests_per_month <= 0:
        return 0.0
    if availability_pct >= 100:
        return 0.0
    fail_rate = 1.0 - (availability_pct / 100.0)
    return fail_rate * requests_per_month


def main():
    parser = argparse.ArgumentParser(
        description="SLO calculator: availability → error budget (downtime, allowed failures)."
    )
    parser.add_argument(
        "--availability",
        "-a",
        type=float,
        required=True,
        help="Target availability (e.g. 99.9 for 99.9%%)",
    )
    parser.add_argument(
        "--requests-per-month",
        "-r",
        type=float,
        help="Total requests per month (for allowed failed-request budget)",
    )
    parser.add_argument(
        "--p50-ms",
        type=float,
        help="Target p50 latency in ms (for report only)",
    )
    parser.add_argument(
        "--p99-ms",
        type=float,
        help="Target p99 latency in ms (for report only)",
    )
    parser.add_argument(
        "--month-days",
        type=float,
        default=DAYS_PER_MONTH,
        help=f"Days per month for downtime calc (default: {DAYS_PER_MONTH})",
    )
    args = parser.parse_args()

    if not 0 < args.availability <= 100:
        print("Error: --availability must be in (0, 100]", file=sys.stderr)
        return 1

    nines = availability_to_nines(args.availability)
    downtime_min = downtime_per_month_minutes(args.availability)
    downtime_sec = downtime_min * 60

    print("\n" + "=" * 60)
    print("📊 LATENCY / SLO CALCULATOR")
    print("=" * 60)
    print("\n📋 AVAILABILITY TARGET:")
    print(f"   • Availability:     {args.availability}%")
    print(f"   • Nines:            {nines:.2f} nines")

    print("\n⏱️  ERROR BUDGET (downtime per month):")
    print(f"   • Downtime:         {downtime_min:.1f} minutes")
    print(f"   •                   {downtime_sec:.0f} seconds")
    if downtime_min >= 60:
        print(f"   •                   {downtime_min / 60:.1f} hours")

    if args.requests_per_month is not None and args.requests_per_month > 0:
        allowed_failures = allowed_failed_requests(args.requests_per_month, args.availability)
        fail_rate_pct = 100.0 - args.availability
        print("\n📉 REQUEST BUDGET:")
        print(f"   • Requests/month:  {args.requests_per_month:,.0f}")
        print(f"   • Allowed failures: {allowed_failures:,.0f} ({fail_rate_pct}% of requests)")
        print(f"   • Effective max error rate: {fail_rate_pct}%")

    if args.p50_ms is not None or args.p99_ms is not None:
        print("\n📈 LATENCY TARGETS (reference):")
        if args.p50_ms is not None:
            print(f"   • p50: {args.p50_ms:.0f} ms")
        if args.p99_ms is not None:
            print(f"   • p99: {args.p99_ms:.0f} ms")
        print("   (Typical interactive targets: p50 <1s, p99 <3s)")

    print("\n" + "=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
