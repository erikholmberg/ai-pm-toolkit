# Evaluation Plan Template

## Eval Overview

**Eval Name:** [Name of this evaluation]

**Date:** [Date]

**Owner:** [PM or researcher owning this eval]

**Objective:** [What decision will this eval inform?]

---

## Background

### What are we evaluating?
[Describe the system, feature, or prompt being evaluated]

### Why now?
[What triggered this eval? New feature, quality concerns, model change?]

### Key Questions
1. [Question this eval will answer]
2. [Question this eval will answer]
3. [Question this eval will answer]

---

## Scope

### In Scope
- [What's included in this eval]
- [What's included in this eval]

### Out of Scope
- [What's NOT included]
- [What's NOT included]

### Evaluation Type
- [ ] Prompt comparison
- [ ] Model comparison
- [ ] A/B test analysis
- [ ] Quality audit
- [ ] Safety review
- [ ] Other: [specify]

---

## Methodology

### Evaluation Dimensions
| Dimension | Weight | Measurement Method |
|-----------|--------|-------------------|
| [Dimension 1] | X% | [How measured] |
| [Dimension 2] | X% | [How measured] |
| [Dimension 3] | X% | [How measured] |

### Evaluation Method
- [ ] Human evaluation
- [ ] Automated metrics
- [ ] LLM-as-judge
- [ ] A/B test metrics
- [ ] Hybrid

### Rubrics
[Include scoring rubrics for each dimension, or link to rubric doc]

---

## Test Data

### Test Set Description
- **Source:** [Where the test data comes from]
- **Size:** [Number of test cases]
- **Composition:** [Types of inputs included]

### Test Case Categories
| Category | Count | Description |
|----------|-------|-------------|
| Happy path | X | Standard inputs |
| Edge cases | X | Boundary conditions |
| Adversarial | X | Challenging inputs |
| Segment-specific | X | By user type/use case |

### Golden Dataset
[Link to golden dataset or describe where it lives]

---

## Execution Plan

### Timeline
| Milestone | Date | Owner |
|-----------|------|-------|
| Test set ready | [Date] | [Name] |
| Eval runs complete | [Date] | [Name] |
| Analysis complete | [Date] | [Name] |
| Report delivered | [Date] | [Name] |

### Resources Required
- [ ] Human evaluators: [Number needed]
- [ ] Compute resources: [If applicable]
- [ ] External tools: [List tools]

### Evaluation Runs
| Run | Description | Config |
|-----|-------------|--------|
| Baseline | [Current system] | [Settings] |
| Variant A | [What's different] | [Settings] |
| Variant B | [What's different] | [Settings] |

---

## Success Criteria

### Minimum Bar
[What's the minimum quality level to pass?]

### Target
[What's the ideal outcome?]

### Decision Framework
| Result | Decision |
|--------|----------|
| [Variant A significantly better] | [Action] |
| [No significant difference] | [Action] |
| [Baseline better] | [Action] |

---

## Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| [Risk 1] | H/M/L | H/M/L | [Mitigation] |
| [Risk 2] | H/M/L | H/M/L | [Mitigation] |

---

## Stakeholders

| Role | Name | Involvement |
|------|------|-------------|
| Owner | [Name] | Day-to-day execution |
| Reviewer | [Name] | Reviews results |
| Decision Maker | [Name] | Final call |

---

## Appendix

### Related Documents
- [Link to PRD]
- [Link to previous evals]
- [Link to technical spec]

### Open Questions
- [Question needing resolution]
- [Question needing resolution]

