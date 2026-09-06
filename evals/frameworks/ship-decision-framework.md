# Ship / No-Ship Decision Framework for AI Features

How to turn eval results into a shipping decision. The rest of [evals/](../) tells you how to *measure* an AI feature; this tells you what to *do* with the numbers.

Use it when you have eval results in hand and someone has to say yes or no — a go/no-go review, a rollout gate, a model swap, a launch readiness check.

---

## Overview

```
┌──────────────────────────────────────────────────────────────────────┐
│  Gate 0   Is the eval itself trustworthy?                            │
│           ↓ (if no, you have no decision to make — fix the eval)     │
├──────────────────────────────────────────────────────────────────────┤
│  Gate 1   QUALITY        Clears the bar on the mean AND the floor    │
│  Gate 2   SAFETY         No unmitigated critical failure mode        │
│  Gate 3   COST & LATENCY Affordable at projected volume              │
│  Gate 4   COUNTERFACTUAL Beats the honest alternative                │
├──────────────────────────────────────────────────────────────────────┤
│           ↓ all four pass                                            │
│  Pick an EXPOSURE RUNG (not a yes/no)                                │
│           ↓                                                          │
│  Commit to MONITORING + pre-agreed ROLLBACK TRIGGERS                 │
└──────────────────────────────────────────────────────────────────────┘
```

Every gate is a veto. A strong quality score does not buy you a pass on cost, and a cheap feature does not buy you a pass on safety.

---

## Step 1: Set the bar before you see the results

Write down the pass threshold, the test set, and the decision rule *before* the eval runs, and get the decision maker to agree to it in writing.

This is the single highest-leverage habit in the whole framework. Eval numbers are easy to rationalize after the fact — 87% feels like a failure when you hoped for 95% and a triumph when you feared 70%. Pre-registering the bar is what stops the ship decision from being a vibe.

Record it in the **Success Criteria** section of [eval-plan-template.md](../templates/eval-plan-template.md):

| Field | Example |
|-------|---------|
| Primary metric | Task success rate, human-rated |
| Test set | Golden set v3, 400 cases, frozen 2026-08-01 |
| Minimum bar | ≥ 85% overall |
| Floor condition | No segment below 75%; zero critical-safety failures |
| Decision rule | Below minimum → no-ship. Above minimum but floor fails → ship to rung 2 only. |
| Decision maker | [Name] |

If you are already looking at results and no bar was set, say so out loud in the review. Set the bar now, acknowledge it is post-hoc, and pre-register the *next* one.

---

## Step 2: Choose the bar from failure cost, not from a universal number

There is no such thing as "AI features need 90% accuracy." The right bar is set by what a wrong output costs — and that varies by three orders of magnitude across features in the same product.

Score the feature on three questions:

| Question | Cheap failure | Expensive failure |
|----------|---------------|-------------------|
| **Can the user see the error?** | Obvious and self-evident (a bad title suggestion) | Invisible and plausible (a wrong number in a summary) |
| **Can the user undo it?** | One click, no consequence | Irreversible, or the action already reached someone else |
| **Who absorbs it?** | The individual user | A customer, a regulator, or the public |

The more "expensive" answers, the higher the bar:

| Tier | Profile | Typical bar | Human in the loop? |
|------|---------|-------------|--------------------|
| **T1 — Suggestive** | Visible, undoable, private. Autocomplete, brainstorm, draft. | 60–75% useful | No |
| **T2 — Assistive** | User reviews before acting. Draft email, suggested tag, summarized thread. | 80–90% | Review by default |
| **T3 — Autonomous** | Acts without review, but reversible and internal. Auto-routing, auto-labeling. | 90–95%+ | Sampled audit |
| **T4 — Consequential** | Irreversible, external, or regulated. Sends money, publishes, denies a claim, gives medical or legal information. | Case-by-case; usually not a single accuracy number | Mandatory, plus escalation path |

> **T4 features rarely ship on an accuracy threshold at all.** They ship on a bounded-failure argument: a documented list of failure modes, and a control for each one that holds even when the model is wrong.

### The lever most teams miss

**Most AI ship decisions are won by lowering the failure cost, not by raising the accuracy.**

Model work to move quality from 82% to 90% can take a quarter. Moving the feature from T3 to T2 can take a sprint, and it changes the bar the feature has to clear:

| Change | Effect |
|--------|--------|
| Show the source / citation | Error becomes checkable → drops a tier |
| Draft instead of send | Error becomes reviewable → drops a tier |
| Add undo, or a confirmation on the irreversible step | Error becomes recoverable → drops a tier |
| Show confidence, and abstain below a threshold | Trades coverage for precision on the cases you keep |
| Narrow the scope to where the eval is strongest | Raises measured quality without touching the model |

When a feature fails Gate 1, ask "how do we make being wrong cheaper?" before "how do we make it righter?"

---

## Step 3: Read the eval past the average

An aggregate score is the least useful number in the report. Three checks matter more.

### 3a. Floor checks

A 92% overall score is not shippable if the missing 8% is concentrated:

| Check | Question | Ship-blocking pattern |
|-------|----------|----------------------|
| **Worst segment** | Break results down by user type, language, tenant size, input length | One segment far below the mean — you'd be shipping a broken feature to an identifiable group |
| **Worst category** | Break down by failure type, not just pass/fail | Errors clustered in one harm class, however small the count |
| **Tail severity** | Of the failures, how bad is the worst one? | A single catastrophic failure outweighs a long tail of mild ones |

Run the breakdown even when the mean looks great. Use `scripts/bias-fairness-scorecard.py` for segment splits and `scripts/red-team-coverage-tracker.py` to check you probed the categories you claim to have covered.

### 3b. Is the difference real?

Eval sets are small, and small sets are noisy. Approximate 95% margin of error on a pass rate near 90%:

| Test set size | Margin of error |
|---------------|-----------------|
| 50 | ± 8 pts |
| 100 | ± 6 pts |
| 200 | ± 4 pts |
| 500 | ± 3 pts |
| 1,000 | ± 2 pts |

(The margin widens as the rate approaches 50%: a 100-case set at 50% is roughly ± 10 pts.)

So "variant B scored 88% vs. baseline 85% on 100 cases" is not a result — it is noise. Two caveats that cut both ways:

- **Paired comparisons are tighter than they look.** When both variants ran on the *same* test set, only the cases where they disagree carry information. That is a much smaller effective sample and a much narrower interval than comparing two independent scores — a 3-point difference can be real if the variants disagree on only 12 cases and B wins 11 of them.
- **Independent runs are looser than they look.** Different test sets, different judge versions, or different sampling temperatures make a 3-point difference close to meaningless.

Use `scripts/confidence-interval-calculator.py` for the interval and `scripts/ab-test-calculator.py` when the comparison is a live experiment rather than an offline eval.

### 3c. Does the eval predict production?

Offline eval scores are systematically optimistic. Expect the production number to land below the eval number, and ask where the gap comes from:

| Source of gap | How to check before shipping |
|---------------|------------------------------|
| Test set is cleaner than real input | Sample 30 real inputs from logs and run them through |
| Test set is stale | When was it last refreshed against current traffic? |
| Contamination — the cases shaped the prompt | Hold out a set the prompt author never saw |
| Judge is miscalibrated | Spot-check the LLM judge against human labels (`scripts/llm-judge-calibration-checker.py`) |
| No adversarial users in the set | Red-team pass before a public launch |

---

## Step 4: Run the gates

### Gate 0 — Is the eval trustworthy?

Fails if: test set is unrepresentative or stale, the sample is too small to resolve the difference you are acting on, the judge is uncalibrated, or the cases leaked into the prompt. **A failed Gate 0 is not a no-ship — it means you don't yet have a decision to make.** Fix the eval.

### Gate 1 — Quality

| Passes | Fails |
|--------|-------|
| Clears the pre-registered bar for its tier, on the mean **and** every floor check, with an interval that excludes the bar | Below the bar, or a floor check fails, or the difference sits inside the noise |

### Gate 2 — Safety

| Passes | Fails |
|--------|-------|
| Every identified harm category at or below its threshold; no unmitigated critical failure mode; refusal and false-refusal rates within policy | Any critical failure without a control; harm rate above threshold in any category, regardless of the overall rate |

Cross-check against [governance/responsible-ai-checklist.md](../../governance/responsible-ai-checklist.md). Safety is a floor, never an average — "0.3% harmful outputs" is a rate, not a pass.

### Gate 3 — Cost and latency

| Passes | Fails |
|--------|-------|
| Cost per request within budget **at projected launch volume**, not at eval volume; p99 latency within the interaction's tolerance | Unit economics only work at current traffic; p99 breaks the interaction even though p50 looks fine |

Interactive features are judged on p99, not p50 — the median user's experience is not the one that generates the complaint. See `scripts/ai-unit-economics-calculator.py` and `scripts/latency-slo-calculator.py`.

### Gate 4 — Counterfactual

The most-skipped gate. The comparison is not "is the AI good?" but "is it better than what the user does today?"

| Alternative | Question |
|-------------|----------|
| Status quo | Does this beat the manual workflow, honestly measured — including the time users spend checking the AI? |
| A non-AI baseline | Would a rule, a lookup, or a sort get 80% of the value at 5% of the cost? |
| Nothing | Would users be worse off with an unreliable version than with no feature at all? |

A feature that is 85% accurate but costs users more time in verification than it saves fails Gate 4 with a great Gate 1 score.

---

## Step 5: Ship to a rung, not to a yes

"Ship / no-ship" is a false binary. The real output is *how much exposure the evidence supports*.

| Rung | Exposure | Evidence needed |
|------|----------|-----------------|
| **0. Internal** | Team dogfood | Gate 0 only — you're still learning what to measure |
| **1. Design partners** | Opt-in, named users, human review, direct feedback channel | Gates 0–2, quality bar may be provisional |
| **2. Limited beta** | Opt-in or small %, behind a flag, fallback path live | Gates 0–4 pass; floor checks may have known gaps you've disclosed |
| **3. Staged rollout** | Default-on for a segment, ramping % | Gates 0–4 clean, monitoring live, rollback tested |
| **4. General availability** | Everyone | Rung 3 held steady for a defined period with production data confirming the eval |

Two rules keep the ladder honest:

1. **Each rung has an exit criterion written before you climb onto it.** "Ramp to 25% after seven days if quality holds above 85% and escalations stay under X/week" — not "ramp when it feels stable."
2. **Production data supersedes eval data at rung 2.** Once real traffic is flowing, the eval's job shifts from predicting quality to catching regressions.

### When a gate fails

No-ship is a routing decision, not a kill:

| Failure | Usual response |
|---------|----------------|
| Gate 0 | Fix the eval, re-run. No decision yet. |
| Gate 1, close to the bar | Narrow scope to where it's strong, or drop a tier via UX (Step 2) |
| Gate 1, far from the bar | Back to model/prompt/retrieval work with a specific target |
| Gate 2 | Ship only with the control in place, or not at all — never "monitor it in production" |
| Gate 3 | Route by complexity, cache, or use a smaller model on the cheap path |
| Gate 4 | Reconsider whether the feature should exist. This is a real answer. |

---

## Step 6: Buy the decision with monitoring

An offline eval predicts launch-day quality. It says nothing about week six — the model gets updated under you, inputs shift, and users find edges your test set never had.

Ship decisions above rung 1 should come with three commitments:

1. **Production quality signal.** A metric you can read weekly without running a manual eval — acceptance rate, edit rate, regeneration rate, thumbs-down rate. See [../metrics/ai-product-metrics.md](../metrics/ai-product-metrics.md).
2. **A regression gate.** The golden set runs on every prompt or model change, not just at launch (`evals/scripts/regression-runner.py`, `scripts/eval-run-diff.py`).
3. **Pre-agreed rollback triggers.** Numeric, written down before launch, in [launch/ai-feature-launch-checklist.md](../../launch/ai-feature-launch-checklist.md) terms.

If nobody will own the weekly read, that is a reason to ship to a lower rung.

---

## Step 7: Write the decision down

```markdown
## Ship Decision: [FEATURE NAME]

**Date:** [DATE]
**Decision owner:** [NAME]
**Decision:** [SHIP TO RUNG N / NO-SHIP — ROUTE TO X]

### Feature tier
[T1–T4] because [visibility / reversibility / blast radius]

### Pre-registered bar
- Primary metric: [metric] ≥ [threshold]
- Floor conditions: [segment / category floors]
- Set on: [date, before or after results — say which]

### Eval results
| Gate | Result | Pass? |
|------|--------|-------|
| 0. Eval trustworthy | [test set, size, judge calibration] | |
| 1. Quality | [mean, interval, worst segment, worst category] | |
| 2. Safety | [per-category rates, unmitigated failure modes] | |
| 3. Cost & latency | [cost/req at projected volume, p99] | |
| 4. Counterfactual | [vs. status quo / non-AI baseline] | |

### Known gaps
[What the eval did not cover, and why we're accepting that]

### Exit criteria for this rung
[What must be true, and for how long, before the next rung]

### Rollback triggers
- [Metric] worse than [threshold] → immediate rollback
- [Metric] worse than [threshold] → review within 24h

### Monitoring owner
[Name], reviewing [metric] [cadence]
```

Log it with `scripts/decision-log.py` so the reasoning is findable when someone asks in six months why this shipped.

---

## Worked example

**Feature:** auto-generated summaries of customer support threads, shown to agents.

| Step | Finding |
|------|---------|
| Tier | T2 — agent reads the summary before acting, but errors are plausible and hard to spot. Bar set at 85% factual accuracy, no segment below 75%. |
| Eval | 300 cases. 89% overall — clears the bar, interval ± 4 pts, so the margin is real. |
| Floor check | Threads over 20 messages: **71%**. That's 18% of real traffic and it fails the floor. |
| Gate 3 | $0.011/summary at 40k/day = $160/day. Within budget. p99 2.4s, acceptable for a non-blocking panel. |
| Gate 4 | Agents currently skim the thread — roughly 45s. Summary saves ~30s when right, costs ~60s when wrong and caught. Net positive at 89%, net negative below ~70%. |
| **Decision** | Not GA. Two options: (a) rung 2 beta for all threads with the accuracy gap disclosed, or (b) **ship to rung 3 for threads under 20 messages only**, which is 82% of traffic and evaluates at 93%. |
| **Chose** | (b). Scope narrowing beat model work: it shipped value to most traffic in a week, and long-thread summarization became its own eval with its own bar. |

Note what did the work here: the floor check, the Gate 4 arithmetic that turned "89%" into a break-even point, and scoping rather than tuning.

---

## Pitfalls to avoid

### 1. Setting the bar after seeing the number
The most common failure. Whatever you scored becomes the bar. Pre-register.

### 2. Shipping on the mean
A great average with a broken segment is a feature that is broken for real, identifiable people. Always cut the data.

### 3. Treating a demo as evidence
Ten impressive outputs tell you the ceiling, not the rate. Ceilings don't ship; rates do.

### 4. Confusing "the model improved" with "the product is ready"
A 6-point quality gain is a good week for the ML team and still no answer to Gates 2, 3, and 4.

### 5. Letting safety be an average
Gate 2 is a floor per harm category. Overall rates hide exactly the thing you're screening for.

### 6. Deferring the hard call to "we'll monitor it"
Monitoring catches regressions from a known-good state. It is not a substitute for a gate you couldn't pass.

### 7. Skipping the counterfactual
The most expensive AI features to maintain are the ones that were never better than the boring alternative.

### 8. One-shot gating
Passing at launch is not passing forever. Without a regression gate, quality decays silently on the next prompt edit or model update.

---

## Quick reference checklist

Before the go/no-go meeting:

- [ ] Feature tier assigned (T1–T4), with reasoning
- [ ] Bar pre-registered, in writing, with a named decision maker
- [ ] Gate 0: test set representative, current, uncontaminated, large enough; judge calibrated
- [ ] Gate 1: mean clears the bar, interval excludes it, floor checks run by segment and category
- [ ] Gate 2: per-category safety rates, every critical failure mode has a control
- [ ] Gate 3: cost at projected volume, p99 latency, not p50
- [ ] Gate 4: compared against status quo and a non-AI baseline
- [ ] Considered lowering failure cost via UX before raising accuracy via model work
- [ ] Target rung chosen, with written exit criteria for the next one
- [ ] Rollback triggers numeric and pre-agreed
- [ ] Monitoring owner and cadence named
- [ ] Decision recorded with rationale and known gaps

---

## Related

- [eval-plan-template.md](../templates/eval-plan-template.md) — pre-register the bar here
- [llm-eval-framework.md](./llm-eval-framework.md) — how to produce the scores this framework consumes
- [../metrics/ai-product-metrics.md](../metrics/ai-product-metrics.md) — metric definitions and target-setting
- [agents/evaluation/agent-evaluation-framework.md](../../agents/evaluation/agent-evaluation-framework.md) — gating agentic features, where failures compound across steps
- [launch/ai-feature-launch-checklist.md](../../launch/ai-feature-launch-checklist.md) — the launch mechanics once the decision is yes
- [governance/responsible-ai-checklist.md](../../governance/responsible-ai-checklist.md) — Gate 2 inputs
- [frameworks/ai-feature-deprecation-playbook.md](../../frameworks/ai-feature-deprecation-playbook.md) — when the answer is "this shouldn't exist anymore"
