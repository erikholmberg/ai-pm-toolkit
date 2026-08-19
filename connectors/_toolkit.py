#!/usr/bin/env python3
"""
Toolkit import shim (internal)

`connectors/` sits beside `scripts/`, not inside it, so a plain
`import csv_columns` fails. Every connector module needs the same two shared
helpers, and without one place to do this each of them grows its own copy of
the same three-line sys.path dance — which then drifts.

Import from here instead:

    from _toolkit import csv_columns, toolkit_io

Requirements:
    None (stdlib only).
"""

import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"

if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import csv_columns  # noqa: E402
import toolkit_io  # noqa: E402

__all__ = ["csv_columns", "toolkit_io", "SCRIPTS_DIR"]
