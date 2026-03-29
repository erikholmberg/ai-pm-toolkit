# Daily AI PM Workflow

How to structure your day as an AI Product Manager using AI tools.

### Toolkit map (this repo)

Goal-based routing to scripts, prompts, templates, and MCP servers: [docs/tool-picker.md](../docs/tool-picker.md).

| Daily moment | Start here |
|--------------|------------|
| Health, incidents, SLOs | [scripts/README.md](../scripts/README.md) (Incidents, SLO), [incidents/](../incidents/) |
| Triage Jira / Slack / GitHub | MCP servers in [mcps/README.md](../mcps/README.md); Jira/Slack/GitHub prompts under [prompts/core-pm/](../prompts/README.md) |
| PRDs, roadmap, stakeholder updates | [prompts/core-pm/](../prompts/README.md), [templates/](../templates/) |
| Product or AI quality metrics | [evals/](../evals/), Braintrust/LangSmith MCP in [mcps/TOOLS.md](../mcps/TOOLS.md) |

---

## Morning Routine (30 min)

### 1. Check AI Feature Health (10 min)

**What to review:**
- Quality metrics dashboard
- Error rates and incidents
- User feedback from overnight
- Cost tracking

**With AI Assistant:**
```
"Summarize any alerts or anomalies in our AI feature metrics from the last 24 hours. 
Flag anything that needs my attention today."
```

### 2. Triage & Prioritize (10 min)

**Review:**
- New support tickets related to AI features
- Slack messages and emails
- Updated Jira tickets

**With AI Assistant:**
```
"Review these support tickets and categorize them by:
1. AI quality issues
2. Feature requests
3. Bugs
4. Questions
Prioritize the AI quality issues."
```

### 3. Set Day's Focus (10 min)

**Decide:**
- Top 3 priorities for today
- Any blockers to resolve
- Meetings to prepare for

**With AI Assistant:**
```
"Based on my calendar and these priorities, help me block time for:
- [Priority 1]
- [Priority 2]
- [Priority 3]
What should I prepare for my [meeting name] at [time]?"
```

---

## Deep Work Blocks

### PRD Writing

**AI-Assisted Flow:**
1. Start with problem statement
2. Use AI to generate initial structure
3. Refine and add your insights
4. Use AI for user story generation
5. Review and edit for voice

**Prompt:**
```
"Help me write a PRD for [feature]. Start with an outline based on:
- Problem: [description]
- Users: [who]
- Success metric: [what we're optimizing]"
```

### Data Analysis

**AI-Assisted Flow:**
1. Define the question
2. AI helps with query/code
3. Review and iterate
4. AI helps summarize findings
5. You add interpretation and recommendations

**Prompt:**
```
"I want to analyze [metric] by [dimension] over [time period].
Help me write the SQL/Python to extract and visualize this.
Then help me summarize the key insights."
```

### Competitive Research

**AI-Assisted Flow:**
1. Define research questions
2. AI conducts initial research
3. You validate and dig deeper
4. AI synthesizes findings
5. You add strategic implications

**Prompt:**
```
"Research [competitor]'s approach to [topic]. 
Cover their product capabilities, pricing, and recent changes.
Summarize implications for our product strategy."
```

---

## Meeting Efficiency

### Pre-Meeting Prep (5 min before)

**Prompt:**
```
"Help me prepare for my meeting about [topic]:
1. Key points I should make
2. Questions I should ask
3. Potential objections and responses
4. Decision I need to get"
```

### Real-Time Meeting Support

**If taking notes:**
```
"Summarize these meeting notes:
- Key decisions made
- Action items (with owners)
- Open questions
- Next steps"
```

### Post-Meeting Follow-up (5 min after)

**Prompt:**
```
"Draft a follow-up email for my [meeting name] covering:
- Summary of what we decided
- Action items and owners
- Next meeting/checkpoint"
```

---

## Stakeholder Communication

### Status Updates

**Prompt:**
```
"Help me write a status update for [stakeholder] on [project]:
- Current status: [details]
- Progress: [what got done]
- Blockers: [issues]
- Next steps: [plans]
Format for [email / Slack / meeting]."
```

### Explaining AI Concepts

**Prompt:**
```
"Help me explain [AI concept] to [audience type].
They care about [priorities].
I have [time constraint].
Make it concrete and business-focused."
```

---

## End of Day (15 min)

### 1. Update Tracking (5 min)

**With AI Assistant:**
```
"Based on today's activities, help me update:
- Jira tickets that progressed
- Documentation that needs updating
- Stakeholders who need updates"
```

### 2. Tomorrow's Prep (5 min)

**Review:**
- Tomorrow's calendar
- Outstanding items
- Prep needed

**Prompt:**
```
"Looking at tomorrow's calendar, what should I prepare today?
Flag any meetings that need significant prep."
```

### 3. Capture Learnings (5 min)

**Quick reflection:**
- What worked well?
- What AI outputs needed heavy editing?
- What prompts to improve?

---

## Weekly Rhythms

### Monday: Planning
- Review week's priorities
- Check AI feature health trends
- Align with team

### Wednesday: Check-in
- Mid-week progress review
- Adjust priorities if needed
- Prep for end-of-week

### Friday: Review & Reflect
- Week summary
- Metrics review
- Plan next week's focus

---

## AI Productivity Tips

### Effective Prompting Habits

1. **Be specific** about format and length
2. **Provide context** about audience and purpose
3. **Iterate** don't accept first output
4. **Add your voice** after AI drafts
5. **Save good prompts** for reuse

### What to Delegate to AI

✅ **Good for AI:**
- First drafts
- Summarization
- Research synthesis
- Data formatting
- Brainstorming options
- Routine communications

❌ **Keep for Yourself:**
- Final decisions
- Sensitive communications
- Strategic judgment
- Stakeholder relationships
- Creative direction

### Building AI Habits

**Week 1:** Use AI for one type of task (e.g., meeting prep)
**Week 2:** Add another task type (e.g., documentation)
**Week 3:** Develop reusable prompts
**Week 4:** Refine and expand

---

## Recommended Tools

| Task | Tool |
|------|------|
| Writing/Analysis | Claude, GPT-4 |
| Coding | Cursor, Copilot |
| Meeting Notes | Otter, Granola |
| Research | Perplexity |
| Documentation | Notion AI, Coda |

