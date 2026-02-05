# AI Product Pricing Strategies

Frameworks and options for pricing AI-powered products.

---

## Why AI Pricing Is Different

| Factor | Traditional Software | AI Products |
|--------|----------------------|-------------|
| **Cost structure** | Mostly fixed (hosting, dev) | Variable (compute, API calls, tokens) |
| **Margins** | Predictable | Can compress when usage spikes |
| **Value perception** | Feature-based | Often "magic" or efficiency gain |
| **Competition** | Feature parity | Rapid commoditization of base models |

**Implications:** You need a pricing model that aligns with variable cost, captures value, and stays understandable to buyers.

---

## Pricing Model Options

### 1. Usage-Based (Pay per use)

**How it works:** Charge per API call, per token, per request, or per unit of output (e.g. per image, per minute of audio).

| Pros | Cons |
|------|------|
| Aligns cost and revenue | Revenue (and cost) hard to predict |
| Low barrier to try | Can feel unpredictable to enterprise |
| Scales with customer value | Heavy users can have shock at scale |

**Best for:** APIs, developer tools, high-variance usage. Examples: OpenAI API, Anthropic, many inference APIs.

**Design choices:**
- **Tiers:** Free tier (rate-limited), then graduated pricing (e.g. first 1M tokens cheap, then step-up).
- **Commitments:** Offer discounts for committed volume (e.g. $X/month minimum for 20% off) to smooth revenue.

---

### 2. Subscription (Flat or Tiered)

**How it works:** Monthly or annual fee per seat, per team, or per product tier. AI may be included or an add-on.

| Pros | Cons |
|------|------|
| Predictable revenue | Light users may feel overcharged |
| Easy to budget for buyer | Need to manage cost per subscriber |
| Familiar motion | Usage can grow inside fixed price |

**Best for:** SaaS with AI features, productivity tools, SMB. Examples: ChatGPT Plus, many vertical SaaS products.

**Design choices:**
- **Seat-based:** Per user/month. Cap or meter heavy usage (e.g. N requests/month) to protect margins.
- **Tiered:** Free / Pro / Team / Enterprise with clear limits and features per tier.
- **AI add-on:** Base product + "AI pack" or "Copilot" add-on so non-AI users don’t subsidize heavy AI use.

---

### 3. Hybrid (Base + Usage)

**How it works:** Fixed fee (subscription or minimum) plus usage-based overage or usage-based add-ons.

| Pros | Cons |
|------|------|
| Predictability + upside | More complex to explain and bill |
| Captures heavy users | Need clear caps and alerts |
| Reduces "bill shock" | Overage rules and communication matter |

**Best for:** Enterprise, prosumer, or when usage variance is high but you want a floor. Examples: GitHub Copilot (seat + possible overage), some data/AI platforms.

**Design choices:**
- **Included allowance:** E.g. $50/month includes 10M tokens; above that, $X per 1M.
- **Overage caps:** Hard cap (stop) or soft cap (alert then bill) to avoid surprise.

---

### 4. Value-Based (Outcome or ROI)

**How it works:** Price tied to outcome (e.g. per resolved ticket, per qualified lead, % of savings).

| Pros | Cons |
|------|------|
| Aligns with customer ROI | Hard to measure and attribute |
| Premium potential | Legal/contract complexity |
| Differentiates | Not all buyers want outcome-based |

**Best for:** High-touch sales, clear ROI (e.g. support, sales automation, risk). Examples: some contact center AI, revenue-share deals.

**Design choices:**
- **Success fee:** Per conversion, per closed deal, etc.
- **Gain-share:** % of savings or incremental revenue. Often requires audit or trusted metrics.

---

## Consumer vs Enterprise

| Dimension | Consumer | Enterprise |
|-----------|----------|------------|
| **Typical model** | Freemium, subscription, low per-unit | Seats + usage, ELA, custom contracts |
| **Price sensitivity** | High; low willingness to pay per token | Lower if ROI is clear; need predictability |
| **Procurement** | Self-serve, card | Procurement, security, legal |
| **Usage patterns** | Spiky, viral risk | More predictable with caps and SLAs |

---

## Handling Variable AI Cost

1. **Model choice:** Use smaller/cheaper models where quality allows; reserve premium models for high-value flows.
2. **Caching:** Cache frequent or repeated inputs to cut API cost.
3. **Prompt design:** Shorter, structured prompts reduce tokens and cost.
4. **Guardrails:** Limit output length and retries to cap cost per request.
5. **Pricing buffer:** Price above expected cost so that variance and heavy users don’t erase margin; revisit as cost and usage data improve.

---

## Pricing Checklist

- [ ] **Cost baseline:** Do you know cost per request/user/month at target usage?
- [ ] **Value narrative:** Can you explain what the customer gets (e.g. time saved, quality, throughput)?
- [ ] **Competitive reference:** How do alternatives price (per seat, per use, hybrid)?
- [ ] **Feedback loop:** Can you track usage, cost, and willingness to pay (surveys, conversion, churn)?
- [ ] **Packaging:** Are tiers/limits simple to explain and sell?
- [ ] **Overage and caps:** Are overages and caps (if any) clear and communicated?

---

## Example Reference (Representative Only)

| Product type | Typical model | Note |
|--------------|----------------|------|
| LLM API | $/1M input + $/1M output tokens | Usage-based; list + volume discounts |
| Coding assistant | $/user/month | Subscription; may cap requests |
| Vertical SaaS + AI | Base + AI add-on or usage | Hybrid common |
| Enterprise copilot | Seats + usage or ELA | Hybrid or custom |

*Update with your own research; pricing changes often.*

---

## Related

- [AI Product Strategy Framework](./ai-product-strategy-framework.md) – Where pricing fits in strategy
- [Go-to-Market for AI Products](./go-to-market-ai-products.md) – Launch and packaging
