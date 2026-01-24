# Roadmap Builder

Build quarterly or annual product roadmaps from strategy documents, goals, and feature requests.

## Usage

Replace the `[PLACEHOLDERS]` with your specific information.

---

## Prompt

```
You are an experienced Product Manager helping me build a product roadmap.

## Strategic Context
- Product/Team: [PRODUCT OR TEAM NAME]
- Roadmap Timeframe: [e.g., Q1 2024, H1 2024, Annual 2024]
- Company/Team Goals: [HIGH-LEVEL OBJECTIVES]
- Key Metrics: [WHAT SUCCESS LOOKS LIKE - OKRs, KPIs]

## Inputs
### Strategy Documents
[PASTE OR SUMMARIZE RELEVANT STRATEGY DOCS]

### Feature Requests / Backlog
[LIST OF FEATURES, INITIATIVES, OR REQUESTS TO CONSIDER]

### Constraints
- Team Capacity: [e.g., 5 engineers, 1 designer]
- Technical Dependencies: [MAJOR BLOCKERS OR PREREQUISITES]
- External Dependencies: [OTHER TEAMS, PARTNERS, ETC.]
- Fixed Commitments: [ANYTHING ALREADY PROMISED OR CONTRACTUAL]

### Stakeholder Priorities
[ANY SPECIFIC REQUESTS FROM LEADERSHIP, CUSTOMERS, OR OTHER STAKEHOLDERS]

## Instructions

Build a roadmap that includes:

### 1. Roadmap Overview
**Vision Statement:** [What we're building toward]
**Theme for this Period:** [1-2 sentence focus area]
**Key Outcomes:** [3-5 measurable outcomes we're targeting]

### 2. Prioritization Summary

For each initiative, evaluate:
- **Impact:** [High/Medium/Low] - Business value and user impact
- **Effort:** [High/Medium/Low] - Engineering and design effort
- **Confidence:** [High/Medium/Low] - How certain are we about scope and value
- **Dependencies:** [What blocks this or is blocked by this]

Prioritization Matrix:
| Initiative | Impact | Effort | Confidence | Priority |
|------------|--------|--------|------------|----------|
| [Initiative 1] | H/M/L | H/M/L | H/M/L | P0/P1/P2 |

### 3. Roadmap by Time Period

#### [Month/Quarter 1]: [Theme]
**Focus:** [What we're prioritizing and why]

| Initiative | Description | Success Metric | Owner | Status |
|------------|-------------|----------------|-------|--------|
| [Name] | [1-2 sentences] | [How we measure success] | [Team/Person] | [Planned/In Progress] |

**Key Milestones:**
- [Date]: [Milestone 1]
- [Date]: [Milestone 2]

**Risks:**
- [Risk 1]: [Mitigation]

#### [Month/Quarter 2]: [Theme]
[Repeat structure]

#### [Month/Quarter 3]: [Theme]
[Repeat structure]

### 4. What We're NOT Doing (And Why)
| Initiative | Reason for Deferral | Revisit When |
|------------|---------------------|--------------|
| [Initiative] | [Why not now] | [Trigger for reconsideration] |

### 5. Dependencies & Critical Path
```
[Initiative A] → [Initiative B] → [Initiative C]
                      ↓
               [Initiative D]
```

**Cross-Team Dependencies:**
| Dependency | Team | Status | Risk Level |
|------------|------|--------|------------|
| [What we need] | [From whom] | [Confirmed/Pending/At Risk] | [High/Medium/Low] |

### 6. Resource Allocation
| Team/Function | Q1 % | Q2 % | Q3 % | Notes |
|---------------|------|------|------|-------|
| New Features | X% | X% | X% | [Context] |
| Tech Debt | X% | X% | X% | [Context] |
| Bug Fixes | X% | X% | X% | [Context] |
| Platform/Infra | X% | X% | X% | [Context] |

### 7. Review Cadence
- **Monthly Reviews:** [What we check and adjust]
- **Quarterly Reviews:** [Deeper evaluation and re-prioritization]
- **Stakeholder Updates:** [Who, when, format]

### 8. Open Questions
- [Question 1] - Decision needed by: [Date]
- [Question 2] - Depends on: [What information we need]

---

Ensure the roadmap:
- Aligns with stated goals and metrics
- Is realistic given capacity constraints
- Has clear ownership and milestones
- Includes buffer for unknowns (recommend 20%)
- Explains what we're NOT doing
```

---

## Quick Version (Quarterly Roadmap)

```
Build a quarterly roadmap:

Quarter: [Q1/Q2/Q3/Q4 YEAR]
Team Capacity: [X engineers, Y designers]
Goals: [TOP 3 GOALS FOR THE QUARTER]

Features to prioritize:
[LIST OF FEATURES/INITIATIVES]

Create:
- Prioritized list with Impact/Effort scores
- Monthly breakdown with milestones
- Key dependencies and risks
- What we're deferring and why
```

---

## Now/Next/Later Version

```
Organize these initiatives into a Now/Next/Later roadmap:

[LIST OF INITIATIVES]

**Now (This Quarter):**
- [High confidence, high priority items]
- Include success metrics

**Next (Next Quarter):**
- [Medium confidence, planned items]
- Note dependencies on "Now" work

**Later (Future):**
- [Lower confidence, exploratory items]
- Note what would move these up
```

---

## Example Input

```
Strategic Context:
- Product/Team: Platform Developer Experience
- Roadmap Timeframe: Q2 2024 (April - June)
- Company Goals: Improve developer retention, reduce time-to-first-value
- Key Metrics: Developer NPS > 40, Time to first API call < 15 minutes

Inputs:
Strategy: Focus on self-service and reducing friction in the getting-started experience.

Feature Requests:
1. Interactive API playground
2. Improved error messages with suggested fixes
3. SDK for Python (most requested)
4. Video tutorials
5. Slack community integration
6. Usage analytics dashboard
7. Webhook reliability improvements
8. API rate limiting improvements

Constraints:
- Team: 4 engineers, 1 designer, 1 tech writer
- Technical: Webhook system needs refactoring before reliability improvements
- Fixed: Python SDK promised to enterprise customer by end of Q2

Stakeholder Priorities:
- CEO wants visible progress on developer NPS
- Enterprise sales needs Python SDK for key deal
- Support wants better error messages to reduce tickets
```

## Example Output

### 1. Roadmap Overview

**Vision Statement:** Make our platform the easiest-to-integrate API in the category, where developers can go from signup to working integration in under 15 minutes.

**Theme for Q2 2024:** Reduce friction in the getting-started experience

**Key Outcomes:**
1. Developer NPS increases from 32 to 40+
2. Time to first API call decreases from 45 minutes to < 15 minutes
3. Support tickets related to integration decrease by 30%
4. Python SDK shipped and adopted by 3+ enterprise customers

### 2. Prioritization Summary

| Initiative | Impact | Effort | Confidence | Priority |
|------------|--------|--------|------------|----------|
| Python SDK | High | High | High | P0 (committed) |
| Interactive API playground | High | Medium | High | P0 |
| Improved error messages | High | Low | High | P0 |
| Video tutorials | Medium | Low | Medium | P1 |
| Webhook reliability | Medium | High | Medium | P2 (blocked) |
| Slack community | Low | Medium | Low | P2 |
| Usage analytics dashboard | Medium | Medium | Medium | P2 |
| API rate limiting | Low | Medium | High | P3 |

### 3. Roadmap by Time Period

#### April: Foundation & Quick Wins
**Focus:** Ship quick wins that improve developer experience while laying groundwork for SDK

| Initiative | Description | Success Metric | Owner | Status |
|------------|-------------|----------------|-------|--------|
| Improved error messages | Add contextual suggestions to top 20 error codes | 20% reduction in error-related support tickets | @Alex | Planned |
| API playground design | Design and prototype interactive playground | Usability test with 5 developers | @Jordan | Planned |
| Python SDK kickoff | Architecture and core implementation | Core endpoints working locally | @Pat + @Morgan | Planned |

**Key Milestones:**
- April 5: Error message improvements shipped
- April 15: Playground design approved
- April 30: SDK alpha ready for internal testing

**Risks:**
- SDK scope creep: Mitigate with strict MVP scope document

#### May: Core Deliverables
**Focus:** Ship playground and make progress on SDK

| Initiative | Description | Success Metric | Owner | Status |
|------------|-------------|----------------|-------|--------|
| API playground v1 | Launch interactive playground with code generation | 500+ monthly active users | @Jordan + @Alex | Planned |
| Python SDK beta | Feature-complete beta for customer testing | 3 enterprise customers testing | @Pat + @Morgan | Planned |
| Video tutorials | Create 5 getting-started videos | 1000+ views, 70%+ completion rate | @TechWriter | Planned |

**Key Milestones:**
- May 10: Playground beta launch
- May 20: SDK beta to enterprise customers
- May 31: Video tutorials published

**Risks:**
- Enterprise feedback delays SDK: Build 1-week buffer for iterations

#### June: Polish & Launch
**Focus:** GA releases and measuring impact

| Initiative | Description | Success Metric | Owner | Status |
|------------|-------------|----------------|-------|--------|
| Python SDK GA | Production-ready SDK with docs | SDK used in production by 3+ customers | @Pat + @Morgan | Planned |
| Playground iteration | Improve based on May feedback | User satisfaction > 4.0/5.0 | @Jordan | Planned |
| Developer NPS survey | Measure Q2 impact | NPS > 40 | @PM | Planned |

**Key Milestones:**
- June 15: Python SDK GA release
- June 25: Q2 Developer NPS survey launched
- June 30: Q2 retrospective and Q3 planning

**Risks:**
- SDK bugs in production: Plan for 1 week of bug fixes post-launch

### 4. What We're NOT Doing (And Why)

| Initiative | Reason for Deferral | Revisit When |
|------------|---------------------|--------------|
| Webhook reliability | Requires refactoring; team focused on SDK | Q3 after SDK ships |
| Slack community | Lower impact; need to validate demand | Q3 if NPS target met |
| Usage analytics dashboard | Nice-to-have; not blocking developer success | Q4 or when resources free |
| API rate limiting | Low urgency; current limits sufficient | When we see abuse patterns |

### 5. Dependencies & Critical Path

```
Error messages (April) → Independent
                              
Playground design (April) → Playground v1 (May) → Playground iteration (June)

SDK kickoff (April) → SDK beta (May) → SDK GA (June)
                           ↓
                    Enterprise testing (May)
```

**Cross-Team Dependencies:**
| Dependency | Team | Status | Risk Level |
|------------|------|--------|------------|
| Enterprise customer for SDK beta | Sales | Confirmed (Acme Corp) | Low |
| Design review for playground | Design | Confirmed | Low |
| Legal review for SDK license | Legal | Pending | Medium |

### 6. Resource Allocation

| Team/Function | April | May | June | Notes |
|---------------|-------|-----|------|-------|
| Python SDK | 50% | 50% | 40% | 2 engineers full-time |
| API Playground | 25% | 30% | 20% | 1 engineer + designer |
| Error messages | 15% | 0% | 0% | Quick win, done in April |
| Video tutorials | 0% | 10% | 0% | Tech writer led |
| Buffer/bugs | 10% | 10% | 40% | Higher buffer in June for polish |

### 7. Review Cadence

- **Weekly:** Team standup reviews roadmap progress and blockers
- **Bi-weekly:** PM + Tech Lead review milestones and adjust
- **Monthly:** Stakeholder update with demos
- **End of Quarter:** Full retrospective and Q3 planning

### 8. Open Questions

- Legal review for SDK license - Decision needed by: April 15
- Video tutorial hosting platform - Depends on: Budget approval
- Playground authentication approach - Needs: Security review by April 10

---

## Tips

- **Start with outcomes, not features** - What are you trying to achieve?
- **Be explicit about trade-offs** - What are you NOT doing and why?
- **Build in buffer** - 15-20% of capacity for unknowns
- **Make dependencies visible** - Cross-team dependencies are the biggest risk
- **Review regularly** - Roadmaps are living documents, not contracts
- **Communicate the "why"** - Context helps stakeholders understand prioritization
