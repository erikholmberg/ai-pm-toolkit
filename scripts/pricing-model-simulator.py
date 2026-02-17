#!/usr/bin/env python3
"""
Pricing Model Simulator

Simulate and compare pricing strategies for AI/SaaS products:
    - Flat-rate (single tier)
    - Tiered (Good / Better / Best)
    - Usage-based (pay per unit — API calls, tokens, seats)
    - Freemium (free tier + paid conversion)
    - Hybrid (base fee + usage overage)

Projects monthly/annual revenue under different user growth and conversion
assumptions. Helps PMs evaluate monetization strategies before committing.

Usage:
    # Compare three models side by side
    python pricing-model-simulator.py \\
        --users 10000 --growth-rate 8 --months 12 \\
        --flat-price 49 \\
        --tiers "Free:0:60,Pro:29:30,Enterprise:99:10" \\
        --usage-price 0.01 --avg-usage 500

    # From a JSON config for complex scenarios
    python pricing-model-simulator.py --config pricing.json

    # Quick freemium analysis
    python pricing-model-simulator.py \\
        --users 50000 --growth-rate 5 --months 12 \\
        --freemium-conversion 4 --freemium-price 19 --churn 3

JSON config format:
    {
      "users": 10000,
      "growth_rate_pct": 8,
      "churn_rate_pct": 3,
      "months": 12,
      "models": [
        {"type": "flat", "name": "Flat $49", "price": 49},
        {"type": "tiered", "name": "3-Tier", "tiers": [
          {"name": "Free", "price": 0, "pct_users": 60},
          {"name": "Pro", "price": 29, "pct_users": 30},
          {"name": "Ent", "price": 99, "pct_users": 10}
        ]},
        {"type": "usage", "name": "Pay-per-use", "price_per_unit": 0.01, "avg_usage": 500},
        {"type": "freemium", "name": "Freemium", "free_pct": 96, "paid_price": 19},
        {"type": "hybrid", "name": "Hybrid", "base_price": 15, "included_units": 100,
         "overage_price": 0.02, "avg_usage": 500}
      ]
    }

Requirements:
    None (stdlib only).
"""

import argparse
import json
import math
import sys
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Growth / churn model
# ---------------------------------------------------------------------------

def project_users(
    initial_users: int,
    monthly_growth_pct: float,
    monthly_churn_pct: float,
    months: int,
) -> List[int]:
    """Project user count month-by-month with growth and churn."""
    users = [initial_users]
    for m in range(1, months + 1):
        prev = users[-1]
        new_users = prev * (monthly_growth_pct / 100)
        churned = prev * (monthly_churn_pct / 100)
        current = max(0, prev + new_users - churned)
        users.append(int(round(current)))
    return users


# ---------------------------------------------------------------------------
# Pricing models
# ---------------------------------------------------------------------------

def simulate_flat(
    user_counts: List[int],
    price: float,
    paid_pct: float = 100.0,
) -> Dict[str, Any]:
    """Flat-rate: every paying user pays the same price."""
    monthly_revenue = []
    for users in user_counts:
        paying = int(users * paid_pct / 100)
        monthly_revenue.append(round(paying * price, 2))

    return {
        "type": "flat",
        "price": price,
        "paid_pct": paid_pct,
        "monthly_revenue": monthly_revenue,
        "total_revenue": round(sum(monthly_revenue), 2),
        "final_mrr": monthly_revenue[-1] if monthly_revenue else 0,
        "final_arr": round(monthly_revenue[-1] * 12, 2) if monthly_revenue else 0,
        "avg_revenue_per_user": round(price * paid_pct / 100, 2),
    }


def simulate_tiered(
    user_counts: List[int],
    tiers: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Tiered pricing: users distributed across tiers with different prices."""
    total_pct = sum(t["pct_users"] for t in tiers)
    if total_pct == 0:
        total_pct = 100

    monthly_revenue = []
    for users in user_counts:
        rev = 0
        for tier in tiers:
            tier_users = int(users * tier["pct_users"] / total_pct)
            rev += tier_users * tier["price"]
        monthly_revenue.append(round(rev, 2))

    blended_arpu = sum(t["price"] * t["pct_users"] / total_pct for t in tiers)

    return {
        "type": "tiered",
        "tiers": tiers,
        "blended_arpu": round(blended_arpu, 2),
        "monthly_revenue": monthly_revenue,
        "total_revenue": round(sum(monthly_revenue), 2),
        "final_mrr": monthly_revenue[-1] if monthly_revenue else 0,
        "final_arr": round(monthly_revenue[-1] * 12, 2) if monthly_revenue else 0,
        "avg_revenue_per_user": round(blended_arpu, 2),
    }


def simulate_usage(
    user_counts: List[int],
    price_per_unit: float,
    avg_usage: float,
    paid_pct: float = 100.0,
) -> Dict[str, Any]:
    """Usage-based: revenue = paying_users × avg_usage × price_per_unit."""
    monthly_revenue = []
    for users in user_counts:
        paying = int(users * paid_pct / 100)
        monthly_revenue.append(round(paying * avg_usage * price_per_unit, 2))

    arpu = avg_usage * price_per_unit * paid_pct / 100

    return {
        "type": "usage",
        "price_per_unit": price_per_unit,
        "avg_usage": avg_usage,
        "paid_pct": paid_pct,
        "monthly_revenue": monthly_revenue,
        "total_revenue": round(sum(monthly_revenue), 2),
        "final_mrr": monthly_revenue[-1] if monthly_revenue else 0,
        "final_arr": round(monthly_revenue[-1] * 12, 2) if monthly_revenue else 0,
        "avg_revenue_per_user": round(arpu, 2),
    }


def simulate_freemium(
    user_counts: List[int],
    conversion_pct: float,
    paid_price: float,
) -> Dict[str, Any]:
    """Freemium: large free base, small % convert to paid."""
    monthly_revenue = []
    for users in user_counts:
        paying = int(users * conversion_pct / 100)
        monthly_revenue.append(round(paying * paid_price, 2))

    arpu = paid_price * conversion_pct / 100

    return {
        "type": "freemium",
        "conversion_pct": conversion_pct,
        "paid_price": paid_price,
        "monthly_revenue": monthly_revenue,
        "total_revenue": round(sum(monthly_revenue), 2),
        "final_mrr": monthly_revenue[-1] if monthly_revenue else 0,
        "final_arr": round(monthly_revenue[-1] * 12, 2) if monthly_revenue else 0,
        "avg_revenue_per_user": round(arpu, 2),
    }


def simulate_hybrid(
    user_counts: List[int],
    base_price: float,
    included_units: float,
    overage_price: float,
    avg_usage: float,
    paid_pct: float = 100.0,
) -> Dict[str, Any]:
    """Hybrid: base subscription + usage overage above included amount."""
    monthly_revenue = []
    overage_units = max(0, avg_usage - included_units)
    per_user_rev = base_price + overage_units * overage_price

    for users in user_counts:
        paying = int(users * paid_pct / 100)
        monthly_revenue.append(round(paying * per_user_rev, 2))

    arpu = per_user_rev * paid_pct / 100

    return {
        "type": "hybrid",
        "base_price": base_price,
        "included_units": included_units,
        "overage_price": overage_price,
        "avg_usage": avg_usage,
        "overage_units": overage_units,
        "per_user_revenue": round(per_user_rev, 2),
        "monthly_revenue": monthly_revenue,
        "total_revenue": round(sum(monthly_revenue), 2),
        "final_mrr": monthly_revenue[-1] if monthly_revenue else 0,
        "final_arr": round(monthly_revenue[-1] * 12, 2) if monthly_revenue else 0,
        "avg_revenue_per_user": round(arpu, 2),
    }


# ---------------------------------------------------------------------------
# Sensitivity analysis
# ---------------------------------------------------------------------------

def sensitivity_analysis(
    base_users: int,
    growth_pct: float,
    churn_pct: float,
    months: int,
    model_fn,
    model_kwargs: Dict,
    param_name: str,
    param_values: List[float],
) -> List[Dict[str, Any]]:
    """Run a model across different values of a parameter."""
    results = []
    for val in param_values:
        kwargs = dict(model_kwargs)
        kwargs[param_name] = val
        user_counts = project_users(base_users, growth_pct, churn_pct, months)
        result = model_fn(user_counts, **kwargs)
        results.append({
            param_name: val,
            "total_revenue": result["total_revenue"],
            "final_mrr": result["final_mrr"],
            "final_arr": result["final_arr"],
        })
    return results


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def _fmt_money(val: float) -> str:
    if abs(val) >= 1_000_000:
        return f"${val/1_000_000:,.1f}M"
    elif abs(val) >= 1_000:
        return f"${val/1_000:,.1f}K"
    else:
        return f"${val:,.2f}"


def _bar(value: float, max_val: float, width: int = 30) -> str:
    if max_val <= 0:
        return "░" * width
    ratio = min(1.0, max(0.0, value / max_val))
    filled = int(ratio * width)
    return "█" * filled + "░" * (width - filled)


def _sparkline(values: List[float]) -> str:
    if not values:
        return ""
    blocks = " ▁▂▃▄▅▆▇█"
    mx = max(values) if values else 1
    mn = min(values) if values else 0
    rng = mx - mn if mx > mn else 1
    return "".join(blocks[min(8, int((v - mn) / rng * 8))] for v in values)


def print_report(
    models: List[Tuple[str, Dict[str, Any]]],
    user_counts: List[int],
    initial_users: int,
    growth_pct: float,
    churn_pct: float,
    months: int,
) -> None:
    """Pretty-print pricing model comparison."""
    print("\n" + "=" * 78)
    print("💰 PRICING MODEL SIMULATOR")
    print("=" * 78)

    # Assumptions
    print(f"\n📋 ASSUMPTIONS:")
    print(f"   • Starting users:     {initial_users:,}")
    print(f"   • Monthly growth:     {growth_pct:.1f}%")
    print(f"   • Monthly churn:      {churn_pct:.1f}%")
    print(f"   • Net monthly growth: {growth_pct - churn_pct:.1f}%")
    print(f"   • Projection period:  {months} months")
    print(f"   • Final user count:   {user_counts[-1]:,}")
    spark = _sparkline([float(u) for u in user_counts])
    print(f"   • User growth curve:  {spark}")

    # Comparison table
    max_total = max((m[1]["total_revenue"] for m in models), default=1)
    max_mrr = max((m[1]["final_mrr"] for m in models), default=1)

    print(f"\n📊 MODEL COMPARISON ({months}-month projection):\n")
    print(f"   {'Model':<22} {'ARPU':>8} {'Final MRR':>12} {'Final ARR':>12} {'Total Rev':>12}")
    print(f"   {'─'*22} {'─'*8} {'─'*12} {'─'*12} {'─'*12}")

    for name, result in models:
        arpu = f"${result['avg_revenue_per_user']:.2f}"
        mrr = _fmt_money(result["final_mrr"])
        arr = _fmt_money(result["final_arr"])
        total = _fmt_money(result["total_revenue"])
        print(f"   {name[:22]:<22} {arpu:>8} {mrr:>12} {arr:>12} {total:>12}")

    # Visual revenue bars
    print(f"\n   Total revenue comparison:")
    for name, result in models:
        bar = _bar(result["total_revenue"], max_total)
        print(f"   {name[:18]:<18} {bar} {_fmt_money(result['total_revenue'])}")

    # Revenue curves
    print(f"\n📈 MONTHLY REVENUE CURVES:")
    for name, result in models:
        spark = _sparkline(result["monthly_revenue"])
        m0 = _fmt_money(result["monthly_revenue"][0]) if result["monthly_revenue"] else "$0"
        mf = _fmt_money(result["monthly_revenue"][-1]) if result["monthly_revenue"] else "$0"
        print(f"   {name[:18]:<18} {m0:>8} {spark} {mf:>8}")

    # Model details
    for name, result in models:
        print(f"\n{'─'*78}")
        print(f"\n💎 {name.upper()} DETAILS:")
        model_type = result["type"]

        if model_type == "flat":
            print(f"   • Price:              ${result['price']:.2f}/mo")
            print(f"   • Paying users:       {result['paid_pct']:.0f}%")

        elif model_type == "tiered":
            print(f"   • Blended ARPU:       ${result['blended_arpu']:.2f}")
            print(f"   • Tier breakdown:")
            final_users = user_counts[-1]
            total_pct = sum(t["pct_users"] for t in result["tiers"])
            for tier in result["tiers"]:
                tier_users = int(final_users * tier["pct_users"] / max(total_pct, 1))
                tier_rev = tier_users * tier["price"]
                pct_label = f"{tier['pct_users']:.0f}%"
                print(f"      {tier['name']:<12} ${tier['price']:>6.2f}  ×  {tier_users:>6,} users ({pct_label:>4}) = {_fmt_money(tier_rev):>10}/mo")

        elif model_type == "usage":
            print(f"   • Price per unit:     ${result['price_per_unit']:.4f}")
            print(f"   • Avg usage/user:     {result['avg_usage']:,.0f} units")
            print(f"   • Revenue/user:       ${result['avg_usage'] * result['price_per_unit']:.2f}/mo")

        elif model_type == "freemium":
            print(f"   • Free → paid rate:   {result['conversion_pct']:.1f}%")
            print(f"   • Paid price:         ${result['paid_price']:.2f}/mo")
            final_paying = int(user_counts[-1] * result["conversion_pct"] / 100)
            final_free = user_counts[-1] - final_paying
            print(f"   • Final free users:   {final_free:,}")
            print(f"   • Final paid users:   {final_paying:,}")

        elif model_type == "hybrid":
            print(f"   • Base price:         ${result['base_price']:.2f}/mo")
            print(f"   • Included units:     {result['included_units']:,.0f}")
            print(f"   • Overage price:      ${result['overage_price']:.4f}/unit")
            print(f"   • Avg usage:          {result['avg_usage']:,.0f} units")
            print(f"   • Overage per user:   {result['overage_units']:,.0f} units → ${result['overage_units'] * result['overage_price']:.2f}")
            print(f"   • Total per user:     ${result['per_user_revenue']:.2f}/mo")

    # Winner
    if len(models) > 1:
        best = max(models, key=lambda m: m[1]["total_revenue"])
        worst = min(models, key=lambda m: m[1]["total_revenue"])
        diff = best[1]["total_revenue"] - worst[1]["total_revenue"]
        print(f"\n{'─'*78}")
        print(f"\n🏆 HIGHEST TOTAL REVENUE: {best[0]} ({_fmt_money(best[1]['total_revenue'])})")
        print(f"   • {_fmt_money(diff)} more than {worst[0]} over {months} months")

        best_arpu = max(models, key=lambda m: m[1]["avg_revenue_per_user"])
        print(f"   • Highest ARPU: {best_arpu[0]} (${best_arpu[1]['avg_revenue_per_user']:.2f}/user)")

    print(f"\n💡 CONSIDERATIONS:")
    print(f"   • Flat-rate: simplest to explain and sell; risks leaving money on the table")
    print(f"   • Tiered: captures different willingness-to-pay; requires clear value differentiation")
    print(f"   • Usage-based: aligns cost with value; revenue can be volatile")
    print(f"   • Freemium: maximizes reach; requires high volume to compensate low conversion")
    print(f"   • Hybrid: predictable base + upside; more complex to communicate")
    print("\n" + "=" * 78)


# ---------------------------------------------------------------------------
# Config parsing
# ---------------------------------------------------------------------------

def parse_tier_string(s: str) -> List[Dict[str, Any]]:
    """Parse 'Name:price:pct,Name:price:pct,...' into tier list."""
    tiers = []
    for part in s.split(","):
        pieces = part.strip().split(":")
        if len(pieces) != 3:
            raise ValueError(f"Invalid tier '{part}'. Format: Name:price:pct_users")
        tiers.append({
            "name": pieces[0].strip(),
            "price": float(pieces[1].strip()),
            "pct_users": float(pieces[2].strip()),
        })
    return tiers


def load_config(path: str) -> Dict[str, Any]:
    """Load pricing configuration from JSON."""
    with open(path, encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Simulate and compare pricing models for AI/SaaS products. "
                    "Projects revenue under growth and churn assumptions.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --users 10000 --growth-rate 8 --months 12 --flat-price 49
  %(prog)s --users 10000 --growth-rate 8 --months 12 \\
           --flat-price 49 \\
           --tiers "Free:0:60,Pro:29:30,Enterprise:99:10" \\
           --usage-price 0.01 --avg-usage 500
  %(prog)s --users 50000 --growth-rate 5 --months 12 \\
           --freemium-conversion 4 --freemium-price 19
  %(prog)s --config pricing.json
        """,
    )

    # Growth assumptions
    parser.add_argument("--users", "-u", type=int, help="Initial user count")
    parser.add_argument("--growth-rate", "-g", type=float, default=5.0, help="Monthly growth rate %% (default: 5)")
    parser.add_argument("--churn", type=float, default=3.0, help="Monthly churn rate %% (default: 3)")
    parser.add_argument("--months", "-m", type=int, default=12, help="Projection period in months (default: 12)")

    # Pricing models
    parser.add_argument("--flat-price", type=float, help="Flat-rate price per user/month")
    parser.add_argument("--flat-paid-pct", type=float, default=100, help="Pct of users who pay (flat model, default: 100)")
    parser.add_argument("--tiers", type=str, help="Tiered pricing: 'Name:price:pct,Name:price:pct,...'")
    parser.add_argument("--usage-price", type=float, help="Usage-based price per unit")
    parser.add_argument("--avg-usage", type=float, default=100, help="Average units consumed per user/month (default: 100)")
    parser.add_argument("--freemium-conversion", type=float, help="Freemium: paid conversion rate %%")
    parser.add_argument("--freemium-price", type=float, help="Freemium: paid tier price")
    parser.add_argument("--hybrid-base", type=float, help="Hybrid: base subscription price")
    parser.add_argument("--hybrid-included", type=float, help="Hybrid: included usage units")
    parser.add_argument("--hybrid-overage", type=float, help="Hybrid: overage price per unit")

    # Config file
    parser.add_argument("--config", type=str, help="JSON config file for complex scenarios")

    parser.add_argument("--output", "-o", type=str, help="Write results to JSON file")
    args = parser.parse_args()

    # Load from config or CLI
    if args.config:
        try:
            config = load_config(args.config)
        except Exception as e:
            print(f"Error loading config: {e}", file=sys.stderr)
            return 1

        initial_users = config.get("users", args.users or 1000)
        growth_pct = config.get("growth_rate_pct", args.growth_rate)
        churn_pct = config.get("churn_rate_pct", args.churn)
        months = config.get("months", args.months)

        user_counts = project_users(initial_users, growth_pct, churn_pct, months)
        models: List[Tuple[str, Dict[str, Any]]] = []

        for mc in config.get("models", []):
            mtype = mc["type"]
            mname = mc.get("name", mtype.title())

            if mtype == "flat":
                models.append((mname, simulate_flat(user_counts, mc["price"], mc.get("paid_pct", 100))))
            elif mtype == "tiered":
                models.append((mname, simulate_tiered(user_counts, mc["tiers"])))
            elif mtype == "usage":
                models.append((mname, simulate_usage(user_counts, mc["price_per_unit"], mc.get("avg_usage", 100), mc.get("paid_pct", 100))))
            elif mtype == "freemium":
                if "conversion_pct" in mc:
                    conv = mc["conversion_pct"]
                elif "free_pct" in mc:
                    conv = 100 - mc["free_pct"]
                else:
                    conv = 4  # sensible default: 4% free-to-paid conversion
                models.append((mname, simulate_freemium(user_counts, conv, mc["paid_price"])))
            elif mtype == "hybrid":
                models.append((mname, simulate_hybrid(
                    user_counts, mc["base_price"], mc.get("included_units", 0),
                    mc.get("overage_price", 0), mc.get("avg_usage", 100), mc.get("paid_pct", 100),
                )))

    else:
        if not args.users:
            print("Error: provide --users or --config.", file=sys.stderr)
            parser.print_help(sys.stderr)
            return 1

        initial_users = args.users
        growth_pct = args.growth_rate
        churn_pct = args.churn
        months = args.months
        user_counts = project_users(initial_users, growth_pct, churn_pct, months)
        models = []

        if args.flat_price is not None:
            models.append((f"Flat ${args.flat_price:.0f}", simulate_flat(user_counts, args.flat_price, args.flat_paid_pct)))

        if args.tiers:
            try:
                tiers = parse_tier_string(args.tiers)
                models.append(("Tiered", simulate_tiered(user_counts, tiers)))
            except ValueError as e:
                print(f"Error parsing tiers: {e}", file=sys.stderr)
                return 1

        if args.usage_price is not None:
            models.append((f"Usage @ ${args.usage_price}", simulate_usage(user_counts, args.usage_price, args.avg_usage)))

        if args.freemium_conversion is not None and args.freemium_price is not None:
            models.append((f"Freemium {args.freemium_conversion:.0f}%", simulate_freemium(user_counts, args.freemium_conversion, args.freemium_price)))

        if args.hybrid_base is not None:
            models.append(("Hybrid", simulate_hybrid(
                user_counts, args.hybrid_base, args.hybrid_included or 0,
                args.hybrid_overage or 0, args.avg_usage,
            )))

    if not models:
        print("Error: no pricing model specified. Use --flat-price, --tiers, --usage-price, "
              "--freemium-conversion/--freemium-price, --hybrid-base, or --config.", file=sys.stderr)
        return 1

    # Report
    print_report(models, user_counts, initial_users, growth_pct, churn_pct, months)

    # JSON output
    if args.output:
        report = {
            "assumptions": {
                "initial_users": initial_users,
                "monthly_growth_pct": growth_pct,
                "monthly_churn_pct": churn_pct,
                "months": months,
                "final_users": user_counts[-1],
            },
            "user_counts": user_counts,
            "models": [{
                "name": name,
                **{k: v for k, v in result.items() if k != "monthly_revenue"},
                "monthly_revenue_final": result["monthly_revenue"][-1] if result["monthly_revenue"] else 0,
            } for name, result in models],
        }
        with open(args.output, "w") as f:
            json.dump(report, f, indent=2)
        print(f"\n📁 Results saved to {args.output}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
