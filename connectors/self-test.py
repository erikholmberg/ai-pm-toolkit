#!/usr/bin/env python3
"""
Connector Self-Test

Runs each connector against its fixture and then feeds the result to every
script the dataset contract claims to feed.

The second half is the part that matters. A connector that writes a tidy CSV
still fails at its actual job if `cycle-lead-time-analyzer.py` can't read it,
and nothing about the CSV looks wrong when that happens — the script just
reports zero tickets and exits 0 with a confident empty table. So this asserts
on the scripts' *behavior*, not just their exit codes: a consumer that runs
cleanly while finding none of the rows is reported as a failure.

That check is what pins the contract. Rename a canonical column and this goes
red immediately, instead of six weeks later in a report nobody re-derived.

Usage:
    python self-test.py
    python self-test.py --verbose
    python self-test.py --only csvfile
    python self-test.py --output report.json

Requirements:
    None (stdlib only).
"""

import argparse
import csv
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import datasets
import registry
from _toolkit import SCRIPTS_DIR, toolkit_io

TOOL = "connector-self-test"
HERE = Path(__file__).resolve().parent
FIXTURES = HERE / "fixtures"

# Extra required flags a consumer needs that carry no data (scalar thresholds,
# capacities). Without these the script exits 2 on argparse, which would look
# like a contract failure but isn't one.
CONSUMER_EXTRA_ARGS: Dict[str, List[str]] = {
    "sprint-scope-checker": ["--capacity", "30"],
}

# How each connector is driven in the test. Adding a source means adding a line.
CONNECTOR_CASES: Dict[str, Dict[str, Any]] = {
    "csvfile": {
        "dataset": "issues",
        "args": ["--input", str(FIXTURES / "sample-jira-export.csv")],
        "min_rows": 6,
    },
    "jira": {
        "dataset": "issues",
        "args": ["--offline", "--with-started"],
        "min_rows": 6,
    },
    "gateway": {
        "dataset": "llm_usage",
        "args": ["--offline"],
        "min_rows": 30,
    },
}


def _run(cmd: List[str], cwd: Optional[Path] = None) -> Tuple[int, str]:
    proc = subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        capture_output=True,
        text=True,
        timeout=120,
    )
    return proc.returncode, (proc.stdout or "") + (proc.stderr or "")


def _row_count(output: str) -> Optional[int]:
    """Largest integer a consumer reports, as a proxy for 'it saw the data'.

    Deliberately loose: these 7 scripts each phrase their headline count
    differently ("Total items", "Tickets analyzed", "Completed"), and pinning
    an exact phrase per script would break every time one is reworded. All this
    needs to distinguish is 'found rows' from 'found nothing'.
    """
    numbers = [int(n) for n in re.findall(r"\b(\d{1,6})\b", output)]
    return max(numbers) if numbers else None


def test_connector(name: str, case: Dict[str, Any], verbose: bool) -> Dict[str, Any]:
    result: Dict[str, Any] = {
        "connector": name,
        "dataset": case["dataset"],
        "fetch": "fail",
        "rows": 0,
        "consumers": [],
        "failures": [],
    }
    dataset = case["dataset"]

    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / f"{dataset}.csv"
        code, output = _run(
            [sys.executable, "fetch.py", name, dataset, "--out", str(out)]
            + case["args"],
            cwd=HERE,
        )
        if code != 0 or not out.exists():
            result["failures"].append(f"fetch failed (exit {code}): {output.strip()}")
            return result

        with out.open(encoding="utf-8") as f:
            reader = csv.DictReader(f)
            data = list(reader)
        rows = len(data)
        result["fetch"] = "ok"
        result["rows"] = rows
        # A column present but blank in every row is not really provided; the
        # coverage matrix should say so rather than imply parity that isn't there.
        result["columns"] = sorted(
            c for c in (reader.fieldnames or [])
            if any(str(r.get(c, "")).strip() for r in data)
        )
        if rows < case.get("min_rows", 1):
            result["failures"].append(
                f"fetch produced {rows} rows, expected >= {case.get('min_rows', 1)}"
            )

        sidecar = Path(f"{out}.meta.json")
        if not sidecar.exists():
            result["failures"].append("no .meta.json provenance sidecar written")
        else:
            meta = toolkit_io.metadata(str(sidecar))
            if meta["tool"] != f"connector:{name}":
                result["failures"].append(
                    f"sidecar tool is {meta['tool']!r}, expected 'connector:{name}'"
                )

        for consumer in datasets.get(dataset).consumers:
            script = SCRIPTS_DIR / f"{consumer}.py"
            entry: Dict[str, Any] = {"script": consumer}
            if not script.exists():
                entry["status"] = "missing"
                result["failures"].append(f"{consumer}: script not found")
                result["consumers"].append(entry)
                continue

            cmd = [sys.executable, str(script), "--csv", str(out)]
            cmd += CONSUMER_EXTRA_ARGS.get(consumer, [])
            code, output = _run(cmd, cwd=SCRIPTS_DIR)
            seen = _row_count(output)
            entry["exit"] = code
            entry["max_number_seen"] = seen

            if code != 0:
                entry["status"] = "error"
                result["failures"].append(
                    f"{consumer}: exit {code} — {output.strip().splitlines()[-1] if output.strip() else 'no output'}"
                )
            elif not seen:
                # Ran fine and found nothing: the silent-mapping failure this
                # whole test exists to catch.
                entry["status"] = "empty"
                result["failures"].append(
                    f"{consumer}: exit 0 but reported no rows — columns likely unmapped"
                )
            else:
                entry["status"] = "ok"
            result["consumers"].append(entry)
            if verbose:
                print(f"    {entry['status']:<8} {consumer}")

    return result


def _report_coverage(results: List[Dict[str, Any]]) -> int:
    """Compare what each connector fills in, per dataset.

    This is the cross-source check the whole contract exists for: two sources
    are interchangeable only if a script asking for `done` gets the same thing
    from both. Divergence — a column no connector populates, or a column
    outside the contract — is a failure. Sources legitimately differ in
    *coverage* (a CSV export has no changelog, so no `started`), and that is
    reported as information, not a failure.
    """
    by_dataset: Dict[str, List[Dict[str, Any]]] = {}
    for result in results:
        if result["fetch"] == "ok":
            by_dataset.setdefault(result["dataset"], []).append(result)

    failures = 0
    for dataset, group in sorted(by_dataset.items()):
        spec = datasets.get(dataset)
        canonical = spec.column_names()
        print(f"\n  coverage — {dataset}")
        width = max(len(c) for c in canonical) + 2
        header = "".join(f"{r['connector'][:9]:<11}" for r in group)
        print(f"    {'column':<{width}}{header}")
        for column in canonical:
            marks = "".join(
                ("  yes      " if column in r.get("columns", []) else "  -        ")
                for r in group
            )
            print(f"    {column:<{width}}{marks}")

        for result in group:
            extras = [c for c in result.get("columns", []) if spec.get_column(c) is None]
            # Passing a source column through unchanged is a feature, so extras
            # alone aren't a fault. An extra whose *name is an alias* of a
            # canonical column is: it means the connector left data sitting in
            # a column no script will look at, while the canonical column it
            # belonged in stays empty. That is the silent-zero failure again,
            # one level up.
            shadowed = [
                (c, spec.resolve_header(c)) for c in extras if spec.resolve_header(c)
            ]
            passthrough = [c for c in extras if not spec.resolve_header(c)]
            for column, canonical in shadowed:
                failures += 1
                print(
                    f"    FAIL {result['connector']}: column {column!r} is an "
                    f"alias of canonical '{canonical}' but was left unmapped"
                )
            if passthrough:
                print(
                    f"    note {result['connector']}: {len(passthrough)} source "
                    f"column(s) passed through: {', '.join(passthrough[:6])}"
                )
    return failures


def main(argv: List[str]) -> int:
    parser = argparse.ArgumentParser(
        description="Verify each connector's output actually feeds its consuming scripts.",
        epilog="Example: self-test.py --verbose",
    )
    parser.add_argument("--only", help="Substring filter on connector name")
    parser.add_argument("--verbose", action="store_true", help="Show each consumer")
    parser.add_argument("--output", help="Write a JSON report")
    args = parser.parse_args(argv)

    cases = {
        name: case
        for name, case in CONNECTOR_CASES.items()
        if not args.only or args.only in name
    }
    untested = [n for n in registry.names() if n not in CONNECTOR_CASES]

    print("=" * 70)
    print("CONNECTOR SELF-TEST")
    print("=" * 70)

    results = []
    for name, case in cases.items():
        print(f"\n  {name} -> {case['dataset']}")
        result = test_connector(name, case, args.verbose)
        results.append(result)
        ok = sum(1 for c in result["consumers"] if c.get("status") == "ok")
        total = len(result["consumers"])
        print(f"    fetch: {result['fetch']} ({result['rows']} rows)")
        print(f"    consumers reading it: {ok}/{total}")
        for failure in result["failures"]:
            print(f"    FAIL {failure}")

    failed = sum(len(r["failures"]) for r in results)
    failed += _report_coverage(results)

    print("\n" + "-" * 70)
    if untested:
        # Reported, not hidden: a registered connector with no case is an
        # untested connector, which is a gap rather than a pass.
        print(f"  no test case: {', '.join(untested)}")
    print(f"  connectors tested: {len(results)}   failures: {failed}")
    print("-" * 70)

    if args.output:
        report = {
            "connectors_tested": len(results),
            "failures": failed,
            "untested": untested,
            "results": results,
        }
        toolkit_io.write(args.output, report, TOOL)
        print(f"  report -> {args.output}")

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
