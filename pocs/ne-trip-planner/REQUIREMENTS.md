# Requirements — NE Trip Planner

Status: **implemented as v0** (see DESIGN §13 for deviations). Decisions confirmed with the requester are marked ✅; open items are in §9.

## 1. Goal

A very simple web bot where a group plans a Northeast India trip together, in one shared session, with the bot supplying grounded destination knowledge.

## 2. Confirmed decisions ✅

| # | Decision |
|---|---|
| D1 | New standalone POC (`pocs/ne-trip-planner/`); **reuses Oxomiai's `knowledge_base/*.jsonl` + schema as seed data**, own backend. |
| D2 | Geography: **all eight NE states, Assam deepest** (Assam, Meghalaya, Arunachal Pradesh, Nagaland, Manipur, Mizoram, Tripura, Sikkim). |
| D3 | Join model: **no login**. Opening the link creates a session; others join with a **6-char code** + display name. |
| D4 | Hosting: **cloud-agnostic** — containers + Postgres (pgvector) + **any LLM provider** (hosted or self-hosted). Maps cleanly to AWS/GCP (see DESIGN §9). |
| D5 | LLM: **very small, cheap model by default**, and the model/provider is **pluggable by config** — not tied to Claude or any vendor. |

## 3. User stories

1. **Start** — As a visitor, when I open the link a new session is created immediately and I'm shown its join code and invite link; I just type my name and start.
2. **Invite** — As a session member I can copy the invite link or code and send it to friends.
3. **Join** — As an invitee I open the link (or enter the code on the home page), pick a display name, and see the full chat history and current plan.
4. **Plan together** — As a member I send messages; everyone sees them (and the bot's replies, streamed) in real time.
5. **Shared plan** — As a member I see a live itinerary panel (days → stops) that the bot builds/edits from the conversation, updated for everyone at once.
6. **Grounded answers** — As a member I get answers on places, seasons, permits, routes, food, and rough budgets that come from the curated KB and cite their source; weather comes from a live API; if the KB doesn't know, the bot says so.
7. **Group-aware** — The bot knows who said what, surfaces disagreements ("Asha wants wildlife, Ravi wants culture") and proposes a compromise.
8. **Rejoin** — If I close the tab and reopen the link on the same device I'm still "me" in the session.

## 4. Functional requirements

| ID | Requirement | Priority |
|---|---|---|
| F1 | `GET /` creates a session and redirects to `/s/<code>`. | Must |
| F2 | Join code: 6 chars, unambiguous alphabet, case-insensitive; max 8 participants/session (configurable). | Must |
| F3 | Participant identity via opaque token stored client-side; display name set on first entry, editable. | Must |
| F4 | Real-time message fan-out (WebSocket); presence ("Asha is typing / online"). | Must |
| F5 | Bot replies streamed token-by-token to all participants; one bot turn at a time per session (queued). | Must |
| F6 | RAG over NE KB: hybrid retrieval (vector + keyword) with metadata filters (state, season, type, permit); answers cite KB entries. | Must |
| F7 | Per turn the orchestrator retrieves KB chunks (`search_kb`) and weather (Open-Meteo) deterministically, then makes **one LLM call** that returns structured JSON (`reply`, `plan_ops`, `cites`). Bot may not state place/permit facts that are not in the retrieved chunks. | Must |
| F15 | **Pluggable LLM**: one `LLM.chat()` port; model, base URL, key and JSON-mode chosen by env config; works with hosted small models and self-hosted open models (OpenAI-compatible API); no reliance on native tool calling. Optional fallback model. | Must |
| F16 | Eval harness can run the same scenario set against several configured models and report quality + cost per model. | Should |
| F8 | Shared itinerary: structured (days → items: place, note, duration, travel hint, added-by); live-updated; versioned. | Must |
| F9 | Members can remove or reorder plan items by hand; bot sees those edits. | Should |
| F10 | Export plan as shareable read-only page / print / copy-as-text. | Should |
| F11 | Bot addressing mode: see open question Q1 (default: every message goes to the bot unless prefixed with `//`). | Must |
| F12 | Session TTL: purge after 14 days idle; "delete session" button for any member. | Should |
| F13 | Conversation context management: rolling summary beyond N messages so long sessions stay cheap and coherent. | Should |
| F14 | Admin-free KB updates: append JSONL/markdown → `make ingest` re-embeds changed docs. | Must |

## 5. Non-functional requirements

| ID | Requirement |
|---|---|
| N1 | Fan-out latency (message → other clients) p95 < 1 s; bot first token p95 < 3 s. |
| N2 | UI: one page, **mobile-first** (tabbed Chat/Plan on phones, split view on desktop), no install, no build step, single ~20 KB file; works on 3G-ish connections. |
| N3 | Cost guardrails: per-session token budget and per-IP/session rate limits; hard stop with friendly message. Target LLM cost ≤ ~2 cents per 30-turn session on a hosted small model; no vendor lock-in. |
| N4 | Privacy: no accounts, no PII beyond display name; messages stored only for session life; join codes are the only secret. |
| N5 | Security: rate-limited code lookups (anti-brute-force), tokens unguessable (≥128-bit), CORS locked, prompt-injection-resistant design (model output can only produce validated plan edits) (KB text is data, never instructions). |
| N6 | Deployable from one `docker compose up` locally and one container image + managed Postgres in cloud. |
| N7 | Observability: structured logs, per-turn trace (retrieved chunks, model used, tokens, latency). |
| N8 | Works with ≥2 instances behind a load balancer (fan-out must not assume a single process) — design requirement, may be exercised only in a test. |

## 6. Knowledge base (RAG) requirements

- **Seed**: Oxomiai's 6 places / 6 gems / 5 experts (Assam) + **~40 new entries** across the 7 other states (≥4 per state): top sites, offbeat spots, festivals, treks.
- **Also include non-place docs**: permit rules (ILP/PAP/RAP), season & road-condition guides, getting-there/transit hubs (Guwahati, Bagdogra, Dimapur, Imphal…), sample itineraries, food, rough budgets, safety/altitude notes.
- **Every chunk carries**: `state`, `region`, `type`, `best_seasons`, `source`, `last_verified` date.
- **Permit/season facts are high-risk** — must come with `source` + `last_verified` and the bot appends "verify before travel" when answering from them.
- Content authored or reviewed by a human; LLM-generated KB text is not acceptable as ground truth.

## 7. Out of scope (this POC)

User accounts/login, payments, bookings, live transport/hotel availability, maps/route optimisation, voice, offline/PWA, multi-language UI, moderation tooling, local-expert video calls (Oxomiai's feature).

## 8. Evaluation

- **Set**: ~30 scripted multi-person scenarios (2–4 simulated participants) + ~30 single-question KB probes incl. a **permit/season subset** (≥10) with known-correct answers.
- **Metrics**: grounded+helpful ≥80% (manual rubric) **on the chosen small model** — the eval is run per candidate model and the cheapest passing one is selected; fabricated permit/season facts = 0; plan completed in ≤15 turns in ≥70% of scenarios; p95 fan-out < 1 s and first-token < 3 s under 5 concurrent sessions.
- **Rubric**: reuse Oxomiai's `eval/README.md` scale; add "did the bot attribute and reconcile participants' preferences".

## 9. Open questions for review

| # | Question | Proposed default |
|---|---|---|
| Q1 | Should the bot reply to **every** message, or only when addressed? In a group, always-reply is noisy. | Bot replies to every message by default (it's a "planning room"); prefix `//` to chat with friends only. Alt: reply only on `@bot`. |
| Q2 | Can any member edit/delete the plan, or only the bot? | Any member can remove/reorder; bot does adds. |
| Q3 | Embedding model (must also be vendor-neutral). | Local `bge-small` (free, in-process). Alt: any OpenAI-compatible embeddings endpoint. |
| Q4 | ~~LLM tier~~ **Decided: very small/cheap model, pluggable.** Remaining: which 2–3 models to benchmark first? | Candidates: one hosted mini/flash/haiku-class model, one 7–8B open model via Ollama. Cheapest that clears the eval bar wins. |
| Q7 | ~~LiteLLM library or own adapter~~ **Resolved:** own thin OpenAI-compatible adapter; LiteLLM as an optional proxy container. | — |
| Q5 | Where does the KB content for 7 new states come from? | You curate/provide sources; I draft entries with citations for your review. |
| Q6 | Host target for the demo (Fly/Render/Cloud Run/…)? | Any container host with WebSocket support + managed Postgres w/ pgvector. |
