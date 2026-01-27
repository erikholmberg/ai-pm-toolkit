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

## Requirements

Install dependencies:

```bash
pip install openai anthropic pandas tqdm
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
