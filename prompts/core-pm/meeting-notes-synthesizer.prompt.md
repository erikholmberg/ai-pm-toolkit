# Meeting Notes Synthesizer

Transform meeting transcripts or rough notes into structured summaries with action items, decisions, and owners.

## Usage

Replace the `[PLACEHOLDERS]` with your specific information.

---

## Prompt

```
You are an experienced Product Manager helping me synthesize meeting notes into a clear, actionable summary.

## Meeting Context
- Meeting Type: [e.g., Sprint Planning, Stakeholder Review, Design Review, 1:1, Team Standup]
- Date: [MEETING DATE]
- Attendees: [LIST OF PARTICIPANTS]
- Meeting Goal: [WHAT WAS THIS MEETING SUPPOSED TO ACCOMPLISH]

## Raw Notes / Transcript
[PASTE YOUR MEETING NOTES, TRANSCRIPT, OR KEY POINTS HERE]

## Instructions

Synthesize the meeting into this structure:

### Meeting Summary
**One-line summary:** [What was this meeting about in one sentence]

**Key Topics Discussed:**
1. [Topic 1] - [Brief summary]
2. [Topic 2] - [Brief summary]
3. [Topic 3] - [Brief summary]

### Decisions Made
| Decision | Context | Made By | Date |
|----------|---------|---------|------|
| [Decision 1] | [Why this decision was made] | [Who decided] | [Date] |
| [Decision 2] | [Why this decision was made] | [Who decided] | [Date] |

### Action Items
| Action | Owner | Due Date | Priority | Status |
|--------|-------|----------|----------|--------|
| [Action 1] | @[Name] | [Date] | [High/Medium/Low] | [ ] Not Started |
| [Action 2] | @[Name] | [Date] | [High/Medium/Low] | [ ] Not Started |

### Open Questions
- [Question 1] - Assigned to: [Name] to follow up
- [Question 2] - Needs discussion in: [Next meeting/Slack/etc.]

### Parking Lot
[Topics raised but deferred for later discussion]
- [Topic 1] - Will discuss in: [When/Where]
- [Topic 2] - Blocked by: [What needs to happen first]

### Key Quotes / Context
[Notable statements that provide important context]
> "[Quote]" - [Person]

### Next Steps
- [What happens next]
- [When is the next meeting/checkpoint]

### Follow-up Meeting
- **Needed:** [Yes/No]
- **Topic:** [If yes, what to discuss]
- **Suggested attendees:** [Who should be there]

---

Be concise but complete. Prioritize action items and decisions. Flag any unclear ownership or missing deadlines.
```

---

## Quick Version (Action Items Only)

```
Extract action items from these meeting notes:

[PASTE NOTES]

For each action item, provide:
- Task description
- Owner (or flag if unclear)
- Due date (or flag if not specified)
- Priority (High/Medium/Low based on context)
```

---

## Standup Summary Version

```
Summarize this standup meeting:

[PASTE STANDUP NOTES]

Format as:
**Yesterday:** [Key accomplishments]
**Today:** [Planned work]
**Blockers:** [Issues needing attention]
**Action Items:** [If any arose during standup]
```

---

## Example Input

```
Meeting Type: Sprint Planning
Date: 2024-01-15
Attendees: Sarah (PM), Alex (Tech Lead), Jordan (Design), Pat (Dev), Morgan (Dev)
Meeting Goal: Plan Sprint 46 and align on priorities

Raw Notes:
- Sarah opened by reviewing sprint 45 velocity (38 points, target was 50)
- Discussed why we missed - Alex mentioned the API dependency blocked PLATFORM-201 for 3 days
- Jordan brought up the notification preferences designs are ready for review
- Pat asked about the analytics dashboard priority - Sarah said it's P2 for now
- Morgan volunteered to take the performance optimization ticket
- Alex suggested we reduce capacity to 45 points this sprint given the learnings
- Sarah agreed and said we need to verify all external dependencies before committing
- Discussion about whether to include the Slack integration - decided to defer to Sprint 47
- Jordan needs design review from Sarah by Wednesday
- Pat will pair with Morgan on the notification integration
- Next sprint demo is Friday Jan 26
- Alex will create the dependency verification checklist before planning
```

## Example Output

### Meeting Summary
**One-line summary:** Sprint 46 planning session where team adjusted capacity based on Sprint 45 learnings and committed to dependency verification.

**Key Topics Discussed:**
1. Sprint 45 retrospective - Missed velocity target (38/50 points) due to API dependency blockers
2. Sprint 46 capacity - Reduced target to 45 points based on learnings
3. Prioritization - Analytics dashboard deferred to P2, Slack integration pushed to Sprint 47

### Decisions Made
| Decision | Context | Made By | Date |
|----------|---------|---------|------|
| Reduce Sprint 46 capacity to 45 points | Sprint 45 missed target due to blockers; need buffer | Sarah + Alex | 2024-01-15 |
| Defer Slack integration to Sprint 47 | Current sprint focused on notification preferences | Sarah | 2024-01-15 |
| Analytics dashboard is P2 priority | Other work takes precedence this sprint | Sarah | 2024-01-15 |

### Action Items
| Action | Owner | Due Date | Priority | Status |
|--------|-------|----------|----------|--------|
| Create dependency verification checklist | @Alex | Before Sprint 46 planning | High | [ ] Not Started |
| Complete design review for notification preferences | @Sarah | Wed Jan 17 | High | [ ] Not Started |
| Pair on notification integration | @Pat + @Morgan | Sprint 46 | Medium | [ ] Not Started |
| Prepare sprint demo | @Team | Fri Jan 26 | Medium | [ ] Not Started |

### Open Questions
- None explicitly raised

### Parking Lot
- Slack integration - Will discuss in Sprint 47 planning
- Analytics dashboard detailed requirements - Deferred until P1 work is complete

### Key Quotes / Context
> "We need to verify all external dependencies before committing" - Sarah (key learning from Sprint 45)

### Next Steps
- Alex creates dependency verification checklist
- Team finalizes Sprint 46 backlog using 45-point capacity
- Sprint demo scheduled for Friday Jan 26

### Follow-up Meeting
- **Needed:** No (regular sprint ceremonies continue)
- **Topic:** N/A
- **Suggested attendees:** N/A

---

## Tips

- **Capture decisions explicitly** - Many meetings have implicit decisions that need to be documented
- **Flag unclear ownership** - If an action item doesn't have a clear owner, note it
- **Include context** - Why a decision was made is often as important as what was decided
- **Prioritize ruthlessly** - Not everything discussed needs to be in the summary
- **Use @ mentions** - Makes it easy to search for your action items later
- **Time-bound actions** - If no deadline was mentioned, flag it or suggest one
