#!/usr/bin/env python3
"""
Model Runtime Orchestrator

Implements a lightweight runtime foundation for:
- Policy-based model routing
- Ordered fallback execution
- Runtime guardrails (PII redaction, injection checks, blocked terms)

This script is provider-agnostic and can run in dry-run mode for planning.
It can also execute subprocess-based adapters for existing scripts/tools.
"""

import argparse
import json
import re
import shlex
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional


DEFAULT_POLICY = {
    "profiles": {
        "fast": {"max_latency_ms": 2000, "max_cost_per_1k": 0.01, "min_quality": 0.65},
        "balanced": {"max_latency_ms": 5000, "max_cost_per_1k": 0.04, "min_quality": 0.75},
        "quality": {"max_latency_ms": 10000, "max_cost_per_1k": 0.15, "min_quality": 0.85},
    },
    "models": [
        {
            "id": "gpt-4o-mini",
            "provider": "openai",
            "quality_score": 0.8,
            "latency_ms": 1500,
            "cost_per_1k": 0.005,
        },
        {
            "id": "claude-3-5-sonnet",
            "provider": "anthropic",
            "quality_score": 0.9,
            "latency_ms": 2800,
            "cost_per_1k": 0.03,
        },
        {
            "id": "gpt-4.1",
            "provider": "openai",
            "quality_score": 0.92,
            "latency_ms": 4000,
            "cost_per_1k": 0.06,
        },
    ],
}

DEFAULT_GUARDRAILS = {
    "pii": {"enabled": True},
    "prompt_injection": {
        "enabled": True,
        "patterns": [
            r"ignore\s+all\s+previous\s+instructions",
            r"reveal\s+(system|hidden)\s+prompt",
            r"override\s+safety",
        ],
    },
    "blocked_terms": {
        "enabled": True,
        "terms": ["api key", "password dump", "private ssh key"],
    },
}


@dataclass
class ModelSpec:
    id: str
    provider: str
    quality_score: float
    latency_ms: int
    cost_per_1k: float


def load_json(path: Optional[str], fallback: Dict[str, Any]) -> Dict[str, Any]:
    if not path:
        return fallback
    return json.loads(Path(path).read_text(encoding="utf-8"))


def detect_and_redact_pii(text: str) -> Dict[str, Any]:
    redacted = text
    findings: List[str] = []

    email_pattern = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
    ssn_pattern = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
    card_pattern = re.compile(r"\b(?:\d[ -]?){13,16}\b")

    if email_pattern.search(redacted):
        redacted = email_pattern.sub("[REDACTED_EMAIL]", redacted)
        findings.append("email")
    if ssn_pattern.search(redacted):
        redacted = ssn_pattern.sub("[REDACTED_SSN]", redacted)
        findings.append("ssn")
    if card_pattern.search(redacted):
        redacted = card_pattern.sub("[REDACTED_CARD]", redacted)
        findings.append("payment_card")

    return {"text": redacted, "findings": findings}


def run_guardrails(prompt: str, cfg: Dict[str, Any]) -> Dict[str, Any]:
    violations: List[str] = []
    transformed = prompt
    pii_findings: List[str] = []

    if cfg.get("pii", {}).get("enabled", False):
        pii_result = detect_and_redact_pii(transformed)
        transformed = pii_result["text"]
        pii_findings = pii_result["findings"]

    inj_cfg = cfg.get("prompt_injection", {})
    if inj_cfg.get("enabled", False):
        for pattern in inj_cfg.get("patterns", []):
            if re.search(pattern, prompt, re.IGNORECASE):
                violations.append(f"prompt_injection:{pattern}")

    blocked_cfg = cfg.get("blocked_terms", {})
    if blocked_cfg.get("enabled", False):
        lowered = prompt.lower()
        for term in blocked_cfg.get("terms", []):
            if term.lower() in lowered:
                violations.append(f"blocked_term:{term}")

    return {
        "safe": len(violations) == 0,
        "prompt": transformed,
        "violations": violations,
        "pii_findings": pii_findings,
    }


def select_candidates(
    profile: str,
    policy: Dict[str, Any],
    task_type: str,
    provider_allowlist: Optional[List[str]],
) -> List[ModelSpec]:
    _ = task_type  # Reserved for future task-level policy tuning.
    profile_cfg = policy["profiles"][profile]

    models = []
    for raw in policy["models"]:
        spec = ModelSpec(**raw)
        if provider_allowlist and spec.provider not in provider_allowlist:
            continue
        if spec.latency_ms > profile_cfg["max_latency_ms"]:
            continue
        if spec.cost_per_1k > profile_cfg["max_cost_per_1k"]:
            continue
        if spec.quality_score < profile_cfg["min_quality"]:
            continue
        models.append(spec)

    models.sort(key=lambda m: (-m.quality_score, m.latency_ms, m.cost_per_1k))
    return models


def execute_adapter(
    adapter_template: str,
    model: ModelSpec,
    prompt: str,
    timeout_s: int,
) -> Dict[str, Any]:
    command = (
        adapter_template.replace("{model_id}", model.id)
        .replace("{provider}", model.provider)
        .replace("{prompt}", shlex.quote(prompt))
    )
    started = time.time()
    completed = subprocess.run(
        command,
        shell=True,
        capture_output=True,
        text=True,
        timeout=timeout_s,
    )
    elapsed_ms = int((time.time() - started) * 1000)
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.strip() or completed.stdout.strip() or "adapter failed")

    return {
        "model": model.id,
        "provider": model.provider,
        "latency_ms": elapsed_ms,
        "output": completed.stdout.strip(),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Route, guard, and execute LLM requests with fallback policies."
    )
    parser.add_argument("--prompt", required=True, help="Prompt text for inference")
    parser.add_argument(
        "--profile", choices=["fast", "balanced", "quality"], default="balanced",
        help="Routing profile policy"
    )
    parser.add_argument(
        "--task-type", default="general",
        help="Task type hint (e.g. summarization, classification, coding)"
    )
    parser.add_argument(
        "--policy-json", help="Optional path to policy JSON (profiles/models)"
    )
    parser.add_argument(
        "--guardrails-json", help="Optional path to guardrails JSON policy"
    )
    parser.add_argument(
        "--provider-allowlist",
        help="Comma-separated allowed providers (e.g. openai,anthropic)",
    )
    parser.add_argument(
        "--adapter-command",
        help=(
            "Optional command template for actual execution. Supports {model_id}, "
            "{provider}, {prompt}. Example: \"python scripts/my_adapter.py "
            "--model {model_id} --prompt {prompt}\""
        ),
    )
    parser.add_argument("--fallback-limit", type=int, default=3, help="Max fallback attempts")
    parser.add_argument("--timeout-seconds", type=int, default=30, help="Adapter timeout")
    parser.add_argument("--dry-run", action="store_true", help="Plan only, do not execute")
    parser.add_argument("--output", help="Write JSON execution report")
    args = parser.parse_args()

    policy = load_json(args.policy_json, DEFAULT_POLICY)
    guardrails_cfg = load_json(args.guardrails_json, DEFAULT_GUARDRAILS)

    allowlist = None
    if args.provider_allowlist:
        allowlist = [p.strip() for p in args.provider_allowlist.split(",") if p.strip()]

    guard_result = run_guardrails(args.prompt, guardrails_cfg)
    if not guard_result["safe"]:
        report = {
            "status": "blocked",
            "reason": "guardrails_violation",
            "violations": guard_result["violations"],
            "pii_findings": guard_result["pii_findings"],
        }
        print(json.dumps(report, indent=2))
        if args.output:
            Path(args.output).write_text(json.dumps(report, indent=2), encoding="utf-8")
        return 2

    candidates = select_candidates(args.profile, policy, args.task_type, allowlist)
    if not candidates:
        report = {"status": "failed", "reason": "no_matching_models", "profile": args.profile}
        print(json.dumps(report, indent=2))
        if args.output:
            Path(args.output).write_text(json.dumps(report, indent=2), encoding="utf-8")
        return 1

    selected = candidates[: max(1, args.fallback_limit)]
    execution_log: List[Dict[str, Any]] = []

    if args.dry_run or not args.adapter_command:
        report = {
            "status": "planned",
            "profile": args.profile,
            "task_type": args.task_type,
            "sanitized_prompt": guard_result["prompt"],
            "fallback_chain": [m.__dict__ for m in selected],
            "note": "Pass --adapter-command to execute model calls.",
        }
        print(json.dumps(report, indent=2))
        if args.output:
            Path(args.output).write_text(json.dumps(report, indent=2), encoding="utf-8")
        return 0

    for candidate in selected:
        try:
            result = execute_adapter(
                adapter_template=args.adapter_command,
                model=candidate,
                prompt=guard_result["prompt"],
                timeout_s=args.timeout_seconds,
            )
            execution_log.append({"attempt": "success", **result})
            report = {
                "status": "success",
                "selected_model": candidate.id,
                "provider": candidate.provider,
                "execution": result,
                "attempts": execution_log,
            }
            print(json.dumps(report, indent=2))
            if args.output:
                Path(args.output).write_text(json.dumps(report, indent=2), encoding="utf-8")
            return 0
        except Exception as exc:  # noqa: BLE001 - keep script stdlib-only and robust.
            execution_log.append(
                {
                    "attempt": "failed",
                    "model": candidate.id,
                    "provider": candidate.provider,
                    "error": str(exc),
                }
            )

    report = {
        "status": "failed",
        "reason": "all_fallbacks_failed",
        "attempts": execution_log,
    }
    print(json.dumps(report, indent=2))
    if args.output:
        Path(args.output).write_text(json.dumps(report, indent=2), encoding="utf-8")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
