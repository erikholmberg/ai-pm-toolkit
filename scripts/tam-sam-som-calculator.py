#!/usr/bin/env python3
"""
TAM / SAM / SOM Calculator

Estimate Total Addressable Market (TAM), Serviceable Addressable Market (SAM),
and Serviceable Obtainable Market (SOM) using top-down, bottom-up, or both
approaches. Foundational for business cases, investor narratives, and
go/no-go decisions.

Definitions:
    TAM  — Total demand for a product category worldwide / in your universe
    SAM  — Portion of TAM you can realistically serve (geo, segment, channel)
    SOM  — Portion of SAM you can capture given your resources and competition

Usage:
    # Top-down approach
    python tam-sam-som-calculator.py \\
        --tam-total-users 50000000 --tam-arpu 120 \\
        --sam-pct 15 --som-pct 5

    # Bottom-up approach
    python tam-sam-som-calculator.py \\
        --bu-segments "SMB:200000:80,Mid-market:50000:250,Enterprise:5000:1200" \\
        --sam-pct 20 --som-pct 8

    # Combined (both approaches)
    python tam-sam-som-calculator.py \\
        --tam-total-users 50000000 --tam-arpu 120 \\
        --bu-segments "SMB:200000:80,Mid-market:50000:250,Enterprise:5000:1200" \\
        --sam-pct 15 --som-pct 5

    # From CSV
    python tam-sam-som-calculator.py --csv segments.csv --som-pct 6

    # With growth projection
    python tam-sam-som-calculator.py \\
        --tam-total-users 50000000 --tam-arpu 120 \\
        --sam-pct 15 --som-pct 5 --growth-rate 12 --years 5

CSV format:
    segment,users,arpu,sam_pct,som_pct
    SMB,200000,80,25,8
    Mid-market,50000,250,20,6
    Enterprise,5000,1200,15,4

    Required: segment, users, arpu
    Optional: sam_pct, som_pct (per-segment overrides)

Requirements:
    None (stdlib only).
"""

import argparse
import csv
import json
import sys
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Market sizing
# ---------------------------------------------------------------------------

def top_down(
    total_users: int,
    arpu: float,
    sam_pct: float,
    som_pct: float,
) -> Dict[str, Any]:
    """Top-down market sizing: TAM × SAM% × SOM%."""
    tam = total_users * arpu
    sam = tam * sam_pct / 100
    som = sam * som_pct / 100

    return {
        "method": "top-down",
        "tam_users": total_users,
        "arpu": arpu,
        "tam": round(tam, 2),
        "sam_pct": sam_pct,
        "sam": round(sam, 2),
        "sam_users": int(total_users * sam_pct / 100),
        "som_pct": som_pct,
        "som": round(som, 2),
        "som_users": int(total_users * sam_pct / 100 * som_pct / 100),
    }


def bottom_up(
    segments: List[Dict[str, Any]],
    default_sam_pct: float = 100.0,
    default_som_pct: float = 100.0,
) -> Dict[str, Any]:
    """Bottom-up market sizing: sum across segments."""
    segment_results = []
    total_tam = 0
    total_sam = 0
    total_som = 0
    total_users = 0

    for seg in segments:
        name = seg["name"]
        users = seg["users"]
        arpu = seg["arpu"]
        sam_pct = seg.get("sam_pct", default_sam_pct)
        som_pct = seg.get("som_pct", default_som_pct)

        seg_tam = users * arpu
        seg_sam = seg_tam * sam_pct / 100
        seg_som = seg_sam * som_pct / 100

        total_tam += seg_tam
        total_sam += seg_sam
        total_som += seg_som
        total_users += users

        segment_results.append({
            "name": name,
            "users": users,
            "arpu": arpu,
            "tam": round(seg_tam, 2),
            "sam_pct": sam_pct,
            "sam": round(seg_sam, 2),
            "som_pct": som_pct,
            "som": round(seg_som, 2),
        })

    blended_arpu = total_tam / total_users if total_users > 0 else 0
    effective_sam_pct = total_sam / total_tam * 100 if total_tam > 0 else 0
    effective_som_pct = total_som / total_sam * 100 if total_sam > 0 else 0

    return {
        "method": "bottom-up",
        "segments": segment_results,
        "n_segments": len(segment_results),
        "total_users": total_users,
        "blended_arpu": round(blended_arpu, 2),
        "tam": round(total_tam, 2),
        "sam": round(total_sam, 2),
        "som": round(total_som, 2),
        "effective_sam_pct": round(effective_sam_pct, 1),
        "effective_som_pct": round(effective_som_pct, 1),
    }


def growth_projection(
    som: float,
    annual_growth_pct: float,
    years: int,
) -> List[Dict[str, Any]]:
    """Project SOM forward with annual growth."""
    projections = []
    current = som
    for year in range(years + 1):
        projections.append({
            "year": year,
            "som": round(current, 2),
            "cumulative_revenue": round(sum(p["som"] for p in projections) + current, 2) if year > 0 else round(current, 2),
        })
        current *= (1 + annual_growth_pct / 100)
    return projections


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def parse_segment_string(s: str) -> List[Dict[str, Any]]:
    """Parse 'Name:users:arpu,Name:users:arpu,...' into segment list."""
    segments = []
    for part in s.split(","):
        pieces = part.strip().rsplit(":", 2)
        if len(pieces) < 3:
            raise ValueError(f"Invalid segment '{part}'. Format: Name:users:arpu")
        segments.append({
            "name": pieces[0].strip(),
            "users": int(pieces[1].strip()),
            "arpu": float(pieces[2].strip()),
        })
    return segments


def _col(fieldnames: List[str], *aliases: str) -> Optional[str]:
    lower_map = {f.lower().strip(): f for f in fieldnames}
    for alias in aliases:
        if alias.lower().strip() in lower_map:
            return lower_map[alias.lower().strip()]
    return None


def load_csv(path: str) -> List[Dict[str, Any]]:
    """Load market segments from CSV."""
    segments: List[Dict[str, Any]] = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fields = reader.fieldnames or []

        c_name = _col(fields, "segment", "name", "market", "category")
        c_users = _col(fields, "users", "customers", "companies", "accounts", "count", "size")
        c_arpu = _col(fields, "arpu", "revenue_per_user", "price", "asp", "avg_price")
        c_sam = _col(fields, "sam_pct", "sam", "serviceable_pct")
        c_som = _col(fields, "som_pct", "som", "obtainable_pct")

        for row in reader:
            name = row.get(c_name or "segment", "").strip()
            if not name:
                continue

            try:
                users = int(float(row.get(c_users or "users", "0").strip().replace(",", "")))
                arpu = float(row.get(c_arpu or "arpu", "0").strip().replace(",", "").replace("$", ""))
            except ValueError:
                continue

            seg: Dict[str, Any] = {"name": name, "users": users, "arpu": arpu}

            if c_sam:
                raw = row.get(c_sam, "").strip().rstrip("%")
                if raw:
                    try:
                        seg["sam_pct"] = float(raw)
                    except ValueError:
                        pass
            if c_som:
                raw = row.get(c_som, "").strip().rstrip("%")
                if raw:
                    try:
                        seg["som_pct"] = float(raw)
                    except ValueError:
                        pass

            segments.append(seg)

    return segments


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def _fmt_money(val: float) -> str:
    if abs(val) >= 1_000_000_000:
        return f"${val / 1_000_000_000:,.1f}B"
    elif abs(val) >= 1_000_000:
        return f"${val / 1_000_000:,.1f}M"
    elif abs(val) >= 1_000:
        return f"${val / 1_000:,.1f}K"
    else:
        return f"${val:,.2f}"


def _fmt_users(val: int) -> str:
    if val >= 1_000_000:
        return f"{val / 1_000_000:,.1f}M"
    elif val >= 1_000:
        return f"{val / 1_000:,.0f}K"
    else:
        return f"{val:,}"


def _bar(value: float, max_val: float, width: int = 30) -> str:
    if max_val <= 0:
        return "░" * width
    ratio = min(1.0, max(0.0, value / max_val))
    filled = int(ratio * width)
    return "█" * filled + "░" * (width - filled)


def print_report(
    td: Optional[Dict[str, Any]],
    bu: Optional[Dict[str, Any]],
    projections: Optional[List[Dict[str, Any]]],
    growth_rate: Optional[float],
) -> None:
    """Pretty-print market sizing analysis."""
    print("\n" + "=" * 78)
    print("🌍 TAM / SAM / SOM CALCULATOR")
    print("=" * 78)

    # Determine primary numbers to display
    if td and bu:
        print(f"\n📋 METHODS: Top-down + Bottom-up comparison")
    elif td:
        print(f"\n📋 METHOD: Top-down")
    elif bu:
        print(f"\n📋 METHOD: Bottom-up")

    # Top-down results
    if td:
        print(f"\n{'─'*78}")
        print(f"\n📐 TOP-DOWN ESTIMATE:")
        print(f"   • Total market users:   {_fmt_users(td['tam_users'])}")
        print(f"   • ARPU:                 ${td['arpu']:,.2f}/year")
        print(f"\n   {'Metric':<8} {'Value':>14} {'Users':>12} {'% of TAM':>10}")
        print(f"   {'─'*8} {'─'*14} {'─'*12} {'─'*10}")
        print(f"   {'TAM':<8} {_fmt_money(td['tam']):>14} {_fmt_users(td['tam_users']):>12} {'100%':>10}")
        print(f"   {'SAM':<8} {_fmt_money(td['sam']):>14} {_fmt_users(td['sam_users']):>12} {td['sam_pct']:>9.1f}%")
        print(f"   {'SOM':<8} {_fmt_money(td['som']):>14} {_fmt_users(td['som_users']):>12} {td['som_pct'] * td['sam_pct'] / 100:>9.2f}%")

        # Visual funnel
        print(f"\n   Market funnel:")
        print(f"   TAM {_bar(td['tam'], td['tam'])} {_fmt_money(td['tam'])}")
        print(f"   SAM {_bar(td['sam'], td['tam'])} {_fmt_money(td['sam'])}")
        print(f"   SOM {_bar(td['som'], td['tam'])} {_fmt_money(td['som'])}")

    # Bottom-up results
    if bu:
        print(f"\n{'─'*78}")
        print(f"\n📊 BOTTOM-UP ESTIMATE:")
        print(f"   • Segments:             {bu['n_segments']}")
        print(f"   • Total market users:   {_fmt_users(bu['total_users'])}")
        print(f"   • Blended ARPU:         ${bu['blended_arpu']:,.2f}/year")

        print(f"\n   {'Metric':<8} {'Value':>14}")
        print(f"   {'─'*8} {'─'*14}")
        print(f"   {'TAM':<8} {_fmt_money(bu['tam']):>14}")
        print(f"   {'SAM':<8} {_fmt_money(bu['sam']):>14}  ({bu['effective_sam_pct']:.1f}% of TAM)")
        print(f"   {'SOM':<8} {_fmt_money(bu['som']):>14}  ({bu['effective_som_pct']:.1f}% of SAM)")

        # Segment breakdown
        print(f"\n   📂 SEGMENT BREAKDOWN:")
        print(f"   {'Segment':<18} {'Users':>10} {'ARPU':>10} {'TAM':>12} {'SAM':>12} {'SOM':>12}")
        print(f"   {'─'*18} {'─'*10} {'─'*10} {'─'*12} {'─'*12} {'─'*12}")

        for seg in bu["segments"]:
            print(f"   {seg['name'][:18]:<18} {_fmt_users(seg['users']):>10} ${seg['arpu']:>8,.0f} {_fmt_money(seg['tam']):>12} {_fmt_money(seg['sam']):>12} {_fmt_money(seg['som']):>12}")

        # Segment TAM share
        print(f"\n   TAM contribution by segment:")
        for seg in sorted(bu["segments"], key=lambda s: -s["tam"]):
            pct = seg["tam"] / bu["tam"] * 100 if bu["tam"] > 0 else 0
            bar = _bar(seg["tam"], bu["tam"], 25)
            print(f"   {seg['name'][:16]:<16} {bar} {pct:.0f}% ({_fmt_money(seg['tam'])})")

        # Funnel
        print(f"\n   Market funnel:")
        print(f"   TAM {_bar(bu['tam'], bu['tam'])} {_fmt_money(bu['tam'])}")
        print(f"   SAM {_bar(bu['sam'], bu['tam'])} {_fmt_money(bu['sam'])}")
        print(f"   SOM {_bar(bu['som'], bu['tam'])} {_fmt_money(bu['som'])}")

    # Comparison (if both methods)
    if td and bu:
        print(f"\n{'─'*78}")
        print(f"\n🔄 METHOD COMPARISON:")
        print(f"   {'':18} {'Top-Down':>14} {'Bottom-Up':>14} {'Delta':>14}")
        print(f"   {'─'*18} {'─'*14} {'─'*14} {'─'*14}")

        for label, td_val, bu_val in [("TAM", td["tam"], bu["tam"]), ("SAM", td["sam"], bu["sam"]), ("SOM", td["som"], bu["som"])]:
            delta = bu_val - td_val
            delta_pct = delta / td_val * 100 if td_val > 0 else 0
            delta_str = f"{_fmt_money(abs(delta))} ({abs(delta_pct):.0f}%)"
            sign = "+" if delta > 0 else "-" if delta < 0 else ""
            print(f"   {label:<18} {_fmt_money(td_val):>14} {_fmt_money(bu_val):>14} {sign}{delta_str:>13}")

        if abs(td["tam"] - bu["tam"]) / max(td["tam"], bu["tam"], 1) > 0.3:
            print(f"\n   ⚠️  >30% gap between methods — review assumptions")
        else:
            print(f"\n   ✅ Methods within 30% — reasonable convergence")

    # Growth projection
    if projections:
        print(f"\n{'─'*78}")
        print(f"\n📈 SOM GROWTH PROJECTION ({growth_rate:.0f}% annual growth):\n")
        print(f"   {'Year':>6} {'SOM':>14}")
        print(f"   {'─'*6} {'─'*14}")

        for p in projections:
            marker = " ← today" if p["year"] == 0 else ""
            print(f"   {'Y' + str(p['year']):>6} {_fmt_money(p['som']):>14}{marker}")

        # Sparkline
        vals = [p["som"] for p in projections]
        blocks = " ▁▂▃▄▅▆▇█"
        mx = max(vals) if vals else 1
        mn = min(vals) if vals else 0
        rng = mx - mn if mx > mn else 1
        spark = "".join(blocks[min(8, int((v - mn) / rng * 8))] for v in vals)
        print(f"\n   Trend: {spark}  ({_fmt_money(vals[0])} → {_fmt_money(vals[-1])})")

        total_period = sum(p["som"] for p in projections)
        print(f"   Total revenue over {len(projections) - 1} years: {_fmt_money(total_period)}")

    # Guidance
    print(f"\n{'─'*78}")
    print(f"\n💡 GUIDANCE:")
    print(f"   • TAM = total demand if you had 100% share and no constraints")
    print(f"   • SAM = portion you can realistically serve (geo, segment, channel)")
    print(f"   • SOM = what you can capture given competition and resources")
    print(f"   • Typical SOM for a startup: 1-5% of SAM in year 1")
    print(f"   • Top-down is useful for investor narratives; bottom-up for planning")
    print(f"   • Use both methods and triangulate — large gaps signal weak assumptions")
    print("\n" + "=" * 78)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Calculate TAM, SAM, and SOM using top-down, bottom-up, or both approaches. "
                    "Foundational for business cases and market analysis.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --tam-total-users 50000000 --tam-arpu 120 --sam-pct 15 --som-pct 5
  %(prog)s --bu-segments "SMB:200000:80,Mid-market:50000:250,Enterprise:5000:1200" --sam-pct 20 --som-pct 8
  %(prog)s --csv segments.csv --som-pct 6
  %(prog)s --tam-total-users 50000000 --tam-arpu 120 --sam-pct 15 --som-pct 5 --growth-rate 12 --years 5
        """,
    )
    # Top-down
    parser.add_argument("--tam-total-users", type=int, help="Total addressable market users")
    parser.add_argument("--tam-arpu", type=float, help="Average revenue per user (annual)")
    parser.add_argument("--tam-revenue", type=float, help="Total TAM revenue directly (alternative to users × arpu)")

    # Bottom-up
    parser.add_argument("--bu-segments", type=str, help="Segments: 'Name:users:arpu,Name:users:arpu,...'")
    parser.add_argument("--csv", "-c", type=str, help="CSV file with segment data")

    # SAM/SOM percentages
    parser.add_argument("--sam-pct", type=float, default=100.0, help="SAM as %% of TAM (default: 100)")
    parser.add_argument("--som-pct", type=float, default=100.0, help="SOM as %% of SAM (default: 100)")

    # Growth
    parser.add_argument("--growth-rate", "-g", type=float, help="Annual market growth rate %% (for projection)")
    parser.add_argument("--years", "-y", type=int, default=5, help="Years to project (default: 5)")

    parser.add_argument("--output", "-o", type=str, help="Write JSON results to file")
    args = parser.parse_args()

    td_result = None
    bu_result = None

    # Top-down
    if args.tam_revenue:
        tam_users = args.tam_total_users or 0
        arpu = args.tam_revenue / tam_users if tam_users > 0 else args.tam_revenue
        if tam_users == 0:
            tam_users = 1
        td_result = top_down(tam_users, arpu, args.sam_pct, args.som_pct)
        td_result["tam"] = args.tam_revenue
        td_result["sam"] = args.tam_revenue * args.sam_pct / 100
        td_result["som"] = td_result["sam"] * args.som_pct / 100
    elif args.tam_total_users and args.tam_arpu:
        td_result = top_down(args.tam_total_users, args.tam_arpu, args.sam_pct, args.som_pct)

    # Bottom-up
    segments = None
    if args.csv:
        try:
            segments = load_csv(args.csv)
        except Exception as e:
            print(f"Error loading CSV: {e}", file=sys.stderr)
            return 1
    elif args.bu_segments:
        try:
            segments = parse_segment_string(args.bu_segments)
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1

    if segments:
        bu_result = bottom_up(segments, args.sam_pct, args.som_pct)

    if not td_result and not bu_result:
        print("Error: provide top-down (--tam-total-users + --tam-arpu) or "
              "bottom-up (--bu-segments or --csv) inputs.", file=sys.stderr)
        parser.print_help(sys.stderr)
        return 1

    # Growth projection
    proj = None
    if args.growth_rate:
        base_som = bu_result["som"] if bu_result else td_result["som"]
        proj = growth_projection(base_som, args.growth_rate, args.years)

    # Report
    print_report(td_result, bu_result, proj, args.growth_rate)

    # JSON output
    if args.output:
        report: Dict[str, Any] = {}
        if td_result:
            report["top_down"] = td_result
        if bu_result:
            report["bottom_up"] = {k: v for k, v in bu_result.items()}
        if proj:
            report["growth_projection"] = proj
        with open(args.output, "w") as f:
            json.dump(report, f, indent=2)
        print(f"\n📁 Results saved to {args.output}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
