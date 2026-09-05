# Evaluation set

Built before the pipeline, per `ARCHITECTURE.md` → Evaluation. This is what the exit criteria in `../README.md` get measured against — don't build against gut feel, build against this.

## How to score a run

For each query in `queries.md`, run it through the bot and record:

- **Route taken** vs. **expected route** — pass/fail, no partial credit. This is the ≥90%-correct-routing bar.
- **Answer quality** — 1 (helpful and accurate), 0.5 (partially right or right-but-incomplete), 0 (wrong, unhelpful, or hallucinated) against the "good answer looks like" note for that query. This is the ≥80%-helpful bar (count 1s + 0.5×0.5s over total).
- **Guardrail check** for weather and expert-flagged queries specifically: did it ever state a weather fact not traceable to the API response, or answer a should-be-escalated query as if it were confident KB fact? A single guardrail violation on these is worth flagging even if the surface answer looked fine — it's the failure mode most likely to actually mislead a traveler.

## A caveat on the place facts below

The specific places, seasons, and details in `queries.md` are illustrative, drawn from general knowledge of Assam tourism — not verified against a curated source. Before this becomes real knowledge-base content (as opposed to test-query scaffolding), have it checked against a local expert or authoritative source. Don't let eval-set text quietly become production KB content without that check.

## Composition

30 queries: ~8 pure place-info, ~6 pure weather, ~5 itinerary (spans KB + weather), ~5 expert-escalation, ~6 edge cases (out-of-KB place, out-of-scope/non-Assam, ambiguous/compound, multi-turn, safety-adjacent). The edge cases matter more than the easy ones — a bot that's good at the easy 24 and bad at the 6 edge cases is not ready to promote.
