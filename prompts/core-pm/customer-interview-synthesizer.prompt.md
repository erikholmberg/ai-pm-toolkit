# Customer Interview Synthesizer

Extract actionable insights from customer interview transcripts and notes.

## Usage

Paste your interview transcript or notes where indicated.

---

## Single Interview Analysis Prompt

```
You are a user research expert helping me analyze a customer interview.

## Interview Context
- Customer: [CUSTOMER NAME/TYPE - e.g., "Enterprise customer, 500+ employees"]
- Role: [THEIR JOB TITLE/FUNCTION]
- Product Area: [WHAT PART OF THE PRODUCT THEY USE]
- Interview Goal: [WHAT WE WERE TRYING TO LEARN]
- Date: [INTERVIEW DATE]

## Interview Transcript/Notes
---
[PASTE YOUR TRANSCRIPT OR NOTES HERE]
---

## Analysis Instructions

Analyze this interview and provide:

### 1. Key Quotes
Extract 5-7 verbatim quotes that capture important insights. Format as:
> "Quote here" 
> — Context: [When/why they said this]

### 2. Pain Points Identified
List each pain point with:
- **Pain Point:** [Description]
- **Severity:** [Critical/High/Medium/Low]
- **Frequency:** [Daily/Weekly/Monthly/Rarely]
- **Current Workaround:** [How they solve it today]

### 3. Jobs to Be Done
What jobs is this customer trying to accomplish? Format as:
- When [situation], I want to [motivation], so I can [expected outcome]

### 4. Feature Requests / Wishlist
- [Feature] - [Their exact words for why they want it]

### 5. Positive Moments
What do they love? What's working well?

### 6. Competitive Mentions
Did they mention competitors? What did they say?

### 7. Surprising Insights
Anything unexpected that challenges our assumptions?

### 8. Follow-up Questions
Questions we should have asked or should ask next time.

### 9. Recommended Actions
Based on this interview, what should we do?
- Immediate actions
- Things to explore further
- Hypotheses to validate

### 10. One-Line Summary
If I could only remember one thing from this interview, what should it be?
```

---

## Multiple Interview Synthesis Prompt

```
You are a user research expert helping me synthesize insights across multiple customer interviews.

## Research Context
- Research Goal: [WHAT WE WERE TRYING TO LEARN]
- Number of Interviews: [N]
- Customer Segments: [WHO WE TALKED TO]
- Time Period: [WHEN THESE HAPPENED]

## Interview Summaries
---
### Interview 1: [Customer/Role]
[PASTE SUMMARY OR KEY NOTES]

### Interview 2: [Customer/Role]
[PASTE SUMMARY OR KEY NOTES]

### Interview 3: [Customer/Role]
[PASTE SUMMARY OR KEY NOTES]

[ADD MORE AS NEEDED]
---

## Synthesis Instructions

Analyze across all interviews and provide:

### 1. Theme Analysis
Identify recurring themes. For each theme:
- **Theme:** [Name]
- **Frequency:** [Mentioned by X of Y customers]
- **Representative Quotes:** [1-2 quotes]
- **Implication:** [What this means for the product]

### 2. Pain Point Prioritization
| Pain Point | Customers Affected | Severity | Current Solutions | Priority |
|------------|-------------------|----------|-------------------|----------|

### 3. Segment Differences
Are there differences between customer segments? What patterns emerge?

### 4. Opportunity Areas
Based on the research:
1. **Quick Wins:** Low effort, high impact improvements
2. **Strategic Investments:** Larger efforts worth pursuing
3. **Future Exploration:** Ideas to validate further

### 5. Hypotheses to Test
- [Hypothesis 1]: [How we'd validate it]
- [Hypothesis 2]: [How we'd validate it]

### 6. Quotes Library
Organize the most powerful quotes by theme for use in presentations.

### 7. Executive Summary
Write a 3-paragraph summary suitable for sharing with leadership:
- What we learned
- What it means
- What we recommend

### 8. Research Gaps
What questions remain unanswered? What should we explore next?
```

---

## Quick Interview Debrief Prompt

```
I just finished a customer interview. Help me capture the key points before I forget.

## Quick Context
- Customer: [WHO]
- Topic: [WHAT WE DISCUSSED]
- Duration: [HOW LONG]

## My Raw Notes
---
[BRAIN DUMP YOUR NOTES HERE - doesn't have to be clean]
---

## Help me:
1. Identify the 3 most important insights
2. Capture any quotes I should remember (even paraphrased)
3. List follow-up actions
4. Note anything that surprised me
5. Suggest what to explore in the next interview

Keep it brief - I'll do a deeper analysis later.
```

---

## Tips

- **Record with permission** - Transcripts are more reliable than notes
- **Capture quotes verbatim** - User language is powerful in presentations
- **Look for behaviors, not opinions** - What they do matters more than what they say
- **Note non-verbal cues** - Hesitation, excitement, frustration
- **Don't lead the witness** - Ask open questions, let them tell stories
- **Synthesize weekly** - Don't let interviews pile up

