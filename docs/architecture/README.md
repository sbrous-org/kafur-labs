# Architecture

This folder holds decisions and designs that outlive any single POC or product.

- `decisions/` — Architecture Decision Records (ADRs). One file per decision that would be expensive to reverse: stack choice, service boundaries, data model, external dependencies, AI/ML model/vendor selection, auth strategy, etc. Immutable once accepted — superseded by a new ADR, never edited in place.
- System design docs (diagrams, data flow, service maps) for anything spanning more than one `products/` entry go directly in this folder as `<topic>.md`. Keep diagrams as text (Mermaid) so they diff cleanly in git.

## When to write an ADR

Ask: "if someone questions this decision in six months, is there anything to point to besides the code and a Slack thread?" If no, write the ADR before merging.

Skip an ADR for anything easily reversible (a library swap with no data/API impact, an internal refactor, a POC-only choice).

## Review

Significant ADRs (anything affecting more than one product, or introducing a new external dependency/vendor) should be reviewed by whoever else has context — treat it like a PR review, not a unilateral log entry.
