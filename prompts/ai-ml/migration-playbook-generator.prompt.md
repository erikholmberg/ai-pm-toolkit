# Migration Playbook Generator

Generate step-by-step migration plans for moving users between AI model versions, API versions, or product tiers. Covers communication, rollout sequencing, rollback criteria, and success metrics.

## Usage

Replace the `[PLACEHOLDERS]` with your specific information.

---

## Model Version Migration Playbook

```
You are a senior AI Product Manager who has managed dozens of model migrations. Help me create a comprehensive migration playbook.

## Context
- Product: [PRODUCT NAME]
- Migration Type: [e.g., "GPT-3.5 → GPT-4o", "Custom model v2 → v3", "Single model → multi-model routing"]
- Affected Users: [NUMBER AND SEGMENT — e.g., "All 50K API users", "Enterprise tier only"]
- Timeline: [TARGET COMPLETION DATE]
- Breaking Changes: [YES/NO — DESCRIBE IF YES]
- Backward Compatibility: [FULL / PARTIAL / NONE]

## Current State
- Current model/version: [DETAILS]
- Current SLAs: [LATENCY, UPTIME, QUALITY GUARANTEES]
- Integration patterns: [e.g., "REST API", "SDK", "Embedded widget"]
- Known pain points with current version: [LIST]

## Target State
- New model/version: [DETAILS]
- Expected improvements: [e.g., "30% lower latency", "Better accuracy on X", "New capabilities"]
- New requirements: [e.g., "Different input format", "New auth", "Higher token limits"]
- Known regressions: [e.g., "Slower on edge case X", "Different output format"]

---

## Instructions

Generate a complete migration playbook with:

### 1. Migration Overview
- One-page summary: what's changing, why, and what users need to do
- Impact assessment matrix: who is affected and how severely
- Success criteria: how we'll know the migration succeeded

### 2. Pre-Migration Checklist
- [ ] Quality validation: eval results comparing old vs. new (link to eval framework)
- [ ] Performance benchmarks: latency, throughput, error rates
- [ ] Compatibility testing: all integration patterns tested
- [ ] Rollback plan documented and tested
- [ ] Monitoring dashboards updated for new version
- [ ] Support team briefed with FAQ and escalation path
- [ ] Customer communication drafted and reviewed
- [ ] Legal/compliance review (if data handling changes)

### 3. Communication Plan
For each audience, draft the actual message:

**a. Pre-Migration Notice (30 days out)**
- What's changing and why
- What they need to do (if anything)
- Timeline with key dates
- Link to migration guide
- Support contact

**b. Migration Guide (technical)**
- Step-by-step instructions for each integration pattern
- Code examples: before and after
- Breaking changes with exact remediation steps
- Testing checklist for customers

**c. Migration Day Notice**
- Confirmation of migration window
- Expected downtime (if any)
- Real-time status page link
- Escalation contact

**d. Post-Migration Confirmation**
- What was completed
- How to verify everything is working
- Where to report issues
- What's improved

### 4. Rollout Phases
Design a phased rollout:

| Phase | Users | % Traffic | Duration | Success Gate |
|-------|-------|-----------|----------|-------------|
| Phase 0 | Internal dogfooding | — | 1 week | No P0/P1 issues |
| Phase 1 | [WHO] | [%] | [DURATION] | [GATE CRITERIA] |
| Phase 2 | [WHO] | [%] | [DURATION] | [GATE CRITERIA] |
| Phase 3 | [WHO] | [%] | [DURATION] | [GATE CRITERIA] |
| GA | All users | 100% | — | All gates passed |

For each phase, define:
- Entry criteria (what must be true to start)
- Monitoring focus (what to watch)
- Exit criteria (what must be true to proceed)
- Rollback trigger (what would cause us to revert)

### 5. Rollback Plan
- Trigger conditions: when to roll back (automatic and manual)
- Rollback procedure: step-by-step
- Data considerations: how to handle requests processed by new version
- Communication: template for rollback notification
- Post-rollback: root cause analysis process

### 6. Monitoring & Metrics
Track during and after migration:

| Metric | Baseline | Alert Threshold | Rollback Threshold |
|--------|----------|-----------------|-------------------|
| Error rate | [%] | [%] | [%] |
| p50 latency | [ms] | [ms] | [ms] |
| p99 latency | [ms] | [ms] | [ms] |
| Output quality score | [score] | [score] | [score] |
| Customer-reported issues | [count] | [count] | [count] |

### 7. Post-Migration
- Deprecation timeline for old version
- Success report template (for stakeholders)
- Lessons learned process
- Documentation updates needed

---

## Guidelines
- Be specific about dates, thresholds, and ownership
- Every phase needs a clearly defined rollback path
- Assume some users will not read the migration notice — design for that
- For AI model migrations, quality regressions on edge cases are the biggest risk
- Include eval comparisons as part of every phase gate
```

---

## API Version Migration

```
Help me create a migration plan for deprecating an API version and moving users to a new one.

## Context
- Product: [PRODUCT NAME]
- Old API Version: [e.g., "v1", "/api/v2"]
- New API Version: [e.g., "v2", "/api/v3"]
- Active Users on Old Version: [NUMBER]
- Deprecation Deadline: [DATE]
- Breaking Changes: [LIST SPECIFIC CHANGES]

## Key Differences
| Aspect | Old Version | New Version |
|--------|------------|-------------|
| [Auth] | [e.g., API key] | [e.g., OAuth 2.0] |
| [Endpoints] | [CHANGES] | [CHANGES] |
| [Request format] | [CHANGES] | [CHANGES] |
| [Response format] | [CHANGES] | [CHANGES] |
| [Rate limits] | [OLD LIMITS] | [NEW LIMITS] |

---

## Instructions

Generate an API migration plan with:

### 1. Deprecation Timeline
- Announcement date → sunset date (recommended minimum: 6 months for enterprise APIs)
- Phase gates with specific dates

### 2. Developer Communications
Draft communications for:
- **Deprecation announcement** (email + in-app banner)
- **Migration guide** (developer docs format with code samples)
- **Reminder at 90 / 30 / 7 days** (progressively urgent)
- **Sunset notice** (final cutoff)
- **Post-sunset** (what happens to calls to the old endpoint)

### 3. Migration Support
- SDK updates needed
- Codemods or automated migration tools (if feasible)
- Office hours / migration support channel
- Incentives for early migration (if applicable)

### 4. Adoption Tracking
- Dashboard tracking migration progress
- Identify top users still on old version for proactive outreach
- Usage analytics: calls to old vs. new endpoint over time

### 5. Sunset Mechanics
- What happens at sunset: 410 Gone vs. redirect vs. compatibility shim
- Grace period behavior
- Data handling for old-version requests in flight

Keep it developer-friendly. Engineers appreciate direct, technical communication.
```

---

## Tier Upgrade / Downgrade Migration

```
Help me create a plan for migrating users when restructuring pricing tiers or plans.

## Context
- Product: [PRODUCT NAME]
- Change Type: [e.g., "Merging two tiers", "Adding a new tier", "Changing feature allocation", "Price increase"]
- Current Tiers: [LIST WITH PRICES AND KEY FEATURES]
- New Tiers: [LIST WITH PRICES AND KEY FEATURES]
- Affected Users: [NUMBER PER TIER]
- Effective Date: [DATE]

## User Impact
- Users gaining features: [SEGMENT AND WHAT THEY GAIN]
- Users losing features: [SEGMENT AND WHAT THEY LOSE — HANDLE WITH CARE]
- Users with price changes: [SEGMENT AND AMOUNT]
- Grandfathered users: [WHO AND FOR HOW LONG]

---

## Instructions

Generate a tier migration plan with:

### 1. Impact Matrix
| Current Plan | # Users | New Plan | Price Change | Feature Change | Risk Level |
|-------------|---------|----------|-------------|---------------|------------|

### 2. Grandfathering Strategy
- Who gets grandfathered and for how long
- What triggers the end of grandfathering (renewal date, usage threshold, etc.)
- How to communicate the eventual transition

### 3. Communication Templates
Draft actual messages for each scenario:
- **Upgrade path** — User gets more for the same or less (celebratory tone)
- **Lateral move** — Plan renamed or restructured, no material change (informative tone)
- **Downgrade or price increase** — User loses features or pays more (empathetic, clear value justification)

### 4. In-App Experience
- What the user sees in their billing/settings page
- Modal or banner copy for the transition
- FAQ page content specific to this migration

### 5. Support Playbook
- Objection handling for common complaints
- Escalation criteria
- Retention offers (if applicable)
- Refund policy during transition

### 6. Success Metrics
- Churn rate during migration vs. baseline
- Support ticket volume
- Upgrade/downgrade rates
- Revenue impact tracking

Tone: respectful and transparent. Never make a user feel like they're losing something without clear justification.
```

---

## Tips

- **Over-communicate** - Users forgetting about a migration is the top cause of migration incidents
- **Grandfather generously** - The short-term revenue loss is worth the goodwill and retention
- **Test rollback before you need it** - Don't discover your rollback plan is broken during an incident
- **Eval, eval, eval** - For model migrations, run comprehensive quality evals before each phase gate
- **Watch the long tail** - The last 5% of users to migrate often generate 50% of the support tickets
- **Include customer success** - They'll hear about problems first; loop them in early

