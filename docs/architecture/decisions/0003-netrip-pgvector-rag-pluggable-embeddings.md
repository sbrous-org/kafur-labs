# ADR-0003: RAG on Postgres + pgvector with pluggable embeddings (hash default)

Date: 2026-10-12
Status: Accepted

## Context

The bot must answer only from a curated Northeast India knowledge base (a few hundred chunk-sized entries). Embeddings must not tie us to one vendor, and the demo must run with no model download or API key.

## Decision

Store the KB in Postgres (`pgvector/pgvector` image) and retrieve with hybrid search: weighted full-text (title > region > body) plus vector similarity (with a distance cutoff so unknown topics return nothing), fused by reciprocal-rank fusion, with state filters, pinned permit/season guides and a place-name boost. Embeddings come from a port: `hash` (offline hashed bag-of-words, default), `openai` (any OpenAI-compatible `/embeddings`, e.g. Ollama `nomic-embed-text`), or `none`.

## Options considered

- **pgvector in the existing DB** — nothing new to run; fine at this scale.
- **Managed vector DB / managed RAG (OpenSearch, Vertex, Bedrock KB)** — lock-in and cost for a tiny corpus.
- **In-process embedding model (fastembed/sentence-transformers)** — heavier image, model download; deferred behind the same port.

## Consequences

The default `hash` embedder is lexical-quality only; real semantic quality needs `EMBED_PROVIDER=openai`. `EMBED_DIM` is fixed in the schema — changing it needs a volume reset. KB content is draft (`last_verified` empty) and is flagged as unverified in the UI until a human reviews it.
