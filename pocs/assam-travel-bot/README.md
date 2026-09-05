# Assam travel bot — POC Implementation

## Hypothesis

A bot combining (1) a curated knowledge base of underrated Assamese places, (2) live weather data, and (3) escalation to human local experts can answer real traveler questions accurately and usefully enough to be worth productionizing — specifically: on a test set of ~30 realistic traveler queries, a manual rubric rates ≥80% of answers "helpful and accurate," with correct routing (place question → KB, weather question → live API, out-of-scope/hyperlocal question → expert escalation) on ≥90% of queries.

## Architecture

See `ARCHITECTURE.md` for the full system design. **Implemented in `IMPLEMENTATION.md`** — FastAPI backend with containerized deployment (docker-compose).

## Stack

- **Language**: Python 3.11
- **API**: FastAPI + Uvicorn
- **LLM**: OpenAI API (GPT-3.5-turbo for routing and synthesis)
- **Weather**: OpenWeatherMap free API
- **KB Search**: In-memory TF-IDF (scalable to ~100 places; swap for PostgreSQL+pgvector for production)
- **Deployment**: Docker + docker-compose (bot + PostgreSQL ready)

## Running the POC

```bash
# Local (dev):
cp .env.example .env  # fill in OPENAI_API_KEY
cd backend && pip install -r requirements.txt
python -m uvicorn app.main:app --reload

# Containerized:
docker-compose up --build
```

Visit http://localhost:8000/docs for interactive API.

## Knowledge base

- **Schema**: `knowledge_base/schema.md` (maps oxomi-core survey fields)
- **Data**: `knowledge_base/places.jsonl` (6 sample Assam sites: Kamakhya, Umananda, Pobitora, Basistha, Deepor Beel, Kalakshetra)
- Easily expanded by appending new place entries — no rebuild needed.

## Evaluation

- **Query set**: `eval/queries.md` (30 realistic traveler queries with expected routes and scoring rubric)
- **Scoring**: Route accuracy ≥90%, answer quality ≥80% helpful-and-accurate (see `eval/README.md`)

## Exit criteria

- **Promote** — hits the accuracy/routing bar (90% correct routing, 80% quality), and the three-way routing (KB / weather / expert) is clearly necessary (i.e., simpler bot without one leg scores visibly worse).
- **Extend** — shape works but one component needs iteration (e.g., KB retrieval confidence tuning, better entity extraction).
- **Kill** — LLM hallucinates unacceptably even against curated KB, or expert escalation adds no measurable value.

## Timebox

2 weeks from this commit to promote/extend/kill decision, measured against the eval set in `eval/queries.md`.

## Outcome

_Fill in when complete._ Decision and reasons, then move to `products/assam-travel-bot/` with production checklist from `docs/standards/`.
