#!/usr/bin/env python3
"""
Toolkit I/O (shared)

A common result envelope for every script's `--output` JSON.

Before this, 80+ scripts each emitted a bare, bespoke JSON blob and not one of
them could read another's — so every "chain these scripts together" workflow was
really a human retyping numbers between steps. The envelope fixes the read side:
`load()` accepts any toolkit output (enveloped or legacy bare JSON) and hands
back the payload, so one script can consume another's results.

It also records provenance. A number in a deck six weeks from now can be traced
back to the script and the moment that produced it.

Envelope shape:
    {
      "toolkit_schema": 1,
      "tool": "sla-uptime-calculator",
      "generated_at": "2026-08-15T09:30:00",
      "warnings": ["..."],          # omitted when empty
      "result": { ...the script's own payload, unchanged... }
    }

Usage (producing):
    import toolkit_io

    with open(args.output, "w") as f:
        json.dump(toolkit_io.envelope(report, TOOL), f, indent=2)

Usage (consuming):
    payload = toolkit_io.load("uptime.json")      # unwrapped, either shape
    meta = toolkit_io.metadata("uptime.json")     # tool, generated_at, warnings

Requirements:
    None (stdlib only).
"""

import json
from datetime import datetime
from typing import Any, Dict, List, Optional

__all__ = ["SCHEMA_VERSION", "envelope", "load", "metadata", "is_enveloped", "write"]

SCHEMA_VERSION = 1


def envelope(
    result: Any,
    tool: str,
    warnings: Optional[List[str]] = None,
    inputs: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Wrap a script's payload in the shared envelope.

    `result` is passed through untouched, so a consumer that already knew the
    script's output shape keeps working after unwrapping.
    """
    env: Dict[str, Any] = {
        "toolkit_schema": SCHEMA_VERSION,
        "tool": tool,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
    }
    if inputs:
        env["inputs"] = inputs
    if warnings:
        env["warnings"] = list(warnings)
    env["result"] = result
    return env


def is_enveloped(obj: Any) -> bool:
    """True if `obj` looks like a toolkit envelope rather than a bare payload."""
    return (
        isinstance(obj, dict)
        and "toolkit_schema" in obj
        and "result" in obj
    )


def load(path: str) -> Any:
    """Read a toolkit JSON file and return the payload.

    Accepts both the envelope and legacy bare output, so consumers don't have to
    care which era produced the file.
    """
    with open(path) as f:
        obj = json.load(f)
    return obj["result"] if is_enveloped(obj) else obj


def metadata(path: str) -> Dict[str, Any]:
    """Provenance for a toolkit JSON file.

    Legacy bare output has none, which is reported honestly rather than guessed:
    `tool` and `generated_at` come back as None.
    """
    with open(path) as f:
        obj = json.load(f)
    if not is_enveloped(obj):
        return {
            "toolkit_schema": None,
            "tool": None,
            "generated_at": None,
            "warnings": [],
            "legacy": True,
        }
    return {
        "toolkit_schema": obj.get("toolkit_schema"),
        "tool": obj.get("tool"),
        "generated_at": obj.get("generated_at"),
        "inputs": obj.get("inputs", {}),
        "warnings": obj.get("warnings", []),
        "legacy": False,
    }


def write(
    path: str,
    result: Any,
    tool: str,
    warnings: Optional[List[str]] = None,
    inputs: Optional[Dict[str, Any]] = None,
    default=None,
) -> None:
    """Write an enveloped result to `path`."""
    with open(path, "w") as f:
        json.dump(envelope(result, tool, warnings, inputs), f, indent=2, default=default)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Inspect a toolkit --output JSON file (provenance + payload keys).",
        epilog="Example: toolkit_io.py uptime.json",
    )
    parser.add_argument("file", nargs="?", help="Toolkit JSON output file to inspect")
    args = parser.parse_args()

    if not args.file:
        parser.print_help()
        raise SystemExit(0)

    meta = metadata(args.file)
    if meta["legacy"]:
        print(f"{args.file}: legacy bare output (no provenance recorded)")
    else:
        print(f"{args.file}:")
        print(f"  tool:         {meta['tool']}")
        print(f"  generated_at: {meta['generated_at']}")
        print(f"  schema:       v{meta['toolkit_schema']}")
        for w in meta["warnings"]:
            print(f"  warning:      {w}")
    payload = load(args.file)
    keys = list(payload) if isinstance(payload, dict) else f"<{type(payload).__name__}>"
    print(f"  result keys:  {keys}")
