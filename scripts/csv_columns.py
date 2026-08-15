#!/usr/bin/env python3
"""
CSV Column Helpers (shared)

Real exports don't use the header names our scripts expect. Jira writes
"Story Points", analytics tools write "Duration (Minutes)", and a script asking
for `row.get("duration_minutes", 0)` silently gets the default — producing a
confident zero instead of an error. That silent-default path is the single most
common way these scripts give a wrong answer on real data.

This module provides two things:

1. `DictReader` — a drop-in `csv.DictReader` replacement that matches header
   names case- and punctuation-insensitively. `Duration (Minutes)`,
   `duration_minutes`, and `DURATION MINUTES` all answer to
   `row["duration_minutes"]`.

2. `resolve()` / `require()` — the explicit alias lookup that 63 of the
   toolkit's scripts already implement privately as `_col()`.

Usage:
    import csv_columns

    with open(path, newline="") as f:
        reader = csv_columns.DictReader(f)
        for row in reader:
            minutes = float(row.get("duration_minutes", 0))

    # Explicit aliases when the concept has several common names:
    col = csv_columns.resolve(reader.fieldnames, "area", "category", "domain")

Requirements:
    None (stdlib only).
"""

import csv
import re
from typing import Any, Dict, Iterable, List, Optional

__all__ = [
    "normalize",
    "resolve",
    "require",
    "MissingColumnError",
    "NormalizedRow",
    "DictReader",
]


class MissingColumnError(KeyError):
    """Raised when a required column can't be found under any known alias."""


def normalize(name: str) -> str:
    """Fold a header into a comparable form.

    Lowercases, trims, and collapses any run of non-alphanumeric characters to a
    single underscore, so "Duration (Minutes)", "duration-minutes", and
    "Duration  Minutes" all normalize to "duration_minutes".
    """
    if name is None:
        return ""
    return re.sub(r"[^a-z0-9]+", "_", str(name).strip().lower()).strip("_")


def resolve(fieldnames: Optional[Iterable[str]], *aliases: str) -> Optional[str]:
    """Return the actual header matching any alias, or None.

    Aliases are tried in order, so pass the preferred name first. Matching is
    normalized, so callers don't need to spell out casing or punctuation variants.
    """
    if not fieldnames:
        return None
    lookup: Dict[str, str] = {}
    for field in fieldnames:
        # First header wins on a collision, matching csv.DictReader's behavior.
        lookup.setdefault(normalize(field), field)
    for alias in aliases:
        hit = lookup.get(normalize(alias))
        if hit is not None:
            return hit
    return None


def require(fieldnames: Optional[Iterable[str]], *aliases: str) -> str:
    """Like `resolve`, but raise a message naming what was actually in the file.

    The error is the point: a missing column should say which columns exist, not
    fall through to a default that produces a plausible wrong number.
    """
    hit = resolve(fieldnames, *aliases)
    if hit is not None:
        return hit
    available = ", ".join(fieldnames) if fieldnames else "(no header row)"
    wanted = " / ".join(aliases)
    raise MissingColumnError(
        f"Required column not found. Looked for: {wanted}. "
        f"CSV has: {available}"
    )


class NormalizedRow(dict):
    """A CSV row whose lookups ignore header case and punctuation.

    Behaves like the plain dict `csv.DictReader` yields — iteration and
    `.items()` still give the file's original header names — but `[]`, `.get()`,
    and `in` also accept normalized spellings.
    """

    def __init__(self, row: Dict[str, Any]):
        super().__init__(row)
        self._normalized: Dict[str, Any] = {}
        for key, value in row.items():
            self._normalized.setdefault(normalize(key), value)

    def __getitem__(self, key: str) -> Any:
        if key in self.keys():
            return super().__getitem__(key)
        norm = normalize(key)
        if norm in self._normalized:
            return self._normalized[norm]
        raise MissingColumnError(
            f"No column {key!r} in row. Columns: {', '.join(self.keys())}"
        )

    def get(self, key: str, default: Any = None) -> Any:
        try:
            return self[key]
        except MissingColumnError:
            return default

    def __contains__(self, key: object) -> bool:
        if super().__contains__(key):
            return True
        return isinstance(key, str) and normalize(key) in self._normalized

    def first(self, *aliases: str, default: Any = None) -> Any:
        """Value of the first alias present, else `default`."""
        for alias in aliases:
            if alias in self:
                return self[alias]
        return default


class DictReader:
    """`csv.DictReader` that yields `NormalizedRow`s.

    Drop-in: swap `csv.DictReader(f)` for `csv_columns.DictReader(f)` and the
    script starts tolerating real-world header spellings without any other
    change. `fieldnames` and `line_num` are passed through.
    """

    def __init__(self, f, *args, **kwargs):
        self._reader = csv.DictReader(f, *args, **kwargs)

    def __iter__(self):
        return self

    def __next__(self) -> NormalizedRow:
        return NormalizedRow(next(self._reader))

    @property
    def fieldnames(self) -> Optional[List[str]]:
        return self._reader.fieldnames

    @property
    def line_num(self) -> int:
        return self._reader.line_num

    def resolve(self, *aliases: str) -> Optional[str]:
        """Resolve an alias against this file's headers."""
        return resolve(self.fieldnames, *aliases)

    def require(self, *aliases: str) -> str:
        """Resolve an alias against this file's headers, or raise."""
        return require(self.fieldnames, *aliases)


if __name__ == "__main__":
    import io
    import sys

    sample = io.StringIO(
        "Area,Item Name,Duration (Minutes),Done\n"
        "QA,Smoke tests,45,yes\n"
    )
    reader = DictReader(sample)
    print(f"Headers as written:  {reader.fieldnames}")
    for row in reader:
        print(f"  row['area']              -> {row['area']!r}")
        print(f"  row['item_name']         -> {row['item_name']!r}")
        print(f"  row['duration_minutes']  -> {row['duration_minutes']!r}")
        print(f"  row.first('task','item_name') -> {row.first('task', 'item_name')!r}")
        print(f"  row.get('missing', 0)    -> {row.get('missing', 0)!r}")
    print("\nAll lookups above would have returned the default with csv.DictReader.")
    sys.exit(0)
