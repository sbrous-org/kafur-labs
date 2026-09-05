# API / interface design guidelines

Applies to any boundary between services, or between a product and external consumers — REST/HTTP APIs, internal service calls, and library/module public interfaces alike.

## Contracts
- Version from day one (`/v1/...` or an explicit schema version) — breaking changes bump the version, they don't mutate it in place.
- Additive changes only within a version: new optional fields, no removed/renamed fields, no changed semantics.
- Document the contract where it's defined (OpenAPI/JSON Schema/type definitions), not only in a separate doc that can drift.

## Errors
- Errors are structured and machine-parseable (a stable error code, not just a message string) — callers should be able to branch on them without string-matching.
- Fail loudly on the caller's mistake (4xx-equivalent), fail informatively on ours (5xx-equivalent with enough detail to debug, without leaking internals).

## Consistency
- Naming, pagination, filtering, and auth conventions match across endpoints/services in the same product — pick one pattern and reuse it, don't let each endpoint invent its own.
- Idempotency for anything that can be safely retried (use idempotency keys for actions with side effects).

## AI/ML interfaces specifically
- Treat prompt templates and tool schemas as part of the versioned contract — changing them can break downstream evals/consumers the same way a field rename would.
- Streaming vs. non-streaming, and token/latency budgets, are part of the interface spec, not an implementation detail decided later.
