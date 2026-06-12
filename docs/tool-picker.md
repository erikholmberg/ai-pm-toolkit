# Tool picker (by goal)

Use this page when you know **what you want to do**, not which file or server to open. For script names and sample CSVs, see [scripts/README.md](../scripts/README.md). For MCP setup, see [mcps/README.md](../mcps/README.md) and [mcps/guides/mcp-setup-guide.md](../mcps/guides/mcp-setup-guide.md).

---

## Planning and communication

| Intent | Start here |
|--------|------------|
| Write or refine a PRD | [templates/prd-template.md](../templates/prd-template.md), [prompts/core-pm/prd-generator.prompt.md](../prompts/core-pm/prd-generator.prompt.md) |
| Roadmap or quarterly planning | [prompts/core-pm/roadmap-builder.prompt.md](../prompts/core-pm/roadmap-builder.prompt.md), [frameworks/](../frameworks/) |
| Stakeholder or exec update | [prompts/core-pm/stakeholder-update.prompt.md](../prompts/core-pm/stakeholder-update.prompt.md) |
| Meeting notes or synthesis | [prompts/core-pm/meeting-notes-synthesizer.prompt.md](../prompts/core-pm/meeting-notes-synthesizer.prompt.md) |
| Competitive analysis | [prompts/core-pm/competitive-analysis.prompt.md](../prompts/core-pm/competitive-analysis.prompt.md) |

---

## Delivery, backlog, and engineering alignment

| Intent | Start here |
|--------|------------|
| Jira tickets, epics, sprints, JQL | [prompts/core-pm/](../prompts/README.md) (Jira prompts), MCP [jira-pm-assistant](../mcps/servers/jira-pm-assistant/) |
| GitHub issues, PRs, release notes | MCP [github-pm-tools](../mcps/servers/github-pm-tools/) |
| Confluence docs, PRDs in wiki | MCP [confluence-docs](../mcps/servers/confluence-docs/) |
| Notion pages, databases, notes | MCP [notion-pm-tools](../mcps/servers/notion-pm-tools/) |
| Calendar meetings, free/busy, agendas | MCP [calendar-meetings-pm-tools](../mcps/servers/calendar-meetings-pm-tools/) |
| Slack context, threads, summaries | MCP [slack-pm-assistant](../mcps/servers/slack-pm-assistant/) |
| Velocity, burndown, backlog health, DORA | [scripts/README.md](../scripts/README.md) (Delivery, velocity & backlog) |

---

## Experiments, metrics, and product health

| Intent | Start here |
|--------|------------|
| A/B sample size, duration, interpretation | `scripts/ab-test-calculator.py`, `experiment-duration-calculator.py`, `experiment-result-interpreter.py` |
| Feature adoption, funnels, retention | [scripts/README.md](../scripts/README.md) (Adoption, health & retention) |
| Incidents, SLOs, error budget | [scripts/README.md](../scripts/README.md) (Incidents, SLO & reliability) |
| Product analytics (events, funnels, cohorts) | MCP [product-analytics-pm-tools](../mcps/servers/product-analytics-pm-tools/) |
| LLM eval runs and experiments | MCP [braintrust-pm-tools](../mcps/servers/braintrust-pm-tools/), [langsmith-pm-tools](../mcps/servers/langsmith-pm-tools/); [evals/](../evals/) |

---

## AI/ML-specific PM work

| Intent | Start here |
|--------|------------|
| Model selection (e.g. Bedrock) | [prompts/ai-ml/bedrock-model-selection.prompt.md](../prompts/ai-ml/bedrock-model-selection.prompt.md), [learning/aws-bedrock-for-pms.md](../learning/aws-bedrock-for-pms.md) |
| Model cards, system design, MLOps | [prompts/ai-ml/](../prompts/README.md), [templates/technical-spec-ml.md](../templates/technical-spec-ml.md) |
| Responsible AI / ethics checks | [prompts/ai-ml/ai-ethics-evaluator.prompt.md](../prompts/ai-ml/ai-ethics-evaluator.prompt.md), [governance/](../governance/) |

---

## Cost, pricing, and strategy

| Intent | Start here |
|--------|------------|
| Inference or multi-model cost | `scripts/bedrock-cost-calculator.py`, `multi-model-cost-comparator.py`, `prompt-cost-optimizer.py` |
| AI initiative ROI, unit economics | `scripts/ai-initiative-roi-calculator.py`, `ai-unit-economics-calculator.py` |
| Pricing and GTM | [strategy/](../strategy/README.md), `scripts/pricing-model-simulator.py` |

---

## Reference indexes

| What | Where |
|------|--------|
| All Python scripts by category | [scripts/README.md](../scripts/README.md) |
| All prompts by folder | [prompts/README.md](../prompts/README.md) |
| MCP servers and env setup | [mcps/README.md](../mcps/README.md) |
| MCP tool names (quick lookup) | [mcps/TOOLS.md](../mcps/TOOLS.md) |
| Example MCP conversations | [mcps/guides/mcp-use-cases-for-pms.md](../mcps/guides/mcp-use-cases-for-pms.md) |
