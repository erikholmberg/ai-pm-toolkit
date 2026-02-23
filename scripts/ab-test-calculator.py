#!/usr/bin/env python3
"""
A/B Test Sample-Size Calculator

Calculate the sample size, duration, and power for A/B tests. Supports:
    - Conversion-rate tests (proportions)
    - Revenue / continuous-metric tests (means)
    - Multiple variants (A/B/n)
    - Multiple-comparison correction (Bonferroni, Šidák)
    - Duration estimation from daily traffic
    - Post-hoc power analysis

Helps PMs right-size experiments before launch and avoid under-powered tests
that waste eng time or over-powered tests that waste user traffic.

Usage:
    # Basic conversion-rate test
    python ab-test-calculator.py \\
        --baseline-rate 5.0 --mde 10 --significance 0.05 --power 80

    # Revenue test (continuous metric)
    python ab-test-calculator.py \\
        --baseline-mean 48.50 --baseline-std 25 --mde 5 \\
        --significance 0.05 --power 80

    # With traffic estimation
    python ab-test-calculator.py \\
        --baseline-rate 3.2 --mde 15 \\
        --daily-traffic 50000 --traffic-pct 100

    # Multiple variants
    python ab-test-calculator.py \\
        --baseline-rate 5.0 --mde 10 --variants 3

    # Post-hoc analysis (already ran the test)
    python ab-test-calculator.py \\
        --baseline-rate 5.0 --variant-rate 5.6 \\
        --sample-size 8000 --post-hoc

    # Batch from CSV (multiple tests)
    python ab-test-calculator.py --csv tests.csv

CSV format:
    test_name,baseline_rate,mde_pct,significance,power,daily_traffic,variants
    Checkout CTA,5.0,10,0.05,80,50000,2
    Onboarding flow,12.0,8,0.05,80,20000,3

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
# Statistics helpers (stdlib-only, no scipy)
# ---------------------------------------------------------------------------

def _norm_cdf(x: float) -> float:
    """Standard normal CDF using Abramowitz & Stegun approximation."""
    sign = 1 if x >= 0 else -1
    x = abs(x)
    t = 1.0 / (1.0 + 0.2316419 * x)
    b1, b2, b3, b4, b5 = 0.319381530, -0.356563782, 1.781477937, -1.821255978, 1.330274429
    poly = t * (b1 + t * (b2 + t * (b3 + t * (b4 + t * b5))))
    pdf = math.exp(-0.5 * x * x) / math.sqrt(2 * math.pi)
    cdf = 1.0 - pdf * poly
    return 0.5 + sign * (cdf - 0.5)


def _norm_ppf(p: float) -> float:
    """Inverse standard normal (percent-point function) via rational approx."""
    if p <= 0:
        return -10.0
    if p >= 1:
        return 10.0
    if p == 0.5:
        return 0.0

    if p < 0.5:
        return -_norm_ppf(1 - p)

    # Rational approximation for 0.5 < p < 1 (Peter Acklam)
    a = [-3.969683028665376e+01, 2.209460984245205e+02,
         -2.759285104469687e+02, 1.383577518672690e+02,
         -3.066479806614716e+01, 2.506628277459239e+00]
    b = [-5.447609879822406e+01, 1.615858368580409e+02,
         -1.556989798598866e+02, 6.680131188771972e+01,
         -1.328068155288572e+01]
    c = [-7.784894002430293e-03, -3.223964580411365e-01,
         -2.400758277161838e+00, -2.549732539343734e+00,
         4.374664141464968e+00, 2.938163982698783e+00]
    d = [7.784695709041462e-03, 3.224671290700398e-01,
         2.445134137142996e+00, 3.754408661907416e+00]

    p_low = 0.02425
    p_high = 1 - p_low

    if p < p_low:
        q = math.sqrt(-2 * math.log(p))
        return (((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5]) / \
               ((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1)
    elif p <= p_high:
        q = p - 0.5
        r = q * q
        return (((((a[0]*r+a[1])*r+a[2])*r+a[3])*r+a[4])*r+a[5])*q / \
               (((((b[0]*r+b[1])*r+b[2])*r+b[3])*r+b[4])*r+1)
    else:
        q = math.sqrt(-2 * math.log(1 - p))
        return -(((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5]) / \
                ((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1)


# ---------------------------------------------------------------------------
# Sample-size calculations
# ---------------------------------------------------------------------------

def sample_size_proportions(
    baseline_rate: float,
    mde_relative_pct: float,
    alpha: float = 0.05,
    power: float = 0.80,
    two_tailed: bool = True,
    n_comparisons: int = 1,
    correction: str = "bonferroni",
) -> Dict[str, Any]:
    """
    Sample size per variant for a proportion (conversion-rate) test.

    baseline_rate: e.g. 5.0 for 5%
    mde_relative_pct: minimum detectable effect as relative % change (e.g. 10 = 10% relative lift)
    """
    p1 = baseline_rate / 100.0
    lift = mde_relative_pct / 100.0
    p2 = p1 * (1 + lift)
    abs_diff = abs(p2 - p1)

    if abs_diff == 0:
        return {"error": "MDE is zero — no test needed"}

    adjusted_alpha = _adjust_alpha(alpha, n_comparisons, correction)
    z_alpha = _norm_ppf(1 - adjusted_alpha / (2 if two_tailed else 1))
    z_beta = _norm_ppf(power)

    pooled_p = (p1 + p2) / 2
    n = ((z_alpha * math.sqrt(2 * pooled_p * (1 - pooled_p)) +
          z_beta * math.sqrt(p1 * (1 - p1) + p2 * (1 - p2))) / abs_diff) ** 2

    n_per_variant = math.ceil(n)
    total_n = n_per_variant * (n_comparisons + 1)

    return {
        "test_type": "proportions",
        "baseline_rate_pct": baseline_rate,
        "variant_rate_pct": round(p2 * 100, 3),
        "absolute_diff_pct": round(abs_diff * 100, 3),
        "relative_mde_pct": mde_relative_pct,
        "alpha": alpha,
        "adjusted_alpha": round(adjusted_alpha, 6),
        "power": power,
        "two_tailed": two_tailed,
        "n_comparisons": n_comparisons,
        "correction": correction if n_comparisons > 1 else "none",
        "sample_per_variant": n_per_variant,
        "total_sample": total_n,
        "n_variants": n_comparisons + 1,
    }


def sample_size_means(
    baseline_mean: float,
    baseline_std: float,
    mde_relative_pct: float,
    alpha: float = 0.05,
    power: float = 0.80,
    two_tailed: bool = True,
    n_comparisons: int = 1,
    correction: str = "bonferroni",
) -> Dict[str, Any]:
    """Sample size per variant for a continuous-metric (means) test."""
    lift = mde_relative_pct / 100.0
    abs_diff = abs(baseline_mean * lift)

    if abs_diff == 0:
        return {"error": "MDE is zero — no test needed"}

    adjusted_alpha = _adjust_alpha(alpha, n_comparisons, correction)
    z_alpha = _norm_ppf(1 - adjusted_alpha / (2 if two_tailed else 1))
    z_beta = _norm_ppf(power)

    n = 2 * ((z_alpha + z_beta) * baseline_std / abs_diff) ** 2
    n_per_variant = math.ceil(n)
    total_n = n_per_variant * (n_comparisons + 1)

    return {
        "test_type": "means",
        "baseline_mean": baseline_mean,
        "baseline_std": baseline_std,
        "target_mean": round(baseline_mean * (1 + lift), 3),
        "absolute_diff": round(abs_diff, 3),
        "relative_mde_pct": mde_relative_pct,
        "alpha": alpha,
        "adjusted_alpha": round(adjusted_alpha, 6),
        "power": power,
        "two_tailed": two_tailed,
        "n_comparisons": n_comparisons,
        "correction": correction if n_comparisons > 1 else "none",
        "sample_per_variant": n_per_variant,
        "total_sample": total_n,
        "n_variants": n_comparisons + 1,
    }


def _adjust_alpha(alpha: float, n_comparisons: int, method: str) -> float:
    if n_comparisons <= 1:
        return alpha
    if method == "sidak":
        return 1 - (1 - alpha) ** (1 / n_comparisons)
    return alpha / n_comparisons  # bonferroni


def estimate_duration(
    total_sample: int,
    daily_traffic: int,
    traffic_pct: float = 100.0,
) -> Dict[str, Any]:
    """Estimate test duration from daily traffic."""
    eligible_daily = daily_traffic * traffic_pct / 100.0
    if eligible_daily <= 0:
        return {"days": float("inf"), "weeks": float("inf"), "eligible_daily": 0}

    days = math.ceil(total_sample / eligible_daily)
    weeks = round(days / 7, 1)

    return {
        "daily_traffic": daily_traffic,
        "traffic_pct": traffic_pct,
        "eligible_daily": int(eligible_daily),
        "days": days,
        "weeks": weeks,
        "feasible": days <= 90,
    }


def post_hoc_power(
    baseline_rate: float,
    variant_rate: float,
    sample_size: int,
    alpha: float = 0.05,
    two_tailed: bool = True,
) -> Dict[str, Any]:
    """Calculate achieved power from observed results."""
    p1 = baseline_rate / 100.0
    p2 = variant_rate / 100.0
    abs_diff = abs(p2 - p1)

    if abs_diff == 0:
        return {"power": 0, "interpretation": "No difference observed"}

    z_alpha = _norm_ppf(1 - alpha / (2 if two_tailed else 1))
    pooled_p = (p1 + p2) / 2
    se = math.sqrt(p1 * (1 - p1) / sample_size + p2 * (1 - p2) / sample_size)
    se_pooled = math.sqrt(2 * pooled_p * (1 - pooled_p) / sample_size)

    z_effect = abs_diff / se
    power_val = _norm_cdf(z_effect - z_alpha)

    # Significance
    z_test = abs_diff / se_pooled
    p_value = 2 * (1 - _norm_cdf(abs(z_test))) if two_tailed else 1 - _norm_cdf(abs(z_test))

    relative_lift = (p2 - p1) / p1 * 100 if p1 > 0 else 0

    if power_val >= 0.8:
        interp = "Well-powered — results are reliable"
    elif power_val >= 0.5:
        interp = "Under-powered — results are directional but not conclusive"
    else:
        interp = "Severely under-powered — cannot trust results"

    return {
        "baseline_rate_pct": baseline_rate,
        "variant_rate_pct": variant_rate,
        "relative_lift_pct": round(relative_lift, 2),
        "sample_per_variant": sample_size,
        "alpha": alpha,
        "achieved_power": round(power_val, 3),
        "z_statistic": round(z_test, 3),
        "p_value": round(p_value, 5),
        "significant": p_value < alpha,
        "interpretation": interp,
    }


def sensitivity_table(
    baseline_rate: float,
    alpha: float = 0.05,
    power: float = 0.80,
    mde_range: Optional[List[float]] = None,
) -> List[Dict[str, Any]]:
    """Generate a sensitivity table across different MDEs."""
    if mde_range is None:
        mde_range = [3, 5, 8, 10, 15, 20, 25, 30, 50]

    rows = []
    for mde in mde_range:
        result = sample_size_proportions(baseline_rate, mde, alpha, power)
        if "error" in result:
            continue
        rows.append({
            "mde_pct": mde,
            "sample_per_variant": result["sample_per_variant"],
            "total_sample": result["total_sample"],
        })
    return rows


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def _col(fieldnames: List[str], *aliases: str) -> Optional[str]:
    lower_map = {f.lower().strip(): f for f in fieldnames}
    for alias in aliases:
        if alias.lower().strip() in lower_map:
            return lower_map[alias.lower().strip()]
    return None


def load_csv(path: str) -> List[Dict[str, Any]]:
    """Load batch of test configs from CSV."""
    tests: List[Dict[str, Any]] = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fields = reader.fieldnames or []

        c_name = _col(fields, "test_name", "name", "test", "experiment")
        c_baseline = _col(fields, "baseline_rate", "baseline", "control_rate", "base_rate")
        c_mde = _col(fields, "mde_pct", "mde", "min_detectable_effect", "lift")
        c_alpha = _col(fields, "significance", "alpha", "sig_level")
        c_power = _col(fields, "power", "statistical_power")
        c_traffic = _col(fields, "daily_traffic", "traffic", "daily_visitors")
        c_variants = _col(fields, "variants", "n_variants", "num_variants")

        for row in reader:
            name = row.get(c_name or "test_name", "").strip()
            if not name:
                continue

            def _num(col: Optional[str], default: float) -> float:
                if not col:
                    return default
                raw = row.get(col, "").strip().rstrip("%")
                try:
                    return float(raw) if raw else default
                except ValueError:
                    return default

            tests.append({
                "name": name,
                "baseline_rate": _num(c_baseline, 5.0),
                "mde_pct": _num(c_mde, 10.0),
                "alpha": _num(c_alpha, 0.05),
                "power": _num(c_power, 80) / 100 if _num(c_power, 80) > 1 else _num(c_power, 0.8),
                "daily_traffic": int(_num(c_traffic, 0)),
                "variants": int(_num(c_variants, 2)),
            })

    return tests


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def _fmt_num(n: int) -> str:
    if n >= 1_000_000:
        return f"{n / 1_000_000:,.1f}M"
    elif n >= 1_000:
        return f"{n / 1_000:,.1f}K"
    else:
        return f"{n:,}"


def _bar(value: float, max_val: float, width: int = 25) -> str:
    if max_val <= 0:
        return "░" * width
    ratio = min(1.0, max(0.0, value / max_val))
    filled = int(ratio * width)
    return "█" * filled + "░" * (width - filled)


def print_report(
    results: List[Tuple[str, Dict[str, Any]]],
    durations: List[Tuple[str, Optional[Dict[str, Any]]]],
    post_hocs: List[Tuple[str, Dict[str, Any]]],
    sens_tables: List[Tuple[str, List[Dict[str, Any]]]],
) -> None:
    """Pretty-print A/B test calculations."""
    print("\n" + "=" * 78)
    print("🧪 A/B TEST SAMPLE-SIZE CALCULATOR")
    print("=" * 78)

    for (name, result), (_, dur) in zip(results, durations):
        title = name if name else "TEST CONFIGURATION"
        print(f"\n{'─'*78}")
        print(f"\n📋 {title.upper()}")

        if "error" in result:
            print(f"\n   ❌ {result['error']}")
            continue

        if result["test_type"] == "proportions":
            print(f"\n   Baseline conversion:  {result['baseline_rate_pct']:.2f}%")
            print(f"   Expected variant:     {result['variant_rate_pct']:.2f}%")
            print(f"   Absolute difference:  {result['absolute_diff_pct']:.3f} pp")
            print(f"   Relative MDE:         {result['relative_mde_pct']:.1f}%")
        else:
            print(f"\n   Baseline mean:        {result['baseline_mean']:.2f}")
            print(f"   Target mean:          {result['target_mean']:.2f}")
            print(f"   Baseline std dev:     {result['baseline_std']:.2f}")
            print(f"   Absolute difference:  {result['absolute_diff']:.3f}")
            print(f"   Relative MDE:         {result['relative_mde_pct']:.1f}%")

        print(f"\n   Significance (α):     {result['alpha']}", end="")
        if result["n_comparisons"] > 1:
            print(f"  (adjusted: {result['adjusted_alpha']:.4f}, {result['correction']})")
        else:
            print()
        print(f"   Power (1−β):          {result['power']*100:.0f}%")
        print(f"   Tails:                {'Two-tailed' if result['two_tailed'] else 'One-tailed'}")
        print(f"   Variants:             {result['n_variants']} ({result['n_comparisons']} treatment{'s' if result['n_comparisons'] > 1 else ''} + 1 control)")

        print(f"\n   📊 SAMPLE SIZE:")
        print(f"   Per variant:          {result['sample_per_variant']:>12,}")
        print(f"   Total (all variants): {result['total_sample']:>12,}")

        if dur:
            print(f"\n   ⏱️  DURATION ESTIMATE:")
            print(f"   Daily traffic:        {dur['daily_traffic']:>12,}")
            print(f"   Eligible ({dur['traffic_pct']:.0f}%):      {dur['eligible_daily']:>12,}")
            print(f"   Estimated duration:   {dur['days']:>9} days ({dur['weeks']:.1f} weeks)")

            if dur["feasible"]:
                print(f"   Status:               🟢 Feasible (≤90 days)")
            else:
                print(f"   Status:               🔴 Long test (>{dur['days']} days) — consider larger MDE or more traffic")

        # Visual sizing
        sizes = [
            ("Per variant", result["sample_per_variant"]),
            ("Total", result["total_sample"]),
        ]
        max_size = result["total_sample"]
        print(f"\n   Scale:")
        for label, size in sizes:
            print(f"   {label:<14} {_bar(size, max_size)} {_fmt_num(size)}")

    # Post-hoc results
    for name, ph in post_hocs:
        print(f"\n{'─'*78}")
        title = name if name else "POST-HOC ANALYSIS"
        print(f"\n🔍 {title.upper()}")
        print(f"\n   Control rate:      {ph['baseline_rate_pct']:.2f}%")
        print(f"   Variant rate:      {ph['variant_rate_pct']:.2f}%")
        print(f"   Relative lift:     {ph['relative_lift_pct']:+.2f}%")
        print(f"   Sample per variant: {ph['sample_per_variant']:,}")
        print(f"\n   Z-statistic:       {ph['z_statistic']:.3f}")
        print(f"   P-value:           {ph['p_value']:.5f}  {'✅ Significant' if ph['significant'] else '❌ Not significant'}")
        print(f"   Achieved power:    {ph['achieved_power']*100:.1f}%")
        print(f"   Verdict:           {ph['interpretation']}")

    # Sensitivity tables
    for name, table in sens_tables:
        if not table:
            continue
        print(f"\n{'─'*78}")
        title = name if name else "SENSITIVITY TABLE"
        print(f"\n📐 {title.upper()}")
        print(f"\n   {'MDE':>6} {'Per Variant':>14} {'Total':>14}")
        print(f"   {'─'*6} {'─'*14} {'─'*14}")

        max_total = table[0]["total_sample"] if table else 1
        for row in table:
            marker = " ◀" if row.get("selected") else ""
            print(f"   {row['mde_pct']:>5.0f}% {row['sample_per_variant']:>14,} {row['total_sample']:>14,}{marker}")

    # Guidance
    print(f"\n{'─'*78}")
    print(f"\n💡 BEST PRACTICES:")
    print(f"   • Don't peek at results — commit to sample size before starting")
    print(f"   • 80% power is standard; 90% for high-stakes decisions")
    print(f"   • α = 0.05 is conventional; use 0.01 for critical features")
    print(f"   • If test runs >4 weeks, consider seasonal and novelty effects")
    print(f"   • MDE should reflect the smallest change worth acting on")
    print(f"   • For >2 variants, always apply multiple-comparison correction")
    print("\n" + "=" * 78)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Calculate A/B test sample sizes, durations, and power. "
                    "Supports conversion-rate and continuous-metric tests.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --baseline-rate 5.0 --mde 10 --significance 0.05 --power 80
  %(prog)s --baseline-rate 3.2 --mde 15 --daily-traffic 50000
  %(prog)s --baseline-rate 5.0 --variant-rate 5.6 --sample-size 8000 --post-hoc
  %(prog)s --csv tests.csv
        """,
    )

    # Proportions
    parser.add_argument("--baseline-rate", type=float,
                        help="Baseline conversion rate (%%), e.g. 5.0 for 5%%")
    parser.add_argument("--mde", type=float,
                        help="Minimum detectable effect as relative %% (e.g. 10 = 10%% relative lift)")

    # Means
    parser.add_argument("--baseline-mean", type=float,
                        help="Baseline metric mean (for continuous metrics)")
    parser.add_argument("--baseline-std", type=float,
                        help="Baseline metric standard deviation")

    # Test params
    parser.add_argument("--significance", "--alpha", type=float, default=0.05,
                        help="Significance level (default: 0.05)")
    parser.add_argument("--power", type=float, default=80,
                        help="Statistical power %% (default: 80)")
    parser.add_argument("--one-tailed", action="store_true",
                        help="One-tailed test (default: two-tailed)")
    parser.add_argument("--variants", type=int, default=2,
                        help="Total variants including control (default: 2)")
    parser.add_argument("--correction", type=str, default="bonferroni",
                        choices=["bonferroni", "sidak"],
                        help="Multiple-comparison correction method (default: bonferroni)")

    # Duration
    parser.add_argument("--daily-traffic", type=int,
                        help="Daily traffic / visitors for duration estimation")
    parser.add_argument("--traffic-pct", type=float, default=100,
                        help="%% of traffic eligible for test (default: 100)")

    # Post-hoc
    parser.add_argument("--variant-rate", type=float,
                        help="Observed variant rate %% (for post-hoc analysis)")
    parser.add_argument("--sample-size", type=int,
                        help="Observed sample size per variant (for post-hoc)")
    parser.add_argument("--post-hoc", action="store_true",
                        help="Run post-hoc power analysis")

    # Sensitivity
    parser.add_argument("--sensitivity", action="store_true",
                        help="Show sensitivity table across MDEs")

    # Batch
    parser.add_argument("--csv", "-c", type=str, help="CSV file with batch test configs")
    parser.add_argument("--output", "-o", type=str, help="Write JSON results to file")
    args = parser.parse_args()

    power = args.power / 100 if args.power > 1 else args.power
    two_tailed = not args.one_tailed
    n_comparisons = max(1, args.variants - 1)

    results: List[Tuple[str, Dict[str, Any]]] = []
    durations: List[Tuple[str, Optional[Dict[str, Any]]]] = []
    post_hocs: List[Tuple[str, Dict[str, Any]]] = []
    sens_tables: List[Tuple[str, List[Dict[str, Any]]]] = []

    # Batch CSV
    if args.csv:
        try:
            tests = load_csv(args.csv)
        except Exception as e:
            print(f"Error loading CSV: {e}", file=sys.stderr)
            return 1

        for t in tests:
            n_comp = max(1, t["variants"] - 1)
            r = sample_size_proportions(
                t["baseline_rate"], t["mde_pct"],
                t["alpha"], t["power"], two_tailed, n_comp, args.correction,
            )
            results.append((t["name"], r))

            dur = None
            if t["daily_traffic"] > 0 and "total_sample" in r:
                dur = estimate_duration(r["total_sample"], t["daily_traffic"])
            durations.append((t["name"], dur))

    # Post-hoc mode
    elif args.post_hoc and args.baseline_rate and args.variant_rate and args.sample_size:
        ph = post_hoc_power(
            args.baseline_rate, args.variant_rate,
            args.sample_size, args.significance, two_tailed,
        )
        post_hocs.append(("", ph))

    # Sample-size mode
    elif args.baseline_rate and args.mde:
        r = sample_size_proportions(
            args.baseline_rate, args.mde,
            args.significance, power, two_tailed, n_comparisons, args.correction,
        )
        results.append(("", r))

        dur = None
        if args.daily_traffic and "total_sample" in r:
            dur = estimate_duration(r["total_sample"], args.daily_traffic, args.traffic_pct)
        durations.append(("", dur))

        if args.sensitivity:
            st = sensitivity_table(args.baseline_rate, args.significance, power)
            for row in st:
                if row["mde_pct"] == args.mde:
                    row["selected"] = True
            sens_tables.append(("Sensitivity (baseline = {:.1f}%)".format(args.baseline_rate), st))

    elif args.baseline_mean is not None and args.baseline_std and args.mde:
        r = sample_size_means(
            args.baseline_mean, args.baseline_std, args.mde,
            args.significance, power, two_tailed, n_comparisons, args.correction,
        )
        results.append(("", r))

        dur = None
        if args.daily_traffic and "total_sample" in r:
            dur = estimate_duration(r["total_sample"], args.daily_traffic, args.traffic_pct)
        durations.append(("", dur))

    else:
        print("Error: provide --baseline-rate + --mde, --baseline-mean + --baseline-std + --mde, "
              "or --post-hoc with observed rates.", file=sys.stderr)
        parser.print_help(sys.stderr)
        return 1

    # Report
    print_report(results, durations, post_hocs, sens_tables)

    # JSON output
    if args.output:
        report: Dict[str, Any] = {}
        if results:
            report["calculations"] = [{"name": n, **r} for n, r in results]
        if durations:
            report["durations"] = [{"name": n, **(d or {})} for n, d in durations if d]
        if post_hocs:
            report["post_hoc"] = [{"name": n, **ph} for n, ph in post_hocs]
        if sens_tables:
            report["sensitivity"] = [{"name": n, "rows": rows} for n, rows in sens_tables]
        with open(args.output, "w") as f:
            json.dump(report, f, indent=2)
        print(f"\n📁 Results saved to {args.output}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
