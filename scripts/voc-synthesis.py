#!/usr/bin/env python3
"""
VoC Synthesis Tool

Combines feedback from Slack/support/interviews, deduplicates similar items,
and ranks opportunities by weighted severity-frequency score.
"""

import argparse
import csv
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, List, Tuple


def normalize(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    words = [w for w in text.split() if len(w) > 2]
    return " ".join(words)


def ngrams(text: str, n: int = 3) -> set[str]:
    words = text.split()
    if len(words) < n:
        return {text} if text else set()
    return {" ".join(words[i : i + n]) for i in range(len(words) - n + 1)}


def jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    return len(a.intersection(b)) / len(a.union(b))


def load_rows(path: str) -> List[Dict[str, str]]:
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def main() -> int:
    parser = argparse.ArgumentParser(description="Synthesize and rank Voice-of-Customer feedback.")
    parser.add_argument("--csv", required=True, help="Input CSV")
    parser.add_argument("--similarity-threshold", type=float, default=0.45, help="Dedup threshold")
    parser.add_argument("--output", help="Write JSON output")
    args = parser.parse_args()

    # Expected columns: source,text,severity (1-5),theme(optional)
    rows = load_rows(args.csv)
    clusters: List[Dict[str, object]] = []
    theme_counter: Counter[str] = Counter()
    source_counter: Counter[str] = Counter()

    for row in rows:
        text = (row.get("text") or "").strip()
        if not text:
            continue
        source = (row.get("source") or "unknown").strip()
        severity = float(row.get("severity") or 3)
        theme = (row.get("theme") or "unlabeled").strip()

        source_counter[source] += 1
        theme_counter[theme] += 1

        normalized = normalize(text)
        sig = ngrams(normalized)

        assigned = False
        for cluster in clusters:
            score = jaccard(sig, cluster["signature"])  # type: ignore[arg-type]
            if score >= args.similarity_threshold:
                cluster["items"].append({"source": source, "text": text, "severity": severity, "theme": theme})  # type: ignore[index]
                cluster["severity_sum"] += severity  # type: ignore[index]
                assigned = True
                break
        if not assigned:
            clusters.append(
                {
                    "signature": sig,
                    "seed": text,
                    "items": [{"source": source, "text": text, "severity": severity, "theme": theme}],
                    "severity_sum": severity,
                }
            )

    opportunities: List[Dict[str, object]] = []
    for idx, cluster in enumerate(clusters, start=1):
        items = cluster["items"]  # type: ignore[assignment]
        freq = len(items)  # type: ignore[arg-type]
        sev_sum = float(cluster["severity_sum"])  # type: ignore[arg-type]
        avg_sev = sev_sum / max(1, freq)
        score = round((freq * 0.6) + (avg_sev * 0.4), 2)
        theme_dist = Counter(item["theme"] for item in items)  # type: ignore[index]
        opportunities.append(
            {
                "opportunity_id": f"VOC-{idx:03d}",
                "problem_statement": cluster["seed"],
                "frequency": freq,
                "avg_severity": round(avg_sev, 2),
                "opportunity_score": score,
                "top_themes": theme_dist.most_common(3),
                "sources": Counter(item["source"] for item in items),  # type: ignore[index]
            }
        )

    opportunities.sort(key=lambda o: (o["opportunity_score"], o["frequency"]), reverse=True)

    report = {
        "summary": {
            "input_rows": len(rows),
            "deduped_problem_clusters": len(opportunities),
            "sources": dict(source_counter),
            "themes": dict(theme_counter),
        },
        "opportunities": opportunities,
    }

    print("\n=== VoC Synthesis ===")
    print(f"Input rows:    {report['summary']['input_rows']}")
    print(f"Problem sets:  {report['summary']['deduped_problem_clusters']}")
    print("Top opportunities:")
    for opp in opportunities[:5]:
        print(
            f"- {opp['opportunity_id']}: score={opp['opportunity_score']} "
            f"freq={opp['frequency']} avg_sev={opp['avg_severity']}"
        )

    if args.output:
        Path(args.output).write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"\nSaved synthesis report: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
