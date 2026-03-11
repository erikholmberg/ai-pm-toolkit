#!/usr/bin/env python3
"""
Risk Register Summary

Summarize risks from a CSV: risk score (likelihood × impact), list sorted by
score, and "top N to mitigate" for status docs and planning. Complements
dependency-risk-mapper for program-level risk view.

Usage:
    # Basic (risk, likelihood, impact columns)
    python risk-register-summary.py --csv risks.csv

    # Top 5 to mitigate; custom columns
    python risk-register-summary.py --csv risks.csv --top 5 --likelihood prob --impact impact_level

    # Export
    python risk-register-summary.py --csv risks.csv --markdown report.md --output report.json

CSV format:
    risk,likelihood,impact,owner
    API dependency on vendor,High,High,Platform
    Key person dependency,3,4,Engineering
    Scope creep,Medium,Medium,PM

    Required: risk (or title/description), likelihood, impact.
    Likelihood/impact: 1-5 numeric, or Low(1)/Medium(2)/High(3)/Critical(4).
    Optional: owner.

Requirements:
    None (stdlib only).
"""

import argparse
import csv
import json
import sys
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Column helper and scale parsing
# ---------------------------------------------------------------------------

def _col(fieldnames: List[str], *aliases: str) -> Optional[str]:
    lower_map = {f.lower().strip(): f for f in fieldnames}
    for alias in aliases:
        if alias.lower().strip() in lower_map:
            return lower_map[alias.lower().strip()]
    return None


# Word to numeric scale (1-5); product L×I gives score 1-25
LIKELIHOOD_IMPACT_MAP = {
    "low": 1, "l": 1, "1": 1,
    "medium": 2, "med": 2, "m": 2, "2": 2,
    "high": 3, "h": 3, "3": 3,
    "critical": 4, "crit": 4, "4": 4,
    "5": 5,
}


def parse_scale(val: str) -> int:
    """Parse likelihood or impact: number 1-5 or word (Low/Medium/High/Critical)."""
    if not val or not str(val).strip():
        return 1
    s = str(val).strip().lower().replace(",", "")
    try:
        n = int(float(s))
        return max(1, min(5, n))
    except ValueError:
        pass
    return LIKELIHOOD_IMPACT_MAP.get(s, 1)


# ---------------------------------------------------------------------------
# Load risks
# ---------------------------------------------------------------------------

def load_risks(
    path: str,
    risk_col: str = "risk",
    likelihood_col: str = "likelihood",
    impact_col: str = "impact",
    owner_col: str = "owner",
) -> List[Dict[str, Any]]:
    """Load risk register from CSV."""
    rows: List[Dict[str, Any]] = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fields = reader.fieldnames or []

        c_risk = _col(fields, risk_col, "risk", "title", "description", "name", "risk_description")
        c_lik = _col(fields, likelihood_col, "likelihood", "probability", "prob", "l")
        c_imp = _col(fields, impact_col, "impact", "impact_level", "severity", "i")
        c_owner = _col(fields, owner_col, "owner", "assignee", "responsible")

        for row in reader:
            risk_text = (row.get(c_risk or "risk", "") or "").strip()
            if not risk_text:
                risk_text = f"Risk {len(rows) + 1}"
            lik_raw = (row.get(c_lik or "likelihood", "") or "").strip()
            imp_raw = (row.get(c_imp or "impact", "") or "").strip()
            lik = parse_scale(lik_raw)
            imp = parse_scale(imp_raw)
            score = lik * imp
            owner = (row.get(c_owner or "owner", "") or "").strip() or "—"
            rows.append({
                "risk": risk_text,
                "likelihood": lik,
                "impact": imp,
                "score": score,
                "owner": owner,
            })

    rows.sort(key=lambda r: (-r["score"], r["risk"]))
    return rows


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

def summarize_risks(risks: List[Dict[str, Any]], top_n: int) -> Dict[str, Any]:
    """Build summary: sorted list, top N to mitigate."""
    if not risks:
        return {"risks": [], "total": 0, "top_to_mitigate": [], "top_n": top_n}
    top_to_mitigate = risks[:top_n]
    return {
        "risks": risks,
        "total": len(risks),
        "top_to_mitigate": top_to_mitigate,
        "top_n": top_n,
        "max_score": max(r["score"] for r in risks),
    }


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def print_report(result: Dict[str, Any]) -> None:
    """Pretty-print risk register summary."""
    print("\n" + "=" * 70)
    print("⚠️  RISK REGISTER SUMMARY")
    print("=" * 70)

    risks = result.get("risks", [])
    if not risks:
        print("\n   No risks in CSV.\n")
        return

    total = result["total"]
    top_n = result["top_n"]
    print(f"\n   Total risks:  {total}")
    print(f"   Score = likelihood × impact (1-5 each, max 25)")
    print(f"\n   {'Risk':<40} {'L':>3} {'I':>3} {'Score':>5}  Owner")
    print("   " + "─" * 62)
    for r in risks:
        risk_short = (r["risk"][:39] + "…") if len(r["risk"]) > 40 else r["risk"]
        print(f"   {risk_short:<40} {r['likelihood']:>3} {r['impact']:>3} {r['score']:>5}  {r['owner']}")

    top = result.get("top_to_mitigate", [])
    if top:
        print(f"\n   Top {len(top)} to mitigate:")
        for i, r in enumerate(top, 1):
            risk_short = (r["risk"][:50] + "…") if len(r["risk"]) > 50 else r["risk"]
            print(f"      {i}. [{r['score']}] {risk_short}  ({r['owner']})")

    print("\n   💡 Use for status updates and prioritising mitigation.\n")


def to_json_result(result: Dict[str, Any]) -> Dict[str, Any]:
    """JSON-serializable result."""
    return {
        "total": result.get("total", 0),
        "top_n": result.get("top_n", 5),
        "risks": result.get("risks", []),
        "top_to_mitigate": result.get("top_to_mitigate", []),
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Summarize risk register: score, sort, top N to mitigate.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--csv", "-c", required=True, help="Path to risk register CSV")
    parser.add_argument("--top", "-t", type=int, default=5, metavar="N", help="Number of top risks to list as 'to mitigate' (default: 5)")
    parser.add_argument("--risk", type=str, default="risk", help="Risk description column name")
    parser.add_argument("--likelihood", type=str, default="likelihood", help="Likelihood column name")
    parser.add_argument("--impact", type=str, default="impact", help="Impact column name")
    parser.add_argument("--owner", type=str, default="owner", help="Owner column name")
    parser.add_argument("--markdown", metavar="FILE", help="Write Markdown report to FILE")
    parser.add_argument("--output", "-o", metavar="FILE", help="Write JSON result to FILE")
    args = parser.parse_args()

    risks = load_risks(
        args.csv,
        risk_col=args.risk,
        likelihood_col=args.likelihood,
        impact_col=args.impact,
        owner_col=args.owner,
    )
    result = summarize_risks(risks, max(1, args.top))
    print_report(result)

    if args.markdown and result.get("risks"):
        with open(args.markdown, "w", encoding="utf-8") as f:
            f.write("# Risk Register Summary\n\n")
            f.write(f"- **Total risks:** {result['total']}\n")
            f.write(f"- **Top to mitigate:** {result['top_n']}\n\n")
            f.write("| Risk | L | I | Score | Owner |\n")
            f.write("|------|---|---|-------|-------|\n")
            for r in result["risks"]:
                risk_esc = r["risk"].replace("|", "\\|")[:60]
                f.write(f"| {risk_esc} | {r['likelihood']} | {r['impact']} | {r['score']} | {r['owner']} |\n")
            f.write("\n## Top to mitigate\n\n")
            for i, r in enumerate(result.get("top_to_mitigate", []), 1):
                risk_esc = r["risk"].replace("|", "\\|")[:60]
                f.write(f"{i}. **{risk_esc}** (score {r['score']}, owner: {r['owner']})\n")
        print(f"Wrote Markdown to {args.markdown}")

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(to_json_result(result), f, indent=2)
        print(f"Wrote JSON to {args.output}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
