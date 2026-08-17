#!/usr/bin/env python3
"""
Training Job Cost Tracker

Every other cost tool in this toolkit prices inference. Training and
fine-tuning runs are the other half of an MLOps platform's compute bill, and
they have a failure mode inference doesn't: a run that OOMs at step 8,000 of
10,000 burns just as many GPU-hours as one that finishes. This script turns a
CSV of training/fine-tuning job runs into total spend, spend wasted on
failed/canceled runs, and a breakdown by GPU type and by model/team.

Tracks:
    - Total GPU-hours and spend across all runs
    - Wasted spend — cost of failed/canceled runs, as a % of total
    - Spend by GPU type, and by model/team (whichever the CSV has)
    - Costliest individual runs
    - Daily/weekly spend trend, if a date column is present

Cost per job = gpu_count × hours × $/GPU-hour. Uses a `cost_usd` column if the
CSV already has one; else a `cost_per_gpu_hour` column if present; else a
built-in on-demand rate table by GPU type (override with --gpu-rate).
Duration comes from an `hours` column, or is derived from `start_time` /
`end_time` if that's what you have instead.

Usage:
    python training-job-cost-tracker.py --csv jobs.csv
    python training-job-cost-tracker.py --csv jobs.csv --group-by team
    python training-job-cost-tracker.py --csv jobs.csv --gpu-rate H100-80GB:2.10
    python training-job-cost-tracker.py --csv jobs.csv --top-n 10 --output report.json

CSV format:
    job,model,team,gpu_type,gpu_count,hours,status,date
    ft-run-0142,support-classifier-v3,platform-ml,A100-80GB,8,14.5,success,2026-08-01
    ft-run-0143,support-classifier-v3,platform-ml,A100-80GB,8,3.0,failed,2026-08-02
    pretrain-x-0007,internal-embed-v2,search-ml,H100-80GB,32,40.0,success,2026-08-03

    Required: job, gpu_type, gpu_count, and either hours or start_time+end_time
    Optional: model, team, status (default "success"), date, cost_usd,
              cost_per_gpu_hour

The built-in GPU rate table (on-demand, USD/hour, approximate — regions and
committed-use discounts vary, so pass real rates via --gpu-rate or a
cost_per_gpu_hour column whenever you have them):
    H100-80GB   $4.10   A100-80GB   $2.75   A100-40GB   $2.20
    L4          $0.70   A10G        $1.00   V100        $1.30   T4  $0.40

Requirements:
    None (stdlib only).
"""

import argparse
import json
import sys
from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, List, Optional

# Shared header matching — tolerates real-world column spellings
# ("GPU Type" == "gpu_type"). See scripts/csv_columns.py.
import csv_columns

# Shared result envelope (provenance + machine-readable chaining).
# See scripts/toolkit_io.py.
import toolkit_io

TOOL = "training-job-cost-tracker"

# On-demand $/GPU-hour, approximate cloud list-price ballpark as of 2026.
# Indicative only — always prefer a cost_usd/cost_per_gpu_hour column or
# --gpu-rate when you know the real number for your account.
DEFAULT_GPU_RATES: Dict[str, float] = {
    "h100-80gb": 4.10,
    "h100": 4.10,
    "a100-80gb": 2.75,
    "a100-40gb": 2.20,
    "a100": 2.75,
    "a10g": 1.00,
    "l4": 0.70,
    "v100": 1.30,
    "t4": 0.40,
}
FALLBACK_RATE = 2.00  # used for an unrecognized gpu_type, with a warning

STATUS_WASTED = {"failed", "cancelled", "canceled", "error", "oom", "timeout"}
STATUS_SUCCESS = {"success", "succeeded", "completed", "complete", "done"}


# ---------------------------------------------------------------------------
# Date parsing (mirrors cycle-lead-time-analyzer.py's convention)
# ---------------------------------------------------------------------------

def parse_date(s: str) -> Optional[datetime]:
    if not s or not s.strip():
        return None
    s = s.strip()
    try:
        from dateutil import parser as date_parser
        return date_parser.parse(s)
    except ImportError:
        pass
    except Exception:
        pass
    for fmt, trim in [
        ("%Y-%m-%dT%H:%M:%S", 19),
        ("%Y-%m-%d %H:%M:%S", 19),
        ("%Y-%m-%d", 10),
        ("%Y/%m/%d", 10),
        ("%m/%d/%Y", 10),
    ]:
        try:
            return datetime.strptime(s[:trim], fmt)
        except ValueError:
            continue
    return None


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def normalize_status(raw: str) -> str:
    s = (raw or "success").strip().lower()
    if s in STATUS_WASTED:
        return "failed" if s not in ("cancelled", "canceled") else "canceled"
    if s in STATUS_SUCCESS:
        return "success"
    return s or "success"


def load_csv(path: str, gpu_rates: Dict[str, float]) -> Dict[str, Any]:
    """Load job runs from CSV. Returns {jobs, warnings, group_field_present}."""
    jobs: List[Dict[str, Any]] = []
    warnings: List[str] = []
    unknown_gpu_types: set = set()
    has_model = False
    has_team = False

    with open(path, newline="", encoding="utf-8") as f:
        reader = csv_columns.DictReader(f)
        fields = reader.fieldnames or []

        c_job = reader.resolve("job", "job_id", "run", "run_id", "name")
        c_model = reader.resolve("model", "model_name")
        c_team = reader.resolve("team", "owner", "squad", "group")
        c_gpu_type = reader.resolve("gpu_type", "gpu", "instance_type", "accelerator")
        c_gpu_count = reader.resolve("gpu_count", "gpus", "num_gpus", "n_gpus")
        c_hours = reader.resolve("hours", "duration_hours", "runtime_hours", "gpu_hours")
        c_start = reader.resolve("start_time", "started_at", "start")
        c_end = reader.resolve("end_time", "ended_at", "end", "finished_at")
        c_status = reader.resolve("status", "outcome", "result")
        c_date = reader.resolve("date", "start_date", "day")
        c_cost = reader.resolve("cost_usd", "cost", "spend")
        c_rate = reader.resolve("cost_per_gpu_hour", "gpu_rate", "rate_per_gpu_hour")

        if not c_job:
            raise ValueError(f"No job/job_id column found. CSV has: {', '.join(fields)}")
        if not c_gpu_type:
            raise ValueError(f"No gpu_type column found. CSV has: {', '.join(fields)}")
        if not c_gpu_count:
            raise ValueError(f"No gpu_count column found. CSV has: {', '.join(fields)}")
        if not c_hours and not (c_start and c_end):
            raise ValueError(
                "No duration found — need an hours/duration_hours column, "
                "or both start_time and end_time."
            )

        for row in reader:
            job = str(row.get(c_job, "")).strip()
            if not job:
                continue

            gpu_type_raw = str(row.get(c_gpu_type, "")).strip()
            gpu_type_key = gpu_type_raw.lower()
            try:
                gpu_count = float(str(row.get(c_gpu_count, "0")).strip().replace(",", ""))
            except ValueError:
                gpu_count = 0.0

            if c_hours:
                try:
                    hours = float(str(row.get(c_hours, "0")).strip().replace(",", ""))
                except ValueError:
                    hours = 0.0
            else:
                start = parse_date(str(row.get(c_start, "")))
                end = parse_date(str(row.get(c_end, "")))
                if start and end and end > start:
                    hours = (end - start).total_seconds() / 3600
                else:
                    hours = 0.0
                    warnings.append(f"Job {job}: could not derive duration from start/end times.")

            model = str(row.get(c_model, "")).strip() if c_model else ""
            team = str(row.get(c_team, "")).strip() if c_team else ""
            if model:
                has_model = True
            if team:
                has_team = True

            status = normalize_status(str(row.get(c_status, "")) if c_status else "")
            date_str = str(row.get(c_date, "")).strip() if c_date else ""

            explicit_cost = None
            if c_cost and str(row.get(c_cost, "")).strip():
                try:
                    explicit_cost = float(str(row[c_cost]).strip().replace(",", "").replace("$", ""))
                except ValueError:
                    explicit_cost = None

            if explicit_cost is not None:
                cost = explicit_cost
                rate = round(cost / (gpu_count * hours), 4) if gpu_count > 0 and hours > 0 else 0.0
            else:
                rate = None
                if c_rate and str(row.get(c_rate, "")).strip():
                    try:
                        rate = float(str(row[c_rate]).strip().replace(",", "").replace("$", ""))
                    except ValueError:
                        rate = None
                if rate is None:
                    rate = gpu_rates.get(gpu_type_key)
                    if rate is None:
                        rate = FALLBACK_RATE
                        unknown_gpu_types.add(gpu_type_raw or "(blank)")
                cost = gpu_count * hours * rate

            jobs.append({
                "job": job,
                "model": model,
                "team": team,
                "gpu_type": gpu_type_raw or "(unknown)",
                "gpu_count": gpu_count,
                "hours": round(hours, 2),
                "gpu_hours": round(gpu_count * hours, 2),
                "rate_per_gpu_hour": round(rate, 4),
                "status": status,
                "date": date_str,
                "cost": round(cost, 2),
                "wasted": status in ("failed", "canceled"),
            })

    if unknown_gpu_types:
        warnings.append(
            f"Used fallback rate ${FALLBACK_RATE:.2f}/GPU-hour for unrecognized gpu_type(s): "
            f"{', '.join(sorted(unknown_gpu_types))}. Pass --gpu-rate TYPE:price for accurate numbers."
        )

    return {
        "jobs": jobs,
        "warnings": warnings,
        "has_model": has_model,
        "has_team": has_team,
    }


# ---------------------------------------------------------------------------
# Analysis
# ---------------------------------------------------------------------------

def analyze(jobs: List[Dict[str, Any]], group_by: str, top_n: int) -> Dict[str, Any]:
    n = len(jobs)
    total_cost = sum(j["cost"] for j in jobs)
    total_gpu_hours = sum(j["gpu_hours"] for j in jobs)

    by_status: Dict[str, Dict[str, Any]] = defaultdict(lambda: {"count": 0, "cost": 0.0, "gpu_hours": 0.0})
    for j in jobs:
        b = by_status[j["status"]]
        b["count"] += 1
        b["cost"] += j["cost"]
        b["gpu_hours"] += j["gpu_hours"]
    for b in by_status.values():
        b["cost"] = round(b["cost"], 2)
        b["gpu_hours"] = round(b["gpu_hours"], 2)
        b["pct_of_cost"] = round(b["cost"] / total_cost * 100, 1) if total_cost > 0 else 0.0

    wasted_cost = sum(j["cost"] for j in jobs if j["wasted"])
    waste_ratio = wasted_cost / total_cost * 100 if total_cost > 0 else 0.0

    if waste_ratio <= 5:
        waste_health = "🟢 Healthy — wasted spend is minor"
    elif waste_ratio <= 15:
        waste_health = "🟡 Watch — failed/canceled runs are a real cost line"
    elif waste_ratio <= 30:
        waste_health = "🟠 High — investigate why runs are failing before they burn budget"
    else:
        waste_health = "🔴 Critical — most of this spend is producing nothing"

    by_gpu: Dict[str, Dict[str, Any]] = defaultdict(lambda: {"count": 0, "cost": 0.0, "gpu_hours": 0.0})
    for j in jobs:
        b = by_gpu[j["gpu_type"]]
        b["count"] += 1
        b["cost"] += j["cost"]
        b["gpu_hours"] += j["gpu_hours"]
    for b in by_gpu.values():
        b["cost"] = round(b["cost"], 2)
        b["gpu_hours"] = round(b["gpu_hours"], 2)

    field_key = "team" if group_by == "team" else "model"
    by_group: Dict[str, Dict[str, Any]] = defaultdict(lambda: {"count": 0, "cost": 0.0, "gpu_hours": 0.0, "wasted_cost": 0.0})
    for j in jobs:
        key = j.get(field_key) or "(unlabeled)"
        b = by_group[key]
        b["count"] += 1
        b["cost"] += j["cost"]
        b["gpu_hours"] += j["gpu_hours"]
        if j["wasted"]:
            b["wasted_cost"] += j["cost"]
    for b in by_group.values():
        b["cost"] = round(b["cost"], 2)
        b["gpu_hours"] = round(b["gpu_hours"], 2)
        b["wasted_cost"] = round(b["wasted_cost"], 2)

    top_jobs = sorted(jobs, key=lambda j: j["cost"], reverse=True)[:top_n]

    success_costs = [j["cost"] for j in jobs if j["status"] == "success"]
    avg_success_cost = sum(success_costs) / len(success_costs) if success_costs else 0.0

    trend: List[Dict[str, Any]] = []
    dated = [j for j in jobs if j["date"]]
    if dated:
        by_date: Dict[str, Dict[str, Any]] = defaultdict(lambda: {"cost": 0.0, "count": 0})
        for j in dated:
            d = by_date[j["date"]]
            d["cost"] += j["cost"]
            d["count"] += 1
        for d in sorted(by_date):
            trend.append({"date": d, "cost": round(by_date[d]["cost"], 2), "count": by_date[d]["count"]})

    return {
        "n_jobs": n,
        "total_cost": round(total_cost, 2),
        "total_gpu_hours": round(total_gpu_hours, 2),
        "avg_cost_per_job": round(total_cost / n, 2) if n else 0.0,
        "avg_cost_per_success": round(avg_success_cost, 2),
        "wasted_cost": round(wasted_cost, 2),
        "waste_ratio_pct": round(waste_ratio, 1),
        "waste_health": waste_health,
        "by_status": dict(by_status),
        "by_gpu_type": dict(by_gpu),
        "group_by": field_key,
        "by_group": dict(sorted(by_group.items(), key=lambda kv: kv[1]["cost"], reverse=True)),
        "top_jobs": top_jobs,
        "trend": trend,
    }


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def _fmt_usd(amount: float) -> str:
    if abs(amount) >= 1000:
        return f"${amount:,.2f}"
    return f"${amount:.2f}"


def _bar(value: float, max_val: float, width: int = 25) -> str:
    if max_val <= 0:
        return "░" * width
    ratio = min(1.0, max(0.0, value / max_val))
    filled = int(ratio * width)
    return "█" * filled + "░" * (width - filled)


def print_report(r: Dict[str, Any], warnings: List[str]) -> None:
    print("\n" + "=" * 78)
    print("🖥️  TRAINING JOB COST TRACKER")
    print("=" * 78)

    print(f"\n📊 OVERVIEW ({r['n_jobs']} jobs):")
    print(f"   Total spend:        {_fmt_usd(r['total_cost'])}")
    print(f"   Total GPU-hours:    {r['total_gpu_hours']:,.1f}")
    print(f"   Avg cost/job:       {_fmt_usd(r['avg_cost_per_job'])}")
    print(f"   Avg cost/success:   {_fmt_usd(r['avg_cost_per_success'])}")

    print(f"\n💸 WASTED SPEND (failed / canceled runs):")
    print(f"   {_fmt_usd(r['wasted_cost'])} of {_fmt_usd(r['total_cost'])} ({r['waste_ratio_pct']:.1f}%)")
    print(f"   {r['waste_health']}")

    print(f"\n📋 BY STATUS:")
    print(f"   {'Status':<14} {'Jobs':>6} {'GPU-hrs':>10} {'Cost':>12} {'% of spend'}")
    print(f"   {'─'*14} {'─'*6} {'─'*10} {'─'*12} {'─'*10}")
    for status, b in sorted(r["by_status"].items(), key=lambda kv: kv[1]["cost"], reverse=True):
        print(f"   {status:<14} {b['count']:>6} {b['gpu_hours']:>10,.1f} {_fmt_usd(b['cost']):>12} {b['pct_of_cost']:>8.1f}%")

    print(f"\n🎛️  BY GPU TYPE:")
    max_gpu_cost = max((b["cost"] for b in r["by_gpu_type"].values()), default=1)
    for gpu_type, b in sorted(r["by_gpu_type"].items(), key=lambda kv: kv[1]["cost"], reverse=True):
        bar = _bar(b["cost"], max_gpu_cost)
        print(f"   {gpu_type:<14} {bar} {_fmt_usd(b['cost']):>12}  ({b['gpu_hours']:,.1f} GPU-hrs, {b['count']} jobs)")

    label = "TEAM" if r["group_by"] == "team" else "MODEL"
    print(f"\n🏷️  BY {label}:")
    max_group_cost = max((b["cost"] for b in r["by_group"].values()), default=1)
    for name, b in list(r["by_group"].items())[:10]:
        bar = _bar(b["cost"], max_group_cost)
        waste_note = f"  ({_fmt_usd(b['wasted_cost'])} wasted)" if b["wasted_cost"] > 0 else ""
        print(f"   {name[:20]:<20} {bar} {_fmt_usd(b['cost']):>12}{waste_note}")

    print(f"\n🔝 TOP {len(r['top_jobs'])} COSTLIEST JOBS:")
    print(f"   {'Job':<20} {'Status':<10} {'GPU':<12} {'GPU-hrs':>9} {'Cost':>12}")
    print(f"   {'─'*20} {'─'*10} {'─'*12} {'─'*9} {'─'*12}")
    for j in r["top_jobs"]:
        print(f"   {j['job'][:20]:<20} {j['status']:<10} {j['gpu_type'][:12]:<12} {j['gpu_hours']:>9,.1f} {_fmt_usd(j['cost']):>12}")

    if r["trend"]:
        print(f"\n📈 SPEND TREND:")
        max_day_cost = max((d["cost"] for d in r["trend"]), default=1)
        for d in r["trend"]:
            bar = _bar(d["cost"], max_day_cost, 20)
            print(f"   {d['date']:<12} {bar} {_fmt_usd(d['cost']):>10}  ({d['count']} jobs)")

    if warnings:
        print(f"\n⚠️  WARNINGS:")
        for w in warnings:
            print(f"   • {w}")

    print(f"\n💡 GUIDANCE:")
    print(f"   • A waste ratio above ~15% usually means checkpointing or pre-flight config")
    print(f"     validation would pay for itself — catch OOMs and bad configs before hour 10.")
    print(f"   • Compare avg cost/success against the value of the model it produces —")
    print(f"     if that ratio is upside down, the experiment cadence is too expensive.")
    print(f"   • Rates here are estimates unless your CSV carries cost_usd or")
    print(f"     cost_per_gpu_hour — pull real billing data before using this for budget asks.")

    print("\n" + "=" * 78)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_gpu_rate_overrides(pairs: Optional[List[str]]) -> Dict[str, float]:
    rates = dict(DEFAULT_GPU_RATES)
    for pair in pairs or []:
        if ":" not in pair:
            raise ValueError(f"Invalid --gpu-rate '{pair}'. Format: TYPE:price (e.g. H100-80GB:4.10)")
        gpu_type, price = pair.rsplit(":", 1)
        try:
            rates[gpu_type.strip().lower()] = float(price.strip())
        except ValueError:
            raise ValueError(f"Invalid price in --gpu-rate '{pair}'")
    return rates


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Track cost and wasted spend across ML training/fine-tuning job runs. "
                    "Breaks down spend by GPU type, model/team, and failed-vs-successful runs.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --csv jobs.csv
  %(prog)s --csv jobs.csv --group-by team
  %(prog)s --csv jobs.csv --gpu-rate H100-80GB:2.10 --gpu-rate A100-80GB:1.85
  %(prog)s --csv jobs.csv --top-n 10 --output report.json
        """,
    )
    parser.add_argument("--csv", "-c", type=str, required=True, help="CSV file with training job runs")
    parser.add_argument("--group-by", choices=["model", "team"], default="model",
                        help="Group spend breakdown by model or team (default: model)")
    parser.add_argument("--top-n", type=int, default=5, help="Number of costliest jobs to show (default: 5)")
    parser.add_argument("--gpu-rate", action="append",
                        help="Override/add a GPU rate: 'TYPE:price' (e.g. H100-80GB:4.10). Repeatable.")
    parser.add_argument("--output", "-o", type=str, help="Write JSON results to file")
    args = parser.parse_args()

    try:
        gpu_rates = parse_gpu_rate_overrides(args.gpu_rate)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    try:
        loaded = load_csv(args.csv, gpu_rates)
    except Exception as e:
        print(f"Error loading CSV: {e}", file=sys.stderr)
        return 1

    jobs = loaded["jobs"]
    if not jobs:
        print("Error: no valid job rows found in CSV.", file=sys.stderr)
        return 1

    result = analyze(jobs, args.group_by, args.top_n)
    print_report(result, loaded["warnings"])

    if args.output:
        with open(args.output, "w") as f:
            json.dump(toolkit_io.envelope(result, TOOL, warnings=loaded["warnings"]), f, indent=2)
        print(f"\n📁 Results saved to {args.output}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
