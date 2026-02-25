#!/usr/bin/env python3
"""
Retention Curve Analyzer

Build Day-N retention curves from cohort data, fit decay models, compare
cohorts, and identify where users drop off. The standard growth PM tool
for understanding user stickiness and product-market fit.

Supports:
    - Day-N retention curves (D1, D7, D14, D30, D60, D90)
    - Multiple cohort comparison
    - Decay model fitting (exponential, power-law)
    - Projected long-term retention
    - Benchmarking against industry standards
    - Cohort-over-cohort trend analysis

Usage:
    # Single cohort inline
    python retention-curve-analyzer.py \\
        --cohort "Jan 2025:10000:6500:4200:3100:2400:1800:1500"

    Format: "Label:D0:D1:D7:D14:D30:D60:D90"

    # Multiple cohorts
    python retention-curve-analyzer.py \\
        --cohort "Jan:10000:6500:4200:3100:2400:1800:1500" \\
        --cohort "Feb:12000:8400:5500:4100:3200:2500:2000" \\
        --cohort "Mar:11000:7700:5100:3900:3000:2300:1900"

    # From CSV
    python retention-curve-analyzer.py --csv retention.csv

    # With benchmarking
    python retention-curve-analyzer.py --csv retention.csv --benchmark saas

    # Custom retention days
    python retention-curve-analyzer.py \\
        --cohort "Q1:5000:3500:2800:2200:1800" \\
        --days "0,1,7,30,90"

CSV format:
    cohort,d0,d1,d7,d14,d30,d60,d90
    Jan 2025,10000,6500,4200,3100,2400,1800,1500
    Feb 2025,12000,8400,5500,4100,3200,2500,2000

    Or with custom day columns:
    cohort,day_0,day_1,day_7,day_14,day_30
    Jan 2025,10000,6500,4200,3100,2400

Requirements:
    None (stdlib only).
"""

import argparse
import csv
import json
import math
import sys
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Retention analysis
# ---------------------------------------------------------------------------

DEFAULT_DAYS = [0, 1, 7, 14, 30, 60, 90]

BENCHMARKS = {
    "saas": {
        "label": "SaaS (B2B)",
        "d1": 80, "d7": 60, "d14": 50, "d30": 40, "d60": 35, "d90": 30,
        "good_d30": 40, "great_d30": 50,
    },
    "consumer": {
        "label": "Consumer App",
        "d1": 40, "d7": 20, "d14": 15, "d30": 10, "d60": 7, "d90": 5,
        "good_d30": 15, "great_d30": 25,
    },
    "mobile": {
        "label": "Mobile App",
        "d1": 35, "d7": 15, "d14": 10, "d30": 7, "d60": 5, "d90": 3,
        "good_d30": 10, "great_d30": 20,
    },
    "ecommerce": {
        "label": "E-commerce",
        "d1": 30, "d7": 18, "d14": 14, "d30": 10, "d60": 8, "d90": 6,
        "good_d30": 12, "great_d30": 20,
    },
    "gaming": {
        "label": "Gaming",
        "d1": 35, "d7": 15, "d14": 8, "d30": 5, "d60": 3, "d90": 2,
        "good_d30": 8, "great_d30": 15,
    },
}


def analyze_cohort(
    label: str,
    counts: List[int],
    days: List[int],
) -> Dict[str, Any]:
    """Analyze retention for a single cohort."""
    if len(counts) != len(days):
        raise ValueError(f"Cohort '{label}': {len(counts)} values but {len(days)} day labels")

    d0 = counts[0]
    if d0 == 0:
        return {"label": label, "error": "D0 is zero"}

    retention_pcts = [round(c / d0 * 100, 1) for c in counts]

    # Key retention metrics
    metrics: Dict[str, Any] = {
        "label": label,
        "cohort_size": d0,
        "days": days,
        "counts": counts,
        "retention_pcts": retention_pcts,
    }

    # Map standard day names
    day_map = dict(zip(days, retention_pcts))
    for d in [1, 7, 14, 30, 60, 90]:
        key = f"d{d}"
        metrics[key] = day_map.get(d)

    # Drop-off analysis
    dropoffs = []
    for i in range(1, len(counts)):
        lost = counts[i-1] - counts[i]
        lost_pct = lost / d0 * 100
        interval_churn = lost / counts[i-1] * 100 if counts[i-1] > 0 else 0
        dropoffs.append({
            "from_day": days[i-1],
            "to_day": days[i],
            "lost": lost,
            "lost_pct": round(lost_pct, 1),
            "interval_churn_pct": round(interval_churn, 1),
        })
    metrics["dropoffs"] = dropoffs

    # Find biggest drop-off
    if dropoffs:
        biggest = max(dropoffs, key=lambda x: x["lost_pct"])
        metrics["biggest_dropoff"] = biggest

    # Fit exponential decay: retention = a * exp(-k * day)
    decay_fit = _fit_exponential(days[1:], retention_pcts[1:])
    if decay_fit:
        metrics["decay_model"] = decay_fit
        # Project retention at D180, D365
        metrics["projected_d180"] = round(decay_fit["a"] * math.exp(-decay_fit["k"] * 180), 1)
        metrics["projected_d365"] = round(decay_fit["a"] * math.exp(-decay_fit["k"] * 365), 1)
        # Half-life
        if decay_fit["k"] > 0:
            metrics["half_life_days"] = round(math.log(2) / decay_fit["k"], 0)

    return metrics


def _fit_exponential(days: List[int], retention_pcts: List[float]) -> Optional[Dict[str, float]]:
    """Fit exponential decay y = a * exp(-k * x) using log-linear regression."""
    valid = [(d, r) for d, r in zip(days, retention_pcts) if r > 0 and d > 0]
    if len(valid) < 2:
        return None

    xs = [d for d, _ in valid]
    ys = [math.log(r) for _, r in valid]
    n = len(xs)

    sum_x = sum(xs)
    sum_y = sum(ys)
    sum_xy = sum(x * y for x, y in zip(xs, ys))
    sum_x2 = sum(x * x for x in xs)

    denom = n * sum_x2 - sum_x * sum_x
    if denom == 0:
        return None

    slope = (n * sum_xy - sum_x * sum_y) / denom
    intercept = (sum_y - slope * sum_x) / n

    a = math.exp(intercept)
    k = -slope

    # R-squared
    y_mean = sum_y / n
    ss_tot = sum((y - y_mean) ** 2 for y in ys)
    ss_res = sum((y - (intercept + slope * x)) ** 2 for x, y in zip(xs, ys))
    r_squared = 1 - ss_res / ss_tot if ss_tot > 0 else 0

    return {
        "a": round(a, 2),
        "k": round(k, 6),
        "r_squared": round(r_squared, 3),
        "equation": f"retention = {a:.1f} * exp(-{k:.5f} * day)",
    }


def compare_cohorts(cohorts: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Compare retention across cohorts."""
    if len(cohorts) < 2:
        return {"comparison": "insufficient_data"}

    # Trend for each standard day
    trends: Dict[str, Any] = {}
    for d_key in ["d1", "d7", "d14", "d30", "d60", "d90"]:
        vals = [(c["label"], c.get(d_key)) for c in cohorts if c.get(d_key) is not None]
        if len(vals) >= 2:
            first_val = vals[0][1]
            last_val = vals[-1][1]
            delta = last_val - first_val
            direction = "improving" if delta > 1 else "declining" if delta < -1 else "stable"
            trends[d_key] = {
                "first": first_val,
                "last": last_val,
                "delta": round(delta, 1),
                "direction": direction,
            }

    # Best and worst cohorts (by D30 if available, else last day)
    scored = []
    for c in cohorts:
        score = c.get("d30") or c.get("d14") or c.get("d7") or c["retention_pcts"][-1]
        scored.append((c["label"], score))

    scored.sort(key=lambda x: -x[1])
    best = scored[0] if scored else None
    worst = scored[-1] if scored else None

    return {
        "n_cohorts": len(cohorts),
        "trends": trends,
        "best_cohort": best,
        "worst_cohort": worst,
    }


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def parse_cohort_string(s: str, days: List[int]) -> Dict[str, Any]:
    """Parse 'Label:D0:D1:D7:...' into cohort analysis."""
    parts = s.split(":")
    if len(parts) < 3:
        raise ValueError(f"Invalid cohort '{s}'. Format: Label:D0:D1:D7:...")

    label = parts[0].strip()
    try:
        counts = [int(float(p.strip())) for p in parts[1:]]
    except ValueError as e:
        raise ValueError(f"Invalid numbers in cohort '{label}': {e}")

    if len(counts) != len(days):
        if len(counts) == len(DEFAULT_DAYS):
            days = DEFAULT_DAYS[:len(counts)]
        else:
            days = list(range(len(counts)))

    return analyze_cohort(label, counts, days)


def _col(fieldnames: List[str], *aliases: str) -> Optional[str]:
    lower_map = {f.lower().strip(): f for f in fieldnames}
    for alias in aliases:
        if alias.lower().strip() in lower_map:
            return lower_map[alias.lower().strip()]
    return None


def load_csv(path: str) -> Tuple[List[Dict[str, Any]], List[int]]:
    """Load cohort data from CSV."""
    cohorts: List[Dict[str, Any]] = []
    days: List[int] = []

    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fields = reader.fieldnames or []

        c_label = _col(fields, "cohort", "name", "month", "period")
        label_col = c_label or fields[0]

        # Detect day columns
        day_cols = []
        for f_name in fields:
            if f_name == label_col:
                continue
            fl = f_name.lower().strip()
            if fl.startswith("d") and fl[1:].isdigit():
                day_cols.append((int(fl[1:]), f_name))
            elif fl.startswith("day_") and fl[4:].isdigit():
                day_cols.append((int(fl[4:]), f_name))
            elif fl.startswith("day") and fl[3:].isdigit():
                day_cols.append((int(fl[3:]), f_name))
            elif fl.isdigit():
                day_cols.append((int(fl), f_name))

        if not day_cols:
            # Assume remaining columns are sequential days
            remaining = [f_name for f_name in fields if f_name != label_col]
            for i, f_name in enumerate(remaining):
                day_cols.append((DEFAULT_DAYS[i] if i < len(DEFAULT_DAYS) else i, f_name))

        day_cols.sort(key=lambda x: x[0])
        days = [d for d, _ in day_cols]

        for row in reader:
            label = row.get(label_col, "").strip()
            if not label:
                continue

            counts = []
            for _, col_name in day_cols:
                raw = row.get(col_name, "0").strip().replace(",", "")
                try:
                    counts.append(int(float(raw)))
                except ValueError:
                    counts.append(0)

            try:
                cohorts.append(analyze_cohort(label, counts, days))
            except ValueError:
                continue

    return cohorts, days


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def _bar(value: float, max_val: float, width: int = 25) -> str:
    if max_val <= 0:
        return "░" * width
    ratio = min(1.0, max(0.0, value / max_val))
    filled = int(ratio * width)
    return "█" * filled + "░" * (width - filled)


def _pct_bar(pct: float, width: int = 20) -> str:
    filled = int(pct / 100 * width)
    return "█" * filled + "░" * (width - filled)


def print_report(
    cohorts: List[Dict[str, Any]],
    comparison: Optional[Dict[str, Any]],
    benchmark_name: Optional[str],
) -> None:
    """Pretty-print retention analysis."""
    print("\n" + "=" * 78)
    print("📉 RETENTION CURVE ANALYZER")
    print("=" * 78)

    benchmark = BENCHMARKS.get(benchmark_name) if benchmark_name else None

    for cohort in cohorts:
        if "error" in cohort:
            print(f"\n   ❌ {cohort['label']}: {cohort['error']}")
            continue

        print(f"\n{'─'*78}")
        print(f"\n📋 COHORT: {cohort['label']}  (n={cohort['cohort_size']:,})\n")

        # Retention table
        days = cohort["days"]
        pcts = cohort["retention_pcts"]
        counts = cohort["counts"]

        header = "   "
        for d in days:
            header += f"{'D'+str(d):>8}"
        print(header)

        row_pct = "   "
        for p in pcts:
            row_pct += f"{p:>7.1f}%"
        print(row_pct)

        row_cnt = "   "
        for c in counts:
            if c >= 1000:
                row_cnt += f"{'(' + str(c//1000) + 'K)':>8}"
            else:
                row_cnt += f"{'(' + str(c) + ')':>8}"
        print(row_cnt)

        # Retention curve visual
        print(f"\n   📊 RETENTION CURVE:")
        for i, (d, p) in enumerate(zip(days, pcts)):
            bar = _pct_bar(p, 30)
            bm_str = ""
            if benchmark and d > 0:
                bm_key = f"d{d}"
                bm_val = benchmark.get(bm_key)
                if bm_val is not None:
                    delta = p - bm_val
                    bm_str = f"  (vs {benchmark['label']}: {delta:+.1f}pp)"
            print(f"   D{d:<4} {bar} {p:.1f}%{bm_str}")

        # Drop-off analysis
        print(f"\n   📉 DROP-OFF ANALYSIS:")
        if cohort["dropoffs"]:
            max_drop = max(d["lost_pct"] for d in cohort["dropoffs"])
            for drop in cohort["dropoffs"]:
                bar = _bar(drop["lost_pct"], max_drop, 15)
                marker = " ← biggest" if drop == cohort.get("biggest_dropoff") else ""
                print(
                    f"   D{drop['from_day']}→D{drop['to_day']:<4} "
                    f"{bar} -{drop['lost_pct']:.1f}pp "
                    f"({drop['interval_churn_pct']:.0f}% of remaining){marker}"
                )

        # Decay model
        if cohort.get("decay_model"):
            dm = cohort["decay_model"]
            print(f"\n   📐 DECAY MODEL (exponential fit):")
            print(f"   {dm['equation']}")
            print(f"   R² = {dm['r_squared']:.3f}  ", end="")
            if dm["r_squared"] >= 0.95:
                print("🟢 Excellent fit")
            elif dm["r_squared"] >= 0.85:
                print("🟡 Good fit")
            else:
                print("🟠 Moderate fit — consider power-law model")

            if cohort.get("half_life_days"):
                print(f"   Half-life: {cohort['half_life_days']:.0f} days")
            if cohort.get("projected_d180") is not None:
                print(f"   Projected D180: {cohort['projected_d180']:.1f}%")
            if cohort.get("projected_d365") is not None:
                print(f"   Projected D365: {cohort['projected_d365']:.1f}%")

        # Key metrics summary
        print(f"\n   📊 KEY METRICS:")
        d30 = cohort.get("d30")
        if d30 is not None:
            print(f"   D30 retention: {d30:.1f}%", end="")
            if benchmark:
                if d30 >= benchmark.get("great_d30", 999):
                    print(f"  🟢 Great (>{benchmark['great_d30']}% for {benchmark['label']})")
                elif d30 >= benchmark.get("good_d30", 999):
                    print(f"  🟢 Good (>{benchmark['good_d30']}% for {benchmark['label']})")
                else:
                    print(f"  🔴 Below benchmark ({benchmark['good_d30']}% for {benchmark['label']})")
            else:
                print()

    # Cohort comparison
    if comparison and comparison.get("n_cohorts", 0) >= 2:
        print(f"\n{'─'*78}")
        print(f"\n🔄 COHORT COMPARISON ({comparison['n_cohorts']} cohorts):\n")

        # Trend table
        if comparison["trends"]:
            print(f"   {'Day':<6} {'First':>8} {'Last':>8} {'Delta':>8} {'Trend'}")
            print(f"   {'─'*6} {'─'*8} {'─'*8} {'─'*8} {'─'*12}")

            for d_key, trend in comparison["trends"].items():
                icon = "📈" if trend["direction"] == "improving" else "📉" if trend["direction"] == "declining" else "➡️"
                print(
                    f"   {d_key.upper():<6} "
                    f"{trend['first']:>7.1f}% "
                    f"{trend['last']:>7.1f}% "
                    f"{trend['delta']:>+7.1f}pp "
                    f"{icon} {trend['direction']}"
                )

        if comparison["best_cohort"]:
            print(f"\n   🏆 Best cohort:  {comparison['best_cohort'][0]} ({comparison['best_cohort'][1]:.1f}%)")
        if comparison["worst_cohort"]:
            print(f"   📉 Worst cohort: {comparison['worst_cohort'][0]} ({comparison['worst_cohort'][1]:.1f}%)")

        # Multi-cohort overlay
        print(f"\n   D30 comparison:")
        d30_vals = [(c["label"], c.get("d30", 0)) for c in cohorts if c.get("d30") is not None]
        max_d30 = max(v for _, v in d30_vals) if d30_vals else 100
        for label, val in d30_vals:
            bar = _bar(val, max_d30, 25)
            print(f"   {label[:12]:<12} {bar} {val:.1f}%")

    # Benchmark comparison
    if benchmark:
        print(f"\n{'─'*78}")
        print(f"\n📏 BENCHMARK: {benchmark['label']}")
        print(f"\n   {'Day':<6} {'Benchmark':>10}")
        print(f"   {'─'*6} {'─'*10}")
        for d in [1, 7, 14, 30, 60, 90]:
            key = f"d{d}"
            val = benchmark.get(key)
            if val is not None:
                print(f"   D{d:<5} {val:>9.0f}%")

    # Guidance
    print(f"\n{'─'*78}")
    print(f"\n💡 RETENTION INSIGHTS:")
    print(f"   • D1 retention reflects first-session experience — optimize onboarding")
    print(f"   • D7 retention signals habit formation — focus on activation loops")
    print(f"   • D30 retention is the benchmark for product-market fit")
    print(f"   • Flattening curve = healthy retention; steep decay = leaky bucket")
    print(f"   • Compare cohorts to measure impact of product changes")
    print(f"   • Half-life >30 days is healthy for most SaaS products")
    print("\n" + "=" * 78)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Build Day-N retention curves, fit decay models, and compare cohorts. "
                    "The standard growth PM tool for measuring user stickiness.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --cohort "Jan:10000:6500:4200:3100:2400:1800:1500"
  %(prog)s --cohort "Jan:10000:6500:4200:3100:2400" --cohort "Feb:12000:8400:5500:4100:3200"
  %(prog)s --csv retention.csv --benchmark saas
  %(prog)s --cohort "Q1:5000:3500:2800:2200:1800" --days "0,1,7,30,90"
        """,
    )

    parser.add_argument("--cohort", type=str, action="append",
                        help="Cohort: 'Label:D0:D1:D7:D14:D30:D60:D90'")
    parser.add_argument("--days", type=str, default=None,
                        help="Custom day labels: '0,1,7,14,30,60,90'")
    parser.add_argument("--csv", "-c", type=str, help="CSV file with cohort data")
    parser.add_argument("--benchmark", "-b", type=str,
                        choices=list(BENCHMARKS.keys()),
                        help="Benchmark category for comparison")
    parser.add_argument("--output", "-o", type=str, help="Write JSON results to file")
    args = parser.parse_args()

    days = DEFAULT_DAYS
    if args.days:
        try:
            days = [int(d.strip()) for d in args.days.split(",")]
        except ValueError:
            print("Error: --days must be comma-separated integers", file=sys.stderr)
            return 1

    cohorts: List[Dict[str, Any]] = []

    if args.csv:
        try:
            cohorts, csv_days = load_csv(args.csv)
            if csv_days:
                days = csv_days
        except Exception as e:
            print(f"Error loading CSV: {e}", file=sys.stderr)
            return 1

    if args.cohort:
        for c_str in args.cohort:
            try:
                cohorts.append(parse_cohort_string(c_str, days))
            except ValueError as e:
                print(f"Error: {e}", file=sys.stderr)
                return 1

    if not cohorts:
        print("Error: provide cohort data via --cohort or --csv.", file=sys.stderr)
        parser.print_help(sys.stderr)
        return 1

    # Compare
    comparison = compare_cohorts(cohorts) if len(cohorts) >= 2 else None

    # Report
    print_report(cohorts, comparison, args.benchmark)

    # JSON output
    if args.output:
        report = {
            "cohorts": cohorts,
        }
        if comparison:
            report["comparison"] = comparison
        with open(args.output, "w") as f:
            json.dump(report, f, indent=2)
        print(f"\n📁 Results saved to {args.output}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
