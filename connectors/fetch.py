#!/usr/bin/env python3
"""
fetch — pull a canonical dataset from a source into CSV

The connector layer's only CLI. It materializes data to a CSV in the shape the
scripts already read, then gets out of the way:

    python connectors/fetch.py csvfile issues --input export.csv --out issues.csv
    python scripts/cycle-lead-time-analyzer.py --csv issues.csv

Two steps rather than teaching 115 scripts to speak HTTP. That keeps the
calculators pure functions over a file — no auth, no network, still testable
offline — and leaves a CSV on disk you can inspect, commit next to a QBR deck,
and re-run in six months. The `.meta.json` sidecar written beside it records
which query produced those rows.

Usage:
    python fetch.py --list                     # sources and the datasets they provide
    python fetch.py --describe issues          # full column contract
    python fetch.py <source> <dataset> --out FILE [source options]
    python fetch.py csvfile issues --input export.csv --out issues.csv

Requirements:
    None (stdlib only).
"""

import argparse
import sys
from typing import List

import datasets
import registry
from base import ConnectorError


def _print_list() -> None:
    print("Sources\n")
    for name, cls, error in registry.describe_all():
        if error:
            print(f"  {name:<12} UNAVAILABLE — {error}")
            continue
        provides = ", ".join(sorted(cls.provides)) or "(nothing)"
        print(f"  {name:<12} {cls.description}")
        print(f"  {'':<12} provides: {provides}")
    print("\nDatasets\n")
    for name in datasets.names():
        spec = datasets.get(name)
        print(f"  {name:<12} {spec.description}")
        print(f"  {'':<12} {len(spec.consumers)} consuming scripts")
    print("\nRun `fetch.py --describe <dataset>` for the column contract.")


def _print_describe(name: str) -> None:
    spec = datasets.get(name)
    print(f"{spec.name} — {spec.description}\n")
    if spec.notes:
        print(spec.notes + "\n")
    print(f"{'column':<16}{'kind':<8}{'req':<5}aliases accepted")
    print("-" * 78)
    for col in spec.columns:
        print(
            f"{col.name:<16}{col.kind:<8}"
            f"{'yes' if col.required else '':<5}"
            f"{', '.join(col.aliases) or '—'}"
        )
    print(f"\nConsuming scripts ({len(spec.consumers)}):")
    for consumer in spec.consumers:
        print(f"  scripts/{consumer}.py")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="fetch.py",
        description="Pull a canonical dataset from a source into CSV.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  fetch.py --list\n"
            "  fetch.py --describe issues\n"
            "  fetch.py csvfile issues --input export.csv --out issues.csv\n"
        ),
    )
    parser.add_argument("--list", action="store_true", help="List sources and datasets")
    parser.add_argument("--describe", metavar="DATASET", help="Show a column contract")

    subparsers = parser.add_subparsers(dest="source", metavar="SOURCE")
    for name, cls, error in registry.describe_all():
        if error:
            continue
        sub = subparsers.add_parser(
            name,
            help=cls.description,
            description=cls.__doc__ or cls.description,
            formatter_class=argparse.RawDescriptionHelpFormatter,
        )
        sub.add_argument(
            "dataset",
            choices=sorted(cls.provides),
            help="Canonical dataset to produce",
        )
        sub.add_argument("--out", required=True, help="Output CSV path")
        sub.add_argument(
            "--offline",
            action="store_true",
            help="Replay the recorded fixture instead of calling the source",
        )
        sub.add_argument(
            "--quiet", action="store_true", help="Only print the output path"
        )
        cls.add_arguments(sub)
    return parser


def main(argv: List[str]) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.list:
        _print_list()
        return 0
    if args.describe:
        try:
            _print_describe(args.describe)
        except datasets.UnknownDatasetError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2
        return 0
    if not args.source:
        parser.print_help()
        return 0

    try:
        connector = registry.load(args.source)(offline=args.offline)
        meta = connector.run(args.dataset, args, args.out)
    except (ConnectorError, datasets.UnknownDatasetError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if args.quiet:
        print(meta["output"])
        return 0

    print(f"{meta['rows']} row(s) -> {meta['output']}")
    print(f"provenance     -> {meta['sidecar']}")
    for warning in meta["warnings"]:
        print(f"  warning: {warning}")
    if meta["rows"]:
        spec = datasets.get(args.dataset)
        print(f"\nFeeds: {', '.join('scripts/' + c + '.py' for c in spec.consumers)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
