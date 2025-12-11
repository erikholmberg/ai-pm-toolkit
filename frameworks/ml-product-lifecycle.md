# ML Product Lifecycle

A framework for understanding and managing ML-powered products through their lifecycle.

---

## Overview

ML products have unique lifecycle considerations compared to traditional software. This framework helps PMs navigate each stage.

```
┌─────────────────────────────────────────────────────────────────┐
│                      ML Product Lifecycle                        │
├──────────┬──────────┬──────────┬──────────┬──────────┬──────────┤
│ Problem  │  Data    │  Model   │  Deploy  │ Monitor  │  Iterate │
│ Framing  │  Prep    │  Dev     │  Launch  │  Operate │  Improve │
└──────────┴──────────┴──────────┴──────────┴──────────┴──────────┘
     1          2          3          4          5          6
```

---

## Stage 1: Problem Framing

### PM Responsibilities
- Define the user problem and success criteria
- Determine if ML is the right solution
- Set performance requirements
- Align stakeholders on scope

### Key Questions

**Is ML the Right Approach?**
- Can a human do this task? (If no, ML probably can't either)
- Is there a simpler heuristic that gets 80% of the value?
- Do we have or can we get the data?
- Is the cost/complexity justified by the value?

**Problem Definition:**
- What are we predicting/classifying/generating?
- What inputs are available at prediction time?
- What latency is acceptable?
- What's the cost of errors (false positives vs false negatives)?

**Success Criteria:**
| Metric | Threshold | Rationale |
|--------|-----------|-----------|
| Accuracy | ≥X% | [Why this threshold] |
| Latency | ≤Xms | [User experience requirement] |
| Business KPI | [Target] | [Connection to value] |

### Deliverables
- [ ] Problem statement document
- [ ] ML feasibility assessment
- [ ] Success metrics defined
- [ ] Stakeholder alignment

### Common Pitfalls
- ❌ Jumping to ML without evaluating alternatives
- ❌ Vague success criteria ("make it smart")
- ❌ Ignoring data availability
- ❌ Underestimating error tolerance requirements

---

## Stage 2: Data Preparation

### PM Responsibilities
- Ensure data availability and quality
- Navigate data access and privacy requirements
- Define labeling requirements and strategy
- Balance data needs with timeline

### Key Questions

**Data Availability:**
- What data do we have today?
- What data do we need but don't have?
- How will we collect labels/ground truth?
- What's the data freshness requirement?

**Data Quality:**
- What's the data quality? (missing values, errors)
- Is the data representative of production?
- Are there known biases in the data?
- How will data quality be maintained over time?

**Data Access:**
- Do we have legal rights to use this data?
- Are there privacy concerns?
- Who needs to approve data access?
- How long can we retain the data?

### Labeling Strategy Options
| Strategy | Pros | Cons | Best For |
|----------|------|------|----------|
| Manual labeling | High quality | Expensive, slow | Complex tasks |
| Crowdsourcing | Scalable | Variable quality | Simple tasks |
| Programmatic | Fast, cheap | May have errors | Clear rules |
| User feedback | Free, relevant | Sparse, biased | Implicit signals |
| Existing labels | No extra work | May not fit task | Adjacent tasks |

### Deliverables
- [ ] Data inventory and gaps identified
- [ ] Data access approvals obtained
- [ ] Labeling strategy and timeline
- [ ] Data quality assessment

### Common Pitfalls
- ❌ Assuming data exists and is usable
- ❌ Underestimating labeling effort
- ❌ Training on data that won't be available at inference
- ❌ Ignoring data biases

---

## Stage 3: Model Development

### PM Responsibilities
- Provide clear requirements to ML team
- Make tradeoff decisions (accuracy vs latency, etc.)
- Review evaluation results
- Ensure model meets product requirements

### Key Questions

**Model Requirements:**
- What's the accuracy/quality bar?
- What's the latency requirement?
- What's the cost budget for inference?
- What explainability is needed?

**Tradeoffs:**
| Tradeoff | Option A | Option B | Decision Factor |
|----------|----------|----------|-----------------|
| Accuracy vs Latency | More accurate, slower | Less accurate, faster | UX requirements |
| Complexity vs Maintainability | Better performance | Easier to maintain | Team capacity |
| Generalization vs Specialization | Works broadly | Works well for segment | User diversity |

### Evaluation Checklist
- [ ] Model meets accuracy thresholds
- [ ] Performance consistent across user segments
- [ ] Latency within requirements
- [ ] Model behavior on edge cases acceptable
- [ ] Failure modes understood and documented

### Deliverables
- [ ] Model selection decision documented
- [ ] Evaluation results reviewed
- [ ] Model card created
- [ ] Known limitations documented

### Common Pitfalls
- ❌ Optimizing for wrong metric
- ❌ Not testing on production-like data
- ❌ Ignoring edge cases and failure modes
- ❌ Over-engineering for marginal gains

---

## Stage 4: Deployment & Launch

### PM Responsibilities
- Define rollout strategy
- Coordinate cross-functional launch activities
- Define rollback criteria
- Manage stakeholder communications

### Rollout Strategy Options

| Strategy | Description | Risk Level | Best For |
|----------|-------------|------------|----------|
| Shadow mode | Run parallel, don't affect users | Low | First deployment |
| Canary | Small % of traffic | Low-Medium | Validating in production |
| A/B test | Random split for comparison | Medium | Measuring impact |
| Staged rollout | Gradual % increase | Medium | Broad rollout |
| Big bang | All users at once | High | Time-sensitive launches |

### Launch Checklist
- [ ] Shadow/canary testing completed
- [ ] Rollback mechanism tested
- [ ] Monitoring and alerting in place
- [ ] On-call team trained
- [ ] User documentation ready
- [ ] Support team briefed
- [ ] Rollout plan approved

### Rollback Criteria
Define specific conditions that trigger rollback:
- Error rate exceeds X%
- Latency p99 exceeds Xms
- User complaints exceed X
- Business metric drops by X%

### Deliverables
- [ ] Rollout plan
- [ ] Rollback runbook
- [ ] Launch communications sent
- [ ] Success metrics being tracked

---

## Stage 5: Monitoring & Operations

### PM Responsibilities
- Monitor model performance and business impact
- Review alerts and incidents
- Decide when retraining is needed
- Balance operational investment

### Monitoring Dimensions

**Model Performance:**
- Prediction accuracy (if labels available)
- Confidence score distribution
- Prediction distribution (shift detection)
- Latency and throughput

**Data Quality:**
- Input data drift (feature distributions)
- Missing value rates
- Schema violations
- Data freshness

**Business Metrics:**
- User engagement with feature
- Task completion rates
- Error/complaint rates
- Business KPIs

### Alert Triage Framework
| Severity | Examples | Response Time | Escalation |
|----------|----------|---------------|------------|
| P1 | Model down, major errors | <15 min | On-call → PM |
| P2 | Performance degradation | <2 hours | On-call |
| P3 | Minor drift detected | <1 day | Weekly review |
| P4 | Optimization opportunity | Next sprint | Backlog |

### Deliverables
- [ ] Monitoring dashboards created
- [ ] Alert thresholds defined
- [ ] On-call runbooks created
- [ ] Weekly review process established

---

## Stage 6: Iteration & Improvement

### PM Responsibilities
- Analyze performance and identify improvement opportunities
- Prioritize model improvements vs new features
- Manage technical debt
- Plan model lifecycle (updates, deprecation)

### Improvement Levers

| Lever | Effort | Impact | When to Use |
|-------|--------|--------|-------------|
| More training data | Low-Medium | Medium | Accuracy plateau |
| Better labels | Medium | High | Label noise issues |
| Feature engineering | Medium | Medium-High | Domain knowledge available |
| Model architecture | High | Variable | Fundamental limitations |
| Hyperparameter tuning | Low | Low-Medium | Quick wins |
| Prompt engineering (LLMs) | Low | Medium-High | LLM-based features |

### Retraining Triggers
- [ ] Scheduled (weekly/monthly)
- [ ] Performance degradation detected
- [ ] Significant data drift
- [ ] New data source available
- [ ] User feedback indicates issues

### Version Management
| Aspect | Strategy |
|--------|----------|
| Model versioning | Semantic versioning (major.minor.patch) |
| A/B testing | Champion/challenger framework |
| Rollback | Keep N previous versions deployable |
| Deprecation | X weeks notice, migration support |

### Deliverables
- [ ] Improvement backlog maintained
- [ ] Retraining strategy defined
- [ ] Version management in place
- [ ] Deprecation policy documented

---

## Lifecycle Metrics Summary

### By Stage

| Stage | Key Metrics |
|-------|-------------|
| 1. Problem | Problem clarity, stakeholder alignment |
| 2. Data | Data coverage, label quality, pipeline reliability |
| 3. Model | Offline accuracy, evaluation coverage |
| 4. Deploy | Rollout velocity, incident count |
| 5. Monitor | Model health, alert volume, MTTR |
| 6. Iterate | Improvement velocity, model freshness |

### Overall ML Product Health
- 📊 Model accuracy/quality
- ⏱️ Latency p50/p99
- 🔥 Error rate
- 📈 Feature adoption
- 💰 Business impact
- 🔧 Operational burden

---

## PM Skills by Stage

| Stage | Technical Skills | Product Skills |
|-------|------------------|----------------|
| 1. Problem | ML basics, feasibility | User research, strategy |
| 2. Data | Data understanding, privacy | Requirements, prioritization |
| 3. Model | Metrics, tradeoffs | Decision-making, communication |
| 4. Deploy | Infrastructure basics | Launch management, coordination |
| 5. Monitor | Dashboards, alerts | Incident response, escalation |
| 6. Iterate | Performance analysis | Roadmapping, stakeholder management |

