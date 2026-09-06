# Platform KPIs

How to measure success for an internal platform, especially one that provides capability that did not exist before.

---

## Why Platforms Are Hard to Measure

Internal platforms break the usual measurement playbook in three ways:

| Problem | Why it matters | What to do instead |
|---------|----------------|--------------------|
| **No baseline** | The capability is new, so there is no "before" number to show lift against | Measure the *workaround* teams used, not the absence of a feature |
| **Captive users** | Adoption can be mandated, so a rising usage line may say nothing about value | Track *voluntary* adoption and stickiness separately from migration |
| **Indirect value** | The platform exists to make other teams succeed, so its outcomes show up in someone else's metrics | Treat *consumer-team outcomes* as the lagging indicator and own the attribution story |

The rest of this guide works through each of these.

---

## Establishing a Baseline When Nothing Existed

The "before" is never truly nothing. Before the platform, consuming teams did one of four things. Each has a measurable cost, and that cost is the baseline.

| Workaround | What it looked like | Baseline to capture |
|------------|---------------------|---------------------|
| **Built it themselves** | Each team has its own script, service, or wrapper | Build time per team, ongoing maintenance hours, number of parallel implementations |
| **Manual process** | Spreadsheet, runbook, copy-paste between tools | Hours per occurrence, occurrences per month, error rate |
| **Asked a person** | Slack DM to the one engineer who knows | Requests per month, turnaround time, share of that person's week |
| **Did not do it** | Requests deferred, declined, or never raised | Count of deferred/declined requests; things that would have shipped |

**"Did not do it" has a baseline of zero.** That is fine. The KPI becomes *count of things that now happen*: evaluations run, deployments made, questions answered, features shipped that depend on the capability. Zero-to-N is a legitimate success measure as long as N is tied to something a consumer team wanted.

### Baseline Interview

Run this with 3–5 consuming teams *before* launch. After launch, memory of the old way fades fast and the baseline is lost.

- [ ] What do you do today when you need [capability]?
- [ ] How long does it take, end to end, and how often?
- [ ] Who has to be involved, and what do they stop doing to help?
- [ ] What goes wrong, and how often?
- [ ] What have you *not* done because it was too hard?
- [ ] If this were free and instant, what would you do differently next quarter?

Record answers in the KPI template at the end of this doc, under "Baseline (workaround)."

---

## Metric Categories

### 1. Adoption & Reach

**What they measure:** Is anyone using it, and are they the teams it was built for?

| Metric | Definition | How to Measure |
|--------|------------|----------------|
| Eligible teams | Teams that have the problem the platform solves | Count from the baseline interviews and org map |
| Active teams | Eligible teams with production usage in the period | Usage logs, grouped by team or service |
| Share of eligible workload | % of qualifying work that runs on the platform vs. elsewhere | Platform volume / (platform + known off-platform volume) |
| Voluntary adoption | Active teams that were not mandated to migrate | Tag each team as opt-in or mandated at onboarding |
| Retention | Teams active this period who were also active last period | Cohort analysis by team |
| Breadth | Distinct use cases or workflows served | Categorize usage by intent, not just by caller |

**Mandated adoption is a compliance number, not a success signal.** If the org requires migration, "% migrated" measures the migration program. Track opt-in adoption and repeat usage separately, and treat those as the health of the platform itself.

---

### 2. Time to Value

**What they measure:** How much friction sits between "I need this" and "it worked"?

| Metric | Definition | How to Measure |
|--------|------------|----------------|
| Time to first success | Elapsed time from first contact to first successful production use | Onboarding timestamp → first successful call or job |
| Onboarding steps | Number of manual steps, approvals, and handoffs to get started | Count them, then count them again each quarter |
| Self-serve rate | % of onboardings completed with no ticket, DM, or meeting | Support log cross-referenced against new teams |
| Docs deflection | % of questions answered by docs rather than the platform team | Support channel volume per active team over time |

See [templates/dx-assessment.md](../templates/dx-assessment.md) for a fuller time-to-first-value breakdown.

---

### 3. Substitution & Avoided Cost

**What they measure:** What did the platform replace, and what did that free up?

| Metric | Definition | How to Measure |
|--------|------------|----------------|
| Hours returned per team | Baseline workaround hours minus current hours, per team per month | Baseline interview × active teams; re-survey quarterly |
| Duplicate builds avoided | Teams that would have built their own, times the estimated build cost | Count from baseline; use a conservative build estimate |
| Workarounds retired | Scripts, tools, or manual processes decommissioned | Ask teams to confirm; track as a list, not a guess |
| Person-dependency removed | Requests that no longer route through a single expert | Request volume to that person before vs. after |

**Be conservative.** Avoided-cost numbers get discounted by every skeptical reader. Use the lowest defensible estimate and show the math.

---

### 4. Consumer Outcomes

**What they measure:** Did the teams using the platform do better because of it?

| Metric | Definition | How to Measure |
|--------|------------|----------------|
| Enabled shipments | Features or projects that shipped and depend on the platform | Tag releases; confirm with consuming teams |
| Consumer cycle time | Cycle time for platform-dependent work vs. before | Delivery data, filtered to work that touches the platform |
| Incidents avoided | Failure classes the platform eliminates (e.g. key leaks, unbounded spend) | Incident log before vs. after, by category |
| Consumer KPI movement | Change in the consuming team's own metrics for platform-dependent work | Their dashboard, cited with their permission |

**Attribution guidance.** The platform never fully owns these outcomes. Do not claim the consuming team's win as a platform number. Instead:

- State the mechanism: "X shipped in 3 weeks; the eval step took 1 day on the platform and was estimated at 2 weeks without it."
- Pair every quantitative outcome with a named case study or a quote from the consuming team.
- Report "enabled by" counts, not "caused by" percentages.

---

### 5. Reliability & Operations

**What they measure:** Can teams depend on it, and what does it cost the platform team to keep it that way?

| Metric | Definition | How to Measure |
|--------|------------|----------------|
| SLO attainment | % of periods where latency and availability targets were met | Standard SLO tooling; see [scripts/latency-slo-calculator.py](../scripts/latency-slo-calculator.py) |
| Error rate | % of requests or jobs that fail for platform reasons | Separate platform errors from consumer misuse |
| Support load per team | Tickets and questions per active team per month | Support channel volume / active teams |
| On-call burden | Pages per week and time to resolve | Paging system |
| Change failure rate | % of platform releases that cause an incident or rollback | Release log |

A platform that other teams build on inherits every consumer's uptime expectation. If it is less reliable than the workaround it replaced, adoption will stall regardless of the feature set.

---

### 6. Satisfaction

**What they measure:** Would the teams choose it again?

| Metric | Definition | How to Measure |
|--------|------------|----------------|
| Internal CSAT | Rating after onboarding and quarterly | Short survey; see [scripts/nps-csat-summary.py](../scripts/nps-csat-summary.py) |
| Internal NPS | "How likely are you to recommend this to another team?" | Same survey |
| Would-not-go-back | % who say they would not return to the old way | One question, asked directly; the most honest signal available |
| Support sentiment | Tone of support requests: confused, frustrated, or extending | Tag a sample of tickets each month |

Internal users are polite in surveys and honest in Slack. Read both.

---

### 7. Cost & Efficiency

**What they measure:** What does it cost to serve, and does that improve with scale?

| Metric | Definition | How to Measure |
|--------|------------|----------------|
| Cost to serve per team | Platform run cost / active teams | Infra and vendor bills plus platform team cost |
| Leverage ratio | Consuming engineers served / platform engineers | Headcount; should rise over time |
| Unit cost trend | Cost per request, job, or unit of work over time | Should fall as volume grows |
| Spend visibility | % of platform-mediated spend attributable to a team | Cost allocation coverage |

---

## KPIs by Platform Stage

The right KPI set changes as the platform matures. Leading indicators are what to watch weekly; lagging indicators are what to report quarterly.

| Stage | Leading indicators | Lagging indicators |
|-------|--------------------|--------------------|
| **Pre-launch** | Design partners committed, baselines captured for each, onboarding steps counted | None yet; the goal is a measurable starting point |
| **Launch** | Time to first success, self-serve rate, support load per team | Active teams, first enabled shipment |
| **Growth** | Share of eligible workload, voluntary adoption, retention by cohort | Hours returned, workarounds retired, consumer cycle time |
| **Mature** | Unit cost trend, leverage ratio, SLO attainment | Duplicate builds avoided, would-not-go-back, alternatives deprecated |

A common mistake is reporting growth-stage numbers at launch. Two active teams out of thirty is not a failure in month one; it is the expected shape. Report the stage's own indicators and say which stage the platform is in.

---

## Anti-Patterns

- **Vanity volume.** API calls, jobs run, and rows processed rise with any usage, including retries, tests, and one noisy consumer. Normalize by team and by use case.
- **"Teams onboarded."** Onboarding is a step, not an outcome. Count teams with repeat production usage.
- **Migration counted as adoption.** A mandated cutover measures the program's enforcement, not the platform's pull. Keep the two lines separate.
- **Measuring the platform team's output.** Features shipped, endpoints added, and docs written are inputs. If consumers do not move, the inputs did not matter.
- **Self-generated demand.** Usage the platform team created for itself (internal tests, demo workloads, dogfooding) inflates every number. Exclude it or label it.
- **One north star with no segments.** A single healthy top-line number can hide a critical consumer silently leaving. Always show the per-team breakdown behind the total.
- **Claiming consumer wins.** "The platform drove a 20% revenue increase" is rarely true and always contested. Report "enabled by," show the mechanism, and let the consuming team own the number.

---

## Choosing Your KPI Set

Aim for 5–8 KPIs, not 20. Before finalizing:

- [ ] Every category that matters for this platform has one leading and one lagging metric
- [ ] Every KPI has a named owner and a data source that exists today (or a dated plan to build it)
- [ ] The baseline for each KPI was captured *before* launch, from the workaround, not assumed
- [ ] Voluntary adoption is tracked separately from any mandated migration
- [ ] At least one KPI could show the platform is *failing*; if every metric can only go up, the set is not honest
- [ ] Every consumer-outcome KPI is paired with a qualitative source (case study, quote, named team)
- [ ] The current stage is stated, and the KPIs match that stage
- [ ] Self-generated usage (tests, demos, dogfooding) is excluded or labeled

### KPI Definition Template

| KPI | Category | Baseline (workaround) | Target | Data source | Owner |
|-----|----------|-----------------------|--------|-------------|-------|
| [Metric name] | [Adoption / Time to value / Substitution / Outcomes / Reliability / Satisfaction / Cost] | [Number from baseline interview and how it was derived] | [Value and date] | [System or survey; "not yet built" is an acceptable answer with a date] | [Person] |
| [Metric name] | | | | | |
| [Metric name] | | | | | |

---

## Worked Example: Internal LLM Gateway

**The platform.** A shared gateway that every team calls for model access, providing routing, key management, spend tracking, and a built-in eval and guardrail step.

**Before.** Eleven teams called model APIs directly with their own keys. No one could see total spend by team. Each team that wanted guardrails or evals built its own, which took about two weeks of one engineer's time per team. Three teams had shelved LLM features because the setup overhead did not fit their sprint. One senior engineer answered most "how do I call the model" questions, taking roughly a day a week.

**Baseline captured.** Eleven eligible teams. Roughly 22 engineer-weeks of duplicated eval and guardrail setup across the teams that built it. Three deferred features. One expert at 20% capacity on support. No spend attributable to a team.

**KPI set for the first two quarters (Launch → Growth):**

| Metric | Category | Baseline | Minimum | Target | Stretch |
|--------|----------|----------|---------|--------|---------|
| Active teams (repeat production use) | Adoption | 0 | 4 | 7 | 11 |
| Voluntary adoption (of active) | Adoption | - | 50% | 75% | 100% |
| Time to first successful call | Time to value | ~2 weeks (own build) | 2 days | 1 day | <1 hour |
| Self-serve onboarding rate | Time to value | 0% | 50% | 75% | 90% |
| Eval/guardrail setup per team | Substitution | ~2 engineer-weeks | 2 days | 1 day | Same day |
| Deferred features now shipped | Outcomes | 0 of 3 | 1 | 2 | 3 |
| Spend attributable to a team | Cost | 0% | 80% | 95% | 100% |
| Gateway p99 latency overhead | Reliability | 0 ms (direct calls) | <150 ms | <75 ms | <40 ms |
| Would-not-go-back | Satisfaction | - | 60% | 80% | 90% |

**What the first quarter showed.** Six teams active, five voluntary. Total request volume was up sharply, but a per-team breakdown showed that a third of it was the platform team's own load tests, which had been counted. Excluding those, two of the six teams were still sending only staging traffic. The reported number became "four teams in production" and the anti-pattern the set nearly fell into was self-generated demand. One of the three deferred features shipped, with the consuming team's own quote in the review: "the eval step took an afternoon."

---

## Related

- [AI Product Metrics](../evals/metrics/ai-product-metrics.md) – quality, performance, cost, and safety metrics for AI features themselves
- [OKR Builder](../templates/okr-builder.md) – turn the KPI set into objectives and key results
- [DX Assessment](../templates/dx-assessment.md) – time-to-first-value and onboarding friction in detail
- [SPACE Framework](../frameworks/space-framework.md) – platform team health alongside platform outcomes
- Scripts: [adoption-funnel-analyzer.py](../scripts/adoption-funnel-analyzer.py), [feature-adoption-trend.py](../scripts/feature-adoption-trend.py), [retention-curve-analyzer.py](../scripts/retention-curve-analyzer.py), [okr-tracker.py](../scripts/okr-tracker.py)
