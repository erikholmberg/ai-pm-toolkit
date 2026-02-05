# Evaluating Models on Amazon Bedrock

How to run evals when your app uses Amazon Bedrock.

---

## Options

### 1. Use your existing eval harness + Bedrock

Your golden dataset and eval scripts stay the same; only the **invocation** changes.

1. **Generate outputs:** For each test case, call Bedrock (e.g. via `boto3` or the AWS SDK) with the same prompt/config you use in production, and save `(test_case_id, input, output)`.
2. **Score:** Feed that JSON into your existing tools:
   - **LLM-as-judge:** Use `llm-as-judge-evaluator.py` with the model output JSON (judge can be Claude/OpenAI or another Bedrock model).
   - **Automated metrics:** Use `automated-metrics.py` with `output` and `expected_output`.
3. **Cost:** Use `bedrock-cost-calculator.py` or `eval-cost-calculator.py` (if you add Bedrock pricing) to estimate eval cost.

**Minimal Bedrock invocation (Python/boto3):**

```python
import boto3
import json

client = boto3.client("bedrock-runtime")
model_id = "anthropic.claude-3-5-sonnet-v2-20241022"

def invoke(prompt: str, max_tokens: int = 1024) -> str:
    body = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": prompt}],
    }
    resp = client.invoke_model(modelId=model_id, body=json.dumps(body))
    result = json.loads(resp["body"].read())
    return result["content"][0]["text"]
```

Run this for each test case, collect `(id, input, output)` into a JSON that matches your [golden dataset schema](../templates/golden-dataset-template.md), then run your usual evals.

---

### 2. Bedrock Model Evaluation (native)

Amazon Bedrock has a **Model Evaluation** feature in the console (and APIs) for:

- Automated evals (e.g. built-in metrics)
- Human-in-the-loop eval workflows
- RAG evaluation against a Knowledge Base
- LLM-as-judge using a Bedrock model

**When to use:** You want a single place for dataset + runs + human tasks inside AWS, or you’re already using Bedrock for the judge.

**Pricing:** You pay for the model invocations used in the eval (on-demand Standard tier) plus, for human eval, $0.21 per completed human task. See [Bedrock pricing – Model Evaluation](https://aws.amazon.com/bedrock/pricing/).

---

### 3. Hybrid: Generate on Bedrock, judge elsewhere

- **Generate** responses with Bedrock (script or pipeline above).
- **Judge** with your existing LLM-as-judge (e.g. Claude or GPT-4 via API) or with automated metrics.
- **Compare** multiple Bedrock models (e.g. Claude vs Llama vs Mistral) on the same test set using the same judge and metrics.

---

## Checklist

- [ ] Golden dataset prepared (see [golden-dataset-template.md](../templates/golden-dataset-template.md)).
- [ ] Bedrock model ID and region fixed; access enabled in console if required.
- [ ] Invocation script or pipeline writes `(id, input, output)` in the format your eval scripts expect.
- [ ] Eval run: LLM-as-judge and/or automated metrics on the collected outputs.
- [ ] Cost estimated with `bedrock-cost-calculator.py` (and eval-cost-calculator if you added Bedrock).
- [ ] Regression: baseline and new runs compared with `regression-runner.py`.

---

## Related

- [LLM Eval Framework](./llm-eval-framework.md)
- [Eval scripts](../scripts/README.md) (llm-as-judge, automated-metrics, regression-runner)
- [AWS Bedrock for PMs](../../learning/aws-bedrock-for-pms.md)
- [Bedrock pricing](https://aws.amazon.com/bedrock/pricing/)
