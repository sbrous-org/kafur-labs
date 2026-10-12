import os
import socket
import threading
import time

import pytest

os.environ.setdefault("DATABASE_URL", "postgresql://postgres@127.0.0.1:5433/netrip")
os.environ["LLM_PROVIDER"] = "mock"
os.environ["EMBED_PROVIDER"] = "hash"
os.environ["WEATHER"] = "0"


def _db_up() -> bool:
    import asyncio
    import asyncpg

    async def go():
        c = await asyncpg.connect(os.environ["DATABASE_URL"], timeout=3)
        await c.close()
    try:
        asyncio.run(go())
        return True
    except Exception:
        return False


@pytest.fixture(scope="session")
def server():
    """Real uvicorn server on a free port, against a real Postgres+pgvector (skips if none)."""
    if not _db_up():
        pytest.skip("no Postgres reachable via DATABASE_URL")
    import uvicorn
    from app.main import app
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    srv = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning"))
    th = threading.Thread(target=srv.run, daemon=True)
    th.start()
    for _ in range(100):
        if srv.started:
            break
        time.sleep(0.1)
    yield f"127.0.0.1:{port}"
    srv.should_exit = True
    th.join(timeout=5)
