#!/usr/bin/env python3
"""
Experiment Result Interpreter

Interpret A/B test results after the experiment has run: observed lift, confidence
interval for the difference, p-value, and a plain-language verdict (significant or not).
Optionally report how much sample would have been needed for 80% power. Complements
ab-test-calculator (sample size) and experiment-duration-calculator (duration).

Usage:
    # Proportions (e.g. conversion rate): baseline 5%%, variant 5.6%%, 8000 per arm
    python experiment-result-interpreter.py \\
        --baseline 5.0 --variant 5.6 --n 8000

    # Unequal sample sizes
    python experiment-result-interpreter.py --baseline 5.0 --variant 5.6 --n-baseline 7500 --n-variant 8200

    # Custom confidence level and power reference
    python experiment-result-interpreter.py --baseline 5.0 --variant 5.6 --n 8000 --confidence 0.90 --show-required-n

    # Means (e.g. revenue per user): baseline mean 48.5, variant 51.2, std 25, n 5000
    python experiment-result-interpreter.py --means --baseline-mean 48.5 --variant-mean 51.2 --std 25 --n 5000

    # Export JSON
    python experiment-result-interpreter.py --baseline 5.0 --variant 5.6 --n 8000 --output result.json

Requirements:
    None (stdlib only).
"""

import argparse
import json
import math
import sys
from typing import Any, Dict, Optional, Tuple


# ---------------------------------------------------------------------------
# Normal distribution (stdlib-only)
# ---------------------------------------------------------------------------

def _norm_cdf(x: float) -> float:
    """Standard normal CDF (Abramowitz & Stegun approximation)."""
    sign = 1 if x >= 0 else -1
    x = abs(x)
    t = 1.0 / (1.0 + 0.2316419 * x)
    b1, b2, b3, b4, b5 = 0.319381530, -0.356563782, 1.781477937, -1.821255978, 1.330274429
    poly = t * (b1 + t * (b2 + t * (b3 + t * (b4 + t * b5))))
    pdf = math.exp(-0.5 * x * x) / math.sqrt(2 * math.pi)
    cdf = 1.0 - pdf * poly
    return 0.5 + sign * (cdf - 0.5)


def _norm_ppf(p: float) -> float:
    """Inverse standard normal (percent-point function)."""
    if p <= 0:
        return -10.0
    if p >= 1:
        return 10.0
    if p == 0.5:
        return 0.0
    if p < 0.5:
        return -_norm_ppf(1 - p)
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
    p_low, p_high = 0.02425, 1 - 0.02425
    if p < p_low:
        q = math.sqrt(-2 * math.log(p))
        return (((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5]) / ((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1)
    elif p <= p_high:
        q, r = p - 0.5, (p - 0.5) ** 2
        return (((((a[0]*r+a[1])*r+a[2])*r+a[3])*r+a[4])*r+a[5])*q / (((((b[0]*r+b[1])*r+b[2])*r+b[3])*r+b[4])*r+1)
    else:
        q = math.sqrt(-2 * math.log(1 - p))
        return -(((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5]) / ((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1)


# ---------------------------------------------------------------------------
# Proportions: two-sample z-test and CI
# ---------------------------------------------------------------------------

def interpret_proportions(
    baseline_pct: float,
    variant_pct: float,
    n_baseline: int,
    n_variant: int,
    alpha: float = 0.05,
    confidence: float = 0.95,
    two_tailed: bool = True,
) -> Dict[str, Any]:
    """
    Interpret A/B result for conversion (proportion). Returns lift, CI for difference,
    p-value, significant, and plain-language verdict.
    """
    p1 = baseline_pct / 100.0
    p2 = variant_pct / 100.0
    diff = p2 - p1
    if n_baseline <= 0 or n_variant <= 0:
        return {"error": "Sample sizes must be positive"}

    # SE of difference (unpooled)
    se_diff = math.sqrt(p1 * (1 - p1) / n_baseline + p2 * (1 - p2) / n_variant)
    if se_diff <= 0:
        return {"error": "Could not compute standard error"}

    # Confidence interval for difference (pp)
    z_conf = _norm_ppf(1 - (1 - confidence) / 2)
    margin = z_conf * se_diff
    ci_low_pp = (diff - margin) * 100
    ci_high_pp = (diff + margin) * 100

    # Two-sample z-test (pooled SE under H0: p1 = p2)
    pooled_p = (p1 * n_baseline + p2 * n_variant) / (n_baseline + n_variant)
    se_pooled = math.sqrt(pooled_p * (1 - pooled_p) * (1 / n_baseline + 1 / n_variant))
    if se_pooled <= 0:
        z_stat = 0.0
        p_value = 1.0
    else:
        z_stat = diff / se_pooled
        p_value = 2 * (1 - _norm_cdf(abs(z_stat))) if two_tailed else 1 - _norm_cdf(abs(z_stat))

    significant = p_value < alpha
    relative_lift_pct = (diff / p1 * 100) if p1 > 0 else 0

    # Verdict
    if significant:
        direction = "higher" if diff > 0 else "lower"
        verdict = (
            f"The variant is statistically significantly {direction} than control "
            f"(p = {p_value:.4f}). Observed lift: {relative_lift_pct:+.2f}%."
        )
    else:
        verdict = (
            f"The result is not statistically significant (p = {p_value:.4f}). "
            f"The observed lift was {relative_lift_pct:+.2f}%; consider a larger sample or smaller effect."
        )

    return {
        "metric_type": "proportion",
        "baseline_pct": round(baseline_pct, 4),
        "variant_pct": round(variant_pct, 4),
        "n_baseline": n_baseline,
        "n_variant": n_variant,
        "absolute_diff_pp": round(diff * 100, 4),
        "relative_lift_pct": round(relative_lift_pct, 2),
        "ci_low_pp": round(ci_low_pp, 4),
        "ci_high_pp": round(ci_high_pp, 4),
        "confidence": confidence,
        "z_statistic": round(z_stat, 4),
        "p_value": round(p_value, 6),
        "significant": significant,
        "alpha": alpha,
        "verdict": verdict,
    }


def required_n_for_power_proportions(
    p1: float,
    p2: float,
    alpha: float = 0.05,
    power: float = 0.80,
    two_tailed: bool = True,
) -> int:
    """Sample size per variant to achieve given power for observed effect (p1, p2 as decimals)."""
    abs_diff = abs(p2 - p1)
    if abs_diff <= 0:
        return 0
    z_alpha = _norm_ppf(1 - alpha / (2 if two_tailed else 1))
    z_beta = _norm_ppf(power)
    pooled = (p1 + p2) / 2
    n = 2 * (
        (z_alpha * math.sqrt(2 * pooled * (1 - pooled)) +
         z_beta * math.sqrt(p1 * (1 - p1) + p2 * (1 - p2)))
        / abs_diff
    ) ** 2
    return max(1, math.ceil(n))


# ---------------------------------------------------------------------------
# Means: two-sample z-test and CI
# ---------------------------------------------------------------------------

def interpret_means(
    baseline_mean: float,
    variant_mean: float,
    n_baseline: int,
    n_variant: int,
    std_baseline: float,
    std_variant: Optional[float] = None,
    alpha: float = 0.05,
    confidence: float = 0.95,
    two_tailed: bool = True,
) -> Dict[str, Any]:
    """Interpret A/B result for a continuous metric (means). Uses pooled std if only one given."""
    if std_variant is None:
        std_variant = std_baseline
    diff = variant_mean - baseline_mean
    if n_baseline <= 0 or n_variant <= 0:
        return {"error": "Sample sizes must be positive"}
    se_diff = math.sqrt(std_baseline**2 / n_baseline + std_variant**2 / n_variant)
    if se_diff <= 0:
        return {"error": "Could not compute standard error"}

    z_conf = _norm_ppf(1 - (1 - confidence) / 2)
    margin = z_conf * se_diff
    ci_low = diff - margin
    ci_high = diff + margin

    z_stat = diff / se_diff
    p_value = 2 * (1 - _norm_cdf(abs(z_stat))) if two_tailed else 1 - _norm_cdf(abs(z_stat))
    significant = p_value < alpha
    relative_lift_pct = (diff / baseline_mean * 100) if baseline_mean != 0 else 0

    if significant:
        direction = "higher" if diff > 0 else "lower"
        verdict = (
            f"The variant is statistically significantly {direction} than control "
            f"(p = {p_value:.4f}). Observed lift: {relative_lift_pct:+.2f}%."
        )
    else:
        verdict = (
            f"The result is not statistically significant (p = {p_value:.4f}). "
            f"Observed difference: {diff:+.4f}; consider larger sample or smaller effect."
        )

    return {
        "metric_type": "mean",
        "baseline_mean": baseline_mean,
        "variant_mean": variant_mean,
        "n_baseline": n_baseline,
        "n_variant": n_variant,
        "std_baseline": std_baseline,
        "std_variant": std_variant,
        "absolute_diff": round(diff, 4),
        "relative_lift_pct": round(relative_lift_pct, 2),
        "ci_low": round(ci_low, 4),
        "ci_high": round(ci_high, 4),
        "confidence": confidence,
        "z_statistic": round(z_stat, 4),
        "p_value": round(p_value, 6),
        "significant": significant,
        "alpha": alpha,
        "verdict": verdict,
    }


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def print_report(result: Dict[str, Any], show_required_n: bool = False) -> None:
    """Pretty-print interpretation."""
    if result.get("error"):
        print(f"\n   Error: {result['error']}\n", file=sys.stderr)
        return

    print("\n" + "=" * 70)
    print("🔬 EXPERIMENT RESULT INTERPRETER")
    print("=" * 70)

    if result["metric_type"] == "proportion":
        print(f"\n   Baseline (control):  {result['baseline_pct']:.2f}%  (n = {result['n_baseline']:,})")
        print(f"   Variant:             {result['variant_pct']:.2f}%  (n = {result['n_variant']:,})")
        print(f"   Absolute difference: {result['absolute_diff_pp']:+.2f} pp")
        print(f"   Relative lift:       {result['relative_lift_pct']:+.2f}%")
        print(f"   {int(result['confidence']*100)}% CI (diff):      [{result['ci_low_pp']:+.2f}, {result['ci_high_pp']:+.2f}] pp")
    else:
        print(f"\n   Baseline (control):  mean = {result['baseline_mean']:.2f}  (n = {result['n_baseline']:,})")
        print(f"   Variant:             mean = {result['variant_mean']:.2f}  (n = {result['n_variant']:,})")
        print(f"   Absolute difference: {result['absolute_diff']:+.4f}")
        print(f"   Relative lift:       {result['relative_lift_pct']:+.2f}%")
        print(f"   {int(result['confidence']*100)}% CI (diff):      [{result['ci_low']:.4f}, {result['ci_high']:.4f}]")

    p_val = result["p_value"]
    p_str = "< 0.0001" if p_val < 0.0001 else f"{p_val:.4f}"
    print(f"\n   z-statistic:          {result['z_statistic']:.3f}")
    print(f"   p-value:             {p_str}")
    print(f"   Significant (α={result['alpha']}):  {'Yes' if result['significant'] else 'No'}")

    if show_required_n and result["metric_type"] == "proportion":
        p1 = result["baseline_pct"] / 100.0
        p2 = result["variant_pct"] / 100.0
        n_req = required_n_for_power_proportions(p1, p2, result["alpha"], 0.80, True)
        print(f"\n   For 80% power at this effect size: ~{n_req:,} per variant")

    print(f"\n   📋 Verdict: {result['verdict']}\n")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Interpret A/B test results: lift, CI, p-value, verdict.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--baseline", type=float, help="Baseline rate (pct, e.g. 5.0 for 5%%)")
    parser.add_argument("--variant", type=float, help="Variant rate (pct)")
    parser.add_argument("--n", type=int, help="Sample size per variant (equal split)")
    parser.add_argument("--n-baseline", type=int, help="Baseline sample size (if unequal)")
    parser.add_argument("--n-variant", type=int, help="Variant sample size (if unequal)")
    parser.add_argument("--confidence", type=float, default=0.95, help="Confidence level (default: 0.95)")
    parser.add_argument("--alpha", type=float, default=0.05, help="Significance level (default: 0.05)")
    parser.add_argument("--show-required-n", action="store_true", help="Show required n per variant for 80%% power")
    parser.add_argument("--output", "-o", metavar="FILE", help="Write JSON to FILE")

    # Means
    parser.add_argument("--means", action="store_true", help="Interpret as means (revenue, etc.)")
    parser.add_argument("--baseline-mean", type=float, help="Baseline mean (for --means)")
    parser.add_argument("--variant-mean", type=float, help="Variant mean (for --means)")
    parser.add_argument("--std", type=float, help="Std dev (pooled or baseline for --means)")

    args = parser.parse_args()

    if args.means:
        if args.baseline_mean is None or args.variant_mean is None or args.std is None:
            print("For --means need --baseline-mean, --variant-mean, --std.", file=sys.stderr)
            return 1
        n_b = args.n_baseline or args.n
        n_v = args.n_variant or args.n
        if not n_b or not n_v:
            print("For --means need --n or --n-baseline and --n-variant.", file=sys.stderr)
            return 1
        result = interpret_means(
            args.baseline_mean, args.variant_mean,
            n_b, n_v, args.std,
            alpha=args.alpha, confidence=args.confidence,
        )
    else:
        if args.baseline is None or args.variant is None:
            print("Need --baseline and --variant (or --means with --baseline-mean, --variant-mean).", file=sys.stderr)
            return 1
        n_b = args.n_baseline or args.n
        n_v = args.n_variant or args.n
        if not n_b or not n_v:
            print("Need --n or --n-baseline and --n-variant.", file=sys.stderr)
            return 1
        result = interpret_proportions(
            args.baseline, args.variant, n_b, n_v,
            alpha=args.alpha, confidence=args.confidence,
        )

    if result.get("error"):
        print(result["error"], file=sys.stderr)
        return 1

    print_report(result, show_required_n=args.show_required_n)

    if args.output:
        out = {k: v for k, v in result.items() if k != "verdict" or True}
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(out, f, indent=2)
        print(f"Wrote JSON to {args.output}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
