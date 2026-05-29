# Frequently Asked Questions (FAQ)

## General Questions

### What is TrynDraft?

TrynDraft is an AI-powered draft assistant for League of Legends that runs entirely in your browser. No account, no login, no server required.

### Is TrynDraft free?

Yes. It's open-source and free to use at https://tryndraft.vercel.app

### Does TrynDraft work with the actual League client?

No — it's a standalone web app you use alongside champion select. It doesn't interact with or modify the game in any way.

### Is TrynDraft against Riot's Terms of Service?

No. TrynDraft is a planning tool that runs completely separate from the game. It doesn't read game memory, inject code, or automate any in-game actions.

---

## Features & Usage

### Do I need to log in?

No. There are no accounts. The app is fully anonymous — just open the page and start drafting.

### How do I get personalized recommendations?

Enter your Riot ID (`Name#TAG`) in the top bar of the Draft page and click **Load**. TrynDraft fetches your champion stats from Deeplol and adjusts recommendations toward champions you play well.

### How accurate are the recommendations?

The DraftTransformer was trained on ~63K professional matches from 2020–2024. It's strong on structural draft principles (synergy, composition balance, role coverage) but may reflect older meta picks. Accuracy improves every patch as new data is scraped and the model is refreshed.

### Why do some off-meta picks still appear?

The model learned patterns from historical pro play. Some champions were dominant in earlier seasons and still score highly in certain contexts. As the model is retrained with more recent SoloQ data, these will fade out.

---

## Technical Questions

### What technologies does TrynDraft use?

**Frontend:** React 19, TypeScript, Vite, TailwindCSS, Zustand  
**AI (in-browser):** ONNX Runtime Web (DraftTransformer), Transformers.js v3 (Qwen2.5 LLM)  
**Data:** Riot Data Dragon CDN, Deeplol CDN  
**Hosting:** Vercel (static site)

There is no backend server.

### Does TrynDraft collect my data?

No data is sent to TrynDraft's infrastructure. Everything runs in your browser. Deeplol stats are fetched directly by your browser from their public CDN and cached in localStorage.

### Why is the LLM (Explain feature) slow?

The first time you click **Explain**, your browser downloads a quantized language model (~500MB for the 1.5B model, ~250MB for 0.5B). After the first load it's cached. Inference takes 5–30 seconds depending on your device. You can switch to the lighter 0.5B model in Settings.

### Can I self-host TrynDraft?

Yes. Clone the repo, `cd frontend && npm install && npm run dev`. See [Development Setup](Development-Setup).

---

## Champion Data

### Where does champion data come from?

- **Champion info + images**: Riot Data Dragon CDN (always up to date)
- **Player stats**: Deeplol CDN (public, by Riot ID)
- **Role frequencies**: Computed from pro-play training data, updated each model refresh

### How often is the model updated?

The model refreshes automatically every patch (~2 weeks). The automation scrapes new high-ELO games, fine-tunes the model, and deploys updated ONNX weights.

---

## Troubleshooting

### The app won't load

1. Check internet connection
2. Clear browser cache and reload
3. Ensure JavaScript is enabled
4. Try Chrome or Firefox

### Champion images are broken

Images load from Riot's CDN — check your internet connection or try refreshing.

### Riot ID not found

Make sure the format is exactly `Name#TAG`. The tag is case-sensitive. Try your correct region if results seem wrong.

### Recommendations seem wrong for my role

Make sure you're on the correct pick slot (each slot has a role assigned: TOP/JNG/MID/ADC/SUP). The model uses this as a lane hint.

---

## Contributing

### How can I contribute?

See the [Contributing](Contributing) guide. Bug reports, feature suggestions, and pull requests are all welcome via GitHub.

### Can I use TrynDraft's code in my project?

Yes — MIT licensed.

---

**Still have questions?** Open an issue on GitHub.
