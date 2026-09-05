# Implementation Guide

This POC implements the architecture described in `ARCHITECTURE.md` with a containerized, scalable design suitable for production graduation.

## What's built

### Backend (FastAPI)
- **Router** (`services/router.py`) — Uses OpenAI API to extract intent and entities, route queries to KB/weather/expert.
- **Knowledge Base** (`services/knowledge_base.py`) — In-memory TF-IDF vector search over place descriptions + metadata filtering.
- **Weather Service** (`services/weather.py`) — Calls OpenWeatherMap free API for current/forecast data.
- **Answer Synthesis** (`services/synthesis.py`) — Composes natural-language response using LLM, respects guardrails (no fabricated weather, grounded place facts).
- **Main API** (`app/main.py`) — FastAPI with endpoints for querying, session management, KB inspection.

### Knowledge Base
- **Schema** (`knowledge_base/schema.md`) — Maps oxomi-core survey fields to bot-friendly structure.
- **Data** (`knowledge_base/places.jsonl`) — Sample 6 Assam sites (Kamakhya, Umananda, Pobitora, etc.) ready for expansion.

### Deployment
- **Docker** — Containerized FastAPI service.
- **Docker Compose** — Orchestrates bot + PostgreSQL (ready for session persistence, logging).
- **.env.example** — API key configuration template.

## Quick start

### 1. Setup

```bash
cd pocs/assam-travel-bot
cp .env.example .env
# Edit .env: add OpenAI API key and (optional) OpenWeatherMap key
```

### 2. Run locally (without Docker)

```bash
pip install -r backend/requirements.txt
cd backend
OPENAI_API_KEY=sk-... python -m uvicorn app.main:app --reload
```

Visit http://localhost:8000/docs (Swagger UI) to try queries.

### 3. Run with Docker

```bash
docker-compose up --build
# Bot runs on http://localhost:8000
```

## Example queries (for eval set)

```bash
# Place info
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"query": "Tell me about Kamakhya Temple"}'

# Weather (compound)
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What is the weather like in Guwahati this week?"}'

# Multi-turn
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "I want to visit a wildlife sanctuary",
    "session_id": "session_123"
  }'

# Follow-up
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is the weather there?",
    "session_id": "session_123"
  }'
```

## Expanding the knowledge base

Add a place to `knowledge_base/places.jsonl`:

1. Verify the place against `oxomi-core/documentation/docs/surveys.md` or similar survey.
2. Create a JSON entry matching the schema in `knowledge_base/schema.md`.
3. Append one line to `places.jsonl`.
4. Restart the bot (KB reloads on startup).

Example:

```json
{"site_id": "new_place_id", "site_name": "New Place", "site_type": "temple", ...}
```

## API endpoints

- `GET /health` — Service status + KB place count.
- `POST /query` — Answer a traveler query. Returns `{answer, sources, route_taken, confidence, ...}`.
- `GET /kb/places` — List all KB places (id, name, type, location).
- `GET /session/{session_id}` — Retrieve conversation history.
- `DELETE /session/{session_id}` — Clear session.

See `app/main.py` or http://localhost:8000/docs for full schema.

## Testing against eval set

Run queries from `eval/queries.md` (30-query set with expected routes and scoring rubric):

```bash
python eval/run_eval.py  # TODO: implement evaluation harness
```

Score each query against the rubric in `eval/README.md` (route accuracy ≥90%, answer quality ≥80%).

## Known limitations & POC-to-production TODOs

**Limitations (acceptable for POC):**
- Knowledge base is in-memory (fine for ~100 places, swap for PostgreSQL for scale).
- TF-IDF search (works for short descriptions, but vector embeddings would be better for semantic search).
- No real expert escalation (mocked with a static response).
- No session persistence (in-memory store, lost on restart).
- No caching (every query hits OpenAI).

**To promote to production:**
1. Migrate KB to PostgreSQL with vector search (pgvector or similar).
2. Add session persistence (log to DB).
3. Implement real expert routing (notification, SLA, response tracking).
4. Add rate limiting and auth.
5. Instrument for monitoring (Prometheus metrics, structured logging).
6. Deploy on Kubernetes or similar (docker-compose is dev-only).
7. Create UI (frontend not yet scaffolded).

See `docs/standards/` and `products/README.md` for the production bar when promotion is considered.
