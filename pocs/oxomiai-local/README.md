# Oxomiai Local — on-device LLM travel bot (POC)

## Hypothesis

A small open-weight LLM (Qwen2.5 1.5B, 4-bit) running **entirely on a
mid-range Android phone** in the browser via WebGPU, grounded on the same
static `destinations.json`, can answer Northeast Assam traveller questions
noticeably better than the rule-based `pocs/oxomiai-pwa/`, while keeping
that POC's properties: no server, no API key, no per-query cost, and fully
offline after a one-time download.

Concretely: on a ~6–8 GB RAM Android phone running current Chrome, the model
loads in under 60s from cache, starts streaming a reply in under 3s,
generates at ≥ 8 tokens/s, and on the ~30-query test set from
`pocs/assam-travel-bot/eval/`, a manual rubric rates ≥ 70% of answers
"helpful and accurate" with no invented facts about places outside the list.

## Approach

- Forked from `pocs/oxomiai-pwa/` (Next.js + Tailwind PWA, static JSON data).
- [WebLLM](https://github.com/mlc-ai/web-llm) (`@mlc-ai/web-llm`) runs the
  model on WebGPU inside a Web Worker (`lib/llm.worker.ts`), so the UI keeps
  responding while it loads and generates.
- **Models** (`lib/localModel.ts`): the user picks *Standard* (Qwen2.5-1.5B-Instruct,
  ~0.9 GB) or *Lite* (Qwen2.5-0.5B-Instruct, ~0.3 GB). The `q4f16_1` build is
  used when the GPU supports `shader-f16`, otherwise `q4f32_1` (many mid-range
  Android GPUs lack f16).
- **Grounding**: the whole destination list (~1k tokens) goes into the system
  prompt. There's no retrieval step, since the dataset is tiny.
- **Download is opt-in**: nothing large downloads until the user taps a model
  button. Once the weights are cached (WebLLM stores them in the Cache API),
  later visits load them automatically, including offline.
- **Graceful fallback**: while the model loads, when WebGPU is missing, or
  if generation fails, the chat answers with the rule-based
  `lib/intentMatcher.ts`, so the bot always responds.
- `public/sw.js` only manages its own `oxomiai-local-*` caches and ignores
  cross-origin requests, so it never deletes or duplicates the model weights.
- Cut: model/vendor evaluation beyond Qwen2.5, RAG, tools (weather, local
  guides), iOS tuning, native app packaging.

## Running

```
npm install
npm run dev          # or: npm run build && npm start
```

To test on a phone, serve over HTTPS (WebGPU needs a secure context), e.g.
deploy to Vercel or use `chrome://inspect` port forwarding to `localhost`.
The model weights come from `huggingface.co` and the WebGPU kernels from
`raw.githubusercontent.com`, so the first load needs those hosts reachable.

## Exit criteria

- **Promote**: meets the latency and quality bar above on a real mid-range
  Android phone. Write an ADR for the on-device model and runtime choice
  (WebLLM + Qwen2.5) and move to `products/`.
- **Extend**: quality is good but too slow or memory-heavy on target
  devices (try the Lite tier, Gemma/Llama 1B, or a native llama.cpp/MediaPipe
  wrapper), or answers drift from the data (tighten the prompt, add retrieval).
- **Kill**: it won't load or run usably on mid-range phones, or it's no better
  than the rule-based bot. That points to the hosted-LLM approach in
  `pocs/assam-travel-bot/`.

## Timebox

1 week from this commit to a promote/extend/kill decision.

## Status

- Build, typecheck and lint pass. In headless Chromium, the no-WebGPU
  fallback, the model-picker banner, the load-error path and the rule-based
  answers all work.
- **Not yet verified**: real on-device inference. The dev sandbox this was
  built in can't reach Hugging Face, so the first real model run needs to be
  on a phone.

## Outcome

_Fill in when complete._
