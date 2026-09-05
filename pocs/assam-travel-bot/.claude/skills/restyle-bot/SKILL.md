---
name: restyle-bot
description: >
  Change the look of the assam-travel-bot frontend: colours, fonts, spacing,
  the header, the chat bubbles, the trip-plan / weather / place cards, the
  sidebar, light/dark theming, or the responsive layout. Use for "restyle the
  UI", "change the colour scheme", "make it look like X", "adjust the card
  design", "tweak the layout / spacing / fonts", or any visual/CSS change to
  this POC. Not for backend answer content — that's the `edit-bot` skill.
---

# Restyling the Assam travel bot frontend

The **entire** frontend is one file: `pocs/assam-travel-bot/frontend/index.html`
(~747 lines). Inline `<style>` in `<head>`, markup in `<body>`, inline `<script>` at the
bottom. No build step, no framework. (`frontend/src/`, `config.js`, `package.json` are a
dead React scaffold — ignore them.)

The container serves this file verbatim via `python -m http.server 3000`. To see changes:
just reload `http://localhost:3000` — no rebuild. (If running `make up`, the `web`
container only re-copies on `make build`; for fast iteration open the file directly in a
browser, or `cd frontend && python3 -m http.server 3000`.)

## The design system (CSS custom properties)

All colour/shape decisions are tokens on `:root` (around line 9). Change the palette here
and it propagates everywhere:

```
--tea / --tea-light        deep green   — headings, user bubble, primary accents
--terracotta / --*-light   burnt orange — buttons, section icons, "gamosa" strip
--muga                     gold          — (Assam silk) accent, currently light use
--river / --river-light    slate blue    — tertiary accent
--cream                    page background
--panel                    card/surface background
--ink / --ink-soft         text / muted text
--border                   hairlines
--radius                   global corner radius (10px)
```

Fonts: `Fraunces` (serif, headings) + `Work Sans` (body), loaded from Google Fonts on
line 7. Swap the `<link>` and the two `font-family` declarations (`body`, and the
`h1`/`h2`/`h3` / `.trip-plan-head` rules).

## Theming (light / dark)

Three-state, already wired (lines ~25–45):
- bare `:root` = full light palette (the source of truth).
- `@media (prefers-color-scheme: dark)` guarded by `:root:not([data-theme="light"])` =
  dark overrides.
- `:root[data-theme="dark"]` = same overrides so an explicit toggle wins.

**Rule:** every token gets its real value on bare `:root`. In the dark blocks, only
*re-declare* tokens that change. Never define a colour only inside a media/attribute block.
There is currently no visible theme toggle — `data-theme` would have to be set on `<html>`
by a script if you want one.

## Markup regions (in `<body>`, from line ~488)

| Region | Class | What it is |
|---|---|---|
| Header | `.header` / `.header-top` / `.gamosa-strip` | title, tagline, woven-stripe motif |
| Layout | `.app` > `.main` (CSS grid) | 2-col: chat + sidebar; collapses to 1-col < 780px |
| Chat | `.chat-panel` > `.messages` | scrolling message list |
| Empty state | `.welcome` | icon + "Plan your journey" |
| Quick actions | `.chip-strip` (mobile) / `.sidebar` `.sb-section` `.sb-btn` (desktop) | canned queries; keep both in sync |
| Input | `.input-bar` input + button | |
| Response cards | `.trip-plan`, `.weather-card`, `.place-card`, `.bubble.bot`, `.bubble.error` | see below |

## Response cards are built in JS, not just CSS

`renderResponse(text, routeTaken)` (line ~646) picks a renderer by content/route:

- day headers present (`DAY_HEADER_RE`) → `renderTripPlan()` → `.trip-plan` with
  `.trip-plan-head`, `.trip-preamble`, `.days` > `.day-card` (`.day-num`, `.day-title`,
  `.activity`).
- route includes `WX` → `renderWeatherResponse()` → `.weather-card` (`.head` + `.body`).
- route includes `KB` → `renderPlaceResponse()` → `.place-card` (`.head` + `.body`).
- else → `addMessage('bot', …)` → plain `.bubble.bot`.

So restyling a card = edit its CSS block **and**, if you change class names or structure,
the matching `render*` function's template string. The inline `<svg>` icons live in those
template strings and in the sidebar markup — edit them in place (they use
`stroke="currentColor"`, so colour follows the surrounding text/`--terracotta`).

Text formatting: `mdToHtml()` (line ~639) does escape-then-minimal-markdown (`**bold**`,
strips list bullets). Keep using it for any user/LLM text you inject — it's the XSS guard.

## Recipes

- **New colour scheme:** edit the `:root` tokens + the dark overrides. Don't hunt for
  hex values in rules — there shouldn't be any outside `:root` except a few `#fff`/`#fdfaf3`
  on dark accent backgrounds and `color-mix()` in `.bubble.error`.
- **Different vibe (fonts + shape):** swap the Google Fonts `<link>`, the `font-family`
  rules, and `--radius`.
- **Restyle a card:** find its `/* --- … card --- */` comment block in `<style>`; adjust.
  Structure changes → also update the `render*` template.
- **Change quick prompts:** edit both `.chip-strip` buttons (line ~513) and `.sidebar`
  `.sb-btn`s (line ~532) — `onclick="quickSend('…')"`.
- **Layout width / columns:** `.app` `max-width` (line ~60) and `.main`
  `grid-template-columns` (line ~117); responsive breakpoint at `@media (max-width: 780px)`
  (line ~472) — per the comment there, keep responsive overrides *after* the base rules.
- **Header motif:** `.gamosa-strip` is a pure-CSS `repeating-linear-gradient`; change
  angle/colours/stripe widths there.

## Before finishing

- Reload at a narrow width (< 780px) — sidebar hides, `.chip-strip` shows; check nothing
  overflows horizontally (`.messages` and cards should wrap/scroll internally).
- Check both themes (OS dark mode toggle).
- Send one of each: a trip query ("Plan a 2-day Assam trip"), a weather query, a place
  query, and something out-of-scope — to see all four renderers.
- If you only want a visual mock (not the live app), consider the `design` skill instead.
