#!/usr/bin/env python3
"""
Eval Score Trend

Track eval metrics over time from a CSV of runs. Report trend, comparison to
baseline (first run or specified), and flag regressions. Use for model/prompt
monitoring and release checks.

Usage:
    # CSV of runs (date, metric, value); baseline = first run by date
    python eval-score-trend.py --csv eval-runs.csv

    # Filter to one metric; specify baseline run
    python eval-score-trend.py --csv eval-runs.csv --metric accuracy --baseline-run run-001

    # Regression threshold: flag if score drops more than 5%% vs baseline
    python eval-score-trend.py --csv eval-runs.csv --regression-threshold 5

    # Latency-style metrics (lower is better): flag when value rises
    python eval-score-trend.py --csv eval-runs.csv --metric latency_p99 --lower-is-better

    # Chart and export
    python eval-score-trend.py --csv eval-runs.csv --chart --markdown report.md --output report.json

CSV format:
    run_id,date,metric,value
    run-001,2025-01-15,accuracy,0.92
    run-001,2025-01-15,latency_p99,120
    run-002,2025-01-22,accuracy,0.94
    run-002,2025-01-22,latency_p99,115

    Required: date (or timestamp), metric (or metric_name), value (or score).
    Optional: run_id (or run). Multiple rows per run (one per metric) are supported.

Requirements:
    None (stdlib only).
"""

import argparse
import csv
import json
import sys
from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Date parsing
# ---------------------------------------------------------------------------

def parse_date(s: str) -> Optional[datetime]:
    if not s or not str(s).strip():
        return None
    s = str(s).strip()[:32]
    for fmt, trim in [
        ("%Y-%m-%dT%H:%M:%S", 19),
        ("%Y-%m-%d %H:%M:%S", 19),
        ("%Y-%m-%d", 10),
        ("%Y/%m/%d", 10),
        ("%m/%d/%Y", 10),
        ("%d/%m/%Y", 10),
    ]:
        try:
            return datetime.strptime(s[:trim].strip(), fmt)
        except ValueError:
            continue
    return None


def _col(fieldnames: List[str], *aliases: str) -> Optional[str]:
    lower_map = {f.lower().strip(): f for f in fieldnames}
    for alias in aliases:
        if alias.lower().strip() in lower_map:
            return lower_map[alias.lower().strip()]
    return None


# ---------------------------------------------------------------------------
# Load runs
# ---------------------------------------------------------------------------

def load_eval_runs(
    path: str,
    run_col: str = "run_id",
    date_col: str = "date",
    metric_col: str = "metric",
    value_col: str = "value",
) -> List[Dict[str, Any]]:
    """Load eval runs from CSV. Each row = one (run, date, metric, value)."""
    rows: List[Dict[str, Any]] = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fields = reader.fieldnames or []

        c_run = _col(fields, run_col, "run_id", "run", "id", "version")
        c_date = _col(fields, date_col, "date", "timestamp", "time", "created")
        c_metric = _col(fields, metric_col, "metric", "metric_name", "name", "score_type")
        c_value = _col(fields, value_col, "value", "score", "result")

        for row in reader:
            raw_date = (row.get(c_date or "date", "") or "").strip()
            dt = parse_date(raw_date)
            metric = (row.get(c_metric or "metric", "") or "").strip()
            raw_val = (row.get(c_value or "value", "") or "").strip().replace(",", "")
            if not dt or not metric or not raw_val:
                continue
            try:
                value = float(raw_val)
            except ValueError:
                continue
            run_id = (row.get(c_run or "run_id", "") or "").strip() or f"run_{len(rows)}"
            rows.append({
                "run_id": run_id,
                "date": dt,
                "date_str": dt.strftime("%Y-%m-%d"),
                "metric": metric,
                "value": value,
            })

    rows.sort(key=lambda r: (r["date"], r["run_id"], r["metric"]))
    return rows


# ---------------------------------------------------------------------------
# Trend analysis
# ---------------------------------------------------------------------------

def compute_trends(
    runs: List[Dict[str, Any]],
    baseline_run: Optional[str],
    baseline_date: Optional[datetime],
    regression_threshold_pct: float,
    lower_is_better: bool = False,
) -> Dict[str, Any]:
    """
    Group by metric; for each metric compute series (date, run_id, value) and
    baseline comparison. Baseline = first run by date, or specified run/date.
    """
    by_metric: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for r in runs:
        by_metric[r["metric"]].append(r)

    metrics = sorted(by_metric.keys())
    result_series: Dict[str, List[Dict[str, Any]]] = {}
    result_baseline: Dict[str, float] = {}
    result_regressions: Dict[str, List[Dict[str, Any]]] = {}

    for metric in metrics:
        series = by_metric[metric]
        # Baseline: first run by date, or run_id/date match
        baseline_val: Optional[float] = None
        if baseline_run:
            for r in series:
                if r["run_id"] == baseline_run:
                    baseline_val = r["value"]
                    break
        elif baseline_date:
            for r in series:
                if r["date"].date() == baseline_date.date():
                    baseline_val = r["value"]
                    break
        if baseline_val is None and series:
            baseline_val = series[0]["value"]

        result_baseline[metric] = baseline_val if baseline_val is not None else 0.0
        out_series = []
        regressions = []
        for r in series:
            val = r["value"]
            delta = (val - baseline_val) if baseline_val is not None else 0
            pct = (delta / baseline_val * 100) if baseline_val and baseline_val != 0 else 0
            is_regression = False
            if baseline_val is not None and baseline_val != 0:
                if lower_is_better:
                    # e.g. latency: regression when value increases above baseline
                    if val > baseline_val:
                        rise_pct = (val - baseline_val) / abs(baseline_val) * 100
                        if rise_pct >= regression_threshold_pct:
                            is_regression = True
                            regressions.append({**r, "vs_baseline_pct": round(pct, 1), "rise_pct": round(rise_pct, 1)})
                else:
                    # higher is better: regression when value drops below baseline
                    if val < baseline_val:
                        drop_pct = (baseline_val - val) / abs(baseline_val) * 100
                        if drop_pct >= regression_threshold_pct:
                            is_regression = True
                            regressions.append({**r, "vs_baseline_pct": round(pct, 1), "drop_pct": round(drop_pct, 1)})
            out_series.append({
                "date": r["date_str"],
                "run_id": r["run_id"],
                "value": round(val, 4),
                "delta": round(delta, 4),
                "vs_baseline_pct": round(pct, 1),
                "regression": is_regression,
            })
        result_series[metric] = out_series
        result_regressions[metric] = regressions

    return {
        "metrics": metrics,
        "series": result_series,
        "baseline": result_baseline,
        "regressions": result_regressions,
        "regression_threshold_pct": regression_threshold_pct,
        "lower_is_better": lower_is_better,
        "baseline_run": baseline_run,
        "baseline_date": baseline_date.strftime("%Y-%m-%d") if baseline_date else None,
    }


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def _bar(value: float, min_val: float, max_val: float, width: int = 20) -> str:
    if max_val <= min_val:
        return "░" * width
    ratio = (value - min_val) / (max_val - min_val)
    ratio = max(0, min(1, ratio))
    filled = int(ratio * width)
    return "█" * filled + "░" * (width - filled)


def print_report(result: Dict[str, Any], metric_filter: Optional[str], chart: bool) -> None:
    """Pretty-print eval score trend."""
    print("\n" + "=" * 70)
    print("📈 EVAL SCORE TREND")
    print("=" * 70)

    metrics = result.get("metrics", [])
    if metric_filter:
        metrics = [m for m in metrics if m.lower() == metric_filter.lower()]
    if not metrics:
        print("\n   No metrics to report.\n")
        return

    baseline_run = result.get("baseline_run")
    baseline_date = result.get("baseline_date")
    bl_note = f"Baseline: run={baseline_run}" if baseline_run else (f"Baseline: date={baseline_date}" if baseline_date else "Baseline: first run")
    direction = "rise" if result.get("lower_is_better") else "drop"
    print(f"\n   {bl_note}  |  Regression: {result.get('regression_threshold_pct', 0)}% {direction} vs baseline")

    for metric in metrics:
        series = result.get("series", {}).get(metric, [])
        baseline = result.get("baseline", {}).get(metric, 0)
        regressions = result.get("regressions", {}).get(metric, [])
        if not series:
            continue
        print(f"\n   ── {metric} (baseline = {baseline}) ──")
        print(f"   {'Date':<12} {'Run':<14} {'Value':>10} {'vs base':>10}  Status")
        print("   " + "─" * 58)
        for r in series:
            status = "🔴 regression" if r.get("regression") else "🟢"
            print(f"   {r['date']:<12} {r['run_id']:<14} {r['value']:>10.4f} {r['vs_baseline_pct']:>+9.1f}%  {status}")
        if regressions:
            print(f"\n   ⚠️  {len(regressions)} regression(s) vs baseline")
        if chart and series:
            vals = [r["value"] for r in series]
            mn, mx = min(vals), max(vals)
            print(f"   Trend: ", end="")
            for r in series:
                bar = _bar(r["value"], mn, mx, 8)
                print(bar, end=" ")
            print(f"  ({mn:.3f} → {mx:.3f})")

    print("\n   💡 Use to spot regressions before release and track metric drift.\n")


def to_json_result(result: Dict[str, Any]) -> Dict[str, Any]:
    """JSON-serializable (no datetime)."""
    return {
        "metrics": result.get("metrics", []),
        "series": result.get("series", {}),
        "baseline": result.get("baseline", {}),
        "regressions": result.get("regressions", {}),
        "regression_threshold_pct": result.get("regression_threshold_pct", 0),
        "lower_is_better": result.get("lower_is_better", False),
        "baseline_run": result.get("baseline_run"),
        "baseline_date": result.get("baseline_date"),
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Track eval score trend over runs; compare to baseline and flag regressions.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--csv", "-c", required=True, help="Path to eval runs CSV (date, metric, value)")
    parser.add_argument("--metric", "-m", type=str, default=None, help="Filter to this metric name")
    parser.add_argument("--baseline-run", type=str, default=None, metavar="RUN_ID", help="Use this run as baseline")
    parser.add_argument("--baseline-date", type=str, default=None, metavar="DATE", help="Use value on this date as baseline per metric")
    parser.add_argument("--regression-threshold", type=float, default=5, help="Flag regression if score drops (or rises for latency) this pct vs baseline (default: 5)")
    parser.add_argument("--lower-is-better", action="store_true", help="For metrics like latency: flag regression when value rises vs baseline")
    parser.add_argument("--chart", action="store_true", help="Print simple value trend bars per metric")
    parser.add_argument("--markdown", metavar="FILE", help="Write Markdown report to FILE")
    parser.add_argument("--output", "-o", metavar="FILE", help="Write JSON result to FILE")
    args = parser.parse_args()

    runs = load_eval_runs(args.csv)
    if not runs:
        print("No valid rows in CSV (need date, metric, value).", file=sys.stderr)
        return 1

    baseline_date = None
    if args.baseline_date:
        baseline_date = parse_date(args.baseline_date)
        if not baseline_date:
            print(f"Invalid --baseline-date: {args.baseline_date}", file=sys.stderr)
            return 1

    result = compute_trends(
        runs,
        args.baseline_run,
        baseline_date,
        max(0, args.regression_threshold),
        lower_is_better=args.lower_is_better,
    )
    print_report(result, args.metric, args.chart)

    if args.markdown:
        metrics = result.get("metrics", [])
        if args.metric:
            metrics = [m for m in metrics if m.lower() == args.metric.lower()]
        with open(args.markdown, "w", encoding="utf-8") as f:
            f.write("# Eval Score Trend\n\n")
            f.write(f"- **Baseline:** {result.get('baseline_run') or result.get('baseline_date') or 'first run'}\n")
            f.write(f"- **Regression threshold:** {result.get('regression_threshold_pct')}%\n\n")
            for metric in metrics:
                series = result.get("series", {}).get(metric, [])
                f.write(f"## {metric}\n\n")
                f.write("| Date | Run | Value | vs baseline % |\n")
                f.write("|------|-----|-------|---------------|\n")
                for r in series:
                    reg = " 🔴" if r.get("regression") else ""
                    f.write(f"| {r['date']} | {r['run_id']} | {r['value']} | {r['vs_baseline_pct']:+.1f}%{reg} |\n")
                f.write("\n")
        print(f"Wrote Markdown to {args.markdown}")

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(to_json_result(result), f, indent=2)
        print(f"Wrote JSON to {args.output}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
