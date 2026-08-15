#!/usr/bin/env python3
"""
Red-Team Coverage Tracker

Track adversarial/red-team test-case coverage across a standard taxonomy of
AI risk categories, so a PM can see coverage gaps before launch instead of
discovering them in production. Ships with a built-in default taxonomy
(editable via --categories-file) and reports pass rate, coverage, and a
go/no-go readiness flag per category.

Usage:
    python red-team-coverage-tracker.py --csv redteam_results.csv
    python red-team-coverage-tracker.py --csv redteam_results.csv --min-tests-per-category 10
    python red-team-coverage-tracker.py --csv redteam_results.csv --categories-file custom_taxonomy.json
    python red-team-coverage-tracker.py --list-taxonomy

CSV format (header row required):
    test_id,category,status
    rt001,jailbreak_instruction_override,pass
    rt002,prompt_injection_indirect,fail
    rt003,pii_data_leakage,pass

    Required columns (fuzzy-matched): test_id (or id), category, status
    (pass/fail/not_run). Category values are matched against the taxonomy
    case-insensitively; unrecognized categories are still tallied under an
    "other" bucket so nothing is silently dropped.

Requirements:
    None (stdlib only).
"""

import argparse
import csv
import json
import sys
from collections import defaultdict
from typing import Any, Dict, List, Optional

# Shared result envelope (provenance + machine-readable chaining).
# See scripts/toolkit_io.py.
import toolkit_io

TOOL = "red-team-coverage-tracker"


# ---------------------------------------------------------------------------
# Default risk taxonomy
# ---------------------------------------------------------------------------

DEFAULT_TAXONOMY: Dict[str, str] = {
    "jailbreak_instruction_override": "Attempts to override system instructions or safety behavior",
    "prompt_injection_indirect": "Instruction hijacking via tool output, RAG content, or other indirect channels",
    "pii_data_leakage": "Leakage of personal, confidential, or training data",
    "harmful_content_generation": "Generation of harmful, illegal, or dangerous content",
    "bias_fairness": "Biased, discriminatory, or unfair outputs across protected groups",
    "misinformation_hallucination_under_pressure": "Confident fabrication when pressured or adversarially prompted",
    "excessive_agency_unauthorized_tool_use": "Unauthorized or out-of-scope tool/action use by the agent",
    "denial_of_wallet_cost_abuse": "Cost-abuse patterns that can run up API/infra spend",
    "off_topic_brand_safety": "Off-topic, off-brand, or reputationally risky responses",
}

PASS_VALUES = {"pass", "passed", "yes", "true", "1", "ok"}
FAIL_VALUES = {"fail", "failed", "no", "false", "0"}
NOT_RUN_VALUES = {"not_run", "not run", "notrun", "pending", "skipped", "n/a", "na", ""}


def normalize_status(val: str) -> str:
    v = str(val).strip().lower()
    if v in PASS_VALUES:
        return "pass"
    if v in FAIL_VALUES:
        return "fail"
    return "not_run"


# ---------------------------------------------------------------------------
# Taxonomy loading
# ---------------------------------------------------------------------------

def load_taxonomy(path: Optional[str]) -> Dict[str, str]:
    if not path:
        return dict(DEFAULT_TAXONOMY)
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, list):
        return {str(c): "" for c in data}
    if isinstance(data, dict):
        return {str(k): str(v) for k, v in data.items()}
    raise ValueError("categories-file must be a JSON list of category names or an object of {category: description}")


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def _col(fieldnames: List[str], *aliases: str) -> Optional[str]:
    lower_map = {f.lower().strip(): f for f in fieldnames}
    for alias in aliases:
        if alias.lower().strip() in lower_map:
            return lower_map[alias.lower().strip()]
    return None


def load_csv(path: str, taxonomy: Dict[str, str]) -> List[Dict[str, Any]]:
    taxonomy_lookup = {k.lower(): k for k in taxonomy}
    rows: List[Dict[str, Any]] = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fields = reader.fieldnames or []
        c_id = _col(fields, "test_id", "id", "case_id")
        c_category = _col(fields, "category", "type", "class", "risk_category")
        c_status = _col(fields, "status", "result", "outcome")

        if not c_category or not c_status:
            raise ValueError("CSV must have category and status columns.")

        for i, row in enumerate(reader):
            cat_raw = (row.get(c_category, "") or "").strip()
            if not cat_raw:
                continue
            cat_key = taxonomy_lookup.get(cat_raw.lower(), cat_raw.lower().replace(" ", "_") or "other")
            rows.append({
                "test_id": (row.get(c_id, "") or "").strip() or f"test_{i + 1}",
                "category": cat_key,
                "status": normalize_status(row.get(c_status, "")),
            })
    return rows


# ---------------------------------------------------------------------------
# Core calculations
# ---------------------------------------------------------------------------

def analyze(
    rows: List[Dict[str, Any]],
    taxonomy: Dict[str, str],
    min_tests_per_category: int,
    max_fail_rate: float,
) -> Dict[str, Any]:
    by_category: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for r in rows:
        by_category[r["category"]].append(r)

    # Ensure every taxonomy category is represented, even with zero tests.
    all_categories = set(taxonomy.keys()) | set(by_category.keys())

    category_stats: Dict[str, Any] = {}
    for cat in sorted(all_categories):
        cat_rows = by_category.get(cat, [])
        n_pass = sum(1 for r in cat_rows if r["status"] == "pass")
        n_fail = sum(1 for r in cat_rows if r["status"] == "fail")
        n_not_run = sum(1 for r in cat_rows if r["status"] == "not_run")
        n_executed = n_pass + n_fail  # tests actually run (pass or fail)
        n_total = len(cat_rows)
        fail_rate = n_fail / n_executed if n_executed else 0.0
        pass_rate = n_pass / n_executed if n_executed else 0.0

        if n_total == 0:
            readiness = "🚫 LAUNCH BLOCKER — zero test cases"
        elif n_executed < min_tests_per_category:
            readiness = f"🔴 NOT READY — only {n_executed} executed (need {min_tests_per_category})"
        elif fail_rate > max_fail_rate:
            readiness = f"🔴 NOT READY — fail rate {fail_rate:.0%} exceeds {max_fail_rate:.0%}"
        else:
            readiness = "🟢 READY"

        category_stats[cat] = {
            "in_default_taxonomy": cat in taxonomy,
            "description": taxonomy.get(cat, ""),
            "n_total": n_total,
            "n_pass": n_pass,
            "n_fail": n_fail,
            "n_not_run": n_not_run,
            "n_executed": n_executed,
            "pass_rate": round(pass_rate, 4),
            "fail_rate": round(fail_rate, 4),
            "readiness": readiness,
        }

    covered_categories = sum(1 for s in category_stats.values() if s["n_total"] > 0)
    taxonomy_size = len(taxonomy)
    coverage_pct = (covered_categories / taxonomy_size * 100) if taxonomy_size else 0.0
    blockers = [c for c, s in category_stats.items() if s["n_total"] == 0 and c in taxonomy]
    not_ready = [c for c, s in category_stats.items() if s["readiness"].startswith("🔴")]

    overall_go = not blockers and not not_ready

    return {
        "n_tests": len(rows),
        "taxonomy_size": taxonomy_size,
        "categories_covered": covered_categories,
        "coverage_pct": round(coverage_pct, 1),
        "by_category": category_stats,
        "launch_blockers": blockers,
        "not_ready_categories": not_ready,
        "overall_readiness": "🟢 GO" if overall_go else "🔴 NO-GO",
    }


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def _bar(value: float, width: int = 20) -> str:
    value = max(0.0, min(1.0, value))
    filled = int(value * width)
    return "█" * filled + "░" * (width - filled)


def print_report(result: Dict[str, Any], min_tests: int, max_fail_rate: float) -> None:
    print("\n" + "=" * 78)
    print("📊 RED-TEAM COVERAGE TRACKER")
    print("=" * 78)

    print(f"\n📋 OVERVIEW:")
    print(f"   • Test cases loaded:      {result['n_tests']}")
    print(f"   • Taxonomy categories:    {result['taxonomy_size']}")
    print(f"   • Categories with tests:  {result['categories_covered']}/{result['taxonomy_size']}")
    print(f"   • Coverage:               {result['coverage_pct']:.1f}%  {_bar(result['coverage_pct'] / 100)}")
    print(f"   • Overall readiness:      {result['overall_readiness']}")
    print(f"   • Thresholds:             min {min_tests} executed tests/category, "
          f"max {max_fail_rate:.0%} fail rate")

    print(f"\n📈 COVERAGE BY CATEGORY:")
    print(f"   {'Category':<44} {'Run':>5} {'Pass':>5} {'Fail':>5} {'NR':>4}  {'Readiness'}")
    print(f"   {'─'*44} {'─'*5} {'─'*5} {'─'*5} {'─'*4}  {'─'*30}")
    for cat, s in result["by_category"].items():
        label = cat if len(cat) <= 44 else cat[:41] + "..."
        print(
            f"   {label:<44} {s['n_executed']:>5} {s['n_pass']:>5} {s['n_fail']:>5} {s['n_not_run']:>4}  {s['readiness']}"
        )

    if result["launch_blockers"]:
        print(f"\n🚫 LAUNCH BLOCKERS (zero test coverage):")
        for cat in result["launch_blockers"]:
            desc = result["by_category"][cat]["description"]
            print(f"   • {cat}" + (f" — {desc}" if desc else ""))
    else:
        print(f"\n✅ No categories with zero test coverage.")

    other_not_ready = [c for c in result["not_ready_categories"] if c not in result["launch_blockers"]]
    if other_not_ready:
        print(f"\n⚠️  NOT READY (insufficient tests or too many failures):")
        for cat in other_not_ready:
            s = result["by_category"][cat]
            print(f"   • {cat} — {s['readiness']}")

    print(f"\n💡 SUMMARY: {result['overall_readiness']} — ", end="")
    if result["overall_readiness"] == "🟢 GO":
        print("every taxonomy category has adequate, passing red-team coverage.")
    else:
        n_issues = len(set(result["launch_blockers"]) | set(result["not_ready_categories"]))
        print(f"{n_issues} categor{'y needs' if n_issues == 1 else 'ies need'} attention before launch.")

    print("\n" + "=" * 78)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Track red-team test coverage across a standard AI risk taxonomy and flag "
                    "launch-blocking gaps.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --csv redteam_results.csv
  %(prog)s --csv redteam_results.csv --min-tests-per-category 10
  %(prog)s --csv redteam_results.csv --categories-file custom_taxonomy.json
  %(prog)s --list-taxonomy
        """,
    )
    parser.add_argument("--csv", "-c", type=str, help="CSV with test_id, category, status columns")
    parser.add_argument("--categories-file", type=str, help="JSON file with a custom taxonomy (list or {category: description})")
    parser.add_argument("--min-tests-per-category", type=int, default=5, help="Minimum executed tests per category to be launch-ready (default: 5)")
    parser.add_argument("--max-fail-rate", type=float, default=0.0, help="Maximum acceptable fail rate per category (default: 0.0)")
    parser.add_argument("--list-taxonomy", action="store_true", help="List the (default or custom) taxonomy and exit")
    parser.add_argument("--output", "-o", type=str, help="Write report to JSON file")
    args = parser.parse_args()

    try:
        taxonomy = load_taxonomy(args.categories_file)
    except Exception as e:
        print(f"Error loading taxonomy: {e}", file=sys.stderr)
        return 1

    if args.list_taxonomy:
        print(f"\n📋 RISK TAXONOMY ({len(taxonomy)} categories):\n")
        for cat, desc in taxonomy.items():
            print(f"   • {cat}")
            if desc:
                print(f"     {desc}")
        print()
        return 0

    if not args.csv:
        print("Error: --csv is required (or use --list-taxonomy).", file=sys.stderr)
        parser.print_help(sys.stderr)
        return 1

    try:
        rows = load_csv(args.csv, taxonomy)
    except Exception as e:
        print(f"Error loading CSV: {e}", file=sys.stderr)
        return 1

    if not rows:
        print("Error: no valid rows found in CSV.", file=sys.stderr)
        return 1

    result = analyze(rows, taxonomy, args.min_tests_per_category, args.max_fail_rate)
    print_report(result, args.min_tests_per_category, args.max_fail_rate)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(toolkit_io.envelope(result, TOOL), f, indent=2)
        print(f"\n📁 Report saved to {args.output}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
