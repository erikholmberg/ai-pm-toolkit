# Prioritization Frameworks for Product Managers

A collection of frameworks for making prioritization decisions.

---

## Framework Overview

| Framework | Best For | Complexity | Team Buy-in |
|-----------|----------|------------|-------------|
| RICE | Feature prioritization | Medium | High |
| Impact/Effort Matrix | Quick decisions | Low | Medium |
| MoSCoW | Release planning | Low | High |
| Kano Model | Feature categorization | Medium | Medium |
| Weighted Scoring | Complex tradeoffs | High | High |
| ICE | Rapid prioritization | Low | Medium |
| Value vs. Complexity | Strategic planning | Low | Medium |

---

## 1. RICE Scoring

**Formula:** `RICE = (Reach × Impact × Confidence) / Effort`

### Components
- **Reach:** Users affected per time period (number)
- **Impact:** Effect on each user (0.25, 0.5, 1, 2, 3)
- **Confidence:** Certainty in estimates (50%, 80%, 100%)
- **Effort:** Person-months to build (number)

### When to Use
- Comparing features within same product area
- Need quantitative justification
- Have reasonable data for estimates

### Example
| Feature | Reach | Impact | Confidence | Effort | RICE |
|---------|-------|--------|------------|--------|------|
| Search improvements | 5000 | 2 | 80% | 2 | 4000 |
| New dashboard | 1000 | 3 | 50% | 3 | 500 |

---

## 2. Impact/Effort Matrix (2×2)

```
        │ Low Effort │ High Effort │
────────┼────────────┼─────────────┤
High    │  QUICK     │   MAJOR     │
Impact  │  WINS      │   PROJECTS  │
        │  (Do Now)  │  (Plan For) │
────────┼────────────┼─────────────┤
Low     │  FILL-INS  │   DON'T     │
Impact  │  (If Time) │   DO        │
────────┴────────────┴─────────────┘
```

### When to Use
- Quick triage sessions
- Limited information available
- Getting team alignment

### Plotting Tips
- Use relative positioning (not absolute)
- Cluster similar items
- Discuss disagreements on placement

---

## 3. MoSCoW Method

### Categories
- **Must Have:** Critical, non-negotiable. Launch fails without it.
- **Should Have:** Important but not critical. Painful to miss.
- **Could Have:** Nice to have. Include if time permits.
- **Won't Have:** Explicitly out of scope for this release.

### Application
```
Release 1.0 Planning:

MUST HAVE
- User authentication
- Core data import
- Basic reporting

SHOULD HAVE  
- Data export
- Email notifications
- Custom fields

COULD HAVE
- Dark mode
- Keyboard shortcuts
- Advanced filters

WON'T HAVE (this release)
- Mobile app
- Third-party integrations
- White-labeling
```

### When to Use
- Release planning and scoping
- Stakeholder alignment on priorities
- Defining MVP

---

## 4. Kano Model

### Categories
- **Basic (Must-Be):** Expected. Absence causes dissatisfaction; presence doesn't delight.
- **Performance (One-Dimensional):** More is better. Linear satisfaction increase.
- **Delighters (Attractive):** Unexpected. Absence is fine; presence delights.
- **Indifferent:** Users don't care either way.
- **Reverse:** Some users want it, others don't.

```
Satisfaction ▲
             │     ╱ Delighters
             │    ╱
             │   ╱  ╱─── Performance
─────────────┼──╱──╱─────────────▶ Feature Level
             │ ╱  ╱
             │╱  ╱
             │  ╱
             │ ╱
             │╱_____ Basic (invisible until missing)
```

### When to Use
- Understanding feature value perception
- Deciding between delight vs. reliability investments
- Product differentiation strategy

### Assessment Questions
- "How would you feel if this feature was present?"
- "How would you feel if this feature was absent?"

---

## 5. Weighted Scoring

### Setup
1. Define criteria (what matters)
2. Assign weights (how much each matters)
3. Score each option on each criterion
4. Calculate weighted totals

### Example

| Criterion | Weight | Feature A | Feature B | Feature C |
|-----------|--------|-----------|-----------|-----------|
| Revenue Impact | 30% | 4 | 2 | 5 |
| User Satisfaction | 25% | 5 | 4 | 3 |
| Strategic Fit | 20% | 3 | 5 | 4 |
| Effort (inverse) | 15% | 2 | 4 | 3 |
| Risk (inverse) | 10% | 4 | 3 | 2 |
| **Weighted Score** | | **3.75** | **3.45** | **3.65** |

### When to Use
- Complex decisions with multiple stakeholders
- Need transparent, defensible process
- Comparing very different initiatives

---

## 6. ICE Scoring

**Formula:** `ICE = Impact × Confidence × Ease`

All components scored 1-10.

### Components
- **Impact:** Potential positive effect
- **Confidence:** How sure we are it will work
- **Ease:** How easy to implement (inverse of effort)

### When to Use
- Rapid prioritization
- Growth experiments
- Quick wins identification

### Example
| Experiment | Impact | Confidence | Ease | ICE |
|------------|--------|------------|------|-----|
| New CTA color | 3 | 5 | 9 | 135 |
| Pricing test | 8 | 3 | 4 | 96 |
| Onboarding redesign | 7 | 6 | 2 | 84 |

---

## 7. Value vs. Complexity Matrix

```
          │ Low Complexity │ High Complexity │
──────────┼────────────────┼─────────────────┤
High      │    STRATEGIC   │    STRATEGIC    │
Value     │    QUICK WINS  │    BETS         │
          │                │                 │
──────────┼────────────────┼─────────────────┤
Low       │    INCREMENTAL │    MONEY        │
Value     │    IMPROVEMENTS│    PIT          │
──────────┴────────────────┴─────────────────┘
```

### When to Use
- Portfolio planning
- Resource allocation decisions
- Balancing quick wins vs. strategic investments

---

## Choosing the Right Framework

```
Start Here
    │
    ▼
How much time do you have?
    │
    ├── Minutes → Impact/Effort Matrix or ICE
    │
    ├── Hours → RICE or Weighted Scoring
    │
    └── Days → Full Kano analysis + Weighted Scoring

What are you deciding?
    │
    ├── What to build next → RICE
    │
    ├── What's in this release → MoSCoW
    │
    ├── How to delight users → Kano
    │
    └── Where to invest → Value/Complexity
```

---

## Framework Pitfalls to Avoid

### 1. Analysis Paralysis
- Don't over-engineer simple decisions
- Set time limits for prioritization sessions
- "Good enough" prioritization > perfect prioritization

### 2. Gaming the System
- Watch for inflated scores to push pet projects
- Require evidence for high scores
- Calibrate across teams

### 3. Ignoring Strategic Context
- Frameworks optimize within constraints
- Strategy should set constraints first
- Some things must be done regardless of score

### 4. False Precision
- 4.23 vs 4.21 is not meaningful
- Use bands/tiers instead of exact rankings
- Focus on clear winners and clear losers

### 5. Set and Forget
- Priorities change as context changes
- Re-evaluate periodically
- New information should update scores

---

## Running a Prioritization Session

### Preparation
1. Define what you're prioritizing (scope)
2. Choose appropriate framework
3. Gather relevant data
4. Invite right stakeholders

### Execution
1. Align on criteria and definitions (15 min)
2. Score/rate independently first
3. Discuss major disagreements
4. Converge on ranking
5. Document rationale

### Follow-up
1. Share decisions and reasoning
2. Connect to roadmap/planning
3. Revisit when assumptions change

