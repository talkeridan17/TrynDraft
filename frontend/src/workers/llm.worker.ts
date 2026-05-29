/* eslint-disable @typescript-eslint/no-explicit-any */

// LLM inference runs here, completely off the main thread.
// The main thread sends {type:'generate', requestId, prompt, modelId, maxNewTokens}
// and receives {type:'result'|'error'|'loading'|'progress', requestId, ...}

let pipeline: any = null;
let loadedModelId = '';

self.onmessage = async (e: MessageEvent) => {
  const { type, requestId, prompt, modelId, maxNewTokens } = e.data;
  if (type !== 'generate') return;

  try {
    const cdnUrl = 'https://cdn.jsdelivr.net/npm/@huggingface/transformers@3.3.3/dist/transformers.min.js';
    const t: any = await (0, eval)(`import("${cdnUrl}")`);
    t.env.allowLocalModels = false;

    if (!pipeline || loadedModelId !== modelId) {
      self.postMessage({ type: 'loading', requestId });
      pipeline = await t.pipeline('text-generation', modelId, {
        quantized: true,
        progress_callback: (p: any) => {
          if (p.status === 'progress') {
            self.postMessage({ type: 'progress', requestId, progress: Math.round(p.progress ?? 0) });
          }
        },
      });
      loadedModelId = modelId;
    }

    const output = await pipeline(prompt, {
      max_new_tokens: maxNewTokens,
      temperature: 0.35,
      do_sample: true,
      repetition_penalty: 1.15,
      return_full_text: false,
    });

    const first = output?.[0]?.generated_text;
    const text = typeof first === 'string'
      ? '1. ' + first.replace(/<\|im_start\|>|<\|im_end\|>|system|user|assistant/gi, '').trim()
      : '';

    self.postMessage({ type: 'result', requestId, text: text || 'LLM returned empty response.' });
  } catch (err) {
    self.postMessage({ type: 'error', requestId, message: String(err) });
  }
};
