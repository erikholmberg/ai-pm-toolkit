# MCP Use Cases for Product Managers

Real-world examples of how PMs can use MCP servers to augment their AI workflow.

---

## Why MCP for PMs?

MCP servers let your AI assistant directly interact with your tools. Instead of copying and pasting, you can have natural conversations that take action.

**Without MCP:**
> "Can you help me write a ticket for the new search feature?"
> 
> *Claude writes the ticket content*
> 
> *You copy it to Jira manually*

**With MCP:**
> "Create a Jira ticket for the new search feature and assign it to the Platform team"
> 
> *Claude creates the ticket directly in Jira*

---

## Jira Use Cases

### 1. Sprint Planning Assistant

**Scenario:** Preparing for sprint planning

```
"Show me the current sprint status for the Platform team. 
How many points are committed vs completed?"
```

```
"What tickets are in the backlog that are ready for sprint planning? 
Prioritize by RICE score."
```

### 2. Ticket Creation from PRD

**Scenario:** Breaking down a PRD into tickets

```
"I have a PRD for user authentication improvements. Create Jira tickets 
for each of these user stories:
1. As a user, I want to log in with SSO
2. As a user, I want to reset my password via email
3. As an admin, I want to require MFA for all users

Assign them to the Platform team and set priority based on dependency order."
```

### 3. Release Notes Generation

**Scenario:** Creating release notes from closed tickets

```
"Generate release notes for Sprint 45. Pull all tickets that moved to Done 
this sprint, categorize them (Features, Improvements, Bug Fixes), and 
format them for our changelog."
```

### 4. Status Updates

**Scenario:** Preparing for standup or stakeholder update

```
"Give me a summary of the Platform team's progress this week:
- Tickets completed
- Tickets in progress
- Any blockers
Format it for my stakeholder update email."
```

---

## Confluence Use Cases

### 1. Documentation Search

**Scenario:** Finding relevant documentation quickly

```
"Search Confluence for documentation about our authentication API. 
Summarize what you find and identify any gaps."
```

### 2. PRD Publishing

**Scenario:** Publishing a PRD to Confluence

```
"Take this PRD I've written and publish it to Confluence in the 
Platform team space. Add it to the 2024 Roadmap parent page."
```

### 3. Meeting Notes

**Scenario:** Creating structured meeting notes

```
"Create a meeting notes page in Confluence for today's sprint retrospective.
Include sections for:
- What went well
- What could improve
- Action items
Add the Platform team as watchers."
```

### 4. Decision Documentation

**Scenario:** Recording architectural decisions

```
"Create an ADR (Architecture Decision Record) in Confluence for our 
decision to use PostgreSQL over MongoDB for the analytics service. 
Include the context, options considered, and rationale."
```

---

## GitHub Use Cases

### 1. Issue Tracking

**Scenario:** Understanding project status

```
"Show me all open issues in the platform-core repo labeled 'bug'. 
Which ones are oldest? Which are assigned vs unassigned?"
```

### 2. PR-Based Release Notes

**Scenario:** Creating release notes from merged PRs

```
"Generate release notes for v2.5.0 based on all PRs merged since v2.4.0.
Categorize by type (feature, fix, chore) based on PR labels or 
conventional commit prefixes."
```

### 3. Issue Triage

**Scenario:** Triaging incoming issues

```
"Look at issues created in the last week. Suggest labels and priorities 
based on the issue content. Flag any that seem like duplicates."
```

### 4. PR Review Analysis

**Scenario:** Understanding team velocity

```
"Analyze PR activity for the Platform team this month:
- Average time to first review
- Average time to merge
- Any PRs stuck without review for >3 days"
```

---

## Cross-Tool Workflows

### 1. Feature Lifecycle Tracking

**Scenario:** Tracking a feature from spec to release

```
"For the 'Advanced Search' feature:
1. Find the PRD in Confluence
2. Show me all related Jira tickets and their status
3. Show me related GitHub PRs
Give me a unified status view."
```

### 2. Sprint-to-Release Pipeline

**Scenario:** Connecting sprint work to releases

```
"For Sprint 45:
1. Get all completed Jira tickets
2. Find the GitHub PRs associated with them
3. Generate a release checklist and changelog
4. Create a release notes draft in Confluence"
```

### 3. Incident Post-Mortem

**Scenario:** Documenting an incident

```
"For yesterday's auth service incident:
1. Create a post-mortem page in Confluence
2. Create follow-up Jira tickets for the action items
3. Create GitHub issues for any code changes needed
Link everything together."
```

---

## Tips for Effective MCP Usage

### Be Specific
```
❌ "Show me tickets"
✅ "Show me open tickets in the AUTH epic assigned to the Platform team"
```

### Provide Context
```
❌ "Create a ticket for this"
✅ "Create a Jira ticket for implementing SSO login. This is part of 
    the Auth Improvements epic. Priority is High because it's blocking 
    the enterprise deal."
```

### Chain Actions
```
"After creating the ticket, also:
1. Add it to the current sprint
2. Create a Confluence page for the technical spec
3. Link them together"
```

### Review Before Confirming
Most MCP operations that modify data will ask for confirmation. Always review:
- Ticket content and fields
- Page structure and location
- Assignments and notifications

---

## Building Your Own Workflows

Think about your repetitive tasks:

1. **What do you do every day/week?**
   - Sprint updates
   - Ticket grooming
   - Documentation updates

2. **What takes multiple tool switches?**
   - Cross-referencing Jira and GitHub
   - Creating connected docs and tickets

3. **What's tedious but important?**
   - Release notes
   - Status reports
   - Audit trails

These are prime candidates for MCP automation.

