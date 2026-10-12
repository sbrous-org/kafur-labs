"""The OpenAI-compatible adapter is what makes the model pluggable (Ollama, vLLM, LiteLLM proxy,
OpenAI, OpenRouter, ...). Verify it against a fake streaming server so no real model is needed."""
import asyncio
import json
import socket
import threading
import time

import pytest
import uvicorn
from fastapi import FastAPI
from fastapi.responses import JSONResponse, StreamingResponse

from app import llm
from app.bot import parse_output
from app.config import Settings


def _fake(status=200):
    api = FastAPI()
    seen = {}

    @api.post("/v1/chat/completions")
    async def chat(body: dict):
        seen["body"] = body
        if status != 200:
            return JSONResponse({"error": "boom"}, status_code=status)
        text = 'Try Kaziranga [kaziranga].\n###PLAN\n{"ops":[{"op":"add","day":1,"title":"Kaziranga","kb_id":"kaziranga"}]}'

        async def gen():
            for i in range(0, len(text), 9):
                yield "data: " + json.dumps({"choices": [{"delta": {"content": text[i:i + 9]}}]}) + "\n\n"
            yield 'data: {"choices":[{"delta":{}}]}\n\n'
            yield "data: [DONE]\n\n"
        return StreamingResponse(gen(), media_type="text/event-stream")
    return api, seen


def _serve(api):
    s = socket.socket(); s.bind(("127.0.0.1", 0)); port = s.getsockname()[1]; s.close()
    srv = uvicorn.Server(uvicorn.Config(api, host="127.0.0.1", port=port, log_level="error"))
    threading.Thread(target=srv.run, daemon=True).start()
    while not srv.started:
        time.sleep(0.05)
    return srv, port


def test_streams_and_parses_openai_compatible_sse():
    api, seen = _fake()
    srv, port = _serve(api)
    try:
        st = Settings(llm_provider="openai", llm_base_url=f"http://127.0.0.1:{port}/v1", llm_model="tiny-model", llm_api_key="k")

        async def go():
            return "".join([d async for d in llm.stream(st, [{"role": "user", "content": "hi"}])])
        out = asyncio.run(go())
        reply, ops = parse_output(out)
        assert reply == "Try Kaziranga [kaziranga]." and ops[0]["kb_id"] == "kaziranga"
        assert seen["body"]["model"] == "tiny-model" and seen["body"]["stream"] is True
    finally:
        srv.should_exit = True


def test_http_error_becomes_llmerror():
    api, _ = _fake(status=500)
    srv, port = _serve(api)
    try:
        st = Settings(llm_provider="openai", llm_base_url=f"http://127.0.0.1:{port}/v1")

        async def go():
            async for _ in llm.stream(st, [{"role": "user", "content": "hi"}]):
                pass
        with pytest.raises(llm.LLMError):
            asyncio.run(go())
    finally:
        srv.should_exit = True


def test_unreachable_endpoint_becomes_llmerror():
    st = Settings(llm_provider="openai", llm_base_url="http://127.0.0.1:9/v1")

    async def go():
        async for _ in llm.stream(st, [{"role": "user", "content": "hi"}]):
            pass
    with pytest.raises(llm.LLMError):
        asyncio.run(go())
