#!/usr/bin/env python3
"""
PRD Traceability Linker

Builds requirement-to-delivery links between PRD sections and execution artifacts.
"""

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List


def load_csv(path: str) -> List[Dict[str, str]]:
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def build_links(rows: List[Dict[str, str]]) -> Dict[str, Any]:
    # Expected columns:
    # requirement_id, requirement_title, artifact_type, artifact_id, artifact_url, status, evidence
    grouped: Dict[str, Dict[str, Any]] = {}
    by_artifact_type = defaultdict(int)

    for row in rows:
        rid = row.get("requirement_id", "").strip()
        if not rid:
            continue
        if rid not in grouped:
            grouped[rid] = {
                "requirement_id": rid,
                "requirement_title": row.get("requirement_title", "").strip(),
                "artifacts": [],
            }

        artifact = {
            "type": row.get("artifact_type", "").strip(),
            "id": row.get("artifact_id", "").strip(),
            "url": row.get("artifact_url", "").strip(),
            "status": row.get("status", "").strip() or "unknown",
            "evidence": row.get("evidence", "").strip(),
        }
        grouped[rid]["artifacts"].append(artifact)
        by_artifact_type[artifact["type"] or "unknown"] += 1

    requirements = list(grouped.values())
    complete = 0
    partial = 0
    missing = 0

    for req in requirements:
        statuses = {a["status"] for a in req["artifacts"]}
        if "done" in statuses and "verified" in statuses:
            req["coverage"] = "complete"
            complete += 1
        elif req["artifacts"]:
            req["coverage"] = "partial"
            partial += 1
        else:
            req["coverage"] = "missing"
            missing += 1

    return {
        "summary": {
            "requirements": len(requirements),
            "complete": complete,
            "partial": partial,
            "missing": missing,
            "artifact_counts": dict(by_artifact_type),
        },
        "requirements": requirements,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Create PRD-to-delivery traceability map.")
    parser.add_argument("--csv", required=True, help="Traceability CSV input")
    parser.add_argument("--output", help="Write JSON report")
    args = parser.parse_args()

    rows = load_csv(args.csv)
    report = build_links(rows)

    summary = report["summary"]
    print("\n=== PRD Traceability Coverage ===")
    print(f"Requirements: {summary['requirements']}")
    print(f"Complete:     {summary['complete']}")
    print(f"Partial:      {summary['partial']}")
    print(f"Missing:      {summary['missing']}")
    print("Artifacts by type:")
    for artifact_type, count in sorted(summary["artifact_counts"].items()):
        print(f"- {artifact_type}: {count}")

    if args.output:
        Path(args.output).write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"\nSaved traceability report: {args.output}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
