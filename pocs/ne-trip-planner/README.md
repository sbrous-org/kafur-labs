# NE Trip Planner — shared-session travel bot (POC)

> **Status: design review — nothing implemented yet.** Open
> [`design/index.html`](design/index.html) in a browser for the visual design,
> watch the 58 s flow video [`design/ne-trip-planner-flow.mp4`](design/ne-trip-planner-flow.mp4)
> (source: `design/flow-video.html`, re-render with `python design/render_video.py`),
> or read [`REQUIREMENTS.md`](REQUIREMENTS.md) and [`DESIGN.md`](DESIGN.md).

## Hypothesis

A group of friends can open one link, join a shared session by code, and — chatting
with a single bot that is grounded in a curated Northeast India knowledge base —
converge on a concrete multi-day itinerary in one sitting — **using a very small, cheap, swappable model** — with ≥80% of bot
answers rated accurate and grounded, and shared updates reaching every
participant in under 1 second (p95).

This is distinct from `pocs/assam-travel-bot` (Oxomiai), which tests single-user
Q&A, hidden gems and expert routing. This POC tests **collaboration + a shared,
live itinerary**. It reuses Oxomiai's KB data and schema as a seed.

## Approach

Cloud-agnostic containers: one FastAPI service (REST + WebSocket) + a static
frontend, Postgres with pgvector for sessions, messages, the shared plan and RAG
chunks, and **a small, cheap LLM behind a pluggable provider-agnostic port** (hosted or self-hosted; one call per turn, JSON output). No login — link + 6-char
join code + display name. Full detail in `DESIGN.md`.

Deliberately cut: accounts, payments/bookings, live transport data, maps, voice,
offline/PWA, multi-language.

## Exit criteria

- **Promote** — meets all of (on the cheapest model that clears the bar): ≥80% helpful+grounded on the eval set (`REQUIREMENTS.md` §8),
  0 fabricated permit/season facts on the permit test subset, plan reached
  within ≤15 turns in ≥70% of scripted group scenarios, p95 fan-out < 1 s.
  Then move to `products/` and write the ADRs listed in `DESIGN.md` §10.
- **Extend** — shared plan UX works but retrieval quality or turn-taking rules need another round.
- **Kill** — bot in a multi-person room is noisy/confusing enough that groups prefer a single-user bot, or KB grounding can't stop fabricated permit/season facts.

## Timebox

2 weeks of build after design sign-off (see `DESIGN.md` §11).

## Outcome

_Fill in when the POC concludes._
