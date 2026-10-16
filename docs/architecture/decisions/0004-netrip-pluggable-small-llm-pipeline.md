# ADR-0004: Pluggable small-LLM port with pipeline orchestration (not tool-calling agent)

Date: 2026-10-12
Status: Accepted

## Context

The requester wants a very small, cheap model and the freedom to plug in any model, not only Claude. Small models are unreliable at native tool calling and strict JSON, and vendor SDK features (tool use, caching) are not portable.

## Decision

The app depends on one function, `llm.stream(settings, messages)`, implemented for any **OpenAI-compatible `/chat/completions`** endpoint (plus an offline `mock`). Vendors without that API (Anthropic, Gemini, Bedrock...) are reached through the stock **LiteLLM proxy container**, not a Python dependency. Each bot turn is a deterministic pipeline — retrieve KB (+ optional weather) without the LLM, build a short prompt, make **one streamed call** whose output is reply text optionally followed by `###PLAN` and a JSON object of plan operations — then validate and apply. Model, base URL and key are environment config.

## Options considered

- **OpenAI-compatible HTTP + LiteLLM proxy as a container** — no vendor SDK in the app; one line of config to switch provider.
- **LiteLLM as a Python library** — convenient, but a heavy dependency in the app image.
- **Native tool-calling agent loop on one vendor SDK** — best with strong models; fails the "small and pluggable" requirement.

## Consequences

Works with Ollama/vLLM/llama.cpp and hosted small models alike. Plan edits depend on the model emitting valid JSON after `###PLAN`; invalid output is dropped (plan unchanged) and the reply is still delivered. The cheapest model that clears the eval bar must be chosen empirically (eval harness still to build).
