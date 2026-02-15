#!/usr/bin/env python3
"""
Metric Forecaster

Simple time-series forecasting for product metrics. Given historical values,
project where a metric will be in N periods using multiple methods. Answers
the PM question: "Will we hit our OKR?"

Methods:
    - Linear trend:      least-squares linear regression
    - Exponential trend: fit exponential growth/decay curve
    - Moving average:    project from rolling average trend
    - Naive (last-value): flat-line from most recent value

Usage:
    # From inline values (one per period)
    python metric-forecaster.py --values 1000 1050 1120 1180 1250 --forecast 6

    # With a target (will we hit it?)
    python metric-forecaster.py --values 1000 1050 1120 1180 1250 --forecast 6 --target 1500

    # From CSV
    python metric-forecaster.py --csv revenue.csv --column mrr --forecast 12 --target 100000

    # Custom period label
    python metric-forecaster.py --values 10 12 15 18 22 --forecast 4 --period weeks

CSV format:
    period,mrr,dau,churn_rate
    Jan,80000,4200,5.1
    Feb,83000,4350,4.8
    Mar,87000,4500,4.5
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
# Statistics helpers
# ---------------------------------------------------------------------------

def mean(values: List[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def linear_regression(values: List[float]) -> Tuple[float, float, float]:
    """
    Least-squares linear regression: y = a + b*x where x = 0,1,2,...

    Returns (intercept, slope, r_squared).
    """
    n = len(values)
    if n < 2:
        return values[0] if values else 0, 0, 0

    x_mean = (n - 1) / 2.0
    y_mean = mean(values)

    ss_xy = sum((i - x_mean) * (v - y_mean) for i, v in enumerate(values))
    ss_xx = sum((i - x_mean) ** 2 for i in range(n))
    ss_yy = sum((v - y_mean) ** 2 for v in values)

    if ss_xx == 0:
        return y_mean, 0, 0

    slope = ss_xy / ss_xx
    intercept = y_mean - slope * x_mean

    r_squared = (ss_xy ** 2) / (ss_xx * ss_yy) if ss_yy > 0 else 0

    return intercept, slope, r_squared


def exponential_fit(values: List[float]) -> Tuple[float, float, bool]:
    """
    Fit exponential curve: y = a * e^(b*x).
    Uses log-linear regression on positive values.

    Returns (a, b, success).
    """
    # Filter to positive values only
    positive = [(i, v) for i, v in enumerate(values) if v > 0]
    if len(positive) < 2:
        return values[-1] if values else 0, 0, False

    log_values = [math.log(v) for _, v in positive]
    indices = [float(i) for i, _ in positive]

    n = len(positive)
    x_mean = mean(indices)
    y_mean = mean(log_values)

    ss_xy = sum((x - x_mean) * (y - y_mean) for x, y in zip(indices, log_values))
    ss_xx = sum((x - x_mean) ** 2 for x in indices)

    if ss_xx == 0:
        return math.exp(y_mean), 0, False

    b = ss_xy / ss_xx
    a = math.exp(y_mean - b * x_mean)

    return a, b, True


def moving_average(values: List[float], window: int = 3) -> List[float]:
    """Compute moving average."""
    if len(values) < window:
        return values[:]
    result = []
    for i in range(len(values) - window + 1):
        result.append(mean(values[i:i + window]))
    return result


# ---------------------------------------------------------------------------
# Forecasting methods
# ---------------------------------------------------------------------------

def forecast_linear(values: List[float], n_periods: int) -> Dict[str, Any]:
    """Forecast using linear trend."""
    intercept, slope, r_sq = linear_regression(values)
    n = len(values)

    forecasted = [round(intercept + slope * (n + i), 2) for i in range(n_periods)]
    growth_per_period = slope
    growth_pct = (slope / values[-1] * 100) if values[-1] != 0 else 0

    return {
        "method": "Linear",
        "forecast": forecasted,
        "slope": round(slope, 4),
        "intercept": round(intercept, 4),
        "r_squared": round(r_sq, 4),
        "growth_per_period": round(growth_per_period, 2),
        "growth_pct_per_period": round(growth_pct, 2),
    }


def forecast_exponential(values: List[float], n_periods: int) -> Dict[str, Any]:
    """Forecast using exponential trend."""
    a, b, success = exponential_fit(values)
    n = len(values)

    if not success:
        return {
            "method": "Exponential",
            "forecast": [round(values[-1], 2)] * n_periods,
            "note": "Could not fit exponential (non-positive values)",
            "growth_rate": 0,
        }

    forecasted = [round(a * math.exp(b * (n + i)), 2) for i in range(n_periods)]
    growth_rate = (math.exp(b) - 1) * 100  # percentage growth per period

    return {
        "method": "Exponential",
        "forecast": forecasted,
        "a": round(a, 4),
        "b": round(b, 6),
        "growth_rate_pct": round(growth_rate, 2),
    }


def forecast_moving_avg(values: List[float], n_periods: int, window: int = 3) -> Dict[str, Any]:
    """Forecast by extending the moving average trend."""
    if len(values) < window:
        window = max(1, len(values))

    ma = moving_average(values, window)
    if len(ma) < 2:
        trend = 0
    else:
        trend = ma[-1] - ma[-2]

    forecasted = []
    last_ma = ma[-1]
    for i in range(n_periods):
        next_val = last_ma + trend * (i + 1)
        forecasted.append(round(next_val, 2))

    return {
        "method": f"Moving Average ({window}-period)",
        "forecast": forecasted,
        "last_ma": round(ma[-1], 2),
        "trend_per_period": round(trend, 2),
        "window": window,
    }


def forecast_naive(values: List[float], n_periods: int) -> Dict[str, Any]:
    """Naive forecast: flat-line from last observed value."""
    last = values[-1] if values else 0
    return {
        "method": "Naive (last value)",
        "forecast": [round(last, 2)] * n_periods,
        "last_value": round(last, 2),
    }


# ---------------------------------------------------------------------------
# Target analysis
# ---------------------------------------------------------------------------

def target_analysis(
    forecasts: Dict[str, Dict[str, Any]],
    target: float,
    n_periods: int,
    current: float,
) -> Dict[str, Any]:
    """Check if/when the target will be hit under each forecast method."""
    results = {}
    for method_name, fdata in forecasts.items():
        fc = fdata["forecast"]
        hit_period = None
        for i, val in enumerate(fc):
            if current <= target and val >= target:
                hit_period = i + 1
                break
            elif current >= target and val <= target:
                hit_period = i + 1
                break

        final = fc[-1] if fc else current
        gap = target - final
        gap_pct = (gap / target * 100) if target != 0 else 0

        results[method_name] = {
            "hits_target": hit_period is not None,
            "hits_at_period": hit_period,
            "final_forecast": final,
            "gap_to_target": round(gap, 2),
            "gap_pct": round(gap_pct, 1),
        }

    return results


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_csv_column(path: str, column: str) -> Tuple[List[float], List[str]]:
    """Load a single metric column from CSV."""
    values: List[float] = []
    labels: List[str] = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fields = reader.fieldnames or []
        lower_map = {fl.lower().strip(): fl for fl in fields}

        actual_col = lower_map.get(column.lower().strip())
        if not actual_col:
            raise ValueError(f"Column '{column}' not found. Available: {', '.join(fields)}")

        # Find period label column
        label_col = None
        for alias in ["period", "date", "month", "week", "day", "timestamp", "label"]:
            if alias in lower_map:
                label_col = lower_map[alias]
                break
        if not label_col:
            label_col = fields[0] if fields[0] != actual_col else None

        for row in reader:
            raw = row.get(actual_col, "")
            if not raw or not str(raw).strip():
                continue
            try:
                values.append(float(str(raw).strip().replace(",", "").replace("$", "").rstrip("%")))
                labels.append(row.get(label_col or "", "").strip() if label_col else "")
            except ValueError:
                continue

    return values, labels


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def _bar(value: float, lo: float, hi: float, width: int = 30) -> str:
    if hi <= lo:
        return "·" * width
    ratio = min(1.0, max(0.0, (value - lo) / (hi - lo)))
    pos = int(ratio * (width - 1))
    bar = list("░" * width)
    bar[pos] = "█"
    return "".join(bar)


def _fmt_num(val: float) -> str:
    if abs(val) >= 1_000_000:
        return f"{val / 1_000_000:,.1f}M"
    elif abs(val) >= 1_000:
        return f"{val:,.0f}"
    elif val == int(val):
        return f"{int(val):,}"
    else:
        return f"{val:,.2f}"


def print_report(
    values: List[float],
    labels: List[str],
    forecasts: Dict[str, Dict[str, Any]],
    n_periods: int,
    target: Optional[float],
    target_results: Optional[Dict[str, Any]],
    period_label: str,
    metric_name: str,
) -> None:
    """Pretty-print forecast report."""
    n = len(values)

    print("\n" + "=" * 78)
    print("📊 METRIC FORECASTER")
    print("=" * 78)

    print(f"\n📋 METRIC: {metric_name}")
    print(f"   • Historical periods:  {n}")
    print(f"   • Forecast horizon:    {n_periods} {period_label}")
    print(f"   • Current value:       {_fmt_num(values[-1])}")
    if target:
        print(f"   • Target:              {_fmt_num(target)}")

    # Historical trend
    if n >= 2:
        total_change = values[-1] - values[0]
        total_pct = (total_change / abs(values[0]) * 100) if values[0] != 0 else 0
        trend_icon = "📈" if total_change > 0 else ("📉" if total_change < 0 else "➡️")
        print(f"   • Historical trend:    {trend_icon} {total_change:+,.2f} ({total_pct:+.1f}%) over {n} {period_label}")

    # Mini sparkline of historical data
    lo = min(values)
    hi = max(values)
    spark_chars = "▁▂▃▄▅▆▇█"
    sparkline = ""
    for v in values:
        idx = int((v - lo) / max(1, hi - lo) * (len(spark_chars) - 1)) if hi > lo else 4
        sparkline += spark_chars[idx]
    print(f"   • History:             {sparkline}")

    # Forecast table
    print(f"\n📈 FORECASTS ({n_periods} {period_label} ahead):\n")

    # Header
    period_headers = [f"+{i+1}" for i in range(n_periods)]
    header = f"   {'Method':<28}" + "".join(f" {h:>8}" for h in period_headers) + f" {'Growth':>10}"
    print(header)
    print(f"   {'─'*28}" + "─" * (9 * n_periods) + f" {'─'*10}")

    for method_name, fdata in forecasts.items():
        fc = fdata["forecast"]
        growth = ""
        if "growth_pct_per_period" in fdata:
            growth = f"{fdata['growth_pct_per_period']:+.1f}%/{period_label[:-1] if period_label.endswith('s') else period_label}"
        elif "growth_rate_pct" in fdata:
            growth = f"{fdata['growth_rate_pct']:+.1f}%/{period_label[:-1] if period_label.endswith('s') else period_label}"
        elif "trend_per_period" in fdata:
            growth = f"{fdata['trend_per_period']:+.1f}/{period_label[:-1] if period_label.endswith('s') else period_label}"

        vals = "".join(f" {_fmt_num(v):>8}" for v in fc[:n_periods])
        print(f"   {method_name:<28}{vals} {growth:>10}")

    # Model quality
    linear = forecasts.get("Linear", {})
    if "r_squared" in linear:
        r2 = linear["r_squared"]
        fit_label = "strong" if r2 >= 0.8 else ("moderate" if r2 >= 0.5 else "weak")
        print(f"\n   📐 Linear fit: R² = {r2:.3f} ({fit_label})")

    # Target analysis
    if target and target_results:
        print(f"\n🎯 TARGET ANALYSIS (target: {_fmt_num(target)}):\n")
        print(f"   {'Method':<28} {'Hits?':>6} {'When':>10} {'Final':>10} {'Gap':>10} {'Gap %':>8}")
        print(f"   {'─'*28} {'─'*6} {'─'*10} {'─'*10} {'─'*10} {'─'*8}")

        for method_name, tr in target_results.items():
            hits = "✅ Yes" if tr["hits_target"] else "❌ No"
            when = f"+{tr['hits_at_period']} {period_label}" if tr["hits_at_period"] else "—"
            final = _fmt_num(tr["final_forecast"])
            gap = _fmt_num(tr["gap_to_target"])
            gap_pct = f"{tr['gap_pct']:+.1f}%"
            print(f"   {method_name:<28} {hits:>6} {when:>10} {final:>10} {gap:>10} {gap_pct:>8}")

        # Verdict
        hits_count = sum(1 for tr in target_results.values() if tr["hits_target"])
        total_methods = len(target_results)
        if hits_count == total_methods:
            print(f"\n   ✅ All models predict hitting the target")
        elif hits_count >= total_methods / 2:
            print(f"\n   🟡 {hits_count}/{total_methods} models predict hitting the target — possible but not certain")
        elif hits_count > 0:
            print(f"\n   🟠 Only {hits_count}/{total_methods} models predict hitting the target — at risk")
        else:
            print(f"\n   🔴 No models predict hitting the target — likely miss without intervention")

    # Visual forecast
    all_vals = list(values)
    for fdata in forecasts.values():
        all_vals.extend(fdata["forecast"])
    if target:
        all_vals.append(target)
    global_lo = min(all_vals)
    global_hi = max(all_vals)

    print(f"\n📊 VISUAL (history + linear forecast):")
    linear_fc = forecasts.get("Linear", {}).get("forecast", [])
    combined = list(values) + linear_fc

    # Scale to width
    chart_width = 50
    for i, val in enumerate(combined):
        pos = int((val - global_lo) / max(1, global_hi - global_lo) * (chart_width - 1))
        bar = "·" * pos + ("●" if i < len(values) else "○") + "·" * (chart_width - 1 - pos)
        label = labels[i] if i < len(labels) and labels[i] else f"+{i - len(values) + 1}" if i >= len(values) else f"  {i + 1}"
        prefix = "  " if i < len(values) else "→ "
        print(f"   {prefix}{label:>6} {bar} {_fmt_num(val)}")

    if target:
        pos = int((target - global_lo) / max(1, global_hi - global_lo) * (chart_width - 1))
        bar = "─" * pos + "◆" + "─" * (chart_width - 1 - pos)
        print(f"   TARGET {bar} {_fmt_num(target)}")

    print(f"\n💡 TIPS:")
    print(f"   • Linear: best for steady, consistent trends")
    print(f"   • Exponential: best for growth/decay patterns (compounding)")
    print(f"   • Moving Average: smooths out noise, conservative estimate")
    print(f"   • Compare methods — agreement = higher confidence")
    print("\n" + "=" * 78)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Forecast product metrics using multiple methods. "
                    "Answers: 'Will we hit our OKR?'",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --values 1000 1050 1120 1180 1250 --forecast 6
  %(prog)s --values 1000 1050 1120 1180 1250 --forecast 6 --target 1500
  %(prog)s --csv revenue.csv --column mrr --forecast 12 --target 100000
  %(prog)s --values 10 12 15 18 22 --forecast 4 --period weeks
        """,
    )
    parser.add_argument("--values", "-v", type=float, nargs="+", help="Historical metric values (one per period)")
    parser.add_argument("--csv", "-c", type=str, help="CSV file with metric data")
    parser.add_argument("--column", type=str, help="Column name to forecast (required with --csv)")
    parser.add_argument("--forecast", "-f", type=int, default=6, help="Number of periods to forecast (default: 6)")
    parser.add_argument("--target", "-t", type=float, help="Target value to check against")
    parser.add_argument("--period", "-p", type=str, default="periods", help="Period label (e.g. weeks, months, sprints)")
    parser.add_argument("--window", "-w", type=int, default=3, help="Moving average window (default: 3)")
    parser.add_argument("--output", "-o", type=str, help="Write results to JSON file")
    args = parser.parse_args()

    metric_name = "metric"
    labels: List[str] = []

    if args.values:
        values = args.values
        metric_name = "inline values"
    elif args.csv:
        if not args.column:
            print("Error: --column is required with --csv.", file=sys.stderr)
            return 1
        try:
            values, labels = load_csv_column(args.csv, args.column)
            metric_name = args.column
        except Exception as e:
            print(f"Error loading CSV: {e}", file=sys.stderr)
            return 1
    else:
        print("Error: provide --values or --csv.", file=sys.stderr)
        parser.print_help(sys.stderr)
        return 1

    if len(values) < 3:
        print("Error: need at least 3 data points for forecasting.", file=sys.stderr)
        return 1

    # Forecast with all methods
    forecasts = {
        "Linear": forecast_linear(values, args.forecast),
        "Exponential": forecast_exponential(values, args.forecast),
        f"Moving Avg ({args.window})": forecast_moving_avg(values, args.forecast, args.window),
        "Naive": forecast_naive(values, args.forecast),
    }

    # Target analysis
    target_results = None
    if args.target:
        target_results = target_analysis(forecasts, args.target, args.forecast, values[-1])

    # Report
    print_report(
        values, labels, forecasts, args.forecast,
        args.target, target_results, args.period, metric_name,
    )

    # JSON output
    if args.output:
        report = {
            "metric": metric_name,
            "n_historical": len(values),
            "n_forecast": args.forecast,
            "current_value": values[-1],
            "target": args.target,
            "forecasts": forecasts,
            "target_analysis": target_results,
        }
        with open(args.output, "w") as f:
            json.dump(report, f, indent=2)
        print(f"\n📁 Results saved to {args.output}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
