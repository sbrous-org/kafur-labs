# Oxomiai PWA (v1 spec)

## Hypothesis

A minimal, installable, **rule-based** (no LLM/API) chat PWA over a static
seed-data file of Northeast Assam destinations is enough to answer the four
core traveller intents — places/things to do, best time to visit, N-day
itinerary, category browsing — usefully enough to be worth carrying forward.
This is a narrower, offline-first sibling to `pocs/assam-travel-bot/`
(the LLM-routed version of the same idea): it tests whether the rule-based
shape alone is good enough before paying for an LLM/backend at all.

## Approach

- Next.js (App Router, TypeScript) + Tailwind, deployable to Vercel with no
  server/database — `public/data/destinations.json` is the only data source.
- Keyword/alias matching in `lib/intentMatcher.ts` — no NLP library, no LLM.
- PWA: `app/manifest.ts` (installable, standalone display) + a hand-written
  `public/sw.js` that caches the app shell and `destinations.json` for
  offline use.
- Cut for v1 (per the spec): live AI/LLM responses, real-time weather or
  transport data, user accounts/saved trips, booking integrations,
  destination detail screens, pre-built itinerary JSON (itineraries are
  generated on the fly from `avg_days_needed`).

## Exit criteria

- **Promote** — the four rule-based intents cover the majority of realistic
  traveller questions without feeling broken, and "Add to Home Screen" +
  offline chat both work on a real phone.
- **Extend** — the shape is right but matching is too brittle (misses common
  phrasings) or the destination set is too thin — worth another round tuning
  `intentMatcher.ts` / seed data before deciding.
- **Kill** — testers routinely hit the fallback message or the rule-based
  answers read as too shallow to be useful without an LLM — validates that
  `pocs/assam-travel-bot/`'s LLM-routed approach is the one worth pursuing
  instead.

## Timebox

1 week from this commit to a promote/extend/kill decision.

## Outcome

_Fill in when complete._
