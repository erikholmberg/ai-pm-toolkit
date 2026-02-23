#!/usr/bin/env python3
"""
Sprint Velocity Tracker

Track, analyze, and forecast sprint velocity across teams. Helps PMs with:
    - Velocity trends and stability
    - Commitment vs. completion accuracy
    - Capacity planning and sprint forecasting
    - Carry-over tracking
    - Confidence-interval estimation for future sprints

Usage:
    # Inline sprint data (completed:committed per sprint)
    python sprint-velocity-tracker.py \\
        --sprint "S1:34:40" --sprint "S2:38:42" \\
        --sprint "S3:36:38" --sprint "S4:41:45" \\
        --sprint "S5:39:40" --sprint "S6:42:44"

    # From CSV
    python sprint-velocity-tracker.py --csv velocity.csv

    # With forecasting
    python sprint-velocity-tracker.py --csv velocity.csv --forecast 3

    # With carry-over tracking
    python sprint-velocity-tracker.py \\
        --sprint "S1:34:40:6" --sprint "S2:38:42:4" \\
        --sprint "S3:36:38:2"

    Format: "Label:completed:committed[:carry_over]"

CSV format:
    sprint,completed,committed,carry_over
    Sprint 1,34,40,6
    Sprint 2,38,42,4
    Sprint 3,36,38,2

    Required: sprint, completed
    Optional: committed, carry_over

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
# Velocity analysis
# ---------------------------------------------------------------------------

def analyze_sprint(
    label: str,
    completed: float,
    committed: float = 0,
    carry_over: float = 0,
) -> Dict[str, Any]:
    """Analyze a single sprint."""
    accuracy = completed / committed * 100 if committed > 0 else 0
    carry_pct = carry_over / committed * 100 if committed > 0 else 0

    return {
        "label": label,
        "completed": completed,
        "committed": committed,
        "carry_over": carry_over,
        "accuracy_pct": round(accuracy, 1),
        "carry_over_pct": round(carry_pct, 1),
    }


def analyze_velocity(sprints: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Compute aggregate velocity statistics."""
    n = len(sprints)
    if n == 0:
        return {"error": "No sprint data"}

    velocities = [s["completed"] for s in sprints]
    mean_vel = sum(velocities) / n
    var = sum((v - mean_vel) ** 2 for v in velocities) / max(n - 1, 1)
    std_vel = math.sqrt(var)
    cv = std_vel / mean_vel * 100 if mean_vel > 0 else 0

    min_vel = min(velocities)
    max_vel = max(velocities)
    sorted_v = sorted(velocities)
    median_vel = sorted_v[n // 2] if n % 2 == 1 else (sorted_v[n // 2 - 1] + sorted_v[n // 2]) / 2

    # Commitment accuracy
    accuracies = [s["accuracy_pct"] for s in sprints if s["committed"] > 0]
    avg_accuracy = sum(accuracies) / len(accuracies) if accuracies else 0

    # Carry-over
    carry_overs = [s["carry_over"] for s in sprints]
    avg_carry = sum(carry_overs) / n

    # Trend: compare first half to second half
    mid = n // 2
    first_half = velocities[:mid] if mid > 0 else velocities[:1]
    second_half = velocities[mid:]
    first_avg = sum(first_half) / len(first_half)
    second_avg = sum(second_half) / len(second_half)
    trend_delta = second_avg - first_avg
    trend_pct = trend_delta / first_avg * 100 if first_avg > 0 else 0

    # Stability assessment
    if cv < 10:
        stability = "excellent"
        stability_label = "🟢 Excellent (CV <10%)"
    elif cv < 20:
        stability = "good"
        stability_label = "🟢 Good (CV <20%)"
    elif cv < 30:
        stability = "fair"
        stability_label = "🟡 Fair (CV <30%)"
    else:
        stability = "poor"
        stability_label = "🔴 Poor (CV ≥30%)"

    return {
        "sprints_analyzed": n,
        "mean_velocity": round(mean_vel, 1),
        "median_velocity": round(median_vel, 1),
        "std_dev": round(std_vel, 1),
        "cv_pct": round(cv, 1),
        "min_velocity": min_vel,
        "max_velocity": max_vel,
        "range": max_vel - min_vel,
        "avg_accuracy_pct": round(avg_accuracy, 1),
        "avg_carry_over": round(avg_carry, 1),
        "trend_delta": round(trend_delta, 1),
        "trend_pct": round(trend_pct, 1),
        "trend_direction": "improving" if trend_delta > 0.5 else "declining" if trend_delta < -0.5 else "stable",
        "stability": stability,
        "stability_label": stability_label,
    }


def forecast_sprints(
    sprints: List[Dict[str, Any]],
    n_sprints: int = 3,
    confidence: float = 0.8,
) -> Dict[str, Any]:
    """Forecast future sprints using recent velocity data."""
    if len(sprints) < 3:
        return {"error": "Need at least 3 sprints for forecasting"}

    recent = sprints[-6:] if len(sprints) >= 6 else sprints
    velocities = [s["completed"] for s in recent]
    n = len(velocities)
    mean_vel = sum(velocities) / n
    var = sum((v - mean_vel) ** 2 for v in velocities) / max(n - 1, 1)
    std_vel = math.sqrt(var)

    # Z-value for confidence interval
    z_map = {0.80: 1.282, 0.85: 1.440, 0.90: 1.645, 0.95: 1.960}
    z = z_map.get(confidence, 1.282)
    margin = z * std_vel / math.sqrt(n)

    low = mean_vel - margin
    high = mean_vel + margin

    forecasts = []
    for i in range(1, n_sprints + 1):
        forecasts.append({
            "sprint": f"F+{i}",
            "predicted": round(mean_vel, 1),
            "low": round(max(0, low), 1),
            "high": round(high, 1),
        })

    # Recommended commitment
    conservative = round(mean_vel - std_vel, 0)
    moderate = round(mean_vel, 0)
    aggressive = round(mean_vel + std_vel * 0.5, 0)

    return {
        "based_on_sprints": n,
        "mean_velocity": round(mean_vel, 1),
        "std_dev": round(std_vel, 1),
        "confidence": confidence,
        "confidence_low": round(low, 1),
        "confidence_high": round(high, 1),
        "forecasts": forecasts,
        "recommended_commitment": {
            "conservative": max(0, conservative),
            "moderate": moderate,
            "aggressive": aggressive,
        },
    }


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def parse_sprint_string(s: str) -> Dict[str, Any]:
    """Parse 'Label:completed:committed[:carry_over]'."""
    parts = s.split(":")
    if len(parts) < 2:
        raise ValueError(
            f"Invalid sprint data '{s}'. "
            "Format: Label:completed[:committed[:carry_over]]"
        )
    try:
        label = parts[0].strip()
        completed = float(parts[1].strip())
        committed = float(parts[2].strip()) if len(parts) > 2 else 0
        carry_over = float(parts[3].strip()) if len(parts) > 3 else 0
    except (ValueError, IndexError) as e:
        raise ValueError(f"Invalid numbers in '{s}': {e}")

    return analyze_sprint(label, completed, committed, carry_over)


def _col(fieldnames: List[str], *aliases: str) -> Optional[str]:
    lower_map = {f.lower().strip(): f for f in fieldnames}
    for alias in aliases:
        if alias.lower().strip() in lower_map:
            return lower_map[alias.lower().strip()]
    return None


def load_csv(path: str) -> List[Dict[str, Any]]:
    """Load sprint data from CSV."""
    sprints: List[Dict[str, Any]] = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fields = reader.fieldnames or []

        c_label = _col(fields, "sprint", "name", "label", "iteration")
        c_completed = _col(fields, "completed", "done", "velocity", "points_done", "actual")
        c_committed = _col(fields, "committed", "planned", "points_planned", "target", "scope")
        c_carry = _col(fields, "carry_over", "carryover", "spill", "incomplete", "remaining")

        for row in reader:
            label = row.get(c_label or "sprint", "").strip()
            if not label:
                continue

            def _num(col: Optional[str], default: float = 0) -> float:
                if not col:
                    return default
                raw = row.get(col, "").strip().replace(",", "")
                try:
                    return float(raw) if raw else default
                except ValueError:
                    return default

            completed = _num(c_completed)
            committed = _num(c_committed)
            carry_over = _num(c_carry)

            sprints.append(analyze_sprint(label, completed, committed, carry_over))

    return sprints


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def _bar(value: float, max_val: float, width: int = 25) -> str:
    if max_val <= 0:
        return "░" * width
    ratio = min(1.0, max(0.0, value / max_val))
    filled = int(ratio * width)
    return "█" * filled + "░" * (width - filled)


def print_report(
    sprints: List[Dict[str, Any]],
    stats: Dict[str, Any],
    forecast: Optional[Dict[str, Any]],
) -> None:
    """Pretty-print sprint velocity analysis."""
    print("\n" + "=" * 78)
    print("🏃 SPRINT VELOCITY TRACKER")
    print("=" * 78)

    # Sprint history
    print(f"\n{'─'*78}")
    print(f"\n📅 SPRINT HISTORY ({len(sprints)} sprints):\n")

    has_committed = any(s["committed"] > 0 for s in sprints)
    has_carry = any(s["carry_over"] > 0 for s in sprints)

    if has_committed:
        header = f"   {'Sprint':<12} {'Done':>6} {'Plan':>6} {'Accuracy':>9}"
        div =    f"   {'─'*12} {'─'*6} {'─'*6} {'─'*9}"
        if has_carry:
            header += f" {'Carry':>7}"
            div += f" {'─'*7}"
        print(header)
        print(div)

        max_vel = max(s["completed"] for s in sprints)
        for s in sprints:
            line = f"   {s['label'][:12]:<12} {s['completed']:>6.0f} {s['committed']:>6.0f} {s['accuracy_pct']:>8.0f}%"
            if has_carry:
                line += f" {s['carry_over']:>7.0f}"
            print(line)
    else:
        print(f"   {'Sprint':<12} {'Velocity':>10}")
        print(f"   {'─'*12} {'─'*10}")
        for s in sprints:
            print(f"   {s['label'][:12]:<12} {s['completed']:>10.0f}")

    # Velocity chart
    if sprints:
        max_vel = max(s["completed"] for s in sprints)
        print(f"\n   Velocity over time:")
        for s in sprints:
            bar = _bar(s["completed"], max_vel, 30)
            print(f"   {s['label'][:8]:<8} {bar} {s['completed']:.0f}")

        # Sparkline
        vals = [s["completed"] for s in sprints]
        blocks = " ▁▂▃▄▅▆▇█"
        mx = max(vals)
        mn = min(vals)
        rng = mx - mn if mx > mn else 1
        spark = "".join(blocks[min(8, int((v - mn) / rng * 8))] for v in vals)
        print(f"\n   Trend: {spark}  ({mn:.0f} → {vals[-1]:.0f})")

    # Stats
    if "error" not in stats:
        print(f"\n{'─'*78}")
        print(f"\n📊 VELOCITY STATISTICS:\n")
        print(f"   Mean velocity:       {stats['mean_velocity']:.1f} points")
        print(f"   Median velocity:     {stats['median_velocity']:.1f} points")
        print(f"   Std deviation:       {stats['std_dev']:.1f}")
        print(f"   Range:               {stats['min_velocity']:.0f} – {stats['max_velocity']:.0f} ({stats['range']:.0f})")
        print(f"   Coefficient of var:  {stats['cv_pct']:.1f}%")
        print(f"   Stability:           {stats['stability_label']}")

        if stats['avg_accuracy_pct'] > 0:
            print(f"\n   Avg accuracy:        {stats['avg_accuracy_pct']:.0f}%", end="")
            if stats['avg_accuracy_pct'] >= 85:
                print("  🟢 Committing well")
            elif stats['avg_accuracy_pct'] >= 70:
                print("  🟡 Room for improvement")
            else:
                print("  🔴 Over-committing")

        if stats['avg_carry_over'] > 0:
            print(f"   Avg carry-over:      {stats['avg_carry_over']:.1f} points")

        trend_icon = "📈" if stats["trend_direction"] == "improving" else "📉" if stats["trend_direction"] == "declining" else "➡️"
        print(f"\n   Trend:               {trend_icon} {stats['trend_direction'].title()} ({stats['trend_delta']:+.1f} pts, {stats['trend_pct']:+.1f}%)")

    # Forecast
    if forecast and "error" not in forecast:
        print(f"\n{'─'*78}")
        print(f"\n🔮 FORECAST (based on last {forecast['based_on_sprints']} sprints, "
              f"{forecast['confidence']*100:.0f}% confidence):\n")

        print(f"   {'Sprint':>8} {'Predicted':>10} {'Low':>8} {'High':>8}")
        print(f"   {'─'*8} {'─'*10} {'─'*8} {'─'*8}")

        for f in forecast["forecasts"]:
            print(f"   {f['sprint']:>8} {f['predicted']:>10.1f} {f['low']:>8.1f} {f['high']:>8.1f}")

        rec = forecast["recommended_commitment"]
        print(f"\n   📋 RECOMMENDED COMMITMENT:")
        print(f"   Conservative (safe):    {rec['conservative']:.0f} points")
        print(f"   Moderate (balanced):    {rec['moderate']:.0f} points")
        print(f"   Aggressive (stretch):   {rec['aggressive']:.0f} points")

        # Visual range
        lo = forecast["confidence_low"]
        hi = forecast["confidence_high"]
        mean = forecast["mean_velocity"]
        print(f"\n   Confidence interval:")
        total_range = hi - lo if hi > lo else 1
        bar_width = 40
        mean_pos = int((mean - lo) / total_range * bar_width) if total_range > 0 else bar_width // 2
        bar = "░" * mean_pos + "█" + "░" * (bar_width - mean_pos - 1)
        print(f"   {lo:.0f} [{bar}] {hi:.0f}")
        print(f"   {'':>{mean_pos + int(len(str(int(lo)))) + 2}}▲ {mean:.1f}")

    # Guidance
    print(f"\n{'─'*78}")
    print(f"\n💡 TIPS:")
    print(f"   • Stable velocity (CV <20%) is more important than high velocity")
    print(f"   • Use 3-6 recent sprints for forecasting — too many dilutes trends")
    print(f"   • Commitment accuracy 80-90% is ideal — too high means sandbagging")
    print(f"   • Track carry-over separately — high carry-over masks estimation issues")
    print(f"   • Velocity is a planning tool, not a performance metric")
    print("\n" + "=" * 78)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Track, analyze, and forecast sprint velocity. "
                    "Helps PMs with capacity planning and commitment accuracy.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --sprint "S1:34:40" --sprint "S2:38:42" --sprint "S3:36:38"
  %(prog)s --csv velocity.csv --forecast 3
  %(prog)s --sprint "S1:34:40:6" --sprint "S2:38:42:4" --sprint "S3:36:38:2"
        """,
    )

    parser.add_argument("--sprint", type=str, action="append",
                        help="Sprint data: 'Label:completed[:committed[:carry_over]]'")
    parser.add_argument("--csv", "-c", type=str, help="CSV file with sprint data")
    parser.add_argument("--forecast", type=int, default=0,
                        help="Forecast N future sprints (default: 0)")
    parser.add_argument("--confidence", type=float, default=80,
                        help="Forecast confidence %% (default: 80)")
    parser.add_argument("--output", "-o", type=str, help="Write JSON results to file")
    args = parser.parse_args()

    sprints: List[Dict[str, Any]] = []

    if args.sprint:
        for s_str in args.sprint:
            try:
                sprints.append(parse_sprint_string(s_str))
            except ValueError as e:
                print(f"Error: {e}", file=sys.stderr)
                return 1

    if args.csv:
        try:
            csv_sprints = load_csv(args.csv)
            sprints.extend(csv_sprints)
        except Exception as e:
            print(f"Error loading CSV: {e}", file=sys.stderr)
            return 1

    if not sprints:
        print("Error: provide sprint data via --sprint or --csv.", file=sys.stderr)
        parser.print_help(sys.stderr)
        return 1

    # Analyze
    stats = analyze_velocity(sprints)

    # Forecast
    conf = args.confidence / 100 if args.confidence > 1 else args.confidence
    forecast_result = None
    if args.forecast > 0:
        forecast_result = forecast_sprints(sprints, args.forecast, conf)

    # Report
    print_report(sprints, stats, forecast_result)

    # JSON output
    if args.output:
        report: Dict[str, Any] = {
            "sprints": sprints,
            "statistics": stats,
        }
        if forecast_result:
            report["forecast"] = forecast_result
        with open(args.output, "w") as f:
            json.dump(report, f, indent=2)
        print(f"\n📁 Results saved to {args.output}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
