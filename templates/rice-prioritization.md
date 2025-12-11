# RICE Prioritization Framework

A systematic framework for prioritizing features based on Reach, Impact, Confidence, and Effort.

## Overview

RICE is a scoring model that helps teams make objective prioritization decisions by evaluating:
- **R**each: How many users will this affect?
- **I**mpact: How much will it affect them?
- **C**onfidence: How sure are we about our estimates?
- **E**ffort: How much work will it take?

**RICE Score = (Reach × Impact × Confidence) / Effort**

---

## Scoring Guidelines

### Reach (R)
How many users/customers will this impact in a given time period?

| Score | Definition | Example |
|-------|------------|---------|
| 10000+ | Impacts all users | Core platform stability |
| 1000-9999 | Impacts most users | Dashboard redesign |
| 100-999 | Impacts a segment | Enterprise feature |
| 10-99 | Impacts few users | Niche integration |
| 1-9 | Impacts handful | Single customer request |

**Tips:**
- Define your time period (per quarter is common)
- Use actual data where possible (DAU, feature usage)
- For new features, estimate based on similar features

### Impact (I)
How much will this affect each user reached?

| Score | Definition | Example |
|-------|------------|---------|
| 3 | Massive impact | Solves critical pain, 10x improvement |
| 2 | High impact | Significant improvement, big time saver |
| 1 | Medium impact | Noticeable improvement |
| 0.5 | Low impact | Nice to have |
| 0.25 | Minimal impact | Minor polish |

**Tips:**
- Be honest—most features are 0.5-1 impact
- 3s should be rare (1-2 per roadmap)
- Consider both frequency and intensity of the problem

### Confidence (C)
How confident are we in our Reach and Impact estimates?

| Score | Definition | When to Use |
|-------|------------|-------------|
| 100% | High confidence | Strong data, validated with users |
| 80% | Medium confidence | Some data, reasonable assumptions |
| 50% | Low confidence | Gut feeling, limited research |

**Tips:**
- Discount uncertain bets appropriately
- Low confidence isn't bad—just be aware
- Consider quick validation to increase confidence

### Effort (E)
How much work will this take? (Person-months)

| Score | Definition | Example |
|-------|------------|---------|
| 0.5 | Trivial | Half a person-month, quick fix |
| 1 | Small | One person-month |
| 2 | Medium | Two person-months |
| 3 | Large | Quarter of a team |
| 6+ | Very large | Multi-quarter initiative |

**Tips:**
- Include design, engineering, QA, documentation
- Get engineering input on effort
- Round to nearest 0.5

---

## Template

### Feature Scoring Table

| Feature | Reach | Impact | Confidence | Effort | RICE Score | Priority |
|---------|-------|--------|------------|--------|------------|----------|
| Feature A | | | | | | |
| Feature B | | | | | | |
| Feature C | | | | | | |

### Detailed Feature Assessment

#### Feature: [Feature Name]

**Description:** [One sentence]

**Reach:** [Score] 
- Reasoning: [Why this number]
- Data source: [Where did this come from]

**Impact:** [Score]
- Reasoning: [Why this number]
- User benefit: [What problem it solves]

**Confidence:** [Score]
- Data we have: [What supports this]
- Data we need: [What would increase confidence]

**Effort:** [Score]
- Engineering estimate: [From whom]
- Breakdown: [Design/Eng/QA]

**RICE Score:** [Calculated]

**Decision:** [Prioritize / Deprioritize / Investigate further]

---

## Example

| Feature | Reach | Impact | Confidence | Effort | RICE Score |
|---------|-------|--------|------------|--------|------------|
| API rate limiting dashboard | 500 | 2 | 80% | 1.5 | 533 |
| Slack notifications | 2000 | 1 | 100% | 2 | 1000 |
| Advanced search | 800 | 2 | 50% | 3 | 267 |
| Onboarding redesign | 1500 | 3 | 80% | 4 | 900 |
| Dark mode | 3000 | 0.5 | 100% | 1 | 1500 |

**Priority Order:** Dark mode > Slack notifications > Onboarding > API dashboard > Search

---

## When to Use RICE

**Good for:**
- Comparing features within the same product area
- Making tradeoffs between known opportunities
- Communicating prioritization rationale

**Not ideal for:**
- Comparing across very different initiatives
- Strategic bets that don't have measurable reach
- Urgent bug fixes or tech debt

---

## Common Pitfalls

1. **Inflating impact scores** - Be brutally honest; not everything is a 2 or 3
2. **Ignoring confidence** - Uncertain high-scorers often disappoint
3. **Underestimating effort** - Get engineering reality checks
4. **Over-indexing on RICE alone** - It's input, not gospel
5. **Comparing apples to oranges** - RICE works best within similar contexts

---

## Combining with Strategy

RICE helps optimize within a strategic frame. Start by asking:
1. What are our strategic bets this quarter?
2. What must we do (compliance, stability)?
3. What's left to prioritize with RICE?

Use RICE for category 3, not to override 1 and 2.

