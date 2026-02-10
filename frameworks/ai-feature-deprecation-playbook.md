# AI Feature Deprecation Playbook

A structured playbook for deprecating AI-powered features, models, or capabilities. AI products evolve faster than traditional software — models get replaced, features sunset, pricing tiers restructure. This playbook ensures deprecations are planned, communicated, and executed without breaking trust.

---

## Overview

```
┌──────────────────────────────────────────────────────────────────────┐
│                    Deprecation Lifecycle                              │
├──────────┬──────────┬──────────┬──────────┬──────────┬──────────────┤
│ Decide   │ Plan     │ Announce │ Migrate  │ Sunset   │ Post-Mortem  │
│          │          │          │          │          │              │
│ Should   │ Timeline │ Comms    │ Support  │ Turn     │ Review &     │
│ we       │ Rollback │ Docs     │ Users    │ Off      │ Learn        │
│ do this? │ Fallback │ FAQ      │ Moving   │          │              │
└──────────┴──────────┴──────────┴──────────┴──────────┴──────────────┘
     1          2          3          4          5           6
```

---

## Stage 1: Decide — Should We Deprecate?

### Decision Criteria

Not every aging feature should be deprecated. Evaluate before committing.

| Criterion | Keep It | Deprecate It |
|-----------|---------|-------------|
| **Usage** | Significant active usage, even if declining | <5% of users, declining trend |
| **Revenue impact** | Meaningful revenue tied to feature | Minimal revenue; cost exceeds value |
| **Replacement ready** | No adequate replacement exists | Superior alternative is available |
| **Maintenance cost** | Low ongoing cost, stable | High cost, security risk, or blocking progress |
| **Strategic fit** | Aligns with product direction | Misaligned; creates confusion |
| **Contractual obligation** | Committed in customer contracts/SLAs | No binding commitments |
| **Technical debt** | Isolated, doesn't affect other systems | Blocks upgrades or creates fragility |

### Impact Assessment

Before proceeding, quantify the impact:

| Metric | Value | Source |
|--------|-------|--------|
| Monthly active users of feature | | Analytics |
| Revenue directly tied to feature | | Billing/Finance |
| API calls per month (if API) | | Monitoring |
| Integrations depending on feature | | Developer relations |
| Support tickets related to feature | | Support data |
| Engineering hours/month to maintain | | Engineering |

### Decision Record

```markdown
## Deprecation Decision: [FEATURE NAME]

**Date:** [DATE]
**Decision Owner:** [PM NAME]
**Decision:** [DEPRECATE / KEEP / DEFER]

**Why deprecate:**
- [Reason 1]
- [Reason 2]

**What replaces it:**
- [Replacement feature/approach]
- [Migration path summary]

**Impact:**
- Users affected: [NUMBER]
- Revenue at risk: [AMOUNT]
- Estimated migration effort (users): [LOW/MEDIUM/HIGH]
- Estimated engineering effort: [PERSON-WEEKS]

**Risks:**
- [Risk 1 and mitigation]
- [Risk 2 and mitigation]

**Approved by:** [STAKEHOLDERS]
```

---

## Stage 2: Plan — Timeline & Migration Path

### Deprecation Timeline

Minimum timelines by audience type:

| Audience | Minimum Notice | Recommended Notice | Notes |
|----------|---------------|-------------------|-------|
| Internal teams | 2 weeks | 4 weeks | Coordinate sprint planning |
| External API users (free) | 3 months | 6 months | Industry standard |
| External API users (paid) | 6 months | 12 months | Contractual obligations may extend |
| Enterprise customers | 6-12 months | 12+ months | Account-by-account planning |
| Partner integrations | 6 months | 12 months | Partners need to update their products |

### Timeline Template

| Date | Milestone | Action |
|------|-----------|--------|
| T-0 | Decision made | Internal alignment, begin planning |
| T+1 week | Internal announcement | Engineering, support, sales briefed |
| T+2 weeks | External announcement | Public deprecation notice |
| T+4 weeks | Migration guide published | Docs, code examples, FAQ live |
| Monthly | Progress check-ins | Track migration %, outreach to laggards |
| T+X-30 days | Final reminder | Direct outreach to remaining users |
| T+X-7 days | Last call notice | Urgent banner/email |
| T+X | Sunset date | Feature turned off |
| T+X+1 week | Grace period ends | Hard removal (if applicable) |
| T+X+2 weeks | Post-mortem | Review process, capture learnings |

### Migration Path Design

For every deprecation, define a clear migration path:

| From (Deprecated) | To (Replacement) | Migration Complexity | Automated? |
|-------------------|-------------------|---------------------|------------|
| [Old feature/API] | [New feature/API] | [Low/Medium/High] | [Yes/No/Partial] |

#### Migration Path Checklist

- [ ] Replacement feature is production-ready and stable
- [ ] Feature parity documented (what's equivalent, what's different, what's missing)
- [ ] Migration guide written with code examples (before/after)
- [ ] Automated migration tool built (if feasible)
- [ ] Eval comparison: old feature vs. new feature quality metrics
- [ ] Performance benchmarks: latency, throughput, cost comparison
- [ ] Data migration plan (if user data needs to move)
- [ ] Rollback plan: can users revert during migration window?

### Fallback Strategy

| Scenario | Fallback |
|----------|----------|
| Replacement has critical bug | Re-enable deprecated feature temporarily |
| Migration volume overwhelms support | Extend deadline by [X weeks] |
| Enterprise customer can't migrate in time | Individual extension (documented) |
| Quality regression in replacement | Revert to dual-running, investigate |

---

## Stage 3: Announce — Communication Plan

### Communication Matrix

| Audience | Channel | Timing | Owner |
|----------|---------|--------|-------|
| Internal engineering | Slack/email + meeting | T+1 week | PM |
| Internal support/CS | Training session + FAQ doc | T+1 week | PM + Support Lead |
| Internal sales | Briefing + objection handling doc | T+1 week | PM + Sales Lead |
| All external users | Email + in-app banner + blog post | T+2 weeks | PM + Marketing |
| Enterprise accounts | Personal outreach from CSM | T+2 weeks | Customer Success |
| Developer community | Docs update + changelog + forum post | T+2 weeks | DevRel |
| Partners | Direct notification + migration support | T+2 weeks | Partnerships |

### Communication Templates

#### External Deprecation Announcement

```
Subject: [PRODUCT]: [FEATURE] is being replaced by [NEW FEATURE] — action required by [DATE]

Hi [NAME],

We're writing to let you know that [FEATURE NAME] will be deprecated on [DATE].

**Why:** [1-2 sentences — honest reason: better replacement, unsustainable cost, 
security concern, strategic direction]

**What's replacing it:** [NEW FEATURE] offers [key improvements: faster, cheaper, 
more accurate, etc.]. [Link to comparison]

**What you need to do:**
1. [Specific action step 1]
2. [Specific action step 2]
3. [Specific action step 3]

**Timeline:**
- Now: Migration guide available at [LINK]
- [DATE]: Final reminder
- [DATE]: [FEATURE] will be turned off

**Need help?** 
- Migration guide: [LINK]
- FAQ: [LINK]  
- Contact us: [SUPPORT CHANNEL]

We know migrations take effort, and we're committed to making this as smooth 
as possible.

[SIGN OFF]
```

#### Internal Briefing Template

```markdown
## Deprecation Briefing: [FEATURE NAME]

**What's happening:** [FEATURE] is being deprecated on [DATE].
**Why:** [Reason]
**Replacement:** [NEW FEATURE]
**Users affected:** [NUMBER / SEGMENT]

### For Support:
- Expected ticket types: [migration help, feature comparison questions, deadline extensions]
- FAQ: [LINK]
- Escalation path: [WHO TO ESCALATE TO]
- Talking points for common objections: [LINK]

### For Sales:
- Impact on active deals: [ASSESSMENT]
- Talking points for prospects: [LINK]
- Competitive positioning: [HOW TO HANDLE]

### For Engineering:
- Sunset date: [DATE]
- Technical migration guide: [LINK]
- Monitoring: [WHAT TO WATCH]
- On-call considerations: [NOTES]
```

### In-App Deprecation Notices

Use progressive urgency:

| Timing | UI Treatment | Tone |
|--------|-------------|------|
| 6+ months out | Info banner (dismissable) | "Heads up — [Feature] is being replaced." |
| 3 months out | Warning banner (dismissable) | "Action needed — migrate to [New Feature] by [Date]." |
| 1 month out | Warning banner (persistent) | "⚠️ [Feature] will be removed on [Date]. Migrate now." |
| 1 week out | Alert modal on feature use | "This feature will stop working in 7 days. [Migrate now]" |
| After sunset | Error page with migration link | "[Feature] has been retired. [Switch to New Feature →]" |

---

## Stage 4: Migrate — Support Users Through the Transition

### Migration Tracking Dashboard

Track migration progress weekly:

| Metric | Target | Current | Status |
|--------|--------|---------|--------|
| % of users migrated | 100% by [DATE] | | |
| % of API traffic on old endpoint | 0% by [DATE] | | |
| Support tickets related to migration | < [N] per week | | |
| Enterprise accounts migrated | 100% by [DATE] | | |
| Migration guide page views | Increasing | | |

### Outreach Cadence for Non-Migrating Users

| % Migrated | Action |
|-----------|--------|
| < 25% at midpoint | Review migration guide, check for blockers, increase visibility |
| < 50% at 75% of timeline | Direct email to non-migrated users, in-app modal |
| < 75% at 90% of timeline | Personal outreach to top accounts, consider deadline extension |
| < 90% at deadline | CSM calls to remaining accounts, final extension decision |

### Handling Migration Objections

| Objection | Response | Escalation |
|-----------|----------|------------|
| "We don't have time to migrate" | Offer migration support, extend deadline if justified | PM decision on extension |
| "The new feature is missing X" | Log feature gap, assess if blocker, provide workaround | PM + Engineering |
| "We'll churn if you force this" | Assess revenue impact, offer extended grandfathering | PM + CS + Finance |
| "Our integration is complex" | Pair with solutions engineer, custom migration support | Engineering |
| "We never got notified" | Apologize, extend deadline, fix notification gap | PM + Ops |

---

## Stage 5: Sunset — Turn It Off

### Pre-Sunset Checklist (1 week before)

- [ ] Final migration numbers reviewed and acceptable
- [ ] Remaining users notified directly (email + in-app)
- [ ] Support team briefed on sunset-day procedures
- [ ] Monitoring dashboards updated for sunset
- [ ] Rollback mechanism tested (in case of emergency revert)
- [ ] Error responses configured for old endpoints/features
- [ ] Redirect or migration prompts in place for lingering users
- [ ] On-call team aware and briefed

### Sunset Day Procedures

1. **Disable feature** at planned time (prefer low-traffic window)
2. **Monitor** error rates, support tickets, and social media for 4 hours
3. **Confirm** old endpoints return helpful error messages with migration links
4. **Update** documentation to remove deprecated feature
5. **Notify** internal teams that sunset is complete

### Post-Sunset Error Handling

| Request Type | Response | Duration |
|-------------|----------|----------|
| API call to deprecated endpoint | `410 Gone` with migration URL in body | 6 months |
| UI navigation to deprecated feature | Redirect to replacement + explanation | 3 months |
| Webhook to deprecated URL | `410 Gone` + email to webhook owner | 3 months |

---

## Stage 6: Post-Mortem — Review & Learn

### Deprecation Review Template

```markdown
## Deprecation Review: [FEATURE NAME]

**Timeline:** [Announcement date] → [Sunset date]
**Users affected:** [NUMBER]
**Final migration rate:** [%] by sunset date

### What went well
- [e.g., Communication was clear, migration tool worked smoothly]

### What didn't go well
- [e.g., 15% of users hadn't migrated at deadline, required 2-week extension]

### Metrics
| Metric | Target | Actual |
|--------|--------|--------|
| Users migrated by deadline | 95% | [%] |
| Support tickets during migration | < 50 | [NUMBER] |
| Churn attributable to deprecation | < 1% | [%] |
| Engineering hours spent | [ESTIMATE] | [ACTUAL] |

### Lessons learned
1. [Lesson 1]
2. [Lesson 2]

### Recommendations for next deprecation
1. [Recommendation 1]
2. [Recommendation 2]
```

---

## AI-Specific Deprecation Scenarios

### Deprecating a Model Version

| Consideration | Guidance |
|--------------|----------|
| **Quality comparison** | Publish eval results: old model vs. new model on representative benchmarks |
| **Output format changes** | If outputs differ in format/structure, provide a compatibility layer |
| **Prompt migration** | Prompts optimized for old model may need adjustment; provide guidance |
| **Cost changes** | New model may cost more or less per request; be transparent about pricing impact |
| **Latency changes** | Benchmark and publish latency comparison |
| **Edge case regressions** | Document known regressions honestly; provide workarounds |

### Deprecating a Pricing Tier

| Consideration | Guidance |
|--------------|----------|
| **Grandfathering** | Decide grandfathering period (typically 6-12 months) |
| **Price increases** | Give maximum notice; industry standard is 60-90 days minimum |
| **Feature removal** | If a lower tier loses features, offer upgrade path at discount |
| **Usage limits** | If limits tighten, give users data to understand their usage |

### Deprecating a Data Source or Training Data

| Consideration | Guidance |
|--------------|----------|
| **Quality impact** | Quantify how model quality changes without this data source |
| **User notice** | If model behavior changes, communicate even if API doesn't change |
| **Compliance** | Ensure data removal is complete and auditable |

---

## Quick Reference Checklist

Use this as a starting point for any deprecation:

- [ ] Decision documented with rationale
- [ ] Impact assessment completed (users, revenue, integrations)
- [ ] Replacement feature is ready and validated
- [ ] Migration path defined and documented
- [ ] Timeline set with appropriate notice period
- [ ] Communication plan approved
- [ ] Internal teams briefed (support, sales, engineering)
- [ ] External announcement sent
- [ ] Migration guide published
- [ ] Tracking dashboard set up
- [ ] Non-migrating users proactively contacted
- [ ] Sunset executed cleanly
- [ ] Post-mortem completed and shared

