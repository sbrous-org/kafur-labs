import asyncio
import hashlib
import json
import logging
import re
import secrets
import time
from collections import defaultdict, deque
from contextlib import asynccontextmanager

from fastapi import FastAPI, Header, HTTPException, Query, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import bot, kb, plan as planlib, services
from .config import get_settings
from .db import make_pool
from .hub import Hub, message_json, participants

log = logging.getLogger("netrip")
ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"  # no 0/O/1/I/L


def new_code() -> str:
    return "".join(secrets.choice(ALPHABET) for _ in range(6))


def norm_code(code: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", code.upper())


def hash_token(t: str) -> str:
    return hashlib.sha256(t.encode()).hexdigest()


class RateLimiter:
    def __init__(self):
        self.hits: dict[str, deque] = defaultdict(deque)

    def ok(self, key: str, limit: int, window: float) -> bool:
        now, q = time.monotonic(), self.hits[key]
        while q and now - q[0] > window:
            q.popleft()
        if len(q) >= limit:
            return False
        q.append(now)
        return True


async def purge_loop(app: FastAPI):
    while True:
        try:
            s = app.state.settings
            await app.state.pool.execute("delete from sessions where last_active_at < now() - make_interval(days => $1)", s.session_ttl_days)
            await app.state.pool.execute(
                "delete from sessions s where created_at < now() - interval '1 hour' and not exists (select 1 from participants p where p.session_id = s.id)")
        except Exception:
            log.exception("purge failed")
        await asyncio.sleep(3600)


@asynccontextmanager
async def lifespan(app: FastAPI):
    s = get_settings()
    app.state.settings = s
    app.state.pool = await make_pool(s)
    app.state.hub = Hub(app.state.pool, s.database_url)
    app.state.running, app.state.tasks, app.state.rl = set(), set(), RateLimiter()
    await app.state.pool.execute("update participants set conns = 0")  # POC: presence resets on boot
    n = await kb.ingest(app.state.pool, s)
    log.info("kb ready: %d docs; llm=%s/%s embeddings=%s", n, s.llm_provider, s.llm_model, s.embed_provider)
    await app.state.hub.start()
    purge = asyncio.create_task(purge_loop(app))
    yield
    purge.cancel()
    await app.state.hub.stop()
    await app.state.pool.close()


app = FastAPI(title="Mynna", lifespan=lifespan)


def client_ip(request: Request) -> str:
    return (request.headers.get("x-forwarded-for", "").split(",")[0].strip()) or (request.client.host if request.client else "?")


async def get_session(code: str):
    row = await app.state.pool.fetchrow("select * from sessions where code = $1", norm_code(code))
    if not row:
        raise HTTPException(404, "No such session")
    return row


async def auth(code: str, token: str):
    row = await app.state.pool.fetchrow(
        "select p.id as pid, p.name, s.id as sid, s.code from participants p join sessions s on s.id = p.session_id "
        "where p.token_hash = $1 and s.code = $2", hash_token(token or ""), norm_code(code))
    return row


@app.get("/healthz")
async def healthz():
    await app.state.pool.fetchval("select 1")
    return {"ok": True}


@app.post("/api/sessions")
async def create_session(request: Request):
    s = app.state.settings
    if not app.state.rl.ok("create:" + client_ip(request), s.creates_per_hour, 3600):
        raise HTTPException(429, "Too many sessions created from this address; try later.")
    for _ in range(8):
        code = new_code()
        try:
            await app.state.pool.execute("insert into sessions(code) values($1)", code)
            return {"code": code}
        except Exception:
            continue
    raise HTTPException(500, "Could not allocate a code")


class JoinIn(BaseModel):
    name: str = Field(min_length=1, max_length=24)


@app.get("/api/sessions/{code}")
async def session_info(code: str):
    row = await get_session(code)
    n = await app.state.pool.fetchval("select count(*) from participants where session_id = $1", row["id"])
    return {"code": row["code"], "participants": n, "full": n >= app.state.settings.max_participants}


@app.post("/api/sessions/{code}/join")
async def join(code: str, body: JoinIn, request: Request):
    s = app.state.settings
    ip = client_ip(request)
    if not app.state.rl.ok("join:" + ip, s.joins_per_minute, 60):
        raise HTTPException(429, "Too many attempts; slow down.")
    row = await get_session(code)  # unknown codes also count against the limiter above
    name = " ".join(body.name.split())
    if not name:
        raise HTTPException(422, "Name required")
    pool = app.state.pool
    async with pool.acquire() as c, c.transaction():
        await c.execute("select 1 from sessions where id = $1 for update", row["id"])
        n = await c.fetchval("select count(*) from participants where session_id = $1", row["id"])
        if n >= s.max_participants:
            raise HTTPException(409, "This session is full")
        taken = {r["name"].lower() for r in await c.fetch("select name from participants where session_id = $1", row["id"])}
        final, i = name, 2
        while final.lower() in taken:
            final, i = f"{name} {i}", i + 1
        token = secrets.token_urlsafe(24)
        pid = await c.fetchval("insert into participants(session_id, name, token_hash) values($1,$2,$3) returning id",
                               row["id"], final, hash_token(token))
    await app.state.hub.publish(row["id"], "participants")
    await services.post_message(app, row["id"], None, "system", f"{final} joined")
    return {"token": token, "participant": {"id": str(pid), "name": final}, "code": row["code"]}


@app.delete("/api/sessions/{code}")
async def delete_session(code: str, x_token: str = Header("")):
    a = await auth(code, x_token)
    if not a:
        raise HTTPException(403, "Not a member")
    await app.state.hub.publish(a["sid"], "eph", data={"type": "closed"})
    await asyncio.sleep(0.2)
    await app.state.pool.execute("delete from sessions where id = $1", a["sid"])
    return {"ok": True}


@app.get("/api/sessions/{code}/plan.txt", response_class=PlainTextResponse)
async def plan_text(code: str, token: str = Query("")):
    a = await auth(code, token)
    if not a:
        raise HTTPException(403, "Not a member")
    row = await app.state.pool.fetchrow("select plan from sessions where id = $1", a["sid"])
    return planlib.to_text(json.loads(row["plan"]))


async def snapshot(a) -> dict:
    pool = app.state.pool
    s = await pool.fetchrow("select plan, plan_version from sessions where id = $1", a["sid"])
    rows = await pool.fetch(
        "select * from (select m.*, p.name from messages m left join participants p on p.id = m.participant_id "
        "where m.session_id = $1 order by m.id desc limit 200) x order by id", a["sid"])
    return {"type": "snapshot", "code": a["code"], "you": {"id": str(a["pid"]), "name": a["name"]},
            "participants": await participants(pool, a["sid"]),
            "messages": [message_json(r, r["name"]) for r in rows],
            "plan": json.loads(s["plan"]), "version": s["plan_version"]}


@app.websocket("/ws/{code}")
async def ws_endpoint(websocket: WebSocket, code: str, token: str = Query("")):
    a = await auth(code, token)
    if not a:
        await websocket.close(code=4401)
        return
    await websocket.accept()
    st, hub, pool = app.state.settings, app.state.hub, app.state.pool
    sid = str(a["sid"])
    conn = hub.register(sid, websocket)
    await pool.execute("update participants set conns = conns + 1 where id = $1", a["pid"])
    await hub.publish(sid, "presence")
    try:
        snap = await snapshot(a)
        await websocket.send_json(snap)
        await conn.mark_ready({m["id"] for m in snap["messages"]})
        while True:
            data = await websocket.receive_json()
            kind = data.get("type")
            if kind == "ping":
                await websocket.send_json({"type": "pong"})
            elif kind == "message":
                text = str(data.get("text", "")).strip()[:1000]
                if not text:
                    continue
                if not app.state.rl.ok("msg:" + str(a["pid"]), st.msgs_per_minute, 60):
                    await websocket.send_json({"type": "error", "message": "Slow down a little - too many messages."})
                    continue
                skip = text.startswith("//")
                if skip:
                    text = text[2:].strip()
                    if not text:
                        continue
                await services.post_message(app, a["sid"], a["pid"], "user", text, {"skip_bot": True} if skip else {})
                if not skip:
                    bot.kick(app, a["sid"])
            elif kind == "plan_edit":
                ops = [o for o in data.get("ops", []) if isinstance(o, dict) and o.get("op") in ("remove", "move")]
                applied, errors, summary = await services.update_plan(app, a["sid"], ops, a["name"], human=True)
                if summary:
                    await services.post_message(app, a["sid"], None, "system", summary)
                elif errors:
                    await websocket.send_json({"type": "error", "message": "That plan change is no longer valid."})
    except WebSocketDisconnect:
        pass
    except Exception:
        log.exception("ws error")
    finally:
        hub.unregister(sid, conn)
        await pool.execute("update participants set conns = greatest(conns - 1, 0) where id = $1", a["pid"])
        try:
            await hub.publish(sid, "presence")
        except Exception:
            pass


# ---- static frontend
@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return PlainTextResponse("", status_code=204)



@app.get("/")
@app.get("/s/{code}")
async def index(code: str = ""):
    return FileResponse(get_settings().frontend_dir / "index.html", headers={"Cache-Control": "no-cache"})


def _mount():
    s = get_settings()
    if s.frontend_dir.exists():
        app.mount("/static", StaticFiles(directory=s.frontend_dir), name="static")


_mount()
