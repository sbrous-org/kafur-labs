"""LLM port. One function: stream(settings, messages) -> async iterator of text deltas.

Providers:
  mock       - offline, deterministic; builds an answer from the retrieved KB block (demo/tests)
  openai     - ANY OpenAI-compatible /chat/completions endpoint: Ollama, vLLM, llama.cpp server,
               LiteLLM proxy (which fronts Anthropic/Gemini/Bedrock/...), OpenAI, OpenRouter, Groq...
  anthropic  - direct to api.anthropic.com/v1/messages. No extra container: for deployments where
               Claude is the only provider in play and litellm's own footprint isn't worth paying
               for (see ADR-0006). Still no vendor SDK — a second small HTTP+SSE translation,
               same spirit as the openai path above.
No vendor SDK, no native tool calling, no provider-specific features are required.
"""
import asyncio
import json
import re
from typing import AsyncIterator

import httpx

from .config import Settings


class LLMError(Exception):
    pass


async def stream(s: Settings, messages: list[dict]) -> AsyncIterator[str]:
    if s.llm_provider == "mock":
        async for t in _mock(messages):
            yield t
        return
    if s.llm_provider == "anthropic":
        async for t in _anthropic(s, messages):
            yield t
        return
    if s.llm_provider != "openai":
        raise LLMError(f"unknown LLM_PROVIDER {s.llm_provider!r} (use 'mock', 'openai' or 'anthropic')")
    headers = {"Authorization": f"Bearer {s.llm_api_key}"} if s.llm_api_key else {}
    body = {"model": s.llm_model, "messages": messages, "stream": True, "temperature": 0.3, "max_tokens": 700}
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(s.llm_timeout, connect=10)) as c:
            async with c.stream("POST", f"{s.llm_base_url.rstrip('/')}/chat/completions", headers=headers, json=body) as r:
                if r.status_code != 200:
                    raise LLMError(f"LLM HTTP {r.status_code}: {(await r.aread())[:200]!r}")
                async for line in r.aiter_lines():
                    if not line.startswith("data:"):
                        continue
                    data = line[5:].strip()
                    if data == "[DONE]":
                        return
                    try:
                        delta = json.loads(data)["choices"][0]["delta"].get("content")
                    except (KeyError, IndexError, json.JSONDecodeError):
                        continue
                    if delta:
                        yield delta
    except httpx.HTTPError as e:
        raise LLMError(f"LLM unreachable: {e}") from e


async def _anthropic(s: Settings, messages: list[dict]) -> AsyncIterator[str]:
    """Direct to Anthropic's native Messages API (no OpenAI-shaped proxy in front).

    Pre-processing: Anthropic takes `system` as its own top-level field, not a message
    with role "system" — pull it out of the list. Post-processing: its SSE stream emits
    several event types; we only care about `content_block_delta` (text_delta) events,
    and stop at `message_stop`.
    """
    system = "\n".join(m["content"] for m in messages if m["role"] == "system")
    turns = [m for m in messages if m["role"] != "system"]
    headers = {
        "x-api-key": s.anthropic_api_key,
        "anthropic-version": s.anthropic_version,
        "content-type": "application/json",
    }
    body = {"model": s.llm_model, "system": system, "messages": turns,
            "stream": True, "temperature": 0.3, "max_tokens": 700}
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(s.llm_timeout, connect=10)) as c:
            url = f"{s.anthropic_base_url.rstrip('/')}/v1/messages"
            async with c.stream("POST", url, headers=headers, json=body) as r:
                if r.status_code != 200:
                    raise LLMError(f"LLM HTTP {r.status_code}: {(await r.aread())[:200]!r}")
                async for line in r.aiter_lines():
                    if not line.startswith("data:"):
                        continue
                    data = line[5:].strip()
                    if not data:
                        continue
                    try:
                        ev = json.loads(data)
                    except json.JSONDecodeError:
                        continue
                    if ev.get("type") == "content_block_delta":
                        delta = ev.get("delta") or {}
                        if delta.get("type") == "text_delta" and delta.get("text"):
                            yield delta["text"]
                    elif ev.get("type") == "message_stop":
                        return
    except httpx.HTTPError as e:
        raise LLMError(f"LLM unreachable: {e}") from e


# ---------------------------------------------------------------- mock
_DOC = re.compile(r"^\[([^\]]+)\] ([^|]+)\| ([^|]*)\| ([^|]*)\| (.*)$", re.M)


async def _mock(messages: list[dict]) -> AsyncIterator[str]:
    prompt = messages[-1]["content"]
    knowledge = prompt.split("KNOWLEDGE:")[-1].split("\nWEATHER:")[0].split("\nCURRENT PLAN:")[0]
    plan_txt = prompt.split("CURRENT PLAN:")[-1].split("\nTRAVELLERS:")[0]
    chat = prompt.split("CHAT:")[-1].split("Reply now.")[0]
    last = chat.strip().splitlines()[-1].lower() if chat.strip() else ""
    docs = [dict(id=m[0], title=m[1].strip(), state=m[2].strip(), kind=m[3].strip(), text=m[4]) for m in _DOC.findall(knowledge)]
    if not docs:
        reply = "I don't have that in my notes yet. Tell me a state, place or month and I'll look again."
        ops = []
    else:
        bits = []
        for d in docs[:3]:
            first = re.split(r"(?<=[.!?])\s", d["text"])[0]
            bits.append(f"{d['title']}: {first} [{d['id']}]")
        reply = "From my notes: " + " ".join(bits)
        if any(d["kind"] in ("permit", "season") or "permit" in d["text"].lower() for d in docs):
            reply += " Please verify before you travel."
        ops = []
        if re.search(r"plan|itinerar|days|trip|add|include|want|include|visit|culture|wildlife", last):
            nxt = max([int(x) for x in re.findall(r"Day (\d+)", plan_txt)] or [0]) + 1
            for d in [d for d in docs if d["kind"] in ("place", "gem") and d["title"] not in plan_txt][:3]:
                ops.append({"op": "add", "day": min(nxt, 14), "title": d["title"], "note": d["state"], "kb_id": d["id"]})
                nxt += 1
        if ops:
            reply += f" I added {len(ops)} stop(s) to the plan."
    out = reply + (("\n###PLAN\n" + json.dumps({"ops": ops})) if ops else "")
    for i in range(0, len(out), 14):
        yield out[i:i + 14]
        await asyncio.sleep(0.004)
