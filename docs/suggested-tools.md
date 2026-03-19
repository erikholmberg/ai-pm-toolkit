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

---

## MCP Servers

| Server | Purpose | Why add |
|--------|--------|--------|
| **Linear** | Issues, projects, cycles, roadmap. | Many teams use Linear instead of (or with) Jira; same PM workflows (sprint status, release notes, ticket creation). |
| **Notion** | Search and create pages, databases, meeting notes, PRDs. | ✅ Implemented: [notion-pm-tools](../mcps/servers/notion-pm-tools/) |
| **Product analytics (read-only)** | Query Amplitude, Mixpanel, or Pendo for key metrics (DAU, funnels, feature usage). | Lets the AI summarize “how is feature X performing?” without leaving the assistant. |
| **Calendar / meetings** | List upcoming meetings, free/busy, or create calendar events. | Supports standup prep, stakeholder updates, and “what’s on my plate today?” |
| **Customer support** | Read-only: Intercom, Zendesk, or Help Scout (tickets, themes, volume). | Complements Slack and customer prompts; good for feedback synthesis and prioritization. |
| **Figma (read-only)** | List files, get frame/screen names and links (no edit). | Helps link specs to design; useful for PRDs and eng handoff. |

---

## Quick wins

- **Scripts:** Multi-model cost comparator and confidence interval calculator (small, high reuse).
- **MCP:** Linear (if your users are on it). Notion is implemented: [notion-pm-tools](../mcps/servers/notion-pm-tools/).

---

## Contributing

When adding a tool:

- **Scripts:** Follow patterns in `scripts/` (argparse, docstring, `requirements.txt`).
- **MCPs:** Follow structure in `mcps/servers/`, document env vars in the server `README.md`, and add the server to `mcps/README.md`.

If you implement one of these, consider adding a short note to this file (e.g. “Implemented: Multi-model cost comparator in `scripts/`”).
