"""Bot orchestrator: a pipeline, not an agent loop (works with very small models).
  1. take the per-session turn lock  2. retrieve KB (+weather) deterministically
  3. build a short prompt            4. ONE streamed LLM call: reply text, then optional '###PLAN' + JSON ops
  5. validate + apply plan ops       6. broadcast"""
import asyncio
import json
import logging
import re
import time
from pathlib import Path

import yaml

from . import kb, llm, plan as planlib, services, weather

log = logging.getLogger("netrip.bot")
WEATHER_WORDS = re.compile(r"weather|rain|raining|temperature|forecast|humid|snow|hot\b|cold\b", re.I)

# Persona, reply rules and the ###PLAN delimiter live in prompts.yaml, not here —
# edit that file (and restart the container) to tune tone/format, no code change.
_PROMPTS = yaml.safe_load(Path(__file__).with_name("prompts.yaml").read_text(encoding="utf-8"))
BOT_NAME = _PROMPTS.get("bot_name", "Mynna")
DELIM = _PROMPTS.get("delim", "###PLAN")
SYSTEM = _PROMPTS["system_prompt"].format(
    bot_name=BOT_NAME, max_reply_words=_PROMPTS.get("max_reply_words", 120), delim=DELIM)


def parse_output(text: str) -> tuple[str, list]:
    reply, _, rest = text.partition(DELIM)
    ops: list = []
    m = re.search(r"\{.*\}|\[.*\]", rest, re.S)
    if m:
        try:
            obj = json.loads(m.group(0))
            ops = obj.get("ops", []) if isinstance(obj, dict) else obj
        except json.JSONDecodeError:
            ops = []
    return reply.strip(), ops if isinstance(ops, list) else []


def kick(app, sid) -> None:
    t = asyncio.get_running_loop().create_task(run_turns(app, sid))
    app.state.tasks.add(t)
    t.add_done_callback(app.state.tasks.discard)


async def run_turns(app, sid) -> None:
    pool = app.state.pool
    if sid in app.state.running:
        return  # the active loop will pick up new messages when its turn ends
    app.state.running.add(sid)
    conn = await pool.acquire()
    try:
        # cross-instance turn lock: only one instance runs a bot turn for this session
        if not await conn.fetchval("select pg_try_advisory_lock(('x' || substr(md5($1::text), 1, 16))::bit(64)::bigint)", str(sid)):
            return
        while True:
            s = await pool.fetchrow("select bot_seq from sessions where id = $1", sid)
            if s is None:
                return
            msgs = await pool.fetch(
                "select m.id, m.content, p.name from messages m left join participants p on p.id = m.participant_id "
                "where m.session_id = $1 and m.role = 'user' and m.id > $2 and coalesce(m.meta->>'skip_bot','') = '' order by m.id",
                sid, s["bot_seq"])
            if not msgs:
                return
            await pool.execute("update sessions set bot_seq = $2 where id = $1", sid, msgs[-1]["id"])
            try:
                await _turn(app, sid, msgs)
            except Exception as e:
                log.exception("bot turn failed")
                msg = "Sorry - I could not reach the language model. Check LLM settings and try again." if isinstance(e, llm.LLMError) else "Sorry - something went wrong on my side."
                await services.post_message(app, sid, None, "system", msg)
                await app.state.hub.publish(sid, "eph", data={"type": "bot_done", "message": None})
    finally:
        try:
            await conn.execute("select pg_advisory_unlock_all()")
        finally:
            await pool.release(conn)
            app.state.running.discard(sid)


async def _turn(app, sid, new_msgs) -> None:
    pool, hub, st = app.state.pool, app.state.hub, app.state.settings
    sess = await pool.fetchrow("select plan, tokens_used from sessions where id = $1", sid)
    plan = json.loads(sess["plan"])
    recent = list(reversed(await pool.fetch(
        "select m.role, m.content, p.name from messages m left join participants p on p.id = m.participant_id "
        "where m.session_id = $1 and m.role in ('user','bot') and coalesce(m.meta->>'skip_bot','') = '' order by m.id desc limit 12", sid)))
    people = [r["name"] for r in await pool.fetch("select name from participants where session_id = $1 order by joined_at", sid)]

    # ---- retrieve (no LLM involved)
    new_text = " ".join(m["content"] for m in new_msgs)
    ctx_user = " ".join(r["content"] for r in recent if r["role"] == "user")
    plan_titles = " ".join(it["title"] for d in plan["days"] for it in d["items"])
    states = kb.detect_states(ctx_user + " " + plan_titles)
    query = new_text if len(new_text.split()) >= 6 else (ctx_user[-300:] + " " + new_text)
    chunks = await kb.search(pool, st, query, states, k=4)
    weather_txt = None
    if st.weather and WEATHER_WORDS.search(new_text):
        for c in chunks:
            if c["lat"] is not None and c["kind"] in ("place", "gem"):
                weather_txt = await weather.forecast(c["lat"], c["lon"], c["title"])
                break

    knowledge = "\n".join(f"[{c['id']}] {c['title']} | {c['state'] or ''} | {c['kind']} | {c['text']}" for c in chunks) or "(nothing found)"
    chat = "\n".join(f"[{r['name'] or BOT_NAME}]: {r['content']}" for r in recent)
    prompt = (f"KNOWLEDGE:\n{knowledge}\n" + (f"\nWEATHER:\n{weather_txt}\n" if weather_txt else "")
              + f"\nCURRENT PLAN:\n{planlib.compact(plan)}\n\nTRAVELLERS: {', '.join(people)}\n\nCHAT:\n{chat}\n\nReply now.")
    est = (len(SYSTEM) + len(prompt)) // 4
    if sess["tokens_used"] + est > st.max_session_tokens:
        await services.post_message(app, sid, None, "system", "This session has reached its AI usage limit. Start a new session to keep planning.")
        return

    # ---- one streamed LLM call; stream only the reply part to clients
    await hub.publish(sid, "eph", data={"type": "bot_start"})
    full, sent, buf_t = "", 0, time.monotonic()
    stop = False

    async def flush(final: bool):
        nonlocal sent
        text = full.partition(DELIM)[0]
        limit = len(text) if (final or DELIM in full) else max(len(text) - (len(DELIM) - 1), 0)
        if limit > sent:
            await hub.publish(sid, "eph", data={"type": "bot_token", "text": text[sent:limit]})
            sent = limit

    async for delta in llm.stream(st, [{"role": "system", "content": SYSTEM}, {"role": "user", "content": prompt}]):
        full += delta
        if time.monotonic() - buf_t > 0.08:
            await flush(False)
            buf_t = time.monotonic()
    await flush(True)

    reply, ops = parse_output(full)
    valid = {c["id"] for c in chunks} | {it["kb_id"] for d in plan["days"] for it in d["items"] if it.get("kb_id")}
    by_id = {c["id"]: c for c in chunks}
    cited = [i for i in dict.fromkeys(re.findall(r"\[([a-z0-9_\-]+)\]", reply)) if i in by_id] or [c["id"] for c in chunks[:2]]
    meta = {"cites": [{"id": i, "title": by_id[i]["title"], "high_risk": by_id[i]["high_risk"],
                        "verified": by_id[i]["last_verified"]} for i in cited]}
    if not reply:
        reply = "I don't have that in my notes."
    mid = await services.post_message(app, sid, None, "bot", reply, meta)
    await pool.execute("update sessions set tokens_used = tokens_used + $2 where id = $1", sid, est + len(full) // 4)
    if ops:
        await services.update_plan(app, sid, ops, BOT_NAME, human=False, valid_kb=valid)
    await hub.publish(sid, "eph", data={"type": "bot_done", "id": mid})
