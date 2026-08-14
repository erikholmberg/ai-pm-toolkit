#!/usr/bin/env python3
"""
Context Window Utilization Analyzer

Analyze how fast a conversation/agent session eats into its context window,
turn by turn, and estimate when it will hit the limit. PMs use this to set
sane compaction/summarization triggers and to size context budgets for
long-running agent sessions before users hit hard truncation or degraded
quality from an overfull window.

Reads a CSV of per-turn token counts (or accepts ad-hoc flags for a quick
projection), computes utilization over time, flags the turn where a warning
threshold is crossed, and linearly extrapolates from recent growth to
estimate turns remaining before the window fills.

Usage:
    # From a session log
    python context-window-utilization-analyzer.py --csv session.csv
    python context-window-utilization-analyzer.py --csv session.csv --context-window 1000000 --warn-at-pct 75

    # Quick ad-hoc projection without a CSV
    python context-window-utilization-analyzer.py --current-tokens 120000 --window 200000 --avg-tokens-per-turn 3500

CSV format (header row required):
    turn,tokens_in_turn,cumulative_tokens
    1,1800,1800
    2,2200,4000
    3,1950,5950

    Required: turn, tokens_in_turn (or cumulative_tokens — the other is derived).
    cumulative_tokens is computed from tokens_in_turn if omitted.

Requirements:
    None (stdlib only).
"""

import argparse
import csv
import json
import sys
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def _col(fieldnames: List[str], *aliases: str) -> Optional[str]:
    lower_map = {f.lower().strip(): f for f in fieldnames}
    for alias in aliases:
        if alias.lower().strip() in lower_map:
            return lower_map[alias.lower().strip()]
    return None


def load_session(path: str) -> List[Dict[str, Any]]:
    """Load turn-by-turn token counts, deriving whichever of
    tokens_in_turn / cumulative_tokens is missing."""
    rows: List[Dict[str, Any]] = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fields = reader.fieldnames or []
        c_turn = _col(fields, "turn", "turn_number", "index", "message_number")
        c_in_turn = _col(fields, "tokens_in_turn", "turn_tokens", "tokens", "delta_tokens")
        c_cumulative = _col(fields, "cumulative_tokens", "cumulative", "total_tokens", "running_total")

        for i, row in enumerate(reader):
            raw_turn = (row.get(c_turn or "turn", "") or "").strip()
            try:
                turn = int(float(raw_turn)) if raw_turn else i + 1
            except ValueError:
                turn = i + 1

            raw_in_turn = (row.get(c_in_turn or "tokens_in_turn", "") or "").strip() if c_in_turn else ""
            raw_cumulative = (row.get(c_cumulative or "cumulative_tokens", "") or "").strip() if c_cumulative else ""

            tokens_in_turn = None
            cumulative = None
            try:
                if raw_in_turn:
                    tokens_in_turn = float(raw_in_turn)
                if raw_cumulative:
                    cumulative = float(raw_cumulative)
            except ValueError:
                pass

            if tokens_in_turn is None and cumulative is None:
                continue

            rows.append({"turn": turn, "tokens_in_turn": tokens_in_turn, "cumulative_tokens": cumulative})

    rows.sort(key=lambda r: r["turn"])

    # Fill in whichever field is missing
    running = 0.0
    for r in rows:
        if r["cumulative_tokens"] is None:
            running += r["tokens_in_turn"] or 0.0
            r["cumulative_tokens"] = running
        else:
            running = r["cumulative_tokens"]
    prev_cumulative = 0.0
    for r in rows:
        if r["tokens_in_turn"] is None:
            r["tokens_in_turn"] = max(0.0, r["cumulative_tokens"] - prev_cumulative)
        prev_cumulative = r["cumulative_tokens"]

    return rows


# ---------------------------------------------------------------------------
# Core calculations
# ---------------------------------------------------------------------------

def analyze_session(
    rows: List[Dict[str, Any]],
    context_window: int,
    warn_at_pct: float,
    extrapolate_window: int,
) -> Dict[str, Any]:
    """Compute utilization over time, warning-threshold turn, and a linear
    projection of turns remaining before the window fills."""
    if not rows:
        return {"error": "No turns found."}

    for r in rows:
        r["utilization_pct"] = round(min(999.0, r["cumulative_tokens"] / context_window * 100), 2)

    current = rows[-1]
    warn_turn = next((r["turn"] for r in rows if r["utilization_pct"] >= warn_at_pct), None)

    # Linear extrapolation using the last N turns' average growth rate
    window_rows = rows[-extrapolate_window:] if len(rows) >= 2 else rows
    if len(window_rows) >= 2:
        span_tokens = window_rows[-1]["cumulative_tokens"] - window_rows[0]["cumulative_tokens"]
        span_turns = window_rows[-1]["turn"] - window_rows[0]["turn"]
        avg_growth_per_turn = span_tokens / span_turns if span_turns > 0 else 0.0
    else:
        avg_growth_per_turn = window_rows[0]["tokens_in_turn"] if window_rows else 0.0

    remaining_tokens = context_window - current["cumulative_tokens"]
    if remaining_tokens <= 0:
        projected_turns_remaining = 0.0
    elif avg_growth_per_turn > 0:
        projected_turns_remaining = remaining_tokens / avg_growth_per_turn
    else:
        projected_turns_remaining = None

    projected_fill_turn = (
        current["turn"] + projected_turns_remaining if projected_turns_remaining is not None else None
    )

    return {
        "context_window": context_window,
        "warn_at_pct": warn_at_pct,
        "extrapolate_window": min(extrapolate_window, len(rows)),
        "turns": rows,
        "current_turn": current["turn"],
        "current_tokens": current["cumulative_tokens"],
        "current_utilization_pct": current["utilization_pct"],
        "warn_turn": warn_turn,
        "avg_growth_per_turn": round(avg_growth_per_turn, 1),
        "remaining_tokens": round(remaining_tokens, 0),
        "projected_turns_remaining": round(projected_turns_remaining, 1) if projected_turns_remaining is not None else None,
        "projected_fill_turn": round(projected_fill_turn, 1) if projected_fill_turn is not None else None,
        "already_over_warn": current["utilization_pct"] >= warn_at_pct,
    }


def adhoc_project(current_tokens: float, window: int, avg_tokens_per_turn: float, warn_at_pct: float) -> Dict[str, Any]:
    """Quick projection from a single current-state snapshot, no per-turn history."""
    utilization_pct = round(min(999.0, current_tokens / window * 100), 2)
    remaining_tokens = window - current_tokens
    if remaining_tokens <= 0:
        projected_turns_remaining = 0.0
    elif avg_tokens_per_turn > 0:
        projected_turns_remaining = remaining_tokens / avg_tokens_per_turn
    else:
        projected_turns_remaining = None

    warn_threshold_tokens = window * warn_at_pct / 100
    already_past_warn = current_tokens >= warn_threshold_tokens
    if already_past_warn:
        turns_to_warn = 0.0
    elif avg_tokens_per_turn > 0:
        turns_to_warn = (warn_threshold_tokens - current_tokens) / avg_tokens_per_turn
    else:
        # No growth observed and not yet past threshold: will never get there at this rate.
        turns_to_warn = None

    return {
        "context_window": window,
        "warn_at_pct": warn_at_pct,
        "current_tokens": current_tokens,
        "current_utilization_pct": utilization_pct,
        "avg_growth_per_turn": avg_tokens_per_turn,
        "remaining_tokens": round(remaining_tokens, 0),
        "projected_turns_remaining": round(projected_turns_remaining, 1) if projected_turns_remaining is not None else None,
        "turns_to_warn_threshold": round(turns_to_warn, 1) if turns_to_warn is not None else None,
        "already_over_warn": utilization_pct >= warn_at_pct,
        "adhoc": True,
    }


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def _bar(pct: float, width: int = 30) -> str:
    ratio = max(0.0, min(1.0, pct / 100))
    filled = int(ratio * width)
    return "█" * filled + "░" * (width - filled)


def print_report(result: Dict[str, Any]) -> None:
    print("\n" + "=" * 78)
    print("🪟 CONTEXT WINDOW UTILIZATION ANALYZER")
    print("=" * 78)

    if result.get("error"):
        print(f"\n   ⚠️  {result['error']}\n")
        return

    window = result["context_window"]
    warn_pct = result["warn_at_pct"]

    print(f"\n📋 SESSION:")
    print(f"   • Context window:     {window:,} tokens")
    print(f"   • Warn threshold:     {warn_pct:.0f}%")
    print(f"   • Current tokens:     {result['current_tokens']:,.0f}")
    print(f"   • Current turn:       {result.get('current_turn', '—')}")

    print(f"\n📊 CURRENT UTILIZATION:")
    icon = "🔴" if result["current_utilization_pct"] >= warn_pct else ("🟡" if result["current_utilization_pct"] >= warn_pct * 0.75 else "🟢")
    print(f"   {_bar(result['current_utilization_pct'])} {result['current_utilization_pct']:.1f}%  {icon}")

    if not result.get("adhoc") and result.get("turns"):
        print(f"\n📈 UTILIZATION OVER TIME:")
        print(f"   {'Turn':<6} {'Tokens/turn':>12} {'Cumulative':>12} {'Util %':>8}  ")
        for r in result["turns"]:
            flag = " ⚠️" if r["utilization_pct"] >= warn_pct else ""
            print(f"   {r['turn']:<6} {r['tokens_in_turn']:>12,.0f} {r['cumulative_tokens']:>12,.0f} {r['utilization_pct']:>7.1f}%{flag}")

        if result.get("warn_turn") is not None:
            print(f"\n⚠️  Turn {result['warn_turn']} is the first to cross the {warn_pct:.0f}% warning threshold.")
        else:
            print(f"\n✅ No turn yet crosses the {warn_pct:.0f}% warning threshold.")

    print(f"\n📐 GROWTH & PROJECTION:")
    n_turns = result.get("extrapolate_window")
    basis = f"last {n_turns} turns" if n_turns else "provided rate"
    print(f"   • Avg growth/turn ({basis}):  {result['avg_growth_per_turn']:,.0f} tokens")
    print(f"   • Remaining capacity:              {result['remaining_tokens']:,.0f} tokens")

    if result.get("remaining_tokens", 1) <= 0:
        print(f"   • Projected turns remaining:       0 — already over the context window")
    elif result.get("projected_turns_remaining") is not None:
        pt = result["projected_turns_remaining"]
        print(f"   • Projected turns remaining:       ~{pt:.1f} turns at current growth rate")
        if result.get("projected_fill_turn") is not None:
            print(f"   • Projected fill at turn:          ~{result['projected_fill_turn']:.0f}")
    else:
        print(f"   • Projected turns remaining:       n/a (no growth observed)")

    if "turns_to_warn_threshold" in result:
        ttw = result["turns_to_warn_threshold"]
        if ttw is None:
            print(f"   • Turns until warn threshold:      never, at a growth rate of 0 tokens/turn")
        elif ttw > 0:
            print(f"   • Turns until warn threshold:      ~{ttw:.1f} turns")
        else:
            print(f"   • Already at or past warn threshold.")

    print(f"\n💡 RECOMMENDATION:")
    if result["already_over_warn"]:
        print(f"   🔴 Already at/above the {warn_pct:.0f}% threshold — trigger compaction/summarization now.")
        print(f"      Summarize older turns, drop stale tool outputs, or start a fresh session with a carried-over summary.")
    elif result.get("projected_turns_remaining") is not None and result["projected_turns_remaining"] <= 5:
        print(f"   🟡 Approaching the limit fast (~{result['projected_turns_remaining']:.0f} turns left) — plan a compaction trigger now so it fires before the window fills.")
    else:
        print(f"   🟢 Plenty of headroom at the current growth rate. Set an automated trigger at {warn_pct:.0f}% utilization so you don't have to watch this manually.")
    print(f"   • Compaction strategies: rolling summary of old turns, drop full tool-call payloads once observed, cap retained turn history, or offload to retrieval.")

    print("\n" + "=" * 78)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Analyze context window utilization turn by turn and project when a "
                    "session will hit its limit, to size compaction/summarization triggers.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --csv session.csv
  %(prog)s --csv session.csv --context-window 1000000 --warn-at-pct 75
  %(prog)s --current-tokens 120000 --window 200000 --avg-tokens-per-turn 3500
        """,
    )
    parser.add_argument("--csv", "-c", type=str, help="CSV file with turn-by-turn token counts")
    parser.add_argument("--context-window", type=int, default=200000, help="Model context window in tokens (default: 200000)")
    parser.add_argument("--warn-at-pct", type=float, default=80.0, help="Utilization %% at which to warn/recommend compaction (default: 80)")
    parser.add_argument("--extrapolate-window", type=int, default=5, help="Number of most recent turns used for the growth-rate projection (default: 5)")

    adhoc = parser.add_argument_group("ad-hoc mode (no CSV)")
    adhoc.add_argument("--current-tokens", type=float, help="Current cumulative tokens used")
    adhoc.add_argument("--window", type=int, help="Context window in tokens (overrides --context-window in ad-hoc mode)")
    adhoc.add_argument("--avg-tokens-per-turn", type=float, help="Average tokens consumed per turn")

    parser.add_argument("--output", "-o", type=str, help="Write report to JSON file")
    args = parser.parse_args()

    if args.csv:
        try:
            rows = load_session(args.csv)
        except FileNotFoundError:
            print(f"Error: file not found: {args.csv}", file=sys.stderr)
            return 1
        except Exception as e:
            print(f"Error loading CSV: {e}", file=sys.stderr)
            return 1
        if not rows:
            print("Error: no valid turns found in CSV (need turn + tokens_in_turn or cumulative_tokens).", file=sys.stderr)
            return 1
        result = analyze_session(rows, args.context_window, args.warn_at_pct, max(2, args.extrapolate_window))
    elif args.current_tokens is not None and args.avg_tokens_per_turn is not None:
        window = args.window or args.context_window
        result = adhoc_project(args.current_tokens, window, args.avg_tokens_per_turn, args.warn_at_pct)
    else:
        print("Error: provide --csv, or ad-hoc --current-tokens and --avg-tokens-per-turn.", file=sys.stderr)
        parser.print_help(sys.stderr)
        return 1

    print_report(result)

    if args.output:
        with open(args.output, "w") as f:
            json.dump(result, f, indent=2)
        print(f"\n📁 Report saved to {args.output}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
