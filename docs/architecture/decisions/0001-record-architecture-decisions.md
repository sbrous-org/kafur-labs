# ADR-0001: Record architecture decisions as ADRs

Date: 2026-09-05
Status: Accepted

## Context

Decisions about stack, service boundaries, data models, and external dependencies get made in conversation, code review comments, or a chat thread, then lost. Six months later nobody can say why a choice was made or whether the constraints that drove it still hold.

## Decision

Every hard-to-reverse technical decision is recorded as a numbered, immutable Markdown file in `docs/architecture/decisions/`, using `template.md`. A decision that's later reversed is superseded by a new ADR that links back to the old one — the old one is never edited or deleted.

## Options considered

- **Nothing written down (status quo)** — zero overhead, but no way to recover the reasoning behind a decision later; every revisit relitigates from scratch.
- **Wiki / external doc tool** — decouples decisions from the code, drifts out of date, doesn't diff or review like code.
- **ADRs in-repo (chosen)** — versioned with the code, reviewable as a PR, cheap to write, survives as long as the repo does.

## Consequences

Adds a small amount of discipline: anyone making a decision that fits the criteria in `docs/architecture/README.md` writes the ADR before merging the related code, not after. In exchange, the repo accumulates a searchable, dated record of *why* it looks the way it does — the main thing a technical lead is expected to be able to answer.
