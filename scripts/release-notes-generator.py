#!/usr/bin/env python3
"""
Release Notes Generator

Generate formatted release notes from git commits, a CSV of tickets, or a JSON
changelog. Groups entries by category (features, fixes, improvements, etc.),
deduplicates, and outputs Markdown or terminal-formatted notes.

Usage:
    # From git log (current repo, last N commits or since a tag/date)
    python release-notes-generator.py --git --since v1.2.0
    python release-notes-generator.py --git --since "2025-06-01" --until "2025-06-14"
    python release-notes-generator.py --git --last 50

    # From CSV of tickets / changelog entries
    python release-notes-generator.py --csv changelog.csv

    # From JSON
    python release-notes-generator.py --json changes.json

    # Output as Markdown file
    python release-notes-generator.py --git --since v1.3.0 --markdown release-v1.4.md

    # With version label
    python release-notes-generator.py --csv changelog.csv --version "v2.1.0" --date "2025-06-15"

CSV format:
    title,category,author,ticket
    Add SSO support,feature,alice,PROJ-123
    Fix login timeout,fix,bob,PROJ-456
    Upgrade to Python 3.12,chore,carol,PROJ-789
    Improve dashboard load time,improvement,dave,PROJ-101
    ...

    Required: title
    Optional: category, author, ticket, description, breaking

JSON format:
    {
      "version": "v2.1.0",
      "entries": [
        {"title": "Add SSO support", "category": "feature", "author": "alice"},
        ...
      ]
    }

Git commit conventions detected:
    feat: / feature:    → Feature
    fix: / bugfix:      → Bug Fix
    perf: / performance → Improvement
    docs:               → Documentation
    chore: / build:     → Chore
    refactor:           → Improvement
    test:               → Testing
    ci:                 → CI/CD
    BREAKING CHANGE     → Breaking Change

Requirements:
    None (stdlib only). Git must be installed for --git mode.
"""

import argparse
import csv
import json
import os
import re
import subprocess
import sys
from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Category detection
# ---------------------------------------------------------------------------

CATEGORY_MAP = {
    "feat": "Feature",
    "feature": "Feature",
    "add": "Feature",
    "new": "Feature",
    "fix": "Bug Fix",
    "bugfix": "Bug Fix",
    "bug": "Bug Fix",
    "hotfix": "Bug Fix",
    "patch": "Bug Fix",
    "perf": "Improvement",
    "performance": "Improvement",
    "improve": "Improvement",
    "improvement": "Improvement",
    "enhance": "Improvement",
    "enhancement": "Improvement",
    "update": "Improvement",
    "optimize": "Improvement",
    "refactor": "Improvement",
    "docs": "Documentation",
    "doc": "Documentation",
    "documentation": "Documentation",
    "chore": "Chore",
    "build": "Chore",
    "deps": "Chore",
    "dependency": "Chore",
    "ci": "CI/CD",
    "cd": "CI/CD",
    "test": "Testing",
    "tests": "Testing",
    "testing": "Testing",
    "style": "Style",
    "breaking": "Breaking Change",
    "deprecate": "Deprecation",
    "deprecated": "Deprecation",
    "remove": "Removal",
    "revert": "Revert",
    "security": "Security",
}

CATEGORY_EMOJI = {
    "Feature": "✨",
    "Bug Fix": "🐛",
    "Improvement": "⚡",
    "Documentation": "📝",
    "Chore": "🔧",
    "CI/CD": "🔄",
    "Testing": "🧪",
    "Style": "🎨",
    "Breaking Change": "💥",
    "Deprecation": "⚠️",
    "Removal": "🗑️",
    "Revert": "⏪",
    "Security": "🔒",
    "Other": "📦",
}

CATEGORY_ORDER = [
    "Breaking Change", "Feature", "Improvement", "Bug Fix", "Security",
    "Documentation", "Testing", "CI/CD", "Chore", "Style",
    "Deprecation", "Removal", "Revert", "Other",
]


def detect_category(text: str) -> str:
    """Detect category from commit message or title."""
    lower = text.lower().strip()

    # Conventional commit prefix: "type: message" or "type(scope): message"
    match = re.match(r"^(\w+)(?:\([^)]*\))?[!]?:\s*", lower)
    if match:
        prefix = match.group(1)
        if prefix in CATEGORY_MAP:
            return CATEGORY_MAP[prefix]

    # Check for BREAKING CHANGE
    if "breaking change" in lower or "breaking:" in lower:
        return "Breaking Change"

    # Keyword heuristics
    for keyword, category in CATEGORY_MAP.items():
        if lower.startswith(keyword + " ") or lower.startswith(keyword + ":"):
            return category

    return "Other"


def clean_title(text: str) -> str:
    """Remove conventional commit prefix and clean up the title."""
    # Remove "type: " or "type(scope): " prefix
    cleaned = re.sub(r"^(\w+)(?:\([^)]*\))?[!]?:\s*", "", text.strip())
    # Capitalize first letter
    if cleaned:
        cleaned = cleaned[0].upper() + cleaned[1:]
    return cleaned


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_git_log(
    since: Optional[str] = None,
    until: Optional[str] = None,
    last: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """Load entries from git log."""
    cmd = ["git", "log", "--pretty=format:%H|||%an|||%ae|||%aI|||%s"]

    if last:
        cmd.append(f"-{last}")
    else:
        if since:
            cmd.append(f"--since={since}" if _is_date(since) else f"{since}..HEAD")
        if until:
            cmd.append(f"--until={until}")

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            raise RuntimeError(f"git log failed: {result.stderr.strip()}")
    except FileNotFoundError:
        raise RuntimeError("git not found. Install git or use --csv/--json instead.")
    except subprocess.TimeoutExpired:
        raise RuntimeError("git log timed out after 30 seconds. Try narrowing the range with --last or --since.")

    entries: List[Dict[str, Any]] = []
    for line in result.stdout.strip().split("\n"):
        if not line.strip():
            continue
        parts = line.split("|||")
        if len(parts) < 5:
            continue
        sha, author, email, date, subject = parts[0], parts[1], parts[2], parts[3], "|||".join(parts[4:])

        category = detect_category(subject)
        title = clean_title(subject)

        entries.append({
            "title": title,
            "raw_title": subject,
            "category": category,
            "author": author,
            "email": email,
            "date": date[:10],
            "sha": sha[:8],
            "ticket": _extract_ticket(subject),
            "breaking": "breaking" in subject.lower() or subject.endswith("!"),
        })

    return entries


def _is_date(s: str) -> bool:
    """Check if string looks like a date rather than a git ref."""
    return bool(re.match(r"^\d{4}-\d{2}-\d{2}", s))


def _extract_ticket(text: str) -> Optional[str]:
    """Extract ticket ID like PROJ-123 or #456 from text."""
    match = re.search(r"([A-Z]+-\d+)", text)
    if match:
        return match.group(1)
    match = re.search(r"#(\d+)", text)
    if match:
        return f"#{match.group(1)}"
    return None


def _col(fieldnames: List[str], *aliases: str) -> Optional[str]:
    lower_map = {f.lower().strip(): f for f in fieldnames}
    for alias in aliases:
        if alias.lower().strip() in lower_map:
            return lower_map[alias.lower().strip()]
    return None


def load_csv(path: str) -> List[Dict[str, Any]]:
    """Load entries from CSV."""
    entries: List[Dict[str, Any]] = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fields = reader.fieldnames or []

        c_title = _col(fields, "title", "summary", "subject", "message", "description", "name")
        c_category = _col(fields, "category", "type", "kind", "label")
        c_author = _col(fields, "author", "assignee", "owner", "user")
        c_ticket = _col(fields, "ticket", "ticket_id", "issue", "jira", "id", "key")
        c_breaking = _col(fields, "breaking", "breaking_change")
        c_desc = _col(fields, "description", "details", "body", "notes")

        for row in reader:
            title = row.get(c_title or "title", "").strip()
            if not title:
                continue

            raw_cat = row.get(c_category or "", "").strip().lower()
            if raw_cat and raw_cat in CATEGORY_MAP:
                category = CATEGORY_MAP[raw_cat]
            elif raw_cat:
                category = raw_cat.title()
            else:
                category = detect_category(title)

            entries.append({
                "title": clean_title(title) if category != "Other" else title,
                "raw_title": title,
                "category": category,
                "author": row.get(c_author or "", "").strip() or None,
                "ticket": row.get(c_ticket or "", "").strip() or _extract_ticket(title),
                "description": row.get(c_desc or "", "").strip() or None,
                "breaking": row.get(c_breaking or "", "").strip().lower() in ("true", "yes", "1", "y"),
            })

    return entries


def load_json(path: str) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    """Load entries from JSON. Returns (entries, version)."""
    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    version = data.get("version")
    raw_entries = data.get("entries", data if isinstance(data, list) else [])

    entries: List[Dict[str, Any]] = []
    for item in raw_entries:
        title = item.get("title", item.get("summary", "")).strip()
        if not title:
            continue

        raw_cat = item.get("category", item.get("type", "")).lower()
        category = CATEGORY_MAP.get(raw_cat, raw_cat.title() if raw_cat else detect_category(title))

        entries.append({
            "title": clean_title(title) if category != "Other" else title,
            "raw_title": title,
            "category": category,
            "author": item.get("author"),
            "ticket": item.get("ticket") or _extract_ticket(title),
            "description": item.get("description"),
            "breaking": item.get("breaking", False),
        })

    return entries, version


# ---------------------------------------------------------------------------
# Grouping and deduplication
# ---------------------------------------------------------------------------

def group_entries(entries: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """Group entries by category, ordered by CATEGORY_ORDER."""
    groups: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for entry in entries:
        groups[entry["category"]].append(entry)

    ordered: Dict[str, List[Dict[str, Any]]] = {}
    for cat in CATEGORY_ORDER:
        if cat in groups:
            ordered[cat] = groups.pop(cat)
    for cat in sorted(groups.keys()):
        ordered[cat] = groups[cat]

    return ordered


def deduplicate(entries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Remove duplicate entries based on title similarity."""
    seen_titles: set = set()
    unique: List[Dict[str, Any]] = []
    for entry in entries:
        normalized = re.sub(r"\s+", " ", entry["title"].lower().strip())
        if normalized not in seen_titles:
            seen_titles.add(normalized)
            unique.append(entry)
    return unique


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def print_report(
    grouped: Dict[str, List[Dict[str, Any]]],
    total: int,
    version: Optional[str],
    date: Optional[str],
    authors: Dict[str, int],
) -> None:
    """Pretty-print release notes to terminal."""
    print("\n" + "=" * 78)
    print("📋 RELEASE NOTES GENERATOR")
    print("=" * 78)

    header = "📦 RELEASE"
    if version:
        header += f" {version}"
    if date:
        header += f" — {date}"
    print(f"\n{header}")
    print(f"   {total} changes across {len(grouped)} categories\n")

    for category, entries in grouped.items():
        emoji = CATEGORY_EMOJI.get(category, "📦")
        print(f"{'─'*78}")
        print(f"\n{emoji} {category.upper()} ({len(entries)})\n")

        for entry in entries:
            parts = [f"   • {entry['title']}"]
            meta = []
            if entry.get("ticket"):
                meta.append(entry["ticket"])
            if entry.get("author"):
                meta.append(f"@{entry['author']}")
            if entry.get("sha"):
                meta.append(entry["sha"])
            if meta:
                parts.append(f" ({', '.join(meta)})")
            print("".join(parts))

            if entry.get("description"):
                for line in entry["description"].split("\n"):
                    print(f"     {line}")

    # Stats
    print(f"\n{'─'*78}")
    print(f"\n📊 SUMMARY:")
    for cat, entries in grouped.items():
        emoji = CATEGORY_EMOJI.get(cat, "📦")
        print(f"   {emoji} {cat}: {len(entries)}")

    if authors:
        print(f"\n👥 CONTRIBUTORS ({len(authors)}):")
        for author, count in sorted(authors.items(), key=lambda x: -x[1])[:10]:
            print(f"   • {author}: {count} change{'s' if count > 1 else ''}")

    breaking = sum(1 for entries in grouped.values() for e in entries if e.get("breaking"))
    if breaking:
        print(f"\n💥 BREAKING CHANGES: {breaking}")

    print("\n" + "=" * 78)


# ---------------------------------------------------------------------------
# Markdown output
# ---------------------------------------------------------------------------

def generate_markdown(
    grouped: Dict[str, List[Dict[str, Any]]],
    total: int,
    version: Optional[str],
    date: Optional[str],
    authors: Dict[str, int],
) -> str:
    """Generate Markdown release notes."""
    lines: List[str] = []

    header = "Release"
    if version:
        header += f" {version}"
    if date:
        header += f" ({date})"
    lines.append(f"# {header}\n")
    lines.append(f"*{total} changes*\n")

    # Breaking changes first as a callout
    breaking_entries = [e for entries in grouped.values() for e in entries if e.get("breaking")]
    if breaking_entries:
        lines.append("> **Breaking Changes**")
        for e in breaking_entries:
            lines.append(f"> - {e['title']}")
        lines.append("")

    for category, entries in grouped.items():
        emoji = CATEGORY_EMOJI.get(category, "📦")
        lines.append(f"## {emoji} {category}\n")

        for entry in entries:
            parts = [f"- {entry['title']}"]
            meta = []
            if entry.get("ticket"):
                meta.append(f"`{entry['ticket']}`")
            if entry.get("author"):
                meta.append(f"@{entry['author']}")
            if meta:
                parts.append(f" ({', '.join(meta)})")
            lines.append("".join(parts))

            if entry.get("description"):
                for line in entry["description"].split("\n"):
                    lines.append(f"  {line}")
        lines.append("")

    # Contributors
    if authors:
        lines.append("## 👥 Contributors\n")
        for author, count in sorted(authors.items(), key=lambda x: -x[1]):
            lines.append(f"- **{author}** ({count} change{'s' if count > 1 else ''})")
        lines.append("")

    lines.append(f"---\n*Generated by release-notes-generator.py*\n")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Generate formatted release notes from git commits, CSV, or JSON. "
                    "Groups by category, deduplicates, and outputs terminal or Markdown.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --git --since v1.2.0
  %(prog)s --git --since "2025-06-01" --until "2025-06-14"
  %(prog)s --git --last 50 --markdown release.md
  %(prog)s --csv changelog.csv --version "v2.1.0"
  %(prog)s --json changes.json --markdown notes.md
        """,
    )

    source = parser.add_mutually_exclusive_group()
    source.add_argument("--git", action="store_true", help="Read from git log")
    source.add_argument("--csv", "-c", type=str, help="CSV file with changelog entries")
    source.add_argument("--json", "-j", type=str, help="JSON file with changelog entries")

    # Git options
    parser.add_argument("--since", type=str, help="Git: start ref (tag, commit, or date)")
    parser.add_argument("--until", type=str, help="Git: end ref or date (default: HEAD)")
    parser.add_argument("--last", type=int, help="Git: last N commits")

    # Output
    parser.add_argument("--version", "-v", type=str, help="Version label (e.g. v2.1.0)")
    parser.add_argument("--date", "-d", type=str, help="Release date (default: today)")
    parser.add_argument("--markdown", "-m", type=str, help="Write Markdown to file")
    parser.add_argument("--output", "-o", type=str, help="Write JSON results to file")
    parser.add_argument("--no-dedup", action="store_true", help="Skip deduplication")
    parser.add_argument("--exclude", type=str, nargs="*",
                        help="Categories to exclude (e.g. Chore Testing Style)")

    args = parser.parse_args()

    # Load entries
    entries: List[Dict[str, Any]] = []
    version = args.version

    if args.git:
        if not args.since and not args.last:
            args.last = 30
        try:
            entries = load_git_log(since=args.since, until=args.until, last=args.last)
        except RuntimeError as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1
    elif args.csv:
        try:
            entries = load_csv(args.csv)
        except Exception as e:
            print(f"Error loading CSV: {e}", file=sys.stderr)
            return 1
    elif args.json:
        try:
            entries, json_version = load_json(args.json)
            if not version and json_version:
                version = json_version
        except Exception as e:
            print(f"Error loading JSON: {e}", file=sys.stderr)
            return 1
    else:
        print("Error: provide --git, --csv, or --json.", file=sys.stderr)
        parser.print_help(sys.stderr)
        return 1

    if not entries:
        print("No entries found.", file=sys.stderr)
        return 1

    # Dedup
    total_raw = len(entries)
    if not args.no_dedup:
        entries = deduplicate(entries)
    deduped = total_raw - len(entries)

    # Exclude categories
    if args.exclude:
        exclude_lower = {e.lower() for e in args.exclude}
        entries = [e for e in entries if e["category"].lower() not in exclude_lower]

    # Elevate breaking changes
    for entry in entries:
        if entry.get("breaking") and entry["category"] != "Breaking Change":
            entry["category"] = "Breaking Change"

    # Group
    grouped = group_entries(entries)
    total = sum(len(v) for v in grouped.values())

    # Authors
    authors: Dict[str, int] = defaultdict(int)
    for entry in entries:
        if entry.get("author"):
            authors[entry["author"]] += 1

    # Date
    date = args.date or datetime.now().strftime("%Y-%m-%d")

    # Terminal report
    print_report(grouped, total, version, date, dict(authors))

    if deduped > 0:
        print(f"\n   ℹ️  {deduped} duplicate{'s' if deduped > 1 else ''} removed (use --no-dedup to keep)")

    # Markdown
    if args.markdown:
        md = generate_markdown(grouped, total, version, date, dict(authors))
        with open(args.markdown, "w", encoding="utf-8") as f:
            f.write(md)
        print(f"\n📄 Markdown saved to {args.markdown}")

    # JSON output
    if args.output:
        report = {
            "version": version,
            "date": date,
            "total_entries": total,
            "categories": {cat: len(items) for cat, items in grouped.items()},
            "contributors": dict(authors),
            "entries": [{k: v for k, v in e.items() if k != "raw_title"} for e in entries],
        }
        with open(args.output, "w") as f:
            json.dump(report, f, indent=2)
        print(f"\n📁 JSON saved to {args.output}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
