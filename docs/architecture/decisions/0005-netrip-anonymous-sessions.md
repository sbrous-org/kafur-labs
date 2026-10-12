# ADR-0005: Anonymous shared sessions — join code + participant token, no accounts

Date: 2026-10-12
Status: Accepted

## Context

Opening the link must create a session instantly; friends join with a code. The POC must not collect personal data or require sign-up.

## Decision

`POST /api/sessions` creates a session with a 6-character code (unambiguous alphabet, ~10^9 space); joining with a display name returns a random 192-bit participant token stored only as a SHA-256 hash server-side and kept in the browser's localStorage. Sessions are capped at 8 participants, rate-limited per IP, expire after 14 idle days (empty ones after 1 hour), and any member can delete the session.

## Options considered

- **Code + token, no login** — zero friction; the code is the only secret.
- **Link-only (code in URL)** — same security, no code to type; we support both (`/s/CODE`).
- **Sign-in (Google)** — persistent trips across devices, but accounts, privacy and build effort.

## Consequences

Anyone with the code can join until the session is full; there is no recovery if a participant clears browser storage (they rejoin as a new name). Unsuitable for sensitive content. Revisit with optional sign-in at promotion.
