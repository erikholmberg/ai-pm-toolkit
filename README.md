# 🚀 AI Product Manager Toolkit

A comprehensive collection of prompts, templates, tools, and frameworks for Product Managers working with AI / ML products.

## 📚 What's Inside

| Section | Description |
|---------|-------------|
| [**prompts/**](./prompts/) | AI-assisted prompts for core PM tasks, AI/ML work, and developer communities |
| [**templates/**](./templates/) | Reusable documents for specs, OKRs, prioritization frameworks |
| [**scripts/**](./scripts/) | Python utilities for analysis, A/B testing, and automation |
| [**frameworks/**](./frameworks/) | Mental models for prioritization and ML product lifecycle |
| [**mcps/**](./mcps/) | Model Context Protocol servers for Jira, Confluence, and GitHub |
| [**agents/**](./agents/) | System prompts, rules, and patterns for AI agents |
| [**evals/**](./evals/) | Evaluation frameworks, scripts, and metrics for AI products |
| [**learning/**](./learning/) | AI/ML fundamentals, glossary, and curated resources |
| [**strategy/**](./strategy/) | AI product strategy, build vs buy, pricing models |
| [**governance/**](./governance/) | Responsible AI, ethics, bias detection, risk assessment |
| [**communication/**](./communication/) | Stakeholder management and executive communication |
| [**launch/**](./launch/) | GTM playbooks for AI features |
| [**incidents/**](./incidents/) | Incident response and rollback strategies |
| [**career/**](./career/) | AI PM skills roadmap and interview prep |
| [**workflows/**](./workflows/) | Daily productivity and tool recommendations |

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
Python scripts require Python 3.10+. 

```bash
pip install -r scripts/requirements.txt
python scripts/ab-test-calculator.py
```

## 🗂️ Directory Structure

```
pm-toolkit/
├── README.md
├── .gitignore
├── prompts/
│   ├── core-pm/              # PRDs, user stories, stakeholder updates
│   ├── ai-ml/                # ML system design, model cards, MLOps
│   └── developer-community/  # AI accelerator resources
├── templates/                # RICE, OKRs, technical specs
├── scripts/                  # Python analysis tools
├── frameworks/               # Prioritization, ML lifecycle
├── mcps/
│   ├── guides/               # Setup and use case documentation
│   └── servers/              # Jira, Confluence, GitHub MCP servers
├── agents/
│   ├── system-prompts/       # Ready-to-use agent personas
│   ├── rules/                # Cursor rules, Claude instructions
│   ├── evaluation/           # Agent evaluation frameworks
│   └── patterns/             # Agent design patterns
├── evals/
│   ├── frameworks/           # LLM evaluation methodology
│   ├── scripts/              # Evaluation harness code
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

## 🤝 Contributing

This toolkit is open for contributions. If you have prompts, templates, or tools that help you as an AI PM, please submit a PR.

## 📄 License

MIT License - Use freely, and attribution appreciated.

---

Built for Product Managers navigating the AI era. 🧠

