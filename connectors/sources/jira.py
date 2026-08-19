#!/usr/bin/env python3
"""
jira connector — pull issues from Jira Cloud or Data Center.

Reads the same JIRA_HOST / JIRA_EMAIL / JIRA_API_TOKEN the MCP server in
mcps/servers/jira-pm-assistant/ already documents, so one credential set serves
both paths.

Three things here are more than a field rename, and each exists because the
naive version produces a plausible wrong answer rather than an error:

1. **Custom field discovery.** Story points and sprint live under a
   `customfield_NNNNN` id that differs per Jira instance. Hardcoding an id
   yields empty points on every other instance — silently, since a missing
   field just reads blank. This asks `/rest/api/3/field` for the id by name,
   and lets `--points-field` or a profile override the answer.

2. **ADF flattening.** API v3 returns `description` as an Atlassian Document
   Format tree, not a string. Written straight to CSV it becomes an unreadable
   JSON blob in one cell; `_adf_text()` walks it back to plain text.

3. **`started` from the changelog.** Jira has no started field — three of the
   seven consuming scripts want one, and without it `blocker-wait-summary`
   silently reports wait == lead time for every ticket. With `--with-started`
   this replays each issue's status history and takes the first transition
   into an in-progress status category.

Endpoint note: Jira Cloud retired `/rest/api/3/search` in favour of
`/rest/api/3/search/jql` with token pagination. Data Center still serves the
old one with `startAt`. This tries the new endpoint and falls back on 404/410,
so both deployments work.

Usage:
    export JIRA_HOST=yourcompany.atlassian.net
    export JIRA_EMAIL=you@company.com
    export JIRA_API_TOKEN=...

    python fetch.py jira issues --project PLAT --out issues.csv
    python fetch.py jira issues --jql "project = PLAT AND sprint in openSprints()" --out issues.csv
    python fetch.py jira issues --project PLAT --updated-since 2026-01-01 --with-started --out issues.csv
    python fetch.py jira issues --project PLAT --points-field customfield_10024 --out issues.csv
    python fetch.py jira issues --offline --out issues.csv        # replay the fixture

Requirements:
    None (stdlib only).
"""

import base64
import json
import re
import urllib.parse
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import datasets
from base import Connector, ConnectorError, FetchResult

PAGE_SIZE = 100

# Names Jira ships for the story-point field. "Story point estimate" is the
# next-gen/team-managed spelling; "Story Points" the classic one.
POINTS_FIELD_NAMES = ("story points", "story point estimate", "story point")
SPRINT_SCHEMA = "com.atlassian.greenhopper.service.sprint.gh-sprint"

BASE_FIELDS = (
    "summary",
    "status",
    "issuetype",
    "priority",
    "assignee",
    "created",
    "updated",
    "resolutiondate",
    "components",
    "description",
)


class JiraConnector(Connector):
    name = "jira"
    provides = frozenset({"issues"})
    description = "Pull issues from Jira Cloud or Data Center via JQL."

    @classmethod
    def add_arguments(cls, parser) -> None:
        parser.add_argument("--jql", help="Raw JQL. Overrides --project/--updated-since")
        parser.add_argument("--project", help="Project key, e.g. PLAT")
        parser.add_argument(
            "--updated-since",
            metavar="YYYY-MM-DD",
            help="Only issues updated on or after this date",
        )
        parser.add_argument(
            "--max",
            type=int,
            default=1000,
            help="Maximum issues to fetch (default: 1000)",
        )
        parser.add_argument(
            "--with-started",
            action="store_true",
            help="Derive `started` from each issue's status changelog (slower)",
        )
        parser.add_argument(
            "--in-progress-status",
            action="append",
            default=[],
            metavar="NAME",
            help="Treat this status name as in-progress for --started; repeatable. "
            "Default: any status whose Jira category is 'In Progress'.",
        )
        parser.add_argument(
            "--points-field", help="Story points field id, e.g. customfield_10016"
        )
        parser.add_argument("--sprint-field", help="Sprint field id")
        parser.add_argument(
            "--field",
            action="append",
            default=[],
            metavar="CANONICAL=FIELD_ID",
            help="Map a canonical column to a Jira field id; repeatable",
        )
        parser.add_argument(
            "--profile", help="JSON file mapping canonical column -> Jira field id"
        )

    # -- config ------------------------------------------------------------

    def _auth_headers(self) -> Dict[str, str]:
        """Basic auth for Cloud; bearer for a Data Center PAT.

        A Data Center personal access token has no email half, so an unset
        JIRA_EMAIL is the signal to send a bearer token rather than an error.
        """
        token = self.env("JIRA_API_TOKEN")
        email = self.env("JIRA_EMAIL", required=False)
        headers = {"Accept": "application/json"}
        if email:
            raw = f"{email}:{token}".encode("utf-8")
            headers["Authorization"] = f"Basic {base64.b64encode(raw).decode('ascii')}"
        else:
            headers["Authorization"] = f"Bearer {token}"
        return headers

    def _base_url(self) -> str:
        host = self.env("JIRA_HOST").replace("https://", "").replace("http://", "")
        return f"https://{host.rstrip('/')}/rest/api/3"

    # -- field resolution --------------------------------------------------

    def _discover_fields(
        self, args, warnings: List[str]
    ) -> Tuple[Dict[str, str], Dict[str, Any]]:
        """Resolve canonical column -> Jira field id.

        Precedence, most specific first: --field, --profile, then discovery by
        name against /rest/api/3/field.
        """
        overrides: Dict[str, str] = {}
        if args.profile:
            path = Path(args.profile)
            if not path.exists():
                raise ConnectorError(f"{self.name}: no such profile: {path}")
            data = json.loads(path.read_text(encoding="utf-8"))
            overrides.update(
                {str(k): str(v) for k, v in (data.get("columns", data)).items()}
            )
        for flag in args.field or []:
            if "=" not in flag:
                raise ConnectorError(
                    f"{self.name}: --field expects CANONICAL=FIELD_ID, got {flag!r}"
                )
            key, value = flag.split("=", 1)
            overrides[key.strip()] = value.strip()
        if args.points_field:
            overrides["points"] = args.points_field
        if args.sprint_field:
            overrides["sprint"] = args.sprint_field

        spec = datasets.get("issues")
        for canonical in list(overrides):
            if spec.get_column(canonical) is None:
                warnings.append(
                    f"field mapping for '{canonical}' ignored: not a column of 'issues'"
                )
                overrides.pop(canonical)

        discovered: Dict[str, Any] = {}
        if "points" in overrides and "sprint" in overrides:
            return overrides, discovered

        catalog = self._field_catalog()
        if "points" not in overrides:
            hit = _find_field(catalog, names=POINTS_FIELD_NAMES)
            if hit:
                overrides["points"] = hit
                discovered["points"] = hit
            else:
                warnings.append(
                    "no story-point field found on this instance; `points` will be "
                    "empty. Pass --points-field customfield_NNNNN if it is named "
                    "something non-standard."
                )
        if "sprint" not in overrides:
            hit = _find_field(catalog, schema=SPRINT_SCHEMA, names=("sprint",))
            if hit:
                overrides["sprint"] = hit
                discovered["sprint"] = hit
        return overrides, discovered

    def _field_catalog(self) -> List[Dict[str, Any]]:
        if self.offline:
            return self.load_fixture("fields")
        return self.get_json(f"{self._base_url()}/field", self._auth_headers())

    # -- status categories -------------------------------------------------

    def _in_progress_statuses(self, args) -> set:
        """Status names that count as in-progress, lowercased.

        Uses Jira's own status categories rather than a hardcoded list of
        names: every team renames these ("Building", "In Dev", "Doing"), and a
        name-matching heuristic would quietly miss all of them.
        """
        explicit = {s.strip().lower() for s in (args.in_progress_status or []) if s.strip()}
        if explicit:
            return explicit
        raw = (
            self.load_fixture("statuses")
            if self.offline
            else self.get_json(f"{self._base_url()}/status", self._auth_headers())
        )
        return {
            str(s.get("name", "")).lower()
            for s in raw
            if (s.get("statusCategory") or {}).get("key") == "indeterminate"
        }

    # -- fetching ----------------------------------------------------------

    def _build_jql(self, args) -> str:
        if args.jql:
            return args.jql
        clauses = []
        if args.project:
            clauses.append(f'project = "{args.project}"')
        if args.updated_since:
            clauses.append(f'updated >= "{args.updated_since}"')
        if not clauses:
            raise ConnectorError(
                f"{self.name}: need --jql, --project, or --updated-since to know "
                f"what to fetch"
            )
        return " AND ".join(clauses) + " ORDER BY created ASC"

    def _pages(self, jql: str, fields: List[str], expand: bool) -> List[Dict[str, Any]]:
        """Every page of results, new endpoint first, legacy on 404/410."""
        if self.offline:
            pages = self.load_fixture("issues")
            return pages if isinstance(pages, list) else [pages]

        base = self._base_url()
        headers = self._auth_headers()
        params = {
            "jql": jql,
            "maxResults": str(PAGE_SIZE),
            "fields": ",".join(fields),
        }
        if expand:
            params["expand"] = "changelog"

        try:
            return _paginate_token(self, f"{base}/search/jql", params, headers)
        except ConnectorError as exc:
            if "HTTP 404" not in str(exc) and "HTTP 410" not in str(exc):
                raise
            # Data Center / older Cloud: the token endpoint doesn't exist.
            return _paginate_offset(self, f"{base}/search", params, headers)

    def fetch(self, dataset: str, args) -> FetchResult:
        warnings: List[str] = []
        # Build the JQL before anything touches the network: field discovery is
        # a request, and spending it only to then fail on a missing --project
        # reports the wrong problem second.
        jql = "(fixture)" if self.offline else self._build_jql(args)
        field_map, discovered = self._discover_fields(args, warnings)

        fields = list(BASE_FIELDS)
        for canonical in ("points", "sprint"):
            field_id = field_map.get(canonical)
            if field_id and field_id not in fields:
                fields.append(field_id)
        for canonical, field_id in field_map.items():
            if canonical not in ("points", "sprint") and field_id not in fields:
                fields.append(field_id)

        pages = self._pages(jql, fields, expand=args.with_started)

        issues: List[Dict[str, Any]] = []
        for page in pages:
            issues.extend(page.get("issues", []))
            if len(issues) >= args.max:
                issues = issues[: args.max]
                break

        in_progress: set = set()
        if args.with_started:
            in_progress = self._in_progress_statuses(args)
            if not in_progress:
                warnings.append(
                    "--with-started: no in-progress statuses resolved, so `started` "
                    "will be empty. Pass --in-progress-status to name them."
                )

        rows = [
            self._to_row(issue, field_map, in_progress if args.with_started else None)
            for issue in issues
        ]

        if args.with_started:
            missing = sum(1 for r in rows if not r.get("started"))
            if missing:
                # Common and load-bearing: an issue never moved through an
                # in-progress status, or its changelog was truncated. Scripts
                # fall back to lead time, which is a different number.
                warnings.append(
                    f"--with-started: no in-progress transition found for "
                    f"{missing}/{len(rows)} issues; `started` is blank for those"
                )

        query = {
            "jql": jql,
            "fields": fields,
            "field_map": field_map,
            "discovered": discovered,
            "with_started": bool(args.with_started),
            "max": args.max,
            "host": "(offline)" if self.offline else self.env("JIRA_HOST", required=False),
        }
        return FetchResult(rows, query, warnings)

    def _to_row(
        self,
        issue: Dict[str, Any],
        field_map: Dict[str, str],
        in_progress: Optional[set],
    ) -> Dict[str, Any]:
        fields = issue.get("fields") or {}
        row: Dict[str, Any] = {
            "id": issue.get("key", ""),
            "summary": fields.get("summary") or "",
            "status": _name_of(fields.get("status")),
            "type": _name_of(fields.get("issuetype")),
            "priority": _name_of(fields.get("priority")),
            "assignee": _display_name(fields.get("assignee")),
            "created": fields.get("created") or "",
            "updated": fields.get("updated") or "",
            "done": fields.get("resolutiondate") or "",
            "component": _components(fields.get("components")),
            "description": _adf_text(fields.get("description")),
        }
        points_field = field_map.get("points")
        if points_field:
            row["points"] = _scalar(fields.get(points_field))
        sprint_field = field_map.get("sprint")
        if sprint_field:
            row["sprint"] = _sprint_name(fields.get(sprint_field))
        for canonical, field_id in field_map.items():
            if canonical in ("points", "sprint") or canonical in row:
                continue
            row[canonical] = _scalar(fields.get(field_id))
        if in_progress is not None:
            row["started"] = _first_in_progress(issue, in_progress)
        return row


# --------------------------------------------------------------------------
# Pagination
# --------------------------------------------------------------------------


def _paginate_token(connector, url, params, headers) -> List[Dict[str, Any]]:
    """Cloud: `nextPageToken` until `isLast`."""
    pages: List[Dict[str, Any]] = []
    token: Optional[str] = None
    while True:
        query = dict(params)
        if token:
            query["nextPageToken"] = token
        page = connector.get_json(f"{url}?{urllib.parse.urlencode(query)}", headers)
        pages.append(page)
        token = page.get("nextPageToken")
        if page.get("isLast") or not token or not page.get("issues"):
            return pages


def _paginate_offset(connector, url, params, headers) -> List[Dict[str, Any]]:
    """Data Center: `startAt` until the page comes back short."""
    pages: List[Dict[str, Any]] = []
    start = 0
    while True:
        query = dict(params, startAt=str(start))
        page = connector.get_json(f"{url}?{urllib.parse.urlencode(query)}", headers)
        pages.append(page)
        issues = page.get("issues", [])
        start += len(issues)
        total = page.get("total")
        if not issues or (total is not None and start >= total):
            return pages


# --------------------------------------------------------------------------
# Field extraction
# --------------------------------------------------------------------------


def _find_field(
    catalog: List[Dict[str, Any]],
    *,
    names: Tuple[str, ...] = (),
    schema: Optional[str] = None,
) -> Optional[str]:
    """Field id matching a schema custom type or one of several display names."""
    if schema:
        for field in catalog:
            if (field.get("schema") or {}).get("custom") == schema:
                return field.get("id")
    wanted = [n.lower() for n in names]
    for want in wanted:  # in preference order, not catalog order
        for field in catalog:
            if str(field.get("name", "")).strip().lower() == want:
                return field.get("id")
    return None


def _name_of(value: Any) -> str:
    return str((value or {}).get("name", "") or "") if isinstance(value, dict) else ""


def _display_name(value: Any) -> str:
    if not isinstance(value, dict):
        return ""
    return str(value.get("displayName") or value.get("name") or "")


def _components(value: Any) -> str:
    if not isinstance(value, list):
        return ""
    return "; ".join(str(c.get("name", "")) for c in value if isinstance(c, dict))


def _scalar(value: Any) -> str:
    """Flatten whatever a custom field holds into one cell."""
    if value is None:
        return ""
    if isinstance(value, dict):
        return str(value.get("value") or value.get("name") or "")
    if isinstance(value, list):
        return "; ".join(_scalar(v) for v in value if v is not None)
    return str(value)


def _sprint_name(value: Any) -> str:
    """Current sprint name from any of the three shapes Jira has used.

    Modern Jira returns objects; older Greenhopper returned a serialized blob
    like "...[id=42,name=Sprint 41,...]". Both still turn up in the wild, and
    an issue in several sprints lists them oldest-first, so the last is current.
    """
    if not value:
        return ""
    items = value if isinstance(value, list) else [value]
    names = []
    for item in items:
        if isinstance(item, dict):
            names.append(str(item.get("name", "")))
        else:
            match = re.search(r"name=([^,\]]+)", str(item))
            names.append(match.group(1) if match else str(item))
    names = [n for n in names if n]
    return names[-1] if names else ""


def _adf_text(node: Any) -> str:
    """Flatten an Atlassian Document Format tree to plain text."""
    if node is None:
        return ""
    if isinstance(node, str):
        return node
    if isinstance(node, list):
        return " ".join(part for part in (_adf_text(n) for n in node) if part)
    if not isinstance(node, dict):
        return str(node)
    if node.get("type") == "text":
        return str(node.get("text", ""))
    inner = _adf_text(node.get("content"))
    # Block-level nodes end a line; inline nodes just run together.
    if node.get("type") in ("paragraph", "heading", "listItem", "blockquote"):
        return inner.strip() + " "
    return inner


def _first_in_progress(issue: Dict[str, Any], in_progress: set) -> str:
    """Timestamp of the first status transition into an in-progress state."""
    histories = ((issue.get("changelog") or {}).get("histories")) or []
    stamps = []
    for history in histories:
        for item in history.get("items") or []:
            if str(item.get("field", "")).lower() != "status":
                continue
            if str(item.get("toString", "")).lower() in in_progress:
                stamps.append(history.get("created", ""))
    stamps = [s for s in stamps if s]
    return min(stamps) if stamps else ""
