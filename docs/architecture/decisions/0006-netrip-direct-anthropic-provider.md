# ADR-0006: Add a direct Anthropic provider; drop LiteLLM from the deployed stack

Date: 2026-10-16
Status: Accepted

## Context

ADR-0004 chose a LiteLLM proxy container as the way to reach any non-OpenAI-compatible
vendor (Anthropic, Gemini, Bedrock), keeping the app itself vendor-free. That holds up
fine with normal resources, but this POC's first real deployment target is a GCP
`e2-micro` Always Free VM — 1 shared vCPU, ~1 GB RAM, by design (see the hosting-cost
discussion that led here). Running Postgres+pgvector, the app, and a LiteLLM proxy
together on that box OOM-killed the LiteLLM container under real request load (it
needs more like 400–450 MB resident to handle one streamed completion, not the ~100–150
MB its idle footprint suggests). LiteLLM is also the only service in the stack that
exists purely to translate one HTTP shape into another — for a deployment that only
ever talks to Claude, it's a whole extra Python process, dependency tree, and memory
reservation bought for optionality nobody is using yet.

## Decision

Add a third `llm.py` provider, `anthropic`, that calls `api.anthropic.com/v1/messages`
directly over `httpx` — same "no vendor SDK" rule as the `openai` provider, just a
second small HTTP+SSE translation instead of one. Pre-processing pulls the `system`
message out of the list (Anthropic wants it as its own field); post-processing reads
`content_block_delta` / `text_delta` events and stops at `message_stop`. The `openai`
provider and the LiteLLM-fronted path from ADR-0004 are **not removed** — they're the
right answer the moment a second vendor (self-hosted small model, Gemini, Bedrock...)
is actually in play, or on hosts with enough headroom that LiteLLM's footprint isn't a
constraint. `anthropic` is simply the default for *this* deployment, chosen because
Claude is the only provider actually being exercised in production right now.

## Options considered

- **Keep LiteLLM, raise its memory cap, shrink others to compensate** — tried first;
  works but leaves ~4 processes fighting over <1 GB with no real slack, and reproduces
  the same failure mode the moment traffic or KB size grows.
- **Move off `e2-micro` to get more RAM** — contradicts the explicit "stay in the free
  tier" constraint for this POC.
- **Add a direct Anthropic provider, keep LiteLLM as an opt-in profile** (chosen) —
  removes an entire container from the critical path for the deployment that actually
  matters today, without deleting the pluggability ADR-0004 built for everyone else.

## Consequences

One fewer container, ~400+ MB of headroom back on the free-tier VM, one fewer network
hop per bot turn. Gives up: switching Claude↔other-vendor with zero code touch (now
needs picking `LLM_PROVIDER=anthropic` vs `openai`+LiteLLM, both already in `.env.example`).
Narrows ADR-0004's "one wire format for everything" a little — justified here by an
observed, reproducible OOM, not a hypothetical. `docker-compose.yml`'s `litellm` profile
stays in the repo for Gemini/Bedrock/self-hosted-model use; it's just not part of the
deployed stack referenced in `README.md`'s run instructions.
