# SPACE Framework for Team Health

A framework for assessing developer productivity and team health beyond velocity alone. SPACE stands for **Satisfaction**, **Performance**, **Activity**, **Communication**, and **Efficiency**. Use it to get a balanced view of team health and identify improvement areas.

---

## Overview

Velocity (story points completed) captures only one dimension. SPACE helps you:

- Avoid over-indexing on output metrics that can incentivize gaming or burnout
- Balance quantitative metrics with qualitative signals
- Identify root causes when velocity drops
- Have productive conversations in retrospectives

```
┌─────────────────────────────────────────────────────────────────────┐
│                        SPACE Framework                               │
├──────────────┬──────────────┬──────────────┬──────────────┬─────────┤
│ Satisfaction │ Performance  │ Activity     │ Communication│Efficiency│
│              │              │              │              │         │
│ How people   │ Outcomes &   │ Counts of    │ Coordination │ Flow &  │
│ feel about   │ results      │ actions      │ & info flow  │ focus   │
│ their work   │              │              │              │         │
└──────────────┴──────────────┴──────────────┴──────────────┴─────────┘
```

---

## 1. Satisfaction

**What it measures:** Well-being, sense of efficacy, and fulfillment.

### Indicators

| Signal | How to Measure | Green | Yellow | Red |
|--------|----------------|-------|--------|-----|
| **Developer satisfaction** | Survey (e.g., eNPS, "I enjoy my work") | ≥ 8/10 | 6–7 | < 6 |
| **Burnout risk** | "I have sustainable workload" | Agree | Neutral | Disagree |
| **Sense of impact** | "My work matters to users" | Agree | Mixed | Disagree |
| ** psychological safety** | "I can raise concerns without fear" | Agree | Neutral | Disagree |

### Data Sources

- Pulse surveys (quarterly or after major releases)
- 1:1 themes (recurring concerns)
- Exit interview patterns
- Absence / sick day trends

### PM Actions

- Include satisfaction in retro discussions
- Don't celebrate velocity at the cost of sustainability
- Address workload and scope creep explicitly
- Protect focus time and discourage always-on culture

---

## 2. Performance

**What it measures:** Outcomes and results — what was achieved.

### Indicators

| Signal | How to Measure | Notes |
|--------|----------------|-------|
| **Delivery** | Velocity, features shipped, releases | Use with trend, not single number |
| **Quality** | Bug escape rate, post-release incidents | Fewer incidents = better performance |
| **User impact** | Adoption, NPS, support volume | Connects output to value |
| **Reliability** | Uptime, SLO compliance | Especially for platform/AI products |

### Caveats

- Performance metrics can be gamed (velocity inflation, quality shortcuts)
- Always pair with Satisfaction — high performance + low satisfaction = burnout risk
- Use relative trends: "Are we improving?" not "Did we hit 50 points?"

### PM Actions

- Set realistic targets informed by capacity
- Celebrate outcomes (shipped, adopted) not just output (points)
- Investigate drops before increasing pressure

---

## 3. Activity

**What it measures:** Counts of actions — commits, PRs, deployments, reviews.

### Indicators

| Signal | How to Measure | Green | Yellow | Red |
|--------|----------------|-------|--------|-----|
| **Code contributions** | Commits, PRs (per dev, trend) | Stable/up | Slight drop | Sharp drop |
| **Code reviews** | PRs reviewed, time to review | < 24h median | 24–48h | > 48h |
| **Deployments** | Deploy frequency | Regular | Irregular | Rare |
| **Collaboration** | Pairing, design discussions | Visible | Limited | Minimal |

### Caveats

- Activity ≠ performance. More commits doesn't mean better software.
- Use to spot disengagement (sudden drop) or overload (no reviews done).
- Activity is a leading indicator; satisfaction and performance are lagging.

### PM Actions

- Use activity to detect "someone checked out" or "bottleneck in reviews"
- Don't optimize for activity metrics; optimize for outcomes
- If activity is high but performance is flat, look at efficiency and focus

---

## 4. Communication

**What it measures:** Coordination and information flow.

### Indicators

| Signal | How to Measure | Green | Yellow | Red |
|--------|----------------|-------|--------|-----|
| **Response time** | Time to reply in Slack, email | < 4h | 4–24h | > 24h |
| **Info sharing** | Docs updated, decisions recorded | Current | Stale | Missing |
| **Cross-team** | Dependencies unblocked, handoffs smooth | Yes | Delays | Blocked |
| **Meeting quality** | "Meetings are productive" (survey) | Agree | Mixed | Disagree |

### Data Sources

- Communication tools (Slack, email analytics)
- Documentation freshness
- Blocker logs, dependency tracking
- Retro themes ("waiting on X" recurring)

### PM Actions

- Reduce meetings that don't create decisions or alignment
- Make dependencies explicit and track unblocking
- Document decisions; avoid "meeting archaeology"
- Create async-first defaults where possible

---

## 5. Efficiency

**What it measures:** Flow and focus — lack of friction.

### Indicators

| Signal | How to Measure | Green | Yellow | Red |
|--------|----------------|-------|--------|-----|
| **Cycle time** | Ticket created → done | < 1 week | 1–2 weeks | > 2 weeks |
| **Lead time** | Request to delivery | Predictable | Variable | Unpredictable |
| **WIP** | In-progress items per dev | ≤ 2 | 2–3 | > 3 |
| **Context switching** | Interruptions, fragmented focus | Low | Medium | High |
| **Flow time** | % of day in deep work | ≥ 3h | 1–3h | < 1h |

### Data Sources

- Jira/Linear cycle time, lead time
- WIP limits and board status
- Developer surveys ("I have enough focus time")

### PM Actions

- Limit WIP; finish before starting
- Batch meetings; protect focus blocks
- Reduce approval bottlenecks and unnecessary gates
- Use capacity planning to avoid overcommitment

---

## SPACE Assessment Template

Use this to run a lightweight team health check.

### Quick Check (5 min)

| Dimension | Score 1–5 | One-line note |
|-----------|-----------|----------------|
| Satisfaction | | |
| Performance | | |
| Activity | | |
| Communication | | |
| Efficiency | | |

**Overall:** Average score _____  
**Focus area:** Lowest dimension = _________________________________

### Detailed Assessment (30 min)

```markdown
## Team: [NAME]
## Date: [DATE]
## Period: [e.g., Last 4 sprints]

### Satisfaction
- [ ] Survey results reviewed
- [ ] 1:1 themes aggregated
- [ ] Concerns: ___________________________
- [ ] Strengths: ___________________________

### Performance
- [ ] Velocity trend: __________ (up / flat / down)
- [ ] Quality: Bugs ________, Incidents ________
- [ ] User impact: ___________________________

### Activity
- [ ] PR/commit trend: _______________________
- [ ] Review turnaround: _____________________
- [ ] Deployment frequency: __________________

### Communication
- [ ] Blocker recurrence: _____________________
- [ ] Doc freshness: _________________________
- [ ] Cross-team handoffs: ___________________

### Efficiency
- [ ] Cycle time: ____________________________
- [ ] WIP per person: _______________________
- [ ] Focus time: ___________________________

### Prioritized Actions
1. _________________________________________
2. _________________________________________
3. _________________________________________
```

---

## Using SPACE in Retrospectives

1. **Pick 1–2 dimensions** — Don't assess all five every retro. Rotate or focus on what's hurting.
2. **Lead with data, then discussion** — "Cycle time is up 30%. What's changed?" not "How do you feel?"
3. **Connect dimensions** — "Velocity dropped and satisfaction dropped. Could efficiency (context switching) be the link?"
4. **Commit to one action** — One concrete improvement per dimension per quarter.

---

## Pitfalls to Avoid

### 1. Over-Measurement
- Don't track everything. Pick 2–3 metrics per dimension.
- Satisfaction and Efficiency often explain Performance; measure those first.

### 2. Gaming
- Activity and Performance can be gamed. Satisfaction and Efficiency are harder to fake.
- If metrics improve but qualitative feedback worsens, dig deeper.

### 3. Velocity as the Only Signal
- Velocity is Performance, not the whole story.
- A team can have high velocity and low Satisfaction (burnout) or low Efficiency (heroics, tech debt).

### 4. Ignoring Interdependencies
- Poor Communication → blocked work → low Efficiency → low Performance → low Satisfaction.
- Fix root causes, not symptoms.

---

## References

- Forsgren, N., Storey, M.-A., Maddila, C., Zimmermann, T., Houck, B., & Butler, J. (2021). *The SPACE of Developer Productivity*. ACM Queue.
- DORA metrics (Deployment Frequency, Lead Time, MTTR, Change Failure Rate) align with Performance and Efficiency.

