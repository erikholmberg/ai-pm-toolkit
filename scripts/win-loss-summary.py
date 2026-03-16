#!/usr/bin/env python3
"""
Win-Loss Summary

Summarize deal outcomes from CSV: win rate, top loss reasons, optional breakdown
by segment. For pricing and GTM reviews.

Usage:
    # Basic (opportunity_id, outcome, reason)
    python win-loss-summary.py --csv deals.csv

    # Top 5 loss reasons; group by segment
    python win-loss-summary.py --csv deals.csv --top 5 --group-by segment

    # Export
    python win-loss-summary.py --csv deals.csv --markdown report.md --output report.json

CSV format:
    opportunity_id,outcome,reason,segment
    opp-001,won,
    opp-002,lost,Price
    opp-003,lost,Competitor - Acme
    opp-004,won,,Enterprise

    Required: outcome (won/lost). Optional: opportunity_id, reason (or competitor), segment.
    Outcome: won/win/yes/1 = won; lost/loss/no/0 = lost.

Requirements:
    None (stdlib only).
"""

import argparse
import csv
import json
import sys
from collections import Counter, defaultdict
from typing import Any, Dict, List, Optional


def _col(fieldnames: List[str], *aliases: str) -> Optional[str]:
    lower_map = {f.lower().strip(): f for f in fieldnames}
    for alias in aliases:
        if alias.lower().strip() in lower_map:
            return lower_map[alias.lower().strip()]
    return None


WON_VALUES = {"won", "win", "yes", "y", "true", "1", "closed won"}
LOST_VALUES = {"lost", "loss", "no", "n", "false", "0", "closed lost"}


def is_won(val: str) -> Optional[bool]:
    if not val or not str(val).strip():
        return None
    s = str(val).strip().lower()
    if s in WON_VALUES:
        return True
    if s in LOST_VALUES:
        return False
    return None


def load_deals(
    path: str,
    id_col: str = "opportunity_id",
    outcome_col: str = "outcome",
    reason_col: str = "reason",
    segment_col: str = "segment",
) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fields = reader.fieldnames or []
        c_id = _col(fields, id_col, "opportunity_id", "id", "deal", "opportunity")
        c_outcome = _col(fields, outcome_col, "outcome", "result", "status", "won")
        c_reason = _col(fields, reason_col, "reason", "competitor", "loss_reason", "why")
        c_segment = _col(fields, segment_col, "segment", "region", "motion")

        for row in reader:
            raw_outcome = (row.get(c_outcome or "outcome", "") or "").strip()
            won = is_won(raw_outcome)
            if won is None:
                continue
            opp_id = (row.get(c_id or "opportunity_id", "") or "").strip() or f"deal_{len(rows) + 1}"
            reason = (row.get(c_reason or "reason", "") or "").strip() or "—"
            segment = (row.get(c_segment or "segment", "") or "").strip() or "—"
            rows.append({
                "opportunity_id": opp_id,
                "won": won,
                "reason": reason,
                "segment": segment,
            })
    return rows


def summarize_win_loss(
    deals: List[Dict[str, Any]],
    top_n: int,
    group_by_segment: bool,
) -> Dict[str, Any]:
    won_count = sum(1 for d in deals if d["won"])
    lost_count = sum(1 for d in deals if d["won"] is False)
    total = len(deals)
    win_rate_pct = (100.0 * won_count / total) if total else 0

    loss_reasons = [d["reason"] for d in deals if not d["won"] and d["reason"] != "—"]
    reason_counts = Counter(loss_reasons).most_common(top_n)
    top_loss_reasons = [{"reason": r, "count": c} for r, c in reason_counts]

    by_segment: Dict[str, Dict[str, Any]] = {}
    if group_by_segment:
        by_seg: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        for d in deals:
            by_seg[d["segment"]].append(d)
        for seg, items in sorted(by_seg.items()):
            w = sum(1 for x in items if x["won"])
            t = len(items)
            by_segment[seg] = {
                "won": w,
                "total": t,
                "win_rate_pct": round(100.0 * w / t, 1) if t else 0,
            }

    return {
        "won": won_count,
        "lost": lost_count,
        "total": total,
        "win_rate_pct": round(win_rate_pct, 1),
        "top_loss_reasons": top_loss_reasons,
        "top_n": top_n,
        "by_segment": by_segment,
    }


def print_report(result: Dict[str, Any]) -> None:
    print("\n" + "=" * 70)
    print("🏆 WIN-LOSS SUMMARY")
    print("=" * 70)

    total = result["total"]
    if total == 0:
        print("\n   No deals with valid outcome in CSV (need won/lost).\n")
        return

    print(f"\n   Total deals:  {total}")
    print(f"   Won:          {result['won']}")
    print(f"   Lost:         {result['lost']}")
    print(f"   Win rate:     {result['win_rate_pct']}%")

    if result.get("top_loss_reasons"):
        print(f"\n   Top loss reasons (top {result['top_n']}):")
        print("   " + "─" * 40)
        for r in result["top_loss_reasons"]:
            print(f"      {r['reason']:<32} {r['count']:>5}")

    if result.get("by_segment"):
        print(f"\n   By segment:")
        print(f"   {'Segment':<18} {'Won':>6} {'Total':>6}  {'Win %':>8}")
        print("   " + "─" * 44)
        for seg, s in result["by_segment"].items():
            print(f"   {seg:<18} {s['won']:>6} {s['total']:>6}  {s['win_rate_pct']:>7.1f}%")

    print("\n   💡 Use for pricing and GTM reviews.\n")


def to_json_result(result: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "won": result.get("won", 0),
        "lost": result.get("lost", 0),
        "total": result.get("total", 0),
        "win_rate_pct": result.get("win_rate_pct", 0),
        "top_loss_reasons": result.get("top_loss_reasons", []),
        "top_n": result.get("top_n", 5),
        "by_segment": result.get("by_segment", {}),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Win rate, top loss reasons, optional by segment.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--csv", "-c", required=True, help="Path to deals CSV (outcome required; reason, segment optional)")
    parser.add_argument("--top", "-t", type=int, default=5, metavar="N", help="Top N loss reasons (default: 5)")
    parser.add_argument("--group-by", type=str, default=None, metavar="COL", help="Group by segment/region")
    parser.add_argument("--markdown", metavar="FILE", help="Write Markdown report to FILE")
    parser.add_argument("--output", "-o", metavar="FILE", help="Write JSON result to FILE")
    args = parser.parse_args()

    deals = load_deals(args.csv)
    if not deals:
        print("No deals with valid outcome in CSV (need won/lost).", file=sys.stderr)
        return 1

    result = summarize_win_loss(
        deals,
        max(1, args.top),
        group_by_segment=args.group_by is not None,
    )
    print_report(result)

    if args.markdown and result.get("total"):
        with open(args.markdown, "w", encoding="utf-8") as f:
            f.write("# Win-Loss Summary\n\n")
            f.write(f"- **Total:** {result['total']}  |  **Won:** {result['won']}  |  **Lost:** {result['lost']}  |  **Win rate:** {result['win_rate_pct']}%\n\n")
            if result.get("top_loss_reasons"):
                f.write("## Top loss reasons\n\n")
                f.write("| Reason | Count |\n")
                f.write("|--------|-------|\n")
                for r in result["top_loss_reasons"]:
                    reason_esc = r["reason"].replace("|", "\\|")
                    f.write(f"| {reason_esc} | {r['count']} |\n")
            if result.get("by_segment"):
                f.write("\n## By segment\n\n")
                f.write("| Segment | Won | Total | Win % |\n")
                f.write("|---------|-----|-------|-------|\n")
                for seg, s in result["by_segment"].items():
                    f.write(f"| {seg} | {s['won']} | {s['total']} | {s['win_rate_pct']:.1f}% |\n")
        print(f"Wrote Markdown to {args.markdown}")

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(to_json_result(result), f, indent=2)
        print(f"Wrote JSON to {args.output}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
