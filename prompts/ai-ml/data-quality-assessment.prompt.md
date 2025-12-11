# Data Quality Assessment

Evaluate data quality for ML projects—a critical PM responsibility.

## Usage

Use these prompts when reviewing data for ML features, evaluating new data sources, or diagnosing model issues.

---

## Data Quality Review Prompt

```
You are a data quality expert helping a PM evaluate a dataset for an ML project.

## Project Context
- ML Use Case: [WHAT WE'RE BUILDING]
- Required Data: [WHAT DATA WE NEED]
- Data Source: [WHERE DATA COMES FROM]

## Dataset Information
---
[PROVIDE ANY AVAILABLE INFORMATION:
- Schema/fields available
- Sample data (anonymized)
- Data dictionary
- Collection methodology
- Historical availability
- Known issues]
---

## Data Quality Assessment

Evaluate across these dimensions:

### 1. Completeness
- **Missing Fields:** Which fields have null/missing values? What %?
- **Coverage:** Does the data represent all user segments?
- **Time Coverage:** Is historical data sufficient for training?
- **Geographic Coverage:** Any regional gaps?

| Field | Missing % | Impact on ML | Mitigation |
|-------|-----------|--------------|------------|

### 2. Accuracy
- **Ground Truth:** How do we know this data is correct?
- **Label Quality:** If labeled data, how reliable are labels?
- **Measurement Error:** What's the margin of error?
- **Staleness:** How fresh is the data? How quickly does it expire?

### 3. Consistency
- **Schema Stability:** Does the schema change over time?
- **Semantic Consistency:** Same field mean same thing everywhere?
- **Unit Consistency:** Consistent units (currencies, timezones)?
- **Encoding Consistency:** Same encoding across sources?

### 4. Representativeness
- **Population Match:** Does training data match production population?
- **Temporal Match:** Is historical data representative of future?
- **Selection Bias:** How was this data collected? What's excluded?
- **Distribution Shift:** Known changes in underlying distribution?

### 5. Bias Audit
- **Demographic Representation:** Underrepresented groups?
- **Historical Bias:** Does data encode past discrimination?
- **Labeler Bias:** Who labeled the data? Any biases?
- **Survivorship Bias:** Only successful cases included?

### 6. Volume & Velocity
- **Current Volume:** How much data do we have?
- **Sufficient for ML:** Is it enough to train reliably?
- **Growth Rate:** How fast is new data coming in?
- **Batch vs. Streaming:** How is data delivered?

### 7. Privacy & Compliance
- **PII Present:** Any personally identifiable information?
- **Consent:** Was data collected with appropriate consent?
- **Retention:** How long can we keep it?
- **Geography:** GDPR/CCPA/other requirements?

### 8. Accessibility
- **Access Method:** How do we query this data?
- **Latency:** How quickly can we access it?
- **Cost:** What does data access cost?
- **Dependencies:** What systems must be up to access it?

### 9. Summary & Recommendations
- **Overall Quality Score:** [High/Medium/Low]
- **Critical Issues:** Must fix before proceeding
- **Improvement Opportunities:** Nice to have
- **Recommendation:** [Use as-is / Use with caveats / Improve first / Find alternative]
```

---

## Quick Data Smell Test

```
I'm evaluating a data source for an ML project. Help me do a quick smell test.

## Context
- Data Source: [WHERE IT COMES FROM]
- Intended Use: [WHAT WE'LL USE IT FOR]

## What I Know
[PASTE ANY AVAILABLE INFO ABOUT THE DATA]

## Red Flag Checklist

Run through these questions:

1. **Do we know where this data comes from?** 
   - [ ] Clear provenance
   - [ ] Collection methodology documented

2. **Is the data representative?**
   - [ ] Matches production population
   - [ ] No obvious selection bias

3. **How accurate is it?**
   - [ ] Verified ground truth
   - [ ] Known error rates

4. **Is it fresh enough?**
   - [ ] Data isn't stale
   - [ ] Update frequency is sufficient

5. **Privacy checked?**
   - [ ] No unexpected PII
   - [ ] Proper consent

6. **Enough volume?**
   - [ ] Sufficient for training
   - [ ] Covers edge cases

Highlight any red flags and suggest next steps.
```

---

## Data Labeling Quality Prompt

```
Help me evaluate the quality of our labeled training data.

## Labeling Context
- Task: [WHAT IS BEING LABELED]
- Label Types: [CATEGORIES OR CONTINUOUS VALUES]
- Labelers: [WHO DID THE LABELING]
- Volume: [HOW MANY LABELED EXAMPLES]

## Available Information
[PASTE ANY INFO: inter-rater agreement, labeling guidelines, sample labels]

## Evaluate:

### 1. Labeling Process
- Were labelers trained?
- Were guidelines clear and consistent?
- What quality control was in place?

### 2. Agreement Metrics
- Inter-rater reliability score?
- Dispute resolution process?
- Edge case handling?

### 3. Label Distribution
- Is the distribution balanced?
- Are rare classes represented?
- Any suspicious patterns?

### 4. Common Errors
- What types of mistakes are common?
- Which categories have lowest agreement?
- Are errors random or systematic?

### 5. Recommendations
- Label quality: [High/Medium/Low]
- Confidence in training with this data
- Improvements to make
```

---

## Tips for PMs

- **"Where does this data come from?" is always valid** - Ask until you understand
- **Sample the data yourself** - Look at actual examples, not just summaries
- **Understand the labels** - Bad labels = bad model, full stop
- **Ask about edge cases** - The long tail is where models fail
- **Data changes over time** - What was true in training may not be true now
- **Data is never perfect** - The question is whether it's good enough

