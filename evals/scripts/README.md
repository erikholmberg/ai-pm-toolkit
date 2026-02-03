# LLM Evaluation Scripts

Python scripts for evaluating LLM outputs and prompts.

## Scripts

### `llm-as-judge-evaluator.py`

Uses a stronger LLM (judge) to evaluate outputs from other models on multiple dimensions.

**Features:**
- Multi-dimensional evaluation (accuracy, relevance, completeness, coherence, fluency)
- Customizable dimensions and scoring scales
- Batch processing with progress tracking
- Comparison between multiple model versions
- Export results to JSON or CSV
- Supports Claude and OpenAI models as judges

**Usage:**

```bash
# Interactive mode
python llm-as-judge-evaluator.py --interactive

# Evaluate from JSON file
python llm-as-judge-evaluator.py --input test_cases.json --output results.json

# Use specific judge model
python llm-as-judge-evaluator.py --input test.json --judge gpt-4 --output results.json

# Custom scoring scale
python llm-as-judge-evaluator.py --input test.json --scale 10
```

**Test Case Format:**

```json
[
  {
    "id": "tc1",
    "input": "What is the capital of France?",
    "output": "The capital of France is Paris.",
    "expected_output": "Paris",
    "category": "geography"
  },
  {
    "id": "tc2",
    "input": "Explain quantum computing in simple terms.",
    "output": "Quantum computing uses quantum mechanics...",
    "category": "science"
  }
]
```

**Example Output:**

The evaluator generates scores for each dimension and provides reasoning:

```json
{
  "test_case_id": "tc1",
  "input": "What is the capital of France?",
  "output": "The capital of France is Paris.",
  "scores": {
    "accuracy": 5.0,
    "relevance": 5.0,
    "completeness": 4.0,
    "coherence": 5.0,
    "fluency": 5.0,
    "overall": 4.8
  },
  "reasoning": {
    "accuracy": "The output is factually correct.",
    "relevance": "Directly answers the question.",
    ...
  }
}
```

### `prompt-eval-harness.py`

Evaluate and compare different prompt versions.

**Usage:**

```bash
python prompt-eval-harness.py --interactive
python prompt-eval-harness.py --config eval_config.json
```

### `automated-metrics.py`

Compute BLEU, ROUGE (1/2/L), exact match, contains-reference, and length ratio for reference-based evals.

**Usage:**

```bash
python automated-metrics.py --input test_cases.json --output metrics.json
python automated-metrics.py --input test_cases.json --reference-field expected_output --no-rouge
```

**Requirements:** `nltk`, `rouge-score`. Run once: `python -c "import nltk; nltk.download('punkt')"`

### `eval-cost-calculator.py`

Estimate the cost of running evals (tokens × model price). Supports planning and post-run cost from results JSON.

**Usage:**

```bash
python eval-cost-calculator.py --cases 500 --avg-input 200 --avg-output 300 --model claude-3-sonnet-20240229
python eval-cost-calculator.py --results results.json
python eval-cost-calculator.py --interactive
python eval-cost-calculator.py --list-models
```

### `regression-runner.py`

Compare new eval results to a baseline and flag regressions (e.g. score drops by more than X%).

**Usage:**

```bash
python regression-runner.py --baseline baseline.json --new new.json
python regression-runner.py --baseline baseline.json --new new.json --threshold 5 --metric overall
python regression-runner.py --baseline baseline.json --new new.json --output comparison.json --fail-on-regression
```

### `eval-report-generator.py`

Generate markdown or HTML reports from eval results JSON (summary stats and per-case table).

**Usage:**

```bash
python eval-report-generator.py --input results.json --output report.md
python eval-report-generator.py --input results.json --output report.html --format html --title "Q2 Eval Report"
```

## Requirements

Install dependencies:

```bash
pip install openai anthropic pandas tqdm nltk rouge-score
python -c "import nltk; nltk.download('punkt')"
```

Or use the main requirements file:

```bash
pip install -r ../../scripts/requirements.txt
```

## Environment Variables

Set API keys before running:

```bash
export ANTHROPIC_API_KEY=your-key-here
export OPENAI_API_KEY=your-key-here
```

## Tips

1. **Choose the right judge model:**
   - For high-quality evaluation: `claude-3-opus-20240229` or `gpt-4`
   - For faster/cheaper evaluation: `claude-3-sonnet-20240229` or `gpt-4-turbo`
   - For large batches: Use faster models to reduce cost/time

2. **Customize dimensions:**
   - Modify the `DEFAULT_DIMENSIONS` in the script or pass custom dimensions

3. **Batch processing:**
   - The evaluator handles errors gracefully and continues processing
   - Results are saved incrementally (if using file output)

4. **Cost considerations:**
   - Judge model calls can be expensive for large batches
   - Consider using faster models for initial screening
   - Use stronger models for final evaluation
