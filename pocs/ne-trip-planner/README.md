# NE Trip Planner — shared-session travel bot (POC)

Open a link → a session is created → friends join with a 6-character code → everyone
plans a Northeast India trip in one chat, with a bot that answers from a curated
knowledge base and builds a **shared, live itinerary**. Mobile-first UI.

> **Status: implemented (v0).** Design: [`design/index.html`](design/index.html) ·
> [`DESIGN.md`](DESIGN.md) · [`REQUIREMENTS.md`](REQUIREMENTS.md) · flow video
> [`design/ne-trip-planner-flow.mp4`](design/ne-trip-planner-flow.mp4). Decisions: ADRs 0002–0005.

## Run it

```bash
cp .env.example .env            # defaults: mock LLM + hash embeddings -> no keys, no model download
docker compose up --build       # http://localhost:8000  (open it on your phone via your LAN IP)
```

Real model, still container-only:

```bash
# self-hosted small model (stock ollama image pulls qwen2.5:1.5b-instruct)
LLM_PROVIDER=openai docker compose --profile ollama up --build
# any other provider: set LLM_PROVIDER=openai + LLM_BASE_URL / LLM_MODEL / LLM_API_KEY in .env
# (OpenAI, OpenRouter, Groq, vLLM, ...). Anthropic/Gemini/Bedrock: use the stock LiteLLM proxy:
#   docker compose --profile litellm up   (edit litellm.config.yaml first)
```

Dev without Docker: Postgres 16 + pgvector, then `pip install -r backend/requirements-dev.txt`,
`DATABASE_URL=... make dev`, `make test`.

## What is reused vs built

| Piece | Reused (stock image / lib) | Built here |
|---|---|---|
| Database + vectors | `pgvector/pgvector:pg16` | schema, hybrid retrieval (~100 lines) |
| Self-hosted LLM + embeddings | `ollama/ollama` (opt-in profile) | — |
| Multi-provider gateway | `ghcr.io/berriai/litellm` (opt-in profile) | — |
| Web/WebSocket server | FastAPI, uvicorn, asyncpg, httpx | sessions, hub, bot pipeline, plan logic |
| Frontend | none (static HTML/CSS/JS, no build) | one responsive page |
| KB content | Oxomiai's Assam seed (`places`, `hidden_gems`) | 40 new entries for all 8 states (**draft, unverified**) |

## How a turn works

1. A member message is stored and fanned out (Postgres `LISTEN/NOTIFY`, works on N instances).
2. A per-session turn lock (Postgres advisory lock) batches queued messages into one bot turn.
3. The app retrieves KB chunks (full-text + vector, state-aware, permit/season guides pinned) and optional live weather — **no LLM involved**.
4. **One** streamed call to the configured LLM: reply text, then optionally `###PLAN` + `{"ops":[...]}`.
5. Plan ops are validated (unknown KB ids dropped, humans can only move/remove), versioned, broadcast. Replies cite KB entries; permit/season answers carry "verify before travel".

`//` before a message = friends-only (bot ignores it); there is a toggle for the same in the UI.

## Verified vs not

- **Verified here**: 14 automated tests against a real Postgres 16 + pgvector (create/join/cap, auth, real-time fan-out between two sockets, streaming, citations, plan edits, `//`, reconnect, permit grounding, unknown-topic refusal, OpenAI-compatible adapter against a fake streaming server); UI driven in headless Chromium with a desktop and a phone-sized browser in one session (screenshots in `design/screens/`).
- **Not verified**: `docker compose up` itself (no Docker daemon in the build sandbox — compose file validates with `docker compose config`); a real LLM (Ollama / hosted) — only the mock and a fake OpenAI-compatible server were exercised; live weather (Open-Meteo unreachable from the sandbox, degrades silently); multi-instance fan-out (designed for, not run).
- **Content caveat**: the 40 new KB entries are general-knowledge drafts for review, not verified sources. Permit/season entries are flagged `high_risk` and shown as "unverified" in the UI.

## Not built yet

Eval harness (scenario set + per-model cost/quality), rolling conversation summary, read-only share page, per-person preference extraction, accounts, presence that survives crashes.

## Hypothesis

A group of friends can open one link, join a shared session by code, and — chatting
with one bot grounded in a curated Northeast India KB, **using a very small, cheap, swappable model** —
converge on a concrete multi-day itinerary in one sitting, with ≥80% of answers accurate and grounded,
and shared updates reaching everyone in under 1 second (p95).

## Exit criteria

- **Promote** — on the cheapest model that clears the bar: ≥80% helpful+grounded on the eval set (`REQUIREMENTS.md` §8), 0 fabricated permit/season facts on the permit subset, plan reached in ≤15 turns in ≥70% of scripted group scenarios, p95 fan-out < 1 s. Then move to `products/` with the standards checklist.
- **Extend** — shared plan UX works but retrieval quality or turn-taking rules need another round.
- **Kill** — the bot in a multi-person room is noisy/confusing enough that groups prefer a single-user bot, or KB grounding cannot stop fabricated permit/season facts.

## Timebox

2 weeks from design sign-off (build started; eval + real-model trial remain).

## Outcome

_Fill in when the POC concludes._
