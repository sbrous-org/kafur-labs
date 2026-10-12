"""Writes that must also be broadcast: messages and plan changes."""
import json

from . import plan as planlib


async def post_message(app, sid, pid, role: str, content: str, meta: dict | None = None) -> int:
    mid = await app.state.pool.fetchval(
        "insert into messages(session_id, participant_id, role, content, meta) values($1,$2,$3,$4,$5::jsonb) returning id",
        sid, pid, role, content, json.dumps(meta or {}))
    await app.state.pool.execute("update sessions set last_active_at = now() where id = $1", sid)
    await app.state.hub.publish(sid, "message", id=mid)
    return mid


async def update_plan(app, sid, ops: list, author: str, human: bool, valid_kb: set[str] | None = None):
    """Apply ops under a row lock (bot and humans may edit concurrently). Returns (applied, errors, summary)."""
    pool = app.state.pool
    async with pool.acquire() as c, c.transaction():
        row = await c.fetchrow("select plan from sessions where id = $1 for update", sid)
        old = json.loads(row["plan"])
        new, applied, errors = planlib.apply_ops(old, ops, author, human, valid_kb)
        if applied:
            await c.execute("update sessions set plan = $2::jsonb, plan_version = plan_version + 1 where id = $1", sid, json.dumps(new))
    summary = ""
    if applied:
        flat = lambda p: {it["id"]: (d["n"], it["title"]) for d in p["days"] for it in d["items"]}
        o, n = flat(old), flat(new)
        parts = [f"removed '{o[i][1]}'" for i in o if i not in n]
        parts += [f"moved '{n[i][1]}' to day {n[i][0]}" for i in n if i in o and o[i][0] != n[i][0]]
        summary = f"{author} " + ", ".join(parts) if human and parts else ""
        await app.state.hub.publish(sid, "plan")
    return applied, errors, summary
