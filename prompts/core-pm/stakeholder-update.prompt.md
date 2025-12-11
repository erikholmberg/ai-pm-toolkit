# Stakeholder Update Generator

Create clear, concise stakeholder updates tailored to different audiences.

## Usage

Replace the `[PLACEHOLDERS]` with your specific information.

---

## Executive Summary Prompt

```
You are helping me write a stakeholder update for executives. They have limited time and need the key points fast.

## Context
- Project/Initiative: [PROJECT NAME]
- Reporting Period: [e.g., Week of Dec 9, Q4 2024]
- Audience: [e.g., VP of Engineering, C-suite, Skip-level]

## Current Status
- Overall Status: [🟢 On Track / 🟡 At Risk / 🔴 Blocked]
- Key Accomplishments: [WHAT GOT DONE]
- Current Focus: [WHAT'S IN PROGRESS]
- Blockers/Risks: [WHAT COULD DERAIL US]
- Upcoming Milestones: [WHAT'S NEXT]

## Metrics (if applicable)
- [METRIC 1]: [VALUE] ([TREND: up/down/flat])
- [METRIC 2]: [VALUE] ([TREND])

## Asks (if any)
- [DECISIONS NEEDED / RESOURCES REQUESTED]

---

## Instructions

Write a stakeholder update following this structure:

### Format
1. **TL;DR** (2 sentences max) - Overall status and the one thing they need to know
2. **Progress** (3-5 bullets) - What got done, with specific metrics where possible
3. **Risks & Blockers** (2-3 bullets) - Be honest about challenges
4. **Next Steps** (2-3 bullets) - What's coming, with dates
5. **Asks** (if any) - Specific, actionable requests

### Guidelines
- Lead with the most important information
- Use specific numbers, not vague language ("increased 23%" not "improved significantly")
- Keep it under 200 words total
- Use bullet points, not paragraphs
- Bold key terms for scanability
- If status is yellow or red, put the reason first
```

---

## Weekly Team Update Prompt

```
Help me write a weekly update for my cross-functional team.

## Context
- Project: [PROJECT NAME]
- Week: [DATE RANGE]
- Team: [ENGINEERING, DESIGN, DATA, etc.]

## This Week
- Completed: [LIST ITEMS]
- In Progress: [LIST ITEMS]
- Blocked: [LIST ITEMS]

## Key Decisions Made
- [DECISION 1]
- [DECISION 2]

## Open Questions
- [QUESTION 1]
- [QUESTION 2]

## Next Week
- [PLANNED ITEM 1]
- [PLANNED ITEM 2]

---

Write a friendly but professional team update. Include:
1. Quick wins worth celebrating
2. Progress against milestones
3. Blockers that need help
4. Shoutouts (if any)
5. Focus areas for next week

Keep it scannable - people will read this in 60 seconds.
```

---

## Monthly Business Review Prompt

```
Help me prepare a monthly business review update for leadership.

## Context
- Product/Area: [PRODUCT NAME]
- Month: [MONTH YEAR]
- Business Goals: [WHAT WE'RE TRYING TO ACHIEVE]

## Metrics
| Metric | Target | Actual | Trend | Notes |
|--------|--------|--------|-------|-------|
| [METRIC] | [TARGET] | [ACTUAL] | [↑/↓/→] | [CONTEXT] |

## Key Accomplishments
- [ACCOMPLISHMENT 1]
- [ACCOMPLISHMENT 2]

## Misses / Learnings
- [WHAT DIDN'T GO WELL AND WHY]

## Strategic Initiatives Status
- [INITIATIVE 1]: [STATUS]
- [INITIATIVE 2]: [STATUS]

## Resource/Budget Status
- [CURRENT STATE]

## Next Month Priorities
1. [PRIORITY 1]
2. [PRIORITY 2]

---

Write a monthly business review that:
1. Tells the story of the month (not just data)
2. Connects metrics to business impact
3. Is honest about misses and learnings
4. Shows clear prioritization for next month
5. Highlights any decisions or support needed

Use a narrative structure: What happened → Why it matters → What's next
```

---

## Tips

- **Know your audience** - Execs want outcomes, teams want details
- **Status colors matter** - Don't default to green; build trust with honest yellows
- **Metrics without context are noise** - Always explain what the number means
- **Asks should be specific** - "I need X by Y to unblock Z"
- **Celebrate wins** - Teams need to see progress acknowledged

