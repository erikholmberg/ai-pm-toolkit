# AI/ML Fundamentals for Product Managers

What you need to know—without the PhD.

---

## Why This Matters

As an AI PM, you don't need to build models, but you do need to:
1. **Communicate** with ML engineers effectively
2. **Make decisions** about ML approaches
3. **Set expectations** with stakeholders
4. **Identify risks** in ML projects
5. **Evaluate quality** of ML outputs

---

## Core Concepts

### Machine Learning vs. Traditional Software

**Traditional Software:**
- Rules are explicitly programmed
- Same input → same output
- Predictable behavior
- Bugs are logic errors

**Machine Learning:**
- Rules are learned from data
- Same input → can vary
- Probabilistic behavior
- "Bugs" can be data problems

### Types of Machine Learning

| Type | What It Does | Examples |
|------|--------------|----------|
| **Supervised** | Learns from labeled examples | Spam detection, image classification |
| **Unsupervised** | Finds patterns in unlabeled data | Customer segmentation, anomaly detection |
| **Reinforcement** | Learns from rewards/penalties | Game playing, robotics |

### Common ML Tasks

| Task | Input | Output | Examples |
|------|-------|--------|----------|
| **Classification** | Data point | Category | Spam/not spam, sentiment |
| **Regression** | Data point | Number | Price prediction, ETA |
| **Generation** | Prompt/seed | New content | Text, images, code |
| **Ranking** | Items | Ordered list | Search results, recommendations |
| **Clustering** | Data points | Groups | Customer segments |
| **Embedding** | Content | Vector | Semantic search |

---

## LLMs: The Basics

### What is an LLM?

A **Large Language Model** is an AI trained on vast amounts of text that can:
- Generate human-like text
- Follow instructions
- Answer questions
- Summarize content
- Translate languages
- Write code

### How LLMs Work (Simplified)

1. **Training:** Model reads billions of texts, learns patterns
2. **Input:** You provide a prompt (text)
3. **Processing:** Model predicts what text should come next
4. **Output:** Model generates tokens (words/pieces) one at a time

### Key Concepts

**Tokens:** The units LLMs process. "Hello world" = ~2 tokens. Pricing and limits are in tokens.

**Context Window:** How much text the model can "see" at once. GPT-4 Turbo: 128K tokens. Claude: 200K tokens.

**Temperature:** Controls randomness. 0 = deterministic, 1 = creative.

**Prompt:** The input you give the model. Better prompts → better outputs.

### LLM Limitations

- **Hallucination:** Making up facts confidently
- **Knowledge cutoff:** Don't know recent events
- **Context limits:** Can't process unlimited text
- **No real-time data:** Unless connected to tools
- **Expensive:** Cost per token adds up

---

## Model Training Concepts

### Training Data

Models learn from data. Data quality matters enormously.

**Garbage In, Garbage Out:**
- Biased data → biased model
- Errors in data → errors in predictions
- Unrepresentative data → poor generalization

### Overfitting vs. Underfitting

**Overfitting:** Model memorizes training data, fails on new data
**Underfitting:** Model is too simple, performs poorly everywhere
**Goal:** Model generalizes well to new data

### Train/Validation/Test Split

- **Training set:** Model learns from this
- **Validation set:** Tune parameters, catch overfitting
- **Test set:** Final evaluation, held out until the end

---

## Evaluation Metrics

### Classification Metrics

| Metric | What It Measures | When to Use |
|--------|------------------|-------------|
| **Accuracy** | % correct overall | Balanced classes |
| **Precision** | Of positives predicted, % correct | When false positives are costly |
| **Recall** | Of actual positives, % found | When false negatives are costly |
| **F1** | Balance of precision and recall | Want both |

### Confusion Matrix

```
                 Predicted
              Positive  Negative
Actual  Positive   TP        FN
        Negative   FP        TN

TP = True Positive (correctly identified)
FP = False Positive (incorrectly flagged)
FN = False Negative (missed)
TN = True Negative (correctly ignored)
```

### Example: Spam Detection

- **High precision:** Few legitimate emails marked spam
- **High recall:** Catches most spam
- **Trade-off:** Aggressive filter = high recall, lower precision

---

## Production ML Concepts

### Model Serving

**Batch:** Run predictions on a schedule
- Good for: Analytics, bulk processing
- Trade-off: Not real-time

**Real-time:** Predictions on demand
- Good for: User-facing features
- Trade-off: Latency, scaling challenges

### Model Drift

**Data Drift:** Input data changes over time
**Concept Drift:** Relationship between input and output changes

**Example:** Fraud model trained on pre-COVID data may miss new pandemic-era fraud patterns.

**Solution:** Monitor distributions, retrain periodically

### Feature Stores

Centralized storage for ML features:
- Ensures consistency between training and serving
- Enables feature reuse across models
- Reduces duplicated work

---

## Practical Knowledge

### Questions to Ask ML Engineers

**About Data:**
- Where does the training data come from?
- How representative is it?
- What's the labeling process?
- Any known biases?

**About the Model:**
- What type of model is this?
- What's the baseline we're comparing to?
- How often will it need retraining?
- What are the known limitations?

**About Performance:**
- What metrics are we optimizing for?
- What's the accuracy on different segments?
- What's the latency expectation?
- What's the cost per prediction?

**About Production:**
- How will we know if the model degrades?
- What's the rollback plan?
- How do we handle edge cases?
- What's the retraining strategy?

### Red Flags in ML Projects

🚩 "We just need more data"
🚩 "The model is 99% accurate" (on what?)
🚩 "We'll figure out evaluation later"
🚩 "It works on my laptop"
🚩 "Users will provide feedback to improve it"
🚩 "We don't need a baseline"

---

## Resources for Going Deeper

### Books
- *Designing Machine Learning Systems* by Chip Huyen
- *Building Machine Learning Powered Applications* by Emmanuel Ameisen

### Courses
- Google's Machine Learning Crash Course (free)
- Fast.ai Practical Deep Learning (free)

### Stay Current
- The Batch (Andrew Ng's newsletter)
- Import AI Newsletter
- AI/ML focused podcasts

