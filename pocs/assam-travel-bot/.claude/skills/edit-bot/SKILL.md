---
name: edit-bot
description: >
  Navigate and safely edit the assam-travel-bot POC: find where a given piece
  of behavior lives, then change it. Use for "add a place to the knowledge
  base", "change how routing works", "adjust the answer tone / guardrails",
  "add an API endpoint", "tune KB retrieval", "swap or configure the LLM
  provider", "change the weather source", or any "where is X handled / how do
  I change X" question about this POC.
---

# Editing the Assam travel bot

Working dir: `pocs/assam-travel-bot/`. It's a FastAPI backend + a single-file HTML
frontend. Backend code is bind-mounted (`./backend` → `/app`), so Python edits
hot-reload under `make up`; `.env` and dependency changes need `make build && make up`.

## Map: what lives where

| Want to change… | File | Notes |
|---|---|---|
| Routing logic (KB / WX / GEMS / EXPERT / EXP / REFUSE) | `backend/services/router.py` | it's the `system_prompt` string + `extract_json()` |
| Final answer wording / tone / guardrails | `backend/services/synthesis.py` | `synthesize()` system prompt; also `intro_hidden_gems()`, `intro_local_expert()`, `handle_no_match()`, `handle_escalation()` |
| KB content (the places) | `knowledge_base/places.jsonl` | one JSON object per line; no rebuild needed (bind-mounted) |
| Hidden-gems content | `knowledge_base/hidden_gems.jsonl` | curated offbeat spots; `gem_id`, `name`, `near`, `embedding_text`, … |
| Local-guide directory | `knowledge_base/local_experts.jsonl` | mock profiles; `availability` is a fixed string |
| KB search behaviour | `backend/services/knowledge_base.py` | TF-IDF; `retrieve()`, `_passes_filters()` |
| Hidden-gems matching | `backend/services/recommendations.py` | `HiddenGems.retrieve(query, region)`, TF-IDF |
| Expert matching | `backend/services/experts.py` | `ExpertDirectory.match(region, interests)` |
| Weather provider / fields | `backend/services/weather.py` | currently Open-Meteo, **no API key** |
| LLM providers + factory | `backend/services/llm_provider.py` | `mock`, `claude`, `openai`, `openrouter` |
| Which provider + keys | `.env` (copy from `.env.example`) | `LLM_PROVIDER=` and the matching `_API_KEY` |
| Config loading / validation | `backend/config.py` | env → `Config`; `get_llm_config()` builds the provider dict |
| HTTP endpoints + pipeline wiring | `backend/app/main.py` | `/query`, `/health`, `/kb/places`, `/kb/hidden-gems`, `/experts`, `/session/*` |
| Request/response shapes | `backend/models/schemas.py` | pydantic `QueryRequest`, `BotResponse`, `HiddenGem`, `LocalExpert` |
| Frontend (everything visual) | `frontend/index.html` | single file, inline `<style>` + `<script>`; see the `restyle-bot` skill |
| Make targets / run flow | `Makefile` | `prereq`, `build`, `up`, `down`, `logs`, `bot-logs`, `status` |

`backend/frontend/src/`, `frontend/config.js`, `frontend/package.json` are an unused React
scaffold — the deployed frontend is `frontend/index.html` only. Don't edit the scaffold.

## Common edits

### Add / edit a knowledge-base place

1. Append one line to `knowledge_base/places.jsonl` (JSON object, no trailing newline issues).
2. Required-ish fields: `site_id` (unique slug), `site_name`, `site_type`, `district`,
   `latitude`, `longitude`, `short_description`, `visiting_hours`, `unique_attractions`
   (list), `best_seasons` / `avoid_seasons` (lists), `embedding_text`.
3. `embedding_text` is what TF-IDF indexes — make it a dense paragraph with the name,
   description, attractions, and significance. If omitted it falls back to `site_name` only
   (bad retrieval). Full field list: `knowledge_base/schema.md`.
4. Validate + reload:
   ```bash
   python3 -c "import json; [json.loads(l) for l in open('knowledge_base/places.jsonl') if l.strip()]; print('valid')"
   curl -s localhost:8000/health          # kb_places count should go up (reload on next request under --reload)
   ```
   The KB is built at process start — restart the bot (`make down && make up`, or the
   `--reload` watcher fires on any `backend/` change) to re-index.

### Change routing behaviour

Edit the `system_prompt` in `backend/services/router.py`. The contract the rest of the
code depends on: the returned JSON must have `intent`, `entities` (with `place_names`,
`region`, `season`, `activity`, `interests`), `route` (a list drawn from `KB`, `WX`,
`GEMS`, `EXPERT`, `EXP`, `REFUSE`), `reasoning`, `confidence`. Keep `route` values
exactly those tokens — `main.py` branches on `"KB" in route`, `"GEMS" in route`, etc.
`GEMS` and `EXPERT` responses return structured cards in `BotResponse.hidden_gems` /
`.local_expert` (rendered as cards by the frontend) plus a one-line LLM intro.

For `LLM_PROVIDER=mock`, also update the keyword lists in `MockProvider.invoke()`
(`llm_provider.py`) so offline/eval runs match the new rules.

### Change answer tone or guardrails

Edit the `system_prompt` and `user_message` template in `AnswerSynthesis.synthesize()`
(`backend/services/synthesis.py`). The weather-facts-verbatim and admit-unknown-places
guardrails are load-bearing per `ARCHITECTURE.md` — keep them.

### Configure / swap the LLM provider

- Fastest, no cost, no network: `LLM_PROVIDER=mock` in `.env`. Deterministic canned
  answers; routing still works via keyword matching.
- Hosted: set `LLM_PROVIDER=claude|openai|openrouter` and the matching key in `.env`,
  then `make build && make up`. Optional `LLM_MODEL=` overrides the per-provider default.
- New provider: add a `LLMProvider` subclass in `llm_provider.py` and a branch in
  `create_llm_provider()`; add key mapping in `config.py` (`LLM_PROVIDER == ...`).
  See `backend/LLM_PROVIDERS.md`.

### Add an endpoint

Add to `backend/app/main.py`, reuse the module-level `knowledge_base`, `hidden_gems`,
`expert_directory`, `router`, `weather_service`, `synthesis`, `llm_provider` singletons.
Add request/response models to `backend/models/schemas.py`. FastAPI auto-docs at
`localhost:8000/docs`.

## Verify a change

```bash
# backend logic without Docker:
cd backend && LLM_PROVIDER=mock python3 -m uvicorn app.main:app --reload

# or full stack:
make build && make up && make bot-logs

# exercise it:
curl -s -X POST localhost:8000/query -H 'Content-Type: application/json' \
  -d '{"query":"..."}' | python3 -m json.tool
```

Regression-check routing against the eval set in `eval/queries.md` (30 queries with
expected routes) — that's the POC's success bar per `README.md`.

## Known doc drift (safe to fix if you touch these)

- `.env.example` mentions `OPENWEATHER_API_KEY`, but `weather.py` uses Open-Meteo and
  needs no key.
- `Makefile` `prereq` doesn't offer the `mock` option in its menu.
- `frontend/src/`, `frontend/config.js`, `frontend/package.json` are a dead React
  scaffold; the live frontend is `frontend/index.html` only.
