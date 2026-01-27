# Frequently Asked Questions (FAQ)

## General Questions

### What is TrynDraft?

TrynDraft is an AI-powered drafting assistant for League of Legends. It helps you make better pick and ban decisions by combining:
- A neural network that scores champions based on the current draft state
- An LLM that provides strategic analysis and explains recommendations
- Your personal preferences and champion pool

### Is TrynDraft free?

Yes! TrynDraft is an open-source project. You can use it for free, host it yourself, or contribute to its development.

### Does TrynDraft work with the actual League client?

No, TrynDraft is a standalone web application. You use it alongside the League client during champion select. It doesn't interact with or modify the game in any way.

### Is TrynDraft against Riot's Terms of Service?

No. TrynDraft is a draft planning tool that runs completely separate from the game. It doesn't read game memory, inject code, or automate any in-game actions. It's similar to using a notepad to plan your draft.

---

## Features & Usage

### Why do I see "[DEV MODE]" in the analysis?

This means the LLM is disabled and you're seeing rule-based fallback analysis. This happens when:
- The server is running in development mode
- The HuggingFace API is disabled to prevent costs

The rule-based analysis still provides useful role-specific advice, just without the advanced LLM reasoning.

### How accurate are the recommendations?

The neural network is trained on champion statistics, matchup data, and meta information. It considers:
- Win rates and pick rates for the current patch
- Team composition balance (damage types, CC, tankiness)
- Your champion pool and proficiency ratings
- Synergies with your team and counters to enemies

Accuracy improves as we collect more training data. Currently in alpha, expect recommendations to be helpful but not perfect.

### Can I use TrynDraft without logging in?

Yes! Guest mode gives you full access to the draft tool. However, your preferences (role, rank, champion pool) won't be saved between sessions.

### How do I get better recommendations?

1. **Set up your profile**: Configure your main role and rank
2. **Build your champion pool**: Add champions you're comfortable playing
3. **Rate your proficiency**: Higher proficiency champions get prioritized
4. **Keep settings updated**: Change rank/role as you improve or flex

---

## Technical Questions

### What technologies does TrynDraft use?

**Frontend:**
- React 19 with TypeScript
- Vite for building
- TailwindCSS for styling
- Zustand for state management

**Backend:**
- FastAPI (Python 3.12)
- SQLAlchemy ORM
- PyTorch neural network
- HuggingFace API for LLM

### Can I self-host TrynDraft?

Yes! See the [Development Setup](Development-Setup) guide. You'll need:
- Python 3.12+
- Node.js 18+
- (Optional) HuggingFace API token for LLM features

### Does TrynDraft collect my data?

When self-hosted, no data leaves your machine. If using a hosted version:
- We store your account info and preferences
- Draft data may be used to improve the AI (anonymized)
- We don't share data with third parties

### Why is the LLM sometimes slow?

LLM inference takes 2-4 seconds because:
- The model is 72 billion parameters
- It runs on HuggingFace's servers
- Network latency adds time

We use request cancellation to prevent outdated responses when you click quickly.

---

## Champion Data

### Where does champion data come from?

- **Champion info**: Riot Data Dragon API (official)
- **Champion images**: Riot Data Dragon CDN
- **Role icons**: Community Dragon
- **Statistics**: Scraped from LoLalytics/U.GG (work in progress)

### How often is data updated?

- **Champion data**: Updated with each new patch
- **Statistics**: Planned daily updates (scraping in development)
- **Meta analysis**: LLM has knowledge up to its training cutoff

### Why isn't [new champion] available?

New champions are added after we update our data from Riot's Data Dragon API. This usually happens within a few days of champion release.

---

## Troubleshooting

### The app won't load

1. Check your internet connection
2. Try clearing browser cache
3. Ensure JavaScript is enabled
4. Try a different browser (Chrome, Firefox, Edge recommended)

### Champion images are broken

- Check internet connection (images load from Riot's CDN)
- Try refreshing the page
- CDN might be temporarily down (rare)

### Login not working

- Verify username and password
- Check if the backend server is running
- Clear browser localStorage and try again

### Recommendations seem completely wrong

- Verify your role is set correctly
- Check your rank setting
- Make sure you have champions in your pool
- If in DEV MODE, analysis is simplified

---

## Contributing

### How can I contribute?

See our [Contributing](Contributing) guide. You can:
- Report bugs via GitHub Issues
- Suggest features via GitHub Discussions
- Submit pull requests with improvements
- Help improve documentation

### I found a bug, what do I do?

1. Check if it's already reported in GitHub Issues
2. If not, create a new issue with:
   - Steps to reproduce
   - Expected vs actual behavior
   - Screenshots if applicable
   - Browser/OS information

### Can I use TrynDraft's code in my project?

Yes! TrynDraft is MIT licensed. You can use, modify, and distribute the code. Attribution is appreciated but not required.

---

## Future Plans

### What features are coming?

**Phase 3 (Current):**
- Data scraping pipeline
- LLM fine-tuning with LoL content
- Improved matchup data

**Phase 4+:**
- Draft history and sharing
- Multi-user live drafts (WebSocket)
- Mobile responsive design
- Voice/audio commentary mode

### Will there be a mobile app?

Not currently planned, but the web app will be made mobile-responsive. You'll be able to use it on mobile browsers.

### Will TrynDraft support other games?

Not in current plans. We're focused on making the best LoL drafting tool possible.

---

**Still have questions?** Open a discussion on GitHub or ask in the community!
