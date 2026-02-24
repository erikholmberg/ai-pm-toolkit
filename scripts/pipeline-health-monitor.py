#!/usr/bin/env python3
"""
Data Pipeline Health Monitor

Monitor data pipeline health across freshness, completeness, volume,
schema drift, and error rates. Generates a dashboard-style report with
health scores and alert recommendations for each pipeline.

Tracks:
    - Freshness    — Is data arriving on schedule?
    - Completeness — Are expected records / fields present?
    - Volume       — Is row count within expected range?
    - Error rate   — Are failures below threshold?
    - Schema       — Have columns or types changed unexpectedly?

Usage:
    # Inline pipeline status
    python pipeline-health-monitor.py \\
        --pipeline "User Events:fresh=15min,sla=30min,rows=450000,expected=500000,errors=12,total=450000" \\
        --pipeline "Billing Sync:fresh=2h,sla=4h,rows=8500,expected=10000,errors=3,total=8500" \\
        --pipeline "ML Features:fresh=25min,sla=15min,rows=120000,expected=120000,errors=0,total=120000"

    # From CSV
    python pipeline-health-monitor.py --csv pipelines.csv

    # From JSON
    python pipeline-health-monitor.py --json pipelines.json

CSV format:
    pipeline,freshness_min,sla_min,rows,expected_rows,errors,total_runs,schema_changes,completeness_pct
    User Events,15,30,450000,500000,12,450000,0,98.5
    Billing Sync,120,240,8500,10000,3,8500,0,95.0
    ML Features,25,15,120000,120000,0,120000,2,100

JSON format:
    {
      "pipelines": [
        {
          "name": "User Events",
          "freshness_min": 15,
          "sla_min": 30,
          "rows": 450000,
          "expected_rows": 500000,
          "errors": 12,
          "total_runs": 450000,
          "schema_changes": 0,
          "completeness_pct": 98.5
        }
      ]
    }

Requirements:
    None (stdlib only).
"""

import argparse
import csv
import json
import re
import sys
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Health assessment
# ---------------------------------------------------------------------------

def _parse_duration(s: str) -> float:
    """Parse duration string like '15min', '2h', '30s' into minutes."""
    s = s.strip().lower()
    match = re.match(r'^([\d.]+)\s*(s|sec|seconds?|m|min|minutes?|h|hr|hours?|d|days?)$', s)
    if not match:
        try:
            return float(s)
        except ValueError:
            return 0
    val = float(match.group(1))
    unit = match.group(2)[0]
    if unit == 's':
        return val / 60
    elif unit == 'h':
        return val * 60
    elif unit == 'd':
        return val * 1440
    return val  # minutes


def assess_pipeline(
    name: str,
    freshness_min: float = 0,
    sla_min: float = 0,
    rows: int = 0,
    expected_rows: int = 0,
    errors: int = 0,
    total_runs: int = 0,
    schema_changes: int = 0,
    completeness_pct: float = 100.0,
) -> Dict[str, Any]:
    """Assess health of a single pipeline."""
    dimensions: Dict[str, Dict[str, Any]] = {}

    # Freshness
    if sla_min > 0:
        freshness_ratio = freshness_min / sla_min
        if freshness_ratio <= 0.5:
            freshness_health = "healthy"
            freshness_label = "🟢 Healthy"
            freshness_score = 1.0
        elif freshness_ratio <= 0.8:
            freshness_health = "warning"
            freshness_label = "🟡 Warning"
            freshness_score = 0.7
        elif freshness_ratio <= 1.0:
            freshness_health = "critical"
            freshness_label = "🟠 Near SLA"
            freshness_score = 0.4
        else:
            freshness_health = "breached"
            freshness_label = "🔴 SLA Breached"
            freshness_score = 0.0
        dimensions["freshness"] = {
            "score": freshness_score,
            "health": freshness_health,
            "label": freshness_label,
            "value": f"{freshness_min:.0f}min / {sla_min:.0f}min SLA",
            "detail": f"{freshness_ratio*100:.0f}% of SLA consumed",
        }

    # Volume
    if expected_rows > 0:
        volume_ratio = rows / expected_rows
        volume_diff_pct = (rows - expected_rows) / expected_rows * 100
        if 0.9 <= volume_ratio <= 1.1:
            volume_health = "healthy"
            volume_label = "🟢 Normal"
            volume_score = 1.0
        elif 0.7 <= volume_ratio <= 1.3:
            volume_health = "warning"
            volume_label = "🟡 Anomalous"
            volume_score = 0.6
        elif 0.5 <= volume_ratio <= 1.5:
            volume_health = "critical"
            volume_label = "🟠 Significant drift"
            volume_score = 0.3
        else:
            volume_health = "failed"
            volume_label = "🔴 Major anomaly"
            volume_score = 0.0
        dimensions["volume"] = {
            "score": volume_score,
            "health": volume_health,
            "label": volume_label,
            "value": f"{rows:,} / {expected_rows:,} expected",
            "detail": f"{volume_diff_pct:+.1f}% delta",
        }

    # Error rate
    if total_runs > 0:
        error_rate = errors / total_runs * 100
        if error_rate <= 0.1:
            error_health = "healthy"
            error_label = "🟢 Clean"
            error_score = 1.0
        elif error_rate <= 1.0:
            error_health = "warning"
            error_label = "🟡 Elevated"
            error_score = 0.6
        elif error_rate <= 5.0:
            error_health = "critical"
            error_label = "🟠 High"
            error_score = 0.3
        else:
            error_health = "failed"
            error_label = "🔴 Failing"
            error_score = 0.0
        dimensions["error_rate"] = {
            "score": error_score,
            "health": error_health,
            "label": error_label,
            "value": f"{errors:,} errors / {total_runs:,} runs",
            "detail": f"{error_rate:.3f}%",
        }

    # Completeness
    if completeness_pct < 100:
        if completeness_pct >= 99:
            comp_health = "healthy"
            comp_label = "🟢 Complete"
            comp_score = 1.0
        elif completeness_pct >= 95:
            comp_health = "warning"
            comp_label = "🟡 Gaps"
            comp_score = 0.6
        elif completeness_pct >= 90:
            comp_health = "critical"
            comp_label = "🟠 Missing data"
            comp_score = 0.3
        else:
            comp_health = "failed"
            comp_label = "🔴 Incomplete"
            comp_score = 0.0
    else:
        comp_health = "healthy"
        comp_label = "🟢 Complete"
        comp_score = 1.0
    dimensions["completeness"] = {
        "score": comp_score,
        "health": comp_health,
        "label": comp_label,
        "value": f"{completeness_pct:.1f}%",
        "detail": f"{100 - completeness_pct:.1f}% missing",
    }

    # Schema
    if schema_changes > 0:
        schema_health = "warning"
        schema_label = "🟡 Changed"
        schema_score = 0.5
    else:
        schema_health = "healthy"
        schema_label = "🟢 Stable"
        schema_score = 1.0
    dimensions["schema"] = {
        "score": schema_score,
        "health": schema_health,
        "label": schema_label,
        "value": f"{schema_changes} changes",
        "detail": "Schema drift detected" if schema_changes > 0 else "No drift",
    }

    # Overall score
    scores = [d["score"] for d in dimensions.values()]
    overall_score = sum(scores) / len(scores) if scores else 0
    min_score = min(scores) if scores else 0

    if min_score >= 0.7:
        overall_health = "healthy"
        overall_label = "🟢 Healthy"
    elif min_score >= 0.3:
        overall_health = "degraded"
        overall_label = "🟡 Degraded"
    else:
        overall_health = "unhealthy"
        overall_label = "🔴 Unhealthy"

    # Alerts
    alerts = []
    for dim_name, dim in dimensions.items():
        if dim["health"] in ("critical", "breached", "failed"):
            alerts.append({
                "severity": "critical",
                "dimension": dim_name,
                "message": f"{name}: {dim_name} — {dim['label']} ({dim['value']})",
            })
        elif dim["health"] == "warning":
            alerts.append({
                "severity": "warning",
                "dimension": dim_name,
                "message": f"{name}: {dim_name} — {dim['label']} ({dim['value']})",
            })

    return {
        "name": name,
        "overall_score": round(overall_score, 2),
        "overall_health": overall_health,
        "overall_label": overall_label,
        "dimensions": dimensions,
        "alerts": alerts,
        "freshness_min": freshness_min,
        "sla_min": sla_min,
        "rows": rows,
        "expected_rows": expected_rows,
        "errors": errors,
        "total_runs": total_runs,
        "schema_changes": schema_changes,
        "completeness_pct": completeness_pct,
    }


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def parse_pipeline_string(s: str) -> Dict[str, Any]:
    """Parse 'Name:key=value,key=value,...' into pipeline assessment."""
    parts = s.split(":", 1)
    if len(parts) < 2:
        raise ValueError(f"Invalid pipeline '{s}'. Format: 'Name:key=val,key=val,...'")

    name = parts[0].strip()
    params: Dict[str, str] = {}
    for kv in parts[1].split(","):
        kv = kv.strip()
        if "=" in kv:
            k, v = kv.split("=", 1)
            params[k.strip().lower()] = v.strip()

    freshness = _parse_duration(params.get("fresh", params.get("freshness", "0")))
    sla = _parse_duration(params.get("sla", params.get("sla_min", "0")))
    rows = int(float(params.get("rows", "0")))
    expected = int(float(params.get("expected", params.get("expected_rows", "0"))))
    errors = int(float(params.get("errors", "0")))
    total = int(float(params.get("total", params.get("total_runs", "0"))))
    schema = int(float(params.get("schema", params.get("schema_changes", "0"))))
    completeness = float(params.get("completeness", params.get("completeness_pct", "100")))

    return assess_pipeline(name, freshness, sla, rows, expected, errors, total, schema, completeness)


def _col(fieldnames: List[str], *aliases: str) -> Optional[str]:
    lower_map = {f.lower().strip(): f for f in fieldnames}
    for alias in aliases:
        if alias.lower().strip() in lower_map:
            return lower_map[alias.lower().strip()]
    return None


def load_csv(path: str) -> List[Dict[str, Any]]:
    """Load pipeline data from CSV."""
    pipelines: List[Dict[str, Any]] = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fields = reader.fieldnames or []

        c_name = _col(fields, "pipeline", "name", "table", "source")
        c_fresh = _col(fields, "freshness_min", "freshness", "fresh_min", "lag_min")
        c_sla = _col(fields, "sla_min", "sla", "freshness_sla")
        c_rows = _col(fields, "rows", "row_count", "records", "volume")
        c_expected = _col(fields, "expected_rows", "expected", "baseline_rows")
        c_errors = _col(fields, "errors", "error_count", "failures")
        c_total = _col(fields, "total_runs", "total", "runs", "executions")
        c_schema = _col(fields, "schema_changes", "schema", "drift")
        c_comp = _col(fields, "completeness_pct", "completeness", "complete")

        for row in reader:
            name = row.get(c_name or "pipeline", "").strip()
            if not name:
                continue

            def _num(col: Optional[str], default: float = 0) -> float:
                if not col:
                    return default
                raw = row.get(col, "").strip().replace(",", "").rstrip("%")
                try:
                    return float(raw) if raw else default
                except ValueError:
                    return default

            pipelines.append(assess_pipeline(
                name,
                freshness_min=_num(c_fresh),
                sla_min=_num(c_sla),
                rows=int(_num(c_rows)),
                expected_rows=int(_num(c_expected)),
                errors=int(_num(c_errors)),
                total_runs=int(_num(c_total)),
                schema_changes=int(_num(c_schema)),
                completeness_pct=_num(c_comp, 100),
            ))

    return pipelines


def load_json(path: str) -> List[Dict[str, Any]]:
    """Load pipeline data from JSON."""
    with open(path, encoding="utf-8") as f:
        config = json.load(f)

    pipelines = []
    for p in config.get("pipelines", []):
        pipelines.append(assess_pipeline(
            name=p.get("name", "Unnamed"),
            freshness_min=p.get("freshness_min", 0),
            sla_min=p.get("sla_min", 0),
            rows=p.get("rows", 0),
            expected_rows=p.get("expected_rows", 0),
            errors=p.get("errors", 0),
            total_runs=p.get("total_runs", 0),
            schema_changes=p.get("schema_changes", 0),
            completeness_pct=p.get("completeness_pct", 100),
        ))

    return pipelines


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def _bar(value: float, max_val: float, width: int = 20) -> str:
    if max_val <= 0:
        return "░" * width
    ratio = min(1.0, max(0.0, value / max_val))
    filled = int(ratio * width)
    return "█" * filled + "░" * (width - filled)


def _score_bar(score: float, width: int = 15) -> str:
    filled = int(score * width)
    return "█" * filled + "░" * (width - filled)


def _fmt_rows(n: int) -> str:
    if n >= 1_000_000:
        return f"{n / 1_000_000:,.1f}M"
    elif n >= 1_000:
        return f"{n / 1_000:,.1f}K"
    else:
        return f"{n:,}"


def print_report(pipelines: List[Dict[str, Any]]) -> None:
    """Pretty-print pipeline health dashboard."""
    print("\n" + "=" * 78)
    print("🔌 DATA PIPELINE HEALTH MONITOR")
    print("=" * 78)

    # Fleet overview
    n = len(pipelines)
    healthy = sum(1 for p in pipelines if p["overall_health"] == "healthy")
    degraded = sum(1 for p in pipelines if p["overall_health"] == "degraded")
    unhealthy = sum(1 for p in pipelines if p["overall_health"] == "unhealthy")

    avg_score = sum(p["overall_score"] for p in pipelines) / n if n else 0

    print(f"\n   📊 FLEET OVERVIEW ({n} pipelines):\n")
    print(f"   Health: 🟢 {healthy} healthy   🟡 {degraded} degraded   🔴 {unhealthy} unhealthy")
    print(f"   Avg score: {_score_bar(avg_score)} {avg_score*100:.0f}%")

    # Status table
    print(f"\n{'─'*78}")
    print(f"\n   {'Pipeline':<20} {'Score':>6} {'Fresh':>8} {'Volume':>10} {'Errors':>8} {'Complete':>9} {'Status'}")
    print(f"   {'─'*20} {'─'*6} {'─'*8} {'─'*10} {'─'*8} {'─'*9} {'─'*12}")

    for p in sorted(pipelines, key=lambda x: x["overall_score"]):
        fresh_str = f"{p['freshness_min']:.0f}m" if p["freshness_min"] > 0 else "—"
        vol_str = _fmt_rows(p["rows"]) if p["rows"] > 0 else "—"
        err_str = f"{p['errors']:,}" if p["total_runs"] > 0 else "—"
        comp_str = f"{p['completeness_pct']:.1f}%" if p["completeness_pct"] < 100 else "100%"

        print(
            f"   {p['name'][:20]:<20} "
            f"{p['overall_score']*100:>5.0f}% "
            f"{fresh_str:>8} "
            f"{vol_str:>10} "
            f"{err_str:>8} "
            f"{comp_str:>9} "
            f"{p['overall_label']}"
        )

    # Detailed per-pipeline view
    for p in pipelines:
        print(f"\n{'─'*78}")
        print(f"\n   🔍 {p['name'].upper()}: {p['overall_label']} (score: {p['overall_score']*100:.0f}%)\n")

        dims = p["dimensions"]
        for dim_name, dim in dims.items():
            score_bar = _score_bar(dim["score"])
            print(f"   {dim_name.capitalize():<14} {score_bar} {dim['score']*100:>4.0f}%  {dim['label']}  ({dim['value']})")

    # All alerts
    all_alerts = []
    for p in pipelines:
        all_alerts.extend(p["alerts"])

    critical_alerts = [a for a in all_alerts if a["severity"] == "critical"]
    warning_alerts = [a for a in all_alerts if a["severity"] == "warning"]

    if all_alerts:
        print(f"\n{'─'*78}")
        print(f"\n🚨 ALERTS ({len(critical_alerts)} critical, {len(warning_alerts)} warnings):\n")

        for a in critical_alerts:
            print(f"   🔴 CRITICAL: {a['message']}")
        for a in warning_alerts:
            print(f"   🟡 WARNING:  {a['message']}")

    if not all_alerts:
        print(f"\n{'─'*78}")
        print(f"\n   ✅ All pipelines healthy — no alerts")

    # Health heatmap
    print(f"\n{'─'*78}")
    print(f"\n   🗺️  HEALTH HEATMAP:\n")

    dim_names = ["freshness", "volume", "error_rate", "completeness", "schema"]
    dim_labels = ["Fresh", "Volume", "Errors", "Complete", "Schema"]

    header = f"   {'Pipeline':<16}"
    for label in dim_labels:
        header += f" {label:^8}"
    print(header)
    div = f"   {'─'*16}"
    for _ in dim_labels:
        div += f" {'─'*8}"
    print(div)

    health_chars = {"healthy": "🟢", "warning": "🟡", "critical": "🟠", "breached": "🔴", "failed": "🔴"}
    for p in pipelines:
        line = f"   {p['name'][:16]:<16}"
        for dim_name in dim_names:
            dim = p["dimensions"].get(dim_name)
            if dim:
                char = health_chars.get(dim["health"], "⬜")
                line += f" {char:^8}"
            else:
                line += f" {'—':^8}"
        print(line)

    # Guidance
    print(f"\n{'─'*78}")
    print(f"\n💡 PIPELINE HEALTH TIPS:")
    print(f"   • Freshness SLA should match downstream consumer needs")
    print(f"   • Volume anomalies >±10% warrant investigation")
    print(f"   • Error rates >1% need immediate attention")
    print(f"   • Schema changes should be coordinated with downstream teams")
    print(f"   • Set up PagerDuty / Slack alerts at 80% of SLA threshold")
    print(f"   • Track completeness trends — gradual decay signals silent failures")
    print("\n" + "=" * 78)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Monitor data pipeline health across freshness, completeness, volume, "
                    "error rates, and schema drift. Generates dashboard-style reports.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --pipeline "Events:fresh=15min,sla=30min,rows=450000,expected=500000,errors=12,total=450000"
  %(prog)s --csv pipelines.csv
  %(prog)s --json pipelines.json
        """,
    )

    parser.add_argument("--pipeline", type=str, action="append",
                        help="Pipeline: 'Name:fresh=Xmin,sla=Ymin,rows=N,expected=M,errors=E,total=T'")
    parser.add_argument("--csv", "-c", type=str, help="CSV file with pipeline data")
    parser.add_argument("--json", "-j", type=str, help="JSON file with pipeline data")
    parser.add_argument("--output", "-o", type=str, help="Write JSON results to file")
    args = parser.parse_args()

    pipelines: List[Dict[str, Any]] = []

    if args.pipeline:
        for p_str in args.pipeline:
            try:
                pipelines.append(parse_pipeline_string(p_str))
            except ValueError as e:
                print(f"Error: {e}", file=sys.stderr)
                return 1

    if args.csv:
        try:
            pipelines.extend(load_csv(args.csv))
        except Exception as e:
            print(f"Error loading CSV: {e}", file=sys.stderr)
            return 1

    if args.json:
        try:
            pipelines.extend(load_json(args.json))
        except Exception as e:
            print(f"Error loading JSON: {e}", file=sys.stderr)
            return 1

    if not pipelines:
        print("Error: provide pipeline data via --pipeline, --csv, or --json.", file=sys.stderr)
        parser.print_help(sys.stderr)
        return 1

    # Report
    print_report(pipelines)

    # JSON output
    if args.output:
        with open(args.output, "w") as f:
            json.dump({"pipelines": pipelines}, f, indent=2)
        print(f"\n📁 Results saved to {args.output}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
