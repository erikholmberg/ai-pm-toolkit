#!/usr/bin/env python3
"""
Cohort Comparison Tool

Compare two user cohorts (e.g. power users vs. churned, control vs. treatment,
free vs. paid) across multiple metrics with statistical significance tests on
each dimension. Produces a side-by-side report with effect sizes and p-values.

Usage:
    # From CSV with two cohorts as rows
    python cohort-comparison-tool.py --csv cohorts.csv

    # Inline: two cohorts with metrics
    python cohort-comparison-tool.py \\
        --cohort-a "Power Users" --cohort-b "Churned" \\
        --metric "Sessions/week:12.5:3.2:4.1:2.8" \\
        --metric "Feature adoption %:78:65:22:18" \\
        --metric "Support tickets:1.2:0.8:4.5:3.1"

    # Format: --metric "Name:mean_a:std_a:mean_b:std_b" (std is optional)

CSV format (header row required):
    metric,cohort_a_mean,cohort_a_std,cohort_a_n,cohort_b_mean,cohort_b_std,cohort_b_n
    Sessions per week,12.5,3.2,500,4.1,2.8,300
    Feature adoption %,78,15,500,22,18,300
    NPS,45,20,500,12,25,300
    Days since last login,3,2,500,28,15,300
    Support tickets,1.2,0.8,500,4.5,3.1,300

    Required: metric, cohort_a_mean, cohort_b_mean
    Optional: cohort_a_std, cohort_b_std (for significance tests)
    Optional: cohort_a_n, cohort_b_n (sample sizes; default 100)

Requirements:
    None (stdlib only). Optional: scipy for exact p-values.
"""

import argparse
import csv
import json
import math
import sys
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Statistics
# ---------------------------------------------------------------------------

def welch_t_test(
    mean_a: float, std_a: float, n_a: int,
    mean_b: float, std_b: float, n_b: int,
) -> Tuple[float, float, float]:
    """
    Welch's t-test for comparing two means with unequal variances.

    Returns (t_statistic, degrees_of_freedom, p_value).
    p_value requires scipy; returns -1 without it.
    """
    if std_a == 0 and std_b == 0:
        return 0.0, 0.0, -1.0

    se_a = (std_a ** 2) / n_a if n_a > 0 else 0
    se_b = (std_b ** 2) / n_b if n_b > 0 else 0
    se = math.sqrt(se_a + se_b)

    if se == 0:
        return 0.0, 0.0, -1.0

    t = (mean_a - mean_b) / se

    # Welch-Satterthwaite degrees of freedom
    num = (se_a + se_b) ** 2
    denom = 0
    if n_a > 1 and se_a > 0:
        denom += (se_a ** 2) / (n_a - 1)
    if n_b > 1 and se_b > 0:
        denom += (se_b ** 2) / (n_b - 1)

    df = num / denom if denom > 0 else max(n_a, n_b) - 1

    # Try scipy for exact p-value
    try:
        from scipy import stats as sp_stats
        p_value = 2 * sp_stats.t.sf(abs(t), df)
        return t, df, p_value
    except ImportError:
        # Approximate p-value using normal distribution for large df
        if df >= 30:
            # Use complementary error function for normal approximation
            z = abs(t)
            p_approx = 2 * (1 - _normal_cdf(z))
            return t, df, p_approx
        return t, df, -1.0


def _normal_cdf(x: float) -> float:
    """Approximate CDF of the standard normal distribution."""
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def cohens_d(mean_a: float, std_a: float, mean_b: float, std_b: float) -> float:
    """
    Cohen's d effect size: (mean_a - mean_b) / pooled_std.
    """
    pooled_std = math.sqrt((std_a ** 2 + std_b ** 2) / 2) if (std_a > 0 or std_b > 0) else 1
    if pooled_std == 0:
        return 0.0
    return (mean_a - mean_b) / pooled_std


def effect_size_label(d: float) -> str:
    """Interpret Cohen's d."""
    d_abs = abs(d)
    if d_abs >= 0.8:
        return "Large"
    elif d_abs >= 0.5:
        return "Medium"
    elif d_abs >= 0.2:
        return "Small"
    else:
        return "Negligible"


def pct_difference(mean_a: float, mean_b: float) -> float:
    """Percentage difference: (a - b) / |b| * 100."""
    if mean_b == 0:
        return 0.0 if mean_a == 0 else float("inf")
    return (mean_a - mean_b) / abs(mean_b) * 100


# ---------------------------------------------------------------------------
# Metric comparison
# ---------------------------------------------------------------------------

def compare_metric(
    name: str,
    mean_a: float, std_a: float, n_a: int,
    mean_b: float, std_b: float, n_b: int,
    direction: Optional[str] = None,
) -> Dict[str, Any]:
    """Compare a single metric between two cohorts."""
    diff = mean_a - mean_b
    pct_diff = pct_difference(mean_a, mean_b)

    result: Dict[str, Any] = {
        "metric": name,
        "cohort_a_mean": round(mean_a, 4),
        "cohort_b_mean": round(mean_b, 4),
        "difference": round(diff, 4),
        "pct_difference": round(pct_diff, 1),
    }

    # Effect size
    if std_a > 0 or std_b > 0:
        d = cohens_d(mean_a, std_a, mean_b, std_b)
        result["cohens_d"] = round(d, 3)
        result["effect_size"] = effect_size_label(d)

    # Statistical significance
    if (std_a > 0 or std_b > 0) and n_a > 1 and n_b > 1:
        t, df, p = welch_t_test(mean_a, std_a, n_a, mean_b, std_b, n_b)
        result["t_statistic"] = round(t, 3)
        result["df"] = round(df, 1)
        result["p_value"] = round(p, 4) if p >= 0 else None
        if p >= 0:
            result["significant"] = p < 0.05
            result["highly_significant"] = p < 0.01
        else:
            result["significant"] = None

    # Who "wins"
    if diff > 0:
        result["higher_cohort"] = "A"
    elif diff < 0:
        result["higher_cohort"] = "B"
    else:
        result["higher_cohort"] = "Equal"

    return result


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def _col(fieldnames: List[str], *aliases: str) -> Optional[str]:
    lower_map = {f.lower().strip(): f for f in fieldnames}
    for alias in aliases:
        if alias.lower().strip() in lower_map:
            return lower_map[alias.lower().strip()]
    return None


def _float(row: Dict, col: Optional[str], default: float = 0.0) -> float:
    if not col:
        return default
    raw = row.get(col, "")
    if not raw or not str(raw).strip():
        return default
    try:
        return float(str(raw).strip().replace(",", "").rstrip("%"))
    except ValueError:
        return default


def load_csv(path: str) -> Tuple[List[Dict[str, Any]], Optional[str], Optional[str]]:
    """
    Load metric comparisons from CSV.
    Returns (metrics_list, cohort_a_name, cohort_b_name).
    """
    metrics: List[Dict[str, Any]] = []
    cohort_a_name = None
    cohort_b_name = None

    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fields = reader.fieldnames or []
        c_metric = _col(fields, "metric", "name", "dimension", "kpi")
        c_a_mean = _col(fields, "cohort_a_mean", "a_mean", "mean_a", "group_a", "control_mean", "control")
        c_a_std = _col(fields, "cohort_a_std", "a_std", "std_a", "control_std")
        c_a_n = _col(fields, "cohort_a_n", "a_n", "n_a", "control_n")
        c_b_mean = _col(fields, "cohort_b_mean", "b_mean", "mean_b", "group_b", "treatment_mean", "treatment")
        c_b_std = _col(fields, "cohort_b_std", "b_std", "std_b", "treatment_std")
        c_b_n = _col(fields, "cohort_b_n", "b_n", "n_b", "treatment_n")
        c_a_name = _col(fields, "cohort_a_name", "a_name", "cohort_a")
        c_b_name = _col(fields, "cohort_b_name", "b_name", "cohort_b")

        for row in reader:
            name = row.get(c_metric or "metric", "").strip()
            if not name:
                continue

            mean_a = _float(row, c_a_mean)
            std_a = _float(row, c_a_std, 0.0)
            n_a = int(_float(row, c_a_n, 100))
            mean_b = _float(row, c_b_mean)
            std_b = _float(row, c_b_std, 0.0)
            n_b = int(_float(row, c_b_n, 100))

            if c_a_name and not cohort_a_name:
                cohort_a_name = row.get(c_a_name, "").strip()
            if c_b_name and not cohort_b_name:
                cohort_b_name = row.get(c_b_name, "").strip()

            metrics.append({
                "name": name,
                "mean_a": mean_a, "std_a": std_a, "n_a": n_a,
                "mean_b": mean_b, "std_b": std_b, "n_b": n_b,
            })

    return metrics, cohort_a_name, cohort_b_name


def parse_inline_metric(s: str) -> Dict[str, Any]:
    """Parse 'Name:mean_a:std_a:mean_b:std_b' into metric dict."""
    parts = s.split(":")
    if len(parts) < 3:
        raise ValueError(f"Invalid metric format '{s}'. Need at least 'Name:mean_a:mean_b'.")

    name = parts[0].strip()
    mean_a = float(parts[1].strip())

    if len(parts) == 3:
        # Name:mean_a:mean_b (no std)
        return {"name": name, "mean_a": mean_a, "std_a": 0, "n_a": 100, "mean_b": float(parts[2].strip()), "std_b": 0, "n_b": 100}
    elif len(parts) == 5:
        # Name:mean_a:std_a:mean_b:std_b
        return {
            "name": name,
            "mean_a": mean_a, "std_a": float(parts[2].strip()), "n_a": 100,
            "mean_b": float(parts[3].strip()), "std_b": float(parts[4].strip()), "n_b": 100,
        }
    elif len(parts) == 7:
        # Name:mean_a:std_a:n_a:mean_b:std_b:n_b
        return {
            "name": name,
            "mean_a": mean_a, "std_a": float(parts[2].strip()), "n_a": int(parts[3].strip()),
            "mean_b": float(parts[4].strip()), "std_b": float(parts[5].strip()), "n_b": int(parts[6].strip()),
        }
    else:
        raise ValueError(f"Invalid metric format '{s}'. Use Name:mean_a:mean_b or Name:mean_a:std_a:mean_b:std_b")


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def _bar_comparison(val_a: float, val_b: float, width: int = 20) -> str:
    """Render a side-by-side comparison bar."""
    max_val = max(abs(val_a), abs(val_b), 0.001)
    bar_a = int(abs(val_a) / max_val * width)
    bar_b = int(abs(val_b) / max_val * width)
    return f"{'█' * bar_a}{'░' * (width - bar_a)} │ {'█' * bar_b}{'░' * (width - bar_b)}"


def _fmt(val: float) -> str:
    if abs(val) >= 10000:
        return f"{val:,.0f}"
    elif val == int(val):
        return f"{int(val):,}"
    elif abs(val) >= 10:
        return f"{val:,.1f}"
    else:
        return f"{val:,.2f}"


def print_report(
    comparisons: List[Dict[str, Any]],
    cohort_a_name: str,
    cohort_b_name: str,
    n_a: Optional[int],
    n_b: Optional[int],
) -> None:
    """Pretty-print cohort comparison."""
    print("\n" + "=" * 78)
    print("📊 COHORT COMPARISON TOOL")
    print("=" * 78)

    print(f"\n📋 COHORTS:")
    print(f"   • Cohort A: {cohort_a_name}" + (f" (n={n_a:,})" if n_a else ""))
    print(f"   • Cohort B: {cohort_b_name}" + (f" (n={n_b:,})" if n_b else ""))
    print(f"   • Metrics compared: {len(comparisons)}")

    # Summary
    sig_count = sum(1 for c in comparisons if c.get("significant") is True)
    large_effect = sum(1 for c in comparisons if c.get("effect_size") in ("Large", "Medium"))
    a_wins = sum(1 for c in comparisons if c["higher_cohort"] == "A")
    b_wins = sum(1 for c in comparisons if c["higher_cohort"] == "B")

    print(f"\n📐 SUMMARY:")
    print(f"   • Statistically significant differences: {sig_count} of {len(comparisons)}")
    print(f"   • Medium/large effect sizes: {large_effect}")
    print(f"   • {cohort_a_name} higher in: {a_wins} metrics")
    print(f"   • {cohort_b_name} higher in: {b_wins} metrics")

    # Comparison table
    a_label = cohort_a_name[:12]
    b_label = cohort_b_name[:12]

    print(f"\n📈 METRIC-BY-METRIC COMPARISON:\n")
    print(f"   {'Metric':<22} {a_label:>12} {b_label:>12} {'Diff':>9} {'% Diff':>8} {'Effect':>10} {'p-value':>9} {'Sig':>4}")
    print(f"   {'─'*22} {'─'*12} {'─'*12} {'─'*9} {'─'*8} {'─'*10} {'─'*9} {'─'*4}")

    for c in comparisons:
        a_val = _fmt(c["cohort_a_mean"])
        b_val = _fmt(c["cohort_b_mean"])
        diff = _fmt(c["difference"])
        pct = f"{c['pct_difference']:+.1f}%"
        effect = c.get("effect_size", "—")
        p = f"{c['p_value']:.4f}" if c.get("p_value") is not None else "—"
        sig = ""
        if c.get("highly_significant"):
            sig = "***"
        elif c.get("significant"):
            sig = "*"
        elif c.get("significant") is False:
            sig = "ns"

        print(f"   {c['metric'][:22]:<22} {a_val:>12} {b_val:>12} {diff:>9} {pct:>8} {effect:>10} {p:>9} {sig:>4}")

    # Visual comparison
    print(f"\n📊 VISUAL COMPARISON:")
    print(f"   {'Metric':<22} {a_label:^20} │ {b_label:^20}")
    print(f"   {'─'*22} {'─'*20} ┼ {'─'*20}")
    for c in comparisons:
        bar = _bar_comparison(c["cohort_a_mean"], c["cohort_b_mean"])
        print(f"   {c['metric'][:22]:<22} {bar}")

    # Key differences
    significant_diffs = [c for c in comparisons if c.get("significant") is True]
    if significant_diffs:
        # Sort by effect size
        significant_diffs.sort(key=lambda x: abs(x.get("cohens_d", 0)), reverse=True)
        print(f"\n🎯 KEY DIFFERENCES (statistically significant):")
        for c in significant_diffs:
            higher = cohort_a_name if c["higher_cohort"] == "A" else cohort_b_name
            d = c.get("cohens_d", 0)
            print(f"   • {c['metric']}: {higher} is {abs(c['pct_difference']):.1f}% higher (d={d:+.2f}, {c['effect_size']})")

    # Non-significant
    non_sig = [c for c in comparisons if c.get("significant") is False]
    if non_sig:
        names = ", ".join(c["metric"] for c in non_sig)
        print(f"\n   ℹ️  No significant difference: {names}")

    print(f"\n💡 INTERPRETATION:")
    print(f"   • * p < 0.05 (significant)  |  *** p < 0.01 (highly significant)  |  ns = not significant")
    print(f"   • Cohen's d: |d| < 0.2 negligible, 0.2-0.5 small, 0.5-0.8 medium, > 0.8 large")
    print(f"   • Significance ≠ importance — consider effect size and business context")
    print("\n" + "=" * 78)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Compare two user cohorts across multiple metrics with statistical tests.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --csv cohorts.csv
  %(prog)s --cohort-a "Power Users" --cohort-b "Churned" \\
           --metric "Sessions/week:12.5:3.2:4.1:2.8" \\
           --metric "Feature adoption:78:15:22:18"
  %(prog)s --csv cohorts.csv --output report.json

Inline metric format:
  "Name:mean_a:mean_b"                             (no std — no significance test)
  "Name:mean_a:std_a:mean_b:std_b"                 (with std — runs t-test, n=100)
  "Name:mean_a:std_a:n_a:mean_b:std_b:n_b"         (with std and sample sizes)
        """,
    )
    parser.add_argument("--csv", "-c", type=str, help="CSV file with cohort metric data")
    parser.add_argument("--cohort-a", type=str, default="Cohort A", help="Name for cohort A")
    parser.add_argument("--cohort-b", type=str, default="Cohort B", help="Name for cohort B")
    parser.add_argument("--metric", "-m", type=str, action="append", help="Metric as 'Name:mean_a:std_a:mean_b:std_b'")
    parser.add_argument("--n-a", type=int, help="Sample size for cohort A (default: per-metric or 100)")
    parser.add_argument("--n-b", type=int, help="Sample size for cohort B (default: per-metric or 100)")
    parser.add_argument("--output", "-o", type=str, help="Write results to JSON file")
    args = parser.parse_args()

    cohort_a_name = args.cohort_a
    cohort_b_name = args.cohort_b
    metrics: List[Dict[str, Any]] = []

    if args.csv:
        try:
            metrics, csv_a_name, csv_b_name = load_csv(args.csv)
            if csv_a_name:
                cohort_a_name = csv_a_name
            if csv_b_name:
                cohort_b_name = csv_b_name
        except Exception as e:
            print(f"Error loading CSV: {e}", file=sys.stderr)
            return 1
    elif args.metric:
        try:
            metrics = [parse_inline_metric(m) for m in args.metric]
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1
    else:
        print("Error: provide --csv or --metric.", file=sys.stderr)
        parser.print_help(sys.stderr)
        return 1

    if not metrics:
        print("Error: no valid metrics found.", file=sys.stderr)
        return 1

    # Override sample sizes if provided
    if args.n_a:
        for m in metrics:
            m["n_a"] = args.n_a
    if args.n_b:
        for m in metrics:
            m["n_b"] = args.n_b

    # Compare each metric
    comparisons = [
        compare_metric(
            m["name"],
            m["mean_a"], m["std_a"], m["n_a"],
            m["mean_b"], m["std_b"], m["n_b"],
        )
        for m in metrics
    ]

    # Determine display sample sizes
    display_n_a = args.n_a or (metrics[0]["n_a"] if metrics else None)
    display_n_b = args.n_b or (metrics[0]["n_b"] if metrics else None)

    # Report
    print_report(comparisons, cohort_a_name, cohort_b_name, display_n_a, display_n_b)

    # JSON output
    if args.output:
        report = {
            "cohort_a": cohort_a_name,
            "cohort_b": cohort_b_name,
            "n_metrics": len(comparisons),
            "significant_differences": sum(1 for c in comparisons if c.get("significant") is True),
            "comparisons": comparisons,
        }
        with open(args.output, "w") as f:
            json.dump(report, f, indent=2)
        print(f"\n📁 Results saved to {args.output}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
