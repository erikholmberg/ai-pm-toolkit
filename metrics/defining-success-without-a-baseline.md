# Defining Success Without a Baseline

How to define success for something new, when there is no existing platform, workflow, or competitor to compare it to.

Most measurement advice assumes a "before" number: conversion was 4%, make it 5%. For genuinely new work — a first-of-its-kind AI feature, a capability nobody in the org has ever had, a job users currently do not do at all — that number does not exist. The failure mode is not "no metrics." It is *late* metrics: a target invented after launch, from data the launch itself produced, which can only ever confirm what happened.

This guide covers how to construct a defensible starting point before launch and how to set thresholds you could actually miss.

For internal platforms specifically — captive users, mandated migration, value that shows up on someone else's dashboard — see [platform-kpis.md](./platform-kpis.md). This doc is the general case and stays focused on the *definition* of success rather than the KPI set.

---

## First: Which Kind of "Nothing" Do You Have?

These get conflated, and they need different treatment. Pick one before going further.

| Case | What it means | Where the baseline comes from |
|------|---------------|-------------------------------|
| **The work happens, badly** | People do the job today with spreadsheets, DMs, or a script | Measure the workaround — see [platform-kpis.md § Establishing a Baseline](./platform-kpis.md#establishing-a-baseline-when-nothing-existed) |
| **The work happens elsewhere** | Users solve it with another product, or out of your surface entirely | Ask where it goes today; instrument the exit, or survey the alternative |
| **The work does not happen** | Requests are deferred, declined, or never raised because it is too hard | Count the deferrals; the baseline is genuinely zero and the KPI is zero-to-N |
| **The demand is unproven** | You believe people want this; nobody has asked for it | You do not have a measurement problem yet. You have a validation problem — see [Before You Have a Product](#before-you-have-a-product) |

The fourth case is the one most often mislabeled as "no baseline." If nobody has asked for the thing, defining a success metric is premature; the first job is producing evidence that anyone wants it at all.

---

## Seven Substitutes for a Baseline

None of these is a real "before" number. Each is defensible if you say plainly how it was constructed.

### 1. Time-and-motion on a sample

Watch 5–10 people do the task the current way and time it. Record steps, handoffs, and rework, not just total minutes.

- **Use when:** the work happens today, even informally.
- **Strength:** grounded in observed behavior, not recall.
- **Weakness:** small N; people work differently when watched. Report the range, not a single average.

### 2. Human-performance baseline

Have people do the task the AI feature will do, on the same inputs it will see, and score them with the same rubric. This is the honest comparison point for most AI features: not "the model scores 82%," but "the model scores 82% where a trained human scores 91% and a rushed human scores 74%."

- **Use when:** the feature automates or accelerates judgment work.
- **Strength:** directly answers "is this good enough to trust?"
- **Weakness:** you have to build the rubric first. See [evals/frameworks/llm-eval-framework.md](../evals/frameworks/llm-eval-framework.md) and [eval-label-economics.py](../scripts/eval-label-economics.py) for what labeling a comparison set costs.

### 3. The deferral count

Every "we'd love to but we can't" is a data point. Go back through backlogs, sales-loss notes, support macros, and meeting notes and count the requests that were dropped for want of this capability.

- **Use when:** the work does not happen at all.
- **Strength:** turns a zero baseline into a target with names attached. "Three deferred features" is a better KPI than "usage."
- **Weakness:** biased toward what was written down. Treat the count as a floor.

### 4. Holdout built forward

You cannot get a before, so build the control alongside the launch: hold back a random slice of eligible users or teams, and compare. The baseline arrives at the same time as the result.

- **Use when:** the population is large enough to split and withholding is ethical and practical.
- **Strength:** the only substitute here that supports a causal claim.
- **Weakness:** needs volume and discipline. Size it first — [experiment-duration-calculator.py](../scripts/experiment-duration-calculator.py), [ab-test-calculator.py](../scripts/ab-test-calculator.py).

### 5. Staged rollout as its own control

Where a holdout is not possible, roll out in cohorts and treat cohort N as the reference for cohort N+1. Differences in *time to value* and *support load per cohort* are usually meaningful even when outcome differences are not.

- **Use when:** rollout is sequential anyway (region, tier, team).
- **Weakness:** later cohorts get better docs and a more stable product; that is improvement, not comparison. Do not read outcome deltas as causal.

### 6. The cost floor

Not a behavioral baseline but a decision-relevant one: what does the thing cost to build and run, and what usage level makes it worth keeping? That number is knowable before launch and does not depend on any history.

- **Use when:** you need a threshold and there is no comparable behavior anywhere.
- **Strength:** produces a *kill* line, which most new-product metric sets lack.
- **Weakness:** says nothing about whether users are better off. Pair it with a quality or satisfaction metric.

### 7. Pre-registered expert prediction

Before launch, have 5–10 people close to the problem privately write down what they expect each metric to be at day 30 and day 90. Collect the spread; do not discuss first.

- **Use when:** nothing else is available.
- **Strength:** makes the implicit expectation explicit and dated, so the result is genuinely informative — a wide spread is itself a finding, and the exercise blocks after-the-fact goalpost moving.
- **Weakness:** it is opinion. Label it as such, and keep the original predictions where everyone can see them.

**Combine two.** One quantitative anchor plus one qualitative source is the practical minimum. A single constructed baseline will be argued with; a number and a named case study together usually survive the room.

---

## Write Success as a Falsifiable Claim

The core discipline: state success in a form that could turn out to be wrong, and write it down before launch.

> **We believe** [who] will [do what], because [why].
> **We will know we are right if** [metric] reaches [threshold] by [date], measured from [source].
> **We will know we are wrong if** [metric] stays below [floor] by [date], or [counter-signal] appears.
> **If we are wrong we will** [narrow the audience / change the mechanism / stop].
> **Baseline:** [constructed how, from what, by whom, on what date].

Two rules make it work:

- **The wrong-condition is not optional.** If no plausible outcome would count as failure, the claim is not a success definition — it is a description. At least one metric in the set must be able to go the wrong way.
- **The date comes before the data.** Write and circulate this before the first user touches the thing. A threshold set afterward is a summary, no matter how it is phrased.

---

## Setting a Threshold With No History

Four ways to anchor a number that nobody can derive from past data. Say which one you used.

| Method | How it works | Best for |
|--------|--------------|----------|
| **Breakeven** | Solve for the usage or savings that covers build and run cost | Anything with a real cost line; produces a floor |
| **Decision relevance** | Ask what number would change a decision: invest more, keep, kill | Setting the *stop* threshold |
| **Alternative use** | What the team would achieve on the next-best project in the same time | Portfolio calls, arguing about opportunity cost |
| **Smallest useful result** | The smallest outcome that would still be worth having shipped | Early-stage features where any signal beats none |

Then set three levels rather than one point target — **minimum** (below this we stop), **target** (what we planned for), **stretch** (what would justify more investment). Three levels give the launch review somewhere to land besides "hit" or "missed," which matters when the target itself was a guess.

State the confidence you have in the number. "Target 40%, derived from breakeven at 25% and one design partner's stated intent; low confidence, revisit at day 30" is more useful to a reader than a bare 40%.

---

## Before You Have a Product

For the unproven-demand case, success in the first phase is *evidence*, not usage. These have baselines that do not depend on the product existing.

| Method | What it produces | Success looks like |
|--------|------------------|--------------------|
| **Concierge / Wizard-of-Oz** | Deliver the outcome manually to a handful of users | Repeat requests, and willingness to wait for a slow manual version |
| **Fake door** | Instrument intent on a surface that does not exist yet | Click-through relative to nearby real features, plus what people type when asked why |
| **Design partners** | 3–5 teams committed before build, with their baselines captured | Written commitment to use it, not enthusiasm in a call |
| **Pre-sell / waitlist** | Demand expressed at some cost to the user | Conversion from waitlist to first use, not waitlist size |

The measurable thing in every row is a cost the user paid — time, waiting, money, a signature. Interest that costs nothing predicts nothing.

Carry each design partner's pre-build baseline forward into the launch KPI set. Their "before" is the only real one you will get.

---

## The First Period Is the Baseline

Once launched, the first period becomes the reference for everything after. Protect it.

- **Instrument before launch, not after.** A metric you start collecting in week 6 has no week 1. Ship the events with the feature.
- **Declare Period 0 explicitly.** Name the window (first 4 weeks is common) and freeze the numbers at the end of it. Then every later report is a comparison, not an assertion.
- **Exclude your own traffic.** Team usage, demos, load tests, and dogfooding inflate the first period more than any later one, which permanently distorts the baseline.
- **Segment from day one.** A blended first-period number that mixes design partners with cold users is not a baseline for either.
- **Record the conditions.** What was in the launch, who could see it, what else shipped that week. In six months this context is what makes the comparison defensible.
- **Re-baseline on material change.** If the audience, surface, or model changes substantially, start a new Period 0 and say so, rather than quietly extending the old series.

---

## Leading Signals for the First 90 Days

Outcome metrics need volume and time. These are available early and say something real.

| Signal | Why it works without a baseline | Watch for |
|--------|--------------------------------|-----------|
| **Repeat use** | Compares each user to themselves; needs no external reference | One enthusiast producing most of the volume |
| **Time to first success** | Absolute and measurable from the first user | Users who never reach it, and are invisible in averages |
| **Completion rate** | Started vs. finished within a session, self-contained | Abandonment that looks like satisfaction |
| **Unprompted requests** | Access requests, questions, and feature asks nobody solicited | Volume from a single team |
| **Manual workaround retirement** | Users turning off the old way is the strongest voluntary signal available | Confirm it happened; do not infer it |
| **Would-not-go-back** | One survey question, interpretable at N=6 | Politeness; ask in the flow, not in a quarterly survey |
| **Correction rate** (AI features) | How often output is edited, rejected, or redone | Silent acceptance of bad output, which reads as success |

At small N, a named case study is worth more than a percentage. "Four of six design partners use it weekly; the two who stopped both said the latency broke their flow" is a finding. "67% weekly active" from the same six users is a number pretending to be one.

---

## Anti-Patterns

- **The metric invented after the fact.** Numbers come in, a threshold is chosen that they clear, and the launch is declared a success. Preventable only by writing the threshold down first.
- **Zero as the baseline for everything.** Technically true, uninformative, and unfalsifiable — any usage beats zero. Zero is a legitimate baseline only when the *unit* is meaningful: three deferred features shipped, not "1,200 API calls."
- **Growth rate as the whole story.** From a small base, every percentage is enormous. Report absolute numbers next to every rate in the first two quarters.
- **Borrowing a benchmark.** Another company's activation rate came from their audience, surface, and funnel. Cite it as a sanity check, never as a target.
- **Confusing novelty with adoption.** The first weeks include everyone who was curious once. Repeat use in weeks 3–6 is the real signal; expect the curve to drop and say so in advance so the dip does not read as failure.
- **Success defined only as usage.** Usage of a bad feature is still usage. Pair every adoption metric with a quality, correction, or satisfaction metric.
- **Moving to a new metric each review.** Switching metrics whenever the current one flattens makes the series unreadable. Change the metric when the strategy changes, and note the switch.
- **Hiding the construction.** A baseline whose derivation is not written down gets treated as fabricated the moment it is inconvenient.

---

## Checklist

Before launch:

- [ ] Named which "nothing" this is (work happens badly / elsewhere / not at all / demand unproven)
- [ ] Constructed at least one quantitative baseline, with its method and date written down
- [ ] Paired it with a qualitative source: design partner, case study, or quote
- [ ] Wrote the success claim in falsifiable form, including the wrong-condition
- [ ] Set minimum / target / stretch, and stated which threshold method produced them
- [ ] At least one metric in the set can move the wrong way
- [ ] Named the decision each metric feeds, and who makes it
- [ ] Events instrumented and verified in staging, before the first user
- [ ] Period 0 window declared, with internal traffic excluded
- [ ] Circulated to the people who will review the launch, and dated

At the first review:

- [ ] Reported against the pre-registered thresholds, including any that were missed
- [ ] Absolute numbers shown alongside every rate
- [ ] Per-segment breakdown shown behind the total
- [ ] Baseline construction restated, so new readers can judge it
- [ ] Said which thresholds were wrong and why, rather than quietly replacing them

---

## Worked Example: Support Conversation Summaries

**The feature.** An AI feature that writes a summary of a support conversation and attaches it to the ticket on close. Nobody did this before: agents closed tickets with a one-line status and no summary, and there is no comparable feature in the product to compare against.

**Which "nothing."** Mostly *the work does not happen* — summaries were never written. Partly *the work happens badly*: about one in five agents wrote freeform notes.

**Baselines constructed, pre-launch:**

| Source | Method | Result |
|--------|--------|--------|
| Manual note sample | Time-and-motion on 8 agents who write notes | 3–6 minutes per ticket; 19% of tickets have any note |
| Human-performance set | 40 conversations summarized by two senior agents, scored on a 5-point rubric | Senior agents average 4.4; a rushed sample averages 3.6 |
| Deferral count | Backlog and QA review notes | 11 escalations in 6 months traced to "no context on the prior ticket" |
| Cost floor | Inference cost at projected volume vs. agent-minutes saved | Breakeven at ~35% of closed tickets using the summary unedited |
| Expert prediction | 6 people, private, pre-launch | Day-30 unedited-acceptance guesses ranged 20%–70% |

The expert spread was the useful finding: a 20–70% range meant nobody actually knew, which is why the threshold was set from breakeven rather than from expectation.

**Success claim, written before launch:**

> We believe support agents will accept AI-written summaries without editing on most tickets, because summary writing is work they skip today rather than work they value doing themselves.
> We will know we are right if unedited acceptance reaches 50% by day 60, with a quality score at or above 4.0 on the same rubric used for the human set.
> We will know we are wrong if acceptance is below 35% (breakeven) at day 60, or if the correction rate rises after week 3, or if any summary-related quality incident reaches a customer.
> If we are wrong we will narrow to the two ticket types with the highest acceptance and re-test, or stop.
> Baseline: constructed 2026-02-11 from a time-and-motion sample (8 agents), a 40-conversation human-scored set, and inference-cost breakeven. No prior feature exists to compare against.

**KPI set for the first quarter:**

| Metric | Baseline | Minimum | Target | Stretch |
|--------|----------|---------|--------|---------|
| Unedited acceptance rate | 0% (feature did not exist) | 35% | 50% | 70% |
| Quality score vs. human set | 4.4 senior / 3.6 rushed | 3.6 | 4.0 | 4.4 |
| Tickets closed with a summary | 19% (freeform notes) | 60% | 85% | 95% |
| Agent minutes per closed ticket | 3–6 min (note-writers only) | No increase | −2 min | −4 min |
| Escalations citing missing context | 11 / 6 months | 8 | 5 | 0 |
| Would-not-go-back (agent survey) | – | 50% | 75% | 90% |
| Summary-related quality incidents | 0 | 0 | 0 | 0 |

**What the first period showed.** Acceptance was 44% at day 60 — above breakeven, below target. The segment breakdown carried the decision: 71% on billing tickets, 22% on technical escalations, where agents rewrote nearly every summary. The pre-registered wrong-condition had not fired, but the pre-registered response to a miss ("narrow to the highest-acceptance ticket types") was the one that got taken. Because the 35% floor was on paper before launch, the review was a decision about scope rather than an argument about whether 44% was good.

---

## Related

- [Platform KPIs](./platform-kpis.md) – the internal-platform case: workaround baselines, voluntary vs. mandated adoption, consumer outcomes
- [AI Product Metrics](../evals/metrics/ai-product-metrics.md) – quality, cost, safety, and UX metrics for AI features
- [Ship / No-Ship Decision Framework](../evals/frameworks/ship-decision-framework.md) – turning thresholds into a launch decision
- [LLM Eval Framework](../evals/frameworks/llm-eval-framework.md) – building the rubric a human-performance baseline needs
- [OKR Builder](../templates/okr-builder.md) – converting the success claim into objectives and key results
- [DX Assessment](../templates/dx-assessment.md) – time-to-first-value measurement in detail
- [AI Feature Launch Checklist](../launch/ai-feature-launch-checklist.md) – instrumentation and readiness before Period 0
- Scripts: [survey-sample-size.py](../scripts/survey-sample-size.py), [confidence-interval-calculator.py](../scripts/confidence-interval-calculator.py), [experiment-duration-calculator.py](../scripts/experiment-duration-calculator.py), [retention-curve-analyzer.py](../scripts/retention-curve-analyzer.py), [feature-adoption-trend.py](../scripts/feature-adoption-trend.py), [nps-csat-summary.py](../scripts/nps-csat-summary.py), [okr-tracker.py](../scripts/okr-tracker.py)
