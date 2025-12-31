# Jira JQL Query Builder

Generate JQL (Jira Query Language) queries to find, filter, and analyze issues in Jira.

## Usage

Replace the `[PLACEHOLDERS]` with your specific information.

---

## Prompt

```
You are an experienced Product Manager helping me build JQL queries for Jira.

## What I Need
[DESCRIBE WHAT YOU'RE TRYING TO FIND OR ANALYZE]

## Context
- Project(s): [PROJECT KEYS, e.g., PLATFORM, AUTH]
- Date Range: [OPTIONAL - e.g., "last 30 days", "Q1 2024"]
- Issue Types: [OPTIONAL - Story, Bug, Task, Epic]
- Additional Filters: [OPTIONAL - e.g., "only high priority", "assigned to specific team"]

## Instructions

Generate a JQL query that:
1. Finds the issues I need
2. Includes appropriate filters
3. Orders results logically (by priority, status, or date)
4. Is optimized for performance (uses indexed fields)

Also provide:
- Explanation of what the query does
- Alternative queries for related use cases
- Tips for modifying the query

---

## Common JQL Patterns

Use these as building blocks:

**By Status:**
- `status = "In Progress"`
- `status IN ("To Do", "In Progress")`
- `status CHANGED FROM "In Progress" TO "Done" AFTER -7d`

**By Priority:**
- `priority = Highest`
- `priority IN (Highest, High)`

**By Assignee:**
- `assignee = currentUser()`
- `assignee IN (user1, user2)`
- `assignee IS EMPTY`

**By Project:**
- `project = PLATFORM`
- `project IN (PLATFORM, AUTH)`

**By Date:**
- `created >= -30d` (last 30 days)
- `updated >= "2024-01-01"`
- `resolved >= -7d` (resolved in last week)

**By Labels:**
- `labels = "frontend"`
- `labels IN (frontend, api)`

**By Epic:**
- `"Epic Link" = PLATFORM-100`
- `"Epic Link" IN (PLATFORM-100, PLATFORM-101)`

**By Sprint:**
- `sprint = "Sprint 45"`
- `sprint IN openSprints()`

**Combining with AND/OR:**
- `project = PLATFORM AND status = "In Progress"`
- `priority = Highest OR priority = High`
- `(project = PLATFORM OR project = AUTH) AND status != Done`

**Ordering:**
- `ORDER BY priority DESC, updated DESC`
- `ORDER BY created ASC`
```

---

## Example Inputs

### Example 1: Sprint Status
```
What I Need: All issues in the current sprint that are blocked or at risk
Project: PLATFORM
Issue Types: Story, Bug
```

### Example 2: Backlog Analysis
```
What I Need: High priority stories in the backlog that haven't been updated in 30 days
Project: PLATFORM, AUTH
Date Range: Updated more than 30 days ago
```

### Example 3: Release Planning
```
What I Need: All bugs fixed in the last sprint that are related to authentication
Project: AUTH
Issue Types: Bug
Date Range: Last 14 days
Labels: authentication
```

---

## Example Outputs

### Example 1 Output

**Query:**
```jql
project = PLATFORM 
AND sprint IN openSprints() 
AND (status = "Blocked" OR labels = "at-risk")
AND type IN (Story, Bug)
ORDER BY priority DESC, updated DESC
```

**Explanation:**
Finds all stories and bugs in active sprints for the PLATFORM project that are either blocked or labeled as "at-risk", ordered by priority and most recently updated.

**Alternative Queries:**

*All in-progress issues in current sprint:*
```jql
project = PLATFORM 
AND sprint IN openSprints() 
AND status = "In Progress"
ORDER BY priority DESC
```

*Issues that became blocked in the last 7 days:*
```jql
project = PLATFORM 
AND sprint IN openSprints() 
AND status CHANGED TO "Blocked" AFTER -7d
ORDER BY updated DESC
```

**Tips:**
- Use `openSprints()` to automatically include all active sprints
- Add `AND assignee IS NOT EMPTY` if you only want assigned issues
- Use `AND resolution = Unresolved` to exclude completed work

---

### Example 2 Output

**Query:**
```jql
project IN (PLATFORM, AUTH) 
AND priority IN (Highest, High) 
AND status = "Backlog"
AND updated <= -30d
AND type = Story
ORDER BY priority DESC, created ASC
```

**Explanation:**
Finds high-priority stories in the backlog that haven't been touched in 30+ days, across both PLATFORM and AUTH projects, ordered by priority then creation date.

**Alternative Queries:**

*Stale high-priority issues (any status):*
```jql
project IN (PLATFORM, AUTH) 
AND priority IN (Highest, High) 
AND updated <= -30d
AND resolution = Unresolved
ORDER BY priority DESC, updated ASC
```

*Backlog items by epic:*
```jql
project = PLATFORM 
AND status = "Backlog"
AND "Epic Link" IS NOT EMPTY
ORDER BY "Epic Link", priority DESC
```

**Tips:**
- `updated <= -30d` means "updated 30 or more days ago"
- Consider adding `AND "Epic Link" IS NOT EMPTY` to focus on epiced work
- Use `resolution = Unresolved` to exclude completed items

---

### Example 3 Output

**Query:**
```jql
project = AUTH 
AND type = Bug 
AND status = Done
AND resolved >= -14d
AND labels = authentication
ORDER BY resolved DESC, priority DESC
```

**Explanation:**
Finds all authentication-related bugs that were resolved in the last 14 days, ordered by resolution date and priority.

**Alternative Queries:**

*All bugs fixed in a specific sprint:*
```jql
project = AUTH 
AND type = Bug 
AND status = Done
AND sprint = "Sprint 45"
AND labels = authentication
ORDER BY resolved DESC
```

*Bugs by severity:*
```jql
project = AUTH 
AND type = Bug 
AND status = Done
AND resolved >= -14d
AND priority = Highest
ORDER BY resolved DESC
```

**Tips:**
- `resolved >= -14d` uses the resolution date, not the status change date
- Add `AND fixVersion = "v2.1"` to filter by release version
- Use `AND reporter = currentUser()` to see bugs you reported

---

## Common Use Cases

### Sprint Planning
```jql
project = PLATFORM 
AND sprint IN openSprints()
AND status != Done
ORDER BY priority DESC, storyPoints ASC
```

### Burndown Analysis
```jql
project = PLATFORM 
AND sprint = "Sprint 45"
AND type = Story
ORDER BY status, priority DESC
```

### Technical Debt
```jql
project = PLATFORM 
AND labels = "technical-debt"
AND resolution = Unresolved
ORDER BY priority DESC, created ASC
```

### Blocked Work
```jql
project = PLATFORM 
AND status = "Blocked"
AND resolution = Unresolved
ORDER BY priority DESC, updated DESC
```

### My Work
```jql
assignee = currentUser() 
AND resolution = Unresolved
ORDER BY priority DESC, updated DESC
```

### Epic Progress
```jql
"Epic Link" = PLATFORM-100
AND resolution = Unresolved
ORDER BY status, priority DESC
```

### Release Candidates
```jql
project = PLATFORM 
AND fixVersion = "v2.1"
AND status != Done
ORDER BY priority DESC
```

---

## Tips

- **Use indexed fields** - `project`, `status`, `type`, `assignee`, `priority` are indexed and fast
- **Avoid functions in WHERE** - Functions like `currentUser()` are slower; use them in ORDER BY if needed
- **Combine with AND first** - More specific queries are faster
- **Use IN instead of OR** - `priority IN (High, Highest)` is faster than `priority = High OR priority = Highest`
- **Limit results** - Add `LIMIT 100` if you only need a subset
- **Test incrementally** - Build queries step by step, testing each addition

