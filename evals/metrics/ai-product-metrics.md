# AI Product Metrics

What to measure for AI-powered products.

---

## Metric Categories

### 1. Quality Metrics

**What they measure:** How good is the AI output?

| Metric | Definition | How to Measure |
|--------|------------|----------------|
| Accuracy | % of outputs that are correct | Ground truth comparison, human eval |
| Relevance | How well output matches intent | Human rating, semantic similarity |
| Completeness | Whether all requirements met | Checklist scoring |
| Coherence | Logical flow and structure | Human rating |
| Hallucination Rate | % of outputs with false claims | Fact-checking, human review |

**Setting Quality Targets:**
- Start with baseline measurement
- Benchmark against alternatives (human, competitor, no-AI)
- Set targets based on user tolerance for errors
- Different use cases may need different bars

---

### 2. Performance Metrics

**What they measure:** How fast and reliable is the system?

| Metric | Definition | Target Range |
|--------|------------|--------------|
| Latency (p50) | Median response time | <1s for interactive |
| Latency (p99) | 99th percentile response | <3s for interactive |
| Throughput | Requests per second | Based on capacity plan |
| Availability | % uptime | 99.9%+ for production |
| Error Rate | % of requests that fail | <0.1% for production |

**Latency Considerations:**
- Streaming vs. complete response
- Cold start vs. warm
- Simple vs. complex queries

---

### 3. Cost Metrics

**What they measure:** How expensive is it to operate?

| Metric | Definition | How to Calculate |
|--------|------------|------------------|
| Cost per Request | Average cost per AI call | Total cost / request count |
| Cost per User | Daily/monthly cost per user | Total cost / active users |
| Token Efficiency | Output quality per token | Quality score / tokens used |
| Margin Impact | AI cost as % of revenue | AI cost / revenue |

**Cost Optimization Levers:**
- Model selection (smaller vs. larger)
- Caching frequent queries
- Prompt optimization
- Batching requests

---

### 4. User Experience Metrics

**What they measure:** How do users perceive and use the AI?

| Metric | Definition | How to Measure |
|--------|------------|----------------|
| Acceptance Rate | % of AI outputs users accept | Track accept/reject actions |
| Edit Rate | % of outputs users modify | Track edits after accept |
| Regeneration Rate | % of outputs users regenerate | Track regenerate clicks |
| Time Saved | Time reduction vs. manual | Before/after measurement |
| User Satisfaction | User rating of AI quality | Thumbs up/down, NPS |

**Interpreting UX Metrics:**
- Low acceptance → quality or UX issue
- High edit rate → close but not quite right
- High regeneration → inconsistent quality
- Declining satisfaction → model drift or changing expectations

---

### 5. Trust & Safety Metrics

**What they measure:** Is the AI safe and trustworthy?

| Metric | Definition | Target |
|--------|------------|--------|
| Safety Incident Rate | Harmful outputs / total | Near 0 |
| Bias Rate | Discriminatory outputs / total | Near 0 |
| Refusal Rate | Appropriate refusals | Based on policy |
| False Refusal Rate | Inappropriate refusals | <1% |
| PII Leakage Rate | PII in outputs when shouldn't | 0 |

**Safety Monitoring:**
- Automated classifiers for known harm types
- Human review sampling
- User reports
- Red team exercises

---

### 6. Business Impact Metrics

**What they measure:** What value does the AI deliver?

| Metric | Definition | How to Measure |
|--------|------------|----------------|
| Feature Adoption | % of eligible users using AI | Usage analytics |
| Retention Impact | Retention of AI users vs. non | Cohort analysis |
| Conversion Impact | AI feature effect on conversion | A/B test |
| Revenue Impact | Revenue attributable to AI | Attribution analysis |
| Efficiency Gain | Time/cost savings from AI | Before/after, sampling |

**Proving AI Value:**
- A/B test feature on/off
- Compare user cohorts (users vs. non-users)
- Survey users on value perception
- Track leading indicators (engagement, frequency)

---

## Metric Selection Guide

### For a New AI Feature

**Must Track:**
1. Quality (accuracy or acceptance rate)
2. Latency (user-facing)
3. Error rate
4. Cost per request
5. Adoption rate

**Nice to Track:**
- User satisfaction
- Edit/regeneration rates
- Safety metrics

### For a Mature AI Feature

**Add:**
1. Business impact metrics
2. Trend analysis (quality over time)
3. Segment breakdowns (by user type, use case)
4. Cost efficiency trends

---

## Dashboards

### Real-Time Dashboard
- Request volume
- Error rate
- Latency percentiles
- Cost (hourly/daily)

### Quality Dashboard
- Quality scores over time
- Acceptance/edit/regeneration rates
- User satisfaction trends
- Safety incidents

### Business Dashboard
- Adoption curve
- Active users
- Business impact metrics
- Cost vs. value

---

## Alerting

| Metric | Alert Threshold | Response |
|--------|-----------------|----------|
| Error rate | >1% | Page on-call |
| Latency p99 | >5s | Investigate |
| Quality score | Drop >10% | Review recent changes |
| Safety incident | Any | Immediate review |
| Cost spike | >2x normal | Investigate |

---

## Baseline & Target Setting

### How to Set Baselines
1. Measure current state (or pre-AI state)
2. Benchmark against alternatives
3. Establish "good enough" threshold
4. Document methodology

### How to Set Targets
1. What's the minimum viable quality?
2. What would delight users?
3. What's technically achievable?
4. What's the cost/quality tradeoff?

### Example Target Setting

| Metric | Baseline | Minimum | Target | Stretch |
|--------|----------|---------|--------|---------|
| Accuracy | 70% | 80% | 90% | 95% |
| Latency p50 | 3s | 2s | 1s | 500ms |
| Acceptance rate | - | 60% | 75% | 85% |
| Cost/request | $0.05 | $0.03 | $0.02 | $0.01 |

