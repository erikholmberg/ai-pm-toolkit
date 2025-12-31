# Jira Ticket Creator

Transform user stories, PRDs, or feature descriptions into well-structured Jira tickets with proper fields, labels, and acceptance criteria.

## Usage

Replace the `[PLACEHOLDERS]` with your specific information.

---

## Prompt

```
You are an experienced Product Manager helping me create Jira tickets from feature descriptions.

## Context
- Project Key: [JIRA PROJECT KEY, e.g., PLATFORM]
- Issue Type: [Story/Bug/Task/Epic]
- Feature/Story: [DESCRIPTION OF WHAT NEEDS TO BE BUILT]
- Priority: [Blocker/Critical/Major/Minor/Trivial or P0/P1/P2]
- Target Sprint: [OPTIONAL - SPRINT NAME OR NUMBER]

## Additional Context
- Related Epic: [EPIC KEY IF APPLICABLE]
- Dependencies: [OTHER TICKETS OR SYSTEMS]
- Technical Notes: [ANY TECHNICAL CONSTRAINTS OR CONSIDERATIONS]
- User Persona: [WHO IS THIS FOR]

## Instructions

Generate a Jira ticket with the following structure:

### Summary
[Clear, concise title - max 255 characters, action-oriented]

### Description
**User Story:**
As a [user type], I want to [action] so that [benefit].

**Context:**
[2-3 sentences explaining why this matters and the problem it solves]

**Acceptance Criteria:**
- [ ] Given [context], when [action], then [expected result]
- [ ] Given [context], when [action], then [expected result]
- [ ] [Additional criteria as needed]

**Edge Cases:**
- [Edge case 1 and how it should be handled]
- [Edge case 2 and how it should be handled]

**Technical Notes:**
[Any implementation hints, API considerations, or technical constraints]

**Definition of Done:**
- [ ] Code reviewed and approved
- [ ] Unit tests written and passing
- [ ] Integration tests passing (if applicable)
- [ ] Documentation updated
- [ ] QA verified
- [ ] Product sign-off

### Additional Fields
**Labels:** [suggest 3-5 relevant labels, e.g., frontend, api, authentication]
**Components:** [if applicable]
**Fix Version:** [if applicable]
**Story Points:** [XS/S/M/L/XL with brief reasoning]

### Related Issues
- Blocks: [if this blocks other work]
- Is blocked by: [if this depends on other tickets]
- Relates to: [if related to other work]

---

Format the output so it can be easily copied into Jira's ticket creation form.
```

---

## Quick Version (Single Ticket)

```
Create a Jira ticket for this:

Feature: [DESCRIBE THE FEATURE IN 1-2 SENTENCES]
Project: [PROJECT KEY]
Type: [Story/Bug/Task]

Include:
- Summary (action-oriented title)
- User story format
- 3-5 acceptance criteria
- Story points estimate
- Relevant labels
```

---

## Example Input

```
- Project Key: PLATFORM
- Issue Type: Story
- Feature/Story: Allow users to customize notification preferences (email, in-app, Slack) to reduce notification fatigue
- Priority: P1
- User Persona: Platform developers who receive too many notifications
- Related Epic: PLATFORM-100 (Notification System Improvements)
- Technical Notes: Must integrate with existing notification service API
```

## Example Output

### Summary
Allow users to customize notification preferences by channel (email, in-app, Slack)

### Description

**User Story:**
As a platform developer, I want to customize which notifications I receive and through which channels (email, in-app, Slack) so that I can reduce notification fatigue and only see what's relevant to me.

**Context:**
Currently, all users receive all notifications via email, leading to notification fatigue and support tickets. This feature will allow users to selectively enable/disable notification types and choose their preferred delivery channels.

**Acceptance Criteria:**
- [ ] Given I am logged in, when I navigate to Settings > Notifications, then I see a list of all notification types with their current channel settings
- [ ] Given I am on the notifications page, when I toggle a notification type on/off, then the change is saved immediately
- [ ] Given I am configuring a notification type, when I select delivery channels (email, in-app, Slack), then at least one channel must be selected
- [ ] Given I have modified my settings, when I navigate away and return, then my preferences are persisted
- [ ] Given the notification service is unavailable, when I try to save settings, then I see a clear error message and my changes are not lost

**Edge Cases:**
- New notification types added after user setup → Default to enabled with all channels, highlight as "new"
- Notification service unavailable → Show cached settings with "last updated" timestamp, disable save button
- User has no channels selected → Prevent save, show validation error

**Technical Notes:**
- Integrate with existing `/api/v1/notifications/preferences` endpoint
- Use feature flag `notification-preferences-v2` for gradual rollout
- Cache preferences locally for offline viewing
- Consider rate limiting on save operations

**Definition of Done:**
- [ ] Code reviewed and approved
- [ ] Unit tests written and passing (coverage >80%)
- [ ] Integration tests for API calls
- [ ] UI/UX reviewed by design team
- [ ] Documentation updated (user guide + API docs)
- [ ] QA verified on staging
- [ ] Product sign-off
- [ ] Feature flag enabled for 10% rollout

### Additional Fields
**Labels:** notifications, settings, user-experience, frontend, api
**Components:** User Settings, Notification Service
**Fix Version:** Q2 2024
**Story Points:** M (Medium) - Requires frontend UI work, API integration, and state management

### Related Issues
- Relates to: PLATFORM-100 (Notification System Improvements Epic)
- Blocks: PLATFORM-145 (Notification Analytics Dashboard)

---

## Tips

- **Action-oriented summaries** - Start with a verb (e.g., "Add", "Implement", "Fix")
- **Specific acceptance criteria** - Use Given/When/Then format for clarity
- **Link related work** - Use "Relates to" for epics, "Blocks" for dependencies
- **Include context** - Help developers understand the "why" not just the "what"
- **Testable criteria** - Each acceptance criterion should be verifiable by QA

