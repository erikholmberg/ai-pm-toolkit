# Incident Postmortem Template

Use after resolving an incident to document what happened and prevent recurrence.  
See also: [AI Incident Response Playbook](../incidents/ai-incident-response-playbook.md).

---

## Incident Postmortem: [Brief Title]

**Incident ID / Tag:** [e.g. INC-2024-001]  
**Date of incident:** [Start – End, UTC]  
**Author:** [Name]  
**Date of postmortem:** [Date]  
**Status:** [Draft | Reviewed | Closed]

---

## 1. Summary

**One-line summary:** [e.g. "Model rollback caused 2h of elevated error rates for 15% of users."]

**Impact:**
- **Users affected:** [Estimate or range]
- **Duration:** [Time from start to resolution]
- **Severity:** [SEV1 / SEV2 / SEV3 / SEV4]
- **Business impact:** [Revenue, trust, support load, etc.]

---

## 2. Timeline

| Time (UTC) | Event |
|------------|--------|
| [HH:MM] | [e.g. Deployment of model v2] |
| [HH:MM] | [e.g. First alert / user report] |
| [HH:MM] | [e.g. Triage started, IC assigned] |
| [HH:MM] | [e.g. Root cause identified] |
| [HH:MM] | [e.g. Mitigation applied / rollback] |
| [HH:MM] | [e.g. Incident declared resolved] |

---

## 3. Root Cause

**What was the direct cause?**  
[Technical explanation: what broke and why.]

**Contributing factors:**  
[Process, tooling, or decisions that made the incident possible or worse.]

**Why did it slip through?**  
[Gaps in tests, monitoring, review, or rollout process.]

---

## 4. Resolution

**What was done to resolve the incident?**  
[Rollback, fix, config change, etc.]

**Who was involved?**  
[Incident commander, engineers, comms, etc.]

---

## 5. Action Items

| # | Action | Owner | Due | Status |
|---|--------|-------|-----|--------|
| 1 | [e.g. Add alert for error rate by model] | [Name] | [Date] | Open / Done |
| 2 | [e.g. Document rollback runbook] | [Name] | [Date] | Open / Done |
| 3 | [e.g. Add canary step before full rollout] | [Name] | [Date] | Open / Done |

**Blameless note:** Focus on systems and process. The goal is learning and prevention, not blame.

---

## 6. Lessons Learned

**What went well?**  
[Detection, communication, collaboration, runbooks, etc.]

**What could be better?**  
[Monitoring, tooling, escalation, documentation, etc.]

**What will we do differently?**  
[Concrete process or product changes.]

---

## 7. Follow-up

- [ ] Action items assigned and tracked
- [ ] Postmortem reviewed with [team/stakeholders]
- [ ] Runbooks or playbooks updated
- [ ] Monitoring/alerting improved (if applicable)
- [ ] Incident closed in tracking system

---

## Related

- [AI Incident Response Playbook](../incidents/ai-incident-response-playbook.md)
