# TrynDraft LLM Strategy: From Scraping to Production

**Last Updated:** 2026-01-26
**Author:** Development Team

---

## Executive Summary

This document outlines TrynDraft's complete LLM strategy, from data collection through fine-tuning to sustainable production deployment. The goal is to transform from expensive pay-per-use APIs to a cost-effective, LoL-specialized AI assistant.

### Current State
- **LLM**: Qwen2.5-72B via HuggingFace (disabled by default)
- **Cost**: ~$0.001 per request (adds up quickly)
- **Quality**: Good general reasoning, but not LoL-specialized
- **Fallback**: Rule-based analysis (free, always available)

### Target State
- **LLM**: Fine-tuned open model (Llama 3, Mistral, or Qwen)
- **Cost**: Fixed infrastructure (~$100-300/month) OR API with caching
- **Quality**: LoL-specialized, accurate meta knowledge, concise responses
- **Reliability**: 99.9% uptime with graceful degradation

---

## Phase 1: Data Scraping (Current Focus)

### What We're Scraping

| Source | Data Type | Purpose | Frequency |
|--------|-----------|---------|-----------|
| MOBAFire | Champion guides | LLM training (strategy text) | Weekly |
| LoLalytics | Win/pick/ban rates | NN training, context | Daily |
| U.GG | Matchup data | Counter/synergy info | Daily |
| Reddit (r/summonerschool) | Strategy discussions | LLM training | Weekly |
| Pro VOD transcripts | Expert analysis | LLM training | After events |

### Scraping Implementation

```python
# Current scraping status
scrapers = {
    'mobafire_guides': 'implemented',      # Basic scraper ready
    'lolalytics_stats': 'implemented',     # Stats scraper ready
    'reddit_discussions': 'planned',       # Next up
    'pro_analysis': 'planned'              # Future
}
```

### Data Volume Targets

| Source | Target Volume | Current |
|--------|---------------|---------|
| MOBAFire guides | 1,000+ champion guides | ~0 |
| LoLalytics stats | All champions × all ranks × 3 patches | ~0 |
| Reddit posts | 10,000+ strategy discussions | ~0 |
| Pro transcripts | 500+ game analyses | ~0 |

### Storage Strategy

```
storage/
├── raw/                    # Unprocessed scraped HTML
│   ├── mobafire/
│   └── lolalytics/
├── processed/              # Cleaned, structured data
│   ├── guides.jsonl        # LLM training format
│   └── stats.parquet       # NN training format
└── training/               # Final training datasets
    ├── llm_finetune.jsonl
    └── nn_features.csv
```

---

## Phase 2: Data Processing & Preparation

### For LLM Fine-Tuning

Convert scraped content into instruction-following format:

```jsonl
{"instruction": "Analyze this draft state", "input": "Blue: Ornn, Viego, Ahri. Red: Jayce, Lee Sin. User is ADC.", "output": "Blue team has strong engage..."}
{"instruction": "Recommend a champion", "input": "Need a jungle pick. Team has Malphite top, Syndra mid. Enemy has Ezreal ADC.", "output": "Consider Jarvan IV..."}
{"instruction": "Explain the matchup", "input": "Darius vs Garen top lane", "output": "Darius has the advantage in extended trades..."}
```

### Processing Pipeline

```python
async def process_for_llm_training():
    """
    Convert raw scraped data to LLM training format
    """
    training_data = []

    # 1. Process MOBAFire guides
    for guide in load_mobafire_guides():
        # Extract strategy sections
        for section in guide.sections:
            training_data.append({
                "instruction": infer_instruction(section),
                "input": extract_context(section),
                "output": clean_text(section.content)
            })

    # 2. Generate synthetic examples from stats
    for matchup in generate_matchup_pairs():
        training_data.append({
            "instruction": "Explain this matchup",
            "input": f"{matchup.champ1} vs {matchup.champ2} in {matchup.role}",
            "output": generate_matchup_explanation(matchup)
        })

    # 3. Process Reddit discussions
    for post in load_reddit_posts():
        if is_high_quality(post):
            training_data.append(format_reddit_qa(post))

    return training_data
```

### Quality Filters

Not all scraped content is useful. Apply filters:

1. **Length filter**: 50-2000 characters (too short = useless, too long = rambling)
2. **Relevance filter**: Must mention LoL concepts (champions, items, objectives)
3. **Recency filter**: Focus on current patch/meta
4. **Quality filter**: Upvotes, author reputation, writing quality

### Target: 50,000+ High-Quality Training Examples

---

## Phase 3: Fine-Tuning Options

### Option A: Fine-Tune on HuggingFace (Easiest)

**Model**: Mistral-7B-Instruct or Llama-3-8B-Instruct
**Platform**: HuggingFace AutoTrain or Transformers
**Cost**: ~$50-100 for training, then hosting costs

```python
# Using HuggingFace AutoTrain
from autotrain.trainers.text_generation import train

train(
    model="mistralai/Mistral-7B-Instruct-v0.2",
    dataset="./training_data.jsonl",
    output_dir="./lol-draft-model",
    epochs=3,
    batch_size=4,
    learning_rate=2e-5,
)
```

**Pros**: Easy, managed infrastructure
**Cons**: Ongoing hosting costs, vendor lock-in

### Option B: Fine-Tune Locally with QLoRA (Best Value)

**Model**: Llama-3-8B or Mistral-7B
**Hardware**: RTX 3090/4090 or cloud GPU
**Cost**: One-time GPU rental (~$20-50) + self-hosting

```python
# Using Unsloth for efficient fine-tuning
from unsloth import FastLanguageModel
from transformers import TrainingArguments
from trl import SFTTrainer

# Load base model with QLoRA (4-bit quantization)
model, tokenizer = FastLanguageModel.from_pretrained(
    model_name="unsloth/Meta-Llama-3-8B-Instruct",
    max_seq_length=2048,
    load_in_4bit=True,
)

# Add LoRA adapters
model = FastLanguageModel.get_peft_model(
    model,
    r=16,
    lora_alpha=16,
    target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
)

# Train
trainer = SFTTrainer(
    model=model,
    tokenizer=tokenizer,
    train_dataset=dataset,
    args=TrainingArguments(
        output_dir="./lol-draft-llama",
        per_device_train_batch_size=4,
        num_train_epochs=3,
        learning_rate=2e-4,
    ),
)
trainer.train()

# Save LoRA weights only (small file, ~100MB)
model.save_pretrained_merged("./lol-draft-model", tokenizer)
```

**Pros**: Full control, one-time training cost, can self-host
**Cons**: Requires technical setup, need hosting infrastructure

### Option C: OpenAI/Anthropic Fine-Tuning (Highest Quality)

**Model**: GPT-3.5-turbo-ft or Claude
**Cost**: ~$100-300 for training, then usage costs

```python
from openai import OpenAI

client = OpenAI()

# Upload training data
file = client.files.create(
    file=open("training_data.jsonl", "rb"),
    purpose="fine-tune"
)

# Create fine-tuning job
job = client.fine_tuning.jobs.create(
    training_file=file.id,
    model="gpt-3.5-turbo-1106",
    hyperparameters={
        "n_epochs": 3,
        "learning_rate_multiplier": 0.5
    }
)
```

**Pros**: Best quality, managed infrastructure
**Cons**: Most expensive, ongoing usage costs

### Recommendation: Start with Option B

1. Fine-tune Llama-3-8B or Mistral-7B with QLoRA
2. Host on Railway/Render ($20-50/month) or your own GPU
3. Fallback to rule-based if LLM is down
4. Graduate to Option A or C if needed for scale

---

## Phase 4: Deployment & Integration

### Hosting Options

| Option | Cost | Latency | Scalability |
|--------|------|---------|-------------|
| Self-hosted GPU (RTX 4090) | $1600 one-time + electricity | 1-2s | Limited |
| Lambda Labs GPU | $0.80/hour (~$600/month) | 1-2s | Good |
| RunPod Serverless | $0.00035/s (~$50/month typical) | 2-3s | Excellent |
| Railway/Render | $25-100/month | 3-5s | Good |
| HuggingFace Inference | Pay-per-request | 2-4s | Excellent |

### Integration Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Frontend (React)                        │
│                    User makes draft action                   │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────┐
│                    Backend (FastAPI)                         │
│                                                              │
│  1. Check Redis cache for identical draft → return cached    │
│  2. Build prompt with draft state + user context             │
│  3. Call LLM service                                         │
│  4. Parse and cache response                                 │
└──────────────────────────┬───────────────────────────────────┘
                           │
            ┌──────────────┼──────────────┐
            │              │              │
            ▼              ▼              ▼
      ┌──────────┐  ┌──────────┐  ┌──────────────┐
      │   Fine-  │  │ HF API   │  │  Rule-Based  │
      │  tuned   │  │ Fallback │  │   Fallback   │
      │  Model   │  │          │  │              │
      └──────────┘  └──────────┘  └──────────────┘
           ↑              ↑              ↑
      Primary        Secondary      Tertiary
      (preferred)    (if primary    (if all
                      fails)         fail)
```

### Caching Strategy (Critical for Cost Control)

```python
import hashlib
from redis import Redis

redis = Redis.from_url(os.getenv('REDIS_URL'))

def get_draft_hash(draft_state: dict) -> str:
    """Generate unique hash for draft state"""
    key = json.dumps({
        'blue_picks': sorted(draft_state.get('blue_picks', [])),
        'red_picks': sorted(draft_state.get('red_picks', [])),
        'bans': sorted(draft_state.get('bans', [])),
        'user_role': draft_state.get('user_role'),
        'phase': draft_state.get('phase')
    }, sort_keys=True)
    return hashlib.sha256(key.encode()).hexdigest()[:16]

async def get_llm_analysis(draft_state: dict) -> str:
    cache_key = f"llm:{get_draft_hash(draft_state)}"

    # Try cache first
    cached = await redis.get(cache_key)
    if cached:
        return cached.decode()

    # Generate new analysis
    analysis = await llm_service.analyze(draft_state)

    # Cache for 30 minutes
    await redis.setex(cache_key, 1800, analysis)

    return analysis
```

**Expected cache hit rate**: 40-60% (many users try similar drafts)

---

## Phase 5: Long-Term Sustainability Analysis

### Cost Projections

| Users/Day | Requests/Day | HF API Cost | Fine-tuned + Self-host |
|-----------|--------------|-------------|------------------------|
| 100 | 500 | $0.50/day | Fixed $50-100/month |
| 1,000 | 5,000 | $5/day (~$150/month) | Fixed $50-100/month |
| 10,000 | 50,000 | $50/day (~$1,500/month) | Fixed $100-300/month |

**Break-even point**: ~1,000 users/day

### Sustainability Strategy

1. **Development (Now)**: Rule-based fallback (free)
2. **Alpha/Beta**: HuggingFace API with aggressive caching
3. **Launch**: Fine-tuned model on RunPod/Railway
4. **Scale**: Self-hosted GPU or dedicated inference service

### Revenue Options (If Needed)

| Model | Description | Estimated Revenue |
|-------|-------------|-------------------|
| Freemium | 5 LLM requests/day free, Pro for unlimited | $5-10/user/month |
| Donations | GitHub Sponsors, Ko-fi | Variable |
| Ads | Non-intrusive banner ads | $2-5 CPM |
| B2B | License to esports orgs | $100-500/org/month |

---

## Do We Need Our Own LLM?

### Short Answer: No, but fine-tuning is recommended

### Analysis

| Approach | Pros | Cons | Recommendation |
|----------|------|------|----------------|
| **API only** (GPT/Claude) | Easy, best quality | Expensive, vendor lock-in | Good for MVP |
| **Fine-tuned open model** | Cheap, customized | Setup effort | **Best balance** |
| **Train from scratch** | Full control | Enormous cost, expertise needed | Not recommended |

### Why NOT train our own model:

1. **Cost**: Training a 7B model from scratch costs $10,000-100,000+
2. **Data**: Need trillions of tokens, we have millions at best
3. **Expertise**: Requires ML research team
4. **Time**: 6-12 months minimum

### Why fine-tuning IS enough:

1. **Base models are excellent**: Llama 3, Mistral, Qwen already understand language
2. **We only need domain expertise**: Add LoL knowledge on top
3. **Efficient**: QLoRA fine-tuning takes hours, not months
4. **Flexible**: Can update with each patch quickly

---

## Implementation Roadmap

### Phase 1: Scraping (Weeks 1-3)
- [ ] Complete MOBAFire guide scraper
- [ ] Complete LoLalytics stats scraper
- [ ] Add Reddit scraping
- [ ] Set up data storage pipeline

### Phase 2: Data Processing (Week 4)
- [ ] Clean and structure scraped data
- [ ] Generate synthetic training examples
- [ ] Create train/validation splits
- [ ] Quality review (manual spot-check)

### Phase 3: Fine-Tuning (Week 5)
- [ ] Set up training environment (Lambda Labs or local GPU)
- [ ] Fine-tune Llama-3-8B with QLoRA
- [ ] Evaluate on test set
- [ ] Iterate on prompt format/hyperparameters

### Phase 4: Deployment (Week 6)
- [ ] Deploy fine-tuned model (RunPod/Railway)
- [ ] Update backend to use new model
- [ ] Add fallback chain (fine-tuned → HF API → rule-based)
- [ ] Implement caching layer

### Phase 5: Monitoring & Iteration (Ongoing)
- [ ] Track response quality (user feedback)
- [ ] Monitor costs and latency
- [ ] Retrain monthly with new data
- [ ] A/B test improvements

---

## Success Metrics

| Metric | Target | How to Measure |
|--------|--------|----------------|
| Response quality | 4+ stars average | User ratings |
| Latency | <3 seconds p95 | Application metrics |
| Cost per request | <$0.001 | Infrastructure costs / requests |
| Availability | 99.9% | Uptime monitoring |
| Cache hit rate | >50% | Redis metrics |

---

## Conclusion

TrynDraft's LLM strategy is achievable and sustainable:

1. **Now**: Use free rule-based fallback during development
2. **After scraping**: Fine-tune an open model (Llama 3 or Mistral)
3. **For production**: Self-host or use serverless inference
4. **Long-term**: Costs stay manageable even at scale

The key insight is that **fine-tuning is enough** - we don't need to train our own LLM from scratch. Modern open models are excellent; we just need to teach them about League of Legends.

---

**Questions?** Open an issue or discussion on GitHub.
