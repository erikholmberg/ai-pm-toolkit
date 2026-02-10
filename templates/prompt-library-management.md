# Prompt Library Management Template

A template for cataloging, versioning, and managing prompts across an AI product. As AI products scale, managing prompt versions across environments becomes a real challenge — this template provides structure for tracking prompts, their performance, ownership, and lifecycle.

---

## Overview

Use this template to maintain a central registry of all prompts used in your product. Each prompt should have:
- A unique identifier and human-readable name
- A clear owner responsible for its quality
- Version history with performance baselines
- Environment deployment status
- Eval results tied to each version

---

## Prompt Registry

### Active Prompts

| Prompt ID | Name | Owner | Current Version | Environment | Last Updated | Status |
|-----------|------|-------|----------------|-------------|-------------|--------|
| `PRM-001` | [e.g., Main System Prompt] | [PM/Eng name] | v2.3 | Production | [DATE] | Active |
| `PRM-002` | [e.g., Summarization Prompt] | [Name] | v1.1 | Production | [DATE] | Active |
| `PRM-003` | [e.g., Classification Prompt] | [Name] | v3.0 | Staging | [DATE] | Testing |
| `PRM-004` | [e.g., RAG Context Prompt] | [Name] | v1.0 | Production | [DATE] | Active |
| `PRM-005` | | | | | | |

### Status Definitions

| Status | Meaning |
|--------|---------|
| **Active** | Running in production, monitored |
| **Testing** | In staging/canary, pending promotion |
| **Deprecated** | Scheduled for removal, replacement available |
| **Archived** | No longer in use, kept for reference |
| **Draft** | Under development, not yet in any environment |

---

## Prompt Detail Card

Fill out one card per prompt. This is the single source of truth for each prompt.

### Prompt: [PROMPT ID] — [NAME]

#### Metadata

| Field | Value |
|-------|-------|
| **Prompt ID** | [e.g., PRM-001] |
| **Name** | [Human-readable name] |
| **Description** | [What this prompt does, in one sentence] |
| **Owner** | [Name and team] |
| **Model(s)** | [Which model(s) this is optimized for] |
| **Feature/Product Area** | [Where this prompt is used] |
| **Created** | [DATE] |
| **Last Modified** | [DATE] |
| **Status** | [Active / Testing / Deprecated / Archived / Draft] |

#### Current Prompt Text

```
[PASTE THE CURRENT PRODUCTION PROMPT HERE]

Include:
- System prompt
- User prompt template (with {{variable}} placeholders)
- Any few-shot examples included in the prompt
```

#### Variables / Inputs

| Variable | Type | Description | Example Value | Required |
|----------|------|-------------|---------------|----------|
| `{{user_input}}` | string | [Description] | [Example] | Yes |
| `{{context}}` | string | [Description] | [Example] | No |
| `{{language}}` | enum | [Options] | `en` | Yes |
| | | | | |

#### Model Configuration

| Parameter | Value | Notes |
|-----------|-------|-------|
| Model | [e.g., claude-3-5-sonnet] | |
| Temperature | [e.g., 0.3] | |
| Max tokens | [e.g., 1024] | |
| Top-p | [e.g., 1.0] | |
| Stop sequences | [e.g., none] | |
| System prompt | [Included above / Separate] | |

#### Performance Baseline

| Metric | Value | Measured On | Eval Dataset |
|--------|-------|------------|-------------|
| Primary quality metric | [e.g., 92% accuracy] | [DATE] | [Dataset name/link] |
| Secondary quality metric | [e.g., 4.2/5 human rating] | [DATE] | [Dataset name/link] |
| Average latency | [e.g., 1.2s p50, 3.4s p99] | [DATE] | [N requests] |
| Average input tokens | [e.g., 850] | [DATE] | |
| Average output tokens | [e.g., 320] | [DATE] | |
| Cost per request | [e.g., $0.0045] | [DATE] | |
| Error/refusal rate | [e.g., 0.3%] | [DATE] | |

#### Dependencies

| Dependency | Description |
|------------|-------------|
| Upstream data | [What data feeds into this prompt — RAG sources, user profile, etc.] |
| Downstream consumers | [What uses this prompt's output — UI, another model, API response] |
| Other prompts | [Does this prompt chain with other prompts?] |
| Feature flags | [Is this prompt behind a feature flag?] |

---

## Version History

Track every change to each prompt. One table per prompt.

### [PROMPT ID] Version History

| Version | Date | Author | Change Summary | Eval Result | Deployed To | Notes |
|---------|------|--------|---------------|-------------|-------------|-------|
| v2.3 | [DATE] | [Name] | [e.g., Added edge case handling for empty input] | [e.g., +2% accuracy] | Production | Current |
| v2.2 | [DATE] | [Name] | [e.g., Reduced token count by 15%] | [e.g., No quality change, -15% cost] | Archived | Cost optimization |
| v2.1 | [DATE] | [Name] | [e.g., Added few-shot examples for category X] | [e.g., +5% on category X] | Archived | |
| v2.0 | [DATE] | [Name] | [e.g., Major rewrite for new model (GPT-4o)] | [e.g., +8% overall] | Archived | Model migration |
| v1.0 | [DATE] | [Name] | [Initial version] | [Baseline] | Archived | |

### Version Naming Convention

Use semantic versioning adapted for prompts:

| Change Type | Version Bump | Examples |
|-------------|-------------|---------|
| **Major** (v1→v2) | New model, complete rewrite, breaking output format change | Migrated from GPT-3.5 to GPT-4o; restructured output JSON |
| **Minor** (v2.1→v2.2) | New capability, additional examples, significant quality improvement | Added few-shot examples; new output field |
| **Patch** (v2.2.0→v2.2.1) | Typo fix, minor wording adjustment, no measurable quality change | Fixed grammar in instruction; clarified ambiguous wording |

---

## Environment Promotion Workflow

### Environments

| Environment | Purpose | Approval Required | Eval Gate |
|-------------|---------|-------------------|-----------|
| **Development** | Author writes and tests prompt | None | Manual spot-check |
| **Staging** | Automated eval suite runs | Prompt owner | Pass all regression tests |
| **Canary** | Small % of production traffic | Prompt owner + PM | No quality regression in canary metrics |
| **Production** | All traffic | PM + Eng lead | Canary metrics stable for [X days] |

### Promotion Checklist

Before promoting a prompt to the next environment:

- [ ] Prompt text reviewed by [REVIEWER]
- [ ] Eval suite run against new version
- [ ] No regression on primary quality metric (>= baseline)
- [ ] No regression on secondary metrics
- [ ] Cost impact assessed (token count change)
- [ ] Latency impact assessed
- [ ] Edge cases tested (empty input, long input, adversarial input, multilingual)
- [ ] Output format validated (downstream consumers won't break)
- [ ] Rollback plan: previous version tagged and deployable
- [ ] Change logged in version history

---

## Eval Integration

### Eval Schedule

| Prompt ID | Eval Type | Frequency | Dataset | Owner |
|-----------|-----------|-----------|---------|-------|
| PRM-001 | Automated metrics (BLEU, exact match) | On every change | [Dataset] | [Name] |
| PRM-001 | LLM-as-judge | Weekly | [Dataset] | [Name] |
| PRM-001 | Human eval | Monthly | [Sample] | [Name] |
| PRM-002 | Automated metrics | On every change | [Dataset] | [Name] |
| | | | | |

### Eval Results Log

| Date | Prompt ID | Version | Eval Type | Score | vs. Baseline | Decision |
|------|-----------|---------|-----------|-------|-------------|----------|
| [DATE] | PRM-001 | v2.3 | Auto | 94.2% | +2.1% | Promote to staging |
| [DATE] | PRM-001 | v2.3 | LLM-judge | 4.3/5 | +0.1 | Promote to canary |
| [DATE] | PRM-001 | v2.3 | Canary | 93.8% | -0.4% (within tolerance) | Promote to prod |

---

## Ownership & Governance

### RACI Matrix

| Activity | PM | ML Engineer | Prompt Author | QA/Eval | Eng Lead |
|----------|-----|------------|--------------|---------|----------|
| Draft new prompt | C | C | **R** | I | I |
| Run eval suite | I | C | A | **R** | I |
| Approve for staging | **R** | C | A | C | I |
| Approve for production | **R** | C | I | C | **A** |
| Monitor in production | C | **R** | I | C | I |
| Incident response | A | **R** | C | C | A |

**R** = Responsible, **A** = Accountable, **C** = Consulted, **I** = Informed

### Review Cadence

| Review | Frequency | Participants | Purpose |
|--------|-----------|-------------|---------|
| Prompt quality review | Weekly | PM, Prompt authors | Review eval results, plan improvements |
| Full prompt audit | Quarterly | PM, Eng, QA | Review all active prompts, archive unused, update baselines |
| Cost review | Monthly | PM, Finance | Token usage trends, cost optimization opportunities |

---

## Incident Response

### When a Prompt Causes an Issue

| Severity | Criteria | Response | SLA |
|----------|----------|----------|-----|
| **P1** | Prompt producing harmful/incorrect output at scale | Immediate rollback to previous version | < 15 min |
| **P2** | Quality regression detected in monitoring | Investigate, rollback if confirmed | < 2 hours |
| **P3** | Edge case producing poor output | Log, fix in next version | < 1 week |
| **P4** | Optimization opportunity identified | Add to backlog | Next sprint |

### Rollback Procedure

1. Identify the problematic prompt version
2. Deploy the previous known-good version (tagged in version history)
3. Notify affected teams
4. Root cause analysis
5. Fix and re-evaluate before re-promotion

---

## Tips

- **Treat prompts like code** — Version them, review them, test them, deploy them through environments
- **One owner per prompt** — Shared ownership means no ownership
- **Eval before every promotion** — Never push a prompt to production without running the eval suite
- **Log everything** — When debugging a quality issue 3 months from now, you'll want the version history
- **Watch for model updates** — When the underlying model changes, all prompts need re-evaluation
- **Budget for prompt maintenance** — Prompts are not write-once; plan for ongoing iteration

