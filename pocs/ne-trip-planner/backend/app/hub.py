"""Real-time fan-out. Every instance LISTENs on one Postgres channel; a publish is a NOTIFY, so it
reaches sockets on ANY instance (no Redis). Durable events carry only ids and are re-read from the DB."""
import asyncio
import json
import logging
from collections import defaultdict

import asyncpg
from fastapi import WebSocket

log = logging.getLogger("netrip.hub")
CHANNEL = "netrip"


def message_json(r: asyncpg.Record, name: str | None) -> dict:
    return {"type": "message", "id": r["id"], "role": r["role"], "pid": str(r["participant_id"]) if r["participant_id"] else None,
            "name": name, "content": r["content"], "meta": json.loads(r["meta"]) if isinstance(r["meta"], str) else r["meta"],
            "ts": r["created_at"].isoformat()}


class Conn:
    """A socket plus a buffer: events that arrive before the snapshot is sent are held, then flushed."""
    def __init__(self, ws: WebSocket):
        self.ws, self.ready, self.pending = ws, False, []

    async def mark_ready(self, snapshot_msg_ids: set[int]):
        while self.pending:
            ev = self.pending.pop(0)
            if ev.get("type") == "message" and ev.get("id") in snapshot_msg_ids:
                continue
            await self.ws.send_json(ev)
        self.ready = True  # no await between the empty check and this line


class Hub:
    def __init__(self, pool: asyncpg.Pool, dsn: str):
        self.pool, self.dsn = pool, dsn
        self.socks: dict[str, set[Conn]] = defaultdict(set)
        self.listener: asyncpg.Connection | None = None
        self._queue: asyncio.Queue = asyncio.Queue()
        self._worker: asyncio.Task | None = None

    async def start(self):
        self.listener = await asyncpg.connect(self.dsn)
        await self.listener.add_listener(CHANNEL, self._on_notify)
        self._worker = asyncio.create_task(self._run())

    async def stop(self):
        if self._worker:
            self._worker.cancel()
        if self.listener:
            await self.listener.close()

    def register(self, sid: str, ws: WebSocket) -> Conn:
        conn = Conn(ws)
        self.socks[sid].add(conn)
        return conn

    def unregister(self, sid: str, conn: Conn):
        self.socks[sid].discard(conn)
        if not self.socks[sid]:
            self.socks.pop(sid, None)

    async def publish(self, sid, kind: str, **data):
        await self.pool.execute("select pg_notify($1, $2)", CHANNEL, json.dumps({"sid": str(sid), "kind": kind, **data}))

    def _on_notify(self, conn, pid, channel, payload):
        self._queue.put_nowait(json.loads(payload))

    async def _run(self):
        # one worker => events reach clients in NOTIFY order (a message row is re-read from the DB,
        # so concurrent dispatch could let a later inline event overtake it)
        while True:
            ev = await self._queue.get()
            try:
                await self._dispatch(ev)
            except Exception:
                log.exception("dispatch failed")

    async def _dispatch(self, ev: dict):
        sid, kind = ev["sid"], ev["kind"]
        targets = list(self.socks.get(sid, ()))
        if not targets:
            return
        try:
            out = await self._build(sid, kind, ev)
        except Exception:
            log.exception("dispatch build failed")
            return
        if out is None:
            return
        dead = []
        for conn in targets:
            try:
                if not conn.ready:
                    conn.pending.append(out)
                    continue
                await conn.ws.send_json(out)
                if out.get("type") == "closed":
                    await conn.ws.close(code=4410)
            except Exception:
                dead.append(conn)
        for conn in dead:
            self.unregister(sid, conn)

    async def _build(self, sid: str, kind: str, ev: dict) -> dict | None:
        if kind == "message":
            r = await self.pool.fetchrow(
                "select m.*, p.name from messages m left join participants p on p.id = m.participant_id where m.id = $1", ev["id"])
            return message_json(r, r["name"] if r else None) if r else None
        if kind == "plan":
            r = await self.pool.fetchrow("select plan, plan_version from sessions where id = $1::uuid", sid)
            return {"type": "plan", "plan": json.loads(r["plan"]), "version": r["plan_version"]} if r else None
        if kind in ("presence", "participants"):
            return {"type": "participants", "participants": await participants(self.pool, sid)}
        if kind == "eph":
            return ev["data"]
        return None


async def participants(pool: asyncpg.Pool, sid) -> list[dict]:
    rows = await pool.fetch("select id, name, conns from participants where session_id = $1::uuid order by joined_at", str(sid))
    return [{"id": str(r["id"]), "name": r["name"], "online": r["conns"] > 0} for r in rows]
