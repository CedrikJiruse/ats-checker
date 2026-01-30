# ATS Checker Provider Presets Guide

This guide explains the three preset configurations available in the ATS Checker: **Budget**, **Balanced**, and **Quality**. Each preset optimizes the balance between cost and quality for different user needs.

---

## Quick Comparison Table

| Aspect | Budget | Balanced | Quality |
|--------|--------|----------|---------|
| **Monthly Cost** | FREE-$10 | $20-50 | $100-250 |
| **Cost per 100 Resumes** | FREE-$1 | $5-10 | $20-50 |
| **Quality** | Good | Excellent | Maximum |
| **Speed** | Medium | Fast | Medium |
| **Best For** | Testing, learning | Most users (RECOMMENDED) | Executive, competitive roles |
| **Recommended** | ⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |

---

## Preset Details

### 1. BUDGET Preset 💰
**Cost: FREE or $0.50-1 per 100 resumes**

#### Configuration
```
Enhancer:       Gemini Flash (free tier available)
Job Summarizer: Gemini Flash (free tier available)
Scorer:         Groq Llama (completely free)
Reviser:        Gemini Flash (free tier available)
```

#### Costs Breakdown
- **Gemini**: $0 (free tier: 60 req/min, 2M req/day)
- **Groq**: $0 (completely free tier)
- **Total**: FREE with free tiers, or ~$0.075 per 1M input tokens if paid

#### Pros ✓
- Zero cost with free tiers (perfect for students/testing)
- Gemini Flash is surprisingly capable
- Groq Llama is completely free for scoring
- Good for batch processing with time flexibility

#### Cons ✗
- Lower output quality than paid models
- Rate limits on free tiers (can't process 1000s simultaneously)
- Gemini Flash sometimes less detailed than GPT-4o
- Free tier limits: 2M requests/day (still quite generous)

#### Best For
- ✓ Students and educators
- ✓ Personal projects and experimentation
- ✓ Learning how the tool works
- ✓ Development and testing
- ✓ Budget-conscious users
- ✓ Batch processing with time flexibility

#### How to Activate
```
In ATS Checker → Option 5 (AI Model Configuration)
→ Option 2 (Load Provider Profile)
→ Choose "Budget Profile"
```

---

### 2. BALANCED Preset ⚖️ **RECOMMENDED**
**Cost: $5-10 per 100 resumes**

#### Configuration
```
Enhancer:       OpenAI GPT-4o-mini
Job Summarizer: OpenAI GPT-4o-mini
Scorer:         Groq Llama (free!)
Reviser:        OpenAI GPT-4o-mini
```

#### Costs Breakdown
- **OpenAI GPT-4o-mini**: $0.15 input / $0.60 output per 1M tokens
- **Groq**: $0 (completely free)
- **Typical per resume**: $0.05-0.10 (depends on resume length)
- **100 resumes**: ~$5-10
- **1000 resumes**: ~$50-100

#### Pros ✓
- Excellent value - best ROI
- GPT-4o-mini is surprisingly capable (nearly as good as GPT-4o)
- Scoring is completely FREE (uses Groq)
- Fast processing
- Significantly better quality than Budget preset
- Minimal cost (~$0.05-0.10 per resume)

#### Cons ✗
- Requires OPENAI_API_KEY
- Not quite as high-quality as Quality preset
- Small cost per resume (though worth it)

#### Best For
- ✓ **Job seekers and career changers** (recommended)
- ✓ Professional resume optimization
- ✓ Multiple rounds of revision
- ✓ Users who want quality without breaking the bank
- ✓ **START HERE** if unsure

#### Pricing Example
```
Processing 10 resumes for 5 different jobs:
50 total processing runs × $0.08 per resume = $4-5

That's:
- Less than a cup of coffee
- Tremendous value for career impact
- ROI: Potentially thousands more in salary
```

#### How to Activate
```
In ATS Checker → Option 5 (AI Model Configuration)
→ Option 2 (Load Provider Profile)
→ Choose "Balanced Profile" (RECOMMENDED)
```

---

### 3. QUALITY Preset 🏆
**Cost: $20-50 per 100 resumes**

#### Configuration
```
Enhancer:       OpenAI GPT-4o (most capable)
Job Summarizer: Anthropic Claude 3.5 Sonnet (best for analysis)
Scorer:         Groq Llama (free!)
Reviser:        OpenAI GPT-4o (highest quality)
```

#### Costs Breakdown
- **OpenAI GPT-4o**: $2.50 input / $10 output per 1M tokens
- **Anthropic Claude 3.5 Sonnet**: $3 input / $15 output per 1M tokens
- **Groq**: $0 (completely free)
- **Typical per resume**: $0.20-0.50
- **100 resumes**: $20-50
- **1000 resumes**: $200-500

#### Pros ✓
- Maximum quality available
- GPT-4o is the most capable language model (as of Jan 2026)
- Claude 3.5 Sonnet excels at structured analysis (perfect for job summaries)
- Highest likelihood of successful resume enhancement
- Best for competitive markets
- Still uses free Groq for scoring (no waste)

#### Cons ✗
- Highest cost of all presets
- Requires 2 API keys: OPENAI_API_KEY + ANTHROPIC_API_KEY
- Cost per resume (~$0.20-0.50) may not be justified for all users
- Slightly slower than GPT-4o-mini

#### Best For
- ✓ **Executive positions** (C-level, director, VP roles)
- ✓ **Highly competitive job markets**
- ✓ **When resume quality is critical to your success**
- ✓ Users targeting high-paying positions ($150k+)
- ✓ Career change situations where positioning is crucial
- ✓ Industries with tough ATS systems (finance, tech, pharma)

#### Cost Analysis
```
For a $200,000/year position:
Cost of Quality preset (100 resumes): $25-50
Potential salary difference: $5,000-20,000

ROI: 100x-400x return on investment! 🚀
```

#### How to Activate
```
In ATS Checker → Option 5 (AI Model Configuration)
→ Option 2 (Load Provider Profile)
→ Choose "Quality Profile"
```

---

## Decision Guide: Which Preset Should You Choose?

### Choose BUDGET if...
- [ ] You're a student or just learning
- [ ] You're testing the tool
- [ ] You have zero budget for APIs
- [ ] You're comfortable with rate limits
- [ ] You can wait for batch processing

**Recommendation**: Use for initial testing only. Upgrade for real job applications.

---

### Choose BALANCED if... ⭐ RECOMMENDED
- [ ] You're actively job hunting
- [ ] You want good quality without high cost
- [ ] You're applying to multiple positions
- [ ] You can afford $5-20/month
- [ ] You want the best value for money
- [ ] You're unsure which preset to choose

**Recommendation**: **START HERE**. This is the best choice for 95% of users.

**What $10/month gets you:**
- 100+ resume processing runs
- High quality output competitive with humans
- Multiple rounds of revision and optimization
- Professional-grade resumes

---

### Choose QUALITY if...
- [ ] You're targeting executive positions
- [ ] You're in a highly competitive market
- [ ] The position pays $150k+
- [ ] Your resume quality is critical to success
- [ ] You're making a major career change
- [ ] You can afford $100-250/month

**Recommendation**: Worth it for high-stakes opportunities.

**What $50/month gets you:**
- 500+ high-quality resume processing runs
- Best-in-class models for every task
- Maximum likelihood of standing out
- Peace of mind knowing you have the best

---

## Cost Comparison by Use Case

### Scenario: Applying to 20 similar jobs
```
Budget Preset:
- 20 resumes × 1 job each = 20 runs
- Cost: FREE (with free tiers)
- Quality: Good

Balanced Preset:
- 20 resumes × 1 job each = 20 runs
- Cost: $1-2
- Quality: Excellent ⭐

Quality Preset:
- 20 resumes × 1 job each = 20 runs
- Cost: $4-10
- Quality: Maximum
```

### Scenario: Intensive job search (20 different jobs)
```
Budget Preset:
- 20 jobs × 5 tailored versions = 100 runs
- Cost: FREE-$1
- Quality: Good
- Time: Days (rate limits)

Balanced Preset:
- 20 jobs × 5 tailored versions = 100 runs
- Cost: $5-10
- Quality: Excellent ⭐⭐⭐⭐⭐
- Time: Hours

Quality Preset:
- 20 jobs × 5 tailored versions = 100 runs
- Cost: $20-50
- Quality: Maximum
- Time: Hours
```

---

## How to Switch Presets

### In the Interactive Menu
```
1. Run: python main.py
2. Select: Option 5 "AI Model Configuration"
3. Select: Option 2 "Load Provider Profile"
4. Choose: Budget, Balanced, or Quality
5. Done! Your configuration is saved.
```

### Switching Later
You can switch presets anytime:
- No permanent changes
- Configurations are saved to your config file
- Switch back anytime

---

## API Key Requirements

### Budget Preset
```
Required:
- GEMINI_API_KEY (get free key at: https://ai.google.dev/)

Optional:
- GROQ_API_KEY (completely free at: https://console.groq.com/)
```

### Balanced Preset
```
Required:
- OPENAI_API_KEY (get at: https://platform.openai.com/api-keys)

Optional:
- GROQ_API_KEY (completely free at: https://console.groq.com/)
  → Highly recommended (makes scoring free)
```

### Quality Preset
```
Required:
- OPENAI_API_KEY (get at: https://platform.openai.com/api-keys)
- ANTHROPIC_API_KEY (get at: https://console.anthropic.com/)

Optional:
- GROQ_API_KEY (completely free at: https://console.groq.com/)
  → Highly recommended (makes scoring free)
```

---

## FAQ

### Q: Can I change presets after starting?
**A:** Yes! Switch anytime from the menu (Option 5 → Option 2). Future processing uses the new preset.

### Q: What if I only have one API key?
**A:** Stick with Budget preset (Gemini only) or wait until you can get additional keys.

### Q: Which preset saves the most money?
**A:** Budget preset (free). But Balanced has the best **value** (cost vs quality).

### Q: Can I get better quality than Quality preset?
**A:** Not with the current models. These are the best available as of January 2026.

### Q: Does Balanced preset really use free Groq for scoring?
**A:** Yes! Groq has a completely free tier. Only Enhancer and Reviser cost money in Balanced preset.

### Q: How long does processing take?
**A:**
- Budget: ~5-10 seconds per resume (sometimes slower due to rate limits)
- Balanced: ~3-5 seconds per resume
- Quality: ~5-8 seconds per resume (slightly slower but better quality)

### Q: Is the cost split between all models or per model?
**A:** Token costs are per model. So:
- Balanced: Pay for GPT-4o-mini usage only (Groq is free)
- Quality: Pay for GPT-4o + Claude Sonnet usage (Groq is free)

---

## Recommendations Summary

| User Type | Preset | Why |
|-----------|--------|-----|
| Student | Budget | Free, good for learning |
| Job Seeker (typical) | **Balanced** | Best value, excellent quality, minimal cost |
| Career Changer | **Balanced** → Quality | Start with Balanced, upgrade if needed |
| Executive | Quality | Worth the cost for high-stakes positions |
| Bulk Processing (1000s) | **Balanced** | Cost-effective at scale |
| Budget-Conscious | Budget | Free tier available |
| Quality-Obsessed | Quality | Best models available |

---

## Getting Started

### Step 1: Set Up API Keys
```
At minimum (for Balanced preset):
1. Get OPENAI_API_KEY from https://platform.openai.com/
2. Get GROQ_API_KEY from https://console.groq.com/ (free)
3. Set environment variables (see MULTI_PROVIDER_SETUP.md)
```

### Step 2: Load a Preset
```
Run: python main.py
Select: Option 5 → Option 2
Choose: Balanced (recommended)
```

### Step 3: Start Processing
```
Select: Option 1 (Process Resumes)
Your resumes will be optimized with your chosen preset!
```

---

## Support

For more details on setting up API keys, see: `docs/MULTI_PROVIDER_SETUP.md`

For detailed provider comparisons, see: `README.md` in the project root

---

**Last Updated**: January 2026
**Models Included**: GPT-4o, GPT-4o-mini, Claude 3.5 Sonnet/Haiku, Gemini Flash/Pro, Llama 3.3
