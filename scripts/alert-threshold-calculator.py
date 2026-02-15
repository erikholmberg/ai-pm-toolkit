#!/usr/bin/env python3
"""
Alert Threshold Calculator

Given a time series of a metric (CSV or inline values), compute sensible static
and dynamic alert thresholds using multiple methods. Helps PMs configure
monitoring without guessing.

Methods:
    - Standard deviation (3-sigma):  mean ± k×σ
    - IQR-based (Tukey fences):      Q1 - 1.5×IQR, Q3 + 1.5×IQR
    - Percentile-based:              alert on p1/p99 or p5/p95
    - Rolling z-score:               flag points that deviate from a rolling window

Usage:
    # From inline values
    python alert-threshold-calculator.py --values 100 102 98 105 97 99 103 250 101 100

    # From CSV (one metric column)
    python alert-threshold-calculator.py --csv latency.csv --column p99_ms

    # With custom sensitivity
    python alert-threshold-calculator.py --csv metrics.csv --column error_rate --sigma 2.5

    # Specify direction (alert on high only, low only, or both)
    python alert-threshold-calculator.py --values 100 102 98 105 --direction upper

CSV format:
    timestamp,p99_ms,error_rate,cpu_pct
    2025-01-01,1200,0.5,42
    2025-01-02,1350,0.8,45
    ...

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
# Statistics helpers (stdlib, no numpy needed)
# ---------------------------------------------------------------------------

def mean(values: List[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def stdev(values: List[float]) -> float:
    if len(values) < 2:
        return 0.0
    m = mean(values)
    variance = sum((x - m) ** 2 for x in values) / (len(values) - 1)
    return math.sqrt(variance)


def percentile(values: List[float], p: float) -> float:
    """Approximate percentile (linear interpolation)."""
    if not values:
        return 0.0
    s = sorted(values)
    n = len(s)
    idx = p / 100.0 * (n - 1)
    lo = int(idx)
    hi = min(lo + 1, n - 1)
    w = idx - lo
    return s[lo] * (1 - w) + s[hi] * w


def median(values: List[float]) -> float:
    return percentile(values, 50)


def iqr(values: List[float]) -> Tuple[float, float, float]:
    """Returns (Q1, Q3, IQR)."""
    q1 = percentile(values, 25)
    q3 = percentile(values, 75)
    return q1, q3, q3 - q1


# ---------------------------------------------------------------------------
# Threshold methods
# ---------------------------------------------------------------------------

def sigma_thresholds(values: List[float], k: float = 3.0) -> Dict[str, Any]:
    """
    Standard deviation method: mean ± k × σ.
    Common: k=2 (aggressive), k=3 (standard), k=4 (conservative).
    """
    m = mean(values)
    s = stdev(values)
    return {
        "method": f"{k:.1f}-sigma",
        "mean": round(m, 4),
        "stdev": round(s, 4),
        "lower": round(m - k * s, 4),
        "upper": round(m + k * s, 4),
    }


def iqr_thresholds(values: List[float], multiplier: float = 1.5) -> Dict[str, Any]:
    """
    Tukey fences: Q1 - multiplier×IQR, Q3 + multiplier×IQR.
    More robust to outliers than sigma method.
    """
    q1, q3, iqr_val = iqr(values)
    return {
        "method": f"IQR (×{multiplier})",
        "q1": round(q1, 4),
        "q3": round(q3, 4),
        "iqr": round(iqr_val, 4),
        "lower": round(q1 - multiplier * iqr_val, 4),
        "upper": round(q3 + multiplier * iqr_val, 4),
    }


def percentile_thresholds(
    values: List[float],
    lower_pct: float = 1.0,
    upper_pct: float = 99.0,
) -> Dict[str, Any]:
    """
    Percentile-based: alert when metric falls outside [p_lower, p_upper].
    """
    return {
        "method": f"Percentile (p{lower_pct:.0f}/p{upper_pct:.0f})",
        "lower": round(percentile(values, lower_pct), 4),
        "upper": round(percentile(values, upper_pct), 4),
        "p5": round(percentile(values, 5), 4),
        "p50": round(percentile(values, 50), 4),
        "p95": round(percentile(values, 95), 4),
    }


def rolling_zscore(values: List[float], window: int = 7, threshold: float = 3.0) -> Dict[str, Any]:
    """
    Rolling z-score: for each point, compute z-score relative to the previous
    `window` points. Flag points that exceed threshold.
    """
    anomalies: List[Dict[str, Any]] = []
    z_scores: List[Optional[float]] = []

    for i in range(len(values)):
        if i < window:
            z_scores.append(None)
            continue
        window_vals = values[i - window:i]
        m = mean(window_vals)
        s = stdev(window_vals)
        if s == 0:
            z = 0.0
        else:
            z = (values[i] - m) / s
        z_scores.append(round(z, 2))

        if abs(z) >= threshold:
            anomalies.append({
                "index": i,
                "value": values[i],
                "z_score": round(z, 2),
                "window_mean": round(m, 2),
                "window_stdev": round(s, 2),
            })

    return {
        "method": f"Rolling z-score (window={window}, threshold={threshold})",
        "window": window,
        "threshold": threshold,
        "anomalies_found": len(anomalies),
        "anomalies": anomalies[:20],
    }


# ---------------------------------------------------------------------------
# Full analysis
# ---------------------------------------------------------------------------

def analyze(
    values: List[float],
    sigma_k: float = 3.0,
    iqr_multiplier: float = 1.5,
    rolling_window: int = 7,
    direction: str = "both",
    zscore_threshold: float = 3.0,
) -> Dict[str, Any]:
    """Run all threshold methods and return unified results."""
    sig = sigma_thresholds(values, sigma_k)
    iqr_t = iqr_thresholds(values, iqr_multiplier)
    pct = percentile_thresholds(values)
    rolling = rolling_zscore(values, rolling_window, zscore_threshold)

    # Count how many existing data points would have triggered each method
    def count_violations(lower: float, upper: float) -> int:
        count = 0
        for v in values:
            if direction in ("both", "lower") and v < lower:
                count += 1
            if direction in ("both", "upper") and v > upper:
                count += 1
        return count

    sig["violations"] = count_violations(sig["lower"], sig["upper"])
    iqr_t["violations"] = count_violations(iqr_t["lower"], iqr_t["upper"])
    pct["violations"] = count_violations(pct["lower"], pct["upper"])

    # Recommended threshold (pick the method with ~1-5% violation rate)
    n = len(values)
    target_violation_pct = 2.0  # ~2% is a good default
    methods = [sig, iqr_t, pct]
    best = min(methods, key=lambda m: abs((m["violations"] / n * 100) - target_violation_pct) if n > 0 else 100)

    return {
        "n_points": n,
        "summary": {
            "min": round(min(values), 4),
            "max": round(max(values), 4),
            "mean": round(mean(values), 4),
            "median": round(median(values), 4),
            "stdev": round(stdev(values), 4),
            "p5": round(percentile(values, 5), 4),
            "p95": round(percentile(values, 95), 4),
        },
        "sigma": sig,
        "iqr": iqr_t,
        "percentile": pct,
        "rolling_zscore": rolling,
        "recommended": best["method"],
        "recommended_lower": best["lower"],
        "recommended_upper": best["upper"],
        "direction": direction,
    }


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_csv_column(path: str, column: str) -> Tuple[List[float], List[str]]:
    """Load a single metric column from CSV. Returns (values, timestamps)."""
    values: List[float] = []
    timestamps: List[str] = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fields = reader.fieldnames or []

        # Find the column (case-insensitive)
        lower_map = {fl.lower().strip(): fl for fl in fields}
        actual_col = lower_map.get(column.lower().strip())
        if not actual_col:
            raise ValueError(f"Column '{column}' not found. Available: {', '.join(fields)}")

        # Try to find a timestamp column
        ts_col = None
        for alias in ["timestamp", "date", "time", "ts", "datetime", "day"]:
            if alias in lower_map:
                ts_col = lower_map[alias]
                break

        for row in reader:
            raw = row.get(actual_col, "")
            if not raw or not str(raw).strip():
                continue
            try:
                values.append(float(str(raw).strip().replace(",", "")))
                timestamps.append(row.get(ts_col or "", "").strip() if ts_col else "")
            except ValueError:
                continue

    return values, timestamps


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def _bar(value: float, lo: float, hi: float, width: int = 40) -> str:
    """Render a value on a [lo, hi] scale."""
    if hi <= lo:
        return "·" * width
    ratio = min(1.0, max(0.0, (value - lo) / (hi - lo)))
    pos = int(ratio * (width - 1))
    bar = list("·" * width)
    bar[pos] = "●"
    return "".join(bar)


def print_report(
    results: Dict[str, Any],
    metric_name: str,
) -> None:
    """Pretty-print threshold analysis."""
    s = results["summary"]
    sig = results["sigma"]
    iqr_t = results["iqr"]
    pct = results["percentile"]
    rolling = results["rolling_zscore"]
    n = results["n_points"]
    direction = results["direction"]

    print("\n" + "=" * 78)
    print("📊 ALERT THRESHOLD CALCULATOR")
    print("=" * 78)

    print(f"\n📋 METRIC: {metric_name}")
    print(f"   • Data points:   {n}")
    print(f"   • Range:          {s['min']:.2f} – {s['max']:.2f}")
    print(f"   • Mean:           {s['mean']:.2f}")
    print(f"   • Median:         {s['median']:.2f}")
    print(f"   • Std dev:        {s['stdev']:.2f}")
    print(f"   • Alert on:       {direction}")

    # Threshold comparison table
    print(f"\n📐 THRESHOLD METHODS:")
    print(f"   {'Method':<28} {'Lower':>12} {'Upper':>12} {'Violations':>12}")
    print(f"   {'─'*28} {'─'*12} {'─'*12} {'─'*12}")

    methods = [
        (sig["method"], sig["lower"], sig["upper"], sig["violations"]),
        (iqr_t["method"], iqr_t["lower"], iqr_t["upper"], iqr_t["violations"]),
        (pct["method"], pct["lower"], pct["upper"], pct["violations"]),
    ]

    for method_name, lower, upper, violations in methods:
        viol_pct = violations / n * 100 if n > 0 else 0
        rec = " ← recommended" if method_name == results["recommended"] else ""
        lower_str = f"{lower:.2f}" if direction in ("both", "lower") else "—"
        upper_str = f"{upper:.2f}" if direction in ("both", "upper") else "—"
        print(f"   {method_name:<28} {lower_str:>12} {upper_str:>12} {violations:>8} ({viol_pct:.1f}%){rec}")

    # Visual scale
    scale_lo = min(sig["lower"], iqr_t["lower"], pct["lower"], s["min"])
    scale_hi = max(sig["upper"], iqr_t["upper"], pct["upper"], s["max"])

    print(f"\n📊 VISUAL SCALE:")
    print(f"   {'':40}  {scale_lo:<10.1f}{'':>20}{scale_hi:>10.1f}")

    # Show where each threshold falls
    for method_name, lower, upper, _ in methods:
        lower_bar = _bar(lower, scale_lo, scale_hi)
        upper_bar = _bar(upper, scale_lo, scale_hi)
        # Combine into one line: show lower and upper markers
        combined = list("·" * 40)
        lo_pos = int(min(1.0, max(0.0, (lower - scale_lo) / max(1, scale_hi - scale_lo))) * 39)
        hi_pos = int(min(1.0, max(0.0, (upper - scale_lo) / max(1, scale_hi - scale_lo))) * 39)
        mean_pos = int(min(1.0, max(0.0, (s["mean"] - scale_lo) / max(1, scale_hi - scale_lo))) * 39)
        if direction in ("both", "lower"):
            combined[lo_pos] = "L"
        if direction in ("both", "upper"):
            combined[hi_pos] = "U"
        combined[mean_pos] = "M"
        # Fill between L and U with dashes
        for k in range(min(lo_pos, hi_pos) + 1, max(lo_pos, hi_pos)):
            if combined[k] == "·":
                combined[k] = "─"
        print(f"   {method_name:<28} {''.join(combined)}")

    print(f"   {'(L=lower, M=mean, U=upper)':>68}")

    # Rolling z-score anomalies
    if rolling["anomalies"]:
        print(f"\n⚠️  ANOMALIES DETECTED (rolling z-score, window={rolling['window']}):")
        for a in rolling["anomalies"][:10]:
            direction_str = "above" if a["z_score"] > 0 else "below"
            print(
                f"   • Index {a['index']}: {a['value']:.2f} "
                f"(z={a['z_score']:+.1f}, {direction_str} window mean {a['window_mean']:.2f})"
            )

    # Recommendation
    print(f"\n🎯 RECOMMENDED THRESHOLDS:")
    if direction in ("both", "lower"):
        print(f"   • Lower alert:  {results['recommended_lower']:.2f}")
    if direction in ("both", "upper"):
        print(f"   • Upper alert:  {results['recommended_upper']:.2f}")
    print(f"   • Method:       {results['recommended']}")
    print(f"   • Rationale:    targets ~2% historical violation rate")

    print(f"\n💡 TIPS:")
    print(f"   • Start with recommended thresholds, tune based on alert fatigue")
    print(f"   • Sigma: best for normally distributed data")
    print(f"   • IQR: more robust to outliers and skewed distributions")
    print(f"   • Percentile: simple and intuitive, good baseline")
    print(f"   • Use --direction upper/lower if only one side matters")
    print("\n" + "=" * 78)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Compute alert thresholds for a metric using multiple statistical methods. "
                    "Helps PMs configure monitoring without guessing.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --values 100 102 98 105 97 99 103 250 101 100
  %(prog)s --csv latency.csv --column p99_ms
  %(prog)s --csv metrics.csv --column error_rate --sigma 2.5 --direction upper
  %(prog)s --values 50 52 48 55 47 49 53 51 --output thresholds.json
        """,
    )
    parser.add_argument("--values", "-v", type=float, nargs="+", help="Metric values (space-separated)")
    parser.add_argument("--csv", "-c", type=str, help="CSV file with metric data")
    parser.add_argument("--column", type=str, help="Column name to analyze (required with --csv)")
    parser.add_argument("--sigma", "-s", type=float, default=3.0, help="Sigma multiplier for std-dev method (default: 3.0)")
    parser.add_argument("--iqr-multiplier", type=float, default=1.5, help="IQR multiplier for Tukey fences (default: 1.5)")
    parser.add_argument("--window", "-w", type=int, default=7, help="Rolling window size for z-score (default: 7)")
    parser.add_argument("--zscore-threshold", type=float, default=3.0,
                        help="Z-score threshold for rolling anomaly detection (default: 3.0). "
                             "Independent of --sigma which controls the static threshold method.")
    parser.add_argument(
        "--direction", "-d", type=str, default="both",
        choices=["both", "upper", "lower"],
        help="Alert direction: both, upper (high only), lower (low only). Default: both",
    )
    parser.add_argument("--output", "-o", type=str, help="Write results to JSON file")
    args = parser.parse_args()

    metric_name = "metric"

    if args.values:
        values = args.values
        metric_name = "inline values"
    elif args.csv:
        if not args.column:
            print("Error: --column is required with --csv.", file=sys.stderr)
            return 1
        try:
            values, timestamps = load_csv_column(args.csv, args.column)
            metric_name = args.column
        except Exception as e:
            print(f"Error loading CSV: {e}", file=sys.stderr)
            return 1
    else:
        print("Error: provide --values or --csv.", file=sys.stderr)
        parser.print_help(sys.stderr)
        return 1

    if len(values) < 5:
        print("Error: need at least 5 data points for meaningful thresholds.", file=sys.stderr)
        return 1

    # Analyze
    results = analyze(
        values,
        sigma_k=args.sigma,
        iqr_multiplier=args.iqr_multiplier,
        rolling_window=args.window,
        direction=args.direction,
        zscore_threshold=args.zscore_threshold,
    )

    # Report
    print_report(results, metric_name)

    # JSON output
    if args.output:
        with open(args.output, "w") as f:
            json.dump(results, f, indent=2)
        print(f"\n📁 Results saved to {args.output}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
