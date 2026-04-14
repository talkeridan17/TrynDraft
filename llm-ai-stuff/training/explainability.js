import { pipeline, env } from "https://cdn.jsdelivr.net/npm/@xenova/transformers@2.17.2/dist/transformers.min.js";

// ── Configuration ──────────────────────────────────────────────────────────────

const MODEL_ID = "Qwen/Qwen2.5-0.5B-Instruct";
const MAX_NEW_TOKENS = 80;
const TEMPERATURE = 0.3;

// Cache model between calls so we only load it once
let _generator = null;
let _loading = false;
let _loadPromise = null;

// ── Model loading ──────────────────────────────────────────────────────────────

/**
 * Loads the Qwen2.5-0.5B model the first time it's called.
 * Subsequent calls return immediately from cache.
 * Progress callback receives {status, progress, file} updates.
 */
export async function loadExplainabilityModel(onProgress = null) {
    if (_generator) return _generator;

    // Prevent duplicate loads if called concurrently
    if (_loadPromise) return _loadPromise;

    _loadPromise = (async () => {
        // transformers.js caches weights in the browser's Cache API
        // after the first download — subsequent loads are instant
        env.allowLocalModels = false;

        _generator = await pipeline(
            "text-generation",
            MODEL_ID,
            {
                quantized: true,   // loads Q4 ONNX weights ~300MB
                progress_callback: onProgress,
            }
        );

        return _generator;
    })();

    return _loadPromise;
}

export function isModelLoaded() {
    return _generator !== null;
}

// ── Prompt builder ─────────────────────────────────────────────────────────────

/**
 * Builds a Qwen2.5-instruct formatted prompt from a SuggestionContext.
 * Uses the ChatML format Qwen2.5 was trained on:
 *   <|im_start|>system ... <|im_end|>
 *   <|im_start|>user   ... <|im_end|>
 *   <|im_start|>assistant
 *
 * Keeping the system prompt short and the user prompt structured
 * is critical for small models — they follow tight templates much
 * better than open-ended instructions.
 */
function buildPrompt(ctx) {
    const allied = ctx.allied_picks.length > 0
        ? ctx.allied_picks.join(", ")
        : "none yet";
    const enemy = ctx.enemy_picks.length > 0
        ? ctx.enemy_picks.join(", ")
        : "none yet";
    const bans = ctx.bans.length > 0
        ? ctx.bans.join(", ")
        : "none";
    const tags = ctx.top_tags.length > 0
        ? ctx.top_tags.join(", ")
        : "none";

    const profStr = ctx.proficiency
        ? `${ctx.proficiency.games} games played, ` +
        `${ctx.proficiency.win_rate.toFixed(1)}% winrate, ` +
        `AI score ${ctx.proficiency.ai_score.toFixed(1)}/100`
        : "no data";

    const action = ctx.is_pick ? "pick" : "ban";

    return (
        `<|im_start|>system
You are a League of Legends draft assistant. Write exactly 2-3 sentences explaining why a champion is a strong ${action}. Be specific, mention the draft context, and never exceed 3 sentences.
<|im_end|>
<|im_start|>user
Draft position: ${ctx.draft_position}
Allied picks: ${allied}
Enemy picks: ${enemy}
Bans: ${bans}

Suggested ${action}: ${ctx.champion_name}
Confidence: ${(ctx.probability * 100).toFixed(1)}% (ranked #${ctx.rank})
Damage type: ${ctx.damage_profile}
Key traits: ${tags}
Player proficiency: ${profStr}

Explain in 2-3 sentences why ${ctx.champion_name} is a good ${action} here:
<|im_end|>
<|im_start|>assistant
`);
}

// ── Generation ─────────────────────────────────────────────────────────────────

/**
 * Generates explanations for all 3 suggestions, streaming them one at a time.
 * Yields {rank, champion_name, explanation} objects as each completes.
 *
 * Usage:
 *   for await (const result of generateExplanations(contexts)) {
 *       displayExplanation(result);
 *   }
 */
export async function* generateExplanations(contexts) {
    const generator = await loadExplainabilityModel();

    for (const ctx of contexts) {
        const prompt = buildPrompt(ctx);

        const output = await generator(prompt, {
            max_new_tokens: MAX_NEW_TOKENS,
            temperature: TEMPERATURE,
            do_sample: true,
            repetition_penalty: 1.2,
            // Stop generating at sentence boundaries to enforce 2-3 sentence limit
            // and prevent the model from rambling
            eos_token_id: [151645],   // Qwen2.5 <|im_end|> token id
        });

        // Strip the input prompt from the output — transformers.js
        // returns the full sequence including the prompt by default
        let explanation = output[0].generated_text
            .slice(prompt.length)
            .trim();

        // Hard truncate to 3 sentences as a safety net
        explanation = truncateToSentences(explanation, 3);

        yield {
            rank: ctx.rank,
            champion_name: ctx.champion_name,
            explanation,
        };
    }
}

// ── Utilities ──────────────────────────────────────────────────────────────────

/**
 * Truncates text to at most maxSentences sentences.
 * Used as a safety net in case the model generates more than instructed.
 */
function truncateToSentences(text, maxSentences) {
    // Split on sentence-ending punctuation followed by whitespace or end of string
    const sentences = text.match(/[^.!?]+[.!?]+(\s|$)/g);
    if (!sentences) return text;
    return sentences.slice(0, maxSentences).join("").trim();
}

/**
 * Formats the full prediction result (from Python inference pipeline)
 * into a display-ready object for the frontend.
 *
 * Call this after generateExplanations yields all three results.
 */
export function formatPredictionDisplay(predictionResult, explanations) {
    return predictionResult.suggestions.map((s, i) => ({
        rank: i + 1,
        champion_id: s.champion_id,
        champion_name: s.champion_name,
        probability: s.probability,
        win_prob: predictionResult.win_prob,
        is_pick: predictionResult.is_pick,
        proficiency: s.proficiency ?? null,
        explanation: explanations[i]?.explanation ?? "",
    }));
}