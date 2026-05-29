# User Guide

This guide explains how to use TrynDraft to improve your League of Legends drafting.

## Getting Started

### 1. Open TrynDraft

Visit **https://tryndraft.vercel.app** — no account, no login, no install required.

### 2. Load Your Profile (Optional)

Enter your Riot ID (`Name#TAG`) in the top bar of the Draft page and press **Load**. TrynDraft fetches your champion stats from Deeplol and uses them to bias recommendations toward champions you're good at.

## The Draft Interface

```
┌─────────────────────────────────────────────────────────────┐
│  [Blue Team]              [Phase]              [Red Team]   │
│  Ban slots (5)          BAN/PICK/COMPLETE     Ban slots (5) │
│  Pick slots (5)          Turn indicator       Pick slots (5)│
├─────────────────────────────────────────────────────────────┤
│                    [Champion Picker]                        │
│              Search, filter and select champions            │
├─────────────────────────────────────────────────────────────┤
│               [Recommendations + LLM Panel]                 │
│         Top picks, stats, and AI explanations               │
└─────────────────────────────────────────────────────────────┘
```

### Draft Phases

**Ban Phase**
- The current slot is highlighted
- Champions in the picker are sorted by ban strength
- Click any champion to ban them
- Banned champions are greyed out

**Pick Phase**
- Recommendations appear sorted by model score × role affinity × your proficiency
- Hover any champion in the picker or in a pick slot to see its stats in the info panel
- Click to lock in the pick

**Complete Phase**
- All 10 champions locked in
- Click **Explain** for an AI summary of the draft

### Champion Picker

- **Search**: Filter by name
- **Drag and drop**: Drag champions between slots to swap
- **Hover**: Hovering any champion (in picker or in a pick slot) shows model rank, your games, and win rate in the side panel

### AI Recommendations

TrynDraft uses two AI systems:

**DraftTransformer (ONNX)** — runs in-browser, no internet call needed after initial load:
- Scores all ~170 champions for the current draft state
- Accounts for draft sequence, team composition, and role context
- Adjusted by role affinity (data-driven frequencies from pro play)
- Adjusted by your Deeplol proficiency if loaded

**LLM Explainability (Qwen2.5)** — optional, click **Explain** to trigger:
- Loads a small quantized model (0.5B or 1.5B) from HuggingFace
- Runs entirely in your browser via a Web Worker
- Generates a 1-sentence explanation per top champion based on their ability tags
- Takes 5–30 seconds depending on your device

## Tips

1. **Load your Riot ID** — even a small proficiency boost meaningfully surfaces champions you actually play
2. **Role slots matter** — each pick slot has a role assigned (TOP/JNG/MID/ADC/SUP); the model uses this as a hint
3. **Early bans** — ban strong meta picks or counters to your intended champion
4. **Flex picks** — champions like Yasuo (mid/top/bot) appear across multiple role slots with reduced penalty

## Troubleshooting

**Champions not loading** — check your internet connection; images come from Riot's Data Dragon CDN

**Riot ID not found** — make sure the format is exactly `Name#TAG` (case-sensitive tag); try your region if results seem wrong

**LLM slow or not loading** — the first load downloads the model (~500MB); subsequent uses are cached. Large models (1.5B) may be slow on lower-end devices

**Recommendations seem off** — the current model was trained on 2020–2024 pro data; meta accuracy improves as new data is scraped each patch

---

**Questions?** See the [FAQ](FAQ) or open a GitHub issue.
