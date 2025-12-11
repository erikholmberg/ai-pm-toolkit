# AI Ethics Evaluator

Red-team AI features for ethical risks and potential harms.

## Usage

Use these prompts before launching AI features to identify ethical risks, potential misuse, and unintended consequences.

---

## Comprehensive Ethics Review

```
You are an AI ethics expert helping me evaluate a new AI feature for potential risks and harms.

## Feature Context
- Feature: [WHAT THE AI FEATURE DOES]
- User Audience: [WHO WILL USE IT]
- Model Type: [WHAT KIND OF AI/ML IS INVOLVED]
- Data Used: [WHAT DATA DOES IT USE OR GENERATE]

## Feature Details
---
[DESCRIBE THE FEATURE IN DETAIL:
- What inputs does it take?
- What outputs does it produce?
- How are outputs used?
- Who can access it?]
---

## Ethics Evaluation Framework

### 1. Harm Assessment

#### Direct Harms
| Harm Type | Description | Likelihood | Severity | Affected Group |
|-----------|-------------|------------|----------|----------------|
| Physical | | | | |
| Psychological | | | | |
| Financial | | | | |
| Reputational | | | | |
| Privacy | | | | |
| Dignity | | | | |

#### Indirect Harms
- Downstream effects on third parties
- Societal-level impacts
- Environmental impacts (compute/energy)

### 2. Bias & Fairness

#### Representation
- Who is well-represented in training data?
- Who is underrepresented or missing?
- How might this affect model performance across groups?

#### Outcome Equity
- Could this feature produce systematically different outcomes for different groups?
- Are there protected characteristics that could influence predictions?
- What disparate impacts are possible?

#### Historical Bias
- Does the training data encode historical discrimination?
- Could this feature perpetuate or amplify existing inequities?

### 3. Autonomy & Agency

- Does this feature manipulate or deceive users?
- Are users aware AI is being used?
- Can users opt out?
- Can users override AI decisions?
- Does this reduce user agency or capability?

### 4. Privacy & Surveillance

- What data is collected?
- How long is it retained?
- Who can access it?
- Could this enable surveillance?
- Inference risks (deriving sensitive info from non-sensitive data)?

### 5. Misuse Potential

| Misuse Scenario | Attacker | Method | Impact | Mitigation |
|-----------------|----------|--------|--------|------------|
| [Scenario 1] | | | | |
| [Scenario 2] | | | | |

- How could bad actors exploit this?
- What guardrails prevent misuse?
- What if those guardrails fail?

### 6. Transparency & Explainability

- Can users understand why they got a particular output?
- Is AI involvement disclosed?
- Are limitations communicated?
- Can decisions be audited?

### 7. Accountability

- Who is responsible when things go wrong?
- Is there a clear escalation path?
- How are errors corrected?
- What recourse do affected users have?

### 8. Long-term Considerations

- What second-order effects could emerge?
- How might this change user behavior over time?
- What happens if this becomes widely adopted?
- What precedent does this set?

### 9. Risk Summary

| Category | Risk Level | Key Concerns | Mitigations Needed |
|----------|------------|--------------|-------------------|
| Bias | 🔴🟡🟢 | | |
| Privacy | 🔴🟡🟢 | | |
| Misuse | 🔴🟡🟢 | | |
| Autonomy | 🔴🟡🟢 | | |
| Transparency | 🔴🟡🟢 | | |

### 10. Recommendations

- **Must Do Before Launch:** [CRITICAL ITEMS]
- **Should Do:** [IMPORTANT IMPROVEMENTS]
- **Consider:** [NICE TO HAVE]
- **Monitor Post-Launch:** [WHAT TO WATCH]

### 11. Go/No-Go Recommendation

- [ ] Proceed with current design
- [ ] Proceed with modifications
- [ ] Significant redesign needed
- [ ] Do not proceed
```

---

## Quick Red Team Prompt

```
Red-team this AI feature for me. I want to find the ways it could go wrong or be misused.

## Feature
[DESCRIBE THE AI FEATURE IN 2-3 SENTENCES]

## Be adversarial. Think about:

1. **Hostile Users**
   - How could someone intentionally misuse this?
   - What's the worst prompt injection / jailbreak?
   - How could this be weaponized?

2. **Edge Cases**
   - What inputs would break this?
   - What user groups would get poor results?
   - What happens at scale?

3. **Unintended Consequences**
   - What behaviors might this incentivize?
   - What could go wrong that we haven't thought of?
   - What if this is wildly successful?

4. **Reputation Risk**
   - What could end up in a negative news article?
   - What would make users lose trust?
   - What would embarrass us?

5. **Legal/Compliance Risk**
   - What regulations might this run afoul of?
   - What claims are we implying?
   - What liability are we taking on?

Give me your top 5-7 concerns and how we might address them.
```

---

## Bias Testing Prompt

```
Help me design bias tests for an AI feature.

## Feature
- What it does: [DESCRIPTION]
- Model type: [TYPE]
- Key outputs: [WHAT IT PRODUCES]

## Protected Characteristics to Test
- [ ] Race/ethnicity
- [ ] Gender
- [ ] Age
- [ ] Disability status
- [ ] Geographic location
- [ ] Socioeconomic status
- [ ] Language/accent
- [ ] Other: [SPECIFY]

## Generate:

### Test Cases
For each protected characteristic:
- Test input variations
- Expected equitable behavior
- Red flags to watch for

### Metrics
- How to measure disparate performance
- Thresholds for acceptable differences
- Statistical tests to use

### Mitigation Strategies
If bias is detected, what can we do?
```

---

## Tips

- **Do ethics review early** - Cheaper to fix in design than after launch
- **Involve diverse perspectives** - Your blind spots are invisible to you
- **Document your reasoning** - Future you will want to know why you decided this
- **Plan for failure** - What's the response when something goes wrong?
- **Ethics is ongoing** - Not a one-time checkbox; monitor and revisit

