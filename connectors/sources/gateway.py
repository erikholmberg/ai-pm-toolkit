#!/usr/bin/env python3
"""
gateway connector — pull real LLM spend from an AI gateway.

Every cost script in this toolkit used to run on assumptions you typed in.
This is where the actuals come from: token counts and dollars per day, per
model, per feature, rolled up into the `llm_usage` contract that
scripts/llm-usage-summary.py reads.

Providers:

    litellm     LiteLLM proxy — GET {LITELLM_BASE_URL}/spend/logs
    openrouter  OpenRouter    — GET https://openrouter.ai/api/v1/activity
    file        A JSON or CSV export you already have (no network, no key)

`file` exists because it always works. The two API providers are written
against documented endpoints but their exact response shapes drift between
releases, so the mapping layer is deliberately tolerant: every field is looked
up through a list of alternative names, unknown keys are ignored rather than
fatal, and `--raw` dumps what actually came back so a mismatch is a five-minute
fix rather than a rewrite.

Rollup: gateways return per-request logs; the contract wants one row per
(date, model, feature). This aggregates before writing, so a month of traffic
becomes a few hundred rows instead of millions.

Usage:
    # LiteLLM proxy
    export LITELLM_BASE_URL=https://llm.internal.company.com
    export LITELLM_API_KEY=sk-...
    python fetch.py gateway llm_usage --provider litellm --days 30 --out usage.csv

    # OpenRouter
    export OPENROUTER_API_KEY=sk-or-...
    python fetch.py gateway llm_usage --provider openrouter --days 30 --out usage.csv

    # An export you already have
    python fetch.py gateway llm_usage --provider file --input export.json --out usage.csv

    # Replay the fixture, no network
    python fetch.py gateway llm_usage --offline --out usage.csv

Then:
    python scripts/llm-usage-summary.py --csv usage.csv

Requirements:
    None (stdlib only).
"""

import csv
import json
import urllib.parse
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

import datasets
from base import Connector, ConnectorError, FetchResult, normalize_date

# Field name candidates, most specific first. Gateways disagree on all of these
# and several change spelling between versions, so nothing here is a single
# hardcoded key.
FIELD_ALIASES: Dict[str, tuple] = {
    "date": ("date", "day", "startTime", "start_time", "created_at", "timestamp"),
    "model": ("model", "model_name", "model_permaslug", "model_id", "engine"),
    "feature": (
        "feature",
        "tag",
        "app",
        "project",
        "key_alias",
        "api_key_alias",
        "user",
        "end_user",
        "team_id",
    ),
    "provider": ("provider", "provider_name", "custom_llm_provider", "vendor"),
    "requests": ("requests", "request_count", "calls", "count", "num_requests"),
    "input_tokens": ("prompt_tokens", "input_tokens", "tokens_in", "prompt"),
    "output_tokens": ("completion_tokens", "output_tokens", "tokens_out"),
    "cached_input_tokens": (
        "cache_read_input_tokens",
        "cached_input_tokens",
        "cache_read_tokens",
        "cached_tokens",
        "prompt_cache_read_tokens",
    ),
    "cache_write_tokens": (
        "cache_creation_input_tokens",
        "cache_write_tokens",
        "cache_creation_tokens",
        "prompt_cache_write_tokens",
    ),
    "reasoning_tokens": ("reasoning_tokens", "thinking_tokens"),
    "cost_usd": ("spend", "cost", "usage", "cost_usd", "total_cost", "amount"),
}

SUMMABLE = (
    "requests",
    "input_tokens",
    "output_tokens",
    "cached_input_tokens",
    "cache_write_tokens",
    "reasoning_tokens",
    "cost_usd",
)


class GatewayConnector(Connector):
    name = "gateway"
    provides = frozenset({"llm_usage"})
    description = "Pull real LLM spend from LiteLLM, OpenRouter, or an export."

    @classmethod
    def add_arguments(cls, parser) -> None:
        parser.add_argument(
            "--provider",
            default="file",
            choices=["litellm", "openrouter", "file"],
            help="Where usage comes from (default: file)",
        )
        parser.add_argument(
            "--input", help="For --provider file: a JSON or CSV export path"
        )
        parser.add_argument(
            "--days",
            type=int,
            default=30,
            help="How many days back to request (default: 30)",
        )
        parser.add_argument("--start", metavar="YYYY-MM-DD", help="Explicit start date")
        parser.add_argument("--end", metavar="YYYY-MM-DD", help="Explicit end date")
        parser.add_argument(
            "--no-rollup",
            action="store_true",
            help="Emit one row per source record instead of per (date, model, feature)",
        )
        parser.add_argument(
            "--raw",
            metavar="PATH",
            help="Also write the untouched provider response here, for debugging",
        )

    # -- window ------------------------------------------------------------

    def _window(self, args) -> tuple:
        end = (
            datetime.strptime(args.end, "%Y-%m-%d")
            if args.end
            else datetime.now()
        )
        start = (
            datetime.strptime(args.start, "%Y-%m-%d")
            if args.start
            else end - timedelta(days=args.days)
        )
        if start > end:
            raise ConnectorError(f"{self.name}: --start is after --end")
        return start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")

    # -- providers ---------------------------------------------------------

    def _from_litellm(self, args, warnings: List[str]) -> List[Dict[str, Any]]:
        base = self.env("LITELLM_BASE_URL").rstrip("/")
        key = self.env("LITELLM_API_KEY")
        start, end = self._window(args)
        query = urllib.parse.urlencode({"start_date": start, "end_date": end})
        payload = self.get_json(
            f"{base}/spend/logs?{query}",
            {"Authorization": f"Bearer {key}", "Accept": "application/json"},
        )
        return _as_records(payload, warnings, self.name)

    def _from_openrouter(self, args, warnings: List[str]) -> List[Dict[str, Any]]:
        key = self.env("OPENROUTER_API_KEY")
        payload = self.get_json(
            "https://openrouter.ai/api/v1/activity",
            {"Authorization": f"Bearer {key}", "Accept": "application/json"},
        )
        records = _as_records(payload, warnings, self.name)
        # The activity endpoint returns a fixed recent window rather than an
        # arbitrary range, so honour --days locally instead of pretending the
        # request was filtered server-side.
        start, _ = self._window(args)
        kept = [r for r in records if str(r.get("date", ""))[:10] >= start]
        if len(kept) < len(records):
            warnings.append(
                f"openrouter returns a fixed activity window; filtered "
                f"{len(records) - len(kept)} record(s) older than {start} locally"
            )
        return kept or records

    def _from_file(self, args, warnings: List[str]) -> List[Dict[str, Any]]:
        if not args.input:
            raise ConnectorError(
                f"{self.name}: --provider file needs --input pointing at a "
                f"JSON or CSV export"
            )
        path = Path(args.input)
        if not path.exists():
            raise ConnectorError(f"{self.name}: no such file: {path}")
        if path.suffix.lower() == ".csv":
            with path.open(newline="", encoding="utf-8-sig") as f:
                return [dict(row) for row in csv.DictReader(f)]
        with path.open(encoding="utf-8") as f:
            return _as_records(json.load(f), warnings, self.name)

    # -- main --------------------------------------------------------------

    def fetch(self, dataset: str, args) -> FetchResult:
        warnings: List[str] = []

        # Validate the window even offline: someone testing flags against the
        # fixture should get the same error a live run would give, not silence.
        window = self._window(args)

        if self.offline:
            records = _as_records(self.load_fixture("llm_usage"), warnings, self.name)
            provider = "(fixture)"
        else:
            provider = args.provider
            records = {
                "litellm": self._from_litellm,
                "openrouter": self._from_openrouter,
                "file": self._from_file,
            }[provider](args, warnings)

        if args.raw:
            Path(args.raw).write_text(
                json.dumps(records, indent=2, default=str), encoding="utf-8"
            )

        if not records:
            warnings.append(
                "provider returned no records for this window — check the date "
                "range, or run with --raw to see the response"
            )

        rows = [_map_record(r) for r in records]
        rows = [r for r in rows if r.get("date") and r.get("model")]
        dropped = len(records) - len(rows)
        if dropped:
            # Loud, because a mapping miss looks exactly like "quiet month".
            warnings.append(
                f"{dropped} of {len(records)} record(s) had no recognizable date "
                f"or model field and were skipped; --raw shows their shape"
            )

        unpriced = sum(1 for r in rows if not r.get("cost_usd"))
        if rows and unpriced == len(rows):
            warnings.append(
                "no cost field found on any record — spend will read as $0. "
                "llm-usage-summary.py can still derive cost from token counts."
            )

        if args.no_rollup:
            rows = [{k: ("" if v is None else v) for k, v in r.items()} for r in rows]
        else:
            rows = _rollup(rows)

        query = {
            "provider": provider,
            "window": None if self.offline else list(window),
            "records_in": len(records),
            "rows_out": len(rows),
            "rolled_up": not args.no_rollup,
        }
        return FetchResult(rows, query, warnings)


# --------------------------------------------------------------------------
# Shape handling
# --------------------------------------------------------------------------


def _as_records(payload: Any, warnings: List[str], source: str) -> List[Dict[str, Any]]:
    """Find the list of records inside whatever envelope the provider used.

    Gateways variously return a bare array, `{"data": [...]}`, or
    `{"results": [...]}`, and the wrapper key changes between versions. Probing
    for the list beats hardcoding one key and returning zero rows when it moves.
    """
    if isinstance(payload, list):
        return [r for r in payload if isinstance(r, dict)]
    if isinstance(payload, dict):
        for key in ("data", "results", "logs", "items", "records", "spend", "activity"):
            value = payload.get(key)
            if isinstance(value, list):
                return [r for r in value if isinstance(r, dict)]
        # Single record rather than a collection.
        if any(k in payload for k in ("model", "spend", "prompt_tokens")):
            return [payload]
        warnings.append(
            f"{source}: response had no recognizable record list "
            f"(keys: {', '.join(list(payload)[:8])})"
        )
        return []
    warnings.append(f"{source}: unexpected response type {type(payload).__name__}")
    return []


def _dig(record: Dict[str, Any], names: Iterable[str]) -> Any:
    """First present value among `names`, looking one level into nested dicts.

    LiteLLM nests token counts under `usage` or `metadata` depending on
    version and call type, so a flat lookup alone misses them.
    """
    for name in names:
        if name in record and record[name] not in (None, ""):
            return record[name]
    for container in ("usage", "metadata", "tokens", "details"):
        nested = record.get(container)
        if isinstance(nested, dict):
            for name in names:
                if name in nested and nested[name] not in (None, ""):
                    return nested[name]
    return None


def _number(value: Any) -> float:
    if value is None:
        return 0.0
    try:
        return float(str(value).replace(",", "").replace("$", "").strip())
    except ValueError:
        return 0.0


def _map_record(record: Dict[str, Any]) -> Dict[str, Any]:
    """One source record -> one canonical row.

    Absent numeric fields stay None rather than becoming 0.0. The distinction
    is load-bearing: 0 means the provider reported zero, blank means it never
    reported the field at all. Collapsing the two makes a gateway that doesn't
    break out cache tokens look like one with a 0% cache hit rate.
    """
    row: Dict[str, Any] = {}
    raw_date = _dig(record, FIELD_ALIASES["date"])
    # Date only: the contract is a daily rollup, and keeping the time component
    # would split one day into hundreds of groups.
    row["date"] = normalize_date(raw_date, date_only=True) if raw_date else ""
    for key in ("model", "feature", "provider"):
        value = _dig(record, FIELD_ALIASES[key])
        row[key] = str(value).strip() if value is not None else ""
    for key in SUMMABLE:
        found = _dig(record, FIELD_ALIASES[key])
        row[key] = None if found is None else _number(found)
    # A per-request log line has no request count; it *is* one request.
    if not row["requests"]:
        row["requests"] = 1.0
    return row


def _rollup(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Collapse to one row per (date, model, feature)."""
    grouped: Dict[tuple, Dict[str, Any]] = {}
    for row in rows:
        key = (row["date"], row["model"], row.get("feature", ""))
        if key not in grouped:
            grouped[key] = {
                "date": row["date"],
                "model": row["model"],
                "feature": row.get("feature", ""),
                "provider": row.get("provider", ""),
                **{k: None for k in SUMMABLE},
            }
        target = grouped[key]
        for field in SUMMABLE:
            value = row.get(field)
            if value is None:
                continue
            target[field] = (target[field] or 0.0) + value
        if not target["provider"] and row.get("provider"):
            target["provider"] = row["provider"]
    # None -> "" so a never-reported field reads blank, not zero.
    return [
        {k: ("" if v is None else v) for k, v in grouped[key].items()}
        for key in sorted(grouped)
    ]
