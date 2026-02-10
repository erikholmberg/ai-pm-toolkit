# Build vs. Buy Decision Framework for AI Products

A structured framework for deciding whether to build AI capabilities in-house, buy/license a vendor solution, or use a managed API. AI PMs face this decision constantly — fine-tune a model vs. use an API, build an eval pipeline vs. adopt a platform, train in-house vs. license a foundation model.

---

## Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Build vs. Buy Spectrum                            │
├────────────┬────────────┬──────────────┬────────────┬───────────────┤
│  Build     │  Fine-Tune │  API + Custom│  Managed   │  Off-the-     │
│  From      │  Open      │  Orchestrate │  Service   │  Shelf SaaS   │
│  Scratch   │  Source    │              │            │               │
├────────────┴────────────┴──────────────┴────────────┴───────────────┤
│ ← More Control                              Less Effort →           │
│ ← More Cost                                Faster to Market →       │
│ ← More Differentiation                     Less Differentiation →   │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Decision Framework

### Step 1: Classify the Capability

Before evaluating build vs. buy, categorize what you're building.

| Category | Description | Default Bias | Examples |
|----------|-------------|-------------|----------|
| **Core Differentiator** | The AI capability IS your product or key competitive advantage | Build | Your proprietary recommendation engine, custom ML model trained on your data |
| **Key Enabler** | Important capability that supports the product but isn't the product itself | Buy or API + Customize | Eval pipeline, monitoring, search/RAG |
| **Commodity** | Well-solved problem, no competitive advantage from custom solution | Buy | Auth, logging, basic NLP, speech-to-text |
| **Experimental** | Unproven capability you're still validating | API first, build later | New AI feature in prototype phase |

> **Rule of thumb:** Only build what differentiates. Buy everything else.

---

### Step 2: Score Decision Criteria

Rate each criterion 1-5 for both Build and Buy options.

#### Strategic Criteria

| Criterion | Weight | Build Score (1-5) | Buy Score (1-5) | Notes |
|-----------|--------|-------------------|-----------------|-------|
| **Competitive differentiation** | High | _How much edge does custom give us?_ | _Can competitors buy the same thing?_ | |
| **Strategic control** | High | _Do we need full control over roadmap?_ | _Is vendor roadmap aligned with ours?_ | |
| **Data sensitivity** | High | _Can we keep data fully in-house?_ | _Does vendor data handling meet our bar?_ | |
| **Speed to value** | Medium | _How long until we ship v1?_ | _How fast can we integrate?_ | |
| **Long-term flexibility** | Medium | _Can we evolve freely?_ | _Are we locked into vendor patterns?_ | |

#### Operational Criteria

| Criterion | Weight | Build Score (1-5) | Buy Score (1-5) | Notes |
|-----------|--------|-------------------|-----------------|-------|
| **Team capability** | High | _Do we have the ML talent?_ | _Can our team integrate effectively?_ | |
| **Maintenance burden** | High | _Can we sustain ongoing operations?_ | _Is vendor reliable and well-maintained?_ | |
| **Cost (Year 1)** | Medium | _Total build cost including opportunity cost_ | _License + integration + ongoing fees_ | |
| **Cost (Year 2-3)** | Medium | _Ongoing: team, infra, iteration_ | _Ongoing: fees, scaling costs_ | |
| **Time to market** | High | _Weeks/months to production_ | _Days/weeks to production_ | |

#### Technical Criteria

| Criterion | Weight | Build Score (1-5) | Buy Score (1-5) | Notes |
|-----------|--------|-------------------|-----------------|-------|
| **Quality/accuracy needed** | High | _Can we achieve required quality?_ | _Does vendor meet our quality bar?_ | |
| **Customization needed** | Medium | _How much do we need to tailor?_ | _Does vendor support our use cases?_ | |
| **Integration complexity** | Medium | _How does it fit our architecture?_ | _How well does vendor API integrate?_ | |
| **Scalability** | Medium | _Can we scale our infra?_ | _Does vendor scale with us?_ | |
| **Observability** | Low | _Full visibility into behavior_ | _Does vendor expose metrics we need?_ | |

---

### Step 3: Evaluate Total Cost of Ownership

#### Build Cost Model

| Cost Component | Year 1 | Year 2 | Year 3 |
|---------------|--------|--------|--------|
| **Engineering headcount** | _____ | _____ | _____ |
| ML engineer(s) | | | |
| Data engineer(s) | | | |
| Infrastructure engineer(s) | | | |
| **Infrastructure** | _____ | _____ | _____ |
| Training compute (GPU) | | | |
| Inference compute | | | |
| Storage (data + models) | | | |
| **Data** | _____ | _____ | _____ |
| Data acquisition/labeling | | | |
| Data pipeline maintenance | | | |
| **Opportunity cost** | _____ | _____ | _____ |
| What could the team build instead? | | | |
| **Total Build** | **_____** | **_____** | **_____** |

#### Buy Cost Model

| Cost Component | Year 1 | Year 2 | Year 3 |
|---------------|--------|--------|--------|
| **Vendor fees** | _____ | _____ | _____ |
| License/subscription | | | |
| Usage-based fees (projected) | | | |
| Overage costs (estimated) | | | |
| **Integration** | _____ | _____ | _____ |
| Integration engineering | | | |
| Custom wrapper/orchestration | | | |
| **Ongoing** | _____ | _____ | _____ |
| Vendor management time | | | |
| Internal maintenance | | | |
| **Risk** | _____ | _____ | _____ |
| Vendor shutdown/pivot risk | | | |
| Migration cost if we switch | | | |
| **Total Buy** | **_____** | **_____** | **_____** |

---

### Step 4: Apply AI-Specific Considerations

These factors are unique to AI/ML build-vs-buy decisions and often overlooked.

#### Model Quality & Iteration Speed

| Factor | Build Advantage | Buy Advantage |
|--------|----------------|---------------|
| **Fine-tuning on your data** | Full control over training data and objectives | Some vendors support fine-tuning; others don't |
| **Eval and testing** | Custom eval pipeline, full regression testing | May be limited to vendor's eval framework |
| **Iteration speed** | Slower initial setup, faster long-term iteration | Fast to start, may hit customization walls |
| **Model updates** | You control when/how model changes | Vendor may update model under you (breaking changes) |

#### Data & Privacy

| Factor | Build Advantage | Buy Advantage |
|--------|----------------|---------------|
| **Data residency** | Full control over where data lives | Must trust vendor's infrastructure |
| **Training data ownership** | Your data stays yours | Vendor may use your data to improve their model |
| **PII handling** | Custom data handling pipeline | Vendor may have mature compliance (SOC2, HIPAA) |
| **Audit trail** | Full visibility | May be opaque |

#### Vendor Lock-in Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Vendor raises prices significantly | Medium | High | Contract terms, usage caps, build migration plan |
| Vendor deprecates your model/API | Medium | High | Abstract vendor behind interface, keep eval suite |
| Vendor gets acquired/shuts down | Low | Critical | Multi-vendor strategy, data export plan |
| Vendor quality degrades | Medium | Medium | Continuous eval monitoring, fallback model |
| Vendor changes data handling policy | Low | High | Contractual guarantees, data processing agreement |

---

### Step 5: Make the Decision

#### Decision Matrix

```
                    │ Low Strategic Value │ High Strategic Value │
────────────────────┼─────────────────────┼──────────────────────┤
 Team Has           │       BUY           │     BUILD or         │
 Capability         │  (don't waste       │     FINE-TUNE        │
                    │   talent on this)   │  (invest in moat)    │
────────────────────┼─────────────────────┼──────────────────────┤
 Team Lacks         │       BUY           │     BUY NOW,         │
 Capability         │  (no brainer)       │     BUILD LATER      │
                    │                     │  (validate first)    │
────────────────────┴─────────────────────┴──────────────────────┘
```

#### Recommended Approach by Scenario

| Scenario | Recommendation | Rationale |
|----------|---------------|-----------|
| Prototyping/validating a new AI feature | **API first** | Validate demand before investing in build |
| AI is the core product differentiator | **Build** | You can't rent your competitive advantage |
| Well-solved problem (search, OCR, STT) | **Buy** | Commoditized; building adds cost, not value |
| Need domain-specific model quality | **Fine-tune open-source** | Best balance of control, cost, and speed |
| Regulated industry (healthcare, finance) | **Build or fine-tune** | Data sovereignty and audit requirements |
| Small team, need to ship fast | **Buy / API** | Engineering bandwidth is the bottleneck |
| Enterprise customers demand on-prem | **Open-source + self-host** | Customer requirements override your preference |

---

### Step 6: Document the Decision

#### Decision Record Template

```markdown
## Build vs. Buy Decision: [CAPABILITY NAME]

**Date:** [DATE]
**Decision Owner:** [PM NAME]
**Decision:** [BUILD / BUY / API + CUSTOMIZE / FINE-TUNE]

### Context
[Why are we making this decision now? What triggered it?]

### Options Considered
1. [Option A]: [Brief description]
2. [Option B]: [Brief description]
3. [Option C]: [Brief description]

### Decision Criteria & Scores
[Paste scored criteria from Step 2]

### Total Cost of Ownership (3-year)
- Build: $[AMOUNT]
- Buy: $[AMOUNT]

### Key Factors
- [Factor 1]: [How it influenced the decision]
- [Factor 2]: [How it influenced the decision]

### Risks & Mitigations
- [Risk 1]: [Mitigation]

### Reversibility
[How hard is it to change this decision later? What's the exit plan?]

### Review Date
[When will we revisit this decision? e.g., 6 months, 12 months]
```

---

## Common Patterns in AI Products

### Pattern: "API Now, Build Later"

Most successful AI products follow this pattern:

```
Phase 1 (0-6 months):    Use API (GPT-4, Claude, etc.)
                          → Validate product-market fit
                          → Build eval suite
                          → Collect user data and feedback

Phase 2 (6-18 months):   Fine-tune open-source model on your data
                          → Reduce cost per request
                          → Improve quality on your domain
                          → Maintain API as fallback

Phase 3 (18+ months):    Custom model (if warranted)
                          → Only if core differentiator
                          → Only if data and team are ready
                          → Most companies never need this
```

### Pattern: "Multi-Model Routing"

Use different solutions for different tiers of the same feature:

| Tier | Model | Use Case |
|------|-------|----------|
| Simple requests | Small/fast model (Haiku, GPT-4o-mini) | Low-cost, high-volume |
| Standard requests | Mid-tier API (Sonnet, GPT-4o) | Balance of quality and cost |
| Complex requests | Best available (Opus, GPT-4) or custom | Quality-critical, lower volume |

---

## Pitfalls to Avoid

### 1. "We can build it better"
Most teams underestimate the effort to match a mature vendor. Build only when the data shows you must.

### 2. "APIs are too expensive at scale"
Do the math. A $500K/year API bill that saves 3 ML engineers ($600K+ fully loaded) is a good deal.

### 3. "We'll build it later"
Vendor integrations become load-bearing. If you plan to build later, invest in an abstraction layer from day one.

### 4. "The vendor will always be there"
Vendor risk is real. Keep an eval suite so you can benchmark alternatives. Abstract behind your own interface.

### 5. "We need to own our model"
Owning the model ≠ owning the business outcome. Focus on owning the data, the eval suite, and the user experience.

---

## Quick Reference Checklist

Before committing to build or buy:

- [ ] Classified the capability (differentiator vs. commodity)
- [ ] Scored all decision criteria
- [ ] Calculated 3-year TCO for both options
- [ ] Assessed data sensitivity and regulatory requirements
- [ ] Evaluated team capability honestly
- [ ] Defined an exit strategy (vendor migration or build pivot)
- [ ] Set a review date to revisit the decision
- [ ] Documented the decision with rationale

