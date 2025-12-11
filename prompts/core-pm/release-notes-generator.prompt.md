# Release Notes Generator

Transform technical changelogs into user-friendly release communications.

## Usage

Replace the `[PLACEHOLDERS]` with your specific information.

---

## Technical to User-Friendly Release Notes

```
You are a product communications expert. Transform this technical changelog into user-friendly release notes.

## Context
- Product: [PRODUCT NAME]
- Version/Release: [VERSION OR DATE]
- Audience: [e.g., "Developers using our API", "Enterprise admins", "End users"]
- Tone: [e.g., "Professional but friendly", "Technical", "Casual"]

## Technical Changelog
---
[PASTE YOUR TECHNICAL CHANGELOG, PR DESCRIPTIONS, OR JIRA TICKETS]

Example:
- FEAT-1234: Implemented batch processing for /api/v2/ingest endpoint
- BUG-5678: Fixed race condition in queue processor causing duplicate events
- PERF-9012: Optimized DB queries in reporting module (3x improvement)
- CHORE-3456: Upgraded to Node 20, updated dependencies
---

## Instructions

Transform into release notes with:

### 1. Headline
A compelling one-liner that captures the most important change.

### 2. TL;DR
2-3 sentences summarizing what's new and why it matters.

### 3. ✨ New Features
For each new feature:
- **Feature Name:** User-friendly name
- **What it does:** One sentence, no jargon
- **Why it matters:** User benefit
- **How to use it:** Quick start instructions or link

### 4. 🔧 Improvements
- Focus on user impact, not technical details
- Group related improvements together

### 5. 🐛 Bug Fixes
- Describe what users experienced, not what was broken internally
- "Fixed an issue where..." format

### 6. ⚠️ Breaking Changes (if any)
- Clear description of what changed
- Migration steps
- Timeline/deprecation notice

### 7. 📚 Documentation
- Links to updated docs
- New guides or tutorials

### 8. 🙏 Thanks
- Acknowledge community contributions if applicable

---

## Formatting Guidelines
- Use active voice ("You can now..." not "It is now possible to...")
- Lead with benefits, not features
- Include links to docs/help articles
- Use emojis sparingly but effectively for scanability
- Keep technical details in collapsible sections if needed
```

---

## Internal Release Notes (Engineering → PM/Stakeholders)

```
Help me translate this engineering release into an internal stakeholder summary.

## Technical Release Notes
---
[PASTE ENGINEERING RELEASE NOTES OR PR LIST]
---

## Create an internal summary that:

### 1. Business Impact Summary
- What does this enable for customers?
- What risks does this mitigate?
- What metrics should we expect to change?

### 2. Customer-Facing Changes
- What will customers notice?
- Any behavior changes?

### 3. Operational Changes
- New monitoring/alerts?
- New runbooks needed?
- Support implications?

### 4. Dependencies Resolved/Created
- What was this blocked on?
- What does this unblock?

### 5. Outstanding Items
- What's deferred to next release?
- Known limitations?

### 6. Rollout Plan
- Staged rollout details
- Rollback triggers

Keep it concise - this is for cross-functional alignment, not customer comms.
```

---

## Email Announcement Generator

```
Create an email announcement for this release.

## Context
- Product: [PRODUCT NAME]  
- Audience: [e.g., "All users", "Enterprise customers", "Beta users"]
- Release Type: [Major/Minor/Patch]
- Key Message: [WHAT'S THE ONE THING THEY SHOULD KNOW]

## Release Details
---
[PASTE YOUR RELEASE NOTES OR CHANGELOG]
---

## Generate an email with:

**Subject Line Options** (provide 3)

**Email Body:**
- Hook (why this matters to them)
- What's new (key highlights, not exhaustive)
- How to access/enable new features
- Clear CTA
- Link to full release notes

**Design Notes:**
- Suggest header image concept
- Recommend screenshots/GIFs to include

Keep it under 200 words. Most people skim.
```

---

## Changelog Entry Prompt

```
Help me write a changelog entry for our developer documentation.

## Change Details
- What changed: [DESCRIPTION]
- API version: [IF APPLICABLE]
- Date: [RELEASE DATE]
- Type: [Added/Changed/Deprecated/Removed/Fixed/Security]

## Technical Details
---
[PASTE TECHNICAL DETAILS, CODE EXAMPLES, ETC.]
---

## Generate a changelog entry that:
1. Uses Keep a Changelog format
2. Includes code examples where helpful
3. Shows before/after if behavior changed
4. Links to relevant API docs
5. Notes any migration required

Format example:
### [1.2.0] - 2024-12-15
#### Added
- New batch processing endpoint `/api/v2/batch` for bulk operations
  - Supports up to 1000 items per request
  - See [Batch Processing Guide](/docs/batch)
```

---

## Tips

- **Lead with value, not version numbers** - "Faster exports" beats "v2.3.4"
- **Test your notes** - Have someone non-technical read them
- **Use consistent formatting** - Readers learn to scan your format
- **Include links** - Let people go deeper if they want
- **Time it right** - Don't announce on Friday afternoon
- **Segment if needed** - Different audiences may need different notes

