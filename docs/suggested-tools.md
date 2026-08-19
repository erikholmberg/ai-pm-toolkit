# Suggested Tools to Add

Ideas for new **scripts** and **MCP servers** that would complement the existing AI PM Toolkit. Prioritized by impact and fit with current content.

---

## Scripts (Python)

| Tool | Purpose | Why add |
|------|--------|--------|
| **Multi-model cost comparator** | Compare inference cost across Bedrock, OpenAI, and Anthropic (input/output tokens, multiple models). | ✅ Implemented: `scripts/multi-model-cost-comparator.py` |
| **Feature rollout calculator** | Compute sample sizes and duration for phased rollouts (e.g. 1% → 5% → 25% → 100%) with risk/SLO inputs. | ✅ Implemented: `scripts/feature-rollout-calculator.py` |
| **AI initiative ROI / payback** | Estimate payback for an AI project (dev cost, inference cost, revenue or cost savings). | ✅ Implemented: `scripts/ai-initiative-roi-calculator.py` |
| **Confidence interval calculator** | Given sample size and rate (or mean), output CI (e.g. Wilson score for proportions). | ✅ Implemented: `scripts/confidence-interval-calculator.py` |
| **NPS / CSAT summary** | Compute NPS from promoter/detractor counts; CSAT average and distribution from scores. | ✅ Implemented: `scripts/nps-csat-summary.py` |
| **Survey sample size** | Sample size for target margin of error and confidence level (proportions). | ✅ Implemented: `scripts/survey-sample-size.py` |
| **Model / system card builder** | Generate Markdown/YAML model or LLM system cards from CLI or JSON. | ✅ Implemented: `scripts/model-system-card-builder.py` |

---

## MCP Servers

**Already in the repo:** Jira, Confluence, GitHub, Slack, Notion, Braintrust, LangSmith, and read-only product analytics — see [mcps/README.md](../mcps/README.md) and [mcps/TOOLS.md](../mcps/TOOLS.md) for the full tool list.

| Server | Purpose | Status |
|--------|--------|--------|
| **Linear** | Issues, projects, cycles, roadmap. | Suggested — many teams use Linear instead of (or with) Jira; same PM workflows (sprint status, release notes, ticket creation). |
| **Calendar / meetings** | List upcoming meetings, free/busy, or create calendar events. | ✅ Implemented: `mcps/servers/calendar-meetings-pm-tools/` |
| **Customer support** | Read-only: Intercom, Zendesk, or Help Scout (tickets, themes, volume). | Suggested — complements Slack and customer prompts; feedback synthesis and prioritization. |
| **Figma (read-only)** | List files, get frame/screen names and links (no edit). | Suggested — link specs to design; PRDs and eng handoff. |

---

## Connector layer

The manual-input pattern is the toolkit's real ceiling, not the script count. 115 tools that each need a hand-built CSV get used once; the same tools reading from a real system get used weekly.

**Step 1 implemented:** [connectors/](../connectors/) — canonical dataset contracts, the `fetch.py` CLI, the shared `base.py`, and the no-auth `csvfile` connector that normalizes a Jira/Linear export into canonical shape. Verified end to end: `connectors/self-test.py` runs all 7 `issues` consumers against connector output.

| Step | Connector | Status |
|------|-----------|--------|
| 1 | Contracts + base + CLI + `csvfile` | ✅ Implemented — `issues` contract feeds 7 scripts |
| 2 | **Jira → `issues`** | Next — highest fan-out; reuses `JIRA_*` env vars from [jira-pm-assistant](../mcps/servers/jira-pm-assistant/) |
| 3 | **AI gateway → `llm_usage`** | Highest new value — turns ~8 cost scripts from estimators into actuals |
| 4 | **Linear → `issues`** | The contract test: if this forces a change to `issues`, the contract was wrong |

Contracts still to define: `llm_usage`, `incidents`, `eval_cases`, `events`. Derive each one's column names from the consuming scripts' existing `_col()` alias lists, as [connectors/datasets.py](../connectors/datasets.py) does for `issues` — designing names fresh produces a contract you then have to edit scripts to satisfy.

---

## Quick wins

- **Scripts:** Multi-model cost comparator and confidence interval calculator (small, high reuse).
- **MCP:** Linear (if your team uses it). Notion, Calendar, and product analytics are implemented: [notion-pm-tools](../mcps/servers/notion-pm-tools/), [calendar-meetings-pm-tools](../mcps/servers/calendar-meetings-pm-tools/), [product-analytics-pm-tools](../mcps/servers/product-analytics-pm-tools/).

---

## Contributing

When adding a tool:

- **Scripts:** Follow patterns in `scripts/` (argparse, docstring, `requirements.txt`).
- **MCPs:** Follow structure in `mcps/servers/`, document env vars in the server `README.md`, and add the server to `mcps/README.md`.

If you implement one of these, consider adding a short note to this file (e.g. “Implemented: Multi-model cost comparator in `scripts/`”).
