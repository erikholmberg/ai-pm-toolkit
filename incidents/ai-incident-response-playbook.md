# AI Incident Response Playbook

How to respond when AI features go wrong.

---

## Incident Severity Levels

| Level | Definition | Examples | Response Time |
|-------|------------|----------|---------------|
| **SEV1** | Critical, affecting many users, safety risk | AI generating harmful content, major outage | Immediate |
| **SEV2** | Significant, affecting subset of users | Quality degradation, elevated errors | <1 hour |
| **SEV3** | Moderate, noticeable but contained | Specific edge case failures | <4 hours |
| **SEV4** | Minor, minimal user impact | Cosmetic issues, minor quality dip | Next business day |

---

## Incident Response Phases

### Phase 1: Detection & Alert

**Detection Sources:**
- Automated monitoring alerts
- User reports / support tickets
- Internal discovery
- Social media mentions

**Initial Actions:**
1. Acknowledge the alert
2. Assess initial severity
3. Page appropriate responders
4. Open incident channel (Slack, Teams, etc.)

**Roles:**
- **Incident Commander (IC):** Owns response, makes decisions
- **Technical Lead:** Investigates and fixes
- **Comms Lead:** Handles stakeholder communication

---

### Phase 2: Triage & Diagnosis

**Quick Assessment (First 15 Minutes):**
1. What is the impact scope? (% users, specific segments)
2. When did it start?
3. What changed recently? (deployments, model updates, data changes)
4. Is it getting worse?

**AI-Specific Diagnosis Questions:**
- Is the model itself broken or infrastructure?
- Is this a quality issue or a safety issue?
- Is it affecting all users or specific inputs/segments?
- Have we seen this failure mode before?
- Did training data or model version change?

**Data to Gather:**
- Error logs
- Quality metrics (before vs. during incident)
- Request/response samples
- Recent deployment history
- Model version in production

---

### Phase 3: Containment

**Containment Options (Least to Most Aggressive):**

| Option | When to Use | Impact |
|--------|-------------|--------|
| **Rate limit** | Volume-related issues | Reduces throughput |
| **Disable specific functionality** | Issue isolated to feature subset | Partial degradation |
| **Fallback to simpler model** | Quality issues with primary model | Reduced capability |
| **Circuit breaker** | Cascading failures | Feature unavailable |
| **Full rollback** | Severe issues, safety concerns | Feature unavailable |

**Decision Framework:**
```
Is there a safety risk?
├── Yes → Immediate rollback
└── No → Is quality severely degraded?
    ├── Yes → Can we isolate the issue?
    │   ├── Yes → Targeted containment
    │   └── No → Full rollback
    └── No → Monitor while investigating
```

---

### Phase 4: Resolution

**AI-Specific Resolution Steps:**

**If Model Issue:**
1. Identify problematic model version
2. Rollback to previous version
3. Investigate what changed
4. Fix and validate in staging
5. Gradual re-deployment

**If Data Issue:**
1. Identify data anomaly
2. Fix data pipeline
3. Reprocess affected data
4. Validate fix
5. Resume normal operation

**If Infrastructure Issue:**
1. Standard infrastructure debugging
2. Scale/restart services as needed
3. Verify model serving correct
4. Validate quality restored

**Validation Before Closing:**
- [ ] Metrics back to normal
- [ ] Sample outputs reviewed
- [ ] No new errors
- [ ] User reports subsided

---

### Phase 5: Communication

**Internal Communication:**

During incident:
```
[TIME] - [SEV LEVEL] Incident: [Brief description]
Impact: [Who/what is affected]
Status: [Investigating/Mitigating/Resolved]
Next update: [Time]
```

Resolution:
```
[SEV LEVEL] Incident Resolved

Duration: [Start] to [End]
Impact: [Summary of impact]
Root Cause: [Brief explanation]
Resolution: [What fixed it]
Follow-up: [What happens next]
```

**External Communication (if needed):**

Status page update:
```
[Feature] - Investigating Issues

We're aware of issues affecting [feature]. 
Users may experience [symptoms].
We're actively investigating and will provide updates.
```

Resolution:
```
[Feature] - Resolved

The issue affecting [feature] has been resolved.
[Brief explanation of what happened]
We apologize for any inconvenience.
```

---

### Phase 6: Post-Mortem

**Post-Mortem Template:**

```
# Incident Post-Mortem: [Title]

**Date:** [Date]
**Duration:** [Start - End]
**Severity:** [SEV level]
**Author:** [Name]
**Reviewers:** [Names]

## Summary
[2-3 sentence summary of what happened]

## Impact
- Users affected: [Number/percentage]
- Duration: [How long]
- Business impact: [Revenue, trust, etc.]

## Timeline
- [Time]: [Event]
- [Time]: [Event]
- ...

## Root Cause
[What actually caused the issue]

## Why It Wasn't Caught
[Gaps in testing, monitoring, etc.]

## Resolution
[What fixed it]

## Action Items
| Action | Owner | Due Date | Status |
|--------|-------|----------|--------|
| [Action] | [Name] | [Date] | [Status] |

## Lessons Learned
- [Learning 1]
- [Learning 2]

## Detection Improvements
[How we'll catch this faster next time]

## Prevention Improvements
[How we'll prevent this from happening again]
```

**AI-Specific Post-Mortem Questions:**
- Did our quality monitoring catch this?
- Were there early warning signs?
- Did model evaluation miss this failure mode?
- Do we need additional test cases?
- Is this a systematic issue or one-off?

---

## AI-Specific Incident Types

### Quality Degradation

**Symptoms:** Accuracy drops, users complaining about output quality

**Diagnosis:**
- Compare quality metrics before/during
- Sample and review outputs
- Check for data drift
- Review recent model/prompt changes

**Resolution:**
- Rollback to previous model/prompt version
- Investigate data pipeline
- Retrain if needed

### Hallucination Spike

**Symptoms:** Model making false claims, inventing information

**Diagnosis:**
- Sample outputs for factual errors
- Check RAG retrieval quality (if applicable)
- Review prompt for grounding instructions

**Resolution:**
- Add/strengthen grounding in prompt
- Fix retrieval issues
- Consider different model

### Safety Incident

**Symptoms:** Harmful, inappropriate, or dangerous outputs

**Immediate Actions:**
1. Rollback/disable immediately
2. Preserve evidence
3. Notify security/legal
4. Don't communicate externally until advised

**Post-Incident:**
- Root cause analysis
- Improve guardrails
- Update safety testing

### Cost Spike

**Symptoms:** Unexpected increase in AI API costs

**Diagnosis:**
- Identify traffic source
- Check for loops or inefficient prompts
- Look for abuse/misuse

**Resolution:**
- Rate limit
- Fix inefficiency
- Block abuse

---

## Runbook Template

```
# [Feature Name] Incident Runbook

## Quick Reference
- On-call: [Schedule link]
- Dashboards: [Links]
- Rollback command: [Command]

## Common Issues

### Issue: [Name]
**Symptoms:** [What you'll see]
**Diagnosis:** [How to confirm]
**Resolution:** [Step by step fix]
**Escalation:** [When to escalate]

### Issue: [Name]
...
```

