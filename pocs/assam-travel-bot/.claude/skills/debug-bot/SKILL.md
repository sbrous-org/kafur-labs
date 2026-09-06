---
name: debug-bot
description: >
  Debug the assam-travel-bot POC when something is broken or behaving wrong:
  the app won't start, containers crash or restart, /query returns 500, the
  frontend won't connect, a query routes to the wrong source (KB / weather /
  expert), the LLM output can't be parsed, or WSL/Docker itself falls over.
  Use for any "it's not working", "why did it answer X", "trace this query",
  or "check the logs" request about this POC.
---

# Debugging the Assam travel bot

Working dir for every command below: `pocs/assam-travel-bot/`.

## 1. Establish where the failure is

The stack is three containers (`docker-compose.yml`): `web` (static `index.html` on :3000),
`bot` (FastAPI on :8000), `db` (postgres, currently unused by app code). The request path is:

```
browser (index.html) --HTTP--> bot:8000 /query
   -> router.route()      LLM call #1  (intent + route JSON)
   -> knowledge_base.retrieve()        (TF-IDF, only if route has "KB")
   -> weather_service.get_weather()    (Open-Meteo, only if route has "WX")
   -> hidden_gems.retrieve()           (TF-IDF over hidden_gems.jsonl, if route has "GEMS")
   -> expert_directory.match()         (static local_experts.jsonl, if route has "EXPERT")
   -> synthesis.synthesize()  LLM call #2  (final answer; GEMS/EXPERT get a 1-line intro
                                            + structured card in BotResponse instead)
```

Routes: `KB`, `WX`, `GEMS`, `EXPERT` (connect to a guide), `EXP` (human
escalation), `REFUSE`. `health` reports `kb_places`, `hidden_gems`,
`local_experts` counts.

First triage command:

```bash
make status                 # or: docker compose ps  — are bot/web up or restarting?
curl -s localhost:8000/health | python3 -m json.tool   # bot alive + KB loaded?
curl -s localhost:3000 -o /dev/null -w '%{http_code}\n' # web serving?
```

- `health` returns `kb_places: 0` → KB file not mounted / not found (see §4).
- `bot` restarting → startup crash, go to §3.
- `health` OK but browser shows "connecting…" forever → §5 (frontend↔API).

## 2. Read the logs (the bot prints a full trace)

```bash
make bot-logs          # just the API   (docker compose logs -f bot)
make logs              # everything
```

The code logs these on failure — grep for them:

| Log line | Meaning | Fix |
|---|---|---|
| `Router error: … \| raw response: …` | LLM output failed `extract_json()` | §6 |
| `Synthesis error: …` | LLM call #2 threw | §6 / provider creds |
| `Error processing query: …` | anything else in `/query` | read the traceback above it |
| `Warning: KB file … not found` | volume mount / path wrong | §4 |
| `⚠️  Configuration error:` | missing API key for the chosen provider | §3 |

## 3. Bot won't start / config errors

`app/main.py` calls `Config.validate()` at import — it raises if the provider needs a
key that isn't set. Check the provider:

```bash
grep -E '^LLM_PROVIDER|_API_KEY' .env
```

- `LLM_PROVIDER=mock` needs **no** key and **no** network — this is the safe default for
  debugging everything that isn't answer quality. If in doubt, set it and rebuild.
- `claude` needs `ANTHROPIC_API_KEY`, `openai` needs `OPENAI_API_KEY`, `openrouter` needs
  `OPENROUTER_API_KEY`.
- After editing `.env`: `make build && make up` (env is baked via `env_file`, and `./backend`
  is bind-mounted so Python changes hot-reload but env changes need a restart).

Import/dependency errors (`ModuleNotFoundError`) → the image is stale: `make build` again.

## 4. KB not loading (`kb_places: 0`, empty answers)

- `knowledge_base/places.jsonl` is bind-mounted to `/app/knowledge_base` (see `docker-compose.yml`).
- Path resolved in `main.py`: `Path(__file__).parent.parent / "knowledge_base" / "places.jsonl"`.
- Validate the file is well-formed JSONL (one object per line, no trailing comma):

```bash
python3 -c "import json,sys; [json.loads(l) for l in open('knowledge_base/places.jsonl') if l.strip()]; print('OK')"
```

- Each entry needs at least `site_id`, `site_name`, `latitude`, `longitude`, and ideally
  `embedding_text` (falls back to `site_name` for the vector index).

## 5. Frontend can't reach the API

- `index.html` hardcodes `const API = 'http://localhost:8000'` (line ~559). It gates the
  input box on `GET /health` succeeding — if health fails, the box stays disabled.
- CORS is wide open in `main.py` (`allow_origins=["*"]`), so a blocked request is almost
  always the bot being down or on a different port, not CORS.
- Open browser devtools → Network. A failed `/health` or `/query` shows the real reason
  (connection refused = bot down; 500 = go to §2).
- Note: `frontend/src/`, `config.js`, `package.json` are an unused React scaffold. The
  container serves the single `frontend/index.html` via `python -m http.server`. Edit that file.

## 6. Wrong routing / unparseable LLM output

Reproduce the exact router decision in isolation (no Docker, uses `.env`):

```bash
cd backend && python3 -c "
from services.llm_provider import create_llm_provider
from config import Config
from services.router import QueryRouter
r = QueryRouter(create_llm_provider(Config.get_llm_config()))
import json; print(json.dumps(r.route('YOUR QUERY HERE'), indent=2))
"
```

- **Router returns `route: ['REFUSE']` unexpectedly** → the LLM call threw and hit the
  `except` fallback in `router.py`. Check `raw response` in the logs.
- **Output has prose / ``` fences around the JSON** → `extract_json()` in `router.py`
  handles fenced + first-`{...}` blocks; if it still fails the model returned no JSON
  object at all. Lower `temperature` (already 0.1) or tighten the system prompt.
- **`mock` provider mis-routes** → `MockProvider.invoke()` in `llm_provider.py` does
  keyword matching; add/adjust the keyword lists there. Mock is deterministic, so a
  mock mis-route is a code bug, not flakiness.
- Routing rules live in the `system_prompt` string in `services/router.py`. Synthesis
  guardrails live in the `system_prompt` in `services/synthesis.py`.

## 7. WSL / Docker instability

This POC has no GPU component anymore (Ollama was removed — `LLM_PROVIDER=mock` or a
hosted API only). If Docker Desktop / the WSL VM still crashes:

- `docker compose down` then restart Docker Desktop; `wsl --shutdown` from Windows as a
  last resort.
- Run the backend **without Docker** to isolate:

```bash
cd backend && pip install -r requirements.txt
LLM_PROVIDER=mock python3 -m uvicorn app.main:app --reload --port 8000
# then open frontend/index.html directly in a browser (API points at localhost:8000)
```

- Check `docker stats` for a container eating RAM; lower Docker Desktop's memory cap or
  add limits under each service in `docker-compose.yml` if the box is tight.

## 8. Quick end-to-end smoke test

```bash
curl -s -X POST localhost:8000/query -H 'Content-Type: application/json' \
  -d '{"query":"Tell me about Kamakhya Temple"}' | python3 -m json.tool
curl -s -X POST localhost:8000/query -H 'Content-Type: application/json' \
  -d '{"query":"What is the weather in Guwahati this week?"}' | python3 -m json.tool
```

Expect `route_taken` of `KB` and `WX` (or `KB, WX`) respectively, and a non-empty `answer`.
With `LLM_PROVIDER=mock` the answer text is canned `[mock LLM] …` — that is expected, only
the routing and `sources` are meaningful in mock mode.
