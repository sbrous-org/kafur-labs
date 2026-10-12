"""Embedding port. 'hash' needs no model (hashed bag-of-words), 'openai' calls any
OpenAI-compatible /embeddings endpoint (Ollama nomic-embed-text, LiteLLM, OpenAI...)."""
import math
import re
import zlib

import httpx

from .config import Settings

_WORD = re.compile(r"[a-z0-9]+")


def hash_embed(text: str, dim: int) -> list[float]:
    v = [0.0] * dim
    words = _WORD.findall(text.lower())
    grams = words + [a + "_" + b for a, b in zip(words, words[1:])]
    for g in grams:
        h = zlib.crc32(g.encode())
        v[h % dim] += 1.0 if (h >> 16) & 1 else -1.0
    n = math.sqrt(sum(x * x for x in v)) or 1.0
    return [x / n for x in v]


async def embed(s: Settings, texts: list[str]) -> list[list[float]] | None:
    if s.embed_provider == "none":
        return None
    if s.embed_provider == "hash":
        return [hash_embed(t, s.embed_dim) for t in texts]
    headers = {"Authorization": f"Bearer {s.embed_api_key}"} if s.embed_api_key else {}
    async with httpx.AsyncClient(timeout=60) as c:
        r = await c.post(f"{s.embed_base_url.rstrip('/')}/embeddings", headers=headers,
                         json={"model": s.embed_model, "input": texts})
        r.raise_for_status()
        out = [d["embedding"] for d in sorted(r.json()["data"], key=lambda d: d["index"])]
    if out and len(out[0]) != s.embed_dim:
        raise RuntimeError(f"embedding dim {len(out[0])} != EMBED_DIM {s.embed_dim}; fix EMBED_DIM and recreate kb_docs")
    return out


def vec_literal(v: list[float]) -> str:
    return "[" + ",".join(f"{x:.6f}" for x in v) + "]"
