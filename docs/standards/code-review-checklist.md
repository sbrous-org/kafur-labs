# Code review checklist

## Correctness
- [ ] Handles the stated edge cases (empty input, concurrent access, partial failure)
- [ ] Tests cover the change, including the failure path, not just the happy path
- [ ] No dead code, commented-out blocks, or debug prints left in

## Design
- [ ] Change is scoped to what was asked — no unrelated refactors bundled in
- [ ] Matches existing patterns in the codebase, or explicitly justifies deviating
- [ ] Public interfaces (APIs, function signatures, schemas) are ones we'd be comfortable committing to

## Security (see `security-checklist.md` for anything touching auth, data, or external input)
- [ ] No secrets, credentials, or tokens in code or logs
- [ ] User input is validated/sanitized at the boundary, not trusted downstream

## Operability
- [ ] Failure modes are observable (logged/metriced), not silent
- [ ] Rollback or feature-flag path exists for anything risky

## Before approving
- [ ] Would I be comfortable being paged for this at 3am without the author around to explain it?
