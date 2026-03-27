#!/usr/bin/env python3
"""
Model / System Card Builder

Generate structured **model cards** (ML transparency) or **system cards**
(LLM applications: product context, tools, guardrails) as Markdown and/or YAML.

Aligns with sections in `prompts/ai-ml/model-card-generator.prompt.md`. Use JSON
for full control; use CLI flags for quick one-off cards.

Usage:
    # Quick model card (Markdown to stdout)
    python model-system-card-builder.py \\
        --name "intent-classifier-v2" \\
        --version "2.1.0" \\
        --owner "ML Platform" \\
        --purpose "Route support tickets to the right queue." \\
        --intended-use "Online inference on ticket subject + body" \\
        --out-of-scope "Medical or legal advice; languages outside en/es"

    # System card (LLM + RAG product)
    python model-system-card-builder.py \\
        --kind system \\
        --name "Support Copilot" \\
        --version "1.4.0" \\
        --base-model "gpt-4o" \\
        --system-prompt-summary "Helpful support assistant; cites KB only." \\
        --retrieval "Pinecone index support_kb_v3, top-k 8"

    # From JSON + write both formats
    python model-system-card-builder.py \\
        --json scripts/samples/sample-model-system-card.json \\
        --output-dir docs/cards \\
        --basename support-copilot

    # YAML only
    python model-system-card-builder.py --json card.json --format yaml --output card.yaml

JSON schema (see sample file):
    Top-level keys: kind, name, version, model_type, owner, last_updated,
    purpose, intended_use, out_of_scope, training_data, evaluation,
    ethical, limitations, failure_modes, deployment, maintenance,
    contact, system (for kind=system).

Requirements:
    None (stdlib only).
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Optional, Union


# ---------------------------------------------------------------------------
# YAML subset emitter (no PyYAML dependency)
# ---------------------------------------------------------------------------


def _yaml_escape(s: str) -> str:
    if s == "":
        return '""'
    if any(ch in s for ch in "\n\r\"") or s.strip() != s:
        return json.dumps(s)
    if any(ch in s for ch in ": #[]{},&*!|>'\"%@`"):
        return json.dumps(s)
    return s


def _yaml_value(value: Any, indent: int) -> str:
    pad = " " * indent
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, str):
        return _yaml_escape(value)
    if isinstance(value, list):
        if not value:
            return "[]"
        lines = []
        for item in value:
            if isinstance(item, (dict, list)):
                lines.append(f"{pad}- {_yaml_dump_block(item, indent + 2).lstrip()}")
            else:
                lines.append(f"{pad}- {_yaml_value(item, indent)}")
        return "\n".join(lines)
    if isinstance(value, dict):
        return _yaml_dump_block(value, indent)
    return _yaml_escape(str(value))


def _yaml_dump_block(obj: Any, indent: int) -> str:
    pad = " " * indent
    if isinstance(obj, dict):
        parts: List[str] = []
        for k, v in obj.items():
            key = str(k)
            if isinstance(v, (dict, list)) and v not in ([], {}):
                if isinstance(v, dict) and v:
                    parts.append(f"{pad}{key}:")
                    parts.append(_yaml_dump_block(v, indent + 2))
                elif isinstance(v, list) and v:
                    parts.append(f"{pad}{key}:")
                    for item in v:
                        if isinstance(item, dict):
                            parts.append(f"{pad}  -")
                            parts.append(_yaml_dump_block(item, indent + 4))
                        else:
                            parts.append(f"{pad}  - {_yaml_value(item, indent)}")
                else:
                    parts.append(f"{pad}{key}: {_yaml_value(v, indent)}")
            else:
                parts.append(f"{pad}{key}: {_yaml_value(v, indent)}")
        return "\n".join(parts)
    return f"{pad}{_yaml_value(obj, indent)}"


def to_yaml(data: Dict[str, Any]) -> str:
    return _yaml_dump_block(data, 0) + "\n"


# ---------------------------------------------------------------------------
# Card schema & defaults
# ---------------------------------------------------------------------------


def empty_card() -> Dict[str, Any]:
    return {
        "kind": "model",
        "name": "",
        "version": "",
        "model_type": "",
        "owner": "",
        "last_updated": date.today().isoformat(),
        "card_version": "1.0",
        "purpose": "",
        "intended_use": [],
        "out_of_scope": [],
        "training_data": {
            "summary": "",
            "datasets": [],
            "date_range": "",
            "collection": "",
            "preprocessing": "",
            "gaps": "",
        },
        "evaluation": {
            "held_out": "",
            "benchmarks": "",
            "representativeness": "",
            "metrics": [],
            "subgroups": [],
            "confidence_thresholds": "",
        },
        "ethical": {
            "potential_harms": [],
            "bias_analysis": "",
            "mitigation": [],
            "sensitive_use_cases": [],
        },
        "limitations": [],
        "failure_modes": [],
        "deployment": {
            "infrastructure": "",
            "latency_p50_ms": None,
            "latency_p99_ms": None,
            "throughput_rps": None,
            "monitoring": [],
            "retraining_schedule": "",
        },
        "maintenance": {
            "feedback_channel": "",
            "update_history": "",
            "deprecation_plan": "",
        },
        "contact": {
            "owner": "",
            "issues": "",
            "documentation": "",
        },
        "system": {
            "base_model": "",
            "system_prompt_summary": "",
            "tools": [],
            "retrieval": "",
            "data_sources": [],
        },
        "examples": [],
    }


def _ensure_list(val: Union[str, List[str], None]) -> List[str]:
    if val is None:
        return []
    if isinstance(val, str):
        return [val.strip()] if val.strip() else []
    return [str(x).strip() for x in val if str(x).strip()]


def merge_json(base: Dict[str, Any], path: str) -> Dict[str, Any]:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(raw, dict) and "card" in raw:
        raw = raw["card"]
    if not isinstance(raw, dict):
        raise ValueError("JSON root must be an object")

    def deep_merge(a: Dict[str, Any], b: Dict[str, Any]) -> Dict[str, Any]:
        out = dict(a)
        for k, v in b.items():
            if k in out and isinstance(out[k], dict) and isinstance(v, dict):
                out[k] = deep_merge(out[k], v)
            else:
                out[k] = v
        return out

    return deep_merge(base, raw)


def parse_metric_arg(s: str) -> Dict[str, str]:
    """Parse name:value, name:value:notes, or name=value."""
    s = s.strip()
    if "=" in s and not s.startswith("="):
        left, right = s.split("=", 1)
        return {"name": left.strip(), "value": right.strip(), "notes": ""}
    parts = s.split(":", 2)
    if len(parts) == 1:
        return {"name": parts[0], "value": "", "notes": ""}
    if len(parts) == 2:
        return {"name": parts[0].strip(), "value": parts[1].strip(), "notes": ""}
    return {"name": parts[0].strip(), "value": parts[1].strip(), "notes": parts[2].strip()}


def apply_cli(args: argparse.Namespace, card: Dict[str, Any]) -> None:
    if args.kind:
        card["kind"] = args.kind
    if args.name:
        card["name"] = args.name
    if args.version:
        card["version"] = args.version
    if args.model_type:
        card["model_type"] = args.model_type
    if args.owner:
        card["owner"] = args.owner
    if args.last_updated:
        card["last_updated"] = args.last_updated
    if args.purpose:
        card["purpose"] = args.purpose
    if args.intended_use:
        card["intended_use"] = _ensure_list(args.intended_use)
    if args.out_of_scope:
        card["out_of_scope"] = _ensure_list(args.out_of_scope)
    if args.limitation:
        card["limitations"] = list(card.get("limitations") or []) + _ensure_list(args.limitation)
    if args.failure_mode:
        card["failure_modes"] = list(card.get("failure_modes") or []) + _ensure_list(args.failure_mode)
    if args.metric:
        metrics = list(card["evaluation"].get("metrics") or [])
        for m in args.metric:
            metrics.append(parse_metric_arg(m))
        card["evaluation"]["metrics"] = metrics

    if args.base_model:
        card["system"]["base_model"] = args.base_model
    if args.system_prompt_summary:
        card["system"]["system_prompt_summary"] = args.system_prompt_summary
    if args.retrieval:
        card["system"]["retrieval"] = args.retrieval
    if args.tool:
        card["system"]["tools"] = list(card["system"].get("tools") or []) + _ensure_list(args.tool)

    if args.training_summary:
        card["training_data"]["summary"] = args.training_summary
    if args.infrastructure:
        card["deployment"]["infrastructure"] = args.infrastructure
    if args.feedback_channel:
        card["maintenance"]["feedback_channel"] = args.feedback_channel
    if args.contact_issues:
        card["contact"]["issues"] = args.contact_issues
    if args.documentation:
        card["contact"]["documentation"] = args.documentation


# ---------------------------------------------------------------------------
# Markdown rendering
# ---------------------------------------------------------------------------


def _bullets(items: List[str]) -> str:
    if not items:
        return "_None specified._\n"
    return "\n".join(f"- {x}" for x in items) + "\n"


def _metrics_table(metrics: List[Dict[str, Any]]) -> str:
    if not metrics:
        return "| Metric | Value | Notes |\n|--------|-------|-------|\n| _TBD_ | | |\n"
    lines = ["| Metric | Value | Notes |", "|--------|-------|-------|"]
    for m in metrics:
        name = m.get("name", "")
        val = m.get("value", "")
        notes = m.get("notes", "")
        lines.append(f"| {name} | {val} | {notes} |")
    return "\n".join(lines) + "\n"


def render_markdown(card: Dict[str, Any]) -> str:
    kind = card.get("kind", "model")
    title = "System card" if kind == "system" else "Model card"
    name = card.get("name") or "Untitled"
    version = card.get("version") or "—"
    lines: List[str] = [
        f"# {title}: {name}",
        "",
        f"- **Version:** {version}",
        f"- **Type:** {card.get('model_type') or '—'}",
        f"- **Owner:** {card.get('owner') or '—'}",
        f"- **Last updated:** {card.get('last_updated') or '—'}",
        f"- **Card schema:** {card.get('card_version', '1.0')}",
        "",
        "## 1. Overview",
        "",
        "### Purpose",
        "",
        (card.get("purpose") or "_Describe the problem this model or system solves._") + "\n",
        "### Intended use",
        "",
        _bullets(_ensure_list(card.get("intended_use"))),
        "### Out of scope",
        "",
        _bullets(_ensure_list(card.get("out_of_scope"))),
    ]

    n = 2
    if kind == "system":
        sys = card.get("system") or {}
        lines += [
            f"## {n}. System context (LLM application)",
            "",
            f"- **Base model / API:** {sys.get('base_model') or '—'}",
            f"- **System prompt / behavior (summary):** {sys.get('system_prompt_summary') or '—'}",
            f"- **Retrieval / tools:** {sys.get('retrieval') or '—'}",
        ]
        tools = _ensure_list(sys.get("tools"))
        if tools:
            lines += ["", "**Tools:**", "", _bullets(tools)]
        ds = _ensure_list(sys.get("data_sources"))
        if ds:
            lines += ["", "**Data sources:**", "", _bullets(ds)]
        lines.append("")
        n = 3

    td = card.get("training_data") or {}
    train_title = "## 2. Training & data" if kind == "model" else f"## {n}. Training & data (if applicable)"
    lines += [
        train_title,
        "",
        f"- **Summary:** {td.get('summary') or '—'}",
        f"- **Dataset(s):** {', '.join(_ensure_list(td.get('datasets'))) or '—'}",
        f"- **Date range:** {td.get('date_range') or '—'}",
        f"- **Collection:** {td.get('collection') or '—'}",
        f"- **Preprocessing:** {td.get('preprocessing') or '—'}",
        f"- **Known gaps:** {td.get('gaps') or '—'}",
        "",
    ]

    ev = card.get("evaluation") or {}
    eval_num = n + 1
    lines += [
        f"## {eval_num}. Evaluation",
        "",
        f"- **Held-out / eval set:** {ev.get('held_out') or '—'}",
        f"- **Benchmarks:** {ev.get('benchmarks') or '—'}",
        f"- **Representativeness:** {ev.get('representativeness') or '—'}",
        f"- **Confidence thresholds:** {ev.get('confidence_thresholds') or '—'}",
        "",
        "### Performance metrics",
        "",
        _metrics_table(ev.get("metrics") or []),
    ]

    sub = ev.get("subgroups") or []
    if sub:
        lines += ["### Performance by segment", "", _metrics_table(sub)]
    lines.append("")

    eth = card.get("ethical") or {}
    lines += [
        f"## {eval_num + 1}. Ethical considerations & safety",
        "",
        "### Potential harms",
        "",
        _bullets(_ensure_list(eth.get("potential_harms"))),
        f"**Bias analysis:** {eth.get('bias_analysis') or '—'}\n",
        "### Mitigation",
        "",
        _bullets(_ensure_list(eth.get("mitigation"))),
        "### Sensitive use cases",
        "",
        _bullets(_ensure_list(eth.get("sensitive_use_cases"))),
    ]

    lines += [
        f"## {eval_num + 2}. Limitations",
        "",
        _bullets(_ensure_list(card.get("limitations"))),
        f"## {eval_num + 3}. Failure modes",
        "",
        _bullets(_ensure_list(card.get("failure_modes"))),
    ]

    dep = card.get("deployment") or {}
    lines += [
        f"## {eval_num + 4}. Deployment & operations",
        "",
        f"- **Infrastructure:** {dep.get('infrastructure') or '—'}",
        f"- **Latency p50 (ms):** {dep.get('latency_p50_ms') if dep.get('latency_p50_ms') is not None else '—'}",
        f"- **Latency p99 (ms):** {dep.get('latency_p99_ms') if dep.get('latency_p99_ms') is not None else '—'}",
        f"- **Throughput (RPS):** {dep.get('throughput_rps') if dep.get('throughput_rps') is not None else '—'}",
        f"- **Retraining / revalidation:** {dep.get('retraining_schedule') or '—'}",
        "",
        "### Monitoring",
        "",
        _bullets(_ensure_list(dep.get("monitoring"))),
    ]

    maint = card.get("maintenance") or {}
    lines += [
        f"## {eval_num + 5}. Maintenance",
        "",
        f"- **Feedback channel:** {maint.get('feedback_channel') or '—'}",
        f"- **Update history:** {maint.get('update_history') or '—'}",
        f"- **Deprecation plan:** {maint.get('deprecation_plan') or '—'}",
        "",
    ]

    ct = card.get("contact") or {}
    lines += [
        f"## {eval_num + 6}. Contact",
        "",
        f"- **Owner:** {ct.get('owner') or card.get('owner') or '—'}",
        f"- **Issues / incidents:** {ct.get('issues') or '—'}",
        f"- **Documentation:** {ct.get('documentation') or '—'}",
        "",
    ]

    ex = card.get("examples") or []
    if ex:
        lines += ["## Appendix: Examples", ""]
        for i, e in enumerate(ex, 1):
            if isinstance(e, dict):
                inp = e.get("input", "")
                out = e.get("output", "")
                lines.append(f"### Example {i}\n\n**Input:** {inp}\n\n**Output:** {out}\n")
            else:
                lines.append(f"- {e}\n")

    lines += [
        "---",
        "",
        "_Generated by `scripts/model-system-card-builder.py`. Review and edit before publishing._",
        "",
    ]
    return "\n".join(lines)


def render_front_matter_yaml(card: Dict[str, Any]) -> str:
    meta = {
        "kind": card.get("kind"),
        "name": card.get("name"),
        "version": card.get("version"),
        "owner": card.get("owner"),
        "last_updated": card.get("last_updated"),
        "card_version": card.get("card_version"),
    }
    return "---\n" + to_yaml(meta).strip() + "\n---\n\n"


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build Markdown and/or YAML model or system cards from CLI or JSON.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--json", "-j", dest="json_path", help="Path to JSON card definition")
    parser.add_argument("--kind", choices=["model", "system"], help="Card kind")
    parser.add_argument("--name", help="Model or system name")
    parser.add_argument("--version", help="Version string")
    parser.add_argument("--model-type", dest="model_type", help="e.g. Classification, LLM, RAG system")
    parser.add_argument("--owner", help="Team or owner")
    parser.add_argument("--last-updated", help="ISO date (default: today)")
    parser.add_argument("--purpose", help="What problem this solves")
    parser.add_argument("--intended-use", action="append", help="Repeatable intended use bullet")
    parser.add_argument("--out-of-scope", action="append", help="Repeatable out-of-scope bullet")
    parser.add_argument("--limitation", action="append", help="Repeatable limitation")
    parser.add_argument("--failure-mode", action="append", help="Repeatable failure mode")
    parser.add_argument(
        "--metric",
        action="append",
        help='Metric as name:value or "Name: value: notes"',
    )
    parser.add_argument("--training-summary", help="Training data summary paragraph")
    parser.add_argument("--infrastructure", help="Deployment infrastructure")
    parser.add_argument("--feedback-channel", help="How to report issues")
    parser.add_argument("--contact-issues", help="Link or channel for incidents")
    parser.add_argument("--documentation", help="Link to docs")

    parser.add_argument("--base-model", help="(system) Base model or API id")
    parser.add_argument("--system-prompt-summary", help="(system) Short behavior summary")
    parser.add_argument("--retrieval", help="(system) Retrieval / tools description")
    parser.add_argument("--tool", action="append", help="(system) Repeatable tool name")

    parser.add_argument(
        "--format",
        choices=["markdown", "yaml", "both", "md-yaml"],
        default="markdown",
        help="markdown: .md | yaml: full card as YAML | both: .md + .yaml (needs --output or --output-dir) | "
        "md-yaml: YAML front matter + Markdown body",
    )
    parser.add_argument("--output", "-o", help="Single output file (for format markdown or yaml)")
    parser.add_argument(
        "--output-dir",
        help="Write basename.md and basename.yaml when --basename is set",
    )
    parser.add_argument("--basename", help="Filename stem for --output-dir")

    args = parser.parse_args()

    card = empty_card()
    if args.json_path:
        card = merge_json(card, args.json_path)
    apply_cli(args, card)

    if not (card.get("name") or "").strip():
        print("Error: set `name` via --name or JSON.", file=sys.stderr)
        return 1

    md_body = render_markdown(card)
    yaml_full = to_yaml(card)

    if args.format == "yaml":
        out = yaml_full
        path = args.output
        if path:
            Path(path).write_text(out, encoding="utf-8")
            print(f"Wrote {path}", file=sys.stderr)
        else:
            print(out, end="")
        return 0

    if args.format == "markdown":
        out = md_body
        path = args.output
        if path:
            Path(path).write_text(out, encoding="utf-8")
            print(f"Wrote {path}", file=sys.stderr)
        else:
            print(out, end="")
        return 0

    if args.format == "md-yaml":
        out = render_front_matter_yaml(card) + md_body
        path = args.output
        if path:
            Path(path).write_text(out, encoding="utf-8")
            print(f"Wrote {path}", file=sys.stderr)
        else:
            print(out, end="")
        return 0

    # both
    if args.output_dir and args.basename:
        out_dir = Path(args.output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        md_path = out_dir / f"{args.basename}.md"
        yml_path = out_dir / f"{args.basename}.yaml"
        md_path.write_text(md_body, encoding="utf-8")
        yml_path.write_text(yaml_full, encoding="utf-8")
        print(f"Wrote {md_path} and {yml_path}", file=sys.stderr)
        return 0

    if args.output:
        base = Path(args.output)
        stem = base.stem if base.suffix else str(base)
        parent = base.parent if base.suffix else Path(".")
        md_path = parent / f"{stem}.md"
        yml_path = parent / f"{stem}.yaml"
        md_path.write_text(md_body, encoding="utf-8")
        yml_path.write_text(yaml_full, encoding="utf-8")
        print(f"Wrote {md_path} and {yml_path}", file=sys.stderr)
        return 0

    print(
        "Error: --format both requires --output PATH (writes PATH.md and PATH.yaml) "
        "or --output-dir DIR --basename STEM.",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
