# Technical Debt Assessment

Evaluate, prioritize, and document technical debt to make informed decisions about when and how to address it.

## Usage

Replace the `[PLACEHOLDERS]` with your specific information.

---

## Prompt

```
You are an experienced Product Manager helping me assess and prioritize technical debt.

## Context
- Product/System: [PRODUCT OR SYSTEM NAME]
- Team: [TEAM NAME AND SIZE]
- Current State: [BRIEF DESCRIPTION OF SYSTEM HEALTH]
- Assessment Goal: [e.g., "Plan Q2 tech debt sprint", "Justify refactoring to leadership"]

## Technical Debt Inventory
[LIST THE TECH DEBT ITEMS YOU'RE AWARE OF]

For each item, if known, include:
- Description of the debt
- When/why it was introduced
- Current impact (bugs, slowness, developer friction)
- Estimated effort to fix

## Additional Context
- Recent incidents related to tech debt: [IF ANY]
- Developer feedback: [PAIN POINTS ENGINEERS HAVE RAISED]
- Business constraints: [DEADLINES, COMMITMENTS, ETC.]
- Upcoming work that might be affected: [FEATURES THAT TOUCH THESE AREAS]

## Instructions

Create a comprehensive technical debt assessment:

### 1. Technical Debt Summary
**Overall Health Score:** [1-5 scale with explanation]
**Trend:** [Improving/Stable/Worsening]
**Top Concern:** [Single biggest issue]

### 2. Debt Categorization

Categorize each item:

**Deliberate Debt (Conscious trade-offs):**
- [Item]: Chosen because [reason], should address when [trigger]

**Accidental Debt (Unintended accumulation):**
- [Item]: Accumulated due to [reason], causing [impact]

**Bit Rot (Outdated dependencies/patterns):**
- [Item]: Outdated since [when], risk level [High/Medium/Low]

**Environment Debt (Infrastructure/tooling):**
- [Item]: Affecting [what], blocking [what improvements]

### 3. Debt Assessment Matrix

| Debt Item | Category | Severity | Effort | Business Impact | Risk if Ignored | Priority |
|-----------|----------|----------|--------|-----------------|-----------------|----------|
| [Item 1] | [Cat] | [1-5] | [S/M/L/XL] | [Description] | [What happens] | [P0-P3] |

**Severity Scale:**
- 5: Critical - Causing incidents or blocking features
- 4: High - Significant developer friction or performance issues
- 3: Medium - Noticeable impact on velocity or reliability
- 2: Low - Minor inconvenience
- 1: Minimal - Cosmetic or future concern

### 4. Impact Analysis

**Developer Experience Impact:**
- Time lost per week to workarounds: [Estimate]
- Onboarding friction: [How debt affects new developers]
- Morale impact: [Developer sentiment]

**Product/User Impact:**
- Performance degradation: [Metrics if available]
- Reliability issues: [Incident frequency, bug rate]
- Feature velocity reduction: [How much slower is development]

**Business Impact:**
- Revenue at risk: [If applicable]
- Customer complaints: [Related support tickets]
- Competitive disadvantage: [What we can't build]

### 5. Prioritization Recommendation

**Immediate Action (P0):**
| Item | Reason | Effort | Suggested Timeline |
|------|--------|--------|-------------------|
| [Item] | [Why urgent] | [Effort] | [When] |

**Plan This Quarter (P1):**
| Item | Reason | Effort | Suggested Timeline |
|------|--------|--------|-------------------|
| [Item] | [Why important] | [Effort] | [When] |

**Track for Later (P2):**
| Item | Trigger to Prioritize | Current Workaround |
|------|----------------------|-------------------|
| [Item] | [When to address] | [How we cope now] |

**Accept (P3):**
| Item | Reason to Accept | Review Cadence |
|------|-----------------|----------------|
| [Item] | [Why it's okay for now] | [When to reconsider] |

### 6. Recommended Approach

**Strategy:** [Full refactor / Incremental / Strangler pattern / Rewrite]

**Proposed Allocation:**
- Suggested % of sprint capacity for tech debt: [X%]
- Duration: [One-time / Ongoing / Time-boxed]

**Sequencing:**
1. [First action] - Enables [what]
2. [Second action] - Depends on [what]
3. [Continue sequence]

### 7. Investment Case

**Cost of Inaction:**
- [Quantified impact over next 6-12 months]
- [Opportunity cost]
- [Risk of incidents]

**Expected ROI:**
- [Productivity gains]
- [Risk reduction]
- [Enablement of future work]

**Payback Period:**
- [When investment pays off]

### 8. Tracking & Metrics

**How to Measure Progress:**
- [Metric 1]: [Current value] → [Target value]
- [Metric 2]: [Current value] → [Target value]

**Review Cadence:**
- [How often to reassess]
- [Who should be involved]

---

Be specific with estimates where possible. Flag assumptions clearly.
```

---

## Quick Version (Single Item Assessment)

```
Assess this technical debt item:

Debt: [DESCRIBE THE TECH DEBT]
Current Impact: [HOW IT AFFECTS US TODAY]
Origin: [WHEN/WHY IT WAS INTRODUCED]

Provide:
- Severity rating (1-5)
- Effort estimate (S/M/L/XL)
- Priority recommendation (P0-P3)
- Suggested approach to address
- Business case for fixing vs. accepting
```

---

## Tech Debt Triage Version

```
Triage these tech debt items for sprint planning:

[LIST OF TECH DEBT ITEMS]

Sprint capacity for tech debt: [X points or Y% of sprint]

Recommend:
- What to tackle this sprint
- What to defer and why
- What to accept permanently
```

---

## Example Input

```
Context:
- Product/System: Platform API
- Team: 6 engineers
- Current State: Functional but showing strain; 2 incidents last month related to legacy code
- Assessment Goal: Build case for dedicated tech debt sprint in Q2

Technical Debt Inventory:
1. Legacy authentication module - Written 4 years ago, uses deprecated library, hard to test
2. Monolithic request handler - 5000+ lines, everyone is afraid to touch it
3. Inconsistent error handling - Different patterns across services, causes debugging nightmares
4. Missing API versioning - Breaking changes have caused customer issues
5. Test coverage gaps - Core payment flow has 30% coverage
6. Outdated Node.js version - 2 major versions behind, security patches only
7. Hardcoded configuration - Env-specific values scattered in code
8. Missing observability - Limited logging, no distributed tracing

Developer feedback: "The request handler is a minefield" - multiple engineers
Recent incidents: Auth module bug caused 2-hour outage; payment test gaps led to production bug

Business constraints: Q2 has major customer launch in May; leadership wants to see progress on new features
```

## Example Output

### 1. Technical Debt Summary

**Overall Health Score:** 2.5/5 (Concerning)
**Trend:** Worsening - Two incidents in the past month, velocity declining
**Top Concern:** Monolithic request handler - High risk, blocking multiple improvements

### 2. Debt Categorization

**Deliberate Debt (Conscious trade-offs):**
- Missing API versioning: Deferred to move fast early; now causing customer pain
- Test coverage gaps: Velocity prioritized over testing; catching up to us

**Accidental Debt (Unintended accumulation):**
- Monolithic request handler: Grew organically; no one refactored as it expanded
- Inconsistent error handling: Different authors, no standards defined

**Bit Rot (Outdated dependencies/patterns):**
- Legacy authentication module: 4 years old, deprecated dependencies
- Outdated Node.js: 2 major versions behind

**Environment Debt (Infrastructure/tooling):**
- Hardcoded configuration: Blocks proper environment management
- Missing observability: Can't debug issues effectively

### 3. Debt Assessment Matrix

| Debt Item | Category | Severity | Effort | Business Impact | Risk if Ignored | Priority |
|-----------|----------|----------|--------|-----------------|-----------------|----------|
| Monolithic request handler | Accidental | 5 | XL | Velocity -30%, incident risk | Major outage likely | P0 |
| Test coverage (payments) | Deliberate | 5 | M | Production bugs | Customer-facing bug | P0 |
| Legacy auth module | Bit Rot | 4 | L | 2-hour outage last month | More outages | P1 |
| Missing observability | Environment | 4 | M | Slow incident response | Longer MTTR | P1 |
| Inconsistent error handling | Accidental | 3 | M | Debugging time | Developer frustration | P1 |
| Outdated Node.js | Bit Rot | 3 | M | Security risk | Vulnerability | P1 |
| API versioning | Deliberate | 3 | L | Customer complaints | Churn risk | P2 |
| Hardcoded config | Environment | 2 | S | Deploy friction | Env issues | P2 |

### 4. Impact Analysis

**Developer Experience Impact:**
- Time lost per week to workarounds: ~8 hours/developer (monolith navigation, debugging)
- Onboarding friction: New engineers take 2 weeks longer to be productive
- Morale impact: "The request handler is a minefield" - multiple engineers

**Product/User Impact:**
- Performance degradation: P95 latency increased 40% YoY
- Reliability issues: 2 incidents last month (auth outage, payment bug)
- Feature velocity reduction: Estimates are 2x what they "should" be

**Business Impact:**
- Revenue at risk: Payment bug cost ~$15k in refunds
- Customer complaints: 3 enterprise customers mentioned API stability in QBRs
- Competitive disadvantage: Can't ship SDK improvements due to versioning gaps

### 5. Prioritization Recommendation

**Immediate Action (P0):**
| Item | Reason | Effort | Suggested Timeline |
|------|--------|--------|-------------------|
| Test coverage (payments) | Production bug last month; high risk | M (2 weeks) | April |
| Monolithic request handler | Begin decomposition; blocking everything | XL (phased) | Start April |

**Plan This Quarter (P1):**
| Item | Reason | Effort | Suggested Timeline |
|------|--------|--------|-------------------|
| Legacy auth module | Caused outage; deprecated deps | L (3 weeks) | May |
| Missing observability | Improves incident response | M (2 weeks) | May |
| Inconsistent error handling | Standards + migration | M (ongoing) | Q2 ongoing |
| Outdated Node.js | Security compliance | M (2 weeks) | June |

**Track for Later (P2):**
| Item | Trigger to Prioritize | Current Workaround |
|------|----------------------|-------------------|
| API versioning | Next breaking change needed | Manual customer communication |
| Hardcoded config | When we add new environment | Careful deploy procedures |

**Accept (P3):**
None - all items warrant eventual attention

### 6. Recommended Approach

**Strategy:** Incremental improvement with one focused refactor

**Proposed Allocation:**
- Suggested % of sprint capacity for tech debt: 30% ongoing (after initial investment)
- Duration: 20% dedicated tech debt sprint in April, then ongoing allocation

**Sequencing:**
1. Payment test coverage (April Week 1-2) - Reduce production risk immediately
2. Begin request handler decomposition (April Week 3+) - Extract first module
3. Observability improvements (May) - Enables faster debugging for remaining work
4. Auth module refactor (May-June) - With observability in place
5. Node.js upgrade (June) - After stability improvements
6. Error handling standards (Ongoing) - Apply to new code, migrate opportunistically

### 7. Investment Case

**Cost of Inaction:**
- Incidents: Likely 1-2 more outages in next 6 months (~$20k+ cost each)
- Velocity: 30% productivity loss = ~$200k/year in engineering cost
- Talent risk: Engineers frustrated with codebase; retention risk

**Expected ROI:**
- 50% reduction in incident frequency
- 20% velocity improvement within 6 months
- Improved developer satisfaction and retention

**Payback Period:**
- Payment tests: Immediate (prevents next bug)
- Request handler: 4-6 months (gradual velocity improvement)
- Full investment: ~8 months to net positive

### 8. Tracking & Metrics

**How to Measure Progress:**
- Incident frequency: 2/month → <1/month
- Deployment confidence: Survey score 3/5 → 4/5
- Time to onboard: 6 weeks → 4 weeks
- Test coverage (critical paths): 30% → 80%

**Review Cadence:**
- Monthly: Review metrics and adjust priorities
- Quarterly: Full debt reassessment with engineering leads

---

## Tips

- **Quantify impact** - "Costs 2 hours/week per developer" is more compelling than "slows us down"
- **Connect to business outcomes** - Leadership cares about customers, revenue, and risk
- **Be realistic about effort** - Underestimating erodes trust
- **Show the cost of inaction** - What happens if we don't fix this?
- **Propose incremental approaches** - Big rewrites are risky; show phased options
- **Track and celebrate progress** - Visibility keeps tech debt on the agenda
