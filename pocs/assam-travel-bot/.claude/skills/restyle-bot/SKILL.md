---
name: restyle-bot
description: >
  Change the look of the assam-travel-bot ("Oxomiai") frontend: colours, fonts,
  spacing, the sidebar/rail, the chat bubbles, the trip-plan / weather / place /
  hidden-gems / local-expert cards, light/dark theming, or the responsive
  layout. Use for "restyle the UI", "change the colour scheme", "make it look
  like X", "adjust the card design", "tweak the layout / spacing / fonts", or
  any visual/CSS change to this POC. Not for backend answer content — that's the
  `edit-bot` skill.
---

# Restyling the Oxomiai frontend

The **entire** frontend is one file: `pocs/assam-travel-bot/frontend/index.html`
(~1400 lines). Inline `<style>` in `<head>`, markup in `<body>`, inline
`<script>` before a `<template id="welcomeTemplate">` at the end. No build step,
no framework. (`frontend/src/`, `config.js`, `package.json` are a dead React
scaffold — ignore them.)

The `web` container serves this file verbatim via `python -m http.server 3000`.
To see changes: reload `http://localhost:3000` — but the container only
re-copies the file on `docker compose build`. For fast iteration open the file
directly in a browser, or `cd frontend && python3 -m http.server 3000`. The page
calls the backend at a hardcoded `const API = 'http://localhost:8000'` (top of
the `<script>`).

## The design system (CSS custom properties)

All colour/shape decisions are tokens on `:root` (starts ~line 12). Change the
palette here and it propagates. Current palette is warm Assam-inspired
(dark-green + terracotta + river-blue + gold on cream):

```
--bg / --surface / --surface-2 / --surface-3   page + card grounds
--text / --text-soft / --text-faint            text ramp
--border / --border-strong                     hairlines
--brand / --brand-bright / --brand-ink / --brand-tint    deep green — logo, avatars, KB accents
--accent / --accent-bright / --accent-tint     terracotta — send button, expert card, EXP tag
--gold                                          Assam-silk gold — hidden-gems accents
--sky / --sky-2 / --sky-tint                    river-blue — user bubble, weather card
--on-brand                                      text on brand/accent fills (cream)
--shadow-xs…-lg, --r-xs…-xl, --font, --display, --ease   elevation, radii, fonts, easing
```

Fonts: `Fraunces` (`--display`, headings/card titles) + `Inter` (`--font`,
body), from Google Fonts (`<link>` ~line 9).

## Theming (light / dark)

Three-state, already wired:
- bare `:root` = full light palette (source of truth).
- `@media (prefers-color-scheme: dark)` guarded by `:root:not([data-theme="light"])`.
- `:root[data-theme="dark"]` = same overrides so the explicit toggle wins.

The two dark blocks are identical value sets — **edit both**. There is a working
theme toggle (`toggleTheme()`, persisted to `localStorage['atp-theme']`); the
sun/moon icon buttons are in `.rail-foot` and `.topbar`.

**Rule:** every token gets its real value on bare `:root`; dark blocks only
re-declare what changes. Never define a colour only inside a media/attribute block.

## Markup regions (in `<body>`)

| Region | Class | What it is |
|---|---|---|
| Sidebar | `.rail` > `.brand`, `.new-chat`, `.rail-group` (`h3` + `.rail-btn`), `.rail-foot` | brand, new-chat, grouped quick prompts, status + theme toggle |
| Mobile top bar | `.topbar` | shown < 880px when `.rail` hides |
| Chat column | `.chat` > `.thread` > `.thread-inner` (`#messages`) | scrolling turn list |
| Welcome / empty state | `.welcome` (`.eyebrow`, `h1`, `.lede`, `.suggestions` > `.sugg`) | duplicated in `<template id="welcomeTemplate">` for "new conversation" — **keep both in sync** |
| Turn | `.turn` (`.user` / `.bot`) > `.avatar` + `.turn-body` | `.turn.user` reverses row; user text in `.bubble` |
| Composer | `.composer` > `.composer-inner` > `.field` (textarea + `.send`) | |
| Response cards | `.card` + `.place-card` / `.weather-card` / `.trip-card` / `.gems-card` / `.expert-card`; route tags `.tags` > `.tag.kb/.wx/.gems/.expert/.exp` | see below |

## Response cards are built in JS, not just CSS

`renderResponse(data)` (~line 1200) receives the whole `/query` JSON and picks a
renderer:

- `data.hidden_gems` (array) → `renderGems()` → `.card.gems-card` > `.gems-list` > `.gem` (`.g-ico`, `.g-name`, `.g-near`, `.g-desc`, `.g-meta`, `.g-pick`).
- `data.local_expert` (object) → `renderExpert()` → `.card.expert-card` > `.expert-body` (`.expert-top`, `.expert-photo`, `.expert-name`, `.expert-avail`, `.expert-specialties`, `.expert-connect`).
- else, day headers present (`DAY_HEADER_RE`) → `renderTripPlan()` → `.card.trip-card` > `.days` > `.day` (`.num`, `.day-title`, `.act`).
- else route includes `WX` → `renderWeather()` → `.card.weather-card`.
- else route includes `KB` → `renderPlace()` → `.card.place-card`.
- else → `msgNode()` → plain `.msg`.

For GEMS/EXPERT the LLM writes only a one-line intro (`data.answer`) rendered as
a `.msg` above the card; the card data itself is structured and never
paraphrased. Route → tag mapping is `ROUTE_META`.

So restyling a card = edit its CSS block **and**, if you change class names or
structure, the matching `render*` template string. Inline `<svg>` icons live in
those template strings (`ICON_*` consts) and the rail markup — they use
`stroke="currentColor"`.

Text formatting: `mdToHtml()` / `escapeHtml()` — escape-then-minimal-markdown.
Keep using them for any user/LLM text you inject (XSS guard).

## Recipes

- **New colour scheme:** edit the `:root` tokens + both dark blocks. No hex
  values should live in rules (a few `#fff`-ish on-fill colours and `color-mix()`
  aside).
- **Different vibe (fonts + shape):** swap the Google Fonts `<link>`, `--font` /
  `--display`, and the `--r-*` radii.
- **Change quick prompts:** edit the `.rail-group` `.rail-btn`s **and** the
  `.suggestions` `.sugg`s in *both* the inline `.welcome` and
  `#welcomeTemplate` — all use `onclick="quickSend('…')"`.
- **Restyle a card:** find its `/* --- */` block in `<style>`; adjust. Structure
  change → also update the `render*` template.
- **Layout width / columns:** `.app` `grid-template-columns` + `max-width`;
  responsive breakpoint `@media (max-width: 880px)`.

## Before finishing

- Reload < 880px — `.rail` hides, `.topbar` shows; nothing should scroll
  horizontally (cards wrap/scroll internally).
- Check both themes (toggle button + OS dark mode).
- Send one of each: trip query, weather query, place query, "show me hidden gems
  near Majuli", "talk to a local guide near Majuli", and something out of scope
  — exercises every renderer. With `LLM_PROVIDER=mock` the prose is canned but
  routing + cards are real.
- Visual-mock only (not the live app)? Use the `design` skill instead.
