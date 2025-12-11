# Agent Design Patterns

Common patterns for building AI agents, explained for Product Managers.

---

## Why Patterns Matter

Understanding agent patterns helps you:
1. **Communicate with engineers** - Speak the same language
2. **Make design decisions** - Choose the right approach
3. **Anticipate tradeoffs** - Know what to expect
4. **Debug issues** - Understand why agents fail

---

## Core Patterns

### 1. ReAct (Reasoning + Acting)

**What it is:** The agent thinks step-by-step, then takes an action, then observes the result, and repeats.

**Flow:**
```
Thought → Action → Observation → Thought → Action → ...
```

**Example:**
```
Thought: I need to find the pricing for Datadog. I should search the web.
Action: search_web("Datadog pricing 2024")
Observation: Found pages about Datadog pricing...
Thought: I found the pricing page. Now I need to extract the tier information.
Action: read_page("https://datadog.com/pricing")
Observation: Infrastructure Monitoring: $15/host/month...
Thought: I have the pricing info. I can now summarize it.
Action: respond("Datadog pricing includes...")
```

**When to use:**
- Complex tasks requiring multiple steps
- When transparency into agent reasoning is important
- When tools need to be selected dynamically

**Tradeoffs:**
- ✅ Interpretable - can see the reasoning
- ✅ Flexible - can handle varied tasks
- ❌ Slower - multiple LLM calls
- ❌ Can loop - may get stuck in reasoning cycles

---

### 2. Chain of Thought (CoT)

**What it is:** Prompting the model to think step-by-step before answering.

**Example Prompt:**
```
Think through this step by step:
1. First, understand the question
2. Then, gather relevant information
3. Next, analyze the options
4. Finally, provide your recommendation

Question: Should we prioritize feature A or feature B?
```

**When to use:**
- Complex reasoning tasks
- When you want to see the logic
- Multi-step problems

**Tradeoffs:**
- ✅ Improves accuracy on complex tasks
- ✅ Provides transparency
- ❌ Uses more tokens
- ❌ Can lead to verbose outputs

---

### 3. Tool Use / Function Calling

**What it is:** The agent can call external functions/APIs to take actions.

**Example:**
```json
{
  "function": "create_jira_ticket",
  "arguments": {
    "project": "PLATFORM",
    "title": "Implement SSO",
    "type": "Story"
  }
}
```

**Tool Types:**
- **Information retrieval** - Search, database queries
- **Actions** - Create tickets, send emails
- **Computation** - Run calculations, code execution
- **External APIs** - Third-party integrations

**When to use:**
- Agent needs to interact with external systems
- Tasks require real-world data
- Actions need to be taken

**Tradeoffs:**
- ✅ Extends capabilities dramatically
- ✅ Grounds responses in real data
- ❌ Adds latency (API calls)
- ❌ Introduces failure points
- ❌ Security considerations (what can agent access?)

---

### 4. Retrieval-Augmented Generation (RAG)

**What it is:** Retrieve relevant context from a knowledge base, then generate a response.

**Flow:**
```
Query → Retrieve relevant docs → Add to context → Generate response
```

**When to use:**
- Agent needs access to private/current data
- Reduces hallucination on factual questions
- Knowledge exceeds context window

**Tradeoffs:**
- ✅ Grounds responses in real data
- ✅ Handles large knowledge bases
- ✅ Reduces hallucination
- ❌ Quality depends on retrieval quality
- ❌ Adds latency
- ❌ May miss relevant context

---

### 5. Planning Agents

**What it is:** Agent creates a plan before executing, then follows the plan.

**Flow:**
```
Task → Create plan → Execute step 1 → Execute step 2 → ... → Complete
```

**Example Plan:**
```
Goal: Write a competitive analysis of Datadog

Plan:
1. Research Datadog's product offerings
2. Research Datadog's pricing
3. Research customer reviews
4. Research recent announcements
5. Synthesize into analysis document
6. Create comparison table
```

**When to use:**
- Complex multi-step tasks
- Tasks requiring coordination
- When you want to review the plan before execution

**Tradeoffs:**
- ✅ Structured approach to complex tasks
- ✅ Plan can be reviewed/modified
- ❌ Plans can be wrong or suboptimal
- ❌ Inflexible if situation changes

---

### 6. Self-Reflection / Self-Critique

**What it is:** Agent evaluates its own output and improves it.

**Flow:**
```
Generate → Critique → Improve → (repeat) → Final output
```

**Example:**
```
Initial output: [First draft]
Critique: "This is missing competitive context and specific metrics."
Improved output: [Better draft with additions]
```

**When to use:**
- High-stakes outputs
- Quality is critical
- Time allows for iteration

**Tradeoffs:**
- ✅ Improves output quality
- ✅ Catches errors
- ❌ Increases latency and cost
- ❌ May over-iterate

---

### 7. Multi-Agent Systems

**What it is:** Multiple specialized agents collaborate on a task.

**Example:**
```
Researcher Agent → finds information
Analyst Agent → interprets data
Writer Agent → creates document
Reviewer Agent → checks quality
```

**When to use:**
- Very complex tasks
- When specialization helps
- When different "perspectives" are valuable

**Tradeoffs:**
- ✅ Specialization improves quality
- ✅ Can parallelize work
- ❌ Complex orchestration
- ❌ Agents may conflict
- ❌ Higher cost

---

## Combining Patterns

Real agents often combine patterns:

**Research Agent Example:**
- **ReAct** for overall reasoning loop
- **Tool use** for web search and page reading
- **RAG** for accessing internal knowledge base
- **Self-reflection** for improving output quality

---

## Pattern Selection Guide

| Task Type | Recommended Pattern |
|-----------|---------------------|
| Simple Q&A | Basic prompting |
| Complex reasoning | Chain of Thought |
| Multi-step tasks | ReAct or Planning |
| Needs external data | RAG or Tool Use |
| Needs to take actions | Tool Use |
| High-quality writing | Self-Reflection |
| Very complex projects | Multi-Agent |

---

## Questions to Ask Your Team

When reviewing agent designs:

1. **What pattern are we using?** - Should match task complexity
2. **How do we handle failures?** - Each step can fail
3. **What's the latency budget?** - Patterns have different costs
4. **How do we evaluate quality?** - Each pattern needs different evals
5. **What's the cost per request?** - More steps = more cost
6. **Can users see the reasoning?** - Transparency requirements

