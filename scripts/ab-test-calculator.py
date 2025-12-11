#!/usr/bin/env python3
"""
A/B Test Sample Size and Significance Calculator

A practical tool for Product Managers to:
1. Calculate required sample sizes for A/B tests
2. Analyze test results for statistical significance
3. Generate reports for stakeholders

Usage:
    python ab-test-calculator.py

Requirements:
    pip install scipy numpy
"""

import math
from scipy import stats
from typing import Tuple, Optional
import argparse


def calculate_sample_size(
    baseline_rate: float,
    minimum_detectable_effect: float,
    alpha: float = 0.05,
    power: float = 0.80,
    two_tailed: bool = True
) -> int:
    """
    Calculate required sample size per variant for an A/B test.
    
    Args:
        baseline_rate: Current conversion rate (e.g., 0.10 for 10%)
        minimum_detectable_effect: Relative change to detect (e.g., 0.10 for 10% lift)
        alpha: Significance level (default 0.05 for 95% confidence)
        power: Statistical power (default 0.80 for 80% power)
        two_tailed: Whether to use two-tailed test (default True)
    
    Returns:
        Required sample size per variant
    """
    # Calculate the expected rate for variant
    p1 = baseline_rate
    p2 = baseline_rate * (1 + minimum_detectable_effect)
    
    # Pooled probability
    p_pooled = (p1 + p2) / 2
    
    # Z-scores
    if two_tailed:
        z_alpha = stats.norm.ppf(1 - alpha / 2)
    else:
        z_alpha = stats.norm.ppf(1 - alpha)
    z_beta = stats.norm.ppf(power)
    
    # Sample size formula
    numerator = (z_alpha * math.sqrt(2 * p_pooled * (1 - p_pooled)) + 
                 z_beta * math.sqrt(p1 * (1 - p1) + p2 * (1 - p2))) ** 2
    denominator = (p2 - p1) ** 2
    
    n = math.ceil(numerator / denominator)
    
    return n


def analyze_test_results(
    control_conversions: int,
    control_visitors: int,
    variant_conversions: int,
    variant_visitors: int,
    alpha: float = 0.05
) -> dict:
    """
    Analyze A/B test results for statistical significance.
    
    Args:
        control_conversions: Number of conversions in control
        control_visitors: Number of visitors in control
        variant_conversions: Number of conversions in variant
        variant_visitors: Number of visitors in variant
        alpha: Significance level
    
    Returns:
        Dictionary with analysis results
    """
    # Conversion rates
    control_rate = control_conversions / control_visitors
    variant_rate = variant_conversions / variant_visitors
    
    # Relative lift
    if control_rate > 0:
        relative_lift = (variant_rate - control_rate) / control_rate
    else:
        relative_lift = float('inf') if variant_rate > 0 else 0
    
    # Pooled probability and standard error
    pooled_rate = (control_conversions + variant_conversions) / (control_visitors + variant_visitors)
    se = math.sqrt(pooled_rate * (1 - pooled_rate) * (1/control_visitors + 1/variant_visitors))
    
    # Z-score and p-value
    if se > 0:
        z_score = (variant_rate - control_rate) / se
        p_value = 2 * (1 - stats.norm.cdf(abs(z_score)))  # Two-tailed
    else:
        z_score = 0
        p_value = 1.0
    
    # Confidence interval for the difference
    z_critical = stats.norm.ppf(1 - alpha / 2)
    diff = variant_rate - control_rate
    ci_lower = diff - z_critical * se
    ci_upper = diff + z_critical * se
    
    # Statistical significance
    is_significant = p_value < alpha
    
    return {
        'control_rate': control_rate,
        'variant_rate': variant_rate,
        'absolute_difference': diff,
        'relative_lift': relative_lift,
        'z_score': z_score,
        'p_value': p_value,
        'confidence_interval': (ci_lower, ci_upper),
        'is_significant': is_significant,
        'confidence_level': 1 - alpha
    }


def calculate_test_duration(
    sample_size_per_variant: int,
    daily_visitors: int,
    traffic_allocation: float = 1.0,
    num_variants: int = 2
) -> int:
    """
    Calculate how long to run the test.
    
    Args:
        sample_size_per_variant: Required sample size per variant
        daily_visitors: Average daily visitors
        traffic_allocation: Fraction of traffic in test (default 1.0)
        num_variants: Number of variants including control (default 2)
    
    Returns:
        Number of days to run the test
    """
    daily_per_variant = (daily_visitors * traffic_allocation) / num_variants
    days = math.ceil(sample_size_per_variant / daily_per_variant)
    return days


def format_percentage(value: float) -> str:
    """Format a decimal as a percentage string."""
    return f"{value * 100:.2f}%"


def print_sample_size_report(
    baseline_rate: float,
    mde: float,
    alpha: float,
    power: float,
    daily_visitors: Optional[int] = None
):
    """Print a formatted sample size calculation report."""
    
    sample_size = calculate_sample_size(baseline_rate, mde, alpha, power)
    
    print("\n" + "=" * 60)
    print("📊 A/B TEST SAMPLE SIZE CALCULATION")
    print("=" * 60)
    
    print("\n📋 INPUT PARAMETERS:")
    print(f"   • Baseline conversion rate: {format_percentage(baseline_rate)}")
    print(f"   • Minimum detectable effect: {format_percentage(mde)} relative lift")
    print(f"   • Expected variant rate: {format_percentage(baseline_rate * (1 + mde))}")
    print(f"   • Significance level (α): {format_percentage(alpha)}")
    print(f"   • Statistical power (1-β): {format_percentage(power)}")
    
    print("\n📈 RESULTS:")
    print(f"   • Required sample size per variant: {sample_size:,}")
    print(f"   • Total sample size (2 variants): {sample_size * 2:,}")
    
    if daily_visitors:
        days = calculate_test_duration(sample_size, daily_visitors)
        print(f"\n⏱️  ESTIMATED DURATION:")
        print(f"   • With {daily_visitors:,} daily visitors: ~{days} days")
        if days > 30:
            print(f"   ⚠️  Consider increasing MDE or traffic allocation")
    
    print("\n" + "=" * 60)


def print_results_report(
    control_conversions: int,
    control_visitors: int,
    variant_conversions: int,
    variant_visitors: int,
    alpha: float = 0.05
):
    """Print a formatted test results analysis report."""
    
    results = analyze_test_results(
        control_conversions, control_visitors,
        variant_conversions, variant_visitors,
        alpha
    )
    
    print("\n" + "=" * 60)
    print("📊 A/B TEST RESULTS ANALYSIS")
    print("=" * 60)
    
    print("\n📋 RAW DATA:")
    print(f"   Control:  {control_conversions:,} / {control_visitors:,} = {format_percentage(results['control_rate'])}")
    print(f"   Variant:  {variant_conversions:,} / {variant_visitors:,} = {format_percentage(results['variant_rate'])}")
    
    print("\n📈 PERFORMANCE:")
    lift_direction = "↑" if results['relative_lift'] > 0 else "↓"
    print(f"   • Relative lift: {lift_direction} {format_percentage(abs(results['relative_lift']))}")
    print(f"   • Absolute difference: {format_percentage(results['absolute_difference'])}")
    
    print("\n📊 STATISTICAL ANALYSIS:")
    print(f"   • Z-score: {results['z_score']:.3f}")
    print(f"   • P-value: {results['p_value']:.4f}")
    ci = results['confidence_interval']
    print(f"   • {format_percentage(results['confidence_level'])} CI: [{format_percentage(ci[0])}, {format_percentage(ci[1])}]")
    
    print("\n🎯 CONCLUSION:")
    if results['is_significant']:
        if results['relative_lift'] > 0:
            print(f"   ✅ WINNER: Variant is statistically significantly BETTER")
            print(f"      The variant shows a {format_percentage(results['relative_lift'])} improvement")
        else:
            print(f"   ❌ LOSER: Variant is statistically significantly WORSE")
            print(f"      The variant shows a {format_percentage(abs(results['relative_lift']))} decline")
    else:
        print(f"   ⚖️  NO SIGNIFICANT DIFFERENCE detected at {format_percentage(results['confidence_level'])} confidence")
        print(f"      Consider running longer or accepting a larger MDE")
    
    print("\n" + "=" * 60)


def interactive_mode():
    """Run the calculator in interactive mode."""
    
    print("\n🧪 A/B Test Calculator")
    print("=" * 40)
    print("\nWhat would you like to do?")
    print("1. Calculate required sample size")
    print("2. Analyze test results")
    print("3. Quick example")
    
    choice = input("\nEnter choice (1/2/3): ").strip()
    
    if choice == "1":
        print("\n📊 Sample Size Calculator\n")
        baseline = float(input("Current conversion rate (e.g., 0.05 for 5%): "))
        mde = float(input("Minimum detectable effect (e.g., 0.10 for 10% lift): "))
        daily = input("Daily visitors (optional, press Enter to skip): ").strip()
        daily_visitors = int(daily) if daily else None
        
        print_sample_size_report(baseline, mde, 0.05, 0.80, daily_visitors)
        
    elif choice == "2":
        print("\n📈 Results Analyzer\n")
        control_conv = int(input("Control conversions: "))
        control_vis = int(input("Control visitors: "))
        variant_conv = int(input("Variant conversions: "))
        variant_vis = int(input("Variant visitors: "))
        
        print_results_report(control_conv, control_vis, variant_conv, variant_vis)
        
    elif choice == "3":
        # Example: Testing a new checkout flow
        print("\n📋 Example: New Checkout Flow Test")
        print("-" * 40)
        print("Scenario: Testing if a simplified checkout increases conversion")
        print("Baseline: 3% conversion rate")
        print("Goal: Detect 15% relative improvement (3.45% absolute)")
        
        print_sample_size_report(0.03, 0.15, 0.05, 0.80, 5000)
        
        print("\n📋 Example Results Analysis")
        print("-" * 40)
        print("After running the test:")
        print_results_report(
            control_conversions=450,
            control_visitors=15000,
            variant_conversions=525,
            variant_visitors=15000
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="A/B Test Calculator for Product Managers")
    parser.add_argument("--sample-size", action="store_true", help="Calculate sample size")
    parser.add_argument("--analyze", action="store_true", help="Analyze test results")
    parser.add_argument("--baseline", type=float, help="Baseline conversion rate")
    parser.add_argument("--mde", type=float, help="Minimum detectable effect")
    parser.add_argument("--daily-visitors", type=int, help="Daily visitors")
    
    args = parser.parse_args()
    
    if args.sample_size and args.baseline and args.mde:
        print_sample_size_report(args.baseline, args.mde, 0.05, 0.80, args.daily_visitors)
    else:
        interactive_mode()

