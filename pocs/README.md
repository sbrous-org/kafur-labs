# POCs

Disposable by default. A POC's job is to answer a question fast, not to be maintainable — no production stack, test coverage, or review bar is required here.

## Starting one

```
cp -r pocs/_template pocs/<name>
```

Fill in the README's hypothesis and exit criteria before writing code — if you can't state what would make this a "no," it isn't a POC yet, it's just building.

## Exit criteria

Every POC ends in one explicit decision, recorded in its own README:

- **Promote** — hypothesis held up. Move it to `products/<name>/` using `products/_template/`, write any ADRs the decision warrants (`docs/architecture/decisions/`), and bring it up to the production bar in `products/README.md`.
- **Extend** — inconclusive, worth another timeboxed round. State the new question and exit criteria.
- **Kill** — hypothesis failed, or the question stopped mattering. Leave the folder in place with the conclusion recorded (don't delete — the negative result is worth keeping) or archive it.

Don't let a POC quietly accrue real users or production traffic while it's still sitting in this folder — that's the case the promote/kill decision exists to prevent.
