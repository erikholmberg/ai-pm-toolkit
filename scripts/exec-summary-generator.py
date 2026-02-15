#!/usr/bin/env python3
"""
Executive Summary Generator

Feed in metrics (CSV or JSON) and generate a formatted executive summary with
highlights, lowlights, trends, and recommended actions. Supports both
heuristic analysis (no API needed) and LLM-powered narrative generation.

Designed for weekly/monthly stakeholder updates — the report every PM writes
but nobody enjoys writing.

Usage:
    # Heuristic mode (no API key needed)
    python exec-summary-generator.py --csv metrics.csv
    python exec-summary-generator.py --json metrics.json --output summary.md

    # LLM-powered narrative (requires API key)
    python exec-summary-generator.py --csv metrics.csv --llm --model claude-3-5-sonnet-20241022

    # With context for better narrative
    python exec-summary-generator.py --csv metrics.csv --llm --context "Q1 launch, 2 new features shipped"

CSV format (header row required):
    metric,current,previous,target,unit
    Revenue,125000,118000,130000,USD
    DAU,4500,4200,,users
    Churn Rate,4.2,5.1,4.0,%
    NPS,42,38,50,score
    P99 Latency,1800,2200,2000,ms
    Support Tickets,89,102,,count

    Required columns: metric, current
    Optional: previous (for trend), target (for status), unit

JSON format:
    {
      "period": "Week of Feb 10, 2026",
      "metrics": [
        {"metric": "Revenue", "current": 125000, "previous": 118000, "target": 130000, "unit": "USD"},
        ...
      ]
    }

Requirements:
    None for heuristic mode (stdlib only).
    Optional: openai/anthropic (for LLM narrative mode).
"""

import argparse
import csv
import json
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Optional imports
# ---------------------------------------------------------------------------

try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def _col(fieldnames: List[str], *aliases: str) -> Optional[str]:
    lower_map = {f.lower().strip(): f for f in fieldnames}
    for alias in aliases:
        if alias.lower().strip() in lower_map:
            return lower_map[alias.lower().strip()]
    return None


def _float(row: Dict, col: Optional[str], default: Optional[float] = None) -> Optional[float]:
    if not col:
        return default
    raw = row.get(col, "")
    if not raw or not str(raw).strip():
        return default
    val = str(raw).strip().replace(",", "").replace("$", "").rstrip("%")
    try:
        return float(val)
    except ValueError:
        return default


def load_csv(path: str) -> List[Dict[str, Any]]:
    """Load metrics from CSV."""
    metrics: List[Dict[str, Any]] = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fields = reader.fieldnames or []
        c_metric = _col(fields, "metric", "name", "kpi", "measure")
        c_current = _col(fields, "current", "value", "actual", "this_period")
        c_previous = _col(fields, "previous", "last", "prior", "last_period")
        c_target = _col(fields, "target", "goal", "objective")
        c_unit = _col(fields, "unit", "units", "type")
        c_direction = _col(fields, "direction", "good_direction", "better")

        for row in reader:
            name = row.get(c_metric or "metric", "").strip()
            current = _float(row, c_current)
            if not name or current is None:
                continue

            metrics.append({
                "metric": name,
                "current": current,
                "previous": _float(row, c_previous),
                "target": _float(row, c_target),
                "unit": row.get(c_unit or "unit", "").strip() if c_unit else "",
                "direction": row.get(c_direction or "", "").strip().lower() if c_direction else None,
            })
    return metrics


def load_json(path: str) -> tuple:
    """Load metrics from JSON. Returns (metrics_list, metadata_dict)."""
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, list):
        return data, {}
    if isinstance(data, dict):
        metrics = data.get("metrics", [])
        meta = {k: v for k, v in data.items() if k != "metrics"}
        return metrics, meta
    return [], {}


# ---------------------------------------------------------------------------
# Analysis engine
# ---------------------------------------------------------------------------

def infer_direction(metric_name: str, explicit: Optional[str] = None) -> str:
    """
    Infer whether 'up' or 'down' is good for a metric.
    Returns 'up' (higher is better) or 'down' (lower is better).
    """
    if explicit and explicit in ("up", "down"):
        return explicit

    name_lower = metric_name.lower()

    down_is_good = [
        "churn", "latency", "error", "bounce", "ticket", "bug", "incident",
        "cost", "cac", "response time", "load time", "drop-off", "dropout",
        "complaint", "downtime", "p50", "p90", "p95", "p99", "ttfb",
    ]
    for pattern in down_is_good:
        if pattern in name_lower:
            return "down"

    return "up"  # default: higher is better


def analyze_metric(m: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze a single metric: compute change, status, and classify."""
    current = m["current"]
    previous = m.get("previous")
    target = m.get("target")
    direction = infer_direction(m["metric"], m.get("direction"))
    unit = m.get("unit", "")

    result = {**m, "direction": direction}

    # Change vs previous
    if previous is not None and previous != 0:
        change = current - previous
        change_pct = (change / abs(previous)) * 100
        result["change"] = round(change, 2)
        result["change_pct"] = round(change_pct, 1)

        # Is the change good or bad?
        if direction == "up":
            result["trend"] = "improving" if change > 0 else ("declining" if change < 0 else "flat")
        else:
            result["trend"] = "improving" if change < 0 else ("declining" if change > 0 else "flat")
    else:
        result["change"] = None
        result["change_pct"] = None
        result["trend"] = "no_data"

    # Status vs target
    if target is not None:
        if direction == "up":
            if current >= target:
                result["status"] = "on_track"
            elif current >= target * 0.9:
                result["status"] = "at_risk"
            else:
                result["status"] = "off_track"
        else:
            if current <= target:
                result["status"] = "on_track"
            elif current <= target * 1.1:
                result["status"] = "at_risk"
            else:
                result["status"] = "off_track"

        result["target_gap"] = round(current - target, 2)
        result["target_gap_pct"] = round((current - target) / abs(target) * 100, 1) if target != 0 else 0
    else:
        result["status"] = "no_target"
        result["target_gap"] = None
        result["target_gap_pct"] = None

    return result


def classify_metrics(analyzed: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """Separate metrics into highlights, lowlights, and neutral."""
    highlights: List[Dict[str, Any]] = []
    lowlights: List[Dict[str, Any]] = []
    neutral: List[Dict[str, Any]] = []

    for m in analyzed:
        trend = m.get("trend", "no_data")
        status = m.get("status", "no_target")
        change_pct = abs(m.get("change_pct", 0) or 0)

        if trend == "improving" and change_pct >= 3:
            highlights.append(m)
        elif trend == "declining" and change_pct >= 3:
            lowlights.append(m)
        elif status == "off_track":
            lowlights.append(m)
        elif status == "on_track" and trend == "improving":
            highlights.append(m)
        else:
            neutral.append(m)

    # Sort highlights by change magnitude (most impressive first)
    highlights.sort(key=lambda x: abs(x.get("change_pct", 0) or 0), reverse=True)
    lowlights.sort(key=lambda x: abs(x.get("change_pct", 0) or 0), reverse=True)

    return {"highlights": highlights, "lowlights": lowlights, "neutral": neutral}


# ---------------------------------------------------------------------------
# Heuristic recommendations
# ---------------------------------------------------------------------------

def generate_recommendations(classified: Dict[str, List[Dict[str, Any]]]) -> List[str]:
    """Generate actionable recommendations based on metric patterns."""
    recs: List[str] = []

    for m in classified["lowlights"]:
        name = m["metric"]
        direction = m["direction"]
        change_pct = m.get("change_pct")
        status = m.get("status", "no_target")

        if status == "off_track":
            gap = m.get("target_gap", 0)
            recs.append(f"Investigate {name} — off track from target by {abs(gap or 0):.1f} {m.get('unit', '')}")
        elif change_pct and abs(change_pct) >= 10:
            direction_word = "increase" if (direction == "down" and (change_pct or 0) > 0) else "decrease"
            recs.append(f"Urgent: {name} {direction_word}d {abs(change_pct):.0f}% — root-cause analysis needed")
        elif change_pct:
            recs.append(f"Monitor {name} closely — trending in wrong direction ({change_pct:+.1f}%)")

    if not classified["lowlights"]:
        recs.append("All metrics trending positively — consider raising targets")

    if len(classified["highlights"]) >= 3:
        recs.append("Strong overall performance — good week to share wins with stakeholders")

    return recs


# ---------------------------------------------------------------------------
# Formatters
# ---------------------------------------------------------------------------

def _fmt_value(value: float, unit: str) -> str:
    """Format a metric value with its unit."""
    if unit.upper() == "USD" or unit == "$":
        if abs(value) >= 1_000_000:
            return f"${value / 1_000_000:,.1f}M"
        elif abs(value) >= 1_000:
            return f"${value:,.0f}"
        else:
            return f"${value:,.2f}"
    elif unit == "%":
        return f"{value:.1f}%"
    elif unit.lower() == "ms":
        return f"{value:,.0f}ms"
    elif abs(value) >= 10_000:
        return f"{value:,.0f} {unit}".strip()
    elif value == int(value):
        return f"{int(value):,} {unit}".strip()
    else:
        return f"{value:,.1f} {unit}".strip()


def _trend_icon(trend: str) -> str:
    return {"improving": "📈", "declining": "📉", "flat": "➡️", "no_data": "❓"}.get(trend, "❓")


def _status_icon(status: str) -> str:
    return {"on_track": "🟢", "at_risk": "🟡", "off_track": "🔴", "no_target": "⚪"}.get(status, "⚪")


# ---------------------------------------------------------------------------
# Report: terminal
# ---------------------------------------------------------------------------

def print_terminal_report(
    analyzed: List[Dict[str, Any]],
    classified: Dict[str, List[Dict[str, Any]]],
    recommendations: List[str],
    period: str,
    context: Optional[str],
) -> None:
    """Pretty-print executive summary to terminal."""
    print("\n" + "=" * 78)
    print("📊 EXECUTIVE SUMMARY")
    if period:
        print(f"   {period}")
    print("=" * 78)

    if context:
        print(f"\n📝 CONTEXT: {context}")

    # Highlights
    if classified["highlights"]:
        print(f"\n✅ HIGHLIGHTS:")
        for m in classified["highlights"]:
            change = m.get("change_pct")
            val = _fmt_value(m["current"], m.get("unit", ""))
            change_str = f" ({change:+.1f}%)" if change else ""
            target_str = ""
            if m.get("status") == "on_track" and m.get("target") is not None:
                target_str = f" — on track to target {_fmt_value(m['target'], m.get('unit', ''))}"
            print(f"   • {m['metric']}: {val}{change_str}{target_str}")

    # Lowlights
    if classified["lowlights"]:
        print(f"\n⚠️  NEEDS ATTENTION:")
        for m in classified["lowlights"]:
            change = m.get("change_pct")
            val = _fmt_value(m["current"], m.get("unit", ""))
            change_str = f" ({change:+.1f}%)" if change else ""
            status_str = ""
            if m.get("status") == "off_track" and m.get("target") is not None:
                status_str = f" — target: {_fmt_value(m['target'], m.get('unit', ''))}"
            print(f"   • {m['metric']}: {val}{change_str}{status_str}")

    # Full table
    print(f"\n📋 ALL METRICS:")
    print(f"   {'Metric':<24} {'Current':>12} {'Previous':>12} {'Change':>9} {'Target':>12} {'Status'}")
    print(f"   {'─'*24} {'─'*12} {'─'*12} {'─'*9} {'─'*12} {'─'*8}")

    for m in analyzed:
        val = _fmt_value(m["current"], m.get("unit", ""))
        prev = _fmt_value(m["previous"], m.get("unit", "")) if m.get("previous") is not None else "—"
        change = f"{m['change_pct']:+.1f}%" if m.get("change_pct") is not None else "—"
        target = _fmt_value(m["target"], m.get("unit", "")) if m.get("target") is not None else "—"
        trend = _trend_icon(m.get("trend", "no_data"))
        status = _status_icon(m.get("status", "no_target"))

        print(f"   {m['metric']:<24} {val:>12} {prev:>12} {change:>9} {target:>12} {status} {trend}")

    # Summary stats
    n_on = sum(1 for m in analyzed if m.get("status") == "on_track")
    n_risk = sum(1 for m in analyzed if m.get("status") == "at_risk")
    n_off = sum(1 for m in analyzed if m.get("status") == "off_track")
    n_imp = sum(1 for m in analyzed if m.get("trend") == "improving")
    n_dec = sum(1 for m in analyzed if m.get("trend") == "declining")

    print(f"\n📐 SCORECARD:")
    print(f"   • On track:    {n_on}  |  At risk: {n_risk}  |  Off track: {n_off}")
    print(f"   • Improving:   {n_imp}  |  Declining: {n_dec}  |  Total: {len(analyzed)}")

    # Recommendations
    if recommendations:
        print(f"\n🎯 RECOMMENDED ACTIONS:")
        for i, rec in enumerate(recommendations, 1):
            print(f"   {i}. {rec}")

    print("\n" + "=" * 78)


# ---------------------------------------------------------------------------
# Report: Markdown
# ---------------------------------------------------------------------------

def generate_markdown(
    analyzed: List[Dict[str, Any]],
    classified: Dict[str, List[Dict[str, Any]]],
    recommendations: List[str],
    period: str,
    context: Optional[str],
) -> str:
    """Generate a markdown executive summary."""
    lines: List[str] = []
    lines.append(f"# Executive Summary")
    if period:
        lines.append(f"**Period:** {period}\n")
    if context:
        lines.append(f"**Context:** {context}\n")

    # Highlights
    if classified["highlights"]:
        lines.append("## Highlights")
        for m in classified["highlights"]:
            change = m.get("change_pct")
            val = _fmt_value(m["current"], m.get("unit", ""))
            change_str = f" ({change:+.1f}%)" if change else ""
            lines.append(f"- **{m['metric']}**: {val}{change_str}")
        lines.append("")

    # Lowlights
    if classified["lowlights"]:
        lines.append("## Needs Attention")
        for m in classified["lowlights"]:
            change = m.get("change_pct")
            val = _fmt_value(m["current"], m.get("unit", ""))
            change_str = f" ({change:+.1f}%)" if change else ""
            target_str = ""
            if m.get("target") is not None:
                target_str = f" (target: {_fmt_value(m['target'], m.get('unit', ''))})"
            lines.append(f"- **{m['metric']}**: {val}{change_str}{target_str}")
        lines.append("")

    # Table
    lines.append("## All Metrics\n")
    lines.append("| Metric | Current | Previous | Change | Target | Status |")
    lines.append("|--------|---------|----------|--------|--------|--------|")
    for m in analyzed:
        val = _fmt_value(m["current"], m.get("unit", ""))
        prev = _fmt_value(m["previous"], m.get("unit", "")) if m.get("previous") is not None else "—"
        change = f"{m['change_pct']:+.1f}%" if m.get("change_pct") is not None else "—"
        target = _fmt_value(m["target"], m.get("unit", "")) if m.get("target") is not None else "—"
        status = _status_icon(m.get("status", "no_target"))
        trend = _trend_icon(m.get("trend", "no_data"))
        lines.append(f"| {m['metric']} | {val} | {prev} | {change} | {target} | {status} {trend} |")
    lines.append("")

    # Recommendations
    if recommendations:
        lines.append("## Recommended Actions\n")
        for i, rec in enumerate(recommendations, 1):
            lines.append(f"{i}. {rec}")
        lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# LLM narrative
# ---------------------------------------------------------------------------

def llm_narrative(
    analyzed: List[Dict[str, Any]],
    classified: Dict[str, List[Dict[str, Any]]],
    period: str,
    context: Optional[str],
    model: str,
) -> str:
    """Generate an LLM-powered executive narrative."""
    # Build a data summary for the LLM
    data_summary = []
    for m in analyzed:
        entry = f"- {m['metric']}: {_fmt_value(m['current'], m.get('unit', ''))}"
        if m.get("change_pct") is not None:
            entry += f" ({m['change_pct']:+.1f}% vs prior)"
        if m.get("target") is not None:
            entry += f" [target: {_fmt_value(m['target'], m.get('unit', ''))}]"
        if m.get("status") and m["status"] != "no_target":
            entry += f" [{m['status'].replace('_', ' ')}]"
        data_summary.append(entry)

    prompt = f"""You are a senior product manager writing a concise executive summary for stakeholders.

Period: {period or 'This period'}
{f'Context: {context}' if context else ''}

Metrics:
{chr(10).join(data_summary)}

Write a 3-4 paragraph executive summary that:
1. Opens with the overall health/trajectory (1 sentence)
2. Highlights the top 2-3 wins with specific numbers
3. Calls out 1-2 areas of concern with specific numbers and suggested next steps
4. Closes with 2-3 recommended actions for the coming period

Keep it factual, concise, and action-oriented. Use the actual numbers. No fluff.
Write in plain prose (no bullet points, no headers). Target ~200 words."""

    try:
        if "claude" in model.lower():
            if not ANTHROPIC_AVAILABLE:
                return "Error: anthropic package required. pip install anthropic"
            client = anthropic.Anthropic()
            resp = client.messages.create(
                model=model,
                max_tokens=1024,
                temperature=0.3,
                messages=[{"role": "user", "content": prompt}],
            )
            return resp.content[0].text
        elif "gpt" in model.lower():
            if not OPENAI_AVAILABLE:
                return "Error: openai package required. pip install openai"
            client = openai.OpenAI()
            resp = client.chat.completions.create(
                model=model,
                temperature=0.3,
                messages=[{"role": "user", "content": prompt}],
            )
            return resp.choices[0].message.content
        else:
            return f"Error: unsupported model {model}"
    except Exception as e:
        return f"Error generating narrative: {e}"


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Generate an executive summary from metrics data. "
                    "Automatically classifies highlights, lowlights, and recommended actions.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --csv metrics.csv
  %(prog)s --json metrics.json --output summary.md
  %(prog)s --csv metrics.csv --llm --model claude-3-5-sonnet-20241022
  %(prog)s --csv metrics.csv --period "Week of Feb 10" --context "Shipped v2.1"
        """,
    )
    parser.add_argument("--csv", "-c", type=str, help="CSV file with metrics")
    parser.add_argument("--json", "-j", type=str, help="JSON file with metrics")
    parser.add_argument("--period", "-p", type=str, default="", help="Period label (e.g. 'Week of Feb 10, 2026')")
    parser.add_argument("--context", type=str, help="Additional context for the summary")
    parser.add_argument("--llm", action="store_true", help="Generate LLM-powered narrative")
    parser.add_argument("--model", type=str, default="claude-3-5-sonnet-20241022", help="LLM model for narrative")
    parser.add_argument("--output", "-o", type=str, help="Write markdown summary to file")
    args = parser.parse_args()

    if not args.csv and not args.json:
        print("Error: provide --csv or --json.", file=sys.stderr)
        parser.print_help(sys.stderr)
        return 1

    # Load metrics
    meta: Dict[str, Any] = {}
    if args.csv:
        try:
            metrics = load_csv(args.csv)
        except Exception as e:
            print(f"Error loading CSV: {e}", file=sys.stderr)
            return 1
    else:
        try:
            metrics, meta = load_json(args.json)
        except Exception as e:
            print(f"Error loading JSON: {e}", file=sys.stderr)
            return 1

    if not metrics:
        print("Error: no valid metrics found.", file=sys.stderr)
        return 1

    period = args.period or meta.get("period", "")

    # Analyze
    analyzed = [analyze_metric(m) for m in metrics]
    classified = classify_metrics(analyzed)
    recommendations = generate_recommendations(classified)

    # Terminal report
    print_terminal_report(analyzed, classified, recommendations, period, args.context)

    # LLM narrative
    if args.llm:
        print(f"\n✍️  LLM NARRATIVE ({args.model}):")
        print("─" * 78)
        narrative = llm_narrative(analyzed, classified, period, args.context, args.model)
        print(narrative)
        print("─" * 78)

    # Markdown output
    if args.output:
        md = generate_markdown(analyzed, classified, recommendations, period, args.context)
        if args.llm:
            narrative = llm_narrative(analyzed, classified, period, args.context, args.model)
            md = f"# Executive Narrative\n\n{narrative}\n\n---\n\n{md}"
        with open(args.output, "w") as f:
            f.write(md)
        print(f"\n📁 Summary saved to {args.output}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
