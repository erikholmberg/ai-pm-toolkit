#!/usr/bin/env python3
"""
Model Deprecation Watch

Track upcoming LLM/model deprecation and sunset dates across a PM's model
portfolio. Providers now retire model versions faster than most orgs can
migrate off them — this tool surfaces which models are closest to sunset,
weighted by how much traffic and business criticality rides on them, so
the highest-blast-radius migrations get prioritized first.

Usage:
    python model-deprecation-watch.py --csv models.csv
    python model-deprecation-watch.py --csv models.csv --warn-within-days 60
    python model-deprecation-watch.py --csv models.csv --today 2026-09-01 --output report.json

CSV format (header row required):
    model,provider,sunset_date,monthly_requests,criticality
    gpt-4-32k,OpenAI,2026-09-15,50000,high
    claude-2.1,Anthropic,2026-10-01,120000,medium

    Required columns (fuzzy-matched): model (or model_name), sunset_date
    (or deprecation_date, retirement_date, eol_date), in YYYY-MM-DD format.
    Optional: provider, monthly_requests (or volume, traffic), criticality
    (low/medium/high, default medium if omitted).

Requirements:
    None (stdlib only).
"""

import argparse
import csv
import json
import sys
from datetime import date, datetime
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CRITICALITY_WEIGHT = {"low": 1, "medium": 2, "high": 3}
DEFAULT_CRITICALITY = "medium"

URGENT_DAYS = 30    # 🔴 sunset within this many days (or already past)
SOON_DAYS = 90      # 🟡 sunset within this many days


def urgency_tier(days_remaining: int) -> str:
    if days_remaining < URGENT_DAYS:
        return "🔴"
    elif days_remaining < SOON_DAYS:
        return "🟡"
    return "🟢"


def urgency_label(days_remaining: int) -> str:
    if days_remaining < 0:
        return "PAST SUNSET"
    if days_remaining < URGENT_DAYS:
        return "URGENT"
    elif days_remaining < SOON_DAYS:
        return "SOON"
    return "PLANNED"


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def _col(fieldnames: List[str], *aliases: str) -> Optional[str]:
    lower_map = {f.lower().strip(): f for f in fieldnames}
    for alias in aliases:
        if alias.lower().strip() in lower_map:
            return lower_map[alias.lower().strip()]
    return None


def parse_date(raw: str) -> Optional[date]:
    raw = raw.strip()
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    return None


def load_csv(path: str) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fields = reader.fieldnames or []
        c_model = _col(fields, "model", "model_name", "name")
        c_provider = _col(fields, "provider", "vendor")
        c_sunset = _col(fields, "sunset_date", "deprecation_date", "retirement_date", "eol_date", "end_of_life")
        c_requests = _col(fields, "monthly_requests", "volume", "traffic", "requests_per_month")
        c_criticality = _col(fields, "criticality", "priority", "importance")

        if not c_model or not c_sunset:
            raise ValueError("CSV must have model and sunset_date columns.")

        for i, row in enumerate(reader):
            model_name = (row.get(c_model, "") or "").strip()
            sunset_raw = (row.get(c_sunset, "") or "").strip()
            if not model_name or not sunset_raw:
                continue
            sunset = parse_date(sunset_raw)
            if sunset is None:
                print(f"Warning: skipping row {i + 1} — could not parse sunset_date '{sunset_raw}'", file=sys.stderr)
                continue

            requests_raw = (row.get(c_requests, "") or "").strip() if c_requests else ""
            try:
                monthly_requests = int(float(requests_raw)) if requests_raw else 0
            except ValueError:
                monthly_requests = 0

            criticality = (row.get(c_criticality, "") or "").strip().lower() if c_criticality else ""
            if criticality not in CRITICALITY_WEIGHT:
                criticality = DEFAULT_CRITICALITY

            rows.append({
                "model": model_name,
                "provider": (row.get(c_provider, "") or "").strip() if c_provider else "",
                "sunset_date": sunset,
                "monthly_requests": monthly_requests,
                "criticality": criticality,
            })
    return rows


# ---------------------------------------------------------------------------
# Core calculations
# ---------------------------------------------------------------------------

def analyze(rows: List[Dict[str, Any]], today: date, warn_within_days: int) -> Dict[str, Any]:
    queue: List[Dict[str, Any]] = []
    for r in rows:
        days_remaining = (r["sunset_date"] - today).days
        weight = CRITICALITY_WEIGHT.get(r["criticality"], CRITICALITY_WEIGHT[DEFAULT_CRITICALITY])
        # Priority score: higher = more urgent + more blast radius.
        # (1 + monthly_requests) avoids zeroing the score out when traffic is unreported.
        denom = max(days_remaining, 1)
        priority_score = weight * (1 + r["monthly_requests"]) / denom

        queue.append({
            **r,
            "sunset_date": r["sunset_date"].isoformat(),
            "days_remaining": days_remaining,
            "urgency_icon": urgency_tier(days_remaining),
            "urgency_label": urgency_label(days_remaining),
            "criticality_weight": weight,
            "priority_score": round(priority_score, 4),
            "within_warning_window": days_remaining <= warn_within_days,
        })

    queue.sort(key=lambda x: -x["priority_score"])

    n_urgent = sum(1 for q in queue if q["days_remaining"] < URGENT_DAYS)
    n_soon = sum(1 for q in queue if URGENT_DAYS <= q["days_remaining"] < SOON_DAYS)
    n_planned = sum(1 for q in queue if q["days_remaining"] >= SOON_DAYS)
    n_within_warning = sum(1 for q in queue if q["within_warning_window"])

    return {
        "today": today.isoformat(),
        "n_models": len(queue),
        "n_urgent": n_urgent,
        "n_soon": n_soon,
        "n_planned": n_planned,
        "n_within_warning_window": n_within_warning,
        "queue": queue,
    }


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def print_report(result: Dict[str, Any], warn_within_days: int) -> None:
    print("\n" + "=" * 78)
    print("📊 MODEL DEPRECATION WATCH")
    print("=" * 78)

    print(f"\n📋 OVERVIEW:")
    print(f"   • As of:                {result['today']}")
    print(f"   • Models tracked:       {result['n_models']}")
    print(f"   • 🔴 Urgent (<{URGENT_DAYS}d):     {result['n_urgent']}")
    print(f"   • 🟡 Soon ({URGENT_DAYS}-{SOON_DAYS}d):    {result['n_soon']}")
    print(f"   • 🟢 Planned (>{SOON_DAYS}d):    {result['n_planned']}")
    print(f"   • Within warning window ({warn_within_days}d): {result['n_within_warning_window']}")

    print(f"\n📈 PRIORITIZED MIGRATION QUEUE (highest blast-radius first):")
    print(f"   {'#':<3} {'':1} {'Model':<24} {'Provider':<12} {'Days':>6} {'Crit':<8} {'Monthly Req':>12} {'Priority':>10}")
    print(f"   {'─'*3} {'─'*1} {'─'*24} {'─'*12} {'─'*6} {'─'*8} {'─'*12} {'─'*10}")
    for i, q in enumerate(result["queue"], 1):
        days_str = str(q["days_remaining"]) if q["days_remaining"] >= 0 else f"{q['days_remaining']}!"
        print(
            f"   {i:<3} {q['urgency_icon']} {q['model']:<24} {q['provider'] or '—':<12} "
            f"{days_str:>6} {q['criticality']:<8} {q['monthly_requests']:>12,} {q['priority_score']:>10.2f}"
        )

    urgent = [q for q in result["queue"] if q["urgency_label"] in ("URGENT", "PAST SUNSET")]
    if urgent:
        print(f"\n⚠️  ACT NOW — sunsetting within {URGENT_DAYS} days (or already past):")
        for q in urgent:
            note = "already past sunset date!" if q["days_remaining"] < 0 else f"{q['days_remaining']} days remaining"
            print(f"   🔴 {q['model']} ({q['provider'] or 'unknown provider'}) — {note}, "
                  f"{q['monthly_requests']:,} req/mo, {q['criticality']} criticality")

    print(f"\n💡 NEXT STEP:")
    print(f"   For each model in the queue, cost out the migration with:")
    print(f"     python model-migration-estimator.py --from <current-model> --to <replacement-model> \\")
    print(f"       --monthly-requests <N> --avg-input-tokens <N> --avg-output-tokens <N>")
    print(f"   (also in this scripts/ directory)")

    print("\n" + "=" * 78)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Track upcoming LLM deprecation/sunset dates and prioritize migrations by "
                    "urgency, criticality, and traffic volume.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --csv models.csv
  %(prog)s --csv models.csv --warn-within-days 60
  %(prog)s --csv models.csv --today 2026-09-01 --output report.json
        """,
    )
    parser.add_argument("--csv", "-c", required=True, help="CSV with model, sunset_date, and optional provider/monthly_requests/criticality")
    parser.add_argument("--today", type=str, default=None, help="Override 'today' as YYYY-MM-DD (default: actual current date)")
    parser.add_argument("--warn-within-days", type=int, default=90, help="Warning window in days (default: 90)")
    parser.add_argument("--output", "-o", type=str, help="Write report to JSON file")
    args = parser.parse_args()

    if args.today:
        today = parse_date(args.today)
        if today is None:
            print(f"Error: could not parse --today '{args.today}' (expected YYYY-MM-DD).", file=sys.stderr)
            return 1
    else:
        today = date.today()

    try:
        rows = load_csv(args.csv)
    except Exception as e:
        print(f"Error loading CSV: {e}", file=sys.stderr)
        return 1

    if not rows:
        print("Error: no valid rows found in CSV.", file=sys.stderr)
        return 1

    result = analyze(rows, today, args.warn_within_days)
    print_report(result, args.warn_within_days)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2)
        print(f"\n📁 Report saved to {args.output}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
