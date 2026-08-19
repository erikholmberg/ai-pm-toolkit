#!/usr/bin/env python3
"""
csvfile connector — normalize an existing CSV export into canonical shape.

Not a placeholder. This is the connector most people will actually reach for
first, because the common way to get data out of Jira or Linear today is the
export button, and what comes out has headers like "Issue key",
"Story Points", and "Resolved" plus fifty columns nobody asked for. Running it
through here produces the canonical `issues` shape, with dates in ISO and the
contract columns in front.

It also proves the layer end to end without any credentials, which is why it
ships first: if the contract is wrong, that shows up here rather than after an
API integration has been written on top of it.

Mapping precedence, most specific first:
    1. --map points="Custom field (Story Points)"   (repeatable, wins outright)
    2. --profile connectors/profiles/jira.json      (canonical -> source header)
    3. the dataset's declared aliases in datasets.py

Usage:
    python fetch.py csvfile issues --input export.csv --out issues.csv
    python fetch.py csvfile issues --input export.csv --out issues.csv \\
        --profile profiles/jira.json
    python fetch.py csvfile issues --input export.csv --out issues.csv \\
        --map points="Custom field (Story Points)" --map done=Resolved
    python fetch.py csvfile issues --input export.csv --out issues.csv --strict

Requirements:
    None (stdlib only).
"""

import json
from pathlib import Path
from typing import Any, Dict, List

import datasets
from _toolkit import csv_columns
from base import Connector, ConnectorError, FetchResult


class CsvFileConnector(Connector):
    name = "csvfile"
    provides = frozenset({"issues"})
    description = "Normalize an existing CSV export into a canonical dataset."

    @classmethod
    def add_arguments(cls, parser) -> None:
        parser.add_argument(
            "--input",
            required=True,
            help="Path to the source CSV (e.g. a Jira or Linear export)",
        )
        parser.add_argument(
            "--profile",
            help="JSON file mapping canonical column -> source header",
        )
        parser.add_argument(
            "--map",
            action="append",
            default=[],
            metavar="CANONICAL=HEADER",
            help="Explicit column mapping; repeatable, overrides --profile",
        )
        parser.add_argument(
            "--drop-extras",
            action="store_true",
            help="Emit only canonical columns instead of passing extras through",
        )
        parser.add_argument(
            "--strict",
            action="store_true",
            help="Fail if a required canonical column can't be mapped",
        )

    def fetch(self, dataset: str, args) -> FetchResult:
        spec = datasets.get(dataset)
        source = Path(args.input)
        if not source.exists():
            raise ConnectorError(f"{self.name}: no such file: {source}")

        overrides = _load_profile(args.profile)
        overrides.update(_parse_map_flags(args.map))

        warnings: List[str] = []
        rows: List[Dict[str, Any]] = []

        with source.open(newline="", encoding="utf-8-sig") as f:
            reader = csv_columns.DictReader(f)
            headers = list(reader.fieldnames or [])
            if not headers:
                raise ConnectorError(f"{self.name}: {source} has no header row")

            mapping, unmapped = _build_mapping(spec, headers, overrides, warnings)

            missing_required = [
                c.name
                for c in spec.columns
                if c.required and c.name not in mapping
            ]
            if missing_required:
                message = (
                    f"could not map required column(s) "
                    f"{', '.join(missing_required)} from headers: "
                    f"{', '.join(headers)}"
                )
                if args.strict:
                    raise ConnectorError(f"{self.name}: {message}")
                warnings.append(message)

            for raw in reader:
                row: Dict[str, Any] = {}
                for canonical, header in mapping.items():
                    row[canonical] = raw.get(header, "")
                if not args.drop_extras:
                    for header in unmapped:
                        row[header] = raw.get(header, "")
                if any(str(v).strip() for v in row.values()):
                    rows.append(row)

        query = {
            "input": str(source),
            "mapped": {k: mapping[k] for k in sorted(mapping)},
            "profile": args.profile or None,
            "dropped_extras": bool(args.drop_extras),
        }
        return FetchResult(rows, query, warnings)


def _load_profile(path: str) -> Dict[str, str]:
    if not path:
        return {}
    target = Path(path)
    if not target.exists():
        # A profile is per-instance config; a typo'd path silently falling back
        # to alias matching would look like the profile simply had no effect.
        raise ConnectorError(f"csvfile: no such profile: {target}")
    with target.open(encoding="utf-8") as f:
        data = json.load(f)
    columns = data.get("columns", data)
    if not isinstance(columns, dict):
        raise ConnectorError(
            f"csvfile: profile {target} must be an object mapping "
            f"canonical column -> source header"
        )
    return {str(k): str(v) for k, v in columns.items()}


def _parse_map_flags(flags: List[str]) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for flag in flags or []:
        if "=" not in flag:
            raise ConnectorError(
                f"csvfile: --map expects CANONICAL=HEADER, got {flag!r}"
            )
        canonical, header = flag.split("=", 1)
        out[canonical.strip()] = header.strip()
    return out


def _build_mapping(spec, headers, overrides, warnings):
    """Resolve canonical column -> actual source header.

    Returns the mapping plus the headers left over, which are passed through
    unless --drop-extras was given.
    """
    mapping: Dict[str, str] = {}
    claimed = set()

    for canonical, wanted in overrides.items():
        if spec.get_column(canonical) is None:
            warnings.append(
                f"mapping for '{canonical}' ignored: not a column of "
                f"'{spec.name}' (columns: {', '.join(spec.column_names())})"
            )
            continue
        hit = csv_columns.resolve(headers, wanted)
        if hit is None:
            warnings.append(
                f"mapping {canonical}={wanted!r} skipped: no such header in input"
            )
            continue
        mapping[canonical] = hit
        claimed.add(hit)

    for col in spec.columns:
        if col.name in mapping:
            continue
        hit = csv_columns.resolve(headers, *col.all_names())
        if hit is not None and hit not in claimed:
            mapping[col.name] = hit
            claimed.add(hit)

    unmapped = [h for h in headers if h not in claimed]
    return mapping, unmapped
