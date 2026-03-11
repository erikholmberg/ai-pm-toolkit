#!/usr/bin/env python3
"""
Prompt Version Diff

Compare two prompt or config versions: token counts, line/word summary, and key
changes (additions/deletions). For change control before deploying prompt updates.

Usage:
    # Compare two files
    python prompt-version-diff.py --old prompt_v1.txt --new prompt_v2.txt

    # Token-only summary
    python prompt-version-diff.py --old prompt_v1.txt --new prompt_v2.txt --tokens-only

    # Export JSON
    python prompt-version-diff.py --old prompt_v1.txt --new prompt_v2.txt --output diff.json

Token counting uses a character-based estimate (~4 chars/token); no external deps.

Requirements:
    None (stdlib only).
"""

import argparse
import difflib
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple


# Same as token-counter fallback (stdlib-only)
CHARS_PER_TOKEN_ESTIMATE = 4


def count_tokens_estimate(text: str) -> int:
    if not text:
        return 0
    return max(1, len(text) // CHARS_PER_TOKEN_ESTIMATE)


def load_text(path: str) -> str:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(path)
    return p.read_text(encoding="utf-8")


def compute_diff(old_text: str, new_text: str) -> Dict[str, Any]:
    """Line-level diff summary and key changes."""
    old_lines = old_text.splitlines(keepends=True)
    if not old_text.endswith("\n") and old_lines:
        old_lines[-1] = old_lines[-1].rstrip("\n") + "\n" if not old_lines[-1].endswith("\n") else old_lines[-1]
    new_lines = new_text.splitlines(keepends=True)
    if not new_text.endswith("\n") and new_lines:
        new_lines[-1] = new_lines[-1].rstrip("\n") + "\n" if not new_lines[-1].endswith("\n") else new_lines[-1]

    matcher = difflib.SequenceMatcher(None, old_lines, new_lines)
    added = sum(j2 - j1 for tag, i1, i2, j1, j2 in matcher.get_opcodes() if tag == "insert")
    removed = sum(i2 - i1 for tag, i1, i2, j1, j2 in matcher.get_opcodes() if tag == "delete")
    replace_count = sum(
        (i2 - i1) + (j2 - j1)
        for tag, i1, i2, j1, j2 in matcher.get_opcodes()
        if tag == "replace"
    )

    # Collect added/removed snippets (first few lines)
    added_lines: List[str] = []
    removed_lines: List[str] = []
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "insert":
            added_lines.extend(new_lines[j1:j2])
        elif tag == "delete":
            removed_lines.extend(old_lines[i1:i2])

    def trim(lines: List[str], max_len: int = 5) -> List[str]:
        out = [ln.rstrip("\n")[:80] for ln in lines[:max_len]]
        if len(lines) > max_len:
            out.append(f"... and {len(lines) - max_len} more")
        return out

    return {
        "lines_added": added,
        "lines_removed": removed,
        "lines_replaced": replace_count,
        "added_preview": trim(added_lines),
        "removed_preview": trim(removed_lines),
    }


def run_diff(old_path: str, new_path: str) -> Dict[str, Any]:
    old_text = load_text(old_path)
    new_text = load_text(new_path)

    old_tokens = count_tokens_estimate(old_text)
    new_tokens = count_tokens_estimate(new_text)
    token_delta = new_tokens - old_tokens

    diff = compute_diff(old_text, new_text)
    old_lines = len(old_text.splitlines())
    new_lines = len(new_text.splitlines())

    return {
        "old_file": old_path,
        "new_file": new_path,
        "old_tokens": old_tokens,
        "new_tokens": new_tokens,
        "token_delta": token_delta,
        "old_lines": old_lines,
        "new_lines": new_lines,
        "line_delta": new_lines - old_lines,
        "lines_added": diff["lines_added"],
        "lines_removed": diff["lines_removed"],
        "lines_replaced": diff["lines_replaced"],
        "added_preview": diff["added_preview"],
        "removed_preview": diff["removed_preview"],
    }


def print_report(result: Dict[str, Any], tokens_only: bool) -> None:
    print("\n" + "=" * 70)
    print("📝 PROMPT VERSION DIFF")
    print("=" * 70)
    print(f"\n   Old: {result['old_file']}  →  New: {result['new_file']}")
    print(f"\n   Tokens:  {result['old_tokens']:,}  →  {result['new_tokens']:,}  (Δ {result['token_delta']:+,})")
    if tokens_only:
        print()
        return
    print(f"   Lines:   {result['old_lines']}  →  {result['new_lines']}  (Δ {result['line_delta']:+d})")
    print(f"   Changes: +{result['lines_added']} / −{result['lines_removed']} lines")
    if result.get("lines_replaced"):
        print(f"   Replaced: {result['lines_replaced']} line(s)")
    if result.get("added_preview"):
        print("\n   Added (preview):")
        for ln in result["added_preview"]:
            print(f"      + {ln}")
    if result.get("removed_preview"):
        print("\n   Removed (preview):")
        for ln in result["removed_preview"]:
            print(f"      − {ln}")
    print("\n   💡 Use for change control before deploying prompt updates.\n")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Compare two prompt versions: tokens, lines, and key changes.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--old", "-o", required=True, metavar="FILE", help="Path to old prompt file")
    parser.add_argument("--new", "-n", required=True, metavar="FILE", help="Path to new prompt file")
    parser.add_argument("--tokens-only", "-t", action="store_true", help="Only print token summary")
    parser.add_argument("--output", metavar="FILE", help="Write JSON result to FILE")
    args = parser.parse_args()

    try:
        result = run_diff(args.old, args.new)
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    print_report(result, args.tokens_only)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2)
        print(f"Wrote JSON to {args.output}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
