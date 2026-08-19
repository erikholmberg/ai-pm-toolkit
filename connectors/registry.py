#!/usr/bin/env python3
"""
Connector registry

Maps a source name to its class. Imports are lazy and failures are contained:
a connector that won't import (missing optional dep, syntax error mid-edit)
must not take down `fetch.py --list`, or the one command you'd run to find out
what still works becomes the one command that also breaks.

Adding a source: append one line to `_SOURCES`, and the CLI picks it up.

Requirements:
    None (stdlib only).
"""

import importlib
from typing import Dict, List, Optional, Tuple

__all__ = ["names", "load", "describe_all", "UnknownConnectorError"]

# name -> "module path:class name"
_SOURCES: Dict[str, str] = {
    "csvfile": "sources.csvfile:CsvFileConnector",
    "jira": "sources.jira:JiraConnector",
}


class UnknownConnectorError(KeyError):
    """Raised when a source name isn't registered."""


def names() -> List[str]:
    return sorted(_SOURCES)


def load(name: str):
    """Import and return a connector class."""
    key = (name or "").strip().lower()
    if key not in _SOURCES:
        raise UnknownConnectorError(
            f"Unknown source {name!r}. Known sources: {', '.join(names())}"
        )
    module_path, class_name = _SOURCES[key].split(":")
    module = importlib.import_module(module_path)
    return getattr(module, class_name)


def describe_all() -> List[Tuple[str, Optional[object], Optional[str]]]:
    """(name, class or None, error or None) for every registered source."""
    out = []
    for name in names():
        try:
            out.append((name, load(name), None))
        except Exception as exc:  # a broken connector shouldn't hide the rest
            out.append((name, None, f"{type(exc).__name__}: {exc}"))
    return out
