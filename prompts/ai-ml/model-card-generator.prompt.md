# Model Card Generator

Create comprehensive model cards for ML model documentation and transparency.

## Usage

Model cards are essential documentation for ML models. Use this to generate cards that support transparency, ethical review, and cross-functional understanding.

---

## Full Model Card Prompt

```
You are an ML documentation expert. Help me create a comprehensive model card.

## Model Information
- Model Name: [NAME]
- Version: [VERSION]
- Type: [e.g., Classification, Regression, LLM, Embedding, Ranking]
- Owner: [TEAM/INDIVIDUAL]
- Last Updated: [DATE]

## Training & Data Information
---
[PASTE ANY AVAILABLE INFORMATION ABOUT:
- Training data sources
- Data preprocessing
- Training methodology
- Evaluation metrics
- Known limitations]
---

## Generate a Model Card

### 1. Model Overview
- **Purpose:** What problem does this model solve?
- **Intended Use:** How should this model be used?
- **Out-of-Scope Uses:** How should this model NOT be used?
- **Model Type:** Technical description of the model architecture

### 2. Training Data
- **Dataset(s):** What data was used to train the model?
- **Data Size:** How much data (samples, tokens, etc.)?
- **Date Range:** What time period does the data cover?
- **Data Collection:** How was data collected?
- **Preprocessing:** What preprocessing was applied?
- **Known Gaps:** What data is missing or underrepresented?

### 3. Evaluation Data
- **Held-out Set:** Description of evaluation data
- **Benchmarks:** Standard benchmarks used
- **Representativeness:** How well does eval data reflect production?

### 4. Performance Metrics
| Metric | Overall | Subgroup A | Subgroup B | Notes |
|--------|---------|------------|------------|-------|
| [Accuracy/F1/etc.] | | | | |

- **Performance by Segment:** Break down by relevant user segments
- **Confidence Thresholds:** Recommended thresholds for different use cases

### 5. Ethical Considerations
- **Potential Harms:** What harms could misuse or errors cause?
- **Bias Analysis:** What biases were tested for?
- **Mitigation Steps:** What was done to reduce risks?
- **Sensitive Use Cases:** Special considerations for sensitive applications

### 6. Limitations
- **Known Limitations:** What doesn't this model do well?
- **Edge Cases:** Scenarios where performance degrades
- **Data Freshness:** How performance changes with time/data drift

### 7. Deployment & Operations
- **Inference Infrastructure:** Where does the model run?
- **Latency:** Expected inference time
- **Throughput:** Requests per second capacity
- **Monitoring:** What metrics are tracked in production?
- **Retraining Schedule:** How often is the model retrained?

### 8. Maintenance
- **Feedback Channels:** How to report issues?
- **Update History:** Previous versions and what changed
- **Deprecation Plan:** When will this version be retired?

### 9. Contact
- **Model Owner:** [Name/Team]
- **Questions/Issues:** [How to reach them]
- **Documentation:** [Links to additional docs]
```

---

## Lightweight Model Card (Internal)

```
Create a quick model card for internal documentation.

## Model
- Name: [MODEL NAME]
- Purpose: [ONE SENTENCE]
- Owner: [TEAM]

## Quick Details
- Model type: [TYPE]
- Training data: [SOURCE]
- Key metric: [METRIC] = [VALUE]
- Last trained: [DATE]

---

Generate a 1-page model card with:

### What it Does
[2-3 sentences]

### When to Use It
[Bullet list of appropriate use cases]

### When NOT to Use It
[Bullet list of inappropriate uses]

### Performance Summary
[Key metrics in a simple table]

### Known Issues
[Bullet list of limitations]

### How to Get Help
[Contact info]
```

---

## Model Comparison Card

```
Create a comparison card for multiple model versions or alternatives.

## Models to Compare
1. [MODEL A]: [Brief description]
2. [MODEL B]: [Brief description]
3. [MODEL C]: [Brief description]

## Available Metrics
[PASTE PERFORMANCE DATA]

---

Generate a comparison card with:

### Head-to-Head Comparison
| Dimension | Model A | Model B | Model C |
|-----------|---------|---------|---------|
| Accuracy | | | |
| Latency (p50) | | | |
| Latency (p99) | | | |
| Model Size | | | |
| Training Cost | | | |
| Inference Cost | | | |

### Strengths & Weaknesses
For each model, list:
- Where it excels
- Where it struggles

### Recommended Use Cases
When to use each model.

### Migration Considerations
If switching from one model to another, what to consider.
```

---

## Tips

- **Update model cards when models change** - Stale docs are dangerous
- **Include failure modes** - Be honest about what breaks
- **Add examples** - Show input/output examples when possible
- **Link to monitoring dashboards** - Make it easy to check health
- **Version the card** - Model cards should be versioned with models
- **Review with ethics team** - Fresh eyes catch blind spots

