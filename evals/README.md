# Evals: AI Product Evaluation Toolkit

Frameworks, scripts, and templates for evaluating AI/ML products.

## What's Here

| Directory | Description |
|-----------|-------------|
| [frameworks/](./frameworks/) | Evaluation methodologies |
| [scripts/](./scripts/) | Python tools for running evals |
| [templates/](./templates/) | Eval plan, golden dataset, and reporting |
| [metrics/](./metrics/) | What to measure and why |

**Templates:** [eval-plan-template.md](./templates/eval-plan-template.md), [golden-dataset-template.md](./templates/golden-dataset-template.md)

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

Use [templates/golden-dataset-template.md](./templates/golden-dataset-template.md) to structure test data. Example: [golden-dataset-example.json](./templates/golden-dataset-example.json).

### 4. Run Evals

Use scripts in [scripts/](./scripts/) or your preferred eval framework.

**Available Scripts:**
- **[llm-as-judge-evaluator.py](./scripts/llm-as-judge-evaluator.py)** - Use a stronger LLM to evaluate outputs on multiple dimensions
- **[prompt-eval-harness.py](./scripts/prompt-eval-harness.py)** - Evaluate and compare prompt versions
- **[automated-metrics.py](./scripts/automated-metrics.py)** - BLEU, ROUGE, exact match, and related reference-based metrics
- **[eval-cost-calculator.py](./scripts/eval-cost-calculator.py)** - Estimate eval cost (tokens × model price)
- **[regression-runner.py](./scripts/regression-runner.py)** - Compare new results to baseline and flag regressions
- **[eval-summary-report.py](./scripts/eval-summary-report.py)** - One-page Markdown summary from eval JSON/CSV (e.g. from prompt-eval-harness)
- **[human-eval-coordinator.py](./scripts/human-eval-coordinator.py)** - Assign tasks to human raters, calculate inter-rater reliability (Cohen's/Fleiss' Kappa, Krippendorff's Alpha), and consolidate ratings

See [scripts/README.md](./scripts/README.md) for usage instructions (if present).

### 5. Report Results

Use [eval-summary-report.py](./scripts/eval-summary-report.py) to generate a one-page Markdown summary from eval results:

```bash
python evals/scripts/eval-summary-report.py results.json --output report.md
python evals/scripts/eval-summary-report.py results.json --stdout
```

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

