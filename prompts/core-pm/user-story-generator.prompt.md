# User Story Generator

Transform feature descriptions into well-structured user stories with acceptance criteria.

## Usage

Replace the `[PLACEHOLDERS]` with your specific information.

---

## Prompt

```
You are an experienced Product Manager helping me break down a feature into user stories.

## Feature Context
- Feature Name: [FEATURE NAME]
- Feature Description: [HIGH-LEVEL DESCRIPTION OF WHAT WE'RE BUILDING]
- Primary Users: [WHO WILL USE THIS]
- Business Goal: [WHAT SUCCESS LOOKS LIKE]

## Additional Context
- Technical constraints: [ANY KNOWN LIMITATIONS]
- Existing patterns: [HOW SIMILAR FEATURES WORK TODAY]
- Sprint capacity: [OPTIONAL - HELPS SIZE STORIES]

## Instructions

Generate user stories following this format:

### Story Format
**Title:** [Short descriptive title]

**User Story:** As a [specific user type], I want to [concrete action] so that [measurable benefit].

**Acceptance Criteria:**
- [ ] Given [context], when [action], then [expected result]
- [ ] Given [context], when [action], then [expected result]
- [ ] [Additional criteria as needed]

**Edge Cases:**
- What happens if [edge case 1]?
- What happens if [edge case 2]?

**Technical Notes:** [Optional implementation hints]

**Story Points Estimate:** [XS/S/M/L/XL with reasoning]

---

## Requirements for Good Stories

1. **Independent** - Can be developed without depending on other stories
2. **Negotiable** - Details can be discussed, not a contract
3. **Valuable** - Delivers value to the user
4. **Estimable** - Team can estimate effort
5. **Small** - Fits in a sprint (break down if larger)
6. **Testable** - Clear pass/fail criteria

## Output Structure

Organize stories by:
1. **Must Have (P0)** - Core functionality, blocks launch
2. **Should Have (P1)** - Important but not blocking
3. **Nice to Have (P2)** - Enhancements for later

For each priority level, order stories by logical implementation sequence.

---

Generate [NUMBER OR "comprehensive"] user stories for this feature.
```

---

## Quick Version (Single Story)

```
Convert this into a user story with acceptance criteria:

Feature: [DESCRIBE THE FEATURE IN 1-2 SENTENCES]

User: [WHO IS THE USER]

Use the format:
- User Story: As a [user], I want to [action] so that [benefit]
- Acceptance Criteria (Given/When/Then format)
- Edge cases to consider
- Suggested story points (XS/S/M/L/XL)
```

---

## Example Input

```
- Feature Name: Notification Preferences
- Feature Description: Allow users to customize which notifications they receive and through which channels (email, in-app, Slack)
- Primary Users: Platform developers who receive too many notifications
- Business Goal: Reduce notification fatigue and support ticket volume by 30%
- Technical constraints: Must integrate with existing notification service
- Existing patterns: Currently all-or-nothing email notifications
```

## Example Output

### Must Have (P0)

**Title:** View Current Notification Settings

**User Story:** As a platform developer, I want to see my current notification settings so that I understand what notifications I'm receiving.

**Acceptance Criteria:**
- [ ] Given I am logged in, when I navigate to Settings > Notifications, then I see a list of all notification types
- [ ] Given I am on the notifications page, when I view a notification type, then I see which channels are enabled (email, in-app, Slack)
- [ ] Given I have never modified settings, when I view the page, then I see the default settings clearly labeled

**Edge Cases:**
- What if the notification service is unavailable? → Show cached settings with "last updated" timestamp
- What if a new notification type was added? → Default to enabled, highlight as "new"

**Story Points Estimate:** S - Mostly UI work with one API call

---

## Tips

- **Start with the happy path** - Get core stories first, then edge cases
- **Use real user language** - Avoid technical jargon in the story itself
- **One thing per story** - If you see "and" in the action, consider splitting
- **Acceptance criteria are testable** - QA should be able to verify each one

