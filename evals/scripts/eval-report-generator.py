#!/usr/bin/env python3
"""
Eval Report Generator

Turn eval results (JSON) into markdown or HTML summaries.

Usage:
    python eval-report-generator.py --input results.json --output report.md
    python eval-report-generator.py --input results.json --output report.html --format html

Requirements:
    None (stdlib only) for markdown; optional jinja2 for fancier HTML
"""

import argparse
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional


def load_results(path: str) -> List[Dict[str, Any]]:
    """Load results from JSON."""
    with open(path, "r") as f:
        data = json.load(f)
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        if "per_case" in data:
            return data["per_case"]
        if "results" in data:
            return data["results"]
    return []


def get_aggregate_scores(results: List[Dict[str, Any]]) -> Dict[str, float]:
    """Compute mean scores across results. Handles scores dict and overall_score."""
    if not results:
        return {}
    dims: Dict[str, List[float]] = {}
    for r in results:
        scores = r.get("scores") or {}
        if isinstance(scores, dict):
            for k, v in scores.items():
                if k != "overall" and v is not None:
                    try:
                        dims.setdefault(k, []).append(float(v))
                    except (TypeError, ValueError):
                        pass
        overall = r.get("overall_score") or (scores.get("overall") if isinstance(scores, dict) else None)
        if overall is not None:
            try:
                dims.setdefault("overall", []).append(float(overall))
            except (TypeError, ValueError):
                pass
    return {k: sum(v) / len(v) for k, v in dims.items() if v}


def generate_markdown(
    results: List[Dict[str, Any]],
    title: str = "Eval Report",
    source_file: Optional[str] = None
) -> str:
    """Generate markdown report."""
    lines = [
        f"# {title}",
        "",
        f"*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}*",
        ""
    ]
    if source_file:
        lines.append(f"*Source: {source_file}*")
        lines.append("")

    agg = get_aggregate_scores(results)
    if agg:
        lines.append("## Summary")
        lines.append("")
        lines.append("| Metric | Mean |")
        lines.append("|--------|------|")
        for k, v in sorted(agg.items()):
            lines.append(f"| {k} | {v:.3f} |")
        lines.append("")
        lines.append(f"*Total cases: {len(results)}*")
        lines.append("")

    # Per-case table (optional, limit rows)
    lines.append("## Per-case results")
    lines.append("")
    if results:
        # Headers from first row
        first = results[0]
        scores = first.get("scores") or {}
        headers = ["id", "overall_score"] + [k for k in sorted(scores.keys()) if k != "overall"]
        lines.append("| " + " | ".join(headers) + " |")
        lines.append("| " + " | ".join("---" for _ in headers) + " |")
        for r in results[:100]:  # cap for readability
            row_id = r.get("test_case_id") or r.get("id") or ""
            overall = r.get("overall_score")
            sc = r.get("scores") or {}
            row_vals = [str(row_id), str(overall) if overall is not None else ""]
            for k in sorted(sc.keys()):
                if k == "overall":
                    continue
                row_vals.append(str(sc.get(k, "")))
            lines.append("| " + " | ".join(row_vals) + " |")
        if len(results) > 100:
            lines.append(f"*... and {len(results) - 100} more cases*")
    lines.append("")
    return "\n".join(lines)


def generate_html(
    results: List[Dict[str, Any]],
    title: str = "Eval Report",
    source_file: Optional[str] = None
) -> str:
    """Generate simple HTML report (no jinja2)."""
    md = generate_markdown(results, title=title, source_file=source_file)
    # Naive markdown-to-HTML: headers and tables only
    html_lines = ["<!DOCTYPE html>", "<html>", "<head>", f"<title>{title}</title>", "<meta charset='utf-8'>", "</head>", "<body>"]
    in_table = False
    for line in md.split("\n"):
        if line.startswith("# "):
            html_lines.append(f"<h1>{line[2:]}</h1>")
        elif line.startswith("## "):
            html_lines.append(f"<h2>{line[3:]}</h2>")
        elif line.startswith("| ") and "---" not in line:
            if not in_table:
                html_lines.append("<table border='1' cellpadding='4'>")
                in_table = True
            cells = [c.strip() for c in line.split("|")[1:-1]]
            tag = "th" if "<th>" not in "".join(html_lines[-3:]) and len(html_lines) > 0 else "td"
            html_lines.append("<tr>" + "".join(f"<{tag}>{c}</{tag}>" for c in cells) + "</tr>")
        elif line.startswith("| ") and "---" in line:
            continue
        elif in_table:
            html_lines.append("</table>")
            in_table = False
        elif line.strip().startswith("*") and line.strip().endswith("*"):
            html_lines.append(f"<p><em>{line.strip()[1:-1]}</em></p>")
        elif line.strip():
            html_lines.append(f"<p>{line}</p>")
    if in_table:
        html_lines.append("</table>")
    html_lines.append("</body></html>")
    return "\n".join(html_lines)


def main():
    parser = argparse.ArgumentParser(description="Generate eval report (markdown or HTML)")
    parser.add_argument("--input", "-i", required=True, help="Input results JSON")
    parser.add_argument("--output", "-o", required=True, help="Output report path")
    parser.add_argument("--title", "-t", default="Eval Report", help="Report title")
    parser.add_argument("--format", "-f", choices=["md", "markdown", "html"], default="md",
                       help="Output format")
    args = parser.parse_args()

    if not Path(args.input).exists():
        print(f"Input file not found: {args.input}")
        return 1

    results = load_results(args.input)
    if not results:
        print("No results found in input.")
        return 1

    if args.format == "html":
        content = generate_html(results, title=args.title, source_file=args.input)
    else:
        content = generate_markdown(results, title=args.title, source_file=args.input)

    with open(args.output, "w") as f:
        f.write(content)
    print(f"Wrote report to {args.output} ({len(results)} cases)")
    return 0


if __name__ == "__main__":
    exit(main())