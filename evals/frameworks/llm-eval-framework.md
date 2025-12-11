# LLM Evaluation Framework

A practical framework for evaluating Large Language Model outputs.

---

## Evaluation Dimensions

### 1. Correctness / Accuracy

**Definition:** Is the output factually correct?

**How to Measure:**
- Compare against ground truth (when available)
- Fact-checking for verifiable claims
- Expert review for domain-specific content

**Metrics:**
- Accuracy (% correct)
- Error rate by type (factual, logical, etc.)
- Hallucination rate

**Challenges:**
- Ground truth may not exist
- Correctness can be subjective
- Partial correctness is hard to score

---

### 2. Relevance

**Definition:** Does the output address the prompt/question?

**How to Measure:**
- Semantic similarity to expected output
- Human rating (1-5 scale)
- Coverage of required elements

**Metrics:**
- Relevance score (human-rated)
- Topic coverage %
- On-topic rate

---

### 3. Coherence

**Definition:** Is the output well-organized and logical?

**How to Measure:**
- Human evaluation
- Reading ease scores
- Structure analysis

**Rubric:**
| Score | Description |
|-------|-------------|
| 5 | Perfectly structured, easy to follow |
| 4 | Well-organized, minor issues |
| 3 | Acceptable structure |
| 2 | Disorganized, hard to follow |
| 1 | Incoherent |

---

### 4. Fluency

**Definition:** Is the output grammatically correct and natural?

**How to Measure:**
- Grammar checking
- Perplexity scores
- Human naturalness ratings

**Common Issues:**
- Grammatical errors
- Awkward phrasing
- Unnatural repetition
- Inconsistent tone

---

### 5. Completeness

**Definition:** Does the output cover all required aspects?

**How to Measure:**
- Checklist of required elements
- Coverage scoring
- Gap analysis

**Metrics:**
- Completeness % (elements present / required)
- Missing element rate

---

### 6. Conciseness

**Definition:** Is the output appropriately sized without unnecessary content?

**How to Measure:**
- Length vs. requirement
- Information density
- Redundancy detection

**Balance:**
- Too short → incomplete
- Too long → verbose/redundant
- Right size → informative and efficient

---

### 7. Safety

**Definition:** Is the output free from harmful content?

**Categories:**
- Harmful/dangerous content
- Bias and discrimination
- Privacy violations
- Misinformation
- Inappropriate content

**How to Measure:**
- Automated classifiers
- Human review
- Red-teaming

---

## Evaluation Methods

### Method 1: Human Evaluation

**Best for:** Subjective quality, nuanced assessment

**Process:**
1. Define rating criteria and rubrics
2. Train evaluators
3. Collect ratings (use multiple evaluators)
4. Calculate inter-rater reliability
5. Aggregate scores

**Tips:**
- Use at least 3 evaluators per sample
- Randomize order to avoid bias
- Include reference outputs for calibration

### Method 2: Automated Metrics

**Best for:** Scalable, consistent measurement

**Common Metrics:**
| Metric | What it Measures | When to Use |
|--------|------------------|-------------|
| BLEU | N-gram overlap | Translation, generation |
| ROUGE | Recall of reference text | Summarization |
| BERTScore | Semantic similarity | Any text comparison |
| Perplexity | Model confidence | Fluency |

**Limitations:**
- May not capture quality well
- Can be gamed
- Require reference text

### Method 3: LLM-as-Judge

**Best for:** Scalable quality assessment

**How it works:**
Use a capable LLM to rate outputs from another model.

**Example Prompt:**
```
Rate the following response on a scale of 1-5 for accuracy, 
relevance, and completeness. Explain your reasoning.

Question: [QUESTION]
Response: [RESPONSE]

Ratings:
- Accuracy (1-5): 
- Relevance (1-5):
- Completeness (1-5):
Explanation:
```

**Tips:**
- Use stronger model as judge
- Provide clear rubrics
- Validate against human ratings
- Be aware of position bias

### Method 4: A/B Testing

**Best for:** Real-world impact measurement

**Process:**
1. Define success metric
2. Split traffic randomly
3. Collect data over time
4. Statistical analysis
5. Make decision

**Metrics to Track:**
- User preference (thumbs up/down)
- Task completion rate
- Engagement (follow-ups, edits)
- Time to completion

---

## Eval Process Template

### 1. Define Objectives
- What are we trying to measure?
- What decisions will this inform?

### 2. Select Dimensions
- Which quality dimensions matter most?
- What's the priority order?

### 3. Choose Methods
- Human eval, automated, or both?
- What sample size is needed?

### 4. Create Test Set
- Representative inputs
- Include edge cases
- Document expected outputs (if available)

### 5. Run Evaluation
- Execute with controls for consistency
- Collect raw data

### 6. Analyze Results
- Aggregate scores
- Identify patterns
- Compare across segments

### 7. Report & Act
- Summarize findings
- Make recommendations
- Implement improvements

---

## Sample Eval Rubric

For a customer support response:

| Dimension | Weight | 1 (Poor) | 3 (Acceptable) | 5 (Excellent) |
|-----------|--------|----------|----------------|---------------|
| Accuracy | 30% | Incorrect info | Minor errors | Fully accurate |
| Helpfulness | 25% | Doesn't address issue | Partially addresses | Fully solves |
| Tone | 20% | Inappropriate | Neutral | Empathetic, on-brand |
| Completeness | 15% | Missing key info | Mostly complete | Comprehensive |
| Conciseness | 10% | Very verbose | Acceptable length | Perfectly sized |

