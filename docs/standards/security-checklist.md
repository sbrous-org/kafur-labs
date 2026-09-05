# Security checklist

Applies to anything in `products/` touching auth, user data, payments, or external/untrusted input. Optional but encouraged for POCs that handle real data.

## Input & data
- [ ] All external input (user, API, file upload, LLM tool output) validated/sanitized at the boundary
- [ ] No string-concatenated queries (SQL, shell, LDAP) — parameterized/escaped throughout
- [ ] PII and secrets never logged; secrets never committed (env vars / secret manager only)

## Auth & access
- [ ] Every endpoint/action has an explicit authorization check — no "authenticated implies authorized"
- [ ] Least privilege: service accounts and API keys scoped to only what they need

## Dependencies & supply chain
- [ ] New dependencies checked for maintenance status and known CVEs before adding
- [ ] Lockfiles committed; no unpinned versions in production code

## AI/ML-specific
- [ ] Untrusted content passed to an LLM (user input, retrieved docs, tool output) is treated as data, not instructions — prompt-injection surface identified
- [ ] Model/vendor API keys scoped and rotated like any other credential
- [ ] Outputs that trigger side effects (sending messages, executing code, spending money) go through the same authorization checks as a human-triggered action would

## Before shipping
- [ ] Would this survive a targeted attempt to abuse it, not just a well-behaved user?
