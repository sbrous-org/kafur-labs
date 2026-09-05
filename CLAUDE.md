# kafur-labs

Workspace for POCs and production code across web/SaaS and AI/ML products. Polyglot by design — each POC/product picks its own stack; nothing is imposed at the workspace root.

## Conventions

- New experiment → `pocs/<name>/`, copied from `pocs/_template/`. No production bar applies here.
- Promoted/production code → `products/<name>/`, copied from `products/_template/`. Must satisfy `docs/standards/`.
- Any hard-to-reverse technical decision (stack, data model, service boundary, external dependency, AI/ML model or vendor choice) gets an ADR in `docs/architecture/decisions/`, using `docs/architecture/decisions/template.md`. Numbered sequentially, never edited after acceptance — superseded by a new ADR instead.
- Don't scaffold CI, linting, or test frameworks at the workspace root — those live inside each `pocs/<name>/` or `products/<name>/` since stacks differ per project.

## When asked to start a new POC or product

1. Read `pocs/README.md` or `products/README.md` for the checklist first.
2. Copy the relevant `_template/` folder rather than inventing a new structure.
3. Ask what's genuinely ambiguous (target stack, scale expectations) rather than guessing silently for anything that's expensive to reverse later.

## When asked about architecture or design tradeoffs

Check `docs/architecture/decisions/` for prior ADRs before proposing something that may already have been decided (or explicitly superseded). Write a new ADR for any decision made during the conversation that fits the criteria above.
