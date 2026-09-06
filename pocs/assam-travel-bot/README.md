# Oxomiai — Assam travel bot (POC)

**Oxomiai** is a conversational travel companion for Northeast Assam. It plans
itineraries, checks live weather, and — the two things that set it apart —
surfaces **hidden gems** that guidebooks miss and connects travellers to
**verified local guides** for a live consultation.

## Demo

▶️ **[docs/demo/oxomiai-demo.mp4](docs/demo/oxomiai-demo.mp4)** — ~30s product
walkthrough (itinerary → hidden gems → local expert). Click to play in GitHub's
viewer, or download and open locally.

<video src="https://github.com/sbrous-org/kafur-labs/raw/HEAD/pocs/assam-travel-bot/docs/demo/oxomiai-demo.mp4" controls width="480"></video>

To replay the **animated** version, open
[`docs/demo/oxomiai-demo.html`](docs/demo/oxomiai-demo.html) in a browser —
it's self-contained, no server needed. Voiceover timing is in
`docs/demo/voiceover-script.md`.

> GitHub plays the `<video>` tag inline when it can reach the raw file on the
> default branch; the `.mp4` link above always works regardless.

## Hypothesis

A bot combining (1) a curated knowledge base of underrated Assamese places,
(2) live weather data, (3) a curated hidden-gems layer, and (4) escalation to
verified local guides can answer real traveller questions accurately and
usefully enough to be worth productionizing — specifically: on a test set of
~30 realistic traveller queries, a manual rubric rates ≥80% of answers "helpful
and accurate," with correct routing (place → KB, weather → live API, offbeat →
hidden gems, "connect me to a person" → local expert, hyperlocal/booking →
human escalation) on ≥90% of queries.

## Architecture

See [`ARCHITECTURE.md`](ARCHITECTURE.md) for the full design — the **target**
microservices system and how each service maps to **what the POC actually
builds** (one FastAPI service + a static frontend, everything else mocked or
in-memory). Diagram source: `docs/architecture-diagram.mermaid`. Reference
infra sketch: `docs/infra-compose.example.yml`.

## Stack (POC)

- **Language**: Python 3.11
- **API**: FastAPI + Uvicorn
- **LLM**: pluggable — `mock` (default, offline), `claude`, `openai`, `openrouter`
- **Weather**: Open-Meteo (free, no key)
- **KB / gems search**: in-memory TF-IDF (swap for pgvector/embeddings for production)
- **Local experts**: static JSONL directory (mocked availability)
- **Frontend**: one self-contained `frontend/index.html` (no build step)
- **Deployment**: Docker + docker-compose (frontend + bot + an unused Postgres)

## Running the POC

```bash
cp .env.example .env          # defaults to LLM_PROVIDER=mock — runs with no keys
docker compose up --build
# Frontend  → http://localhost:3000
# API docs  → http://localhost:8000/docs
```

For real answer quality, set `LLM_PROVIDER=claude` (or `openai`/`openrouter`)
and the matching API key in `.env`. See `backend/LLM_PROVIDERS.md`.

Local dev without Docker: see [`IMPLEMENTATION.md`](IMPLEMENTATION.md).

## Knowledge & data

| File | What |
|---|---|
| `knowledge_base/places.jsonl` | 6 seed Assam sites (Kamakhya, Umananda, Pobitora, Basistha, Deepor Beel, Kalakshetra) |
| `knowledge_base/hidden_gems.jsonl` | 6 curated local-only spots (Chunchali Beel, Salmara Sandbar, Kamalabari Pottery Lane…) |
| `knowledge_base/local_experts.jsonl` | 5 mock verified-guide profiles |
| `knowledge_base/schema.md` | maps oxomi-core survey fields to the place schema |

All three are append-only JSONL — add a line, restart the bot, no rebuild.

## Evaluation

- **Query set**: `eval/queries.md` — ~30 realistic queries with expected routes and a scoring rubric
- **Bar**: route accuracy ≥90%, answer quality ≥80% helpful-and-accurate (`eval/README.md`)

## Exit criteria

- **Promote** — hits the accuracy/routing bar, and the routing legs are each
  clearly necessary (a bot missing one leg scores visibly worse). Then move to
  `products/oxomiai/` with the `docs/standards/` production checklist.
- **Extend** — shape works but one component needs iteration (KB retrieval
  tuning, gems ranking, entity extraction).
- **Kill** — LLM hallucinates unacceptably even against curated data, or the
  hidden-gems / expert legs add no measurable value over a plain KB bot.

## Timebox

2 weeks from this commit to a promote/extend/kill decision, measured against
`eval/queries.md`.

## Outcome

_Fill in when complete._
