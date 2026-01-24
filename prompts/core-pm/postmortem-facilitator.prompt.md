# Postmortem Facilitator

Guide blameless postmortems and generate structured incident reports with root cause analysis and action items.

## Usage

Replace the `[PLACEHOLDERS]` with your specific information.

---

## Prompt

```
You are an experienced incident manager helping me facilitate a blameless postmortem.

## Incident Context
- Incident Title: [BRIEF DESCRIPTION]
- Incident ID: [IF YOU HAVE ONE]
- Severity: [SEV1/SEV2/SEV3/SEV4 or Critical/High/Medium/Low]
- Date/Time: [WHEN IT OCCURRED]
- Duration: [HOW LONG IT LASTED]
- Services Affected: [WHAT WAS IMPACTED]
- Customer Impact: [HOW USERS WERE AFFECTED]

## Timeline
[PASTE RAW INCIDENT TIMELINE, SLACK LOGS, OR DESCRIBE WHAT HAPPENED]

## Additional Context
- Who was involved: [RESPONDERS]
- Related changes: [DEPLOYMENTS, CONFIG CHANGES, ETC.]
- Previous related incidents: [IF THIS HAS HAPPENED BEFORE]
- Monitoring/alerting behavior: [DID ALERTS FIRE? WHEN?]

## Instructions

Generate a comprehensive postmortem document:

### 1. Incident Summary
**One-line summary:** [What happened in plain language]

**Impact:**
- Duration: [Total time]
- Users affected: [Number or percentage]
- Revenue impact: [If applicable]
- SLA impact: [If applicable]

**Severity Justification:** [Why this severity level]

### 2. Timeline
| Time (UTC) | Event | Actor | Notes |
|------------|-------|-------|-------|
| [Time] | [What happened] | [Who/what] | [Context] |

**Key Moments:**
- Detection: [When and how we noticed]
- Response: [When response began]
- Mitigation: [When bleeding stopped]
- Resolution: [When fully resolved]

### 3. Root Cause Analysis

**What Happened (Facts):**
[Objective description of the sequence of events]

**Why It Happened (Analysis):**

**5 Whys:**
1. Why did [immediate cause] happen?
   → Because [reason 1]
2. Why did [reason 1] happen?
   → Because [reason 2]
3. Why did [reason 2] happen?
   → Because [reason 3]
4. Why did [reason 3] happen?
   → Because [reason 4]
5. Why did [reason 4] happen?
   → Because [root cause]

**Contributing Factors:**
- [Factor 1]: How it contributed
- [Factor 2]: How it contributed
- [Factor 3]: How it contributed

**Root Cause:** [Single sentence identifying the fundamental issue]

### 4. What Went Well
- [Positive 1]: [Why this helped]
- [Positive 2]: [Why this helped]
- [Positive 3]: [Why this helped]

### 5. What Went Poorly
- [Issue 1]: [Impact on incident]
- [Issue 2]: [Impact on incident]
- [Issue 3]: [Impact on incident]

### 6. Where We Got Lucky
- [Lucky break 1]: [What could have been worse]
- [Lucky break 2]: [What could have been worse]

### 7. Action Items

**Immediate (This Week):**
| Action | Owner | Due Date | Priority | Tracking |
|--------|-------|----------|----------|----------|
| [Action] | @[Name] | [Date] | [P0/P1] | [Ticket #] |

**Short-term (This Quarter):**
| Action | Owner | Due Date | Priority | Tracking |
|--------|-------|----------|----------|----------|
| [Action] | @[Name] | [Date] | [P1/P2] | [Ticket #] |

**Long-term (Backlog):**
| Action | Owner | Priority | Notes |
|--------|-------|----------|-------|
| [Action] | @[Name] | [P2/P3] | [Context] |

**Action Item Categories:**
- 🔧 **Fix:** Directly addresses root cause
- 🛡️ **Prevent:** Stops similar incidents
- 🔍 **Detect:** Improves monitoring/alerting
- 📖 **Document:** Improves runbooks/procedures
- 🧪 **Test:** Adds testing/validation

### 8. Lessons Learned

**Technical Lessons:**
- [Lesson 1]
- [Lesson 2]

**Process Lessons:**
- [Lesson 1]
- [Lesson 2]

**Communication Lessons:**
- [Lesson 1]
- [Lesson 2]

### 9. Follow-up Questions

- [Question 1] - To be answered by: [Who]
- [Question 2] - Depends on: [What investigation]

### 10. Appendix

**Related Documents:**
- [Link to incident channel]
- [Link to metrics/dashboards]
- [Link to related tickets]

**Glossary:** [Define any technical terms for broader audience]

---

Remember: This is a blameless postmortem. Focus on systems and processes, not individuals. The goal is learning and improvement.
```

---

## Quick Version (Action Items Focus)

```
Generate postmortem action items for this incident:

Incident: [WHAT HAPPENED]
Root Cause: [WHY IT HAPPENED]
Duration: [HOW LONG]

Provide:
- 3-5 immediate actions (this week)
- 2-3 preventive measures (this quarter)
- Suggested owners for each
- Priority rankings
```

---

## Pre-Postmortem Prep

```
Help me prepare for a postmortem meeting:

Incident: [BRIEF DESCRIPTION]
Timeline: [KEY EVENTS]

Generate:
- Key questions to ask during the meeting
- Timeline template to fill in
- 5 Whys worksheet
- Discussion prompts for blameless reflection
```

---

## Example Input

```
Incident Context:
- Incident Title: API Gateway Timeout Storm
- Severity: SEV2
- Date/Time: 2024-01-15, 14:30 UTC
- Duration: 47 minutes
- Services Affected: All API endpoints
- Customer Impact: 30% of API requests failed with 504 errors

Timeline:
14:30 - First alerts fire for elevated 504 errors
14:35 - On-call engineer (Alex) acknowledges alert, starts investigating
14:40 - Alex notices database connection pool exhausted
14:45 - Rollback of 14:00 deployment attempted
14:50 - Rollback fails (deployment had DB migration)
14:55 - Alex escalates to database team, Sarah joins
15:00 - Sarah identifies long-running query from new feature
15:05 - Kill long-running queries manually
15:10 - Connection pool recovering
15:17 - All systems normal, monitoring continues

Additional Context:
- Related changes: Feature deployment at 14:00 included new analytics query
- Previous incidents: Similar connection pool issue 6 months ago
- Monitoring: Connection pool alert was set at 95%, fired at 14:32
```

## Example Output

### 1. Incident Summary

**One-line summary:** A new analytics query exhausted database connection pools, causing 47 minutes of API gateway timeouts affecting 30% of requests.

**Impact:**
- Duration: 47 minutes (14:30 - 15:17 UTC)
- Users affected: ~30% of API requests (estimated 50,000 failed requests)
- Revenue impact: Estimated $8,000 in failed transactions
- SLA impact: Monthly uptime dropped from 99.95% to 99.89%

**Severity Justification:** SEV2 - Significant customer impact (30% error rate) but not total outage; no data loss.

### 2. Timeline

| Time (UTC) | Event | Actor | Notes |
|------------|-------|-------|-------|
| 14:00 | Feature deployment with analytics query | Deploy Bot | Included DB migration |
| 14:28 | Connection pool reaches 90% | System | No alert at this threshold |
| 14:30 | 504 errors begin, connection pool at 100% | System | Queries start failing |
| 14:32 | PagerDuty alert fires (95% threshold) | Monitoring | 2-minute delay from start |
| 14:35 | Alex acknowledges, begins investigation | Alex | Looked at error logs first |
| 14:40 | Alex identifies connection pool exhaustion | Alex | Checked database metrics |
| 14:45 | Rollback attempted | Alex | Standard procedure |
| 14:50 | Rollback fails due to migration | Alex | Migration not reversible |
| 14:55 | Escalation to database team | Alex | Sarah paged |
| 15:00 | Long-running query identified | Sarah | Query from new feature |
| 15:05 | Queries killed manually | Sarah | 15 queries terminated |
| 15:10 | Connection pool recovering | System | Errors decreasing |
| 15:17 | All systems normal | System | Monitoring confirmed |

**Key Moments:**
- Detection: 14:32 (2 minutes after impact started)
- Response: 14:35 (3 minutes after alert)
- Mitigation: 15:05 (33 minutes to identify and kill queries)
- Resolution: 15:17 (47 minutes total)

### 3. Root Cause Analysis

**What Happened (Facts):**
A feature deployment at 14:00 included a new analytics query that performed a full table scan on user activity data. Under production load, this query took 30+ seconds to complete and held database connections. As queries accumulated, the connection pool (max 100 connections) was exhausted within 30 minutes, causing new requests to timeout.

**Why It Happened (Analysis):**

**5 Whys:**
1. Why did API requests timeout?
   → Because database connections were unavailable
2. Why were database connections unavailable?
   → Because the connection pool was exhausted
3. Why was the connection pool exhausted?
   → Because long-running queries were holding connections
4. Why were queries running so long?
   → Because a new analytics query did a full table scan
5. Why did the full table scan get to production?
   → Because query performance wasn't tested at production scale

**Contributing Factors:**
- No query timeout configured: Queries could run indefinitely
- Connection pool alert threshold too high: 95% meant little time to react
- No pre-production load testing: Query worked fine with test data
- Migration blocked rollback: Couldn't quickly revert the deployment

**Root Cause:** Untested analytics query performed full table scan, exhausting database connections under production load.

### 4. What Went Well
- Alert fired within 2 minutes of impact starting
- On-call engineer responded within 3 minutes
- Escalation to database team was quick and effective
- Manual query termination successfully mitigated impact
- Team communication in incident channel was clear

### 5. What Went Poorly
- No load testing caught the problematic query
- Rollback was blocked by database migration
- Took 25 minutes to identify the specific cause (14:35 - 15:00)
- Connection pool alert threshold (95%) left little reaction time
- No query timeout prevented runaway queries

### 6. Where We Got Lucky
- Query was killable without data corruption
- Database didn't crash despite connection pressure
- Incident happened during business hours with team available
- Only 30% of requests affected (could have been 100%)

### 7. Action Items

**Immediate (This Week):**
| Action | Owner | Due Date | Priority | Tracking |
|--------|-------|----------|----------|----------|
| 🔧 Add index to user_activity table | @Sarah | Jan 17 | P0 | PLATFORM-301 |
| 🛡️ Add 30-second query timeout to DB config | @Sarah | Jan 17 | P0 | PLATFORM-302 |
| 🔍 Lower connection pool alert to 80% | @Alex | Jan 16 | P0 | PLATFORM-303 |

**Short-term (This Quarter):**
| Action | Owner | Due Date | Priority | Tracking |
|--------|-------|----------|----------|----------|
| 🛡️ Add query EXPLAIN analysis to CI pipeline | @Pat | Feb 1 | P1 | PLATFORM-310 |
| 🛡️ Implement reversible migration pattern | @Morgan | Feb 15 | P1 | PLATFORM-311 |
| 🔍 Add connection pool usage dashboard | @Alex | Jan 31 | P1 | PLATFORM-312 |
| 📖 Update runbook for connection pool issues | @Alex | Jan 22 | P2 | PLATFORM-313 |

**Long-term (Backlog):**
| Action | Owner | Priority | Notes |
|--------|-------|----------|-------|
| 🧪 Implement production-scale load testing | @Platform Team | P2 | Requires test environment upgrade |
| 🛡️ Evaluate read replicas for analytics | @Sarah | P3 | Separate analytics from OLTP |

### 8. Lessons Learned

**Technical Lessons:**
- Query performance at scale can differ dramatically from development
- Database migrations can block rollbacks; consider reversibility
- Connection pools need headroom; alert early, not at capacity

**Process Lessons:**
- Load testing with production-like data would have caught this
- Query review should be part of code review for DB changes
- Having a database specialist on-call accelerates resolution

**Communication Lessons:**
- Incident channel updates were helpful; keep that practice
- Customer communication was delayed 20 minutes; could be faster

### 9. Follow-up Questions

- Should we implement a query review process for all new queries? - To be discussed: Platform team
- What's our tolerance for analytics query impact on OLTP? - To be discussed: Product + Engineering leads

### 10. Appendix

**Related Documents:**
- Incident Slack channel: #incident-2024-01-15-api-timeouts
- Database metrics dashboard: [link]
- Deployment record: [link]

**Glossary:**
- Connection pool: Cached database connections for reuse
- 504 error: Gateway timeout, typically means upstream server didn't respond
- OLTP: Online Transaction Processing (regular database operations)

---

## Blameless Postmortem Principles

1. **Focus on systems, not people** - "The deploy process allowed..." not "Alex deployed..."
2. **Assume good intent** - Everyone was trying to do the right thing
3. **Seek understanding** - "Why did this seem like the right thing to do?"
4. **Improve the system** - Make it harder to make mistakes, easier to recover
5. **Share learnings** - Incidents are learning opportunities for the whole organization

---

## Tips

- **Write it quickly** - Postmortems lose value if written weeks later
- **Involve the responders** - They have context no one else has
- **Be specific** - Vague action items don't get done
- **Assign owners** - Every action needs a single owner and due date
- **Follow up** - Track action items to completion
- **Share broadly** - The whole organization benefits from incident learnings
