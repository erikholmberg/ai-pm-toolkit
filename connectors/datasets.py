#!/usr/bin/env python3
"""
Dataset contracts (shared)

The canonical column shapes every connector emits and every script already
reads.

This module — not the fetchers — is the point of the connector layer. A Jira
fetcher is worth little on its own; a Jira fetcher and a Linear fetcher that
emit *the same columns* mean `cycle-lead-time-analyzer.py` works against either
without knowing which one ran. That only holds if the column names are pinned
somewhere both connectors can read, which is here.

Every canonical name below was derived from the `_col()` alias lists already
in scripts/, not invented. The rule the derivation had to satisfy:

    A canonical name is valid only if it appears somewhere in the alias list
    of *every* script that consumes the dataset.

`_col()` returns the first alias that matches the file's headers, so a name
that is any script's alias — even its fourth — resolves correctly there. Names
that failed the rule were rejected as canonical: `resolved` appears in no
issue script's alias list for the completion date (they all say `done`), and
`category` is absent from `backlog-health-report.py` and `sprint-mix-report.py`
(both say `type`). Each column below records which scripts accept it.

Rejected-as-canonical is not rejected outright. Jira's export header for that
date is literally "Resolved", so `resolved` is carried as an *alias* on `done`:
aliases are what a connector matches source headers against, while the
canonical name is what gets written out. The two lists serve different ends and
only the canonical name has to satisfy the rule above.

Usage:
    import datasets

    spec = datasets.get("issues")
    warnings = spec.validate(rows)
    print(spec.column_names())

    python datasets.py            # list contracts
    python datasets.py issues     # full column detail for one

Requirements:
    None (stdlib only).
"""

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from _toolkit import csv_columns

__all__ = ["Column", "Dataset", "DATASETS", "get", "names", "UnknownDatasetError"]


class UnknownDatasetError(KeyError):
    """Raised when a dataset name isn't in the registry."""


@dataclass(frozen=True)
class Column:
    """One canonical column in a dataset contract.

    `aliases` is the union of spellings the consuming scripts already accept,
    which is what lets a source connector map a raw export header
    ("Story Points", "customfield_10016") onto the canonical name.
    """

    name: str
    description: str
    kind: str = "text"  # text | number | date
    required: bool = False
    aliases: Tuple[str, ...] = ()
    consumers: Tuple[str, ...] = ()

    def all_names(self) -> Tuple[str, ...]:
        """Canonical name first, then every accepted alias."""
        return (self.name,) + tuple(a for a in self.aliases if a != self.name)


@dataclass(frozen=True)
class Dataset:
    """A canonical table shape that connectors produce and scripts consume."""

    name: str
    description: str
    columns: Tuple[Column, ...]
    consumers: Tuple[str, ...] = ()
    notes: str = ""

    def column_names(self) -> List[str]:
        return [c.name for c in self.columns]

    def required_columns(self) -> List[str]:
        return [c.name for c in self.columns if c.required]

    def get_column(self, name: str) -> Optional[Column]:
        target = csv_columns.normalize(name)
        for col in self.columns:
            if csv_columns.normalize(col.name) == target:
                return col
        return None

    def resolve_header(self, header: str) -> Optional[str]:
        """Map a source header onto a canonical column name, or None.

        Matching is normalized, so "Story Points", "story_points", and
        "STORY POINTS" all land on `points`.
        """
        norm = csv_columns.normalize(header)
        for col in self.columns:
            for candidate in col.all_names():
                if csv_columns.normalize(candidate) == norm:
                    return col.name
        return None

    def validate(self, rows: Sequence[Dict[str, Any]]) -> List[str]:
        """Check rows against the contract; return warnings (never raises).

        Warnings, not errors, because a partial dataset is still useful: most
        scripts need only a subset of the columns, so a fetch missing
        `blocker_reason` should still be written out — just noisily.
        """
        warnings: List[str] = []
        if not rows:
            return [f"{self.name}: no rows returned"]

        present = set()
        for row in rows:
            present.update(row.keys())

        for col in self.columns:
            if col.required and col.name not in present:
                warnings.append(
                    f"{self.name}: required column '{col.name}' missing "
                    f"({col.description})"
                )

        extras = [c for c in sorted(present) if self.get_column(c) is None]
        if extras:
            warnings.append(
                f"{self.name}: {len(extras)} non-canonical column(s) passed "
                f"through unchanged: {', '.join(extras[:8])}"
                + (" ..." if len(extras) > 8 else "")
            )

        # Sample rather than scan: this is a smell test for a mis-mapped column,
        # and a bad mapping shows up in the first few rows or not at all.
        sample = rows[: min(50, len(rows))]
        for col in self.columns:
            if col.kind not in ("number", "date") or col.name not in present:
                continue
            bad = 0
            for row in sample:
                raw = str(row.get(col.name, "") or "").strip()
                if not raw:
                    continue
                ok = (
                    _looks_numeric(raw) if col.kind == "number" else _looks_dateish(raw)
                )
                if not ok:
                    bad += 1
            if bad:
                warnings.append(
                    f"{self.name}: column '{col.name}' expects {col.kind} but "
                    f"{bad}/{len(sample)} sampled rows don't parse — likely "
                    f"mapped to the wrong source field"
                )
        return warnings


def _looks_numeric(raw: str) -> bool:
    try:
        float(raw.replace(",", "").replace("%", "").strip())
        return True
    except ValueError:
        return False


def _looks_dateish(raw: str) -> bool:
    """Cheap shape check, not a parse.

    The connector has already normalized what it could to ISO; anything left
    that carries no digits is almost certainly not a date.
    """
    digits = sum(ch.isdigit() for ch in raw)
    return digits >= 4 and any(sep in raw for sep in ("-", "/", ":", " ")) or digits >= 6


# --------------------------------------------------------------------------
# issues — one row per ticket
#
# Consumers confirmed by reading their alias lists (7 scripts). Note that
# sprint-velocity-tracker.py, commitment-predictability-index.py, and
# sprint-burndown-checker.py are NOT consumers: they read sprint-level
# aggregates, and status-duration-analyzer.py reads a transition log. Those are
# separate contracts, not this one.
# --------------------------------------------------------------------------

_ISSUE_CONSUMERS = (
    "backlog-aging-report",
    "backlog-health-report",
    "blocker-wait-summary",
    "cycle-lead-time-analyzer",
    "sprint-mix-report",
    "sprint-scope-checker",
    "throughput-wip-analyzer",
)

ISSUES = Dataset(
    name="issues",
    description="One row per ticket / work item.",
    consumers=_ISSUE_CONSUMERS,
    notes=(
        "Different consumers require different subsets: cycle-lead-time needs "
        "created + done; throughput-wip needs id plus done or status; "
        "backlog-aging needs id + created. Only id and created are marked "
        "required here — the intersection every consumer depends on."
    ),
    columns=(
        Column(
            name="id",
            description="Ticket key or unique id.",
            required=True,
            aliases=("key", "issue_key", "issue key", "issue_id", "ticket_id"),
            consumers=_ISSUE_CONSUMERS,
        ),
        Column(
            name="summary",
            description="Short title.",
            aliases=("title", "subject"),
            consumers=(
                "backlog-aging-report",
                "backlog-health-report",
                "sprint-scope-checker",
            ),
        ),
        Column(
            name="status",
            description="Current workflow state.",
            aliases=("state", "stage"),
            consumers=("backlog-health-report", "throughput-wip-analyzer"),
        ),
        Column(
            name="type",
            description="Issue type (Bug, Story, Task...).",
            aliases=("issue type", "issuetype", "issue_type"),
            consumers=(
                "backlog-health-report",
                "blocker-wait-summary",
                "sprint-mix-report",
            ),
        ),
        Column(
            name="priority",
            description="Priority label.",
            aliases=("pri",),
            consumers=(
                "backlog-aging-report",
                "backlog-health-report",
                "sprint-mix-report",
                "sprint-scope-checker",
            ),
        ),
        Column(
            name="assignee",
            description="Current assignee.",
            aliases=("assignee name", "owner"),
            consumers=("backlog-health-report", "sprint-mix-report"),
        ),
        Column(
            name="points",
            description="Story point estimate.",
            kind="number",
            aliases=(
                "story points",
                "story point",
                "estimate",
                "customfield_10016",
                "custom field (story points)",
            ),
            consumers=(
                "backlog-aging-report",
                "backlog-health-report",
                "sprint-scope-checker",
            ),
        ),
        Column(
            name="created",
            description="Creation timestamp (ISO 8601).",
            kind="date",
            required=True,
            aliases=("created date", "createdate", "created_at", "created_date"),
            consumers=(
                "backlog-aging-report",
                "backlog-health-report",
                "blocker-wait-summary",
                "cycle-lead-time-analyzer",
                "throughput-wip-analyzer",
            ),
        ),
        Column(
            name="started",
            description="Moved to in-progress (ISO 8601).",
            kind="date",
            aliases=("in_progress", "in development", "indev", "started_at"),
            consumers=(
                "blocker-wait-summary",
                "cycle-lead-time-analyzer",
                "throughput-wip-analyzer",
            ),
        ),
        Column(
            name="done",
            description="Completion timestamp (ISO 8601).",
            kind="date",
            aliases=(
                "resolved",
                "resolution date",
                "resolutiondate",
                "completed",
                "closed",
                "completed_at",
            ),
            consumers=(
                "blocker-wait-summary",
                "cycle-lead-time-analyzer",
                "throughput-wip-analyzer",
            ),
        ),
        Column(
            name="updated",
            description="Last update timestamp (ISO 8601).",
            kind="date",
            aliases=("updated date", "updatedate", "last updated"),
            consumers=("backlog-health-report",),
        ),
        Column(
            name="sprint",
            description="Sprint or cycle name.",
            aliases=("sprint_id", "cycle"),
            consumers=("throughput-wip-analyzer",),
        ),
        Column(
            name="component",
            description="Component / area.",
            aliases=("components", "component/s"),
            consumers=("sprint-mix-report",),
        ),
        Column(
            name="description",
            description="Full description body.",
            consumers=("backlog-health-report",),
        ),
        Column(
            name="blocker_reason",
            description="Why the item sat blocked.",
            aliases=("blocker", "blocked_reason", "wait_reason"),
            consumers=("blocker-wait-summary",),
        ),
    ),
)


DATASETS: Dict[str, Dataset] = {ISSUES.name: ISSUES}


def names() -> List[str]:
    """Registered dataset names."""
    return sorted(DATASETS)


def get(name: str) -> Dataset:
    """Look up a dataset contract by name."""
    key = (name or "").strip().lower()
    if key not in DATASETS:
        raise UnknownDatasetError(
            f"Unknown dataset {name!r}. Known datasets: {', '.join(names())}"
        )
    return DATASETS[key]


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Inspect the canonical dataset contracts.",
        epilog="Example: datasets.py issues",
    )
    parser.add_argument("dataset", nargs="?", help="Dataset to describe in full")
    args = parser.parse_args()

    if not args.dataset:
        print("Canonical datasets\n")
        for spec in (DATASETS[n] for n in names()):
            print(f"  {spec.name:<10} {spec.description}")
            print(f"  {'':<10} columns:   {', '.join(spec.column_names())}")
            print(f"  {'':<10} consumers: {len(spec.consumers)} scripts")
            print()
        print("Run `datasets.py <name>` for full column detail.")
        raise SystemExit(0)

    spec = get(args.dataset)
    print(f"{spec.name} — {spec.description}\n")
    if spec.notes:
        print(f"{spec.notes}\n")
    print(f"{'column':<16}{'kind':<8}{'req':<5}aliases accepted")
    print("-" * 78)
    for col in spec.columns:
        req = "yes" if col.required else ""
        alias = ", ".join(col.aliases) or "—"
        print(f"{col.name:<16}{col.kind:<8}{req:<5}{alias}")
    print(f"\nConsumers ({len(spec.consumers)}):")
    for c in spec.consumers:
        print(f"  scripts/{c}.py")
