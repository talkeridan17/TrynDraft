# User Guide

This guide explains how to use TrynDraft to improve your League of Legends drafting.

## Getting Started

### 1. Access TrynDraft

Visit the application at your deployment URL or run it locally (see [Development Setup](Development-Setup)).

### 2. Choose Your Mode

**Guest Mode**: Start drafting immediately without an account. Your settings won't be saved.

**Logged In**: Create an account to save your preferences, champion pool, and get personalized recommendations.

## The Draft Interface

### Overview

The draft page has three main sections:

```
┌─────────────────────────────────────────────────────────────┐
│  [Blue Team]              [Phase]              [Red Team]   │
│  Ban slots (5)          BAN/PICK/COMPLETE     Ban slots (5) │
│  Pick slots (5)          Turn indicator       Pick slots (5)│
├─────────────────────────────────────────────────────────────┤
│                    [Champion Picker]                        │
│              Search and select champions                    │
├─────────────────────────────────────────────────────────────┤
│                    [LLM Analysis Panel]                     │
│         Strategic advice and recommendations                │
└─────────────────────────────────────────────────────────────┘
```

### Setting Up Your Draft

1. **Select Your Role**: Choose your primary role (Top, Jungle, Mid, ADC, Support)
2. **Select Your Rank**: Choose your rank for meta-appropriate recommendations
3. **Select Game Mode**: Ranked, Clash, or Pro (affects recommendation style)

### Draft Phases

**Ban Phase**
- Click any ban slot to select it (highlighted in yellow)
- Search for a champion in the picker
- Click the champion to ban them
- Banned champions are greyed out and can't be picked

**Pick Phase**
- Click any pick slot on your team to select it
- Search for a champion
- Click to lock in your pick
- Watch the LLM panel for recommendations

**Complete Phase**
- All 10 champions are locked
- Full gameplan analysis appears in the LLM panel
- Review team compositions and strategy

### Using the Champion Picker

**Search**: Type in the search box to filter champions by name

**Quick Pick**: Click any champion to select them for the current slot

**Drag and Drop**: Drag champions between slots to swap positions

**Recommendations**: Click recommended champions in the LLM panel to quick-select them

### Understanding LLM Analysis

The LLM panel provides real-time analysis during your draft:

**During Ban Phase:**
- Recommended bans based on your role
- Meta threats to consider
- Counter-ban suggestions

**During Pick Phase:**
- Champion recommendations for your role
- Why each pick is strong in this draft
- Synergy and counter information

**After Draft Complete:**
- Full team composition analysis
- Win conditions for your team
- Enemy threats to watch for
- Phase-by-phase gameplan (early/mid/late game)

### Clickable Recommendations

When the LLM suggests champions, you can click them directly:
- Champions appear as buttons with splash art
- Click to select that champion for the current slot
- Unavailable champions (already picked/banned) are greyed out

## Profile & Preferences

### Setting Up Your Profile

1. Go to **Profile** page
2. Set your profile picture (champion splash art)
3. Select your main role
4. Set your current rank

### Managing Your Champion Pool

1. Go to **Profile** page
2. Scroll to "Champion Pool" section
3. Click champions to add them to your pool
4. Set proficiency (1-5 stars) for each champion
5. Save your preferences

**Proficiency affects recommendations**: Higher proficiency champions are prioritized in suggestions.

### Settings Page

Access **Settings** to configure:
- **Game Mode**: Ranked (solo focus), Clash (team coordination), Pro (advanced strategies)

## Tips for Better Drafts

### General Tips

1. **Pay attention to phase**: Early bans/picks should target power picks, later picks can counter
2. **Consider team composition**: Balance damage types, CC, and tank/damage ratio
3. **Watch the recommendations**: The NN considers many factors you might miss
4. **Read the analysis**: LLM explains why picks are good/bad

### Using Recommendations Effectively

**During Bans:**
- Ban champions that counter your intended pick
- Or ban generally strong meta champions
- Role-specific: If jungle, ban enemy jungle threats

**During Picks:**
- Early picks: Flexible champions with low counter-ability
- Counter picks: Wait to see enemy picks before locking
- Comfort picks: Your proficiency matters - a comfortable pick beats a "better" champion

### Understanding the AI

**Neural Network (NN):**
- Scores champions based on 50 features
- Considers your champion pool and proficiency
- Factors in matchups and synergies
- Updates based on current patch meta

**LLM Analysis:**
- Provides strategic reasoning
- Explains team compositions
- Generates gameplan advice
- Role-specific recommendations

**Development Mode:**
- Shows "[DEV MODE]" when using rule-based fallback
- Still provides useful role-specific advice
- Real LLM available when enabled by admins

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `Esc` | Clear champion search |
| `Enter` | Select first search result |

## Troubleshooting

### Champions not loading
- Check your internet connection
- Images come from Riot's CDN

### LLM not responding
- May be in DEV MODE (rule-based fallback)
- Check if API is enabled (admin setting)

### Recommendations seem wrong
- Ensure your role is set correctly
- Check your rank setting
- Verify your champion pool is configured

---

**Questions?** See the [FAQ](FAQ) or open a GitHub issue.
