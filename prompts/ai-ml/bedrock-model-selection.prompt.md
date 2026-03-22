# Bedrock Model Selection

Use this prompt to choose the right Amazon Bedrock foundation model for your use case.

---

## Prompt

```
You are helping me choose an Amazon Bedrock foundation model for a product feature.

## Context
- **Use case:** [e.g. customer support chatbot, document summarization, code review assistant]
- **Constraints:** [e.g. max latency 2s, budget $X per 1M tokens, must support 100K context]
- **Quality needs:** [e.g. must be highly accurate, multilingual, or strong at reasoning]
- **Volume:** [e.g. 10K requests/day, batch overnight jobs]

## Available model families (representative)
- **Anthropic Claude** (e.g. Claude 3.5 Sonnet, Haiku, Opus): Strong instruction-following, long context, higher cost for larger models.
- **Amazon Nova / Titan**: Low latency, cost-effective, good for high volume; Titan for embeddings and image.
- **Meta Llama** (e.g. 3.2, 3.3): Open, cost-effective, fine-tunable.
- **Mistral** (e.g. Mistral Large, Ministral): Good quality/cost, multilingual.
- **Cohere**: Strong for embeddings, RAG, rerank.

## What I need from you
1. Recommend 1–2 specific Bedrock model IDs (or family + size) that fit the use case and constraints.
2. Briefly explain tradeoffs (cost vs quality vs latency).
3. Note any limits I should plan for (context length, rate limits, region availability).
4. If relevant, suggest when to use batch inference or provisioned throughput instead of on-demand.
```

---

## Example fill-in

**Use case:** In-app chat assistant that answers questions about our product docs.  
**Constraints:** Response within 3 seconds; we’re cost-sensitive.  
**Quality:** Must be accurate and stay on-topic; English only for now.  
**Volume:** ~50K requests/day.

---

## Tips

- **Latency:** Prefer Haiku, Titan Lite, or smaller Mistral/Llama for real-time chat; use Sonnet/Opus or Mistral Large where quality matters more than speed.
- **Cost:** Start with a smaller or cheaper model and only move up if quality or capability isn’t enough.
- **Context:** If you need 100K+ tokens (long docs), ensure the model supports it (e.g. Claude, some Llama variants).
- **Region:** Confirm the model is available in your chosen AWS region (Bedrock console or docs).
- **Pricing:** Use the toolkit’s `bedrock-cost-calculator.py` to compare $/1M tokens for candidates.
- **Structured tradeoffs:** Score candidates on shared criteria (quality, latency fit, context, etc.) with `model-selection-scorecard.py` and optional weight sensitivity.
