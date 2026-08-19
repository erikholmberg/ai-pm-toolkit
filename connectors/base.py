#!/usr/bin/env python3
"""
Connector base (shared)

Everything a connector needs that isn't the API call itself: config from the
environment, retrying HTTP, date/number normalization, canonical CSV writing,
and the provenance sidecar.

The split matters. A connector author should write only two things — how to
reach the source, and which source field maps to which canonical column. If
each connector also hand-rolls its own CSV writer, they drift, and the promise
that Jira and Linear produce interchangeable output quietly stops being true.

Provenance: every fetch writes `<out>.meta.json` beside the CSV, recording the
source, the query, the fetch time, and any contract warnings. `toolkit_io`'s
envelope already lets you trace a number back to the script that produced it;
this extends that backwards to the query that fed the script, which is the half
that was missing.

Usage (writing a connector):

    from base import Connector, FetchResult

    class MySource(Connector):
        name = "mysource"
        provides = {"issues"}

        @classmethod
        def add_arguments(cls, parser):
            parser.add_argument("--project", required=True)

        def fetch(self, dataset, args):
            rows = [...]                      # list of dicts, canonical keys
            return FetchResult(rows, {"project": args.project})

Requirements:
    None (stdlib only).
"""

import csv
import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence

import datasets
from _toolkit import toolkit_io

__all__ = [
    "Connector",
    "FetchResult",
    "ConnectorError",
    "MissingConfigError",
    "normalize_date",
    "normalize_number",
    "write_dataset_csv",
    "SCHEMA_VERSION",
]

SCHEMA_VERSION = 1
FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"


class ConnectorError(RuntimeError):
    """A connector could not produce data."""


class MissingConfigError(ConnectorError):
    """A required environment variable or profile entry is absent."""


@dataclass
class FetchResult:
    """Rows plus whatever the connector wants recorded about the query."""

    rows: List[Dict[str, Any]]
    query: Dict[str, Any] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)


# --------------------------------------------------------------------------
# Value normalization
#
# Downstream scripts parse dates with several different tolerant parsers, but
# none of them handle every format a source API emits. Normalizing to ISO here
# means the variance is absorbed once, in the layer that knows where the data
# came from, rather than seven times downstream.
# --------------------------------------------------------------------------

_DATE_FORMATS = (
    "%Y-%m-%dT%H:%M:%S.%f%z",
    "%Y-%m-%dT%H:%M:%S%z",
    "%Y-%m-%dT%H:%M:%S.%fZ",
    "%Y-%m-%dT%H:%M:%SZ",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d %H:%M",
    "%Y-%m-%d",
    "%d/%b/%y %I:%M %p",  # Jira CSV export (12-hour)
    "%d/%b/%Y %I:%M %p",
    "%d/%b/%y %H:%M",  # same layout, 24-hour clock
    "%d/%b/%Y %H:%M",
    "%d-%b-%Y %H:%M",
    "%m/%d/%Y %H:%M",
    "%m/%d/%Y",
    "%d/%m/%Y",
    "%b %d, %Y",
)


def normalize_date(raw: Any, *, date_only: bool = False) -> str:
    """Best-effort ISO 8601. Returns the input unchanged if unparseable.

    Unchanged rather than blank on failure: a value we can't parse is still
    evidence for whoever debugs the mapping, and `validate()` will flag it. A
    silent blank would look like a legitimately empty field.
    """
    if raw is None:
        return ""
    text = str(raw).strip()
    if not text:
        return ""
    candidate = text.replace("Z", "+0000") if text.endswith("Z") else text
    # %z rejects the colon in "+00:00" before Python 3.7 and is picky after.
    if len(candidate) > 6 and candidate[-3] == ":" and candidate[-6] in "+-":
        candidate = candidate[:-3] + candidate[-2:]
    for fmt in _DATE_FORMATS:
        try:
            parsed = datetime.strptime(candidate, fmt)
        except ValueError:
            continue
        if date_only or (
            parsed.hour == 0 and parsed.minute == 0 and parsed.second == 0
        ):
            return parsed.strftime("%Y-%m-%d")
        return parsed.strftime("%Y-%m-%dT%H:%M:%S")
    return text


def normalize_number(raw: Any) -> str:
    """Strip thousands separators and stray symbols; pass through on failure."""
    if raw is None:
        return ""
    text = str(raw).strip()
    if not text:
        return ""
    cleaned = text.replace(",", "").replace("$", "").strip()
    try:
        value = float(cleaned)
    except ValueError:
        return text
    return str(int(value)) if value.is_integer() else str(value)


def write_dataset_csv(
    rows: Sequence[Dict[str, Any]],
    spec: "datasets.Dataset",
    path: str,
) -> List[str]:
    """Write rows as canonical CSV; return column ordering warnings.

    Canonical columns come first and in contract order, so a human opening the
    file sees the shape the scripts expect. Non-canonical columns are kept and
    appended — dropping them would silently discard source data the operator
    may have deliberately requested.
    """
    canonical = spec.column_names()
    present = set()
    for row in rows:
        present.update(row.keys())

    ordered = [c for c in canonical if c in present]
    extras = sorted(c for c in present if c not in set(canonical))
    header = ordered + extras

    out = Path(path)
    if out.parent and not out.parent.exists():
        out.parent.mkdir(parents=True, exist_ok=True)

    with out.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=header, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in header})

    warnings = []
    missing = [c for c in canonical if c not in present]
    if missing:
        warnings.append(
            f"columns not provided by this source: {', '.join(missing)}"
        )
    return warnings


class Connector:
    """Base class for every source.

    Subclasses set `name` and `provides`, optionally add CLI arguments, and
    implement `fetch`. Everything else — validation, CSV layout, provenance —
    is handled here so it stays identical across sources.
    """

    name: str = ""
    provides: frozenset = frozenset()
    description: str = ""

    def __init__(self, offline: bool = False):
        self.offline = offline

    # -- to implement ------------------------------------------------------

    @classmethod
    def add_arguments(cls, parser) -> None:
        """Register connector-specific CLI flags. Override as needed."""

    def fetch(self, dataset: str, args) -> FetchResult:
        raise NotImplementedError

    # -- provided ----------------------------------------------------------

    def supports(self, dataset: str) -> bool:
        return dataset in self.provides

    def env(self, var: str, required: bool = True, default: str = "") -> str:
        """Read config from the environment.

        Deliberately the same variable names the MCP servers in mcps/ already
        document, so one credential set serves both paths.
        """
        value = os.environ.get(var, "").strip()
        if value:
            return value
        if required:
            raise MissingConfigError(
                f"{self.name}: environment variable {var} is not set. "
                f"See connectors/README.md for this source's configuration."
            )
        return default

    def get_json(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        *,
        retries: int = 3,
        timeout: int = 30,
    ) -> Any:
        """GET JSON with exponential backoff on 429/5xx.

        stdlib urllib rather than requests: the shared modules in scripts/ are
        stdlib-only, and keeping connectors dependency-free means the toolkit
        stays clone-and-run.
        """
        if self.offline:
            raise ConnectorError(
                f"{self.name}: --offline was requested but this call needs the network"
            )
        last: Optional[Exception] = None
        for attempt in range(retries):
            request = urllib.request.Request(url, headers=headers or {})
            try:
                with urllib.request.urlopen(request, timeout=timeout) as response:
                    return json.loads(response.read().decode("utf-8"))
            except urllib.error.HTTPError as exc:
                last = exc
                if exc.code not in (429, 500, 502, 503, 504):
                    raise ConnectorError(
                        f"{self.name}: HTTP {exc.code} from {url}"
                    ) from exc
            except urllib.error.URLError as exc:
                last = exc
            if attempt < retries - 1:
                time.sleep(2**attempt)
        raise ConnectorError(f"{self.name}: request failed after {retries} tries: {last}")

    def load_fixture(self, dataset: str) -> Any:
        """Read the recorded response for offline runs and tests."""
        path = FIXTURES_DIR / f"{self.name}-{dataset}.json"
        if not path.exists():
            raise ConnectorError(
                f"{self.name}: no fixture at {path}. Offline mode needs one."
            )
        with path.open(encoding="utf-8") as f:
            return json.load(f)

    def normalize_rows(
        self, rows: Iterable[Dict[str, Any]], spec: "datasets.Dataset"
    ) -> List[Dict[str, Any]]:
        """Apply per-column kind normalization to already-canonical rows."""
        kinds = {c.name: c.kind for c in spec.columns}
        out = []
        for row in rows:
            clean = {}
            for key, value in row.items():
                kind = kinds.get(key)
                if kind == "date":
                    clean[key] = normalize_date(value)
                elif kind == "number":
                    clean[key] = normalize_number(value)
                else:
                    clean[key] = "" if value is None else str(value).strip()
            out.append(clean)
        return out

    def run(self, dataset: str, args, out_path: str) -> Dict[str, Any]:
        """Fetch, validate, write CSV, write sidecar. Returns the sidecar."""
        if not self.supports(dataset):
            raise ConnectorError(
                f"{self.name} does not provide '{dataset}'. "
                f"It provides: {', '.join(sorted(self.provides)) or '(nothing)'}"
            )
        spec = datasets.get(dataset)
        result = self.fetch(dataset, args)
        rows = self.normalize_rows(result.rows, spec)

        warnings = list(result.warnings)
        warnings += spec.validate(rows)
        warnings += write_dataset_csv(rows, spec, out_path)

        # The query goes in the envelope's `inputs` slot, not in the payload —
        # storing it in both made every sidecar carry it twice.
        meta = {
            "source": self.name,
            "dataset": dataset,
            "rows": len(rows),
            "columns": spec.column_names(),
            "offline": self.offline,
            "fetched_at": datetime.now(timezone.utc)
            .astimezone()
            .isoformat(timespec="seconds"),
            "output": str(out_path),
        }
        sidecar = f"{out_path}.meta.json"
        toolkit_io.write(
            sidecar,
            meta,
            tool=f"connector:{self.name}",
            warnings=warnings or None,
            inputs=result.query or None,
        )
        meta["warnings"] = warnings
        meta["sidecar"] = sidecar
        return meta
