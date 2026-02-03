# Golden Dataset Template

Use this template to document and structure a golden (reference) dataset for LLM evaluation.

---

## Dataset Overview

**Dataset Name:** [e.g. "Search QA v1", "Support Responses – Q2"]

**Version:** [e.g. 1.0]

**Created:** [Date]

**Owner:** [Name or team]

**Purpose:** [What evals this dataset supports: regression, prompt comparison, model comparison, etc.]

**Last Updated:** [Date]

---

## Schema

Each test case in the dataset should follow this structure (JSON).

### Required Fields

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Unique identifier (e.g. `tc_001`, `search_qa_42`) |
| `input` | string | The prompt or user input sent to the model |
| `output` | string | **For evals:** model output to score. **For golden:** reference answer (if applicable) |
| `expected_output` | string (optional) | Reference / gold answer. Used for BLEU, ROUGE, exact match |

### Optional Fields

| Field | Type | Description |
|-------|------|-------------|
| `category` | string | Category or tag (e.g. `geography`, `edge_case`, `safety`) |
| `metadata` | object | Arbitrary key-value (e.g. `difficulty`, `source`, `locale`) |
| `context` | string | Additional context (e.g. conversation history, document) |
| `rubric` | string or object | Scoring rubric or criteria for this case |

### Example JSON

```json
[
  {
    "id": "tc_001",
    "input": "What is the capital of France?",
    "output": "",
    "expected_output": "Paris",
    "category": "geography",
    "metadata": { "difficulty": "easy", "source": "manual" }
  },
  {
    "id": "tc_002",
    "input": "Explain quantum computing in one sentence.",
    "output": "",
    "expected_output": "Quantum computing uses quantum mechanics to process information in ways that classical computers cannot.",
    "category": "science",
    "metadata": { "difficulty": "medium" }
  }
]
```

**Note:** Leave `output` empty when building a golden set; fill it when you have model outputs to evaluate (e.g. from a run or from LLM-as-judge input).

---

## Test Case Categories

Define categories so you can slice results (e.g. by difficulty, domain, or risk).

| Category | Description | Target Count |
|----------|-------------|--------------|
| [e.g. Happy path] | [Description] | [Number] |
| [e.g. Edge cases] | [Description] | [Number] |
| [e.g. Adversarial] | [Description] | [Number] |
| [e.g. By segment] | [Description] | [Number] |

---

## Composition Checklist

- [ ] **Coverage:** Cases span main user intents and segments
- [ ] **Edge cases:** Boundary inputs, ambiguous questions, rare domains
- [ ] **Reference quality:** `expected_output` (where used) is correct and consistent
- [ ] **Ids:** Unique, stable IDs for regression tracking
- [ ] **Categories:** Every case has a category (or "uncategorized")
- [ ] **Size:** Enough cases for statistical power (see eval plan; often 50–500+ per eval)

---

## File Conventions

- **Storage:** [e.g. `evals/datasets/<name>_v1.json`]
- **Naming:** `{dataset_name}_v{version}.json`
- **Versioning:** Bump version when adding/removing or materially changing cases; keep a changelog below.

---

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | [Date] | Initial dataset |
| | | |

---

## Usage with Toolkit Scripts

- **LLM-as-judge:** Use this file as `--input`; ensure each row has `input` and `output` (model output). Optionally include `expected_output`.
- **Automated metrics:** Use `--input` pointing to a JSON with `output` and `expected_output`; script will compute BLEU, ROUGE, exact match.
- **Regression runner:** Compare a baseline results JSON to a new run; baseline and new runs should share the same test case IDs.
