# Neural Network Architecture for Draft Recommendations

## Executive Summary
This document outlines the neural network architecture for TrynDraft's draft recommendation system. The NN will complement the LLM by providing fast, data-driven pick/ban suggestions based on millions of historical games.

---

## 1. Problem Statement

### What We're Predicting
1. **Champion Pick Recommendation**: Given current draft state, predict best champion to pick
2. **Win Probability**: Predict win rate for each team based on current composition
3. **Counter-Pick Strength**: Score how well each champion counters enemy picks
4. **Synergy Score**: Rate team composition synergy (1-10)

### Input Features
- **Draft State**: Current bans (10 champions), current picks (0-10 champions)
- **Champion Pool**: User's champion pool with proficiency ratings
- **Meta Context**: Current patch, rank, region
- **Champion Stats**: Win rate, pick rate, ban rate per role
- **Matchup Data**: Historical win rates vs specific champions

---

## 2. Architecture Design

### Option A: Transformer-Based Architecture (Recommended)

**Why Transformers?**
- Excellent at sequence modeling (draft is a sequence of picks/bans)
- Self-attention captures champion interactions naturally
- Handles variable-length inputs (different draft states)
- State-of-the-art for recommendation systems

**Architecture:**
```
Input Layer (Draft State Encoding)
    ↓
Champion Embedding Layer (170 champions → 128-dim vectors)
    ↓
Positional Encoding (draft order matters)
    ↓
Transformer Encoder Blocks (4 layers, 8 heads)
    ↓
Global Context Vector (pooling)
    ↓
Multi-Task Output Heads:
    ├─ Pick Recommendation Head (softmax over available champions)
    ├─ Win Probability Head (sigmoid, 0-1)
    ├─ Synergy Score Head (regression, 0-10)
    └─ Counter Strength Head (softmax per enemy champion)
```

**Model Size:**
- Parameters: ~15-20M (manageable for CPU inference)
- Input: Variable length (1-20 champions)
- Output: 170-dim probability distribution (one per champion)

### Option B: Graph Neural Network (GNN)

**Why GNNs?**
- Draft is inherently a graph (champion relationships)
- Edges represent synergies/counters
- Natural fit for meta-game modeling

**Architecture:**
```
Graph Construction:
    - Nodes: Champions (features: stats, role, class)
    - Edges: Synergy/counter relationships (weighted)

GNN Layers:
    ↓
Graph Convolution (3 layers)
    ↓
Node Aggregation (attention pooling)
    ↓
Team Composition Vectors (Blue, Red)
    ↓
Comparison Layer (concat + FC)
    ↓
Output Predictions
```

**Pros:** Interpretable, captures domain knowledge
**Cons:** Requires manual graph construction, harder to train

### Option C: Hybrid Approach (Best of Both)

**Combine transformer with GNN:**
1. **Transformer** for sequence modeling (draft order)
2. **GNN** for champion relationship encoding
3. **Cross-attention** to merge both representations

---

## 3. Training Data Pipeline

### Data Collection

#### Source 1: Riot API (Official Match History)
```python
# Fetch ranked games from Riot API
async def fetch_ranked_games(region: str, tier: str, count: int):
    """
    Pull ranked SoloQ games from Riot API
    - Requires Riot API key (free 20 req/sec)
    - 100 games/request
    - Focus on Diamond+ for quality data
    """
    games = await riot_api.get_match_history(
        region=region,
        tier=tier,
        queue_type='RANKED_SOLO_5x5',
        count=count
    )
    return parse_games(games)
```

**Target:** 1 million ranked games (Diamond+) across last 3 patches

#### Source 2: Pro Match Data (LoL Esports API)
```python
async def fetch_pro_drafts():
    """
    Scrape professional drafts from:
    - lolesports.com API
    - LCS, LEC, LCK, LPL tournaments
    - Includes draft order, side selection
    """
    return await scrape_pro_matches(leagues=['LCS', 'LEC', 'LCK', 'LPL'])
```

**Target:** 50k pro drafts (higher quality, meta-defining)

#### Source 3: User-Generated Drafts
```python
async def collect_user_drafts():
    """
    Use drafts created in TrynDraft tool as training data
    - Labels: user ratings, comments
    - Feedback loop: improve model with real usage
    """
    return await db.query(Draft).filter(Draft.completed == True)
```

**Target:** 10k+ user drafts (grows over time)

### Data Processing

**Feature Engineering:**
```python
class DraftFeatureExtractor:
    def extract_features(self, draft: Draft) -> torch.Tensor:
        features = {
            # Champion IDs (one-hot or embeddings)
            'blue_picks': [champ_to_id(c) for c in draft.blue_picks],
            'red_picks': [champ_to_id(c) for c in draft.red_picks],
            'blue_bans': [champ_to_id(c) for c in draft.blue_bans],
            'red_bans': [champ_to_id(c) for c in draft.red_bans],

            # Meta context
            'patch': patch_to_id(draft.patch),
            'rank': rank_to_id(draft.rank),

            # Champion stats (from scraped data)
            'champion_winrates': self.get_winrates(draft.patch),
            'champion_pickrates': self.get_pickrates(draft.patch),

            # Team composition features
            'blue_damage_types': self.analyze_damage(draft.blue_picks),
            'blue_cc_score': self.calculate_cc(draft.blue_picks),
            'blue_tankiness': self.calculate_tankiness(draft.blue_picks),

            # Same for red team
            # ...
        }
        return self.encode_features(features)
```

**Labels (What We're Predicting):**
```python
labels = {
    'winner': 'BLUE' or 'RED',  # Classification
    'game_duration': 1850,  # Regression (seconds)
    'blue_gold_advantage_15min': 2500,  # Early game strength
    'mvp_champion': 'Ahri',  # Most impactful pick
}
```

### Data Augmentation

**Technique 1: Side Swapping**
```python
def augment_by_side_swap(draft):
    """
    Swap blue/red sides to double training data
    Important: Win rate adjustments (blue has ~52% win rate)
    """
    return Draft(
        blue_picks=draft.red_picks,
        red_picks=draft.blue_picks,
        winner='RED' if draft.winner == 'BLUE' else 'BLUE'
    )
```

**Technique 2: Partial Draft Completion**
```python
def augment_by_partial_drafts(draft):
    """
    Generate training samples from intermediate draft states
    - After 5 bans (predict next pick)
    - After 1st rotation (predict 2nd rotation)
    - Increases training samples by 10x
    """
    samples = []
    for i in range(1, len(draft.picks)):
        partial = draft[:i]
        label = draft[i]  # Next pick
        samples.append((partial, label))
    return samples
```

**Technique 3: Champion Substitution**
```python
def augment_by_champion_substitution(draft):
    """
    Replace similar champions to teach role equivalence
    - Swap Ahri ↔ Syndra (mid lane mages)
    - Swap Lee Sin ↔ Elise (early game junglers)
    """
    similar_champions = get_similar_champions()
    # Create variations by swapping
    return create_variations(draft, similar_champions)
```

---

## 4. Training Strategy

### Phase 1: Pre-Training (Offline)
```python
# Train on historical data (1M+ games)
# Objective: Learn general draft patterns

model = DraftTransformer(
    vocab_size=170,  # Number of champions
    d_model=128,
    nhead=8,
    num_layers=4
)

optimizer = AdamW(model.parameters(), lr=1e-4)
criterion = CrossEntropyLoss()

for epoch in range(50):
    for batch in dataloader:
        # Forward pass
        predictions = model(batch['draft_state'])
        loss = criterion(predictions, batch['next_pick'])

        # Backward pass
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()
```

**Training Time:** ~8-12 hours on single GPU (RTX 3090)

### Phase 2: Fine-Tuning (Per-Patch)
```python
# Fine-tune on latest patch data
# Objective: Adapt to meta changes

for new_patch in ['16.1', '16.2', '16.3']:
    # Load pre-trained model
    model.load_state_dict(torch.load('base_model.pt'))

    # Fine-tune on new patch data
    patch_data = load_patch_data(new_patch)
    fine_tune(model, patch_data, epochs=5)

    # Save patch-specific model
    torch.save(model.state_dict(), f'model_patch_{new_patch}.pt')
```

**Training Time:** ~1-2 hours per patch

### Phase 3: Online Learning (User Feedback)
```python
# Continuously improve with user interactions
# Objective: Learn from real tool usage

@app.post("/feedback/pick")
async def record_pick_feedback(
    draft_id: str,
    recommended_pick: str,
    actual_pick: str,
    user_rating: int  # 1-5 stars
):
    """
    User feedback: "Model suggested Ahri, I picked Syndra, it worked!"
    Use this to refine recommendations
    """
    await db.insert(UserFeedback(
        draft_id=draft_id,
        recommended=recommended_pick,
        actual=actual_pick,
        rating=user_rating
    ))

    # Trigger incremental training every 1000 feedbacks
    if await count_new_feedback() >= 1000:
        await trigger_incremental_training()
```

---

## 5. Model Evaluation

### Metrics

**1. Pick Accuracy (Top-K)**
```python
def evaluate_pick_accuracy(model, test_data):
    """
    How often is the correct pick in model's top-K recommendations?
    """
    top1_accuracy = 0
    top3_accuracy = 0
    top5_accuracy = 0

    for draft in test_data:
        predictions = model.predict(draft.partial_state)
        actual_pick = draft.next_pick

        if actual_pick == predictions[0]:
            top1_accuracy += 1
        if actual_pick in predictions[:3]:
            top3_accuracy += 1
        if actual_pick in predictions[:5]:
            top5_accuracy += 1

    return {
        'top1': top1_accuracy / len(test_data),
        'top3': top3_accuracy / len(test_data),
        'top5': top5_accuracy / len(test_data),
    }
```

**Target:** Top-1: 25%, Top-3: 50%, Top-5: 70%

**2. Win Probability Calibration**
```python
def evaluate_win_probability(model, test_data):
    """
    Are predicted win probabilities accurate?
    E.g., of all games predicted as 60% blue win, do 60% actually win?
    """
    from sklearn.metrics import brier_score_loss

    predictions = [model.predict_win_prob(d) for d in test_data]
    actuals = [1 if d.winner == 'BLUE' else 0 for d in test_data]

    return {
        'brier_score': brier_score_loss(actuals, predictions),
        'calibration_plot': plot_calibration(predictions, actuals)
    }
```

**Target:** Brier score < 0.15

**3. Synergy/Counter Understanding**
```python
def test_domain_knowledge(model):
    """
    Does model understand game mechanics?
    """
    tests = [
        # Test 1: Should recommend tanky engage vs poke comp
        {
            'enemy': ['Jayce', 'Nidalee', 'Lux', 'Ezreal', 'Karma'],
            'expected_attributes': ['engage', 'tankiness', 'hard_engage'],
        },

        # Test 2: Should recommend scaling vs early game comp
        {
            'enemy': ['Renekton', 'Lee Sin', 'Talon', 'Draven', 'Leona'],
            'expected_attributes': ['scaling', 'waveclear', 'disengage'],
        },
    ]

    for test in tests:
        recommendation = model.recommend(enemy=test['enemy'])
        attributes = analyze_recommendation(recommendation)
        assert any(attr in attributes for attr in test['expected_attributes'])
```

### Comparison with Baselines

**Baseline 1: Random Selection**
- Pick accuracy: ~0.6% (1 in 170)

**Baseline 2: Most Popular Pick**
- Always suggest highest win rate champion
- Pick accuracy: ~5%

**Baseline 3: Rule-Based System**
- Use hardcoded counter-pick rules
- Pick accuracy: ~15%

**Our NN Target:**
- Pick accuracy: 25-35% (5-7x better than rule-based)

---

## 6. Inference & Production Deployment

### Model Serving

```python
class DraftRecommendationService:
    def __init__(self):
        self.model = self.load_model()
        self.model.eval()  # Inference mode

    def load_model(self):
        # Load latest model from S3 or local cache
        model_path = self.get_model_path()
        model = DraftTransformer.load_from_checkpoint(model_path)
        return model.to('cpu')  # CPU inference for cost

    @torch.no_grad()
    async def get_recommendations(
        self,
        draft_state: Dict,
        user_pool: List[str],
        top_k: int = 5
    ) -> List[Tuple[str, float]]:
        """
        Get top-K champion recommendations with confidence scores
        """
        # Encode draft state
        encoded = self.encode_draft(draft_state)

        # Run inference
        logits = self.model(encoded)
        probs = torch.softmax(logits, dim=-1)

        # Filter by user champion pool
        if user_pool:
            probs = self.filter_by_pool(probs, user_pool)

        # Get top-K
        top_probs, top_indices = torch.topk(probs, k=top_k)

        recommendations = [
            (self.id_to_champion(idx), prob.item())
            for idx, prob in zip(top_indices, top_probs)
        ]

        return recommendations
```

**Inference Time:** ~50-100ms per request (acceptable for real-time)

### Caching Strategy

```python
from functools import lru_cache

class CachedRecommendationService:
    @lru_cache(maxsize=10000)
    def get_cached_recommendations(self, draft_hash: str):
        """
        Cache recommendations for identical draft states
        draft_hash = hash(sorted(blue_picks + red_picks + bans))
        """
        return self.model.get_recommendations(draft_hash)
```

**Cache Hit Rate Target:** 60-70% (many users try similar drafts)

### Model Updates

```python
# Automated model deployment pipeline

# 1. Train new model on updated data
new_model = train_model(latest_data)

# 2. Evaluate on test set
metrics = evaluate_model(new_model, test_data)

# 3. A/B test: serve 10% of users with new model
if metrics['top3_accuracy'] > current_metrics['top3_accuracy']:
    # 4. Gradual rollout
    deploy_canary(new_model, percentage=10)
    time.sleep(3600)  # Monitor for 1 hour

    if no_errors_detected():
        deploy_full(new_model)
        archive_old_model()
```

---

## 7. Integration with LLM

### Hybrid Recommendation System

**NN provides:** Fast, numerical recommendations (top 5 picks)
**LLM provides:** Explanations, strategic advice, context

```python
async def get_hybrid_recommendations(draft_state):
    # Step 1: NN generates top-5 picks (fast, 100ms)
    nn_picks = await nn_service.get_recommendations(draft_state, top_k=5)

    # Step 2: LLM explains why these picks are good (slow, 2-3s)
    explanations = await llm_service.explain_recommendations(
        draft_state=draft_state,
        recommended_picks=nn_picks
    )

    # Step 3: Combine and return
    return [
        {
            'champion': pick,
            'confidence': score,
            'explanation': explanations[pick],
            'source': 'neural_network'
        }
        for pick, score in nn_picks
    ]
```

**User Experience:**
1. User sees NN recommendations instantly (100ms)
2. LLM explanations load in background (3s)
3. Both displayed together in UI

---

## 8. Implementation Roadmap

### Phase 1: Data Collection (2-3 weeks)
- [ ] Set up Riot API scraping (1M games)
- [ ] Scrape pro match data (50k drafts)
- [ ] Build data processing pipeline
- [ ] Create training dataset (preprocessed, augmented)

### Phase 2: Model Development (3-4 weeks)
- [ ] Implement transformer architecture
- [ ] Set up training pipeline (GPU)
- [ ] Train initial model (v1.0)
- [ ] Evaluate on test set
- [ ] Iterate on architecture

### Phase 3: Integration (1-2 weeks)
- [ ] Build inference API endpoint
- [ ] Integrate with frontend
- [ ] Add caching layer
- [ ] Deploy to production

### Phase 4: Monitoring & Iteration (Ongoing)
- [ ] Collect user feedback
- [ ] A/B test model versions
- [ ] Retrain monthly with new data
- [ ] Fine-tune per patch

---

## 9. Hardware Requirements

### Training
- **GPU**: NVIDIA RTX 3090 or A100 (24GB VRAM)
- **RAM**: 64GB+
- **Storage**: 500GB SSD (training data)
- **Time**: 8-12 hours per full training run

**Alternatives:**
- AWS SageMaker (ml.g4dn.xlarge): ~$1.50/hour
- Google Colab Pro+ (A100): $50/month
- Lambda Labs (A6000): $0.80/hour

### Inference (Production)
- **CPU**: 4-core modern CPU (inference on CPU is fine)
- **RAM**: 8GB
- **Model Size**: 80MB (.pt file)
- **Throughput**: 10-20 requests/second

---

## 10. Success Metrics

### Technical Metrics
- **Top-3 Accuracy**: >50% (our pick in user's top 3)
- **Win Probability MAE**: <5% (predicted vs actual win rate)
- **Inference Latency**: <100ms (p95)
- **Model Size**: <100MB (fast loading)

### Business Metrics
- **User Adoption**: 70% of users use NN recommendations
- **User Satisfaction**: 4+ stars average rating
- **Retention**: Users who use NN return 2x more
- **Feedback Loop**: 10% of users provide feedback

---

## 11. Risk Mitigation

### Risk 1: Model Becomes Outdated (Patch Changes)
**Mitigation:** Automated retraining every patch (bi-weekly)

### Risk 2: Overfitting to High-Elo Play
**Mitigation:** Train separate models per rank tier

### Risk 3: Inference Too Slow
**Mitigation:** Model quantization (INT8), ONNX runtime

### Risk 4: Data Drift
**Mitigation:** Monitor prediction accuracy over time, alert on drops

---

## References & Inspiration

- **AlphaGo/AlphaStar**: Monte Carlo Tree Search + NN
- **OpenAI Dota 2 Bot**: Transformers for action prediction
- **Riot's ML Systems**: https://technology.riotgames.com/tags/machine-learning
- **Research**: "Deep Reinforcement Learning for MOBA Games" (various papers)

---

**Last Updated:** 2026-01-26
**Status:** Implemented (50-feature model active)
**Next Step:** Train with real scraped data for improved accuracy
