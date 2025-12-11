# Developer Task Prompts

A library of prompts for common development tasks to share with your developer community.

## Usage

Share these prompts with developers to help them get more value from AI assistants. Customize for your tech stack.

---

## Code Review Assistant

```
Review this code for:
1. **Bugs:** Logic errors, edge cases, null handling
2. **Security:** Vulnerabilities, injection risks, auth issues
3. **Performance:** N+1 queries, unnecessary computation, memory leaks
4. **Readability:** Naming, structure, complexity
5. **Best Practices:** For [LANGUAGE/FRAMEWORK]

Be specific. For each issue:
- Line number or code section
- What's wrong
- How to fix it
- Severity (Critical/High/Medium/Low)

Code:
\`\`\`[language]
[PASTE CODE]
\`\`\`
```

---

## Debug Assistant

```
I'm debugging an issue. Help me find the root cause.

## Problem
[DESCRIBE WHAT'S HAPPENING]

## Expected Behavior
[WHAT SHOULD HAPPEN]

## Actual Behavior
[WHAT IS HAPPENING]

## Error Messages
\`\`\`
[PASTE ERROR OUTPUT]
\`\`\`

## Relevant Code
\`\`\`[language]
[PASTE RELEVANT CODE]
\`\`\`

## What I've Tried
- [ATTEMPT 1]
- [ATTEMPT 2]

## Help me:
1. Identify the most likely root cause
2. Suggest debugging steps to confirm
3. Propose a fix
```

---

## Test Generator

```
Generate tests for this code:

\`\`\`[language]
[PASTE CODE TO TEST]
\`\`\`

## Requirements
- Framework: [e.g., Jest, pytest, JUnit]
- Coverage: [Unit tests / Integration tests / Both]
- Style: [AAA pattern / Given-When-Then / etc.]

## Generate:
1. Happy path tests
2. Edge case tests (nulls, empty, boundaries)
3. Error handling tests
4. If applicable: mock setup for dependencies

Include comments explaining what each test validates.
```

---

## Documentation Generator

```
Generate documentation for this code:

\`\`\`[language]
[PASTE CODE]
\`\`\`

## Generate:

### 1. Code Comments
- Docstrings/JSDoc for all public functions
- Inline comments for complex logic

### 2. README Section
- What this does
- How to use it
- Example usage

### 3. API Documentation (if applicable)
- Endpoint description
- Request/response formats
- Error codes
```

---

## Refactoring Assistant

```
Refactor this code for better [GOAL: readability / performance / testability / maintainability]:

\`\`\`[language]
[PASTE CODE]
\`\`\`

## Constraints
- Maintain backward compatibility: [YES/NO]
- Framework version: [VERSION]
- Must preserve: [SPECIFIC REQUIREMENTS]

## Provide:
1. Refactored code
2. Explanation of changes
3. Before/after comparison of key improvements
4. Any breaking changes introduced
```

---

## API Design Review

```
Review this API design:

## Endpoint
- Method: [GET/POST/PUT/DELETE]
- Path: [/api/v1/...]
- Purpose: [WHAT IT DOES]

## Request
\`\`\`json
[REQUEST BODY/PARAMS]
\`\`\`

## Response
\`\`\`json
[RESPONSE BODY]
\`\`\`

## Review for:
1. RESTful conventions
2. Naming consistency
3. Error response format
4. Pagination/filtering (if applicable)
5. Security considerations
6. Versioning strategy
7. Documentation completeness

Suggest improvements with rationale.
```

---

## SQL Query Optimization

```
Optimize this SQL query:

\`\`\`sql
[PASTE QUERY]
\`\`\`

## Context
- Database: [PostgreSQL/MySQL/etc.]
- Table sizes: [APPROXIMATE ROW COUNTS]
- Existing indexes: [LIST IF KNOWN]
- Current performance: [EXECUTION TIME]

## Analyze:
1. Execution plan issues
2. Missing indexes
3. Query structure improvements
4. Potential rewrites

Provide optimized query with explanation.
```

---

## Error Message Improver

```
Improve these error messages for developers:

Current error messages:
1. "[ERROR MESSAGE 1]"
2. "[ERROR MESSAGE 2]"
3. "[ERROR MESSAGE 3]"

## Make them:
- Clear about what went wrong
- Actionable (what to do about it)
- Consistent in format
- Helpful for debugging

Provide improved versions with rationale.
```

---

## Regex Builder

```
I need a regex pattern for:

[DESCRIBE WHAT YOU NEED TO MATCH]

## Examples
Should match:
- [EXAMPLE 1]
- [EXAMPLE 2]

Should NOT match:
- [EXAMPLE 1]
- [EXAMPLE 2]

## Provide:
1. The regex pattern
2. Explanation of each part
3. Edge cases to watch for
4. Test cases to validate

Language: [JavaScript/Python/etc.]
```

---

## Code Explanation

```
Explain this code for a [JUNIOR/MID/SENIOR] developer:

\`\`\`[language]
[PASTE CODE]
\`\`\`

## Explain:
1. What it does (high-level)
2. How it works (step by step)
3. Why it's written this way (design decisions)
4. Key concepts to understand
5. Potential gotchas or edge cases

Use [LANGUAGE/FRAMEWORK] terminology appropriate for the audience.
```

---

## Commit Message Generator

```
Generate a commit message for these changes:

## What changed:
[DESCRIBE CHANGES OR PASTE DIFF]

## Follow:
- Conventional Commits format (feat/fix/docs/refactor/etc.)
- Max 50 chars for subject line
- Wrap body at 72 chars
- Include "why" not just "what"

Generate:
- Subject line
- Body (if needed)
- Footer (if breaking change)
```

---

## Tips for Developers Using AI

1. **Be specific** - Vague prompts get vague answers
2. **Include context** - Language, framework, constraints
3. **Show your work** - Include what you've already tried
4. **Ask for explanations** - Don't just copy-paste; understand
5. **Verify outputs** - AI can be confidently wrong
6. **Iterate** - First output is rarely perfect

