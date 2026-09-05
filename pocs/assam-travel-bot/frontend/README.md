# Assam Travel Bot UI

React-based chat interface for the Assam travel bot backend.

## Running locally (development)

```bash
npm install
REACT_APP_API_URL=http://localhost:8000 npm start
```

Opens http://localhost:3000 with hot-reload.

## Running in Docker

```bash
docker build -t assam-travel-bot-ui .
docker run -p 3000:3000 -e REACT_APP_API_URL=http://bot:8000 assam-travel-bot-ui
```

Or use docker-compose from the root POC directory.

## Features

- **Chat interface** — Send queries, view responses with multi-turn support
- **Source display** — See which sources (KB, weather) were used
- **Route visualization** — Shows routing decision (KB/WX/EXP/etc.)
- **Session persistence** — Conversation history within session
- **Responsive design** — Works on desktop and tablet

## Customization

- Colors/branding: edit the `<style>` section in `public/index.html`
- API URL: set `REACT_APP_API_URL` environment variable (defaults to `http://localhost:8000`)
