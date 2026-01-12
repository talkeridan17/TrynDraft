# LLM Integration Strategy for TrynDraft

## Overview
This document outlines how Large Language Models (LLMs) are integrated into TrynDraft to provide strategic draft analysis, explain recommendations, and generate contextual insights.

---

## 1. Use Cases for LLM in TrynDraft

### Primary Use Cases

#### 1.1 Draft Analysis & Explanations
**Input:** Current draft state (picks, bans, user settings)
**Output:** Strategic analysis of composition strengths/weaknesses

```python
# Example prompt
prompt = f"""
You are an expert League of Legends draft analyst. Analyze this draft:

Blue Team: {blue_picks}
Red Team: {red_picks}
Bans: {all_bans}

User plays: {user_role} at {user_rank} rank

Provide a concise analysis covering:
1. Team composition strengths (2-3 sentences)
2. Win conditions (2-3 sentences)
3. Key threats from enemy team (2-3 sentences)
4. Recommended playstyle (1-2 sentences)

Keep response under 150 words.
"""
```

**Expected Output:**
```
Blue Team has a strong engage composition with Leona and Ornn providing
multiple initiation tools. Their team fights excel in extended fights with
Cassiopeia's sustained damage and Graves' tankiness. However, they lack
early game pressure and are vulnerable to poke compositions.

Win Condition: Force team fights mid-game around objectives after Ornn's
item upgrades come online. Use Leona engage to catch isolated targets.

Key Threats: Red team's Nidalee can invade Graves early and deny power
farming. Ezreal's mobility makes him hard to lock down. Janna can disengage
your team fights.

Recommended Playstyle: Play for scaling, avoid early skirmishes. Ward deep
to track Nidalee. Flash engage with Leona when enemy team is grouped for objectives.
```

#### 1.2 Champion Recommendation Explanations
**Input:** NN-generated champion recommendations
**Output:** Why each pick makes sense

```python
prompt = f"""
Explain why {recommended_champion} is a good pick in this situation:

Current draft: {draft_state}
User champion pool: {user_pool}
Enemy team: {enemy_picks}

Provide 2-3 sentences explaining:
- What this pick brings to the team
- How it counters enemy threats
- What the win condition is

Be concise and strategic.
"""
```

#### 1.3 Counter-Pick Advice
**Input:** Enemy just picked a champion
**Output:** Best counter options and how to play the matchup

```python
prompt = f"""
The enemy just picked {enemy_pick} for {role}.

Your champion pool: {user_pool}

Recommend your 3 best counter-picks from your pool and explain:
1. Why it counters (laning phase and team fights)
2. Key trading patterns to win lane
3. Common mistakes to avoid

Format as:
1. [Champion]: [Explanation]
"""
```

#### 1.4 Gameplan Generation
**Input:** Completed draft (all 10 picks + bans)
**Output:** Step-by-step gameplan for the game

```python
prompt = f"""
Generate a gameplan for this completed draft:

Your Team (Blue): {blue_picks}
Enemy Team (Red): {red_picks}

Provide a phase-by-phase gameplan:

Early Game (0-15 min):
- Jungle pathing and gank priorities
- Lane assignments and matchups
- First objective priority

Mid Game (15-25 min):
- Team fight positioning
- Objective control strategy
- Split push vs grouping decision

Late Game (25+ min):
- Win condition execution
- Key cooldowns to track
- Macro decisions (Baron/Elder priority)

Keep each section to 3-4 bullet points.
"""
```

---

## 2. LLM Selection & Comparison

### Option 1: HuggingFace Inference API (Current)

**Model:** Mistral-7B-Instruct-v0.2
**Cost:** Free tier (rate limited) or $0.001 per 1k tokens
**Latency:** 2-4 seconds per request
**Max Context:** 8192 tokens

**Pros:**
- Free tier available for development
- Easy integration (API call)
- Good quality for general tasks

**Cons:**
- Rate limiting on free tier (1-2 req/sec)
- Not specialized for League of Legends
- No fine-tuning control

**Implementation:**
```python
import aiohttp

HF_TOKEN = os.getenv('HF_TOKEN')
API_URL = "https://api-inference.huggingface.co/models/mistralai/Mistral-7B-Instruct-v0.2"

async def generate_llm_response(prompt: str) -> str:
    headers = {"Authorization": f"Bearer {HF_TOKEN}"}

    payload = {
        "inputs": prompt,
        "parameters": {
            "max_new_tokens": 300,
            "temperature": 0.7,
            "top_p": 0.9,
            "return_full_text": False
        }
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(API_URL, headers=headers, json=payload) as resp:
            result = await resp.json()
            return result[0]['generated_text']
```

### Option 2: OpenAI GPT-4 Turbo

**Model:** gpt-4-turbo (gpt-4-1106-preview)
**Cost:** $0.01 per 1k input tokens, $0.03 per 1k output tokens
**Latency:** 1-3 seconds
**Max Context:** 128k tokens

**Pros:**
- Highest quality responses
- Excellent at following instructions
- Strong reasoning capabilities
- Huge context window

**Cons:**
- Expensive at scale ($0.04 per request average)
- External dependency (OpenAI outage affects us)
- Data privacy concerns (sent to OpenAI)

**Cost Estimate:**
- 1000 users/day × 5 requests each = 5000 requests
- 5000 × $0.04 = $200/day = $6000/month

**Implementation:**
```python
from openai import AsyncOpenAI

client = AsyncOpenAI(api_key=os.getenv('OPENAI_API_KEY'))

async def generate_gpt4_response(prompt: str) -> str:
    response = await client.chat.completions.create(
        model="gpt-4-turbo",
        messages=[
            {"role": "system", "content": "You are an expert League of Legends draft analyst."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=300,
        temperature=0.7
    )
    return response.choices[0].message.content
```

### Option 3: Anthropic Claude 3 Haiku

**Model:** claude-3-haiku-20240307
**Cost:** $0.00025 per 1k input tokens, $0.00125 per 1k output tokens
**Latency:** 1-2 seconds
**Max Context:** 200k tokens

**Pros:**
- Very fast and cheap
- Good quality (better than Mistral)
- Huge context window
- Strong safety features

**Cons:**
- Requires Anthropic API key
- Not as good as GPT-4 (but close)

**Cost Estimate:**
- 5000 requests/day × $0.002 = $10/day = $300/month

**Recommendation:** Best balance of cost/quality/speed

**Implementation:**
```python
from anthropic import AsyncAnthropic

client = AsyncAnthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))

async def generate_claude_response(prompt: str) -> str:
    response = await client.messages.create(
        model="claude-3-haiku-20240307",
        max_tokens=300,
        messages=[
            {"role": "user", "content": prompt}
        ]
    )
    return response.content[0].text
```

### Option 4: Self-Hosted Llama 3 8B

**Model:** Meta-Llama-3-8B-Instruct
**Cost:** Fixed infrastructure cost (~$200-500/month for GPU)
**Latency:** 1-2 seconds (with GPU)
**Max Context:** 8192 tokens

**Pros:**
- No per-request cost
- Full control and privacy
- Can fine-tune on LoL data
- Predictable costs

**Cons:**
- Requires GPU infrastructure
- Maintenance overhead
- Need to handle scaling

**Infrastructure:**
- AWS EC2 g4dn.xlarge: ~$0.50/hour = $360/month
- Lambda Labs GPU: ~$0.50/hour = $360/month
- Self-hosted RTX 4090: $1600 one-time + electricity

**Implementation:**
```python
from vllm import AsyncLLMEngine, SamplingParams

# Initialize model (once at startup)
engine = AsyncLLMEngine.from_pretrained(
    "meta-llama/Meta-Llama-3-8B-Instruct",
    tensor_parallel_size=1,
    gpu_memory_utilization=0.9
)

async def generate_llama_response(prompt: str) -> str:
    sampling_params = SamplingParams(
        temperature=0.7,
        max_tokens=300,
        top_p=0.9
    )

    results = await engine.generate(prompt, sampling_params)
    return results[0].outputs[0].text
```

### Recommended Strategy

**Phase 1 (MVP):** HuggingFace Mistral (free tier)
**Phase 2 (Production):** Claude 3 Haiku (cost-effective, high quality)
**Phase 3 (Scale):** Self-hosted Llama 3 8B (fine-tuned on LoL data)

---

## 3. Prompt Engineering

### Prompt Template Structure

```python
class DraftAnalysisPrompt:
    SYSTEM_PROMPT = """
You are an expert League of Legends draft analyst with deep knowledge of:
- Champion matchups and synergies
- Team composition theory (engage, poke, scaling, etc.)
- Win conditions and macro strategy
- Current meta and patch-specific strengths

Provide concise, actionable advice. Focus on strategic insights, not obvious facts.
"""

    DRAFT_ANALYSIS_TEMPLATE = """
Analyze this League of Legends draft:

DRAFT STATE:
- Blue Team: {blue_picks}
- Red Team: {red_picks}
- Bans: {all_bans}
- Current Patch: {patch}

USER CONTEXT:
- Role: {user_role}
- Rank: {user_rank}
- Champion Pool: {user_pool}

PROVIDE:
1. **Team Composition Analysis** (3-4 sentences)
   - Identify comp type (engage, poke, scaling, etc.)
   - Key strengths and weaknesses
   - Power spikes (early/mid/late game)

2. **Win Conditions** (2-3 sentences)
   - How this team wins the game
   - Key objectives to prioritize

3. **Enemy Threats** (2-3 sentences)
   - Biggest threats from enemy team
   - How to neutralize them

4. **Strategic Advice** (2-3 sentences)
   - Recommended playstyle
   - Macro priorities

Keep response under 200 words. Be specific and actionable.
"""

    @classmethod
    def build_analysis_prompt(cls, draft_state: dict, user_context: dict) -> str:
        return cls.DRAFT_ANALYSIS_TEMPLATE.format(
            blue_picks=", ".join(draft_state['blue_picks']),
            red_picks=", ".join(draft_state['red_picks']),
            all_bans=", ".join(draft_state['bans']),
            patch=draft_state.get('patch', '16.1'),
            user_role=user_context['role'],
            user_rank=user_context['rank'],
            user_pool=", ".join(user_context['champion_pool'][:10])  # Top 10
        )
```

### Optimization Techniques

#### 1. Token Reduction
```python
# Bad: Sending full champion names
"Blue team has Aurelion Sol, Kha'Zix, LeBlanc, Miss Fortune, and Thresh"

# Good: Use abbreviations
"Blue: ASol, Kha, LB, MF, Thresh"

# Saves ~30% tokens
```

#### 2. Few-Shot Examples
```python
FEW_SHOT_EXAMPLES = """
Example 1:
Draft: Blue (Ornn, Viego, Ahri, Jinx, Leona) vs Red (Jayce, Nidalee, Zed, Ezreal, Janna)

Analysis:
Blue has a strong team fight composition with multi-layered engage from Ornn and Leona.
Their win condition is forcing mid-game skirmishes around objectives after Jinx gets 2 items.

However, Red's poke composition with Jayce/Nidalee/Ezreal can prevent team fight setups.
Key threat is Zed's split push pressure. Counter by grouping mid, warding flanks, and
taking quick fights before poke wears you down.

---

Now analyze this draft:
{user_draft}
"""
```

#### 3. Response Format Control
```python
prompt = f"""
{draft_details}

Respond ONLY in this format (no extra text):

STRENGTHS: [2-3 key strengths]
WEAKNESSES: [2-3 key weaknesses]
WIN CONDITION: [1-2 sentences]
THREATS: [Top 2 enemy threats]
ADVICE: [2-3 actionable tips]
"""
```

---

## 4. Caching Strategy

### Cache by Draft Hash
```python
import hashlib
from functools import lru_cache

def draft_hash(draft_state: dict) -> str:
    """Generate unique hash for draft state"""
    picks = sorted(draft_state['blue_picks'] + draft_state['red_picks'])
    bans = sorted(draft_state['bans'])
    key = f"{'-'.join(picks)}_{'-'.join(bans)}"
    return hashlib.md5(key.encode()).hexdigest()

@lru_cache(maxsize=1000)
async def get_cached_analysis(draft_hash: str) -> str:
    # Check Redis cache first
    cached = await redis.get(f"llm:analysis:{draft_hash}")
    if cached:
        return cached

    # Generate new analysis
    analysis = await generate_llm_response(prompt)

    # Cache for 30 minutes
    await redis.setex(f"llm:analysis:{draft_hash}", 1800, analysis)

    return analysis
```

**Cache Hit Rate:** 60-70% expected (many users try similar drafts)

### Precomputation for Popular Drafts
```python
async def precompute_popular_drafts():
    """
    Precompute LLM responses for most common draft combinations
    Run this weekly when new patch drops
    """
    # Get top 50 most-played champions
    top_champions = await get_top_champions(limit=50)

    # Generate all reasonable 10-champion combinations (limited)
    # Store in cache

    for combo in generate_draft_combinations(top_champions):
        analysis = await generate_llm_response(combo)
        await cache.set(f"llm:precomputed:{combo.hash}", analysis)
```

---

## 5. Fine-Tuning for League of Legends

### Why Fine-Tune?

**Problems with Base Models:**
- Generic gaming knowledge (not LoL-specific)
- Outdated meta information (trained on old data)
- Verbose responses (need concise, actionable advice)
- Hallucinations (makes up champion abilities)

**Benefits of Fine-Tuning:**
- LoL-specific terminology and meta knowledge
- Concise, structured responses
- Accurate champion abilities and matchup knowledge
- Patch-aware recommendations

### Training Data Collection

```python
training_examples = []

# Source 1: Manual expert annotations
example = {
    "input": "Analyze: Blue (Ornn, Viego, Ahri, Jinx, Leona) vs Red (Jayce, Nidalee, Zed, Ezreal, Janna)",
    "output": """
COMP TYPE: Blue has team fight engage, Red has poke/disengage.

STRENGTHS: Multi-engage from Ornn/Leona. Jinx hypercarry late game. Viego reset potential.

WEAKNESSES: Vulnerable to poke. No answer to Zed split push. Jinx immobile.

WIN CONDITION: Force mid-game fights around Dragon after Jinx 2-item spike.
Use Leona engage when enemy is grouped for objective.

THREATS: Nidalee invades Viego early. Zed can assassinate Jinx. Janna disrupts engage.

ADVICE: Ward deep to track Nidalee. Group mid, don't split. Flash engage when enemy
is setting up poke. Jinx needs frontline protection.
"""
}

# Source 2: Scrape analysis from Reddit, MOBAFire guides
reddit_analysis = scrape_reddit_draft_analysis(subreddit='summonerschool')

# Source 3: Pro game commentary transcripts
pro_analysis = scrape_pro_game_commentary()

# Source 4: User-generated feedback (after deployment)
user_feedback = collect_user_ratings_and_corrections()
```

**Target:** 10k-50k high-quality examples

### Fine-Tuning Process

**Option A: OpenAI Fine-Tuning**
```python
from openai import OpenAI

client = OpenAI()

# Prepare training file
training_data = [
    {"messages": [
        {"role": "system", "content": "You are a League of Legends draft expert."},
        {"role": "user", "content": example["input"]},
        {"role": "assistant", "content": example["output"]}
    ]}
    for example in training_examples
]

# Upload training file
file = client.files.create(
    file=open("training_data.jsonl", "rb"),
    purpose="fine-tune"
)

# Create fine-tuning job
job = client.fine_tuning.jobs.create(
    training_file=file.id,
    model="gpt-3.5-turbo",
    hyperparameters={"n_epochs": 3}
)

# Wait for completion (~1-2 hours for 10k examples)
# Cost: ~$100-200 for 10k examples
```

**Option B: Llama 3 Fine-Tuning (Self-Hosted)**
```python
from unsloth import FastLanguageModel
import torch

# Load base model
model, tokenizer = FastLanguageModel.from_pretrained(
    model_name="unsloth/Meta-Llama-3-8B-Instruct",
    max_seq_length=2048,
    load_in_4bit=True,  # QLoRA for efficiency
)

# Prepare for fine-tuning
model = FastLanguageModel.get_peft_model(
    model,
    r=16,  # LoRA rank
    lora_alpha=16,
    lora_dropout=0.05,
    target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
)

# Train
from datasets import load_dataset

dataset = load_dataset("json", data_files="training_data.json")

from transformers import Trainer, TrainingArguments

trainer = Trainer(
    model=model,
    args=TrainingArguments(
        output_dir="./lol-draft-llama3",
        per_device_train_batch_size=4,
        gradient_accumulation_steps=4,
        num_train_epochs=3,
        learning_rate=2e-4,
        fp16=True,
    ),
    train_dataset=dataset["train"],
)

trainer.train()
model.save_pretrained("lol-draft-llama3-finetuned")
```

**Training Time:** 4-8 hours on single A100 GPU
**Cost:** ~$50-100 (Lambda Labs GPU rental)

---

## 6. Production Architecture

```
┌──────────────────────────────────────┐
│        Frontend (React)              │
│  User completes draft                │
└─────────────┬────────────────────────┘
              │
              │ POST /api/v1/llm/analyze
              ▼
┌──────────────────────────────────────┐
│      Backend API (FastAPI)           │
│  - Validate draft state              │
│  - Check cache (Redis)               │
│  - Rate limit per user               │
└─────────────┬────────────────────────┘
              │
              ├─── Cache Hit? ──────────────┐
              │                             │
              │ NO                          │ YES
              ▼                             ▼
┌──────────────────────────────────────┐  Return
│    LLM Service                       │  Cached
│  - Build prompt                      │  Result
│  - Call HuggingFace/Claude API       │
│  - Parse response                    │
│  - Cache result                      │
└─────────────┬────────────────────────┘
              │
              ▼
┌──────────────────────────────────────┐
│        Response                      │
│  {                                   │
│    "analysis": "...",                │
│    "win_condition": "...",           │
│    "threats": [...],                 │
│    "advice": "..."                   │
│  }                                   │
└──────────────────────────────────────┘
```

### Service Implementation

```python
class LLMService:
    def __init__(self):
        self.client = self._init_client()
        self.cache = Redis.from_url(os.getenv('REDIS_URL'))

    async def analyze_draft(
        self,
        draft_state: Dict,
        user_context: Dict
    ) -> Dict[str, Any]:
        """
        Main entry point for draft analysis
        """
        # Generate cache key
        cache_key = self._generate_cache_key(draft_state)

        # Check cache
        cached = await self.cache.get(cache_key)
        if cached:
            logger.info(f"Cache hit for {cache_key}")
            return json.loads(cached)

        # Generate prompt
        prompt = self._build_prompt(draft_state, user_context)

        # Call LLM
        response = await self._call_llm(prompt)

        # Parse response
        parsed = self._parse_response(response)

        # Cache result (30 minutes)
        await self.cache.setex(
            cache_key,
            1800,
            json.dumps(parsed)
        )

        return parsed

    async def _call_llm(self, prompt: str) -> str:
        """Call LLM with retry logic"""
        max_retries = 3

        for attempt in range(max_retries):
            try:
                response = await self.client.generate(prompt)
                return response

            except RateLimitError:
                if attempt == max_retries - 1:
                    raise
                await asyncio.sleep(2 ** attempt)

            except Exception as e:
                logger.error(f"LLM error: {e}")
                if attempt == max_retries - 1:
                    return self._fallback_response(draft_state)

    def _fallback_response(self, draft_state: Dict) -> str:
        """Rule-based fallback if LLM fails"""
        return generate_rule_based_analysis(draft_state)
```

---

## 7. Cost Optimization

### Techniques

**1. Aggressive Caching**
- Cache identical drafts for 30 min
- Cache similar drafts (fuzzy matching)
- Precompute popular drafts

**2. Response Length Control**
```python
# Enforce strict token limits
"Respond in under 150 words"
"Use bullet points, not paragraphs"
```

**3. Batch Requests**
```python
# If user requests multiple analyses, batch them
prompts = [build_prompt(draft) for draft in drafts]
responses = await llm.generate_batch(prompts)  # Single API call
```

**4. Use Cheaper Models for Simple Tasks**
```python
if draft_phase == 'early':  # Only 2-3 picks
    # Use fast, cheap model (Claude Haiku)
    model = "claude-3-haiku"
elif draft_phase == 'complete':  # All 10 picks
    # Use better model for full analysis (GPT-4)
    model = "gpt-4-turbo"
```

**5. User-Tier Pricing**
```python
# Free tier: 5 LLM requests/day
# Pro tier ($5/month): Unlimited LLM requests
if user.tier == 'free' and user.llm_requests_today >= 5:
    return "Upgrade to Pro for more LLM analyses"
```

---

## 8. Monitoring & Evaluation

### Metrics to Track

```python
# Track LLM usage
metrics.increment('llm.request')
metrics.histogram('llm.latency', duration_ms)
metrics.increment(f'llm.cache.{hit_or_miss}')

# Track user satisfaction
@app.post("/feedback/llm")
async def rate_llm_response(
    analysis_id: str,
    rating: int,  # 1-5 stars
    feedback: Optional[str]
):
    await db.insert(LLMFeedback(
        analysis_id=analysis_id,
        rating=rating,
        feedback=feedback
    ))

    metrics.histogram('llm.user_rating', rating)
```

### Quality Evaluation

```python
async def evaluate_llm_quality():
    """
    Periodically evaluate LLM response quality
    """
    test_cases = load_test_cases()  # Hand-curated examples

    for test in test_cases:
        response = await llm_service.analyze_draft(test.draft)

        # Check for hallucinations
        if contains_invalid_champion(response):
            alert("LLM hallucinating champion names")

        # Check for irrelevant advice
        if not is_relevant_to_draft(response, test.draft):
            alert("LLM giving generic advice")

        # Compare to expert annotation
        similarity = calculate_similarity(response, test.expected)
        metrics.histogram('llm.quality_score', similarity)
```

---

## 9. Future Enhancements

### Multimodal LLM (Vision)
```python
# Upload image of draft screen
# LLM analyzes both draft state and minimap

response = await llm.analyze_with_vision(
    draft_image=screenshot,
    prompt="Analyze this draft from the image"
)
```

### Voice Output (Text-to-Speech)
```python
# Read analysis aloud during champion select
from elevenlabs import generate

audio = generate(
    text=analysis_text,
    voice="professional_analyst"
)
```

### Real-Time Streaming
```python
# Stream LLM response as it generates (faster perceived latency)
async for chunk in llm.stream_response(prompt):
    await websocket.send_text(chunk)
```

---

**Last Updated:** 2026-01-11
**Status:** Active Development (using HuggingFace Mistral)
**Next Step:** Migrate to Claude 3 Haiku for production
