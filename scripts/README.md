# Scripts

Python 3.10+ utilities for PM workflows. Install once, then run any script:

```bash
pip install -r scripts/requirements.txt
python scripts/<script-name>.py --help
```

Sample CSVs and example files live in **`scripts/samples/`** (e.g. `samples/sample-feature-adoption.csv`). Use your own data or these for testing.

---

## By category

### Experiments & statistics
| Script | Description | Sample CSV |
|--------|-------------|------------|
| [ab-test-calculator.py](ab-test-calculator.py) | A/B test sample size, duration, power; proportions or means | — |
| [experiment-duration-calculator.py](experiment-duration-calculator.py) | How long to run an experiment given traffic and sample size | — |
| [experiment-result-interpreter.py](experiment-result-interpreter.py) | Interpret baseline vs variant with confidence | — |
| [confidence-interval-calculator.py](confidence-interval-calculator.py) | Wilson score and mean CIs | — |
| [survey-sample-size.py](survey-sample-size.py) | Sample size for target margin and confidence | — |
| [cohort-comparison-tool.py](cohort-comparison-tool.py) | Compare cohorts (e.g. retention, conversion) | — |

### Cost & economics
| Script | Description | Sample CSV |
|--------|-------------|------------|
| [bedrock-cost-calculator.py](bedrock-cost-calculator.py) | Bedrock inference cost from tokens and model | — |
| [multi-model-cost-comparator.py](multi-model-cost-comparator.py) | Compare cost across Bedrock, OpenAI, Anthropic | — |
| [prompt-cost-optimizer.py](prompt-cost-optimizer.py) | Estimate and optimize prompt cost by model/volume | — |
| [ai-unit-economics-calculator.py](ai-unit-economics-calculator.py) | Cost per request, revenue per user, unit economics | — |
| [ai-initiative-roi-calculator.py](ai-initiative-roi-calculator.py) | Payback for AI projects (dev + inference vs benefit) | — |
| [ltv-cac-calculator.py](ltv-cac-calculator.py) | LTV, CAC, payback | — |
| [tam-sam-som-calculator.py](tam-sam-som-calculator.py) | TAM/SAM/SOM sizing | — |
| [pricing-model-simulator.py](pricing-model-simulator.py) | Model pricing scenarios (usage-based, tiered) | — |
| [revenue-waterfall.py](revenue-waterfall.py) | Revenue waterfall breakdown | — |

### Delivery, velocity & backlog
| Script | Description | Sample CSV |
|--------|-------------|------------|
| [velocity-trend-analyzer.py](velocity-trend-analyzer.py) | Sprint velocity trend, rolling window, target | — |
| [sprint-burndown-checker.py](sprint-burndown-checker.py) | Burndown vs plan, chart | samples/sample-burndown.csv |
| [sprint-mix-report.py](sprint-mix-report.py) | Mix by type/priority; balance | samples/sample-sprint-mix.csv |
| [sprint-velocity-tracker.py](sprint-velocity-tracker.py) | Track velocity over sprints | samples/sample-velocity.csv |
| [sprint-goal-checker.py](sprint-goal-checker.py) | Goals vs completed work | samples/sample-sprint-goals.csv, samples/sample-sprint-done.csv |
| [sprint-scope-checker.py](sprint-scope-checker.py) | Scope vs capacity | — |
| [commitment-predictability-index.py](commitment-predictability-index.py) | CPI from velocity history | samples/sample-velocity.csv |
| [capacity-planning-calculator.py](capacity-planning-calculator.py) | Capacity from team size, PTO, meetings, points/day | — |
| [capacity-planner.py](capacity-planner.py) | Capacity planning with scenarios | — |
| [cycle-lead-time-analyzer.py](cycle-lead-time-analyzer.py) | Cycle/lead time from ticket CSV | — |
| [throughput-wip-analyzer.py](throughput-wip-analyzer.py) | Throughput and WIP over time | — |
| [backlog-aging-report.py](backlog-aging-report.py) | Age bands, oldest items | samples/sample-backlog-aging.csv |
| [backlog-health-report.py](backlog-health-report.py) | Backlog health (estimation, priority, stale) | — |
| [status-duration-analyzer.py](status-duration-analyzer.py) | Time in status from transitions | samples/sample-status-transitions.csv, samples/sample-status-spans.csv |
| [release-impact-summary.py](release-impact-summary.py) | Shipped scope by version | samples/sample-release-impact.csv |
| [release-cadence-report.py](release-cadence-report.py) | Release frequency and grouping | samples/sample-release-cadence.csv |
| [release-notes-generator.py](release-notes-generator.py) | Generate release notes from data | — |
| [roadmap-timeline-summary.py](roadmap-timeline-summary.py) | Roadmap view, overlaps, by quarter | samples/sample-roadmap.csv |
| [delivery-completion-forecaster.py](delivery-completion-forecaster.py) | Forecast completion dates | — |
| [dora-metrics-calculator.py](dora-metrics-calculator.py) | DORA deployment, lead time, change failure | — |

### Adoption, health & retention
| Script | Description | Sample CSV |
|--------|-------------|------------|
| [adoption-funnel-analyzer.py](adoption-funnel-analyzer.py) | Funnel steps and conversion (e.g. Visit→Signup→Activate) | — |
| [feature-adoption-trend.py](feature-adoption-trend.py) | Adoption % or DAU/WAU over time, trend label | samples/sample-feature-adoption.csv |
| [feature-adoption-scorecard.py](feature-adoption-scorecard.py) | Adoption scorecard by segment/feature | — |
| [customer-health-score-trend.py](customer-health-score-trend.py) | Health score over time, at-risk threshold | samples/sample-customer-health.csv |
| [churn-risk-calculator.py](churn-risk-calculator.py) | Churn risk from usage drop, adoption, tickets | — |
| [retention-curve-analyzer.py](retention-curve-analyzer.py) | Retention curves and cohort comparison | — |
| [beta-conversion-report.py](beta-conversion-report.py) | Beta→GA conversion, trend | samples/sample-beta-conversion.csv |

### Incidents, SLO & reliability
| Script | Description | Sample CSV |
|--------|-------------|------------|
| [incident-rate-trend.py](incident-rate-trend.py) | Incident rate over time, chart | samples/sample-incidents.csv |
| [incident-postmortem.py](incident-postmortem.py) | Structure postmortem output | — |
| [latency-slo-calculator.py](latency-slo-calculator.py) | Latency SLO and error budget from availability/RPM | — |
| [sla-uptime-calculator.py](sla-uptime-calculator.py) | Uptime, error budget remaining, breach risk | — |
| [error-budget-burn-rate.py](error-budget-burn-rate.py) | Error budget burn rate | — |
| [alert-threshold-calculator.py](alert-threshold-calculator.py) | Alert thresholds from SLO and baseline | — |
| [inference-latency-trend.py](inference-latency-trend.py) | Inference latency (e.g. p99) over time | samples/sample-inference-latency.csv |

### Feedback, NPS & support
| Script | Description | Sample CSV |
|--------|-------------|------------|
| [nps-csat-summary.py](nps-csat-summary.py) | NPS from promoter/passive/detractor; CSAT summary | — |
| [feedback-theme-counter.py](feedback-theme-counter.py) | Count feedback by theme | samples/sample-feedback.csv |
| [sentiment-analysis.py](sentiment-analysis.py) | Sentiment on text (e.g. feedback) | — |
| [support-escalation-trend.py](support-escalation-trend.py) | Escalation volume/trend by severity | samples/sample-support-tickets.csv |

### Risk, dependencies & governance
| Script | Description | Sample CSV |
|--------|-------------|------------|
| [risk-register-summary.py](risk-register-summary.py) | Top risks, summary by category | samples/sample-risks.csv |
| [dependency-blocked-summary.py](dependency-blocked-summary.py) | Blocked-by and blocking summary | samples/sample-dependency-blocked.csv |
| [dependency-risk-mapper.py](dependency-risk-mapper.py) | Dependency and risk mapping | — |
| [blocker-wait-summary.py](blocker-wait-summary.py) | Blocker and wait-time summary | — |
| [audit-checklist-summary.py](audit-checklist-summary.py) | Audit controls, open/by domain | samples/sample-audit-controls.csv |

### Launch & rollout
| Script | Description | Sample CSV |
|--------|-------------|------------|
| [launch-readiness-score.py](launch-readiness-score.py) | Go/no-go score from checklist | samples/sample-launch-readiness.csv |
| [launch-checklist.py](launch-checklist.py) | Launch checklist workflow | — |
| [feature-rollout-calculator.py](feature-rollout-calculator.py) | Phased rollout sample size and duration | — |
| [feature-flag-planner.py](feature-flag-planner.py) | Feature flag stages and gates | — |

### Evals & quality
| Script | Description | Sample CSV |
|--------|-------------|------------|
| [eval-label-economics.py](eval-label-economics.py) | Gold-set size & labeling cost for target CI width on pass rate, precision, or recall | — |
| [eval-score-trend.py](eval-score-trend.py) | Eval score over time, chart | samples/sample-eval-runs.csv |
| [hallucination-safety-trend.py](hallucination-safety-trend.py) | Hallucination/safety metric trend | samples/sample-hallucination-safety.csv |
| [data-drift-detector.py](data-drift-detector.py) | Drift between baseline and current dataset | — |
| [prompt-version-diff.py](prompt-version-diff.py) | Diff two prompt versions | samples/sample-prompt-v1.txt, sample-prompt-v2.txt |
| [groundedness-scorer.py](groundedness-scorer.py) | Groundedness scoring for outputs | — |
| [rag-quality-analyzer.py](rag-quality-analyzer.py) | RAG retrieval/answer quality | — |

### Strategy & prioritization
| Script | Description | Sample CSV |
|--------|-------------|------------|
| [rice-wsjf-scorer.py](rice-wsjf-scorer.py) | RICE / WSJF scoring | — |
| [opportunity-scorer.py](opportunity-scorer.py) | Score opportunities from criteria | — |
| [competitive-feature-matrix.py](competitive-feature-matrix.py) | Feature matrix vs competitors | — |
| [impact-sizing-estimator.py](impact-sizing-estimator.py) | Impact sizing for roadmap | — |

### Budget, sales & OKRs
| Script | Description | Sample CSV |
|--------|-------------|------------|
| [budget-burn-summary.py](budget-burn-summary.py) | Budget burn by category/period | samples/sample-budget.csv |
| [win-loss-summary.py](win-loss-summary.py) | Win/loss summary, top reasons | samples/sample-win-loss.csv |
| [okr-tracker.py](okr-tracker.py) | OKR progress and tracking | — |

### Stakeholders, communication & team
| Script | Description | Sample CSV |
|--------|-------------|------------|
| [exec-summary-generator.py](exec-summary-generator.py) | Executive summary from inputs | — |
| [stakeholder-update.py](stakeholder-update.py) | Generate stakeholder update | — |
| [stakeholder-signoff-tracker.py](stakeholder-signoff-tracker.py) | Track sign-offs by deliverable | samples/sample-stakeholder-signoff.csv |
| [interview-note-analyzer.py](interview-note-analyzer.py) | Analyze interview notes | — |
| [space-team-health.py](space-team-health.py) | SPACE (satisfaction, performance, etc.) | — |
| [retro-action-tracker.py](retro-action-tracker.py) | Retrospective action tracking | — |
| [raci-matrix.py](raci-matrix.py) | RACI matrix helper | — |
| [decision-log.py](decision-log.py) | Decision log structure | — |

### AI/ML ops & tokens
| Script | Description | Sample CSV |
|--------|-------------|------------|
| [token-counter.py](token-counter.py) | Token count for prompts/models | — |
| [token-budget-allocator.py](token-budget-allocator.py) | Allocate token budget across use cases | — |
| [model-migration-estimator.py](model-migration-estimator.py) | Estimate effort/cost for model migration | — |
| [pipeline-health-monitor.py](pipeline-health-monitor.py) | ML pipeline health checks | — |
| [tech-debt-scorer.py](tech-debt-scorer.py) | Tech debt scoring | — |
| [metric-forecaster.py](metric-forecaster.py) | Simple metric forecasting | — |

---

## Quick run with samples

From the repo root:

```bash
# Try a CSV-based script with a sample file (samples live in scripts/samples/)
python scripts/feature-adoption-trend.py --csv scripts/samples/sample-feature-adoption.csv --chart
python scripts/sprint-burndown-checker.py --csv scripts/samples/sample-burndown.csv --chart
python scripts/backlog-aging-report.py --csv scripts/samples/sample-backlog-aging.csv --oldest 10
```

For full options, always run:

```bash
python scripts/<script>.py --help
```

Evaluation-specific scripts (eval harness, regression runner, etc.) live in [evals/scripts/](../evals/scripts/) and are documented in [evals/scripts/README.md](../evals/scripts/README.md).
