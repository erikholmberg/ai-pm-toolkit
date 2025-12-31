# Jira Epic Breakdown

Break down large epics into manageable stories, tasks, and subtasks with proper sequencing and dependencies.

## Usage

Replace the `[PLACEHOLDERS]` with your specific information.

---

## Prompt

```
You are an experienced Product Manager helping me break down an epic into actionable Jira tickets.

## Epic Context
- Epic Name: [EPIC NAME]
- Epic Key: [EPIC KEY IF IT EXISTS]
- Epic Description: [HIGH-LEVEL DESCRIPTION OF THE EPIC]
- Business Goal: [WHAT SUCCESS LOOKS LIKE FOR THIS EPIC]
- Target Timeline: [e.g., "Q2 2024", "3 sprints", "8 weeks"]

## User & Business Context
- Primary Users: [WHO WILL USE THIS]
- Problem Statement: [WHAT PROBLEM ARE WE SOLVING]
- Success Metrics: [HOW WE'LL MEASURE SUCCESS]

## Technical Context
- Technical Approach: [HIGH-LEVEL ARCHITECTURE OR APPROACH]
- Dependencies: [OTHER SYSTEMS, TEAMS, OR EPICS]
- Constraints: [TECHNICAL LIMITATIONS OR REQUIREMENTS]

## Instructions

Break down this epic into:

### 1. Epic Summary
- **Epic Name:** [Clear, user-focused name]
- **Epic Description:** [2-3 sentences]
- **Epic Goal:** [What we're trying to achieve]
- **Success Metrics:** [Measurable outcomes]

### 2. Breakdown Structure

Organize work into logical phases or themes:

#### Phase/Theme 1: [NAME]
**Goal:** [What this phase achieves]

**Stories:**
- [Story 1]: [Title] - [Story points] - [Priority]
  - User Story: As a [user], I want to [action] so that [benefit]
  - Acceptance Criteria: [3-5 criteria]
  - Dependencies: [What blocks or is blocked by]
  
- [Story 2]: [Title] - [Story points] - [Priority]
  - [Same format]

**Tasks:**
- [Task 1]: [Technical task] - [Story points]
- [Task 2]: [Technical task] - [Story points]

#### Phase/Theme 2: [NAME]
[Repeat structure]

### 3. Implementation Sequence

**Sprint 1 Focus:** [Theme/Phase]
- Must complete: [Critical path items]
- Can start: [Parallel work]

**Sprint 2 Focus:** [Theme/Phase]
- [Continue sequence]

### 4. Dependencies Map

```
[Story A] → [Story B] → [Story C]
     ↓
[Story D] (parallel)
```

### 5. Risk Assessment

- **High Risk Stories:** [Stories with uncertainty]
  - Risk: [What could go wrong]
  - Mitigation: [How to address]
  
- **Blocking Stories:** [Stories that block others]
  - Impact: [What's blocked]
  - Priority: [Why it's critical]

### 6. Epic-Level Acceptance Criteria

- [ ] [Epic-level criterion 1]
- [ ] [Epic-level criterion 2]
- [ ] [Epic-level criterion 3]

### 7. Labels & Organization

**Suggested Labels:** [Labels to apply to all tickets]
**Components:** [Jira components if applicable]
**Fix Version:** [Target release version]

---

Ensure stories are:
- **Independent** - Can be developed separately
- **Small** - Fit in a sprint (typically 3-8 story points)
- **Valuable** - Deliver user value on their own
- **Testable** - Clear acceptance criteria
- **Sequenced** - Logical order with dependencies mapped
```

---

## Quick Version

```
Break down this epic into stories:

Epic: [EPIC NAME]
Description: [WHAT WE'RE BUILDING]
Goal: [WHAT SUCCESS LOOKS LIKE]

Break into:
- 5-10 user stories (3-8 points each)
- Clear acceptance criteria for each
- Dependencies between stories
- Suggested sprint sequence
```

---

## Example Input

```
Epic Context:
- Epic Name: Notification Preferences System
- Epic Description: Allow users to customize which notifications they receive and through which channels (email, in-app, Slack) to reduce notification fatigue
- Business Goal: Reduce notification-related support tickets by 30% and improve user satisfaction scores
- Target Timeline: 3 sprints (6 weeks)

User & Business Context:
- Primary Users: Platform developers, DevOps engineers, Product Managers
- Problem Statement: Users receive too many notifications across multiple channels, leading to fatigue and missing important updates
- Success Metrics: 30% reduction in support tickets, 80% of users customize preferences within 30 days, 4.0+ satisfaction score

Technical Context:
- Technical Approach: New preferences API, frontend settings page, integration with existing notification service
- Dependencies: Notification service API, user authentication system
- Constraints: Must work with existing notification infrastructure, cannot break current notification delivery
```

## Example Output

### 1. Epic Summary

**Epic Name:** Notification Preferences System
**Epic Description:** Enable users to customize notification delivery preferences by type and channel (email, in-app, Slack) to reduce notification fatigue and improve user experience.
**Epic Goal:** Reduce notification-related support tickets by 30% and achieve 80% user adoption of preferences within 30 days of launch.
**Success Metrics:**
- 30% reduction in notification-related support tickets
- 80% of active users customize preferences within 30 days
- User satisfaction score of 4.0+ (out of 5.0)
- Average notification volume per user decreases by 25%

### 2. Breakdown Structure

#### Phase 1: Foundation & API
**Goal:** Build the backend infrastructure to support notification preferences

**Stories:**

- **PLATFORM-201: Preferences Data Model & Storage** (5 points, P0)
  - User Story: As a system, I want to store user notification preferences so that preferences persist across sessions
  - Acceptance Criteria:
    - [ ] Database schema supports notification type, channel, and user preferences
    - [ ] API can create, read, update, and delete preferences
    - [ ] Preferences are user-scoped and secure
    - [ ] Default preferences are applied for new users
  - Dependencies: None (foundational)
  
- **PLATFORM-202: Preferences API Endpoints** (8 points, P0)
  - User Story: As a frontend application, I want to retrieve and update notification preferences via API so that users can manage their settings
  - Acceptance Criteria:
    - [ ] GET `/api/v1/notifications/preferences` returns user's current preferences
    - [ ] PUT `/api/v1/notifications/preferences` updates preferences with validation
    - [ ] API returns appropriate error codes for invalid requests
    - [ ] API supports bulk updates for multiple notification types
    - [ ] Rate limiting prevents abuse
  - Dependencies: Blocks on PLATFORM-201

**Tasks:**
- PLATFORM-203: API Documentation (3 points)
- PLATFORM-204: API Unit Tests (5 points)

#### Phase 2: User Interface
**Goal:** Provide intuitive UI for users to manage preferences

**Stories:**

- **PLATFORM-205: Notification Settings Page** (8 points, P0)
  - User Story: As a platform developer, I want to view and modify my notification preferences in a settings page so that I can control what notifications I receive
  - Acceptance Criteria:
    - [ ] Settings page displays all notification types with current channel settings
    - [ ] Users can toggle notification types on/off
    - [ ] Users can select delivery channels (email, in-app, Slack) per notification type
    - [ ] Changes are saved immediately with visual feedback
    - [ ] Page is accessible (WCAG 2.1 AA compliant)
  - Dependencies: Blocks on PLATFORM-202

- **PLATFORM-206: Preference Validation & Error Handling** (5 points, P1)
  - User Story: As a user, I want clear feedback when my preference changes fail so that I understand what went wrong
  - Acceptance Criteria:
    - [ ] Validation errors are displayed clearly
    - [ ] At least one channel must be selected per enabled notification type
    - [ ] Network errors show retry options
    - [ ] Success messages confirm saved changes
  - Dependencies: Blocks on PLATFORM-205

**Tasks:**
- PLATFORM-207: UI Component Library Updates (3 points)
- PLATFORM-208: UI/UX Testing (5 points)

#### Phase 3: Integration & Delivery
**Goal:** Integrate preferences with notification delivery system

**Stories:**

- **PLATFORM-209: Notification Service Integration** (8 points, P0)
  - User Story: As the notification service, I want to check user preferences before sending notifications so that users only receive notifications they've opted into
  - Acceptance Criteria:
    - [ ] Notification service queries preferences API before sending
    - [ ] Notifications are filtered by user preferences
    - [ ] Default preferences are applied if user hasn't customized
    - [ ] Integration handles API failures gracefully (fail open with logging)
  - Dependencies: Blocks on PLATFORM-202, PLATFORM-205

- **PLATFORM-210: Notification Delivery Logging** (5 points, P1)
  - User Story: As a product manager, I want to see notification delivery metrics so that I can measure the impact of preferences
  - Acceptance Criteria:
    - [ ] System logs when notifications are filtered by preferences
    - [ ] Metrics track notification volume by channel
    - [ ] Dashboard shows preference adoption rates
  - Dependencies: Blocks on PLATFORM-209

#### Phase 4: Enhancement & Analytics
**Goal:** Improve experience and measure success

**Stories:**

- **PLATFORM-211: Bulk Preference Management** (5 points, P2)
  - User Story: As a user, I want to apply the same preference settings to multiple notification types at once so that I can quickly configure my preferences
  - Acceptance Criteria:
    - [ ] Users can select multiple notification types
    - [ ] Bulk actions apply to selected types
    - [ ] Undo functionality available
  - Dependencies: Blocks on PLATFORM-205

- **PLATFORM-212: Preference Analytics Dashboard** (8 points, P2)
  - User Story: As a product manager, I want to see analytics on preference usage so that I can understand adoption and optimize the feature
  - Acceptance Criteria:
    - [ ] Dashboard shows preference adoption rates
    - [ ] Charts display notification volume trends
    - [ ] User segmentation by preference patterns
  - Dependencies: Blocks on PLATFORM-210

### 3. Implementation Sequence

**Sprint 1 Focus:** Foundation & API (Phase 1)
- Must complete: PLATFORM-201, PLATFORM-202 (API ready for frontend)
- Can start: PLATFORM-203, PLATFORM-204 (documentation and tests in parallel)

**Sprint 2 Focus:** User Interface (Phase 2)
- Must complete: PLATFORM-205 (core UI), PLATFORM-206 (validation)
- Can start: PLATFORM-209 (integration planning)

**Sprint 3 Focus:** Integration & Polish (Phase 3)
- Must complete: PLATFORM-209 (integration), PLATFORM-210 (logging)
- Can start: PLATFORM-211, PLATFORM-212 (if capacity allows)

### 4. Dependencies Map

```
PLATFORM-201 (Data Model)
    ↓
PLATFORM-202 (API) → PLATFORM-205 (UI) → PLATFORM-206 (Validation)
    ↓                                           ↓
PLATFORM-209 (Integration) ←────────────────────┘
    ↓
PLATFORM-210 (Logging) → PLATFORM-212 (Analytics)

Parallel:
PLATFORM-203 (Docs) ─┐
PLATFORM-204 (Tests) ─┘ (can be done anytime after API)
PLATFORM-211 (Bulk) (can be done after UI)
```

### 5. Risk Assessment

**High Risk Stories:**
- PLATFORM-209 (Integration): Risk of breaking existing notification delivery
  - Mitigation: Feature flag, extensive testing, gradual rollout, fail-open with monitoring

**Blocking Stories:**
- PLATFORM-201 (Data Model): Blocks all other work
  - Impact: Entire epic blocked
  - Priority: Must be Sprint 1, Week 1

- PLATFORM-202 (API): Blocks all frontend work
  - Impact: UI cannot be built
  - Priority: Must be Sprint 1, deployed by end of week 1

### 6. Epic-Level Acceptance Criteria

- [ ] Users can view all notification types and their current preferences
- [ ] Users can enable/disable notification types
- [ ] Users can select delivery channels (email, in-app, Slack) per notification type
- [ ] Preferences persist across sessions and devices
- [ ] Notification service respects user preferences
- [ ] System handles edge cases (new notification types, service failures)
- [ ] Feature is accessible and meets WCAG 2.1 AA standards
- [ ] Analytics track adoption and usage

### 7. Labels & Organization

**Suggested Labels:** `notifications`, `user-preferences`, `settings`, `api`, `frontend`
**Components:** Notification Service, User Settings, API Gateway
**Fix Version:** Q2 2024

---

## Tips

- **Start with the foundation** - API and data model should come first
- **Keep stories small** - If a story is >8 points, break it down further
- **Map dependencies early** - Identify critical path and blockers
- **Include non-functional work** - Documentation, tests, and monitoring are important
- **Plan for unknowns** - Reserve 20% capacity for discovered work
- **Think in phases** - Group related stories into logical phases or themes

