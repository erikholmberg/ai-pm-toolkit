# Jira Sprint Planning Assistant

Help plan and organize sprints by analyzing backlog, estimating capacity, and suggesting sprint goals.

## Usage

Replace the `[PLACEHOLDERS]` with your specific information.

---

## Prompt

```
You are an experienced Product Manager helping me plan a sprint.

## Sprint Context
- Sprint Name/Number: [e.g., Sprint 45]
- Sprint Duration: [e.g., 2 weeks]
- Team Capacity: [e.g., 5 developers, 40 story points, or 80 developer-hours]
- Sprint Goal: [OPTIONAL - HIGH-LEVEL OBJECTIVE FOR THIS SPRINT]

## Backlog Context
[PASTE YOUR BACKLOG ITEMS OR DESCRIBE THEM]

Or provide:
- Project: [PROJECT KEY]
- Epic(s): [EPIC KEYS IF FOCUSING ON SPECIFIC EPICS]
- Priority Focus: [e.g., "P0 and P1 items", "Critical bugs"]

## Constraints
- Must Include: [ANY TICKETS THAT MUST BE IN THIS SPRINT]
- Dependencies: [TICKETS THAT BLOCK OR ARE BLOCKED BY OTHERS]
- Team Availability: [e.g., "2 developers out for 2 days", "QA capacity limited"]
- Technical Constraints: [e.g., "Infrastructure work needed first"]

## Instructions

Analyze the backlog and create a sprint plan that includes:

### 1. Sprint Goal
[1-2 sentence objective that ties the work together]

### 2. Capacity Analysis
- Total available capacity: [story points or hours]
- Recommended commitment: [80-90% of capacity for buffer]
- Target story points: [recommended commitment]

### 3. Recommended Sprint Backlog

For each ticket, provide:
- **Ticket Key/Title:** [if available]
- **Story Points:** [estimate]
- **Priority:** [P0/P1/P2]
- **Dependencies:** [if any]
- **Risk Level:** [Low/Medium/High]
- **Why Include:** [1 sentence justification]

### 4. Sprint Structure
- **Must Have (P0):** [Core work that blocks launch or other teams]
- **Should Have (P1):** [Important work if capacity allows]
- **Nice to Have (P2):** [Can be deferred if needed]

### 5. Risk Assessment
- **High Risk Items:** [Tickets with uncertainty, dependencies, or complexity]
- **Mitigation Strategies:** [How to handle risks]
- **Buffer Recommendations:** [Extra capacity to hold for unknowns]

### 6. Dependencies & Sequencing
- **Critical Path:** [Order of work that must be done sequentially]
- **Parallel Work:** [Work that can be done simultaneously]
- **Blockers:** [Items that need to be completed first]

### 7. Definition of Done Checklist
[Ensure all tickets have clear DoD criteria]

### 8. Success Metrics
- **Velocity Target:** [story points to complete]
- **Key Deliverables:** [What must ship this sprint]
- **Stakeholder Updates:** [Who needs to know what]

---

Provide a balanced plan that:
- Achieves the sprint goal
- Respects team capacity
- Manages risk appropriately
- Includes buffer for unknowns
- Sequences work logically
```

---

## Quick Version (Capacity-Based)

```
Plan a sprint with:
- Capacity: [X story points or Y developer-hours]
- Duration: [Z weeks]
- Focus: [e.g., "Bug fixes", "Feature X", "Technical debt"]

Backlog items:
[LIST OR PASTE TICKETS]

Prioritize and select items that fit the capacity, considering:
- Dependencies
- Risk levels
- Team skills
- Sprint goal alignment
```

---

## Example Input

```
Sprint Context:
- Sprint Name: Sprint 45
- Sprint Duration: 2 weeks
- Team Capacity: 6 developers, target 50 story points
- Sprint Goal: Launch notification preferences feature to beta users

Backlog Context:
- Project: PLATFORM
- Epic: PLATFORM-100 (Notification System Improvements)
- Priority Focus: P0 and P1 items for notification preferences

Constraints:
- Must Include: PLATFORM-201 (Notification Settings UI), PLATFORM-202 (API Integration)
- Dependencies: PLATFORM-201 blocks PLATFORM-203 (User Testing)
- Team Availability: 1 developer out for 3 days, QA capacity at 60%
- Technical Constraints: API changes need to be deployed before frontend work

Backlog Items:
1. PLATFORM-201: Notification Settings UI (8 points, P0)
2. PLATFORM-202: API Integration for preferences (5 points, P0)
3. PLATFORM-203: User Testing Setup (3 points, P1)
4. PLATFORM-204: Notification Analytics Dashboard (13 points, P1)
5. PLATFORM-205: Email Notification Improvements (5 points, P1)
6. PLATFORM-206: Documentation Updates (3 points, P1)
7. PLATFORM-207: Performance Optimization (8 points, P2)
8. PLATFORM-208: Accessibility Improvements (5 points, P2)
```

## Example Output

### 1. Sprint Goal
Launch the notification preferences feature to beta users, enabling them to customize notification channels and reduce notification fatigue.

### 2. Capacity Analysis
- Total available capacity: 50 story points (target)
- Recommended commitment: 45 story points (90% for buffer)
- Target story points: 45 points
- Adjusted for availability: 42-45 points (accounting for 1 developer out)

### 3. Recommended Sprint Backlog

**PLATFORM-202: API Integration for preferences** (5 points, P0)
- Dependencies: None (must be first)
- Risk Level: Low
- Why Include: Blocks all frontend work; must be deployed early

**PLATFORM-201: Notification Settings UI** (8 points, P0)
- Dependencies: Blocks on PLATFORM-202
- Risk Level: Medium (complex UI state management)
- Why Include: Core feature requirement; must be done for beta launch

**PLATFORM-203: User Testing Setup** (3 points, P1)
- Dependencies: Blocks on PLATFORM-201
- Risk Level: Low
- Why Include: Enables beta testing; lightweight but important

**PLATFORM-206: Documentation Updates** (3 points, P1)
- Dependencies: Blocks on PLATFORM-201
- Risk Level: Low
- Why Include: Required for beta launch; can be done in parallel with testing

**PLATFORM-205: Email Notification Improvements** (5 points, P1)
- Dependencies: None (can be parallel)
- Risk Level: Medium
- Why Include: Enhances core feature; independent work stream

**PLATFORM-207: Performance Optimization** (8 points, P2)
- Dependencies: None
- Risk Level: Low
- Why Include: If capacity allows, improves user experience

**Total: 32 points (P0+P1 core) + 8 points (P2 optional) = 40 points**

### 4. Sprint Structure

**Must Have (P0) - 13 points:**
- PLATFORM-202: API Integration (5 pts) - Week 1
- PLATFORM-201: Notification Settings UI (8 pts) - Week 1-2

**Should Have (P1) - 19 points:**
- PLATFORM-203: User Testing Setup (3 pts) - Week 2
- PLATFORM-206: Documentation (3 pts) - Week 2
- PLATFORM-205: Email Improvements (5 pts) - Week 1-2 (parallel)
- PLATFORM-204: Analytics Dashboard (13 pts) - **DEFER** (too large, can be next sprint)

**Nice to Have (P2) - 8 points:**
- PLATFORM-207: Performance Optimization (8 pts) - If time allows
- PLATFORM-208: Accessibility (5 pts) - **DEFER** to next sprint

### 5. Risk Assessment

**High Risk Items:**
- PLATFORM-201 (UI): Complex state management, depends on API being stable
  - *Mitigation:* API deployed by end of Week 1, UI work can start with mocks

**Medium Risk Items:**
- PLATFORM-205 (Email): May uncover integration issues
  - *Mitigation:* Start early, can be done in parallel with UI work

**Buffer Recommendations:**
- Hold 5-8 points of capacity for:
  - Bug fixes from API deployment
  - UI refinement based on early feedback
  - Unexpected integration issues

### 6. Dependencies & Sequencing

**Critical Path:**
1. Week 1: PLATFORM-202 (API) → Deploy to staging
2. Week 1-2: PLATFORM-201 (UI) → Can start with mocks, integrate when API ready
3. Week 2: PLATFORM-203 (Testing) → After UI is functional

**Parallel Work:**
- PLATFORM-205 (Email) can run parallel with UI work
- PLATFORM-206 (Docs) can be written as features are built

**Blockers:**
- PLATFORM-202 must be completed and deployed before UI integration
- PLATFORM-201 must be functional before testing setup

### 7. Definition of Done Checklist

Ensure all tickets include:
- [ ] Code reviewed and approved
- [ ] Unit tests written and passing (>80% coverage)
- [ ] Integration tests passing (for API/UI integration)
- [ ] QA verified on staging
- [ ] Documentation updated
- [ ] Product sign-off
- [ ] Feature flag enabled (if applicable)

### 8. Success Metrics

**Velocity Target:** 32-40 story points completed

**Key Deliverables:**
- Notification preferences feature functional in staging
- Beta users can access and use the feature
- Documentation complete for beta launch

**Stakeholder Updates:**
- Engineering Lead: Daily standup updates on API deployment
- Design Team: Review UI before Week 2
- Beta Program Manager: Coordinate beta user access by end of sprint
- Product: Final sign-off before beta launch

---

## Tips

- **Start with the goal** - Every ticket should contribute to the sprint goal
- **Respect capacity** - Better to under-commit and over-deliver
- **Sequence dependencies** - Map critical path early
- **Plan for unknowns** - Keep 10-20% buffer for bugs and refinement
- **Balance work types** - Mix of features, bugs, and tech debt keeps team engaged
- **Consider skills** - Match work to team member strengths when possible

