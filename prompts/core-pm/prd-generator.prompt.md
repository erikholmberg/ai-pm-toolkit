# PRD Generator

Generate comprehensive Product Requirements Documents from high-level feature descriptions.

## Usage

Replace the `[PLACEHOLDERS]` with your specific information and run with your preferred AI assistant.

---

## Prompt

```
You are an experienced Product Manager helping me write a comprehensive PRD (Product Requirements Document).

## Context
- Product/Feature Name: [FEATURE NAME]
- Product Area: [e.g., User Authentication, Data Pipeline, API Gateway]
- Target Users: [PRIMARY USER PERSONA]
- Business Context: [WHY NOW? WHAT PROBLEM ARE WE SOLVING?]

## Additional Context (if available)
- Existing documentation: [PASTE OR SUMMARIZE]
- Technical constraints: [ANY KNOWN LIMITATIONS]
- Dependencies: [OTHER TEAMS/SYSTEMS]

## Instructions

Generate a PRD with the following sections:

### 1. Overview
- Problem Statement (2-3 sentences)
- Proposed Solution (2-3 sentences)
- Success Metrics (3-5 measurable KPIs)

### 2. Background & Strategic Fit
- Why this matters now
- How it fits into the product strategy
- Competitive context (if relevant)

### 3. Goals & Non-Goals
- Explicit goals for this iteration
- Explicit non-goals (what we're NOT doing)

### 4. User Stories
Format each as: "As a [user type], I want to [action] so that [benefit]"
Include acceptance criteria for each story.

### 5. Requirements
#### Functional Requirements
- Numbered list with priority (P0/P1/P2)

#### Non-Functional Requirements
- Performance expectations
- Security requirements
- Scalability considerations

### 6. Design & UX
- Key user flows (describe step by step)
- Edge cases to handle
- Error states

### 7. Technical Considerations
- High-level architecture notes
- API contracts (if applicable)
- Data model changes
- Integration points

### 8. Launch Plan
- Rollout strategy (% rollout, feature flags)
- Beta/dogfooding plan
- Documentation needs
- Support/training requirements

### 9. Risks & Mitigations
| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|

### 10. Open Questions
- List any unresolved questions that need answers before development

### 11. Timeline & Milestones
- Key milestones with target dates
- Dependencies on other teams

---

Be specific and actionable. Avoid vague language. If you need more information to complete a section, note it as an open question.
```

---

## Example Input

```
- Product/Feature Name: AI-Powered Code Review Assistant
- Product Area: Developer Tools
- Target Users: Software Engineers on platform teams
- Business Context: Our developers spend 4+ hours/week on code reviews. We want to augment (not replace) human review with AI suggestions to catch common issues faster.
- Technical constraints: Must work with GitHub, cannot send code to external APIs (security requirement)
- Dependencies: ML Platform team for model serving
```

## Tips

- **Be specific about constraints** - The more context you provide, the better the output
- **Iterate** - Use the generated PRD as a starting point, then refine with follow-up prompts
- **Add your voice** - The AI will generate structure; you add the product intuition

