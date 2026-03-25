#!/usr/bin/env python3
"""
Release Gate Scorer

Scores go/no-go readiness based on weighted evidence categories.
"""

import argparse
import csv
import json
from pathlib import Path
from typing import Dict, List


def load_rows(path: str) -> List[Dict[str, str]]:
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def main() -> int:
    parser = argparse.ArgumentParser(description="Score release gate confidence from evidence CSV.")
    parser.add_argument("--csv", required=True, help="CSV with gate checks")
    parser.add_argument("--go-threshold", type=float, default=85.0, help="Go threshold in percentage")
    parser.add_argument("--output", help="Write JSON decision")
    args = parser.parse_args()

    # Expected columns: category,check,weight,status,evidence
    rows = load_rows(args.csv)
    weighted_sum = 0.0
    total_weight = 0.0
    blockers: List[Dict[str, str]] = []

    for row in rows:
        weight = float(row.get("weight") or 1)
        status = (row.get("status") or "").strip().lower()
        value = 1.0 if status in {"pass", "passed", "done", "yes"} else 0.0
        weighted_sum += value * weight
        total_weight += weight
        if value == 0.0 and weight >= 2:
            blockers.append(row)

    score = 0.0 if total_weight == 0 else round((weighted_sum / total_weight) * 100, 2)
    decision = "go" if score >= args.go_threshold and not blockers else "no-go"

    report = {
        "score": score,
        "go_threshold": args.go_threshold,
        "decision": decision,
        "blocker_count": len(blockers),
        "blockers": blockers,
    }

    print("\n=== Release Gate Decision ===")
    print(f"Readiness score: {score:.2f}")
    print(f"Decision:        {decision.upper()}")
    print(f"Blockers:        {len(blockers)}")

    if args.output:
        Path(args.output).write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"\nSaved gate report: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
