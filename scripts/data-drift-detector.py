#!/usr/bin/env python3
"""
Data Drift Detector

Compare input feature distributions between a baseline period and a current
period to detect silent model degradation. Reports KS test, Population
Stability Index (PSI), and basic summary statistics.

Critical for ML products where silent drift erodes quality without obvious errors.

Usage:
    python data-drift-detector.py --baseline baseline.csv --current current.csv
    python data-drift-detector.py --baseline baseline.csv --current current.csv --columns score,latency_ms
    python data-drift-detector.py --baseline baseline.csv --current current.csv --threshold 0.1

CSV format:
    Each CSV should have numeric columns with a header row. Both CSVs must
    share the column names being compared.

Requirements:
    numpy, scipy (for KS test and statistics).
"""

import argparse
import csv
import math
import sys
from typing import Dict, List, Optional, Tuple


def read_csv_columns(path: str, columns: Optional[List[str]] = None) -> Dict[str, List[float]]:
    """Read numeric columns from CSV. If columns is None, read all numeric columns."""
    data: Dict[str, List[float]] = {}
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            return data
        target_cols = columns if columns else list(reader.fieldnames)
        for col in target_cols:
            data[col] = []
        for row in reader:
            for col in target_cols:
                if col in row:
                    try:
                        data[col].append(float(row[col]))
                    except (ValueError, TypeError):
                        pass  # skip non-numeric
    # Remove columns with no data
    return {k: v for k, v in data.items() if v}


def compute_stats(values: List[float]) -> Dict[str, float]:
    """Basic summary stats without numpy."""
    if not values:
        return {"n": 0, "mean": 0, "std": 0, "min": 0, "max": 0, "median": 0}
    n = len(values)
    mean = sum(values) / n
    variance = sum((x - mean) ** 2 for x in values) / n
    std = math.sqrt(variance)
    sorted_v = sorted(values)
    if n % 2 == 0:
        median = (sorted_v[n // 2 - 1] + sorted_v[n // 2]) / 2
    else:
        median = sorted_v[n // 2]
    return {"n": n, "mean": mean, "std": std, "min": sorted_v[0], "max": sorted_v[-1], "median": median}


def ks_test(baseline: List[float], current: List[float]) -> Tuple[float, float]:
    """
    Two-sample Kolmogorov-Smirnov test.
    Returns (ks_statistic, p_value).
    Uses scipy if available, otherwise computes statistic only (p_value = -1).
    """
    try:
        from scipy import stats as sp_stats
        result = sp_stats.ks_2samp(baseline, current)
        return result.statistic, result.pvalue
    except ImportError:
        pass

    # Fallback: compute KS statistic manually, no p-value
    all_values = sorted(set(baseline + current))
    n1 = len(baseline)
    n2 = len(current)
    if n1 == 0 or n2 == 0:
        return 0.0, -1.0

    baseline_sorted = sorted(baseline)
    current_sorted = sorted(current)

    max_d = 0.0
    i1 = i2 = 0
    for val in all_values:
        while i1 < n1 and baseline_sorted[i1] <= val:
            i1 += 1
        while i2 < n2 and current_sorted[i2] <= val:
            i2 += 1
        d = abs(i1 / n1 - i2 / n2)
        if d > max_d:
            max_d = d

    return max_d, -1.0  # -1 indicates p-value not available


def compute_psi(baseline: List[float], current: List[float], bins: int = 10) -> float:
    """
    Population Stability Index.
    PSI < 0.1: no significant drift
    PSI 0.1–0.25: moderate drift
    PSI > 0.25: significant drift
    """
    if not baseline or not current:
        return 0.0

    # Create bins from baseline
    min_val = min(min(baseline), min(current))
    max_val = max(max(baseline), max(current))
    if min_val == max_val:
        return 0.0

    bin_width = (max_val - min_val) / bins
    edges = [min_val + i * bin_width for i in range(bins + 1)]
    edges[-1] = max_val + 1e-10  # ensure max value is included

    def bin_proportions(values: List[float]) -> List[float]:
        counts = [0] * bins
        n = len(values)
        for v in values:
            for b in range(bins):
                if edges[b] <= v < edges[b + 1]:
                    counts[b] += 1
                    break
        # Avoid zeros with small epsilon
        return [(c / n) if c > 0 else 1e-6 for c in counts]

    baseline_props = bin_proportions(baseline)
    current_props = bin_proportions(current)

    psi = 0.0
    for bp, cp in zip(baseline_props, current_props):
        psi += (cp - bp) * math.log(cp / bp)

    return psi


def drift_severity(ks_stat: float, psi: float) -> str:
    """Combined drift severity label."""
    if psi > 0.25 or ks_stat > 0.2:
        return "SIGNIFICANT"
    if psi > 0.1 or ks_stat > 0.1:
        return "MODERATE"
    return "MINIMAL"


def main():
    parser = argparse.ArgumentParser(
        description="Detect data drift between baseline and current distributions using KS test and PSI."
    )
    parser.add_argument(
        "--baseline", "-b", required=True,
        help="Path to baseline period CSV",
    )
    parser.add_argument(
        "--current", "-c", required=True,
        help="Path to current period CSV",
    )
    parser.add_argument(
        "--columns", type=str, default=None,
        help="Comma-separated column names to compare (default: all numeric columns)",
    )
    parser.add_argument(
        "--threshold", "-t", type=float, default=0.1,
        help="KS statistic threshold for drift alert (default: 0.1)",
    )
    parser.add_argument(
        "--bins", type=int, default=10,
        help="Number of bins for PSI calculation (default: 10)",
    )
    args = parser.parse_args()

    columns = [c.strip() for c in args.columns.split(",")] if args.columns else None

    try:
        baseline_data = read_csv_columns(args.baseline, columns)
    except Exception as e:
        print(f"Error reading baseline CSV: {e}", file=sys.stderr)
        return 1

    try:
        current_data = read_csv_columns(args.current, columns)
    except Exception as e:
        print(f"Error reading current CSV: {e}", file=sys.stderr)
        return 1

    # Find common columns
    common_cols = sorted(set(baseline_data.keys()) & set(current_data.keys()))
    if not common_cols:
        print("Error: no common numeric columns found between baseline and current CSVs.", file=sys.stderr)
        return 1

    print("\n" + "=" * 70)
    print("📊 DATA DRIFT DETECTOR")
    print("=" * 70)

    print(f"\n📋 INPUTS:")
    print(f"   • Baseline: {args.baseline} ({len(next(iter(baseline_data.values()))):,} rows)")
    print(f"   • Current:  {args.current} ({len(next(iter(current_data.values()))):,} rows)")
    print(f"   • Columns:  {len(common_cols)}")
    print(f"   • KS threshold: {args.threshold}")

    drift_flags: List[str] = []

    for col in common_cols:
        b = baseline_data[col]
        c = current_data[col]
        b_stats = compute_stats(b)
        c_stats = compute_stats(c)
        ks_stat, ks_p = ks_test(b, c)
        psi = compute_psi(b, c, bins=args.bins)
        severity = drift_severity(ks_stat, psi)

        icon = {"SIGNIFICANT": "🔴", "MODERATE": "🟡", "MINIMAL": "🟢"}.get(severity, "⚪")
        alert = " ⚠️  DRIFT DETECTED" if ks_stat >= args.threshold else ""

        print(f"\n{icon} {col}{alert}")
        print(f"   ┌─ Baseline:  n={b_stats['n']:,}  mean={b_stats['mean']:.4f}  std={b_stats['std']:.4f}  median={b_stats['median']:.4f}")
        print(f"   ├─ Current:   n={c_stats['n']:,}  mean={c_stats['mean']:.4f}  std={c_stats['std']:.4f}  median={c_stats['median']:.4f}")
        mean_shift = c_stats['mean'] - b_stats['mean']
        mean_shift_pct = (100 * mean_shift / b_stats['mean']) if b_stats['mean'] != 0 else 0
        print(f"   ├─ Mean shift: {mean_shift:+.4f} ({mean_shift_pct:+.1f}%)")
        print(f"   ├─ KS statistic: {ks_stat:.4f}" + (f"  (p={ks_p:.4f})" if ks_p >= 0 else "  (p-value: install scipy)"))
        print(f"   ├─ PSI: {psi:.4f}" + _psi_label(psi))
        print(f"   └─ Severity: {severity}")

        if ks_stat >= args.threshold:
            drift_flags.append(col)

    # Summary
    print("\n" + "-" * 70)
    print("📋 SUMMARY:")
    print(f"   • Columns analyzed: {len(common_cols)}")
    print(f"   • Drift detected:   {len(drift_flags)}")
    if drift_flags:
        print(f"   • Flagged columns:  {', '.join(drift_flags)}")
        print(f"\n   ⚠️  Recommendation: Investigate flagged features for upstream data")
        print(f"      changes. Consider retraining or recalibrating the model.")
    else:
        print(f"\n   ✅ No significant drift detected. Distributions are stable.")

    print(f"\n📐 REFERENCE:")
    print(f"   • PSI < 0.10: No significant drift")
    print(f"   • PSI 0.10–0.25: Moderate drift (monitor)")
    print(f"   • PSI > 0.25: Significant drift (action needed)")
    print("=" * 70)
    return 0


def _psi_label(psi: float) -> str:
    """Inline PSI severity note."""
    if psi > 0.25:
        return "  (significant)"
    if psi > 0.1:
        return "  (moderate)"
    return "  (stable)"


if __name__ == "__main__":
    sys.exit(main())
