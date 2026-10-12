# Design — NE Trip Planner

Status: **approved and implemented (v0)** — see §13 for where the build differs from the original design. Visual version: [`design/index.html`](design/index.html).

## 1. Shape of the system

```
Browsers (A, B, C) ──HTTPS/WSS──▶ Load balancer (TLS, WS upgrade)
                                       │
                         ┌─────────────▼──────────────┐
                         │  App container (FastAPI)    │  ×N instances
                         │  • REST: sessions/join/plan │
                         │  • WS hub: fan-out, presence│
                         │  • Orchestrator: turn lock, │
                         │    retrieve, 1 LLM call     │
                         │  • Embedder (bge-small)     │
                         └───┬───────────┬─────────┬───┘
                             │           │         │
                    Postgres+pgvector   LLM        Open-Meteo
                    (sessions, msgs,    (any       (weather)
                     plan, kb_chunks,   provider)
                     LISTEN/NOTIFY)
```

One image serves the API **and** the static frontend. Postgres is the only stateful dependency; it also carries cross-instance fan-out (LISTEN/NOTIFY), so no Redis in the POC.

## 2. Session & join flow

1. `GET /` → server creates `session` (id, 6-char `code`), creates a `participant` token → redirect to `/s/<code>`.
2. Page asks for a display name once; token stored in `localStorage` + cookie → "same device = same person" on reopen.
3. Invite = link `/s/<code>` or typing the code on the home page. `POST /api/sessions/<code>/join {name}` returns a participant token. Joins are rate-limited per IP; cap 8 participants.
4. Client opens `WSS /ws/<code>?token=…`, receives a snapshot (messages, plan, presence), then live events.

Code alphabet: `ABCDEFGHJKMNPQRSTUVWXYZ23456789` (no 0/O/1/I/L) → ~10⁹ codes; sessions expire so the live space is tiny.

## 3. Real-time model

Events (JSON over WS): `message.created`, `bot.token`, `bot.done`, `plan.updated`, `presence`, `typing`.

- Server writes event to Postgres, then `NOTIFY session_<id>`; every instance holding sockets for that session forwards it. Works on 1 or N instances (N8).
- Reconnect: client sends `last_seq`; server replays missed events from `messages`/`plan_versions`.
- **Turn lock**: one bot turn per session at a time. Messages arriving mid-turn are stored and batched into the next turn (so 3 friends typing at once produce one coherent answer, not three).

## 4. Bot orchestration — a pipeline, not an agent loop

The bot is deliberately built for a **very small, cheap model**. Instead of letting the model decide which tools to call (needs a strong, tool-calling model), the **orchestrator does retrieval deterministically** and makes **one LLM call per turn**:

1. **Turn lock** — take the session's bot turn; batch queued human messages.
2. **Retrieve (no LLM)** — `search_kb` with the latest messages (hybrid RAG, top-4, metadata filters inferred by simple rules/keywords: state, season, permit words → `high_risk`); `get_weather` when a place + month/dates are mentioned (coordinates from the KB).
3. **Prompt (short)** — system rules + participants and their preferences + the current plan (compact JSON) + last ~10 messages with `[Name]:` prefixes + the retrieved chunks in a delimited block.
4. **One streamed LLM call** — output is the **reply text first**, then optionally a line `###PLAN` followed by `{"ops":[...]}`. Text-then-JSON (instead of a pure JSON object) lets the reply stream to clients immediately and is easier for small models.
5. **Validate** — if the JSON after `###PLAN` is missing/invalid, the reply is still delivered and the plan is left untouched (never corrupt the plan). Unknown `kb_id`s are dropped; duplicates and out-of-range days rejected; humans may only move/remove.
6. **Apply** — `plan_ops` (add/move/remove item, set day title, note) validated against the plan schema, versioned, broadcast as `plan.updated`.

System-prompt rules: facts only from the retrieved block, cite KB ids, add "verify before travel" for permits/seasons, say "I don't have that" when the block is empty, reconcile participants, keep replies short.

### 4.1 Pluggable, small-by-default LLM

The orchestrator talks to a single port:

```
LLM.chat(messages, *, stream=True, json_schema=None) -> async iterator of text deltas
```

- **Adapter**: a ~50-line client for any **OpenAI-compatible `/chat/completions`** endpoint (Ollama, vLLM, llama.cpp, OpenAI, OpenRouter, Groq...). Providers without that API (Anthropic, Gemini, Bedrock...) go through the stock **LiteLLM proxy container** (compose profile `litellm`), so the app has no vendor SDK and no LiteLLM Python dependency (ADR-0004).
- **Config only** (env): `LLM_PROVIDER=mock|openai`, `LLM_BASE_URL`, `LLM_MODEL`, `LLM_API_KEY`. (`mock` is an offline, deterministic provider used for the demo and tests.)
- **Works with**: hosted small models (Claude Haiku-class, GPT mini/nano-class, Gemini Flash-Lite-class, Mistral small, DeepSeek) and **self-hosted open models** (Qwen/Llama/Gemma 3–8B via Ollama, vLLM or llama.cpp) — anything that speaks the OpenAI-compatible API.
- **No dependence on native tool calling or vendor-specific features** (prompt caching, extended thinking), so the weakest plausible model still works. Output format is plain text + a trailing JSON block, validated server-side.
- **Summariser** (rolling session summary) uses the same port, same or cheaper model.
- **Pick the model by eval, not by brand**: the eval harness runs the same set against N configured models and reports quality + cost; ship the cheapest that clears the bar.

Why this is cheap: retrieval is local (embeddings in-process, pgvector), the prompt is ~1.5–2.5k tokens, one call per turn. At small-model prices a 30-turn session is on the order of **a fraction of a cent to a few cents**, and **zero marginal cost** if self-hosted.

## 5. RAG

- **Ingest** (automatic at app start, re-embeds only changed entries): JSONL entries authored chunk-sized (one entry = one chunk, ~50–120 words) → embeddings via the embedding port (default `hash`, 256-d, offline; or any OpenAI-compatible endpoint such as Ollama `nomic-embed-text`) → `kb_docs` with metadata. Oxomiai's `places`/`hidden_gems` are adapted on the fly.
- **Retrieve**: hybrid — weighted full-text (title > region > body) ∪ pgvector cosine (with a distance cutoff, so unrelated queries return nothing), merged by reciprocal-rank fusion; state filter inferred from chat + plan (NE-wide guides always admitted); permit/season guides pinned when asked; place-name boost. Rerank deferred.
- **Why not a managed RAG product**: corpus is tiny (hundreds of chunks); pgvector in the DB we already run is simplest and cloud-portable.
- **Citations**: each chunk has `kb_id`; the bot references them, UI shows them as small chips.
- **Freshness**: every chunk has `source` + `last_verified`; permit/season chunks flagged `high_risk`.

## 6. Data model (Postgres)

```
sessions(id, code UNIQUE, created_at, last_active_at, plan jsonb, plan_version, bot_seq, tokens_used)
participants(id, session_id, name, token_hash, joined_at, conns)
messages(id bigserial, session_id, participant_id NULL, role[user|bot|system], content, meta jsonb, created_at)
kb_docs(id, kind, state, region, title, text, best_seasons, high_risk, source, last_verified, lat, lon, h, tsv, embedding vector(N))
```

Plan JSON: `{ days: [ { n, title, items: [ { id, place_id, title, note, duration_h, travel_hint, added_by } ] } ], notes }`.

## 7. Frontend

Single page, mobile-first, vanilla JS or Preact (no heavy build): header (code chip, copy link, avatars) → chat column → plan panel (tabs on mobile, split view on desktop) → composer. Wireframes in `design/index.html`.

## 8. Safety, limits, cost

- Per-session token budget and message rate limit; friendly cut-off.
- Join/code lookups rate-limited; tokens stored hashed; codes never logged in full.
- KB text and user messages are placed in delimited data blocks; the model's only write effect is validated `plan_ops` on the plan, nothing else.
- Rough cost: ~2k input + ~300 output tokens per turn × 30 turns ≈ 60k in / 9k out per session → well under a cent on small hosted models; free on a self-hosted one.
- Small-model risks handled by design: weaker instruction-following → retrieval is deterministic and the model only writes text + JSON; hallucination → answer only from the retrieved block, "I don't have that" fallback, eval subset for permits/seasons.

## 9. Deployment (cloud-agnostic)

One container image + managed Postgres with pgvector + an LLM API key **or** an internal URL of a self-hosted model server (Ollama/vLLM).

| Piece | AWS | GCP | Anywhere |
|---|---|---|---|
| App container | ECS Fargate / App Runner | Cloud Run (WS ok, set timeout) | Fly.io / Render / VM |
| Postgres+pgvector | RDS / Aurora PG | Cloud SQL PG / AlloyDB | Neon / Supabase |
| Secrets | Secrets Manager | Secret Manager | env vars |
| TLS/LB | ALB | Cloud LB | provider edge |

Local: `docker compose up` (app + postgres).

## 10. Decisions → ADRs (written: `docs/architecture/decisions/0002`–`0005`)

| ADR | Decision |
|---|---|
| 0002 | App stack: Python/FastAPI, WebSocket, Postgres LISTEN/NOTIFY fan-out, no Redis |
| 0003 | Postgres+pgvector for RAG; local bge-small embeddings (vs Voyage/managed KB) |
| 0004 | LLM access: OpenAI-compatible port + LiteLLM proxy container, small model by default, pipeline orchestration (vs vendor SDK + native tool use) |
| 0005 | Anonymous sessions: join code + participant token, no accounts |

## 11. Build plan (after approval, ~2 weeks)

1. **Days 1–2**: scaffold, compose, schema, session/join REST, WS hub with fan-out.
2. **Days 3–5**: frontend chat + presence; bot turn loop, streaming, turn lock.
3. **Days 6–8**: KB ingest, hybrid search, `search_kb` + `get_weather`, citations.
4. **Days 9–10**: shared plan (`update_plan`, versions, manual edits, export).
5. **Days 11–12**: limits, summariser, multi-instance test, deploy to chosen host.
6. **Days 13–14**: run eval set, write Outcome, promote/extend/kill.

## 12. Risks

| Risk | Mitigation |
|---|---|
| Wrong permit/season info | Source+date on chunks, high_risk flag, "verify" suffix, dedicated eval subset |
| Bot noisy in groups | Turn batching, `//` human-only prefix (Q1), brevity rules |
| KB for 7 new states is thin | Human-curated, start with ~4/state; bot says "I don't have that" |
| Anyone with code can join | Short TTL, cap 8, rate-limit, owner can delete session |
| WebSocket limits on some serverless hosts | Pick host with WS support; fall back to SSE + POST |

## 13. As built (v0) — differences from the original design

| Design | Built |
|---|---|
| Embeddings: local `bge-small` | Pluggable port; default `hash` (offline, lexical quality) so the demo needs no model. Real embeddings via any OpenAI-compatible endpoint (e.g. Ollama `nomic-embed-text`). |
| Separate `kb_chunks` table | One entry = one chunk in `kb_docs`. |
| Pure-JSON model output | Reply text, then `###PLAN` + JSON (streams better, friendlier to small models). |
| LiteLLM library (Q7) | Plain OpenAI-compatible HTTP; LiteLLM runs as an optional **proxy container**. |
| `plan_versions` table | Plan + version counter on `sessions` (row-locked updates). |
| Rolling summariser, per-person preference extraction, read-only share page, replay by `last_seq` | Not built. Reconnect re-sends a snapshot (last 200 messages + plan); events arriving during the snapshot are buffered per socket. |
| Presence | DB connection counter per participant; reset on boot (stale after a crash, wrong for rolling multi-instance deploys). |
| Mobile | Same page, mobile-first: tabs (Chat / Plan) under 760 px, 44 px touch targets, safe-area insets, `100dvh`, share sheet via `navigator.share`. |
