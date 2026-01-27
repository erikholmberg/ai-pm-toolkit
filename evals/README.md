# Evals: AI Product Evaluation Toolkit

Frameworks, scripts, and templates for evaluating AI/ML products.

## What's Here

| Directory | Description |
|-----------|-------------|
| [frameworks/](./frameworks/) | Evaluation methodologies |
| [scripts/](./scripts/) | Python tools for running evals |
| [templates/](./templates/) | Documents for planning and reporting |
| [metrics/](./metrics/) | What to measure and why |

## Why Evals Matter

As an AI PM, you need to:
1. **Measure quality** - Know if your AI is working
2. **Compare options** - Choose between approaches
3. **Detect regressions** - Catch problems early
4. **Build trust** - Show stakeholders the data
5. **Iterate effectively** - Improve based on evidence

## Quick Start

### 1. Plan Your Eval

Use [templates/eval-plan-template.md](./templates/eval-plan-template.md) to scope your evaluation.

### 2. Choose Metrics

Reference [metrics/ai-product-metrics.md](./metrics/ai-product-metrics.md) for what to measure.

### 3. Build Test Cases

Use [templates/golden-dataset-template.md](./templates/golden-dataset-template.md) to structure test data.

### 4. Run Evals

Use scripts in [scripts/](./scripts/) or your preferred eval framework.

**Available Scripts:**
- **[llm-as-judge-evaluator.py](./scripts/llm-as-judge-evaluator.py)** - Use a stronger LLM to evaluate outputs on multiple dimensions
- **[prompt-eval-harness.py](./scripts/prompt-eval-harness.py)** - Evaluate and compare prompt versions

See [scripts/README.md](./scripts/README.md) for usage instructions.

### 5. Report Results

Use [templates/eval-results-template.md](./templates/eval-results-template.md) for stakeholder communication.

## Common Eval Types

| Eval Type | When to Use |
|-----------|-------------|
| **Prompt Eval** | Comparing prompt variants |
| **Model Comparison** | Evaluating different models |
| **A/B Test** | Measuring real-world impact |
| **Regression Test** | Catching quality drops |
| **Human Eval** | Subjective quality assessment |
| **LLM-as-Judge** | Scalable quality assessment using stronger models |
| **Safety Eval** | Testing for harmful outputs |

## Tools We Recommend

- **Braintrust** - Eval platform with good UX
- **LangSmith** - If using LangChain
- **Weights & Biases** - ML experiment tracking
- **Custom logging** - For bespoke needs

