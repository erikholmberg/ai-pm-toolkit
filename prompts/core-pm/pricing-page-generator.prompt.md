# Pricing Page Generator

Generate pricing page copy, tier descriptions, and feature comparison tables for AI-powered products.

## Usage

Replace the `[PLACEHOLDERS]` with your specific information.

---

## Pricing Page Copy

```
You are a product marketing expert specializing in SaaS and AI product pricing pages. Help me create compelling pricing page copy that converts.

## Context
- Product: [PRODUCT NAME]
- Product Type: [e.g., "AI writing assistant", "LLM API platform", "ML monitoring tool"]
- Target Audience: [e.g., "Developers", "Enterprise teams", "SMB marketers"]
- Pricing Model: [e.g., "Per seat", "Usage-based", "Tiered", "Credits/tokens"]
- Number of Tiers: [e.g., 3 — Free, Pro, Enterprise]
- Key Competitors: [COMPETITOR 1, COMPETITOR 2]
- Primary Differentiator: [WHAT SETS YOU APART]

## Tier Details
For each tier, provide what you know:
- Tier 1: [NAME, PRICE, KEY FEATURES/LIMITS]
- Tier 2: [NAME, PRICE, KEY FEATURES/LIMITS]
- Tier 3: [NAME, PRICE, KEY FEATURES/LIMITS]
- Add-ons (if any): [DESCRIPTION, PRICE]

## AI-Specific Considerations
- Token/credit limits per tier: [IF APPLICABLE]
- Model access by tier: [e.g., "Free gets GPT-3.5, Pro gets GPT-4"]
- Rate limits: [IF APPLICABLE]
- Data retention/privacy by tier: [IF APPLICABLE]

---

## Instructions

Generate pricing page content with:

### 1. Page Headline
3 options — lead with value, not price. Emphasize the outcome the AI delivers.

### 2. Subheadline
One sentence explaining who it's for and the core value proposition.

### 3. Tier Cards
For each tier:
- **Tier Name:** Short, memorable name
- **Tagline:** One-liner for who this tier is for (e.g., "For individuals getting started")
- **Price Display:** How to present the price (monthly, annual, usage-based)
- **CTA Button Text:** Action-oriented (e.g., "Start Free", "Upgrade to Pro")
- **Feature List:** 6-10 features, most important first
- **Highlighted Feature:** The one feature that makes this tier worth it

### 4. Feature Comparison Table
Full matrix of features × tiers with:
- ✓ / ✗ for boolean features
- Specific limits for quantitative features (e.g., "100 requests/day", "Unlimited")
- Group features by category (e.g., Core, AI/ML, Collaboration, Security, Support)

### 5. FAQ Section
5-7 common pricing questions and answers, including:
- "What happens if I exceed my limits?"
- "Can I switch plans?"
- "Is there a free trial?"
- Any AI-specific questions (model availability, data handling, etc.)

### 6. Social Proof
Suggest placement for:
- Customer logos
- Usage stats ("X million requests processed")
- Testimonial themes to source

### 7. Conversion Copy
- Urgency/scarcity elements (if appropriate)
- Annual vs. monthly savings callout
- Enterprise CTA ("Talk to Sales" section copy)

---

## Guidelines
- Lead with outcomes, not technical specs
- Make the recommended tier visually obvious
- Use specific numbers over vague language ("3x faster" vs. "much faster")
- Address AI-specific concerns (data privacy, model accuracy, rate limits)
- Price anchoring: present the highest tier first or highlight the middle tier
- Avoid jargon in the Free/starter tier; allow more technical language in higher tiers
```

---

## Usage-Based Pricing Calculator Copy

```
Help me create copy for an interactive pricing calculator on our pricing page. Many AI products use usage-based pricing and customers need to estimate their costs.

## Context
- Product: [PRODUCT NAME]
- Pricing Dimensions: [e.g., "API calls", "Tokens", "Minutes processed", "Documents"]
- Price per Unit: [e.g., "$0.002 per 1K tokens", "$0.10 per API call"]
- Volume Discounts: [IF APPLICABLE — e.g., "First 10K free, then $X"]
- Minimum Commitment: [IF APPLICABLE]

## Instructions

Generate copy for a pricing calculator section that includes:

### 1. Calculator Section Header
- Headline: Inviting, not intimidating
- Description: Explain what the calculator does in one sentence

### 2. Input Labels & Helper Text
For each pricing dimension:
- Clear label (avoid jargon)
- Helper text explaining the unit
- Suggested default values for typical use cases
- Example scenarios: "A small team typically uses X per month"

### 3. Output Display Copy
- Monthly estimate label and format
- Annual savings callout
- "This is an estimate" disclaimer language
- CTA below the result ("Start with this plan" or "Talk to us for custom pricing")

### 4. Use Case Presets
3-4 preset scenarios users can click:
- Starter/Hobbyist
- Growing Team
- Scale/Enterprise
Each with a short description and pre-filled values

### 5. Cost Optimization Tips
2-3 tips for reducing costs, shown alongside the calculator:
- e.g., "Use prompt caching to reduce token usage by up to 40%"
- e.g., "Batch requests to take advantage of volume discounts"

Keep the tone helpful and transparent. Never make pricing feel hidden or confusing.
```

---

## Pricing Tier Naming

```
I need help naming pricing tiers for my AI product. Good tier names communicate value level and target audience at a glance.

## Context
- Product: [PRODUCT NAME]
- Product Category: [e.g., "Developer tool", "Enterprise SaaS", "Consumer AI"]
- Number of Tiers: [NUMBER]
- Tier Positioning: [DESCRIBE EACH TIER'S TARGET USER IN ONE SENTENCE]
- Brand Personality: [e.g., "Technical and precise", "Friendly and approachable", "Premium and enterprise"]

## Instructions

Generate 3 naming options for my pricing tiers. For each option:

1. **Theme Name** — What unifying concept ties the tier names together
2. **Tier Names** — The actual name for each tier
3. **Why It Works** — Brief rationale

### Guidelines
- Tier names should clearly imply a progression (small → big, simple → powerful)
- Avoid names that make the lowest tier feel inferior
- Consider how the name sounds in sales calls ("You're on our ___ plan")
- For AI products, consider names that reference intelligence, capability, or scale
- Stay consistent with your brand personality

### Also provide:
- 2-3 tier name anti-patterns to avoid (e.g., names that confuse, overlap, or alienate)
```

---

## Tips

- **Anchor with the recommended tier** - Most SaaS products want users on the middle tier; make it visually dominant
- **AI pricing is hard** - Usage-based pricing is powerful but confusing; invest in a calculator and clear examples
- **Show per-seat and per-usage costs separately** - Don't force users to do math
- **Address model access clearly** - If different tiers get different AI models, explain the quality difference simply
- **Localize pricing** - Different regions expect different price points and payment methods
- **Update regularly** - AI costs drop fast; revisit pricing quarterly

