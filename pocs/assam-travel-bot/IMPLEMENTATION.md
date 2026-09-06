# Implementation Guide

This POC implements the **POC-scope** slice of `ARCHITECTURE.md` — one FastAPI
service plus a static single-file frontend, with every other target service
mocked or held in memory.

## What's built

### Backend (FastAPI, `backend/`)

| Module | Role |
|---|---|
| `app/main.py` | HTTP endpoints + pipeline wiring: `/query`, `/health`, `/kb/places`, `/kb/hidden-gems`, `/experts`, `/session/*` |
| `services/router.py` | LLM call #1 — extract intent + entities, choose route(s): `KB` / `WX` / `GEMS` / `EXPERT` / `EXP` / `REFUSE` |
| `services/knowledge_base.py` | in-memory TF-IDF search over `places.jsonl` + metadata filters |
| `services/weather.py` | Open-Meteo live current + 3-day forecast (no API key); mock fallback on error |
| `services/recommendations.py` | `HiddenGems` — TF-IDF match over `hidden_gems.jsonl`, region-filtered |
| `services/experts.py` | `ExpertDirectory` — static profile match by region + interests + availability |
| `services/synthesis.py` | LLM call #2 — compose the answer under guardrails; `intro_hidden_gems()` / `intro_local_expert()` write only a one-line framing for the structured cards |
| `services/llm_provider.py` | provider abstraction: `mock` (default), `claude`, `openai`, `openrouter` |
| `models/schemas.py` | `QueryRequest`, `BotResponse` (+ optional `hidden_gems` / `local_expert`), `HiddenGem`, `LocalExpert` |
| `config.py` | env → `Config`; picks the API-key var per provider |

### Data (`knowledge_base/`)

- `places.jsonl` — 6 seed sites. `schema.md` documents the fields.
- `hidden_gems.jsonl` — 6 curated local-only spots.
- `local_experts.jsonl` — 5 mock verified-guide profiles.

All append-only: add a line, restart the bot (KB/gems indexes build at startup).

### Frontend (`frontend/index.html`)

One self-contained file — inline CSS + JS, no build. Sidebar rail + chat column,
light/dark toggle, and dedicated renderers for place / weather / trip-plan /
**hidden-gems** / **local-expert** responses. Served by the `web` container via
`python -m http.server 3000`. The dead React scaffold (`src/`, `config.js`,
`package.json`) is not used.

### Deployment

- `docker-compose.yml` — `web` (frontend) + `bot` (FastAPI) + `db` (Postgres, declared but unused by app code).
- `.env.example` → `.env`. Default `LLM_PROVIDER=mock` runs with no keys/network.

## Quick start

```bash
cd pocs/assam-travel-bot
cp .env.example .env
docker compose up --build
# Frontend → http://localhost:3000
# API docs → http://localhost:8000/docs
```

### Real answers (not mock)

Set in `.env`, then `docker compose up --build`:

```
LLM_PROVIDER=claude
ANTHROPIC_API_KEY=sk-ant-...
```

(or `openai` / `openrouter` with their keys — see `backend/LLM_PROVIDERS.md`).

### Local backend without Docker

```bash
pip install -r backend/requirements.txt
cd backend && LLM_PROVIDER=mock python -m uvicorn app.main:app --reload
```

Then open `frontend/index.html` directly in a browser (it targets `localhost:8000`).

## Example queries

```bash
# Place info (→ KB)
curl -s localhost:8000/query -H 'Content-Type: application/json' \
  -d '{"query":"Tell me about Kamakhya Temple"}' | python3 -m json.tool

# Weather (→ WX)
curl -s localhost:8000/query -H 'Content-Type: application/json' \
  -d '{"query":"What is the weather in Guwahati this week?"}' | python3 -m json.tool

# Hidden gems (→ GEMS, returns hidden_gems[])
curl -s localhost:8000/query -H 'Content-Type: application/json' \
  -d '{"query":"Show me hidden gems near Majuli"}' | python3 -m json.tool

# Local expert (→ EXPERT, returns local_expert{})
curl -s localhost:8000/query -H 'Content-Type: application/json' \
  -d '{"query":"Can I talk to a local guide near Majuli?"}' | python3 -m json.tool

# Multi-turn: pass the same session_id to carry context
```

## API endpoints

- `GET /health` — status + `kb_places` / `hidden_gems` / `local_experts` counts.
- `POST /query` — `{answer, route_taken, sources, confidence, hidden_gems?, local_expert?, ...}`.
- `GET /kb/places` · `GET /kb/hidden-gems` · `GET /experts` — inspect the curated data.
- `GET /session/{id}` · `DELETE /session/{id}` — conversation history (in-memory).

## Testing against the eval set

Run the queries in `eval/queries.md` (30-query set with expected routes) and
score each against the rubric in `eval/README.md` — route accuracy ≥90%,
answer quality ≥80%. A harness is not yet written; score manually for now.

## Known limitations (acceptable for POC)

- KB / gems search is in-memory TF-IDF (fine for ~100 entries; swap for
  embeddings + pgvector at scale).
- Hidden gems and local experts are hand-curated; expert availability is a fixed
  string, and the "Connect via video call" button is inert.
- No expert escalation infra, no session persistence, no caching, no auth.
- `db` container runs but nothing uses it.

## To promote to production

Follow the target build order in `ARCHITECTURE.md` §10 and the `docs/standards/`
bar. First moves: real embeddings + vector DB for KB and gems; session
persistence; a real Local Expert service (KYC, calendar) and Booking + Video
services behind the "Connect" button.
