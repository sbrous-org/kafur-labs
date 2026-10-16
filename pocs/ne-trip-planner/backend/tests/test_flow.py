import asyncio
import json

import httpx
import pytest
import websockets


def api(server):
    return httpx.Client(base_url=f"http://{server}", timeout=10)


def new_member(c, code, name):
    r = c.post(f"/api/sessions/{code}/join", json={"name": name})
    assert r.status_code == 200, r.text
    return r.json()["token"]


async def recv_until(ws, pred, timeout=10):
    async def go():
        while True:
            m = json.loads(await ws.recv())
            if pred(m):
                return m
    return await asyncio.wait_for(go(), timeout)


def test_create_join_codes(server):
    with api(server) as c:
        code = c.post("/api/sessions").json()["code"]
        assert len(code) == 6 and not set(code) & set("01OIL")
        assert c.get(f"/api/sessions/{code.lower()}").json()["participants"] == 0  # case-insensitive
        assert c.get("/api/sessions/ZZZZZZ").status_code == 404
        t1 = new_member(c, code, "Asha")
        assert t1
        r = c.post(f"/api/sessions/{code}/join", json={"name": "asha"})
        assert r.json()["participant"]["name"] == "asha 2"  # duplicate names get a suffix


def test_participant_cap(server, monkeypatch):
    with api(server) as c:
        code = c.post("/api/sessions").json()["code"]
        for i in range(8):
            new_member(c, code, f"P{i}")
        assert c.post(f"/api/sessions/{code}/join", json={"name": "late"}).status_code == 409


def test_ws_rejects_bad_token(server):
    async def go():
        with api(server) as c:
            code = c.post("/api/sessions").json()["code"]
        with pytest.raises(Exception):
            async with websockets.connect(f"ws://{server}/ws/{code}?token=nope") as ws:
                await ws.recv()
    asyncio.run(go())


def test_group_chat_bot_and_plan(server):
    """Two people in one session: A's message reaches B in real time, the bot answers both
    (streamed), cites KB entries, and builds a shared plan that both see."""
    async def go():
        with api(server) as c:
            code = c.post("/api/sessions").json()["code"]
            ta, tb = new_member(c, code, "Asha"), new_member(c, code, "Ravi")
        async with websockets.connect(f"ws://{server}/ws/{code}?token={ta}") as a, \
                   websockets.connect(f"ws://{server}/ws/{code}?token={tb}") as b:
            sa = json.loads(await a.recv())
            assert sa["type"] == "snapshot" and sa["you"]["name"] == "Asha"
            await recv_until(b, lambda m: m["type"] == "snapshot")
            await a.send(json.dumps({"type": "message", "text": "Plan a trip with Kaziranga wildlife and Meghalaya caves please"}))
            m = await recv_until(b, lambda m: m["type"] == "message" and m["role"] == "user")
            assert m["name"] == "Asha"
            await recv_until(b, lambda m: m["type"] == "bot_start")
            tokens = ""
            while True:
                x = json.loads(await asyncio.wait_for(b.recv(), 10))
                if x["type"] == "bot_token":
                    tokens += x["text"]
                if x["type"] == "message" and x["role"] == "bot":
                    bot_msg = x
                if x["type"] == "bot_done":
                    break
            assert "###PLAN" not in tokens and tokens.strip()
            assert bot_msg["meta"]["cites"], "bot reply should carry KB sources"
            plan = (await recv_until(a, lambda m: m["type"] == "plan"))["plan"]
            assert plan["days"] and plan["days"][0]["items"][0]["added_by"] == "Mynna"
            # human edit: remove an item -> both see updated plan + a system note
            item = plan["days"][0]["items"][0]
            await b.send(json.dumps({"type": "plan_edit", "ops": [{"op": "remove", "id": item["id"]}]}))
            p2 = await recv_until(a, lambda m: m["type"] == "plan" and item["id"] not in json.dumps(m["plan"]))
            assert p2["version"] > 1
            note = await recv_until(a, lambda m: m["type"] == "message" and m["role"] == "system" and "removed" in m["content"])
            assert "Ravi" in note["content"]
    asyncio.run(go())


def test_double_slash_skips_bot_and_reconnect_snapshot(server):
    async def go():
        with api(server) as c:
            code = c.post("/api/sessions").json()["code"]
            ta = new_member(c, code, "Asha")
        async with websockets.connect(f"ws://{server}/ws/{code}?token={ta}") as a:
            await a.recv()
            await a.send(json.dumps({"type": "message", "text": "// shall we ask Ravi first?"}))
            m = await recv_until(a, lambda m: m["type"] == "message" and m["role"] == "user")
            assert m["content"] == "shall we ask Ravi first?" and m["meta"].get("skip_bot")
            with pytest.raises(asyncio.TimeoutError):
                await recv_until(a, lambda m: m["type"] == "bot_start", timeout=1.5)
        async with websockets.connect(f"ws://{server}/ws/{code}?token={ta}") as a2:  # reconnect
            snap = json.loads(await a2.recv())
            assert any(x["content"] == "shall we ask Ravi first?" for x in snap["messages"])
    asyncio.run(go())


def test_permit_question_is_grounded(server):
    async def go():
        with api(server) as c:
            code = c.post("/api/sessions").json()["code"]
            ta = new_member(c, code, "Asha")
        async with websockets.connect(f"ws://{server}/ws/{code}?token={ta}") as a:
            await a.recv()
            await a.send(json.dumps({"type": "message", "text": "Do we need a permit for Tawang in Arunachal?"}))
            m = await recv_until(a, lambda m: m["type"] == "message" and m["role"] == "bot")
            ids = {x["id"] for x in m["meta"]["cites"]}
            assert ids & {"permits-arunachal", "tawang"}, ids
            assert "verify" in m["content"].lower()
    asyncio.run(go())


def test_unknown_topic_says_so(server):
    async def go():
        with api(server) as c:
            code = c.post("/api/sessions").json()["code"]
            ta = new_member(c, code, "Asha")
        async with websockets.connect(f"ws://{server}/ws/{code}?token={ta}") as a:
            await a.recv()
            await a.send(json.dumps({"type": "message", "text": "xyzzy plugh qwertyuiop zzzz"}))
            m = await recv_until(a, lambda m: m["type"] == "message" and m["role"] == "bot")
            assert "don't have that" in m["content"]
    asyncio.run(go())
