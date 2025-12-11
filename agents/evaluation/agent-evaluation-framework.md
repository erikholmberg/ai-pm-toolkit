# Agent Evaluation Framework

How to evaluate AI agent products and features.

---

## Why Agent Evaluation is Different

Agents are harder to evaluate than traditional software because:
1. **Non-deterministic** - Same input can produce different outputs
2. **Multi-step** - Failures can compound across steps
3. **Tool use** - Need to evaluate tool selection and execution
4. **Subjective quality** - "Good" often requires human judgment
5. **Edge cases** - Failure modes can be unexpected

---

## Evaluation Dimensions

### 1. Task Completion

**Definition:** Does the agent successfully complete the assigned task?

**Metrics:**
- Success rate (% of tasks completed)
- Partial completion rate
- Failure rate by error type

**How to Measure:**
- Create golden test cases with known correct outcomes
- Use human evaluators for subjective tasks
- Track real-world task completion

**Example Criteria:**
```
| Task Type | Success Criteria |
|-----------|------------------|
| Research | Found relevant info, answered question |
| Coding | Code runs, passes tests |
| Writing | Coherent, on-topic, correct length |
| Analysis | Insights are accurate, actionable |
```

### 2. Quality of Output

**Definition:** How good is the output, not just whether it's complete?

**Metrics:**
- Human quality ratings (1-5 scale)
- Accuracy of factual claims
- Relevance to the request
- Coherence and clarity

**Rubric Example:**
```
5 - Exceptional: Exceeds expectations, no improvements needed
4 - Good: Meets expectations, minor improvements possible
3 - Acceptable: Completes task but needs improvement
2 - Poor: Partially completes task, significant issues
1 - Unacceptable: Fails task or causes harm
```

### 3. Efficiency

**Definition:** How efficiently does the agent complete tasks?

**Metrics:**
- Steps to completion
- Time to completion
- Token/API usage
- Cost per task
- Unnecessary actions taken

**Efficiency Goals:**
- Minimize tool calls for same outcome
- Avoid redundant steps
- Complete within latency requirements
- Stay within cost budget

### 4. Tool Use Quality

**Definition:** Does the agent use tools correctly and appropriately?

**Metrics:**
- Correct tool selection rate
- Tool parameter accuracy
- Tool error rate
- Unnecessary tool calls

**Evaluation Questions:**
- Did it pick the right tool for the task?
- Were tool parameters correct?
- Did it handle tool errors gracefully?
- Did it avoid unnecessary tool calls?

### 5. Robustness

**Definition:** Does the agent handle edge cases and adversarial inputs?

**Test Categories:**
- Ambiguous requests
- Incomplete information
- Contradictory instructions
- Adversarial prompts
- Out-of-scope requests

**Metrics:**
- Graceful degradation rate (fails safely)
- Appropriate refusal rate (refuses when should)
- False refusal rate (refuses when shouldn't)

### 6. Safety & Alignment

**Definition:** Does the agent behave safely and as intended?

**Safety Checks:**
- Stays within defined scope
- Doesn't take unauthorized actions
- Asks for confirmation on high-impact actions
- Handles PII appropriately
- Doesn't generate harmful content

**Alignment Checks:**
- Follows instructions accurately
- Maintains persona consistency
- Respects stated constraints
- Aligns with user intent, not just literal request

---

## Evaluation Process

### Step 1: Define Test Cases

Create a diverse set of test cases covering:
- Happy path scenarios
- Edge cases
- Failure modes
- Adversarial inputs

**Test Case Template:**
```yaml
id: TC001
name: Research competitor pricing
category: Research
priority: High
input: "Research Datadog's current pricing model"
expected_behavior:
  - Searches for Datadog pricing information
  - Returns current pricing tiers
  - Includes sources
success_criteria:
  - Factually accurate pricing
  - At least 2 sources cited
  - Response within 30 seconds
```

### Step 2: Run Evaluations

For automated testing:
```python
def evaluate_agent(test_case):
    result = agent.run(test_case['input'])
    
    scores = {
        'completed': check_completion(result, test_case['expected_behavior']),
        'quality': rate_quality(result),
        'accuracy': check_accuracy(result, test_case['ground_truth']),
        'efficiency': measure_efficiency(result),
        'safety': check_safety(result),
    }
    
    return scores
```

For human evaluation:
1. Present output to evaluators
2. Collect ratings on standardized rubrics
3. Use multiple evaluators per case
4. Track inter-rater reliability

### Step 3: Analyze Results

**By Category:**
- Success rate by task type
- Quality distribution
- Failure mode breakdown
- Cost and efficiency trends

**Over Time:**
- Week-over-week trends
- Regression detection
- Improvement tracking

### Step 4: Iterate

Based on findings:
- Update system prompts
- Improve tool descriptions
- Add guardrails for failure modes
- Expand test coverage

---

## Evaluation Cadence

| Type | Frequency | Purpose |
|------|-----------|---------|
| Smoke Tests | Every deploy | Catch regressions |
| Full Eval | Weekly | Comprehensive quality |
| Human Eval | Monthly | Subjective quality |
| Adversarial | Quarterly | Safety and robustness |

---

## Tools for Agent Evaluation

**Frameworks:**
- LangSmith (LangChain)
- Weights & Biases
- Braintrust
- Custom logging + analysis

**Key Features to Use:**
- Trace logging
- Evaluation datasets
- Comparison across versions
- Human feedback collection

---

## Reporting Template

### Agent Evaluation Report

**Period:** [Date range]

**Summary:**
- Tasks evaluated: X
- Overall success rate: X%
- Quality score (avg): X/5
- Safety incidents: X

**By Task Type:**
| Type | Success Rate | Avg Quality | Notes |
|------|--------------|-------------|-------|

**Top Failure Modes:**
1. [Mode]: X occurrences - [Root cause]
2. [Mode]: X occurrences - [Root cause]

**Improvements from Last Period:**
- [Improvement 1]
- [Improvement 2]

**Recommendations:**
1. [Action item]
2. [Action item]

