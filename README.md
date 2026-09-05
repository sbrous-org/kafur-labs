# kafur-labs

A workspace for building proofs-of-concept and taking the ones that prove out to production — spanning web/SaaS products and AI/ML/LLM-based products.

The structure below exists to enforce the habits a technical lead is responsible for: documented architecture decisions, a real POC → production gate, and written standards instead of tribal knowledge. See [`docs/tech-lead-playbook.md`](docs/tech-lead-playbook.md) for how each competency area maps to a folder here.

## Layout

```
docs/
  architecture/
    decisions/     ADRs — one file per significant technical decision
    README.md      how architecture is documented and reviewed here
  standards/        code review, security, API design checklists
  tech-lead-playbook.md

pocs/
  _template/        copy this to start a new POC
  <name>/           one folder per experiment, disposable by default

products/
  _template/        copy this when a POC graduates
  <name>/           production code — held to the production bar

infra/              infra-as-code, environments, deployment config
```

## POC → production

1. Start in `pocs/<name>/` using `pocs/_template/`. Pick any stack — POCs are not held to production standards.
2. When a POC proves its hypothesis, decide explicitly: promote, extend, or kill. Don't let it drift into production unreviewed.
3. Promoting means moving it into `products/<name>/` using `products/_template/`, and writing an ADR in `docs/architecture/decisions/` for any decision that would be expensive to reverse (stack choice, data model, service boundaries, external dependencies).
4. Production code is held to `docs/standards/` — tests, review, security, and (for AI/ML products) eval coverage before it ships.

## Adding a new product or POC

- POC: `cp -r pocs/_template pocs/<name>`, fill in the README's hypothesis and exit criteria.
- Product: `cp -r products/_template products/<name>`, fill in the README's ownership and production checklist.
- Any decision worth remembering in six months: add an ADR (`docs/architecture/decisions/template.md`).
