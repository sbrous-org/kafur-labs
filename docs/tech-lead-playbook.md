# Technical lead playbook

What a technical lead is responsible for here, and where that responsibility lives in the repo. This is an index into practice, not a textbook — each area links to the artifact that enforces it.

| Competency | What it means here | Where it lives |
|---|---|---|
| Architecture & system design | Decompose the product into services/components, define boundaries and data flow, choose the stack deliberately | `docs/architecture/README.md`, `docs/architecture/decisions/` |
| Decision records | Every hard-to-reverse call is written down with context, options considered, and consequences — so it can be revisited without relitigating from scratch | `docs/architecture/decisions/` (ADRs) |
| POC discipline | Every experiment has a stated hypothesis and exit criteria, and gets an explicit promote/extend/kill decision instead of silently becoming production | `pocs/README.md` |
| Production readiness | A concrete bar (tests, monitoring, rollback, ownership) a POC must clear before it's trusted with real users/data | `products/README.md` |
| Code review standards | What "good" looks like in a review, independent of who's reviewing | `docs/standards/code-review-checklist.md` |
| Security | Threat modeling and hygiene baked into the review/production checklist, not bolted on after an incident | `docs/standards/security-checklist.md` |
| API / interface design | Consistent contracts between services and with external consumers | `docs/standards/api-design-guidelines.md` |
| AI/ML-specific architecture | Model/vendor selection as an ADR-worthy decision; eval coverage and prompt/data versioning treated as first-class before production | `docs/architecture/decisions/`, `products/README.md` |
| Infra & delivery | Environments, deployment, and infra-as-code kept separate from application code | `infra/` |

## How this gets used day to day

- Starting something new → check this table for which checklist applies, not just which folder to put code in.
- Reviewing a PR → `docs/standards/code-review-checklist.md` plus `docs/standards/security-checklist.md` for anything touching auth, data, or external input.
- Making a call that a future engineer will ask "why did we do it this way" about → write the ADR *before* merging the code, not after.
- A POC starts looking permanent → force the promote/kill decision explicitly (`pocs/README.md`) rather than letting it accrete production traffic while still living in `pocs/`.
