# Responsible AI Checklist

Pre-launch checklist for responsible AI deployment.

---

## How to Use This Checklist

Complete before launching any AI feature. Document your answers and get sign-off from appropriate stakeholders.

---

## 1. Purpose & Value

### 1.1 Clear Purpose
- [ ] The purpose of this AI feature is clearly defined
- [ ] The problem it solves is real and validated
- [ ] AI is the appropriate solution (not over-engineering)
- [ ] The value to users is articulated

**Documentation:**
- Purpose statement: ___
- User problem: ___
- Why AI vs. alternatives: ___

### 1.2 Stakeholder Impact
- [ ] All affected stakeholders are identified
- [ ] Positive impacts are documented
- [ ] Potential negative impacts are considered
- [ ] Affected groups have been consulted (if appropriate)

---

## 2. Data & Privacy

### 2.1 Data Sources
- [ ] Training data sources are documented
- [ ] Data collection methods are ethical
- [ ] Consent was obtained appropriately
- [ ] Data represents intended user population

**Documentation:**
- Data sources: ___
- Collection method: ___
- Consent mechanism: ___

### 2.2 Privacy
- [ ] PII handling is documented and appropriate
- [ ] Data minimization principle applied
- [ ] Data retention policies defined
- [ ] GDPR/CCPA compliance verified (if applicable)
- [ ] User data rights are respected (access, deletion)

### 2.3 Data Security
- [ ] Data is encrypted at rest and in transit
- [ ] Access controls are in place
- [ ] Audit logging is enabled
- [ ] Third-party data handling is reviewed

---

## 3. Fairness & Bias

### 3.1 Bias Assessment
- [ ] Potential sources of bias identified
- [ ] Training data reviewed for representation
- [ ] Model tested across demographic groups
- [ ] Performance disparities documented

**Protected characteristics considered:**
- [ ] Race/ethnicity
- [ ] Gender
- [ ] Age
- [ ] Disability
- [ ] Geographic location
- [ ] Socioeconomic status
- [ ] Other: ___

### 3.2 Bias Mitigation
- [ ] Mitigation strategies implemented
- [ ] Trade-offs documented and accepted
- [ ] Ongoing monitoring planned
- [ ] Escalation path for bias issues defined

**Mitigation strategies used:**
- ___

### 3.3 Fairness Metrics
- [ ] Fairness metrics defined
- [ ] Thresholds set for acceptable disparities
- [ ] Metrics will be monitored in production

---

## 4. Transparency & Explainability

### 4.1 User Transparency
- [ ] Users know AI is being used
- [ ] AI capabilities are not overstated
- [ ] Limitations are communicated
- [ ] AI decisions are distinguishable from human decisions

### 4.2 Explainability
- [ ] Outputs can be explained (at appropriate level)
- [ ] Users can understand why they received a result
- [ ] Appeals/correction mechanisms exist
- [ ] Explanations are accessible to target audience

### 4.3 Documentation
- [ ] Model card created
- [ ] Technical documentation complete
- [ ] User-facing documentation ready

---

## 5. Safety & Security

### 5.1 Harm Assessment
- [ ] Potential harms identified (physical, psychological, financial, reputational)
- [ ] Severity and likelihood assessed
- [ ] Mitigations implemented
- [ ] Acceptable risk level determined

**Harm assessment:**
| Harm Type | Risk Level | Mitigation |
|-----------|------------|------------|
| | | |

### 5.2 Misuse Prevention
- [ ] Potential misuse scenarios identified
- [ ] Guardrails implemented
- [ ] Abuse detection mechanisms in place
- [ ] Rate limiting and access controls configured

### 5.3 Failure Modes
- [ ] Failure modes documented
- [ ] Graceful degradation implemented
- [ ] Fallback mechanisms in place
- [ ] Rollback plan tested

### 5.4 Security
- [ ] Input validation implemented
- [ ] Prompt injection defenses in place (if applicable)
- [ ] Output filtering implemented (if applicable)
- [ ] Security review completed

---

## 6. Human Oversight

### 6.1 Human-in-the-Loop
- [ ] Appropriate level of human oversight determined
- [ ] High-stakes decisions have human review
- [ ] Users can override AI decisions
- [ ] Escalation paths defined

### 6.2 Accountability
- [ ] Ownership is clear (who's responsible)
- [ ] Escalation paths documented
- [ ] Incident response plan exists
- [ ] Post-mortem process defined

---

## 7. Ongoing Governance

### 7.1 Monitoring
- [ ] Performance monitoring in place
- [ ] Bias monitoring configured
- [ ] Drift detection implemented
- [ ] Alert thresholds set

### 7.2 Feedback & Improvement
- [ ] User feedback collection mechanism ready
- [ ] Issue reporting path defined
- [ ] Improvement process documented
- [ ] Retraining strategy defined

### 7.3 Review Cadence
- [ ] Regular review schedule set
- [ ] Review criteria defined
- [ ] Sunset/deprecation criteria defined

---

## Sign-off

| Role | Name | Date | Signature |
|------|------|------|-----------|
| Product Owner | | | |
| Engineering Lead | | | |
| Legal/Compliance | | | |
| Privacy | | | |
| Security | | | |

---

## Summary

**Feature:** ___

**Risk Level:** [ ] Low [ ] Medium [ ] High

**Approval Decision:** [ ] Approved [ ] Approved with conditions [ ] Not approved

**Conditions (if any):**
- ___

**Next Review Date:** ___

