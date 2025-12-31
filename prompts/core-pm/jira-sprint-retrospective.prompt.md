# Jira Sprint Retrospective Analysis

Analyze sprint performance using Jira data to identify patterns, bottlenecks, and improvement opportunities.

## Usage

Replace the `[PLACEHOLDERS]` with your specific information.

---

## Prompt

```
You are an experienced Product Manager helping me analyze sprint performance for a retrospective.

## Sprint Context
- Sprint Name/Number: [e.g., Sprint 45]
- Sprint Duration: [e.g., 2 weeks]
- Team Size: [NUMBER OF DEVELOPERS]
- Planned Capacity: [STORY POINTS OR HOURS PLANNED]
- Actual Completed: [STORY POINTS OR HOURS COMPLETED]

## Jira Data
[PASTE JIRA DATA OR DESCRIBE WHAT YOU HAVE]

Or provide:
- Project: [PROJECT KEY]
- Sprint: [SPRINT NAME/NUMBER]
- JQL Query Results: [IF YOU HAVE QUERY RESULTS]

## Focus Areas
[OPTIONAL - WHAT TO ANALYZE]
- Velocity trends
- Blocked work
- Scope changes
- Bug rates
- Cycle time
- Other: [SPECIFY]

## Instructions

Analyze the sprint and provide:

### 1. Sprint Summary
- **Planned vs. Completed:** [Comparison]
- **Velocity:** [Story points completed]
- **Completion Rate:** [Percentage of planned work completed]
- **Scope Changes:** [Items added/removed mid-sprint]

### 2. Issue Analysis

**By Status:**
- Completed: [COUNT AND PERCENTAGE]
- In Progress (not done): [COUNT]
- Blocked: [COUNT AND DURATION]
- Deferred: [COUNT AND REASON]

**By Type:**
- Stories: [COMPLETED/TOTAL]
- Bugs: [COMPLETED/TOTAL]
- Tasks: [COMPLETED/TOTAL]

**By Priority:**
- P0/P1 completed: [COUNT]
- P2 deferred: [COUNT]

### 3. Performance Metrics

**Cycle Time:**
- Average time from "In Progress" to "Done": [DAYS]
- Longest cycle time: [TICKET AND DAYS]
- Shortest cycle time: [TICKET AND DAYS]

**Blocked Work:**
- Total blocked time: [HOURS/DAYS]
- Most common blocker: [CATEGORY]
- Impact: [HOW IT AFFECTED SPRINT]

**Scope Creep:**
- Items added mid-sprint: [COUNT AND POINTS]
- Items removed: [COUNT AND POINTS]
- Net change: [POINTS]

### 4. Patterns & Insights

**What Went Well:**
- [Pattern 1]: [Evidence and impact]
- [Pattern 2]: [Evidence and impact]

**What Didn't Go Well:**
- [Issue 1]: [Evidence and impact]
- [Issue 2]: [Evidence and impact]

**Bottlenecks:**
- [Bottleneck 1]: [Where work got stuck]
- [Bottleneck 2]: [Where work got stuck]

**Surprises:**
- [Unexpected event 1]: [Impact]
- [Unexpected event 2]: [Impact]

### 5. Root Cause Analysis

For each major issue, identify:
- **Symptom:** [What we observed]
- **Root Cause:** [Why it happened]
- **Impact:** [How it affected the sprint]
- **Frequency:** [Is this recurring?]

### 6. Action Items

**Immediate Actions (Next Sprint):**
- [Action 1]: [Owner] - [Due date]
- [Action 2]: [Owner] - [Due date]

**Process Improvements:**
- [Improvement 1]: [What to change]
- [Improvement 2]: [What to change]

**Experiments to Try:**
- [Experiment 1]: [Hypothesis and how to test]
- [Experiment 2]: [Hypothesis and how to test]

### 7. Recommendations

**For Next Sprint Planning:**
- Capacity adjustment: [Recommendation based on this sprint]
- Risk mitigation: [How to avoid similar issues]
- Process changes: [What to do differently]

**For Team:**
- Skills/Knowledge gaps: [What to address]
- Tool improvements: [What would help]
- Communication improvements: [What to change]

---

Use data to support insights. If data is missing, note what would be helpful to track.
```

---

## Quick Version

```
Analyze this sprint's performance:

Sprint: [SPRINT NAME]
Planned: [X points]
Completed: [Y points]

Key issues:
[LIST ANY MAJOR ISSUES]

Provide:
- What went well
- What didn't go well
- Root causes
- Action items for next sprint
```

---

## Example Input

```
Sprint Context:
- Sprint Name: Sprint 45
- Sprint Duration: 2 weeks
- Team Size: 6 developers
- Planned Capacity: 50 story points
- Actual Completed: 38 story points

Jira Data:
- Project: PLATFORM
- Sprint: Sprint 45
- Completed: 12 stories (38 points), 3 bugs (5 points), 2 tasks (3 points)
- Not Completed: 4 stories (15 points) - 2 blocked, 2 deferred
- Blocked Issues: PLATFORM-201 (blocked for 3 days), PLATFORM-205 (blocked for 2 days)
- Scope Changes: Added PLATFORM-220 (5 points) mid-sprint, removed PLATFORM-215 (8 points)

Focus Areas:
- Blocked work analysis
- Why we didn't hit velocity target
- Cycle time patterns
```

## Example Output

### 1. Sprint Summary

- **Planned vs. Completed:** 50 points planned, 38 points completed (76% completion rate)
- **Velocity:** 38 story points (below target of 50)
- **Completion Rate:** 76% of planned work
- **Scope Changes:** 
  - Added: PLATFORM-220 (5 points) - urgent bug fix
  - Removed: PLATFORM-215 (8 points) - deferred due to dependency
  - Net: -3 points (effectively 47 points planned, 38 completed = 81% of adjusted plan)

### 2. Issue Analysis

**By Status:**
- Completed: 17 issues (38 points) - 81% of issues
- In Progress (not done): 2 issues (8 points)
- Blocked: 2 issues (7 points) - total 5 days of blocked time
- Deferred: 2 issues (7 points) - moved to next sprint

**By Type:**
- Stories: 12 completed (38 points) / 16 total (53 points) = 72% completion
- Bugs: 3 completed (5 points) / 3 total (5 points) = 100% completion
- Tasks: 2 completed (3 points) / 2 total (3 points) = 100% completion

**By Priority:**
- P0/P1 completed: 15 issues (35 points)
- P2 deferred: 2 issues (7 points)

### 3. Performance Metrics

**Cycle Time:**
- Average time from "In Progress" to "Done": 4.2 days
- Longest cycle time: PLATFORM-201 (8 days) - was blocked for 3 days
- Shortest cycle time: PLATFORM-210 (1.5 days) - straightforward bug fix

**Blocked Work:**
- Total blocked time: 5 days (2 issues × 2.5 days average)
- Most common blocker: External API dependency (PLATFORM-201 waiting on third-party service)
- Impact: Lost ~7 story points of capacity, delayed 2 stories to next sprint

**Scope Creep:**
- Items added mid-sprint: 1 item (PLATFORM-220, 5 points) - production bug
- Items removed: 1 item (PLATFORM-215, 8 points) - dependency not ready
- Net change: -3 points (but added urgent work that disrupted flow)

### 4. Patterns & Insights

**What Went Well:**
- **Bug fixes completed quickly:** All 3 bugs (5 points) completed with average 2-day cycle time
- **High completion on tasks:** 100% of planned tasks completed
- **Team collaboration:** Pair programming on complex stories reduced rework

**What Didn't Go Well:**
- **Blocked work:** 2 stories blocked for 5 total days, reducing effective capacity
- **Scope change disruption:** Mid-sprint production bug (PLATFORM-220) disrupted planned work
- **Underestimated complexity:** PLATFORM-201 took 8 days vs. estimated 5 points (should have been 8 points)

**Bottlenecks:**
- **External dependencies:** PLATFORM-201 blocked waiting on third-party API documentation (3 days)
- **Code review queue:** 2 stories waited 1+ days for review, slowing cycle time
- **QA capacity:** Limited QA availability delayed sign-off on 3 stories

**Surprises:**
- **Production bug:** Unexpected critical bug (PLATFORM-220) required immediate attention
- **API complexity:** PLATFORM-201 revealed more integration complexity than anticipated

### 5. Root Cause Analysis

**Issue: Blocked Work (External Dependencies)**
- **Symptom:** PLATFORM-201 blocked for 3 days waiting on third-party API docs
- **Root Cause:** Assumed API documentation would be available; didn't verify before sprint start
- **Impact:** Delayed story completion, reduced sprint velocity by ~3 points
- **Frequency:** First time this sprint, but similar issues in Sprint 43

**Issue: Scope Change Disruption**
- **Symptom:** Production bug (PLATFORM-220) added mid-sprint, disrupted planned work
- **Root Cause:** No buffer for urgent work; sprint plan was too tight
- **Impact:** Team context-switched, 2 stories deferred
- **Frequency:** Happens ~1-2 times per quarter

**Issue: Code Review Bottleneck**
- **Symptom:** Stories waited 1+ days for code review
- **Root Cause:** Reviewers busy with their own work; no dedicated review time
- **Impact:** Increased cycle time, delayed deployments
- **Frequency:** Recurring issue across multiple sprints

### 6. Action Items

**Immediate Actions (Next Sprint):**
- **Verify external dependencies before sprint start** - [Tech Lead] - Before Sprint 46 planning
- **Reserve 10% capacity buffer for urgent work** - [PM] - Sprint 46 planning
- **Schedule dedicated code review time slots** - [Engineering Manager] - Week 1 of Sprint 46

**Process Improvements:**
- **Dependency checklist:** Add "Verify external dependencies available" to sprint planning checklist
- **Review process:** Implement "review within 4 hours" SLA with rotation schedule
- **Scope change process:** Require PM + Tech Lead approval for mid-sprint additions

**Experiments to Try:**
- **Dedicated review day:** Try "Review Thursday" where team focuses on reviews
- **Dependency pre-work:** Start dependency verification 1 week before sprint
- **Buffer allocation:** Reserve 5-10 points per sprint for urgent/unplanned work

### 7. Recommendations

**For Next Sprint Planning:**
- **Capacity adjustment:** Plan for 45 points (90% of 50) to account for buffer and learnings
- **Risk mitigation:** 
  - Verify all external dependencies are available before committing
  - Add buffer stories that can be dropped if urgent work comes in
- **Process changes:**
  - Start dependency verification earlier
  - Include "urgent work" as a planned risk in sprint planning

**For Team:**
- **Skills/Knowledge gaps:** 
  - API integration best practices workshop (address PLATFORM-201 complexity)
  - Code review efficiency training
- **Tool improvements:**
  - Jira automation to flag stories blocked >1 day
  - Slack notifications for code review requests
- **Communication improvements:**
  - Daily standup focus on blockers (not just status)
  - Weekly dependency check-in with external teams

---

## Tips

- **Use data, not opinions** - Let Jira metrics guide the analysis
- **Focus on patterns** - One-off issues are less important than recurring problems
- **Be specific** - "Code reviews are slow" is less useful than "Average review wait time is 1.5 days"
- **Actionable items** - Every insight should lead to a concrete action
- **Celebrate wins** - Don't just focus on problems; highlight what worked
- **Track over time** - Compare metrics across sprints to see trends

