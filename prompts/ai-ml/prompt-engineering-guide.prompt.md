# Prompt Engineering Guide

A practical guide to writing effective prompts for LLMs—essential knowledge for AI PMs.

## Usage

Reference this guide when designing LLM-powered features, reviewing prompt implementations, or helping your dev community.

---

## Prompt Improvement Assistant

```
You are a prompt engineering expert. Help me improve this prompt.

## Current Prompt
---
[PASTE YOUR CURRENT PROMPT]
---

## Context
- LLM Being Used: [e.g., GPT-4, Claude, Llama]
- Use Case: [WHAT THIS PROMPT IS FOR]
- Current Issues: [WHAT'S NOT WORKING WELL]

## Analyze and improve:

### 1. Diagnosis
- What's wrong with the current prompt?
- Why is it producing suboptimal results?

### 2. Improved Prompt
[Provide the improved version]

### 3. What Changed
- [Change 1]: Why it helps
- [Change 2]: Why it helps

### 4. Testing Suggestions
- Test cases to validate improvement
- Edge cases to check
```

---

## Prompt Design from Scratch

```
Help me design a prompt for a new LLM feature.

## Feature Requirements
- Task: [WHAT THE LLM NEEDS TO DO]
- Input: [WHAT THE USER PROVIDES]
- Output: [WHAT WE NEED BACK]
- Constraints: [ANY LIMITATIONS OR REQUIREMENTS]

## User Context
- Who uses this: [USER PERSONA]
- How they'll use it: [USAGE CONTEXT]
- Error tolerance: [HOW BAD IS A BAD OUTPUT]

## Generate:

### System Prompt
[The system/instruction prompt]

### User Prompt Template
[Template with {placeholders}]

### Example Inputs & Expected Outputs
3 example input/output pairs

### Edge Cases
- [Edge case 1]: How to handle
- [Edge case 2]: How to handle

### Failure Modes
- What could go wrong?
- How to detect and handle failures

### Evaluation Criteria
How to measure if this prompt is working well
```

---

## Prompt Engineering Principles Reference

```
Give me a refresher on prompt engineering best practices for [USE CASE].

Cover:

### 1. Structure
- How to organize the prompt
- When to use sections/headers
- Optimal prompt length

### 2. Instructions
- How specific to be
- Positive vs negative instructions
- Handling ambiguity

### 3. Context
- What context to include
- How to format context
- Context window considerations

### 4. Examples (Few-shot)
- When to use examples
- How many examples
- How to select good examples

### 5. Output Format
- Specifying format (JSON, markdown, etc.)
- Structured vs freeform
- Parsing considerations

### 6. Constraints
- Setting boundaries
- Content policies
- Length limits

### 7. Common Pitfalls
- Mistakes to avoid
- Signs of a bad prompt
```

---

## Prompt Patterns Library

### Chain of Thought
```
Think through this step by step:

1. First, [IDENTIFY/ANALYZE] the [KEY ELEMENT]
2. Then, [CONSIDER/EVALUATE] the [FACTORS]
3. Based on that, [DETERMINE/DECIDE] the [CONCLUSION]
4. Finally, [PROVIDE/FORMAT] the [OUTPUT]

Show your reasoning at each step.
```

### Role Assignment
```
You are a [SPECIFIC ROLE] with expertise in [DOMAIN]. 

Your communication style is [STYLE DESCRIPTION].

When responding, you should:
- [BEHAVIOR 1]
- [BEHAVIOR 2]
- [BEHAVIOR 3]
```

### Output Format Control
```
Respond in the following JSON format:
{
  "field1": "description of what goes here",
  "field2": ["list", "of", "items"],
  "field3": {
    "nested": "object structure"
  }
}

Do not include any text outside the JSON.
```

### Constrained Generation
```
Generate a [THING] that:
- MUST: [REQUIREMENT 1]
- MUST: [REQUIREMENT 2]
- MUST NOT: [CONSTRAINT 1]
- SHOULD: [PREFERENCE 1]
- MAY: [OPTIONAL 1]
```

### Self-Critique
```
After generating your response:
1. Review it for [CRITERIA]
2. Identify any weaknesses or errors
3. Provide an improved version

Format:
## Initial Response
[Response]

## Self-Critique
[What could be better]

## Improved Response
[Better version]
```

### Multi-Perspective
```
Analyze [TOPIC] from multiple perspectives:

1. **[Perspective A]:** [Analysis]
2. **[Perspective B]:** [Analysis]
3. **[Perspective C]:** [Analysis]

Then provide a balanced synthesis.
```

### Iterative Refinement
```
I'll provide feedback on your outputs. With each iteration:
1. Acknowledge the feedback
2. Explain how you'll address it
3. Provide an improved version

Start with your first attempt at [TASK].
```

---

## Prompt Testing Checklist

```
Help me create a test plan for this prompt.

## Prompt
[THE PROMPT TO TEST]

## Generate test cases for:

### Happy Path
- Normal inputs that should work well

### Edge Cases
- Boundary conditions
- Unusual but valid inputs
- Empty/minimal inputs
- Maximum-length inputs

### Adversarial Inputs
- Prompt injection attempts
- Conflicting instructions
- Attempts to bypass constraints

### Consistency Tests
- Same input multiple times
- Semantically similar inputs

### Format Validation
- Does output match expected format?
- Can it be parsed reliably?

### Quality Metrics
- How to score output quality
- Acceptable thresholds
```

---

## Tips for AI PMs

- **Prompts are code** - Version control them, test them, review them
- **Small changes matter** - Single words can dramatically change output
- **Test at scale** - One good output doesn't mean it works
- **Temperature tuning** - Lower for consistency, higher for creativity
- **Document your prompts** - Future you will forget why you wrote it that way
- **Build evaluation sets** - You can't improve what you don't measure
- **Watch for drift** - Model updates can break working prompts

