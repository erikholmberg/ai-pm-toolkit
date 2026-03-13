#!/usr/bin/env python3
"""
Feedback Theme Counter

Count theme or keyword mentions in feedback CSV for prioritization and retros.
Supports predefined themes (--themes) or top N significant words (default).

Usage:
    # Top 20 significant words (stopwords removed)
    python feedback-theme-counter.py --csv feedback.csv

    # Predefined themes: count mentions of pricing, reliability, ux
    python feedback-theme-counter.py --csv feedback.csv --themes "pricing,reliability,ux,support"

    # Top 30 words; optional source column
    python feedback-theme-counter.py --csv feedback.csv --top 30 --group-by source

    # Export
    python feedback-theme-counter.py --csv feedback.csv --output themes.json

CSV format:
    text,source,date
    "Login is slow and often fails",support,2025-01-15
    "Pricing is too high for small teams",sales,2025-01-16

    Required: text (or feedback, comment, content).
    Optional: source, date for --group-by.

Requirements:
    None (stdlib only).
"""

import argparse
import csv
import json
import re
import sys
from collections import Counter, defaultdict
from typing import Any, Dict, List, Optional


def _col(fieldnames: List[str], *aliases: str) -> Optional[str]:
    lower_map = {f.lower().strip(): f for f in fieldnames}
    for alias in aliases:
        if alias.lower().strip() in lower_map:
            return lower_map[alias.lower().strip()]
    return None


# Common stopwords for word-count mode
STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "has", "he",
    "in", "is", "it", "its", "of", "on", "that", "the", "to", "was", "were", "will",
    "with", "i", "we", "they", "this", "but", "or", "if", "so", "can", "just",
    "not", "no", "very", "when", "what", "which", "who", "how", "all", "each",
}

def tokenize(text: str) -> List[str]:
    """Lowercase words (letters + optional apostrophe)."""
    if not text:
        return []
    text = str(text).lower()
    words = re.findall(r"[a-z']+", text)
    return [w for w in words if len(w) > 1]


def load_feedback(
    path: str,
    text_col: str = "text",
    source_col: str = "source",
    date_col: str = "date",
) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fields = reader.fieldnames or []
        c_text = _col(fields, text_col, "text", "feedback", "comment", "content", "body", "message")
        c_source = _col(fields, source_col, "source", "channel", "origin", "segment")
        c_date = _col(fields, date_col, "date", "timestamp", "created")

        for row in reader:
            text = (row.get(c_text or "text", "") or "").strip()
            if not text:
                continue
            source = (row.get(c_source or "source", "") or "").strip() or "—"
            date = (row.get(c_date or "date", "") or "").strip() or ""
            rows.append({"text": text, "source": source, "date": date})
    return rows


def count_themes(feedback: List[Dict[str, Any]], theme_list: List[str]) -> Dict[str, int]:
    """Count how many feedback items mention each theme (word or phrase, case-insensitive)."""
    themes = [t.strip().lower() for t in theme_list if t.strip()]
    counts: Dict[str, int] = {t: 0 for t in themes}
    for row in feedback:
        text = row["text"].lower()
        for t in themes:
            if t in text:
                counts[t] += 1
    return dict(sorted(counts.items(), key=lambda x: -x[1]))


def count_words(feedback: List[Dict[str, Any]], top_n: int, min_len: int) -> List[tuple]:
    """Top N significant words across all feedback (stopwords removed, min length)."""
    word_counts: Counter = Counter()
    for row in feedback:
        for w in tokenize(row["text"]):
            if len(w) >= min_len and w not in STOPWORDS:
                word_counts[w] += 1
    return word_counts.most_common(top_n)


def summarize_by_group(
    feedback: List[Dict[str, Any]],
    theme_list: Optional[List[str]],
    top_n: int,
    group_by: Optional[str],
) -> Dict[str, Any]:
    by_group: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for row in feedback:
        key = row.get("source", "—") if group_by and group_by.lower() in ("source", "channel", "origin") else "—"
        by_group[key].append(row)

    if theme_list:
        overall = count_themes(feedback, theme_list)
        by_group_counts = {}
        for grp, items in by_group.items():
            by_group_counts[grp] = count_themes(items, theme_list)
        return {
            "mode": "themes",
            "themes": overall,
            "total_items": len(feedback),
            "by_group": dict(by_group_counts) if group_by else {},
        }
    else:
        overall = count_words(feedback, top_n, 2)
        by_group_words = {}
        for grp, items in by_group.items():
            by_group_words[grp] = count_words(items, top_n, 2)
        return {
            "mode": "words",
            "top_words": overall,
            "total_items": len(feedback),
            "by_group": dict(by_group_words) if group_by else {},
        }


def print_report(result: Dict[str, Any], theme_mode: bool) -> None:
    print("\n" + "=" * 70)
    print("💬 FEEDBACK THEME COUNTER")
    print("=" * 70)

    n = result.get("total_items", 0)
    print(f"\n   Total feedback items: {n}")
    if n == 0:
        print("\n   No feedback rows in CSV (need text column).\n")
        return

    if theme_mode:
        print("\n   Theme mentions (items containing theme):")
        print("   " + "─" * 36)
        for theme, count in result.get("themes", {}).items():
            pct = (100.0 * count / n) if n else 0
            print(f"   {theme:<24} {count:>6}  ({pct:.0f}%)")
        for grp, counts in result.get("by_group", {}).items():
            print(f"\n   By {grp}:")
            for theme, c in list(counts.items())[:10]:
                print(f"      {theme:<20} {c:>5}")
    else:
        print("\n   Top words (stopwords removed):")
        print("   " + "─" * 36)
        for word, count in result.get("top_words", []):
            print(f"   {word:<24} {count:>6}")
        for grp, words in result.get("by_group", {}).items():
            print(f"\n   By {grp}:")
            for word, c in words[:10]:
                print(f"      {word:<20} {c:>5}")

    print("\n   💡 Use for prioritization and retro themes.\n")


def to_json_result(result: Dict[str, Any]) -> Dict[str, Any]:
    out = {"total_items": result.get("total_items", 0), "mode": result.get("mode", "words")}
    if result.get("mode") == "themes":
        out["themes"] = result.get("themes", {})
    else:
        out["top_words"] = result.get("top_words", [])
    if result.get("by_group"):
        out["by_group"] = result["by_group"]
    return out


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Count theme or keyword mentions in feedback CSV.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--csv", "-c", required=True, help="Path to feedback CSV (text required)")
    parser.add_argument("--themes", "-t", type=str, default=None, metavar="LIST", help="Comma-separated themes to count (e.g. pricing,reliability,ux)")
    parser.add_argument("--top", type=int, default=20, metavar="N", help="Top N words when not using --themes (default: 20)")
    parser.add_argument("--group-by", type=str, default=None, metavar="COL", help="Group counts by column (e.g. source)")
    parser.add_argument("--markdown", metavar="FILE", help="Write Markdown report to FILE")
    parser.add_argument("--output", "-o", metavar="FILE", help="Write JSON result to FILE")
    args = parser.parse_args()

    feedback = load_feedback(args.csv)
    if not feedback:
        print("No feedback rows in CSV (need text column).", file=sys.stderr)
        return 1

    theme_list = [s.strip() for s in args.themes.split(",")] if args.themes else None
    result = summarize_by_group(
        feedback,
        theme_list,
        max(1, args.top),
        args.group_by if args.group_by else None,
    )
    print_report(result, result.get("mode") == "themes")

    if args.markdown and result.get("total_items"):
        with open(args.markdown, "w", encoding="utf-8") as f:
            f.write("# Feedback Theme Counter\n\n")
            f.write(f"- **Total items:** {result['total_items']}\n\n")
            if result.get("mode") == "themes":
                f.write("| Theme | Count | % |\n")
                f.write("|-------|-------|---|\n")
                n = result["total_items"]
                for theme, count in result.get("themes", {}).items():
                    pct = (100.0 * count / n) if n else 0
                    f.write(f"| {theme} | {count} | {pct:.0f}% |\n")
            else:
                f.write("| Word | Count |\n")
                f.write("|------|-------|\n")
                for word, count in result.get("top_words", []):
                    f.write(f"| {word} | {count} |\n")
        print(f"Wrote Markdown to {args.markdown}")

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(to_json_result(result), f, indent=2)
        print(f"Wrote JSON to {args.output}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
