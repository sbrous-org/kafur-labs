# Oxomiai frontend

The **entire** frontend is one self-contained file: **`index.html`**. Inline
`<style>` + `<script>`, no build step, no framework.

`src/`, `config.js`, `package.json` are a **dead React scaffold** — not used by
anything. The `web` container's Dockerfile only copies `index.html` and serves
it with `python -m http.server 3000`.

## Running

```bash
# via docker-compose (from pocs/assam-travel-bot/)
docker compose up --build          # → http://localhost:3000

# or standalone, for fast CSS/JS iteration
cd frontend && python3 -m http.server 3000
# then open http://localhost:3000 — needs the bot running on :8000
```

The page targets a hardcoded `const API = 'http://localhost:8000'` (top of the
`<script>`).

## What it renders

- Sidebar rail with grouped quick prompts (Plan a trip / Discover / Weather / Places)
- Chat thread with light/dark theme toggle (persisted to `localStorage`)
- Response renderers keyed off the `/query` JSON:
  - `hidden_gems[]` → hidden-gems card
  - `local_expert{}` → local-expert card
  - `Day N:` headers → trip river-timeline card
  - route `WX` → weather card · route `KB` → place card · else plain message

## Changing the look

See the **`restyle-bot`** skill (`.claude/skills/restyle-bot/`). All colour and
shape decisions are CSS custom properties on `:root`; edit those and both
`@media`/`[data-theme]` dark blocks.
