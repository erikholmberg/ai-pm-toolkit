# Explaining AI to Executives

Prompts and frameworks for communicating AI concepts and decisions to leadership.

---

## Executive Translation Prompt

```
You are helping me explain an AI-related topic to executives who are not AI experts.

## Context
- Audience: [EXECUTIVE LEVEL - e.g., VP, C-suite, Board]
- Their background: [TECHNICAL LITERACY LEVEL]
- Their priorities: [WHAT THEY CARE ABOUT - growth, risk, efficiency]
- Time constraint: [HOW LONG I HAVE - 2 min, 5 min, 30 min]

## Topic to Explain
[DESCRIBE THE AI TOPIC, FEATURE, OR DECISION]

## What I Need
Create an executive-ready explanation that:

### 1. The Hook (10 seconds)
Why should they care? Connect to business outcomes.

### 2. The Simple Explanation (30 seconds)
Explain the concept without jargon. Use analogies if helpful.

### 3. The Business Impact (1 minute)
- What does this enable/prevent?
- What's the ROI or risk?
- How does this compare to alternatives?

### 4. The Ask (if any)
What decision or action do you need from them?

### 5. Anticipated Questions
- [Question they might ask]: [Concise answer]
- [Question they might ask]: [Concise answer]

## Style Guidelines
- No jargon (or define it immediately if essential)
- Lead with "so what"
- Use concrete examples
- Quantify when possible
- Be honest about uncertainties
```

---

## Common Topics: Pre-Written Explanations

### What is an LLM?

**For executives:**
> "An LLM is an AI that can read and write like a human. Think of it as a very well-read assistant that's studied the entire internet. It can answer questions, write content, and help with tasks—but it doesn't truly 'understand' like humans do, and it can sometimes make mistakes confidently."

**Key points:**
- It's pattern matching at massive scale
- It can be wrong but sound confident
- It needs human oversight for important decisions

### Why AI Features Take Longer Than Expected

**For executives:**
> "Traditional software is like following a recipe—predictable and testable. AI is more like training a new employee—you can't perfectly predict their performance, and you need time to evaluate and improve. The extra time goes into ensuring quality and safety."

**What takes time:**
- Collecting and cleaning training data
- Evaluating quality (no simple pass/fail test)
- Handling edge cases and failures
- Safety and bias testing

### Why AI Costs Are Uncertain

**For executives:**
> "AI costs depend on usage in ways traditional software doesn't. It's like paying per question answered rather than a flat software license. The more users use it, and the more complex their requests, the higher the cost. We're building monitoring to predict and control this."

### Why AI Can't Guarantee Accuracy

**For executives:**
> "AI makes predictions based on patterns, not rules. Like a weather forecast, it can be highly accurate overall but will sometimes be wrong. For critical decisions, we keep humans in the loop. For routine tasks, the time savings outweigh occasional errors."

---

## Frameworks for Executive Communication

### BLUF: Bottom Line Up Front

```
BOTTOM LINE: [What you need them to know or do]

BACKGROUND: [Brief context - 2-3 sentences max]

DETAILS: [Supporting information, if they want to go deeper]
```

### STAR: Situation, Task, Action, Result

```
SITUATION: [Context and challenge]
TASK: [What needed to be done]
ACTION: [What we did]
RESULT: [Outcome and next steps]
```

### Risk Communication Template

```
RISK: [What could go wrong]
LIKELIHOOD: [High/Medium/Low]
IMPACT: [If it happens]
MITIGATION: [What we're doing about it]
DECISION NEEDED: [If any]
```

---

## Handling Tough Questions

### "Is this AI hype or real?"

> "There's definitely hype in the market, but for our specific use case, we've validated with [data/pilots/customer feedback]. We're being selective about where AI adds real value versus where it's theater."

### "What if the AI makes a mistake?"

> "It will make mistakes—the question is how we handle them. For this feature, [explain human oversight, error handling, rollback capability]. The rate of errors is [X]%, which is [better/comparable to] human performance."

### "How do we know it's not biased?"

> "We've tested across [demographic groups] and found [results]. We have ongoing monitoring in place. We're being transparent about limitations. No system is perfect, but we're actively managing this risk."

### "What's the ROI?"

> "We project [efficiency gain / revenue impact / cost savings] based on [data source]. The investment is [X] with expected payback in [time]. We'll have concrete data after [milestone]."

### "What if a competitor does this first?"

> "There's a first-mover advantage in [specific area], but the sustainable advantage is in [data/integration/quality]. We're prioritizing based on [strategic rationale]."

---

## Tips for Executive Communication

1. **Lead with the punchline** - Don't build up to the point
2. **Use business language** - Revenue, cost, risk, growth—not tokens and epochs
3. **Be honest about uncertainty** - Overconfidence loses trust
4. **Use analogies** - Connect to concepts they know
5. **Anticipate objections** - Address concerns before they're raised
6. **Know when to simplify** - You can always go deeper if asked
7. **Quantify when possible** - Numbers beat adjectives
8. **Have the backup** - Be ready for "how did you calculate that?"

