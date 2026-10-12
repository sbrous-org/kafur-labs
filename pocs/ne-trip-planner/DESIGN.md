# Design — NE Trip Planner

Status: **draft for review**. Visual version: [`design/index.html`](design/index.html).

## 1. Shape of the system

```
Browsers (A, B, C) ──HTTPS/WSS──▶ Load balancer (TLS, WS upgrade)
                                       │
                         ┌─────────────▼──────────────┐
                         │  App container (FastAPI)    │  ×N instances
                         │  • REST: sessions/join/plan │
                         │  • WS hub: fan-out, presence│
                         │  • Orchestrator: turn lock, │
                         │    prompt build, tool loop  │
                         │  • Embedder (bge-small)     │
                         └───┬───────────┬─────────┬───┘
                             │           │         │
                    Postgres+pgvector   Anthropic  Open-Meteo
                    (sessions, msgs,    API (LLM)  (weather)
                     plan, kb_chunks,
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

## 4. Bot orchestration

Per turn, the orchestrator assembles:

- **System prompt**: role (NE India group-trip planner), rules (facts only via tools, cite KB ids, add "verify before travel" for permits/seasons, reconcile participants, ask clarifying questions sparingly), today's date.
- **Group context**: participant list, extracted preferences per person (rolling, maintained by a cheap summariser call every N messages).
- **Current plan** (JSON) so the bot edits rather than rewrites.
- **Recent messages** with `[Name]:` prefixes; older ones replaced by the rolling summary.

Tool loop (Anthropic tool use, streaming):

| Tool | Purpose | Notes |
|---|---|---|
| `search_kb(query, state?, type?, season?, k)` | RAG | Returns chunks with id, text, source, last_verified |
| `get_weather(place, days)` | Open-Meteo forecast / climatology | Coordinates come from the KB |
| `update_plan(ops[])` | add/move/remove item, set day title, note | Server validates against plan schema, bumps version, broadcasts `plan.updated` |

The bot never answers factual place/permit questions from memory: the system prompt forbids it and the eval checks it.

## 5. RAG

- **Ingest** (`make ingest`): JSONL entries + markdown guides → chunks (≈300–500 tokens, one place = few chunks: overview, logistics, season/permits, food/stay) → embeddings (local `bge-small-en-v1.5`, 384-d) → `kb_chunks` with metadata.
- **Retrieve**: hybrid — pgvector cosine top-k ∪ `tsvector` keyword top-k, merged by reciprocal-rank fusion, metadata pre-filter (state/type/season). Optional rerank is deferred.
- **Why not a managed RAG product**: corpus is tiny (hundreds of chunks); pgvector in the DB we already run is simplest and cloud-portable.
- **Citations**: each chunk has `kb_id`; the bot references them, UI shows them as small chips.
- **Freshness**: every chunk has `source` + `last_verified`; permit/season chunks flagged `high_risk`.

## 6. Data model (Postgres)

```
sessions(id, code UNIQUE, created_at, last_active_at, token_budget_used, summary)
participants(id, session_id, name, token_hash, joined_at, last_seen_at)
messages(id, session_id, seq, participant_id NULL, role[user|bot|system], content, meta jsonb, created_at)
plan_versions(session_id, version, plan jsonb, changed_by, created_at)   -- current = max(version)
kb_docs(id, kind, state, region, title, source, last_verified, high_risk, raw jsonb)
kb_chunks(id, doc_id, text, metadata jsonb, embedding vector(384), tsv tsvector)
```

Plan JSON: `{ days: [ { n, title, items: [ { id, place_id, title, note, duration_h, travel_hint, added_by } ] } ], notes }`.

## 7. Frontend

Single page, mobile-first, vanilla JS or Preact (no heavy build): header (code chip, copy link, avatars) → chat column → plan panel (tabs on mobile, split view on desktop) → composer. Wireframes in `design/index.html`.

## 8. Safety, limits, cost

- Per-session token budget and message rate limit; friendly cut-off.
- Join/code lookups rate-limited; tokens stored hashed; codes never logged in full.
- KB text and user messages are placed in delimited data blocks; tools can only write the plan, nothing else.
- Rough cost: a 30-turn session ≈ 100–200k input tokens with caching → low single-digit cents–tens of cents depending on model tier.

## 9. Deployment (cloud-agnostic)

One container image + managed Postgres with pgvector + a secret for the Anthropic key.

| Piece | AWS | GCP | Anywhere |
|---|---|---|---|
| App container | ECS Fargate / App Runner | Cloud Run (WS ok, set timeout) | Fly.io / Render / VM |
| Postgres+pgvector | RDS / Aurora PG | Cloud SQL PG / AlloyDB | Neon / Supabase |
| Secrets | Secrets Manager | Secret Manager | env vars |
| TLS/LB | ALB | Cloud LB | provider edge |

Local: `docker compose up` (app + postgres).

## 10. Decisions → ADRs to write once design is approved

| ADR | Decision |
|---|---|
| 0002 | App stack: Python/FastAPI, WebSocket, Postgres LISTEN/NOTIFY fan-out, no Redis |
| 0003 | Postgres+pgvector for RAG; local bge-small embeddings (vs Voyage/managed KB) |
| 0004 | LLM vendor/model: Anthropic API direct, tool-use orchestration (vs Bedrock/Vertex) |
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
