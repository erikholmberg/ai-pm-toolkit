# 🚀 AI Product Manager Toolkit

A comprehensive collection of prompts, templates, tools, and frameworks for Product Managers working with AI/ML products.

## 📚 What's Inside

| Section | Description |
|---------|-------------|
| [**prompts/**](./prompts/) | AI-assisted prompts for core PM tasks, AI/ML work, and developer communities |
| [**templates/**](./templates/) | PRD, postmortem, OKRs, RICE, technical specs, prioritization, prompt library management |
| [**scripts/**](./scripts/) | 80+ Python utilities by category: experiments, cost/ROI, delivery & velocity, adoption & health, incidents/SLO, feedback & support, risk & governance, launch, evals, strategy. See [scripts/README.md](./scripts/README.md) for the full index and sample CSVs. |
| [**frameworks/**](./frameworks/) | Prioritization, ML product lifecycle, build vs. buy, AI feature deprecation, SPACE (team health) |
| [**mcps/**](./mcps/) | MCP servers for Jira, Confluence, GitHub, Slack, Notion, Braintrust, LangSmith, product analytics, and Calendar/meetings ([mcps/README.md](./mcps/README.md)) |
| [**agents/**](./agents/) | System prompts, rules, and patterns for AI agents |
| [**evals/**](./evals/) | Evaluation frameworks, scripts, and metrics for AI products |
| [**learning/**](./learning/) | AI/ML fundamentals, [AWS Bedrock for PMs](./learning/aws-bedrock-for-pms.md), glossary, resources |
| [**strategy/**](./strategy/) | AI product strategy, pricing, go-to-market (see [strategy/README.md](./strategy/README.md)) |
| [**governance/**](./governance/) | Responsible AI, ethics, bias detection, risk assessment |
| [**communication/**](./communication/) | Stakeholder management and executive communication |
| [**launch/**](./launch/) | GTM playbooks for AI features |
| [**incidents/**](./incidents/) | Incident response and rollback strategies |
| [**career/**](./career/) | AI PM skills roadmap and interview prep |
| [**workflows/**](./workflows/) | Daily productivity and tool recommendations |

## 🧭 Finding things

- **By goal (recommended)** → [docs/tool-picker.md](./docs/tool-picker.md): what to open for planning, delivery, experiments, AI/ML work, and cost.
- **Scripts** → [scripts/README.md](./scripts/README.md): categorized index, one-line descriptions, and which sample CSV to use with each script.
- **Prompts** → [prompts/README.md](./prompts/README.md): index by category; files are `prompts/*/*.prompt.md`.
- **Templates** → [templates/](./templates/): PRD, OKR, RICE, technical spec, DX assessment, etc.
- **MCPs** → [mcps/README.md](./mcps/README.md): Jira, Confluence, GitHub, Slack, Notion, Braintrust, LangSmith, Product Analytics. **Task-based routing** → [docs/tool-picker.md](./docs/tool-picker.md).
- **Evals** → [evals/scripts/README.md](./evals/scripts/README.md): eval harness, regression runner, cost calculator.

## 🎯 Quick Start

### Using Prompts
All prompt files end in `.prompt.md`. Copy the prompt content and use it with your preferred AI assistant (Claude, ChatGPT, Copilot, etc.).

```bash
# Example: Generate a PRD
cat prompts/core-pm/prd-generator.prompt.md
```

### Using MCP Servers
MCP servers require Node.js 18+. See [mcps/README.md](./mcps/README.md) for setup instructions.

```bash
cd mcps/servers/jira-pm-assistant
npm install
npm run build
```

### Using Scripts
Python scripts require Python 3.10+. Sample data lives in **`scripts/samples/`**; see [scripts/README.md](scripts/README.md) for the full index and which sample file goes with each script.

```bash
pip install -r scripts/requirements.txt
python scripts/ab-test-calculator.py
python scripts/experiment-duration-calculator.py --baseline 0.05 --mde 0.10 --daily-visitors 5000
python scripts/ai-unit-economics-calculator.py --cost-per-request 0.002 --requests-per-month 1e6 --revenue-per-user 5 --mau 200000
python scripts/bedrock-cost-calculator.py --input-tokens 1000 --output-tokens 500 --model claude
python scripts/multi-model-cost-comparator.py --input-tokens 1000 --output-tokens 500
python scripts/model-selection-scorecard.py -s scripts/samples/sample-model-selection-scores.csv -w scripts/samples/sample-model-selection-weights.csv
python scripts/meeting-load-optimizer.py --csv scripts/samples/sample-meetings.csv
python scripts/feature-rollout-calculator.py --daily-volume 100000
python scripts/ai-initiative-roi-calculator.py --dev-cost 50000 --monthly-ai-cost 2000 --monthly-benefit 10000
python scripts/confidence-interval-calculator.py --n 500 --proportion 0.32
python scripts/nps-csat-summary.py nps --promoters 40 --passives 30 --detractors 30
python scripts/survey-sample-size.py --margin 0.05 --confidence 0.95
python scripts/latency-slo-calculator.py --availability 99.9 --requests-per-month 10e6
python scripts/churn-risk-calculator.py --cohort "New Users" --usage-drop 40 --adoption 25 --tickets 12
python scripts/prompt-cost-optimizer.py --file prompt.txt --model gpt-4o --requests-per-month 500000
python scripts/data-drift-detector.py --baseline baseline.csv --current current.csv
python scripts/adoption-funnel-analyzer.py --steps "Visit:10000" "Signup:4000" "Activate:2500" "Repeat:800"
python scripts/sla-uptime-calculator.py --sla 99.9 --incidents 45 120 15 --forecast-days 90
python scripts/velocity-trend-analyzer.py --sprints 38 42 35 45 40 48 --window 3 --target 45
python scripts/capacity-planning-calculator.py --team 6 --sprint-days 10 --pto 2 --meetings 0.2 --points-per-day 4
python scripts/cycle-lead-time-analyzer.py --csv tickets.csv --group-by type
python scripts/sprint-burndown-checker.py --csv burndown.csv --chart
python scripts/sprint-mix-report.py --csv sprint.csv --group-by type
python scripts/commitment-predictability-index.py --csv velocity.csv
python scripts/status-duration-analyzer.py --csv transitions.csv --chart
python scripts/experiment-result-interpreter.py --baseline 5.0 --variant 5.6 --n 8000
python scripts/backlog-aging-report.py --csv backlog.csv --oldest 15
python scripts/sprint-goal-checker.py --goals goals.csv --completed done.csv
python scripts/eval-label-economics.py --margin 0.05 --confidence 0.95 --proportion 0.5 --cost-per-label 2.50
python scripts/eval-score-trend.py --csv eval-runs.csv --chart
python scripts/incident-rate-trend.py --csv incidents.csv --chart
python scripts/risk-register-summary.py --csv risks.csv --top 5
python scripts/release-impact-summary.py --csv shipped.csv --version "v2.1.0" --bullets
python scripts/prompt-version-diff.py --old prompt_v1.txt --new prompt_v2.txt
python scripts/hallucination-safety-trend.py --csv evals.csv --metric-type hallucination --chart
python scripts/roadmap-timeline-summary.py --csv roadmap.csv --overlaps --by-quarter
python scripts/launch-readiness-score.py --csv checklist.csv --go-threshold 95
python scripts/feedback-theme-counter.py --csv feedback.csv --themes "pricing,reliability,ux,support"
python scripts/support-escalation-trend.py --csv tickets.csv --chart --group-by severity
python scripts/audit-checklist-summary.py --csv controls.csv --group-by domain --open
python scripts/budget-burn-summary.py --csv budget.csv --group-by category
python scripts/win-loss-summary.py --csv deals.csv --top 5 --group-by segment
python scripts/inference-latency-trend.py --csv latency-runs.csv --metric p99 --chart
python scripts/feature-adoption-trend.py --csv adoption.csv --chart --group-by segment
python scripts/stakeholder-signoff-tracker.py --csv signoffs.csv --pending --group-by deliverable
python scripts/dependency-blocked-summary.py --csv deps.csv --blocking
python scripts/beta-conversion-report.py --csv beta.csv --chart
python scripts/customer-health-score-trend.py --csv health.csv --at-risk-below 50 --chart --group-by segment
python scripts/release-cadence-report.py --csv releases.csv --period month --chart --group-by product
```

## 🗂️ Directory Structure

```
pm-toolkit/
├── README.md
├── .gitignore
├── prompts/
│   ├── core-pm/              # PRDs, user stories, stakeholder updates, pricing page, API changelog
│   ├── ai-ml/                # ML system design, model cards, MLOps, migration playbooks
│   └── developer-community/  # AI accelerator resources
├── templates/                # RICE, OKRs, technical specs, prompt library management
├── scripts/                  # See scripts/README.md for categorized index and sample CSVs
├── frameworks/               # Prioritization, ML lifecycle, build vs. buy, deprecation playbook, SPACE
├── mcps/
│   ├── guides/               # Setup and use case documentation
│   ├── TOOLS.md              # Server → MCP tool name reference
│   └── servers/              # Jira, Confluence, GitHub, Slack, Notion, Calendar, etc.
├── agents/
│   ├── system-prompts/       # Ready-to-use agent personas
│   ├── rules/                # Cursor rules, Claude instructions
│   ├── evaluation/           # Agent evaluation frameworks
│   └── patterns/             # Agent design patterns
├── evals/
│   ├── frameworks/           # LLM evaluation methodology
│   ├── scripts/              # Eval harness, eval summary report generator
│   ├── templates/            # Eval planning docs
│   └── metrics/              # AI product metrics guide
├── learning/                 # AI/ML fundamentals, glossary, resources
├── strategy/                 # AI product strategy frameworks
├── governance/               # Responsible AI checklist
├── communication/            # Executive communication prompts
├── launch/                   # AI feature launch checklist
├── incidents/                # Incident response playbook
├── career/                   # AI PM skills roadmap
└── workflows/                # Daily AI PM workflow
```

## ☁️ Building on AWS Bedrock

If you use **Amazon Bedrock**, see:

- [AWS Bedrock for PMs](./learning/aws-bedrock-for-pms.md) – concepts, model families, data/compliance
- [scripts/bedrock-cost-calculator.py](./scripts/bedrock-cost-calculator.py) – estimate inference cost
- [prompts/ai-ml/bedrock-model-selection.prompt.md](./prompts/ai-ml/bedrock-model-selection.prompt.md) – choose a model
- [evals/frameworks/bedrock-eval-guide.md](./evals/frameworks/bedrock-eval-guide.md) – run evals with Bedrock

---

## 🤝 Contributing

This toolkit is open for contributions. See [CONTRIBUTING.md](CONTRIBUTING.md) for where to add scripts, prompts, and templates so the repo stays easy to navigate. Then open a PR.

## 📄 License

MIT License - Use freely, and attribution appreciated.

---

Built for Product Managers navigating the AI era. 🧠

