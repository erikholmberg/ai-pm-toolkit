#!/usr/bin/env python3
"""
Eval Summary Report Generator

Consume JSON or CSV from prompt-eval-harness (or similar) and produce a one-page
Markdown summary: pass rate, results by category, avg latency/tokens, and
comparison across prompt versions.

Usage:
    python eval-summary-report.py results.json
    python eval-summary-report.py results.json --output report.md
    python eval-summary-report.py results.csv
    python eval-summary-report.py results.json --stdout

Expects JSON: list of objects with test_case_id, prompt_version, latency_ms, tokens_used, scores (dict).
CSV: same columns where applicable.
"""

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional
from collections import defaultdict


def load_json(path: Path) -> List[Dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, list):
        return data
    if isinstance(data, dict) and "results" in data:
        return data["results"]
    return [data]


def load_csv(path: Path) -> List[Dict[str, Any]]:
    rows = []
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Coerce numeric fields
            for key in ("latency_ms", "tokens_used"):
                if key in row and row[key]:
                    try:
                        row[key] = float(row[key])
                    except ValueError:
                        pass
            if "scores" in row and row["scores"]:
                try:
                    row["scores"] = json.loads(row["scores"])
                except (json.JSONDecodeError, TypeError):
                    row["scores"] = {}
            rows.append(row)
    return rows


def load_results(path: Path) -> List[Dict[str, Any]]:
    suffix = path.suffix.lower()
    if suffix == ".json":
        return load_json(path)
    if suffix == ".csv":
        return load_csv(path)
    raise ValueError(f"Unsupported format: {suffix}. Use .json or .csv")


def first_score_value(scores: Any) -> Optional[float]:
    """Single numeric score for pass/fail (e.g. 0/1 or 0-1)."""
    if not scores or not isinstance(scores, dict):
        return None
    for v in scores.values():
        if isinstance(v, (int, float)):
            return float(v)
    return None


def summarize(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Build summary stats: by prompt_version, and overall."""
    by_version: Dict[str, List[Dict]] = defaultdict(list)
    for r in results:
        ver = r.get("prompt_version") or "default"
        by_version[ver].append(r)

    summary = {"by_version": {}, "overall": {}}
    all_latencies = []
    all_tokens = []
    all_scores = []

    for version, rows in by_version.items():
        latencies = [x.get("latency_ms") for x in rows if x.get("latency_ms") is not None]
        tokens = [x.get("tokens_used") for x in rows if x.get("tokens_used") is not None]
        scores_list = []
        for x in rows:
            s = first_score_value(x.get("scores"))
            if s is not None:
                scores_list.append(s)
        pass_count = sum(1 for s in scores_list if s >= 0.99 or s == 1.0)
        total_scored = len(scores_list)
        pass_rate = (pass_count / total_scored * 100) if total_scored else None

        summary["by_version"][version] = {
            "count": len(rows),
            "avg_latency_ms": sum(latencies) / len(latencies) if latencies else None,
            "avg_tokens": sum(tokens) / len(tokens) if tokens else None,
            "pass_rate_pct": pass_rate,
            "pass_count": pass_count,
            "total_scored": total_scored,
            "avg_score": sum(scores_list) / len(scores_list) if scores_list else None,
        }
        all_latencies.extend(latencies)
        all_tokens.extend(tokens)
        all_scores.extend(scores_list)

    summary["overall"] = {
        "total_cases": len(results),
        "versions": list(by_version.keys()),
        "avg_latency_ms": sum(all_latencies) / len(all_latencies) if all_latencies else None,
        "avg_tokens": sum(all_tokens) / len(all_tokens) if all_tokens else None,
        "pass_rate_pct": (
            (sum(1 for s in all_scores if s >= 0.99 or s == 1.0) / len(all_scores) * 100)
            if all_scores else None
        ),
    }
    return summary


def by_category(results: List[Dict[str, Any]]) -> Dict[str, List[Dict]]:
    """Group results by category if present (e.g. metadata.category or category)."""
    by_cat: Dict[str, List[Dict]] = defaultdict(list)
    for r in results:
        cat = None
        if isinstance(r.get("metadata"), dict) and "category" in r["metadata"]:
            cat = r["metadata"]["category"]
        elif r.get("category"):
            cat = r["category"]
        by_cat[cat or "uncategorized"].append(r)
    return dict(by_cat)


def render_markdown(summary: Dict[str, Any], results: List[Dict[str, Any]], title: str = "Eval Summary") -> str:
    lines = [
        f"# {title}",
        "",
        "## Overview",
        "",
        f"- **Total cases:** {summary['overall']['total_cases']}",
        f"- **Prompt versions:** {', '.join(summary['overall']['versions'])}",
        "",
    ]
    if summary["overall"].get("avg_latency_ms") is not None:
        lines.append(f"- **Avg latency:** {summary['overall']['avg_latency_ms']:.0f} ms")
    if summary["overall"].get("avg_tokens") is not None:
        lines.append(f"- **Avg tokens:** {summary['overall']['avg_tokens']:.0f}")
    if summary["overall"].get("pass_rate_pct") is not None:
        lines.append(f"- **Overall pass rate:** {summary['overall']['pass_rate_pct']:.1f}%")
    lines.extend(["", "## By prompt version", ""])

    for version, stats in summary["by_version"].items():
        lines.append(f"### {version}")
        lines.append("")
        lines.append(f"- Cases: {stats['count']}")
        if stats.get("avg_latency_ms") is not None:
            lines.append(f"- Avg latency: {stats['avg_latency_ms']:.0f} ms")
        if stats.get("avg_tokens") is not None:
            lines.append(f"- Avg tokens: {stats['avg_tokens']:.0f}")
        if stats.get("pass_rate_pct") is not None:
            lines.append(f"- Pass rate: {stats['pass_rate_pct']:.1f}% ({stats.get('pass_count', 0)}/{stats.get('total_scored', 0)})")
        if stats.get("avg_score") is not None:
            lines.append(f"- Avg score: {stats['avg_score']:.3f}")
        lines.append("")

    by_cat = by_category(results)
    if len(by_cat) > 1 or (len(by_cat) == 1 and "uncategorized" not in by_cat):
        lines.extend(["## By category", ""])
        for cat, cat_results in sorted(by_cat.items()):
            n = len(cat_results)
            scores = [first_score_value(r.get("scores")) for r in cat_results]
            scores = [s for s in scores if s is not None]
            pass_pct = (sum(1 for s in scores if s >= 0.99 or s == 1.0) / len(scores) * 100) if scores else None
            lines.append(f"- **{cat}:** {n} cases" + (f", pass rate {pass_pct:.1f}%" if pass_pct is not None else ""))
        lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Generate a one-page Markdown summary from eval JSON/CSV (e.g. from prompt-eval-harness)."
    )
    parser.add_argument(
        "input",
        type=Path,
        help="Path to eval results (.json or .csv)",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        help="Write report to this file (default: stdout or input with .md suffix)",
    )
    parser.add_argument(
        "--stdout",
        action="store_true",
        help="Print report to stdout",
    )
    parser.add_argument(
        "--title",
        type=str,
        default="Eval Summary",
        help="Report title (default: Eval Summary)",
    )
    args = parser.parse_args()

    if not args.input.exists():
        print(f"Error: file not found: {args.input}", file=sys.stderr)
        return 1

    try:
        results = load_results(args.input)
    except Exception as e:
        print(f"Error loading results: {e}", file=sys.stderr)
        return 1

    if not results:
        print("Error: no results in file", file=sys.stderr)
        return 1

    summary = summarize(results)
    md = render_markdown(summary, results, title=args.title)

    if args.stdout:
        print(md)
        return 0

    out_path = args.output
    if out_path is None:
        out_path = args.input.with_suffix(".md")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(md)
    print(f"Wrote: {out_path}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
