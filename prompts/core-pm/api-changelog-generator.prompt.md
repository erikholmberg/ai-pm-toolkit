# API Changelog Generator

Generate developer-facing changelogs from diffs, PR descriptions, or lists of API changes. Designed for AI products with public APIs where clear developer communication is critical.

## Usage

Replace the `[PLACEHOLDERS]` with your specific information.

---

## API Changelog from Changes

```
You are a developer relations expert writing API changelogs. Generate a clear, developer-friendly changelog from the following changes.

## Context
- Product/API: [PRODUCT NAME / API NAME]
- Version: [e.g., "v2.4.0", "2025-01-15 release"]
- Release Date: [DATE]
- API Style: [e.g., "REST", "GraphQL", "gRPC", "WebSocket"]
- Audience: [e.g., "External developers", "Internal teams", "Partner integrations"]
- Changelog Format: [e.g., "Keep a Changelog", "Stripe-style dated", "Custom"]

## Changes
---
[PASTE YOUR CHANGES HERE — any of the following formats work:
- Git diff
- PR titles and descriptions
- Jira ticket summaries
- Bullet-point list of changes
- Commit messages]

Example:
- Added POST /v2/embeddings/batch for bulk embedding generation
- Changed: /v2/completions now returns `usage.cache_hit` field in response
- Fixed: 500 error when `max_tokens` exceeds model context window — now returns 400 with descriptive message
- Deprecated: `model` parameter value "gpt-3" — use "gpt-3.5-turbo" instead, removal in v3
- Rate limit on /v2/completions increased from 60 to 120 RPM for Pro tier
- Auth: API keys now require the `v2_` prefix — old keys valid until 2025-06-01
---

## Instructions

Generate a developer changelog with:

### 1. Release Header
- Version / date identifier
- One-sentence summary of the release theme

### 2. Categorized Changes
Group changes using these categories (omit empty categories):

#### ✨ Added
For each new endpoint, field, or capability:
- **What:** Clear description of the addition
- **Endpoint:** `METHOD /path` (for API changes)
- **Example:** Request/response snippet showing usage
- **Docs:** Link placeholder to documentation

#### 🔄 Changed
For each behavior or interface change:
- **What:** What changed and why
- **Before:** Previous behavior (with code example if helpful)
- **After:** New behavior (with code example)
- **Migration:** What developers need to do (if anything)

#### ⚠️ Deprecated
For each deprecation:
- **What:** What's being deprecated
- **Replacement:** What to use instead
- **Timeline:** When it will be removed
- **Migration:** Steps to migrate

#### 🐛 Fixed
For each bug fix:
- **What:** Description of the fix from the developer's perspective
- **Impact:** Who was affected and how
- **Details:** Technical detail (if relevant to API consumers)

#### 🗑️ Removed
For each removal:
- **What:** What was removed
- **Reason:** Why
- **Alternative:** What to use instead

#### 🔒 Security
For security-related changes:
- **What:** Description (without exposing vulnerability details)
- **Action Required:** What developers need to do

#### ⚡ Performance
For performance improvements:
- **What:** What improved
- **Impact:** Specific metrics (e.g., "p99 latency reduced from 800ms to 200ms")

### 3. Breaking Changes Summary
If any changes are breaking:
- Prominent callout box at the top
- Table: Change | Impact | Migration Steps | Deadline

### 4. Migration Checklist
If breaking changes exist, provide a developer checklist:
- [ ] Step 1: [SPECIFIC ACTION]
- [ ] Step 2: [SPECIFIC ACTION]
- [ ] Step 3: Test with [SPECIFIC SCENARIO]

### 5. SDK Updates
If applicable:
- SDK versions that include these changes
- Package manager install commands

---

## Guidelines
- Write for developers who will scan, not read — use headers, code blocks, and tables
- Every breaking change needs a code example showing before/after
- Use HTTP method + path format for endpoint references: `POST /v2/embeddings`
- Include response codes where behavior changed
- Timestamp deprecation deadlines precisely — "Q2 2025" is not good enough; "2025-06-30" is
- Link to relevant docs, migration guides, and API reference
- For AI APIs specifically: note changes to model behavior, output format, token counting, or pricing
```

---

## Changelog from Git Diff

```
Generate an API changelog from this git diff. Focus only on changes that affect the public API contract — ignore internal refactors, test changes, and CI/CD updates.

## Context
- API: [PRODUCT NAME]
- Release: [VERSION OR DATE]
- Audience: [EXTERNAL DEVELOPERS / INTERNAL TEAMS]

## Git Diff
---
[PASTE GIT DIFF OR `git log --oneline v1.2.0..v1.3.0`]
---

## Instructions

1. **Filter** — Identify only changes that affect the public API surface:
   - New or changed endpoints
   - Request/response schema changes
   - Authentication or authorization changes
   - Rate limit changes
   - Error code or message changes
   - SDK method signature changes

2. **Categorize** — Group using Added / Changed / Deprecated / Fixed / Removed

3. **Enrich** — For each change:
   - Write a developer-friendly description (not the commit message)
   - Add code examples for non-obvious changes
   - Flag breaking changes prominently

4. **Summarize** — Write a 2-3 sentence release summary at the top

Ignore: dependency updates, internal refactors, test changes, documentation-only changes, CI/CD changes.
```

---

## Cumulative Changelog (Multi-Release)

```
Help me create a cumulative changelog that summarizes multiple releases for developers who haven't updated in a while.

## Context
- API: [PRODUCT NAME]
- Covering Versions: [FROM VERSION] → [TO VERSION]
- Time Period: [DATE RANGE]
- Audience: [WHO NEEDS TO CATCH UP]

## Individual Changelogs
---
[PASTE ALL INDIVIDUAL CHANGELOGS OR RELEASE NOTES FOR THE PERIOD]
---

## Instructions

Generate a cumulative changelog that:

### 1. Executive Summary
- How many releases this covers
- Top 3 most important changes across all releases
- Any breaking changes (aggregated)

### 2. Aggregated Breaking Changes
All breaking changes in one place, deduplicated:
- If a field was added in v2.1 and then renamed in v2.3, only show the final state
- Provide migration path from the starting version directly to the latest version

### 3. Full Changelog (Condensed)
Group by category across all releases:
- Deduplicate (don't list something added and then modified — show final state)
- Mark which version introduced each change

### 4. Upgrade Guide
Step-by-step instructions to go from [FROM VERSION] to [TO VERSION]:
- Ordered by dependency (do X before Y)
- Code migration examples
- Testing recommendations

This is for the developer who skipped 5 releases and needs a single document to catch up.
```

---

## Tips

- **Ship the changelog with the release** - Don't make developers discover changes through errors
- **Use machine-readable format too** - Consider also generating OpenAPI diff or JSON changelog for tooling
- **Test your examples** - Code snippets in changelogs that don't work destroy trust
- **Distinguish internal vs. external** - Not all changes are relevant to API consumers
- **Version your changelog format** - Consistency across releases makes changelogs scannable
- **RSS/webhook for changelogs** - Let developers subscribe to API changes instead of checking manually

