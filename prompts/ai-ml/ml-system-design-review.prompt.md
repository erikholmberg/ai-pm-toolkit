# ML System Design Review

Evaluate ML system architecture decisions from a product perspective.

## Usage

This prompt helps PMs ask the right questions and understand tradeoffs in ML system designs.

---

## ML Architecture Review Prompt

```
You are an ML systems expert helping a Product Manager review a proposed ML system design.

## System Context
- Product/Feature: [WHAT THE ML FEATURE DOES]
- Business Goal: [WHAT SUCCESS LOOKS LIKE]
- User Context: [WHO USES IT, HOW, AND WHEN]

## Proposed Design
---
[PASTE THE TECHNICAL DESIGN DOC, ARCHITECTURE DIAGRAM DESCRIPTION, OR SUMMARY]

Include if available:
- Model type/approach
- Training data sources
- Inference architecture (batch vs real-time)
- Infrastructure choices
- Monitoring approach
---

## Review Framework

Analyze this design across the following dimensions:

### 1. Product-Model Fit
- Does this model type match the user problem?
- Are we solving the right problem with ML, or would rules/heuristics work?
- What's the cost of model errors for users?
- Is the expected accuracy sufficient for the use case?

### 2. Data Evaluation
- **Availability:** Do we have enough data to train this?
- **Quality:** What are the data quality risks?
- **Bias:** What populations might be underrepresented?
- **Freshness:** How quickly does the underlying data change?
- **Privacy:** Any PII or sensitive data concerns?

### 3. User Experience Implications
- **Latency:** Is inference speed acceptable for the UX?
- **Reliability:** What happens when the model fails or is unavailable?
- **Explainability:** Can we explain predictions to users if needed?
- **Feedback Loop:** Can users correct bad predictions?
- **Edge Cases:** How are low-confidence predictions handled?

### 4. Operational Considerations
- **Training Cost:** What's the compute cost to train/retrain?
- **Inference Cost:** What's the per-prediction cost at scale?
- **Monitoring:** How will we detect model degradation?
- **Retraining:** How often and how automated?
- **Rollback:** Can we revert to a previous model quickly?

### 5. Risks & Mitigation
| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|

### 6. Questions for the ML Team
Generate 5-7 questions the PM should ask the ML engineers.

### 7. MVP vs. Future State
- What's the simplest version that delivers value?
- What capabilities should we defer?
- What does v2 look like?

### 8. Go/No-Go Recommendation
Based on this review:
- ✅ Proceed as designed
- 🟡 Proceed with modifications: [WHAT CHANGES]
- 🔴 Reconsider approach: [WHY]
```

---

## Quick Design Sanity Check

```
I'm reviewing an ML feature proposal. Help me do a quick sanity check.

## Feature
[ONE PARAGRAPH DESCRIBING THE ML FEATURE]

## Proposed Approach
[ONE PARAGRAPH ON THE TECHNICAL APPROACH]

## Questions to Answer

1. **Is ML the right tool?**
   - Could we achieve 80% of the value with rules?
   - What's the ML buying us?

2. **Data reality check:**
   - Do we have the data to train this?
   - What's the labeling strategy?

3. **Error tolerance:**
   - What's the cost of a wrong prediction?
   - How will users experience errors?

4. **Complexity vs. value:**
   - Is the complexity justified by the user value?
   - What's the maintenance burden?

5. **Red flags to watch for:**
   - List any concerns about this approach
```

---

## Model Tradeoff Discussion Guide

```
Help me facilitate a tradeoff discussion with my ML team.

## Context
We're deciding between approaches for: [FEATURE DESCRIPTION]

## Options on the Table
1. [OPTION A]: [BRIEF DESCRIPTION]
2. [OPTION B]: [BRIEF DESCRIPTION]
3. [OPTION C]: [BRIEF DESCRIPTION]

## Create a comparison framework:

### Tradeoff Matrix
| Dimension | Option A | Option B | Option C |
|-----------|----------|----------|----------|
| Accuracy | | | |
| Latency | | | |
| Cost | | | |
| Time to Build | | | |
| Maintenance | | | |
| Explainability | | | |
| Scalability | | | |

### Questions to Resolve
- [KEY QUESTION 1]
- [KEY QUESTION 2]

### Recommendation Criteria
What would make us choose each option? Define the conditions.

### Decision Framework
How should we make this decision? What data would help?
```

---

## Tips for PM-ML Collaboration

- **Don't pretend to be an ML expert** - Ask "help me understand" questions
- **Focus on user impact** - Always bring it back to what users experience
- **Push on data quality** - "Where does this data come from?" is always valid
- **Ask about failure modes** - "What happens when this is wrong?"
- **Understand the confidence** - "How confident are we in this working?"
- **Question the timeline** - ML projects often take longer; add buffer
- **Plan for iteration** - First version is rarely good enough

