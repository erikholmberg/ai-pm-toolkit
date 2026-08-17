# Scripts

Python 3.10+ utilities for PM workflows. Install once, then run any script:

```bash
pip install -r scripts/requirements.txt
python scripts/<script-name>.py --help
```

Sample CSVs and example files live in **`scripts/samples/`** (e.g. `samples/sample-feature-adoption.csv`). Use your own data or these for testing.

Goal-based routing (scripts + prompts + MCP): [docs/tool-picker.md](../docs/tool-picker.md).

---

## Shared modules

Three modules underpin the rest. They are imported by the scripts, not run directly (though each has a CLI for inspection).

| Module | What it does | Why it exists |
|--------|--------------|---------------|
| [model_pricing.py](model_pricing.py) | Single source of truth for per-token LLM pricing, with a `last_verified` date and `source` per model. | Four scripts used to carry overlapping price tables that **disagreed with each other**. Stale or never-verified prices now warn loudly instead of producing a confident wrong number. |
| [csv_columns.py](csv_columns.py) | `DictReader` that matches headers case- and punctuation-insensitively, so `Duration (Minutes)` answers to `duration_minutes`. | A real export whose headers didn't match exactly used to hit the `.get(col, 0)` default path and return **0 silently**. |
| [toolkit_io.py](toolkit_io.py) | Shared result envelope for every `--output` JSON: tool name, timestamp, schema version, and the payload. `load()` reads enveloped or legacy bare output. | 80+ scripts each emitted a bespoke blob and none could read another's, so "chaining" meant a human retyping numbers. |

```bash
# What pricing is stale or unverified? (exits 1 if anything needs attention)
python scripts/model_pricing.py --check

# Price a request, including cache and batch rates
python scripts/model_pricing.py --cost claude-opus-5 --input-tokens 1e6 --output-tokens 5e5

# Where did this number come from?
python scripts/toolkit_io.py results.json
```

**Pricing is verified, not guessed.** Anthropic model prices were checked against the
published rates; Bedrock, OpenAI, and Google entries are carried over from the original
tables and are marked `UNVERIFIED` until someone checks them against the vendor's page.
Any comparison that includes an unverified model says so in its output.

### Smoke test

[smoke-test.py](smoke-test.py) runs every script against the sample data listed in this
file's per-script tables and checks it actually produces output — not just that `--help`
exits 0. `--help` passing and the script working are different claims; three scripts
(`eval-score-trend`, `hallucination-safety-trend`, `inference-latency-trend`) had a working
`--help` and a `--output` flag that raised `TypeError` on every real invocation until this
caught it.

```bash
python scripts/smoke-test.py              # summary
python scripts/smoke-test.py --verbose    # every script's result, not just failures
```

Scripts with no sample data listed in this README are only `--help`-checked (reported as
`SKIP`, not `PASS`) — there's no generic way to guess a required scalar flag like
`--baseline-rate`. Add a sample-data row for a script here to bring it under real coverage.

---

## Common questions

| Question | Script |
|----------|--------|
| How big should my A/B test be (sample size, power)? | [ab-test-calculator.py](ab-test-calculator.py) |
| How long do I need to run the experiment? | [experiment-duration-calculator.py](experiment-duration-calculator.py), [experiment-result-interpreter.py](experiment-result-interpreter.py) |
| Is this lift statistically meaningful? | [experiment-result-interpreter.py](experiment-result-interpreter.py), [confidence-interval-calculator.py](confidence-interval-calculator.py) |
| What’s the ROI or payback of an AI initiative? | [ai-initiative-roi-calculator.py](ai-initiative-roi-calculator.py), [ai-unit-economics-calculator.py](ai-unit-economics-calculator.py) |
| What does this LLM inference cost (Bedrock / compare vendors)? | [bedrock-cost-calculator.py](bedrock-cost-calculator.py), [multi-model-cost-comparator.py](multi-model-cost-comparator.py) |
| Are we burning error budget too fast? | [error-budget-burn-rate.py](error-budget-burn-rate.py), [sla-uptime-calculator.py](sla-uptime-calculator.py) |
| How healthy is the sprint / backlog? | [sprint-burndown-checker.py](sprint-burndown-checker.py), [backlog-health-report.py](backlog-health-report.py), [backlog-aging-report.py](backlog-aging-report.py) |
| How do we size a phased rollout? | [feature-rollout-calculator.py](feature-rollout-calculator.py), [release-gate-scorer.py](release-gate-scorer.py) |
| What does an agentic (multi-step tool-calling) workflow cost vs a single call? | [agentic-cost-simulator.py](agentic-cost-simulator.py), [reasoning-token-budget-calculator.py](reasoning-token-budget-calculator.py) |
| Is our AI agent actually succeeding at tasks, and which tools are flaky? | [agent-task-success-tracker.py](agent-task-success-tracker.py), [tool-use-reliability-scorer.py](tool-use-reliability-scorer.py) |
| Can we trust an LLM-as-judge, and is our guardrail catching real violations? | [llm-judge-calibration-checker.py](llm-judge-calibration-checker.py), [guardrail-effectiveness-analyzer.py](guardrail-effectiveness-analyzer.py) |
| Are we red-team-tested enough to launch, and is this prompt injection-risky? | [red-team-coverage-tracker.py](red-team-coverage-tracker.py), [prompt-injection-risk-scanner.py](prompt-injection-risk-scanner.py) |
| Is our model's outcome disparate across demographic groups? | [bias-fairness-scorecard.py](bias-fairness-scorecard.py) |
| Which models in our portfolio are about to be deprecated? | [model-deprecation-watch.py](model-deprecation-watch.py), [model-migration-estimator.py](model-migration-estimator.py) |
| What is training/fine-tuning actually costing us, and how much is wasted on failed runs? | [training-job-cost-tracker.py](training-job-cost-tracker.py) |

---

## By category

### Experiments & statistics
| Script | Description | Sample CSV |
|--------|-------------|------------|
| [ab-test-calculator.py](ab-test-calculator.py) | A/B test sample size, duration, power; proportions or means | samples/sample-ab-test-calculator.csv |
| [experiment-duration-calculator.py](experiment-duration-calculator.py) | How long to run an experiment given traffic and sample size | — |
| [experiment-result-interpreter.py](experiment-result-interpreter.py) | Interpret baseline vs variant with confidence | — |
| [experiment-lifecycle-manager.py](experiment-lifecycle-manager.py) | Decision memo with guardrail-aware ship/iterate/stop recommendation | — |
| [confidence-interval-calculator.py](confidence-interval-calculator.py) | Wilson score and mean CIs | — |
| [survey-sample-size.py](survey-sample-size.py) | Sample size for target margin and confidence | — |
| [cohort-comparison-tool.py](cohort-comparison-tool.py) | Compare cohorts (e.g. retention, conversion) | samples/sample-cohort-comparison-tool.csv |

### Cost & economics
| Script | Description | Sample CSV |
|--------|-------------|------------|
| [bedrock-cost-calculator.py](bedrock-cost-calculator.py) | Bedrock inference cost from tokens and model | — |
| [multi-model-cost-comparator.py](multi-model-cost-comparator.py) | Compare cost across Bedrock, OpenAI, Anthropic | — |
| [prompt-cost-optimizer.py](prompt-cost-optimizer.py) | Estimate and optimize prompt cost by model/volume | samples/sample-prompt-v1.txt |
| [ai-unit-economics-calculator.py](ai-unit-economics-calculator.py) | Cost per request, revenue per user, unit economics | — |
| [ai-initiative-roi-calculator.py](ai-initiative-roi-calculator.py) | Payback for AI projects (dev + inference vs benefit) | — |
| [ltv-cac-calculator.py](ltv-cac-calculator.py) | LTV, CAC, payback | samples/sample-ltv-cac-calculator.csv |
| [tam-sam-som-calculator.py](tam-sam-som-calculator.py) | TAM/SAM/SOM sizing | samples/sample-tam-sam-som-calculator.csv |
| [pricing-model-simulator.py](pricing-model-simulator.py) | Model pricing scenarios (usage-based, tiered) | — |
| [revenue-waterfall.py](revenue-waterfall.py) | Revenue waterfall breakdown | samples/sample-revenue-waterfall.csv |

### Delivery, velocity & backlog
| Script | Description | Sample CSV |
|--------|-------------|------------|
| [velocity-trend-analyzer.py](velocity-trend-analyzer.py) | Sprint velocity trend, rolling window, target | samples/sample-velocity-trend-analyzer.csv |
| [sprint-burndown-checker.py](sprint-burndown-checker.py) | Burndown vs plan, chart | samples/sample-burndown.csv |
| [sprint-mix-report.py](sprint-mix-report.py) | Mix by type/priority; balance | samples/sample-sprint-mix.csv |
| [sprint-velocity-tracker.py](sprint-velocity-tracker.py) | Track velocity over sprints | samples/sample-velocity.csv |
| [sprint-goal-checker.py](sprint-goal-checker.py) | Goals vs completed work | samples/sample-sprint-goals.csv, samples/sample-sprint-done.csv |
| [sprint-scope-checker.py](sprint-scope-checker.py) | Scope vs capacity | samples/sample-sprint-scope-checker.csv |
| [commitment-predictability-index.py](commitment-predictability-index.py) | CPI from velocity history | samples/sample-velocity.csv |
| [capacity-planning-calculator.py](capacity-planning-calculator.py) | Capacity from team size, PTO, meetings, points/day | — |
| [capacity-planner.py](capacity-planner.py) | Capacity planning with scenarios | samples/sample-capacity-planner.csv |
| [cycle-lead-time-analyzer.py](cycle-lead-time-analyzer.py) | Cycle/lead time from ticket CSV | samples/sample-cycle-lead-time-analyzer.csv |
| [throughput-wip-analyzer.py](throughput-wip-analyzer.py) | Throughput and WIP over time | samples/sample-throughput-wip-analyzer.csv |
| [backlog-aging-report.py](backlog-aging-report.py) | Age bands, oldest items | samples/sample-backlog-aging.csv |
| [backlog-health-report.py](backlog-health-report.py) | Backlog health (estimation, priority, stale) | samples/sample-backlog-health-report.csv |
| [status-duration-analyzer.py](status-duration-analyzer.py) | Time in status from transitions | samples/sample-status-transitions.csv, samples/sample-status-spans.csv |
| [release-impact-summary.py](release-impact-summary.py) | Shipped scope by version | samples/sample-release-impact.csv |
| [release-cadence-report.py](release-cadence-report.py) | Release frequency and grouping | samples/sample-release-cadence.csv |
| [release-notes-generator.py](release-notes-generator.py) | Generate release notes from data | samples/sample-release-notes-generator.csv |
| [roadmap-timeline-summary.py](roadmap-timeline-summary.py) | Roadmap view, overlaps, by quarter | samples/sample-roadmap.csv |
| [delivery-completion-forecaster.py](delivery-completion-forecaster.py) | Forecast completion dates | samples/sample-delivery-completion-forecaster.csv |
| [dora-metrics-calculator.py](dora-metrics-calculator.py) | DORA deployment, lead time, change failure | samples/sample-dora-metrics-calculator.csv |

### Adoption, health & retention
| Script | Description | Sample CSV |
|--------|-------------|------------|
| [adoption-funnel-analyzer.py](adoption-funnel-analyzer.py) | Funnel steps and conversion (e.g. Visit→Signup→Activate) | samples/sample-adoption-funnel-analyzer.csv |
| [feature-adoption-trend.py](feature-adoption-trend.py) | Adoption % or DAU/WAU over time, trend label | samples/sample-feature-adoption.csv |
| [feature-adoption-scorecard.py](feature-adoption-scorecard.py) | Adoption scorecard by segment/feature | samples/sample-feature-adoption-scorecard.csv |
| [customer-health-score-trend.py](customer-health-score-trend.py) | Health score over time, at-risk threshold | samples/sample-customer-health.csv |
| [churn-risk-calculator.py](churn-risk-calculator.py) | Churn risk from usage drop, adoption, tickets | samples/sample-churn-risk-calculator.csv |
| [retention-curve-analyzer.py](retention-curve-analyzer.py) | Retention curves and cohort comparison | samples/sample-retention-curve-analyzer.csv |
| [beta-conversion-report.py](beta-conversion-report.py) | Beta→GA conversion, trend | samples/sample-beta-conversion.csv |

### Incidents, SLO & reliability
| Script | Description | Sample CSV |
|--------|-------------|------------|
| [incident-rate-trend.py](incident-rate-trend.py) | Incident rate over time, chart | samples/sample-incidents.csv |
| [incident-postmortem.py](incident-postmortem.py) | Structure postmortem output | samples/sample-incident-postmortem.json |
| [latency-slo-calculator.py](latency-slo-calculator.py) | Latency SLO and error budget from availability/RPM | — |
| [sla-uptime-calculator.py](sla-uptime-calculator.py) | Uptime, error budget remaining, breach risk | samples/sample-sla-uptime-calculator.csv |
| [error-budget-burn-rate.py](error-budget-burn-rate.py) | Error budget burn rate | samples/sample-error-budget-burn-rate.csv |
| [alert-threshold-calculator.py](alert-threshold-calculator.py) | Alert thresholds from SLO and baseline | samples/sample-alert-threshold-calculator.csv |
| [inference-latency-trend.py](inference-latency-trend.py) | Inference latency (e.g. p99) over time | samples/sample-inference-latency.csv |

### Feedback, NPS & support
| Script | Description | Sample CSV |
|--------|-------------|------------|
| [nps-csat-summary.py](nps-csat-summary.py) | NPS from promoter/passive/detractor; CSAT summary | — |
| [feedback-theme-counter.py](feedback-theme-counter.py) | Count feedback by theme | samples/sample-feedback.csv |
| [sentiment-analysis.py](sentiment-analysis.py) | Sentiment on text (e.g. feedback) | samples/sample-sentiment-feedback.csv |
| [support-escalation-trend.py](support-escalation-trend.py) | Escalation volume/trend by severity | samples/sample-support-tickets.csv |
| [voc-synthesis.py](voc-synthesis.py) | Deduplicate multi-source feedback and rank top opportunities | samples/sample-voc-synthesis.csv |

### Risk, dependencies & governance
| Script | Description | Sample CSV |
|--------|-------------|------------|
| [risk-register-summary.py](risk-register-summary.py) | Top risks, summary by category | samples/sample-risks.csv |
| [dependency-blocked-summary.py](dependency-blocked-summary.py) | Blocked-by and blocking summary | samples/sample-dependency-blocked.csv |
| [dependency-risk-mapper.py](dependency-risk-mapper.py) | Dependency and risk mapping | samples/sample-dependency-risk-mapper.csv |
| [blocker-wait-summary.py](blocker-wait-summary.py) | Blocker and wait-time summary | samples/sample-blocker-wait-summary.csv |
| [audit-checklist-summary.py](audit-checklist-summary.py) | Audit controls, open/by domain | samples/sample-audit-controls.csv |

### Launch & rollout
| Script | Description | Sample CSV |
|--------|-------------|------------|
| [launch-readiness-score.py](launch-readiness-score.py) | Go/no-go score from checklist | samples/sample-launch-readiness.csv |
| [launch-checklist.py](launch-checklist.py) | Launch checklist workflow; `--csv` emits the format the scorer reads | — (generative; --csv writes the launch-readiness-score.py input format) |
| [release-gate-scorer.py](release-gate-scorer.py) | Weighted evidence-based release gate decision | samples/sample-release-gate-scorer.csv |
| [feature-rollout-calculator.py](feature-rollout-calculator.py) | Phased rollout sample size and duration | — |
| [feature-flag-planner.py](feature-flag-planner.py) | Feature flag stages and gates | — |

These two now compose. Generate the checklist, fill in `done` as the team works, then score the same file:

```bash
python scripts/launch-checklist.py --name "Agent Copilot" --type backend --csv gate.csv
# ...team fills in the `done` column...
python scripts/launch-readiness-score.py --csv gate.csv --per-area
```

### Evals & quality
| Script | Description | Sample CSV |
|--------|-------------|------------|
| [eval-label-economics.py](eval-label-economics.py) | Gold-set size & labeling cost for target CI width on pass rate, precision, or recall | — |
| [eval-score-trend.py](eval-score-trend.py) | Eval score over time, chart | samples/sample-eval-runs.csv |
| [hallucination-safety-trend.py](hallucination-safety-trend.py) | Hallucination/safety metric trend | samples/sample-hallucination-safety.csv |
| [data-drift-detector.py](data-drift-detector.py) | Drift between baseline and current dataset | — |
| [prompt-version-diff.py](prompt-version-diff.py) | Diff two prompt versions | samples/sample-prompt-v1.txt, sample-prompt-v2.txt |
| [groundedness-scorer.py](groundedness-scorer.py) | Groundedness scoring for outputs | samples/sample-groundedness-scorer.csv |
| [rag-quality-analyzer.py](rag-quality-analyzer.py) | RAG retrieval/answer quality | samples/sample-rag-quality.csv |

### Agentic AI & orchestration
| Script | Description | Sample CSV |
|--------|-------------|------------|
| [agent-task-success-tracker.py](agent-task-success-tracker.py) | Success/failure/escalation rates, steps-to-completion, category breakdown for an AI agent's task runs | samples/sample-agent-task-runs.csv |
| [tool-use-reliability-scorer.py](tool-use-reliability-scorer.py) | Per-tool call success/retry/timeout rate and latency from an agent's tool-call log; flags unreliable tools | samples/sample-tool-calls.csv |
| [agentic-cost-simulator.py](agentic-cost-simulator.py) | Cost & latency of a multi-step think/tool/observe agent loop vs a naive single-call baseline (the "agent tax") | — |
| [reasoning-token-budget-calculator.py](reasoning-token-budget-calculator.py) | Cost/latency at each extended-thinking effort tier (low/medium/high) for reasoning models | — |
| [context-window-utilization-analyzer.py](context-window-utilization-analyzer.py) | Turn-by-turn context usage, warning-threshold crossing, and projected turns until compaction is needed | samples/sample-context-window-session.csv |

### AI safety, red-teaming & guardrails
| Script | Description | Sample CSV |
|--------|-------------|------------|
| [llm-judge-calibration-checker.py](llm-judge-calibration-checker.py) | Agreement (kappa/correlation, bias) between an LLM-as-judge and human labels; verdict on trusting the judge | samples/sample-judge-vs-human.csv |
| [prompt-injection-risk-scanner.py](prompt-injection-risk-scanner.py) | Heuristic first-pass linter for prompt-injection risk patterns in system prompts/instructions | samples/sample-system-prompt-risky.txt |
| [guardrail-effectiveness-analyzer.py](guardrail-effectiveness-analyzer.py) | Precision/recall/confusion matrix for a safety guardrail vs labeled actual violations, by category | samples/sample-guardrail-labels.csv |
| [red-team-coverage-tracker.py](red-team-coverage-tracker.py) | Adversarial test coverage against a risk-category taxonomy (jailbreak, PII, bias, etc.); go/no-go per category | samples/sample-redteam-results.csv |
| [bias-fairness-scorecard.py](bias-fairness-scorecard.py) | Group-fairness metrics from labeled predictions: selection-rate disparity (four-fifths rule), TPR/FPR gaps (equal opportunity/equalized odds) | samples/sample-bias-fairness-scorecard.csv |

### Strategy & prioritization
| Script | Description | Sample CSV |
|--------|-------------|------------|
| [rice-wsjf-scorer.py](rice-wsjf-scorer.py) | RICE / WSJF scoring | samples/sample-rice-wsjf-scorer.csv |
| [opportunity-scorer.py](opportunity-scorer.py) | Score opportunities from criteria | samples/sample-opportunity-scorer.csv |
| [competitive-feature-matrix.py](competitive-feature-matrix.py) | Feature matrix vs competitors | samples/sample-competitive-feature-matrix.csv |
| [impact-sizing-estimator.py](impact-sizing-estimator.py) | Impact sizing for roadmap | samples/sample-impact-sizing-estimator.csv |
| [roadmap-simulator.py](roadmap-simulator.py) | Monte Carlo style scenario simulation for roadmap confidence | samples/sample-roadmap-simulator.csv |
| [prd-traceability-linker.py](prd-traceability-linker.py) | Requirement-to-artifact trace coverage from PRD to delivery | samples/sample-prd-traceability-linker.csv |

### Budget, sales & OKRs
| Script | Description | Sample CSV |
|--------|-------------|------------|
| [budget-burn-summary.py](budget-burn-summary.py) | Budget burn by category/period | samples/sample-budget.csv |
| [win-loss-summary.py](win-loss-summary.py) | Win/loss summary, top reasons | samples/sample-win-loss.csv |
| [okr-tracker.py](okr-tracker.py) | OKR progress and tracking | samples/sample-okr-tracker.csv |

### Stakeholders, communication & team
| Script | Description | Sample CSV |
|--------|-------------|------------|
| [meeting-load-optimizer.py](meeting-load-optimizer.py) | Meeting load vs work window, focus blocks, recurring-title signals | samples/sample-meetings.csv |
| [exec-summary-generator.py](exec-summary-generator.py) | Executive summary from inputs | samples/sample-exec-summary-generator.csv |
| [stakeholder-update.py](stakeholder-update.py) | Generate stakeholder update | samples/sample-stakeholder-update.json |
| [stakeholder-signoff-tracker.py](stakeholder-signoff-tracker.py) | Track sign-offs by deliverable | samples/sample-stakeholder-signoff.csv |
| [interview-note-analyzer.py](interview-note-analyzer.py) | Analyze interview notes | samples/sample-interview-note-analyzer.csv |
| [space-team-health.py](space-team-health.py) | SPACE (satisfaction, performance, etc.) | samples/sample-space-team-health.csv |
| [retro-action-tracker.py](retro-action-tracker.py) | Retrospective action tracking | samples/sample-retro-action-tracker.csv |
| [raci-matrix.py](raci-matrix.py) | RACI matrix helper | samples/sample-raci-matrix.csv |
| [decision-log.py](decision-log.py) | Decision log structure | samples/sample-decision-log.csv |

### AI/ML ops & tokens
| Script | Description | Sample CSV |
|--------|-------------|------------|
| [model-selection-scorecard.py](model-selection-scorecard.py) | Weighted MCDA rank for models/tiers; optional +weight sensitivity | samples/sample-model-selection-scores.csv, samples/sample-model-selection-weights.csv |
| [model-system-card-builder.py](model-system-card-builder.py) | Generate model or LLM system cards as Markdown/YAML from CLI or JSON | samples/sample-model-system-card.json |
| [model-runtime-orchestrator.py](model-runtime-orchestrator.py) | Runtime model routing, fallback, and guardrails orchestration | — |
| [token-counter.py](token-counter.py) | Token count for prompts/models | samples/sample-prompt-v1.txt |
| [token-budget-allocator.py](token-budget-allocator.py) | Allocate token budget across use cases | — |
| [model-migration-estimator.py](model-migration-estimator.py) | Estimate effort/cost for model migration | — |
| [model-deprecation-watch.py](model-deprecation-watch.py) | Track model sunset dates across your portfolio; prioritized migration queue by urgency × traffic × criticality | samples/sample-model-portfolio.csv |
| [pipeline-health-monitor.py](pipeline-health-monitor.py) | ML pipeline health checks | samples/sample-pipeline-health-monitor.csv |
| [training-job-cost-tracker.py](training-job-cost-tracker.py) | Training/fine-tuning job spend, wasted spend on failed runs, by GPU type and model/team | samples/sample-training-job-cost-tracker.csv |
| [tech-debt-scorer.py](tech-debt-scorer.py) | Tech debt scoring | samples/sample-tech-debt-scorer.csv |
| [metric-forecaster.py](metric-forecaster.py) | Simple metric forecasting | samples/sample-metric-forecaster.csv |

---

## Quick run with samples

From the repo root:

```bash
# Try a CSV-based script with a sample file (samples live in scripts/samples/)
python scripts/feature-adoption-trend.py --csv scripts/samples/sample-feature-adoption.csv --chart
python scripts/sprint-burndown-checker.py --csv scripts/samples/sample-burndown.csv --chart
python scripts/backlog-aging-report.py --csv scripts/samples/sample-backlog-aging.csv --oldest 10
python scripts/meeting-load-optimizer.py --csv scripts/samples/sample-meetings.csv
python scripts/agentic-cost-simulator.py --steps-per-task 6 --retry-rate 0.15 --sub-agent-fanout 2
python scripts/guardrail-effectiveness-analyzer.py --csv scripts/samples/sample-guardrail-labels.csv
python scripts/red-team-coverage-tracker.py --csv scripts/samples/sample-redteam-results.csv
python scripts/model-deprecation-watch.py --csv scripts/samples/sample-model-portfolio.csv
```

For full options, always run:

```bash
python scripts/<script>.py --help
```

Evaluation-specific scripts (eval harness, regression runner, etc.) live in [evals/scripts/](../evals/scripts/) and are documented in [evals/scripts/README.md](../evals/scripts/README.md).

---

## Keyword index (search / grep)

Useful when you know the topic but not the filename:

| Keywords | Scripts |
|----------|---------|
| `ab-test`, `sample-size`, `power`, `mde` | ab-test-calculator.py, survey-sample-size.py |
| `roi`, `payback`, `unit-economics`, `ltv`, `cac` | ai-initiative-roi-calculator.py, ai-unit-economics-calculator.py, ltv-cac-calculator.py |
| `bedrock`, `tokens`, `inference-cost`, `multi-model` | bedrock-cost-calculator.py, multi-model-cost-comparator.py, prompt-cost-optimizer.py |
| `slo`, `sla`, `uptime`, `error-budget`, `latency-slo` | latency-slo-calculator.py, sla-uptime-calculator.py, error-budget-burn-rate.py |
| `velocity`, `sprint`, `burndown`, `backlog`, `dora` | sprint-velocity-tracker.py, sprint-burndown-checker.py, backlog-aging-report.py, dora-metrics-calculator.py |
| `funnel`, `retention`, `adoption`, `churn` | adoption-funnel-analyzer.py, retention-curve-analyzer.py, feature-adoption-trend.py, churn-risk-calculator.py |
| `nps`, `csat`, `feedback` | nps-csat-summary.py, feedback-theme-counter.py, voc-synthesis.py |
| `eval`, `hallucination`, `drift`, `prompt-diff` | eval-label-economics.py, eval-score-trend.py, hallucination-safety-trend.py, data-drift-detector.py, prompt-version-diff.py |
| `risk`, `dependency`, `audit`, `launch-readiness` | risk-register-summary.py, dependency-blocked-summary.py, audit-checklist-summary.py, launch-readiness-score.py |
| `tam`, `pricing`, `roadmap`, `stakeholder` | tam-sam-som-calculator.py, pricing-model-simulator.py, roadmap-timeline-summary.py, win-loss-summary.py |
| `agent`, `agentic`, `tool-use`, `agent-tax` | agent-task-success-tracker.py, tool-use-reliability-scorer.py, agentic-cost-simulator.py |
| `reasoning-tokens`, `extended-thinking`, `context-window`, `compaction` | reasoning-token-budget-calculator.py, context-window-utilization-analyzer.py |
| `judge`, `calibration`, `guardrail`, `red-team`, `injection`, `jailbreak` | llm-judge-calibration-checker.py, guardrail-effectiveness-analyzer.py, red-team-coverage-tracker.py, prompt-injection-risk-scanner.py |
| `deprecation`, `sunset`, `model-portfolio` | model-deprecation-watch.py, model-migration-estimator.py |
| `training-cost`, `gpu-hours`, `fine-tuning`, `wasted-spend` | training-job-cost-tracker.py |
| `bias`, `fairness`, `disparate-impact`, `equal-opportunity`, `demographic-parity` | bias-fairness-scorecard.py |
