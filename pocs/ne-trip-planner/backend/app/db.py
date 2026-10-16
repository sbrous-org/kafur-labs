import asyncpg

from .config import Settings


def schema_sql(dim: int) -> str:
    return f"""
create extension if not exists vector;
create table if not exists sessions(
  id uuid primary key default gen_random_uuid(),
  code text unique not null,
  created_at timestamptz not null default now(),
  last_active_at timestamptz not null default now(),
  plan jsonb not null default '{{"days": []}}',
  plan_version int not null default 0,
  bot_seq bigint not null default 0,
  tokens_used int not null default 0
);
create table if not exists participants(
  id uuid primary key default gen_random_uuid(),
  session_id uuid not null references sessions(id) on delete cascade,
  name text not null,
  token_hash text unique not null,
  joined_at timestamptz not null default now(),
  conns int not null default 0
);
create table if not exists messages(
  id bigserial primary key,
  session_id uuid not null references sessions(id) on delete cascade,
  participant_id uuid references participants(id) on delete set null,
  role text not null check (role in ('user','bot','system')),
  content text not null,
  meta jsonb not null default '{{}}',
  created_at timestamptz not null default now()
);
create index if not exists messages_session_idx on messages(session_id, id);
create table if not exists kb_docs(
  id text primary key,
  kind text not null,
  state text,
  region text,
  title text not null,
  text text not null,
  best_seasons text[] not null default '{{}}',
  high_risk boolean not null default false,
  source text,
  last_verified text,
  lat double precision,
  lon double precision,
  h text,
  tsv tsvector generated always as (
    setweight(to_tsvector('english', title), 'A') ||
    setweight(to_tsvector('english', coalesce(state,'') || ' ' || coalesce(region,'')), 'B') ||
    setweight(to_tsvector('english', text), 'C')) stored,
  embedding vector({dim})
);
create index if not exists kb_docs_tsv_idx on kb_docs using gin(tsv);
create index if not exists kb_docs_state_idx on kb_docs(state);
"""


async def make_pool(s: Settings) -> asyncpg.Pool:
    pool = await asyncpg.create_pool(s.database_url, min_size=1, max_size=10)
    async with pool.acquire() as c:
        await c.execute("select pg_advisory_lock(727272)")  # serialise concurrent startups
        try:
            await c.execute(schema_sql(s.embed_dim))
        finally:
            await c.execute("select pg_advisory_unlock(727272)")
    return pool
