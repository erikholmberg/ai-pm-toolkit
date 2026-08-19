#!/usr/bin/env python3
"""
Eval Run Diff

Compare two eval runs case by case, and say whether the difference is real.

eval-score-trend.py answers "did the aggregate score move?" — which is the
wrong question at a model upgrade. An eval set can hold its mean while twelve
cases regress and twelve unrelated ones improve, and the aggregate reports
nothing. Worse, the usual instinct on seeing 84% versus 86% is to treat two
independent proportions as comparable, when the runs are *paired*: the same
cases, scored twice. Ignoring the pairing throws away most of the statistical
power and can invert the conclusion.

So this pairs on case id and runs McNemar's test — the correct test for paired
binary outcomes — on the cases that actually changed. Cases that pass or fail in
both runs carry no information about which run is better and are excluded from
the test, which is exactly why McNemar is more sensitive than comparing two
percentages.

It then names the regressed cases. "Quality dropped 2 points" is not actionable;
a list of eleven case ids is.

Statistics are stdlib only — no scipy — following the `_norm_cdf` pattern
already used in ab-test-calculator.py and experiment-result-interpreter.py.

Usage:
    # Two files, one per run
    python eval-run-diff.py --baseline run-v1.csv --candidate run-v2.csv

    # One file holding both runs
    python eval-run-diff.py --csv all-runs.csv --baseline-run v1 --candidate-run v2

    # Continuous scores: set the pass line, and see the paired mean shift
    python eval-run-diff.py --baseline a.csv --candidate b.csv --pass-threshold 0.7

    python eval-run-diff.py --baseline a.csv --candidate b.csv --by category --top 20
    python eval-run-diff.py --baseline a.csv --candidate b.csv --markdown diff.md --output diff.json

CSV format (header row required):
    case_id,score,category
    q-001,0.92,retrieval
    q-002,fail,summarization

    Required: case_id, score. `score` may be numeric (0.0-1.0 or 0-100) or a
    pass/fail label (pass/fail, yes/no, true/false, 1/0).
    Optional: category, for the per-category breakdown.

    With --csv, a run_id column is also required.

Requirements:
    None (stdlib only).
"""

import argparse
import math
import random
import sys
from collections import defaultdict
from typing import Any, Dict, List, Optional, Sequence, Tuple

import csv_columns
import toolkit_io

TOOL = "eval-run-diff"

PASS_WORDS = {"pass", "passed", "yes", "y", "true", "t", "ok", "success", "correct"}
FAIL_WORDS = {"fail", "failed", "no", "n", "false", "f", "error", "incorrect", "wrong"}


# --------------------------------------------------------------------------
# Statistics (stdlib only)
# --------------------------------------------------------------------------


def _norm_cdf(x: float) -> float:
    """Standard normal CDF. Same helper as ab-test-calculator.py."""
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def mcnemar(regressions: int, fixes: int) -> Dict[str, Any]:
    """McNemar's test on the discordant pairs.

    `regressions` (baseline passed, candidate failed) and `fixes` (the
    reverse) are the only cases carrying information: under the null they
    should be equal. Cases with the same outcome in both runs are excluded by
    construction, which is where the extra power over comparing two
    proportions comes from.

    Uses the exact binomial test when discordant pairs are few — the
    chi-square approximation is unreliable below roughly 25, and eval sets
    routinely have single-digit discordance.
    """
    n = regressions + fixes
    if n == 0:
        return {
            "test": None,
            "p_value": None,
            "discordant": 0,
            "note": "no case changed outcome; the runs are identical on pass/fail",
        }

    if n < 25:
        # Two-sided exact: P(X <= min) doubled, X ~ Binomial(n, 0.5).
        smaller = min(regressions, fixes)
        tail = sum(math.comb(n, k) for k in range(smaller + 1)) / (2**n)
        return {
            "test": "exact binomial",
            "p_value": min(1.0, 2 * tail),
            "discordant": n,
            "note": f"exact test used ({n} discordant pairs < 25)",
        }

    # Chi-square with Edwards' continuity correction, 1 df.
    chi2 = (abs(regressions - fixes) - 1) ** 2 / n
    p = 2 * (1 - _norm_cdf(math.sqrt(chi2)))
    return {
        "test": "chi-square (continuity corrected)",
        "p_value": min(1.0, p),
        "statistic": chi2,
        "discordant": n,
        "note": None,
    }


def bootstrap_ci(
    deltas: Sequence[float], iterations: int = 2000, seed: int = 42
) -> Optional[Dict[str, float]]:
    """Percentile bootstrap CI for the mean paired difference.

    Bootstrap rather than a paired t-test because eval scores are rarely
    normal — they pile up at 0 and 1 — and resampling needs no distributional
    assumption, nor scipy. Seeded so a rerun gives the same interval.
    """
    values = [d for d in deltas if d is not None]
    if len(values) < 2:
        return None
    rng = random.Random(seed)
    n = len(values)
    means = []
    for _ in range(iterations):
        means.append(sum(values[rng.randrange(n)] for _ in range(n)) / n)
    means.sort()
    return {
        "mean": sum(values) / n,
        "lo": means[int(0.025 * iterations)],
        "hi": means[min(iterations - 1, int(0.975 * iterations))],
    }


# --------------------------------------------------------------------------
# Loading
# --------------------------------------------------------------------------


def parse_score(raw: Any) -> Tuple[Optional[float], Optional[bool]]:
    """Return (numeric score, explicit boolean) for a cell.

    A run may be scored either way, and sometimes both appear in one file, so
    both readings are kept rather than forcing one at load time.
    """
    text = str(raw or "").strip().lower()
    if not text:
        return None, None
    if text in PASS_WORDS:
        return 1.0, True
    if text in FAIL_WORDS:
        return 0.0, False
    try:
        value = float(text.replace("%", "").replace(",", ""))
    except ValueError:
        return None, None
    if "%" in str(raw):
        value /= 100.0
    return value, None


def read_run(path: str, run_filter: Optional[str] = None) -> Dict[str, Dict[str, Any]]:
    cases: Dict[str, Dict[str, Any]] = {}
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv_columns.DictReader(f)
        headers = reader.fieldnames or []
        if not csv_columns.resolve(headers, "case_id", "id", "case", "test_id", "name"):
            raise SystemExit(
                f"Error: no case id column in {path}. "
                f"CSV has: {', '.join(headers) or '(empty)'}"
            )
        if not csv_columns.resolve(
            headers, "score", "value", "result", "judge_score", "rating", "passed"
        ):
            raise SystemExit(
                f"Error: no score column in {path}. "
                f"CSV has: {', '.join(headers) or '(empty)'}"
            )
        for row in reader:
            if run_filter is not None:
                run = str(
                    row.first("run_id", "run", "version", "experiment", default="")
                ).strip()
                if run != run_filter:
                    continue
            case_id = str(
                row.first("case_id", "id", "case", "test_id", "name", default="")
            ).strip()
            if not case_id:
                continue
            score, explicit = parse_score(
                row.first(
                    "score", "value", "result", "judge_score", "rating", "passed",
                    default="",
                )
            )
            if score is None:
                continue
            cases[case_id] = {
                "score": score,
                "passed": explicit,
                "category": str(
                    row.first("category", "type", "class", "group", "tag", default="")
                ).strip()
                or "—",
            }
    return cases


def available_runs(path: str) -> List[str]:
    runs = []
    with open(path, newline="", encoding="utf-8-sig") as f:
        for row in csv_columns.DictReader(f):
            run = str(
                row.first("run_id", "run", "version", "experiment", default="")
            ).strip()
            if run and run not in runs:
                runs.append(run)
    return runs


# --------------------------------------------------------------------------
# Analysis
# --------------------------------------------------------------------------


def to_pass(case: Dict[str, Any], threshold: float) -> bool:
    """Pass/fail for one case: an explicit label wins over the threshold."""
    if case["passed"] is not None:
        return case["passed"]
    return case["score"] >= threshold


def analyze(
    baseline: Dict[str, Dict[str, Any]],
    candidate: Dict[str, Dict[str, Any]],
    threshold: float,
    group_by: str,
    seed: int,
) -> Dict[str, Any]:
    shared = sorted(set(baseline) & set(candidate))
    only_baseline = sorted(set(baseline) - set(candidate))
    only_candidate = sorted(set(candidate) - set(baseline))

    if not shared:
        raise SystemExit(
            "Error: the two runs share no case ids, so nothing can be paired. "
            "Check that both files use the same case id column and values."
        )

    cases: List[Dict[str, Any]] = []
    for case_id in shared:
        before, after = baseline[case_id], candidate[case_id]
        before_pass = to_pass(before, threshold)
        after_pass = to_pass(after, threshold)
        cases.append(
            {
                "case_id": case_id,
                "category": after["category"] or before["category"],
                "baseline_score": before["score"],
                "candidate_score": after["score"],
                "delta": after["score"] - before["score"],
                "baseline_pass": before_pass,
                "candidate_pass": after_pass,
                "outcome": (
                    "regression"
                    if before_pass and not after_pass
                    else "fix"
                    if after_pass and not before_pass
                    else "both_pass"
                    if before_pass
                    else "both_fail"
                ),
            }
        )

    counts = defaultdict(int)
    for case in cases:
        counts[case["outcome"]] += 1
    regressions = counts["regression"]
    fixes = counts["fix"]

    test = mcnemar(regressions, fixes)
    ci = bootstrap_ci([c["delta"] for c in cases], seed=seed)

    by_group: Dict[str, Dict[str, Any]] = defaultdict(
        lambda: {"n": 0, "regression": 0, "fix": 0, "delta_sum": 0.0}
    )
    for case in cases:
        key = case[group_by] if group_by in case else case["category"]
        bucket = by_group[str(key)]
        bucket["n"] += 1
        bucket["delta_sum"] += case["delta"]
        if case["outcome"] in ("regression", "fix"):
            bucket[case["outcome"]] += 1
    for bucket in by_group.values():
        bucket["mean_delta"] = bucket["delta_sum"] / bucket["n"] if bucket["n"] else 0.0
        bucket["net"] = bucket["fix"] - bucket["regression"]

    base_pass = sum(1 for c in cases if c["baseline_pass"])
    cand_pass = sum(1 for c in cases if c["candidate_pass"])

    return {
        "paired_cases": len(cases),
        "pass_threshold": threshold,
        "baseline": {
            "passed": base_pass,
            "pass_rate": base_pass / len(cases),
            "mean_score": sum(c["baseline_score"] for c in cases) / len(cases),
        },
        "candidate": {
            "passed": cand_pass,
            "pass_rate": cand_pass / len(cases),
            "mean_score": sum(c["candidate_score"] for c in cases) / len(cases),
        },
        "matrix": {
            "both_pass": counts["both_pass"],
            "regression": regressions,
            "fix": fixes,
            "both_fail": counts["both_fail"],
        },
        "mcnemar": test,
        "score_delta": ci,
        "by_group": {k: dict(v) for k, v in sorted(by_group.items())},
        "group_by": group_by,
        "regressed_cases": sorted(
            [c for c in cases if c["outcome"] == "regression"],
            key=lambda c: c["delta"],
        ),
        "fixed_cases": sorted(
            [c for c in cases if c["outcome"] == "fix"],
            key=lambda c: -c["delta"],
        ),
        "coverage": {
            "only_in_baseline": only_baseline,
            "only_in_candidate": only_candidate,
        },
        "verdict": verdict(regressions, fixes, test),
    }


def verdict(regressions: int, fixes: int, test: Dict[str, Any]) -> Dict[str, Any]:
    p = test.get("p_value")
    if p is None:
        return {"label": "identical", "significant": False}
    significant = p < 0.05
    if not significant:
        label = "no significant change"
    elif regressions > fixes:
        label = "regression"
    else:
        label = "improvement"
    return {"label": label, "significant": significant, "p_value": p}


# --------------------------------------------------------------------------
# Output
# --------------------------------------------------------------------------


def pct(value: float) -> str:
    return f"{value * 100:.1f}%"


def print_report(report: Dict[str, Any], names: Tuple[str, str], top: int) -> None:
    base_name, cand_name = names
    matrix = report["matrix"]
    test = report["mcnemar"]
    v = report["verdict"]

    print("=" * 78)
    print("🔬 EVAL RUN DIFF")
    print("=" * 78)
    print()
    print(f"   Baseline:   {base_name}")
    print(f"   Candidate:  {cand_name}")
    print(f"   Paired:     {report['paired_cases']} cases "
          f"(pass threshold {report['pass_threshold']})")
    print()
    base, cand = report["baseline"], report["candidate"]
    delta_rate = cand["pass_rate"] - base["pass_rate"]
    print(
        f"   Pass rate:  {pct(base['pass_rate'])} → {pct(cand['pass_rate'])}  "
        f"({delta_rate * 100:+.1f} pts)"
    )
    print(
        f"   Mean score: {base['mean_score']:.3f} → {cand['mean_score']:.3f}  "
        f"({cand['mean_score'] - base['mean_score']:+.3f})"
    )

    print()
    print("─" * 78)
    print()
    print("   PAIRED OUTCOMES:")
    print()
    print("                            candidate")
    print("                        pass        fail")
    print(f"     baseline  pass  {matrix['both_pass']:>6}      {matrix['regression']:>6}"
          f"   ← {matrix['regression']} regressed")
    print(f"               fail  {matrix['fix']:>6}      {matrix['both_fail']:>6}")
    print(f"                     ↑ {matrix['fix']} fixed")
    print()
    print(
        f"   Only the {matrix['regression'] + matrix['fix']} discordant cases inform "
        f"the test; the {matrix['both_pass'] + matrix['both_fail']} that"
    )
    print("   agreed carry no signal about which run is better.")

    print()
    print("─" * 78)
    print()
    if test["p_value"] is None:
        print(f"   ⚪ {test['note']}")
    else:
        icon = {"regression": "🔴", "improvement": "✅", "no significant change": "➖"}[
            v["label"]
        ]
        print(f"   McNemar ({test['test']}):  p = {test['p_value']:.4f}")
        print()
        print(f"   {icon} {v['label'].upper()}")
        if v["significant"]:
            direction = (
                "more regressions than fixes"
                if matrix["regression"] > matrix["fix"]
                else "more fixes than regressions"
            )
            print(f"      Significant at p < 0.05 — {direction}.")
        else:
            print(
                f"      {matrix['regression']} regressions vs {matrix['fix']} fixes is "
                f"within what chance produces.\n"
                f"      Not evidence the runs are equivalent — just insufficient "
                f"evidence they differ."
            )
        if test.get("note"):
            print(f"      ({test['note']})")

    ci = report["score_delta"]
    if ci:
        print()
        print(
            f"   Mean paired score delta: {ci['mean']:+.4f}  "
            f"(95% CI {ci['lo']:+.4f} to {ci['hi']:+.4f}, bootstrap)"
        )
        if ci["lo"] > 0:
            print("      CI excludes zero — the candidate scores higher.")
        elif ci["hi"] < 0:
            print("      CI excludes zero — the candidate scores lower.")
        else:
            print("      CI spans zero — the mean shift is not distinguishable from noise.")

    groups = report["by_group"]
    if len(groups) > 1:
        print()
        print("─" * 78)
        print()
        print(f"   BY {report['group_by'].upper()}:")
        print()
        print(f"   {'Group':<26}{'N':>5}{'Regressed':>11}{'Fixed':>7}{'Net':>6}{'Δ mean':>10}")
        print("   " + "─" * 65)
        for name, bucket in sorted(groups.items(), key=lambda kv: kv[1]["net"]):
            print(
                f"   {name[:25]:<26}{bucket['n']:>5}{bucket['regression']:>11}"
                f"{bucket['fix']:>7}{bucket['net']:>+6}{bucket['mean_delta']:>+10.3f}"
            )

    regressed = report["regressed_cases"]
    if regressed:
        print()
        print("─" * 78)
        print()
        print(f"   🔴 REGRESSED CASES ({len(regressed)}):")
        print()
        for case in regressed[:top]:
            print(
                f"      {case['case_id']:<28}{case['baseline_score']:.3f} → "
                f"{case['candidate_score']:.3f}   [{case['category']}]"
            )
        if len(regressed) > top:
            print(f"      … {len(regressed) - top} more (raise --top to see them)")

    coverage = report["coverage"]
    missing = coverage["only_in_baseline"]
    added = coverage["only_in_candidate"]
    if missing or added:
        print()
        print("─" * 78)
        print()
        print("   ⚠️  EVAL SET DRIFT:")
        if missing:
            print(
                f"      {len(missing)} case(s) in baseline but not candidate: "
                f"{', '.join(missing[:5])}"
                + (" …" if len(missing) > 5 else "")
            )
        if added:
            print(
                f"      {len(added)} case(s) in candidate but not baseline: "
                f"{', '.join(added[:5])}"
                + (" …" if len(added) > 5 else "")
            )
        print("      These are excluded from the comparison — the runs are only")
        print("      comparable on cases both scored.")
    print()


def to_markdown(report: Dict[str, Any], names: Tuple[str, str]) -> str:
    matrix = report["matrix"]
    v = report["verdict"]
    test = report["mcnemar"]
    lines = [
        "# Eval Run Diff",
        "",
        f"**{names[0]}** → **{names[1]}** · {report['paired_cases']} paired cases",
        "",
        f"- Pass rate: {pct(report['baseline']['pass_rate'])} → "
        f"{pct(report['candidate']['pass_rate'])}",
        f"- Regressed: **{matrix['regression']}** · Fixed: **{matrix['fix']}**",
        f"- Verdict: **{v['label']}**"
        + (f" (McNemar p = {test['p_value']:.4f})" if test["p_value"] is not None else ""),
        "",
        "| | candidate pass | candidate fail |",
        "|---|---:|---:|",
        f"| **baseline pass** | {matrix['both_pass']} | {matrix['regression']} |",
        f"| **baseline fail** | {matrix['fix']} | {matrix['both_fail']} |",
    ]
    if report["regressed_cases"]:
        lines += ["", "## Regressed cases", "", "| Case | Baseline | Candidate | Category |", "|---|---:|---:|---|"]
        for case in report["regressed_cases"]:
            lines.append(
                f"| {case['case_id']} | {case['baseline_score']:.3f} | "
                f"{case['candidate_score']:.3f} | {case['category']} |"
            )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Compare two eval runs case by case with McNemar's test.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  eval-run-diff.py --baseline v1.csv --candidate v2.csv\n"
            "  eval-run-diff.py --csv runs.csv --baseline-run v1 --candidate-run v2\n"
        ),
    )
    parser.add_argument("--baseline", "-b", help="Baseline run CSV")
    parser.add_argument("--candidate", "-t", help="Candidate run CSV")
    parser.add_argument("--csv", "-c", help="One CSV holding both runs (needs run_id)")
    parser.add_argument("--baseline-run", help="run_id of the baseline, with --csv")
    parser.add_argument("--candidate-run", help="run_id of the candidate, with --csv")
    parser.add_argument(
        "--pass-threshold",
        type=float,
        default=0.5,
        help="Score at or above which a case passes (default: 0.5). Ignored for "
        "cases already labelled pass/fail.",
    )
    parser.add_argument(
        "--by", default="category", help="Grouping column for the breakdown"
    )
    parser.add_argument(
        "--top", type=int, default=15, help="Regressed cases to list (default: 15)"
    )
    parser.add_argument(
        "--seed", type=int, default=42, help="Bootstrap seed (default: 42)"
    )
    parser.add_argument(
        "--fail-on-regression",
        action="store_true",
        help="Exit 1 on a significant regression, for use as a CI gate",
    )
    parser.add_argument("--markdown", help="Write a Markdown report")
    parser.add_argument("--output", help="Write JSON results")
    args = parser.parse_args()

    if args.csv:
        if not args.baseline_run or not args.candidate_run:
            runs = available_runs(args.csv)
            parser.error(
                "--csv needs --baseline-run and --candidate-run. "
                f"Runs found in {args.csv}: {', '.join(runs) or '(none)'}"
            )
        baseline = read_run(args.csv, args.baseline_run)
        candidate = read_run(args.csv, args.candidate_run)
        names = (args.baseline_run, args.candidate_run)
        for label, cases in ((names[0], baseline), (names[1], candidate)):
            if not cases:
                runs = available_runs(args.csv)
                raise SystemExit(
                    f"Error: no rows for run {label!r}. "
                    f"Runs in file: {', '.join(runs) or '(none)'}"
                )
    elif args.baseline and args.candidate:
        baseline = read_run(args.baseline)
        candidate = read_run(args.candidate)
        names = (args.baseline, args.candidate)
    else:
        parser.error(
            "need either --baseline and --candidate, or --csv with "
            "--baseline-run and --candidate-run"
        )

    report = analyze(
        baseline, candidate, args.pass_threshold, args.by, args.seed
    )
    report["runs"] = {"baseline": names[0], "candidate": names[1]}
    print_report(report, names, args.top)

    if args.markdown:
        with open(args.markdown, "w", encoding="utf-8") as f:
            f.write(to_markdown(report, names))
        print(f"   📝 Markdown → {args.markdown}")
    if args.output:
        toolkit_io.write(args.output, report, TOOL)
        print(f"   💾 JSON → {args.output}")

    if args.fail_on_regression and report["verdict"]["label"] == "regression":
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
