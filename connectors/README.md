# Connectors

Pull data from the systems you already use into the CSV shapes `scripts/` already reads.

Most scripts in this toolkit are excellent and rarely run, for one reason: each needs a hand-built CSV. A tool you have to prepare data for gets used once. A tool that reads from Jira gets used every sprint. Connectors close that gap.

```bash
# 1. fetch                                        2. analyze
python connectors/fetch.py csvfile issues \
    --input jira-export.csv --out issues.csv
python scripts/cycle-lead-time-analyzer.py --csv issues.csv
```

Two steps, not one. The alternative — teaching all 115 scripts to speak HTTP — would put auth and network failures inside tools that are currently pure functions over a file, and would break the offline guarantee `smoke-test.py` relies on. It also leaves you a CSV on disk: inspectable, committable next to the deck that quotes it, re-runnable in six months.

## Quick start

```bash
python connectors/fetch.py --list              # sources and datasets
python connectors/fetch.py --describe issues   # the column contract
python connectors/self-test.py                 # verify connectors feed their scripts
```

## The idea: dataset contracts

The connectors are not the point — the **contracts** are. A Jira fetcher alone is worth little. A Jira fetcher and a Linear fetcher that emit *the same columns* mean every downstream script works against either without knowing which ran.

Those contracts live in [`datasets.py`](datasets.py), and every canonical column name in them was **derived from the scripts, not invented**. The rule:

> A canonical name is valid only if it appears somewhere in the alias list of *every* script that consumes the dataset.

The 63 scripts with private `_col()` alias lists already declare what they accept. Reading them out and taking the intersection is what makes a contract that requires zero script changes. Designing names fresh is what produces a contract you then have to edit 7 scripts to satisfy.

That rule rejected several obvious-looking names. `resolved` reads like the right name for a completion date, but no issue script lists it — they all say `done`. `category` sounds more general than `type`, but `backlog-health-report.py` and `sprint-mix-report.py` don't accept it. Both are carried as *aliases* (Jira's export header is literally `Resolved`) while the canonical name stays the one the scripts read.

### `issues`

One row per ticket. Feeds 7 scripts: `backlog-aging-report`, `backlog-health-report`, `blocker-wait-summary`, `cycle-lead-time-analyzer`, `sprint-mix-report`, `sprint-scope-checker`, `throughput-wip-analyzer`.

| column | kind | required | notes |
|---|---|---|---|
| `id` | text | yes | ticket key |
| `summary` | text | | |
| `status` | text | | |
| `type` | text | | not `category` |
| `priority` | text | | |
| `assignee` | text | | |
| `points` | number | | |
| `created` | date | yes | ISO 8601 |
| `started` | date | | |
| `done` | date | | not `resolved` |
| `updated` | date | | |
| `sprint` | text | | |
| `component` | text | | |
| `description` | text | | |
| `blocker_reason` | text | | |

Only `id` and `created` are required — the intersection every consumer needs. Individual scripts want more (`cycle-lead-time-analyzer` needs `created` + `done`), and a fetch missing them still writes, with a warning.

Run `fetch.py --describe issues` for the full alias list per column.

> Not this contract: `sprint-velocity-tracker`, `commitment-predictability-index`, and `sprint-burndown-checker` read *sprint-level aggregates*, and `status-duration-analyzer` reads a *transition log*. Those are separate shapes and get their own contracts when a connector needs them.

## Sources

| source | provides | config |
|---|---|---|
| `csvfile` | `issues` | none |

### `csvfile`

Normalizes an existing export — the Jira/Linear "export to CSV" button — into canonical shape: contract columns first, dates in ISO 8601, story points de-comma'd.

```bash
python fetch.py csvfile issues --input export.csv --out issues.csv
python fetch.py csvfile issues --input export.csv --out issues.csv --profile profiles/jira.json
python fetch.py csvfile issues --input export.csv --out issues.csv --map points="Custom field (Story Points)"
```

Mapping precedence, most specific first:

1. `--map canonical=header` — repeatable, wins outright
2. `--profile <file>` — per-instance JSON, canonical → source header
3. the aliases declared in `datasets.py`

Useful flags: `--drop-extras` (emit only contract columns; unmapped source columns pass through by default), `--strict` (exit non-zero if a required column can't be mapped instead of warning).

## Provenance

Every fetch writes `<out>.csv.meta.json` beside the CSV — source, resolved column mapping, row count, timestamp, warnings — using the same `toolkit_io` envelope the scripts write. `toolkit_io` could already trace a number back to the script that produced it; this extends that backwards to the query that fed the script.

```bash
python scripts/toolkit_io.py issues.csv.meta.json
```

## Writing a new connector

Three steps.

**1. Implement it** in `sources/<name>.py`:

```python
from base import Connector, FetchResult

class MySourceConnector(Connector):
    name = "mysource"
    provides = frozenset({"issues"})
    description = "One line for --list."

    @classmethod
    def add_arguments(cls, parser):
        parser.add_argument("--project", required=True)

    def fetch(self, dataset, args):
        raw = self.get_json(url, headers={...})     # retries + backoff provided
        rows = [{"id": r["key"], "created": r["createdAt"], ...} for r in raw]
        return FetchResult(rows, query={"project": args.project})
```

You write the API call and the field mapping. `base.py` handles config, retries, ISO date normalization, canonical column ordering, validation, and the sidecar — so output stays identical across sources, which is the whole promise.

**2. Register it** — one line in `registry.py`.

**3. Add a test case** — one entry in `self-test.py`'s `CONNECTOR_CASES`, plus a fixture in `fixtures/`. A registered connector with no case is reported as untested rather than silently passing.

### Two rules worth following

**Credentials reuse the MCP env var names.** `mcps/servers/jira-pm-assistant/` already documents `JIRA_HOST` / `JIRA_EMAIL` / `JIRA_API_TOKEN`. Use `self.env("JIRA_API_TOKEN")` and one credential set serves both paths.

**Instance-specific field IDs are config, not code.** Jira story points live in `customfield_10016` on one instance and `customfield_10024` on the next. Hardcode it and the connector works only for you. Put it in `profiles/`.

## Testing

`self-test.py` fetches from each connector's fixture and then runs **every script the contract claims to feed**, asserting each one actually finds rows. Exit 0 with an empty table is the failure mode this catches — a mis-mapped column doesn't look wrong in the CSV, it just makes every downstream number quietly zero.

This is what pins the contract. Renaming `done` to `resolved` in `datasets.py` turns it red immediately:

```
FAIL blocker-wait-summary: exit 1 — No tickets found (need created and done dates).
FAIL cycle-lead-time-analyzer: exit 1 — no valid tickets found.
```

No network and no credentials needed — fixtures only.

## Status

Step 1 of the plan in [`docs/suggested-tools.md`](../docs/suggested-tools.md): contract + base + CLI + the no-auth connector. Next: **Jira → `issues`** (highest fan-out), then **gateway → `llm_usage`** (turns ~8 cost scripts from estimators into actuals), then **Linear → `issues`** — which is the real test of the contract. If adding Linear forces a change to `issues`, the contract was wrong, and better to learn that at connector 3 than connector 9.
