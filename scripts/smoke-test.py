#!/usr/bin/env python3
"""
Smoke Test

Runs every script in scripts/ against the sample data scripts/README.md says
goes with it, and checks that it actually produces output. This is the check
that would have caught three scripts (eval-score-trend, hallucination-safety-trend,
inference-latency-trend) whose --output flag raised TypeError on every
invocation — a bug that survived because "python script.py --help" passing is
not the same as "python script.py --csv sample.csv --output out.json" working.

What it checks, per script:
    1. `--help` exits 0.
    2. If scripts/README.md lists sample data for it, run the script against
       that data (auto-detecting the input flag from --help) and confirm the
       process exits 0.
    3. If the script also supports --output, confirm the JSON it writes is
       valid and — via toolkit_io — carries the expected tool name.

A script with no listed sample data only gets the --help check (there's no
generic way to guess required scalar flags like --baseline-rate). That's a
real gap, not a false pass — it's reported as SKIP, not PASS.

Usage:
    python smoke-test.py                  # run everything, summary only
    python smoke-test.py --verbose         # show each script's result
    python smoke-test.py --only launch     # substring-filter script names
    python smoke-test.py --output report.json

Requirements:
    None (stdlib only).
"""

import argparse
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import toolkit_io

TOOL = "smoke-test"

SCRIPTS_DIR = Path(__file__).resolve().parent
README = SCRIPTS_DIR / "README.md"

# Explicit invocations for scripts the generic "one sample file -> the
# script's primary flag" detection can't handle on its own: multiple input
# files with different flag names, a CSV that needs extra required scalar
# flags alongside it, or a script that's scalar-only and has no file input at
# all. Args here always win over README-based auto-detection, and unlike
# that path they're checked regardless of what scripts/README.md's Sample CSV
# column says — several of these (the scalar-only ones) correctly say "—"
# there because they take no file.
#
# Values are extracted from each script's own docstring `Usage:` example
# wherever one exists, so this is the author's own validated invocation, not
# a guess. Paths are relative to scripts/.
EXPLICIT_ARGS: Dict[str, List[str]] = {
    # Multiple input files with different flags.
    "sprint-goal-checker": ["--goals", "samples/sample-sprint-goals.csv",
                             "--completed", "samples/sample-sprint-done.csv"],
    "status-duration-analyzer": ["--csv", "samples/sample-status-transitions.csv"],
    "prompt-version-diff": ["--old", "samples/sample-prompt-v1.txt",
                             "--new", "samples/sample-prompt-v2.txt"],
    "model-selection-scorecard": ["--scores", "samples/sample-model-selection-scores.csv",
                                   "--weights", "samples/sample-model-selection-weights.csv"],
    "data-drift-detector": ["--baseline", "samples/sample-drift-baseline.csv",
                             "--current", "samples/sample-drift-current.csv"],
    # CSV plus required scalar flags the generic detector can't guess.
    "alert-threshold-calculator": ["--csv", "samples/sample-alert-threshold-calculator.csv",
                                    "--column", "p99_ms"],
    "capacity-planner": ["--csv", "samples/sample-capacity-planner.csv",
                          "--team-size", "6", "--velocity", "40", "--sprints", "6"],
    "error-budget-burn-rate": ["--csv", "samples/sample-error-budget-burn-rate.csv",
                                "--sla", "99.9", "--period-days", "30"],
    "metric-forecaster": ["--csv", "samples/sample-metric-forecaster.csv", "--column", "mrr"],
    # Scalar-only — no file input. Taken from each script's own Usage: example.
    "agentic-cost-simulator": [],
    "ai-initiative-roi-calculator": ["--dev-cost", "50000", "--monthly-ai-cost", "2000",
                                      "--monthly-benefit", "10000"],
    "ai-unit-economics-calculator": ["--cost-per-request", "0.002", "--requests-per-month", "1e6",
                                      "--revenue-per-user", "5"],
    "bedrock-cost-calculator": ["--input-tokens", "1000", "--output-tokens", "500", "--model", "claude"],
    "capacity-planning-calculator": ["--team", "6", "--sprint-days", "10", "--pto", "2", "--meetings", "0.2"],
    "confidence-interval-calculator": ["--n", "500", "--proportion", "0.32"],
    "eval-label-economics": ["--margin", "0.05", "--confidence", "0.95", "--cost-per-label", "2.50"],
    "experiment-duration-calculator": ["--baseline", "0.05", "--mde", "0.10", "--daily-visitors", "5000"],
    "experiment-lifecycle-manager": ["--experiment-id", "EXP-001",
                                      "--hypothesis", "New onboarding flow increases activation",
                                      "--primary-metric", "activation_rate",
                                      "--baseline", "45", "--variant", "52", "--p-value", "0.03"],
    "experiment-result-interpreter": ["--baseline", "5.0", "--variant", "5.6", "--n", "8000"],
    "feature-flag-planner": ["--flag", "new-checkout-flow", "--total-users", "500000",
                              "--stages", "Internal:1:2,Beta:5:3,Canary:25:5,GA-50:50:7,GA-100:100:3"],
    "feature-rollout-calculator": ["--daily-volume", "100000"],
    "latency-slo-calculator": ["--availability", "99.9"],
    "model-migration-estimator": ["--from", "claude-3-opus", "--to", "claude-3-5-sonnet",
                                   "--monthly-requests", "100000", "--avg-input-tokens", "800",
                                   "--avg-output-tokens", "400"],
    "model-runtime-orchestrator": ["--prompt", "Summarize this document", "--dry-run"],
    "multi-model-cost-comparator": ["--input-tokens", "1000", "--output-tokens", "500"],
    "nps-csat-summary": ["nps", "--promoters", "40", "--passives", "30", "--detractors", "30"],
    "pricing-model-simulator": ["--users", "10000", "--growth-rate", "8", "--months", "12",
                                 "--flat-price", "49", "--tiers", "Free:0:60,Pro:29:30,Enterprise:99:10",
                                 "--usage-price", "0.01", "--avg-usage", "500"],
    "reasoning-token-budget-calculator": [],
    "survey-sample-size": ["--margin", "0.05", "--confidence", "0.95"],
    "token-budget-allocator": ["--context-window", "128000", "--max-output", "4096",
                                "--system-prompt", "1500", "--avg-user-input", "500",
                                "--rag-chunks", "5", "--chunk-size", "800"],

    # CSV plus extra required flags, or CSV scripts with no --output (JSON envelope)
    # flag at all — the generic detector handles the file, these supply the rest.
    "competitive-feature-matrix": ["--csv", "samples/sample-competitive-feature-matrix.csv", "--us", "Us"],
    "delivery-completion-forecaster": ["--csv", "samples/sample-delivery-completion-forecaster.csv",
                                        "--backlog", "200"],
    "roadmap-simulator": ["--csv", "samples/sample-roadmap-simulator.csv", "--capacity-points", "300"],
    "sla-uptime-calculator": ["--csv", "samples/sample-sla-uptime-calculator.csv", "--sla", "99.9"],
    "sprint-scope-checker": ["--csv", "samples/sample-sprint-scope-checker.csv", "--capacity", "30"],

    # JSON-based scripts.
    "incident-postmortem": ["--json", "samples/sample-incident-postmortem.json"],
    "stakeholder-update": ["--json", "samples/sample-stakeholder-update.json"],
    "rag-quality-analyzer": ["--csv", "samples/sample-rag-quality.csv"],

    # Plain-text-file scripts (reuse the prompt-version-diff sample).
    "prompt-cost-optimizer": ["--file", "samples/sample-prompt-v1.txt", "--model", "claude-opus-5",
                               "--requests-per-month", "500000"],
    "token-counter": ["--file", "samples/sample-prompt-v1.txt", "--model", "claude-opus-5"],
    "sentiment-analysis": ["--file", "samples/sample-sentiment-feedback.csv"],

    # Generative, not analytical — --csv here *writes* a file rather than
    # reading one (it emits the format launch-readiness-score.py consumes).
    "launch-checklist": ["--name", "Agent Copilot", "--type", "backend"],
}

# Preference order when a script's --help lists more than one plausible input
# flag (rare, but --csv and --file both show up across the toolkit).
FLAG_PREFERENCE = ["--csv", "--file", "--input", "--json", "--files"]


def parse_readme_samples() -> Dict[str, List[str]]:
    """script stem -> list of sample file paths (relative to scripts/), from
    the third column of scripts/README.md's per-script tables."""
    samples: Dict[str, List[str]] = {}
    row = re.compile(r"^\|\s*\[([a-z0-9_.-]+\.py)\]\([^)]*\)\s*\|[^|]*\|([^|]*)\|\s*$")
    for line in README.read_text().splitlines():
        m = row.match(line.strip())
        if not m:
            continue
        stem = m.group(1)[:-3]
        cell = m.group(2).strip()
        if cell in ("", "—", "-"):
            continue
        paths = [p.strip() for p in cell.split(",") if "samples/" in p]
        if paths:
            samples[stem] = paths
    return samples


def detect_help(script: Path) -> Tuple[bool, str]:
    """Run --help. Returns (ok, help_text_or_error)."""
    try:
        proc = subprocess.run(
            [sys.executable, str(script), "--help"],
            capture_output=True, text=True, timeout=30,
        )
    except Exception as e:
        return False, str(e)
    if proc.returncode != 0:
        return False, (proc.stderr or proc.stdout).strip().splitlines()[-1:][0] if proc.stderr or proc.stdout else "no output"
    return True, proc.stdout


def detect_input_flag(help_text: str) -> Optional[str]:
    """Find the long-form flag name for the script's primary data input."""
    flag_lines = re.findall(r"^\s+(--[a-z][a-z-]*)", help_text, flags=re.M)
    for preferred in FLAG_PREFERENCE:
        if preferred in flag_lines:
            return preferred
    return None


def output_flag_help_line(help_text: str) -> Optional[str]:
    # `--output` must end the flag token here (comma before a short alias,
    # or whitespace before its metavar) — plain \b also matches inside
    # "--output-tokens" and "--output-dir", which are different flags.
    m = re.search(r"^\s+--output(?:,|\s).*(?:\n\s{10,}.*)*", help_text, flags=re.M)
    return m.group(0) if m else None


def output_writes_json(help_text: str) -> bool:
    """Most scripts' --output help text says "JSON" explicitly. A few (e.g. the
    system-card builder) reuse --output for a rendered document — those are a
    different, legitimate contract and shouldn't be judged against the JSON
    envelope."""
    line = output_flag_help_line(help_text)
    return bool(line and "json" in line.lower())


def run_with_data(script: Path, stem: str, help_text: str, sample_files: List[str]):
    """Returns (status, detail) where status is PASS / FAIL / SKIP."""
    if stem in EXPLICIT_ARGS:
        args = list(EXPLICIT_ARGS[stem])
    else:
        if len(sample_files) != 1:
            return "SKIP", f"README lists {len(sample_files)} sample files; no flag mapping for this script"
        flag = detect_input_flag(help_text)
        if not flag:
            return "SKIP", "no recognizable input flag in --help (looked for --csv/--file/--input)"
        args = [flag, sample_files[0]]

    for i, val in enumerate(args):
        if val.startswith("samples/"):
            candidate = SCRIPTS_DIR / val
            if not candidate.exists():
                return "SKIP", f"sample file not found: {val}"
            args[i] = str(candidate)

    out_path = None
    check_json = output_flag_help_line(help_text) is not None and output_writes_json(help_text)
    if output_flag_help_line(help_text) is not None:
        tmp = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
        out_path = tmp.name
        tmp.close()
        args += ["--output", out_path]

    try:
        proc = subprocess.run(
            [sys.executable, str(script), *args],
            capture_output=True, text=True, timeout=30,
        )
    except Exception as e:
        return "FAIL", f"execution error: {e}"

    if proc.returncode != 0:
        tail = (proc.stderr or proc.stdout).strip().splitlines()
        return "FAIL", tail[-1] if tail else f"exit {proc.returncode}, no output"

    if out_path:
        try:
            size = Path(out_path).stat().st_size
            if size == 0:
                return "FAIL", "--output file was created but left empty"
            if check_json:
                with open(out_path) as f:
                    obj = json.load(f)
                if toolkit_io.is_enveloped(obj) and obj.get("tool") != stem:
                    return "FAIL", f"envelope tool mismatch: wrote '{obj.get('tool')}', expected '{stem}'"
        except json.JSONDecodeError as e:
            return "FAIL", f"--output wrote invalid JSON: {e}"
        finally:
            Path(out_path).unlink(missing_ok=True)

    detail = "ran with sample data"
    if out_path:
        detail += " + validated JSON --output" if check_json else " + --output non-empty (non-JSON contract, not envelope-checked)"
    return "PASS", detail


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run every scripts/*.py against its sample data and report what actually works.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  smoke-test.py
  smoke-test.py --verbose
  smoke-test.py --only launch
  smoke-test.py --output report.json
        """,
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Print every script's result, not just failures")
    parser.add_argument("--only", help="Substring filter on script name")
    parser.add_argument("--output", "-o", help="Write JSON results to file")
    args = parser.parse_args()

    samples = parse_readme_samples()
    scripts = sorted(
        p for p in SCRIPTS_DIR.glob("*.py")
        if p.stem not in ("model_pricing", "csv_columns", "toolkit_io", "smoke-test".replace("-", "_"), "smoke-test")
    )
    if args.only:
        scripts = [p for p in scripts if args.only in p.stem]

    results: Dict[str, Dict[str, str]] = {}
    counts = {"PASS": 0, "FAIL": 0, "SKIP": 0, "HELP_FAIL": 0}

    for script in scripts:
        stem = script.stem
        help_ok, help_text = detect_help(script)
        if not help_ok:
            results[stem] = {"status": "HELP_FAIL", "detail": help_text}
            counts["HELP_FAIL"] += 1
            continue

        sample_files = samples.get(stem)
        if not sample_files and stem not in EXPLICIT_ARGS:
            results[stem] = {"status": "SKIP", "detail": "no sample data listed in scripts/README.md"}
            counts["SKIP"] += 1
            continue

        status, detail = run_with_data(script, stem, help_text, sample_files or [])
        results[stem] = {"status": status, "detail": detail}
        counts[status] += 1

    print(f"\n{'SCRIPT':<38}{'STATUS':<10}DETAIL")
    print("-" * 100)
    for stem in sorted(results):
        r = results[stem]
        if r["status"] in ("PASS",) and not args.verbose:
            continue
        print(f"{stem:<38}{r['status']:<10}{r['detail']}")

    print("-" * 100)
    print(
        f"PASS: {counts['PASS']}   FAIL: {counts['FAIL']}   "
        f"SKIP: {counts['SKIP']}   HELP_FAIL: {counts['HELP_FAIL']}   "
        f"(of {len(scripts)} scripts)"
    )
    if counts["SKIP"]:
        print(
            f"\n{counts['SKIP']} scripts have no listed sample data and were only "
            f"--help-checked. Add a row to scripts/README.md's per-script table to "
            f"cover them here."
        )

    if args.output:
        toolkit_io.write(args.output, {"results": results, "counts": counts}, TOOL)
        print(f"\nWrote {args.output}")

    return 1 if (counts["FAIL"] or counts["HELP_FAIL"]) else 0


if __name__ == "__main__":
    sys.exit(main())
