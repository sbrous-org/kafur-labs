"""Knowledge base: ingest JSONL -> kb_docs, and hybrid (full-text + vector) retrieval.
Each entry is authored chunk-sized (~50-120 words), so one doc == one chunk."""
import hashlib
import json
import re

import asyncpg

from .config import Settings
from .embeddings import embed, vec_literal

STATE_WORDS = {
    "Assam": "assam guwahati kaziranga majuli manas sivasagar jorhat dibrugarh kamakhya tezpur brahmaputra",
    "Meghalaya": "meghalaya shillong cherrapunji sohra dawki mawlynnong cherrapunjee khasi umiam",
    "Arunachal Pradesh": "arunachal tawang ziro namdapha itanagar sela",
    "Nagaland": "nagaland kohima dimapur hornbill dzukou khonoma",
    "Manipur": "manipur imphal loktak ukhrul",
    "Mizoram": "mizoram aizawl champhai reiek",
    "Tripura": "tripura agartala neermahal unakoti",
    "Sikkim": "sikkim gangtok nathu pelling yumthang tsomgo changu gurudongmar",
}
_WORD_TO_STATE = {w: st for st, ws in STATE_WORDS.items() for w in ws.split()}
_TOK = re.compile(r"[a-z0-9]{3,}")
_STOP = set("the and for with that this are you can have from what when where which would could should about there their any not but all our your how why does did doing get lets let just also into over out its who has was were been being very much some more most than then them they".split())
PERMIT_WORDS = {"permit", "permits", "ilp", "pap", "visa", "permission", "inner", "line", "passport"}
SEASON_WORDS = {"season", "weather", "monsoon", "rain", "winter", "summer", "month", "october", "november",
                "december", "january", "february", "march", "april", "when", "best", "climate"}


def detect_states(text: str) -> set[str]:
    return {_WORD_TO_STATE[w] for w in _TOK.findall(text.lower()) if w in _WORD_TO_STATE}


def tokens(text: str) -> list[str]:
    return [t for t in dict.fromkeys(_TOK.findall(text.lower())) if t not in _STOP]


def _convert(path_name: str, d: dict) -> dict | None:
    """Accept the new schema as-is and adapt Oxomiai's places/hidden_gems rows."""
    if "id" in d and "text" in d:
        return d
    if "site_id" in d:
        text = d.get("embedding_text") or d.get("short_description", "")
        extra = []
        if d.get("visiting_hours"):
            extra.append(f"Hours: {d['visiting_hours']}.")
        if d.get("entry_fee_details"):
            extra.append(f"Entry: {d['entry_fee_details']}.")
        return dict(id=d["site_id"], kind="place", state="Assam", region=d.get("district"), title=d["site_name"],
                    text=" ".join([text, d.get("short_description", ""), *extra]).strip(),
                    best_seasons=d.get("best_seasons", []), high_risk=False,
                    source="oxomiai knowledge_base/places.jsonl", last_verified=d.get("last_verified_date"),
                    lat=d.get("latitude"), lon=d.get("longitude"))
    if "gem_id" in d:
        return dict(id=d["gem_id"], kind="gem", state="Assam", region=d.get("district"), title=d["name"],
                    text=f"{d.get('embedding_text','')} {d.get('why_hidden','')} How to reach: {d.get('how_to_reach','')} Best time: {d.get('best_time','')}",
                    best_seasons=[], high_risk=False, source="oxomiai knowledge_base/hidden_gems.jsonl",
                    last_verified=None, lat=d.get("latitude"), lon=d.get("longitude"))
    return None  # local_experts etc. are out of scope


async def ingest(pool: asyncpg.Pool, s: Settings) -> int:
    docs = []
    for f in sorted(s.kb_dir.glob("*.jsonl")):
        for line in f.read_text().splitlines():
            if line.strip():
                d = _convert(f.name, json.loads(line))
                if d:
                    docs.append(d)
    existing = {r["id"]: r["h"] for r in await pool.fetch("select id, h from kb_docs")}
    todo = []
    for d in docs:
        d["h"] = hashlib.sha1(json.dumps(d, sort_keys=True).encode() + s.embed_provider.encode() + s.embed_model.encode()).hexdigest()
        if existing.get(d["id"]) != d["h"]:
            todo.append(d)
    if todo:
        vecs = await embed(s, [f"{d['title']}. {d['text']}" for d in todo])
        async with pool.acquire() as c, c.transaction():
            for i, d in enumerate(todo):
                await c.execute(
                    """insert into kb_docs(id,kind,state,region,title,text,best_seasons,high_risk,source,last_verified,lat,lon,h,embedding)
                       values($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14::vector)
                       on conflict (id) do update set kind=$2,state=$3,region=$4,title=$5,text=$6,best_seasons=$7,
                         high_risk=$8,source=$9,last_verified=$10,lat=$11,lon=$12,h=$13,embedding=$14::vector""",
                    d["id"], d.get("kind", "place"), d.get("state"), d.get("region"), d["title"], d["text"],
                    d.get("best_seasons") or [], bool(d.get("high_risk")), d.get("source"), d.get("last_verified"),
                    d.get("lat"), d.get("lon"), d["h"], vec_literal(vecs[i]) if vecs else None)
    keep = [d["id"] for d in docs]
    await pool.execute("delete from kb_docs where id <> all($1::text[])", keep)
    return len(docs)


async def search(pool: asyncpg.Pool, s: Settings, query: str, states: set[str], k: int = 4) -> list[asyncpg.Record]:
    """Hybrid retrieval: full-text OR-query + vector similarity, fused by RRF.
    State filter (when states are known) also admits NE-wide guide docs; falls back to unfiltered."""
    toks = tokens(query)
    qwords = set(toks)
    want_permit = bool(qwords & PERMIT_WORDS)
    want_season = bool(qwords & SEASON_WORDS)
    tsq = " | ".join(toks[:24])
    qvec = (await embed(s, [query]) or [None])[0]

    async def run(filter_states: set[str] | None):
        where, args = "true", []
        if filter_states:
            args.append(sorted(filter_states) + ["NE"])
            where = f"state = any(${len(args)}::text[])"
        fts, vec = [], []
        if tsq:
            args_f = args + [tsq]
            fts = await pool.fetch(
                f"select id from kb_docs where {where} and tsv @@ to_tsquery('english', ${len(args_f)}) "
                f"order by ts_rank(tsv, to_tsquery('english', ${len(args_f)})) desc limit 12", *args_f)
        if qvec is not None:
            args_v = args + [vec_literal(qvec)]
            vec = await pool.fetch(
                f"select id from kb_docs where {where} and embedding is not null "
                f"and embedding <=> ${len(args_v)}::vector < {float(s.embed_max_dist)} "
                f"order by embedding <=> ${len(args_v)}::vector limit 12", *args_v)
        return fts, vec

    fts, vec = await run(states or None)
    if len(set(r["id"] for r in fts) | set(r["id"] for r in vec)) < 2 and states:
        fts, vec = await run(None)
    score: dict[str, float] = {}
    for lst in (fts, vec):
        for rank, r in enumerate(lst):
            score[r["id"]] = score.get(r["id"], 0.0) + 1.0 / (60 + rank)
    if want_permit or want_season:  # pin guide docs for the relevant states (state-specific beats NE-wide)
        kinds = (["permit"] if want_permit else []) + (["season"] if want_season else [])
        rows = await pool.fetch(
            "select id, state from kb_docs where kind = any($1::text[]) and (state = any($2::text[]) or state = 'NE')",
            kinds, sorted(states) + ["NE"] if states else ["NE"])
        for r in rows:
            score[r["id"]] = score.get(r["id"], 0.0) + (0.06 if r["state"] in states else 0.03)
    if score:  # entity boost: the query names a place (its id parts / first title word), not a descriptor like "wildlife"
        for r in await pool.fetch("select id, title, kind from kb_docs where id = any($1::text[]) and kind in ('place','gem')", list(score)):
            first = tokens(r["title"])[:1]
            if (set(first) | set(tokens(r["id"].replace("-", " ").replace("_", " ")))) & qwords:
                score[r["id"]] += 0.04
    top = sorted(score, key=score.get, reverse=True)[:k]
    if not top:
        return []
    rows = {r["id"]: r for r in await pool.fetch("select * from kb_docs where id = any($1::text[])", top)}
    return [rows[i] for i in top]
