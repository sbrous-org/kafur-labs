# ADR-0002: NE Trip Planner app stack — FastAPI + WebSocket, Postgres LISTEN/NOTIFY fan-out

Date: 2026-10-12
Status: Accepted

## Context

`pocs/ne-trip-planner` needs real-time multi-user chat (messages, streamed bot replies, shared plan) that must work on 1 or N app instances, with as few moving parts as possible and deployable on any cloud.

## Decision

A single Python/FastAPI service serves REST, WebSocket and the static frontend; Postgres is the only stateful dependency and also carries cross-instance fan-out via `LISTEN/NOTIFY` (durable events carry only ids and are re-read; streamed tokens are sent inline; one ordered worker per instance preserves event order).

## Options considered

- **FastAPI + Postgres NOTIFY** — one datastore, no extra service; NOTIFY payload limit (8 KB) and one listener connection per instance.
- **FastAPI + Redis pub/sub** — scales further, but a second stateful service for a POC.
- **Managed realtime (Firebase/Supabase Realtime/Ably)** — fastest to build, but vendor lock-in and splits state across two systems.

## Consequences

Easy: `docker compose up` runs everything; works on any host with WebSocket support. Harder: presence is a DB counter (reset on boot, stale after a crash); NOTIFY fan-out will need Redis/NATS if sessions per second grow by orders of magnitude. Revisit at promotion.
