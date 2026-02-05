# AWS Bedrock for Product Managers

What you need to know about building on Amazon Bedrock—without being an AWS expert.

---

## What Is Bedrock?

**Amazon Bedrock** is a managed service that lets you use foundation models (FMs) from multiple providers (Anthropic, Meta, Mistral, Amazon, Cohere, etc.) through a single API. You don’t host the models yourself; AWS runs them and bills you for usage.

**Why it matters for PMs:**
- **One contract:** Use Claude, Llama, Titan, and others without separate vendor deals.
- **Data in AWS:** Inference runs in your chosen AWS region; data doesn’t leave your cloud for third‑party model providers (provider runs in AWS).
- **Enterprise fit:** IAM, VPC, compliance, and existing AWS spend.
- **Choice:** Swap or compare models without rewriting the whole app.

---

## Key Concepts

| Concept | What it means |
|--------|----------------|
| **Foundation model (FM)** | A pre-trained model (e.g. Claude, Llama) you invoke via API. |
| **Model ID** | The Bedrock identifier for a model (e.g. `anthropic.claude-3-5-sonnet-v2-20241022`). |
| **On-demand inference** | Pay per request (per input/output token). Default for most use cases. |
| **Provisioned Throughput** | Reserve capacity (model units) for predictable latency and higher throughput; billed by time. |
| **Batch inference** | Submit large jobs (e.g. overnight); often ~50% cheaper than on-demand. |
| **Knowledge Bases** | RAG: ingest docs, query with a model. You pay for embedding + retrieval + model tokens. |
| **Guardrails** | Content filters, PII redaction, denied topics. You pay per text unit processed. |

---

## Model Families on Bedrock (Representative)

| Provider | Examples | Typical use |
|----------|----------|-------------|
| **Anthropic** | Claude 3.5 Sonnet, Claude 3 Haiku | General chat, long context, strong instruction-following |
| **Amazon** | Nova, Titan (text, embeddings, image) | Low latency, embeddings, image generation, AWS-native |
| **Meta** | Llama 3.2, 3.3 | Open weights, cost-effective, customization (fine-tuning) |
| **Mistral** | Mistral Large, Ministral | Multilingual, good quality/cost |
| **Cohere** | Command, Embed | Embeddings, RAG, rerank |
| **Others** | Google Gemma, NVIDIA, etc. | Specialized or regional needs |

**Pricing** is per 1M input and 1M output tokens and varies by model and region. See [AWS Bedrock pricing](https://aws.amazon.com/bedrock/pricing/) and the `bedrock-cost-calculator.py` script in this toolkit.

---

## When to Use Bedrock vs Direct APIs

| Use Bedrock when | Prefer direct API when |
|------------------|-------------------------|
| You’re already on AWS | You’re not on AWS and don’t want to be |
| You need data in a specific region | You’re fine with data in provider’s cloud |
| You want to switch models without new contracts | You’re committed to one provider (e.g. OpenAI only) |
| You need IAM, VPC, private link | You’re building a quick prototype or external app |
| You want multiple FMs from one place | You need provider-specific features (e.g. fine-tuning UI) |

---

## Tiers and Cost Levers

- **Standard (on-demand):** Default; pay per token.
- **Batch:** Async jobs; often ~50% lower $/token.
- **Provisioned Throughput:** Reserve capacity; good for steady, high-volume or latency-sensitive workloads.
- **Flex / Priority:** Discount or premium tiers for some models; check the pricing page.

**PM takeaway:** For variable or early-stage usage, start with on-demand. Use batch for bulk evals or offline jobs. Consider provisioned only when you have stable, high volume and need predictable latency/cost.

---

## Data and Compliance

- **Region:** You choose the region; inference and (for most services) data stay there. Use this for data residency.
- **No training on your data:** AWS does not use your inputs/outputs to train provider models (see AWS and provider terms).
- **Guardrails:** Use Bedrock Guardrails for content filters, PII, and denied topics if you have safety or compliance requirements.

---

## Limits and Quotas

- **Model access:** Some models require “extended access” or approval in the Bedrock console.
- **Rate limits:** Per-account and per-model TPM (tokens per minute) and RPM (requests per minute). Request increases via Service Quotas.
- **Context length:** Varies by model (e.g. 8K–200K tokens). Check the model card in the console or docs.

---

## What to Track as a PM

| Metric | Why it matters |
|--------|----------------|
| **Token usage (input/output)** | Drives cost; optimize prompts and model choice. |
| **Latency (TTFT, time to last token)** | UX; may need provisioned or a smaller model. |
| **Error rate and throttles** | Reliability; may need backoff or quota increase. |
| **Model mix** | Cost and quality; use smaller/cheaper models where quality allows. |
| **Guardrails usage** | If you use them; cost is per text unit. |

---

## Quick Links

- [Bedrock pricing](https://aws.amazon.com/bedrock/pricing/)
- [Bedrock user guide](https://docs.aws.amazon.com/bedrock/latest/userguide/)
- [Service tiers](https://aws.amazon.com/bedrock/service-tiers/)
- **In this toolkit:** [Bedrock cost calculator](../scripts/bedrock-cost-calculator.py), [Bedrock model selection prompt](../prompts/ai-ml/bedrock-model-selection.prompt.md), [Bedrock eval guide](../evals/frameworks/bedrock-eval-guide.md)
