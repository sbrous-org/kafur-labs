# Products

Production code. Held to a real bar because it's expected to carry real users, data, or traffic.

## Starting one

```
cp -r products/_template products/<name>
```

Usually this happens by promoting a POC (`pocs/README.md`), not by starting fresh here.

## Production bar

Before this is trusted with real users/data:

- [ ] Any hard-to-reverse decision behind it has an ADR (`docs/architecture/decisions/`)
- [ ] Passes `docs/standards/code-review-checklist.md` and, if it touches auth/data/external input, `docs/standards/security-checklist.md`
- [ ] External-facing interfaces follow `docs/standards/api-design-guidelines.md`
- [ ] Has tests covering the failure path, not just the happy path
- [ ] Has an owner (a person or team, named in the product's own README) and a monitoring/alerting story
- [ ] Has a rollback path (feature flag, versioned deploy, or equivalent)
- [ ] **AI/ML products additionally:** has eval coverage for the behaviors it's expected to get right, and prompt/data/model versions are pinned and reproducible, not "whatever's latest"

A product that doesn't clear this bar yet is still effectively a POC — leave it in `pocs/` until it does, or track the gap explicitly in its README rather than pretending it's done.
