"""All configuration comes from environment variables (see ../.env.example)."""
import os
from dataclasses import dataclass, field
from pathlib import Path


def _int(name: str, default: int) -> int:
    return int(os.getenv(name, default))


@dataclass(frozen=True)
class Settings:
    database_url: str = field(default_factory=lambda: os.getenv(
        "DATABASE_URL", "postgresql://netrip:netrip@localhost:5432/netrip"))
    # --- LLM port: "mock" (offline demo) or "openai" (any OpenAI-compatible endpoint:
    # Ollama, vLLM, llama.cpp, LiteLLM proxy, OpenAI, OpenRouter, Groq, Together...)
    llm_provider: str = field(default_factory=lambda: os.getenv("LLM_PROVIDER", "mock"))
    llm_base_url: str = field(default_factory=lambda: os.getenv("LLM_BASE_URL", "http://ollama:11434/v1"))
    llm_model: str = field(default_factory=lambda: os.getenv("LLM_MODEL", "qwen2.5:1.5b-instruct"))
    llm_api_key: str = field(default_factory=lambda: os.getenv("LLM_API_KEY", ""))
    llm_timeout: int = field(default_factory=lambda: _int("LLM_TIMEOUT", 90))
    # --- embeddings: "hash" (offline, no model), "openai" (any /v1/embeddings), "none"
    embed_provider: str = field(default_factory=lambda: os.getenv("EMBED_PROVIDER", "hash"))
    embed_base_url: str = field(default_factory=lambda: os.getenv("EMBED_BASE_URL", "") or os.getenv("LLM_BASE_URL", "http://ollama:11434/v1"))
    embed_model: str = field(default_factory=lambda: os.getenv("EMBED_MODEL", "nomic-embed-text"))
    embed_api_key: str = field(default_factory=lambda: os.getenv("EMBED_API_KEY", "") or os.getenv("LLM_API_KEY", ""))
    embed_max_dist: float = field(default_factory=lambda: float(os.getenv("EMBED_MAX_DIST", "0.85" if os.getenv("EMBED_PROVIDER", "hash") == "hash" else "0.6")))
    embed_dim: int = field(default_factory=lambda: _int("EMBED_DIM", 256))
    # --- limits
    max_participants: int = field(default_factory=lambda: _int("MAX_PARTICIPANTS", 8))
    session_ttl_days: int = field(default_factory=lambda: _int("SESSION_TTL_DAYS", 14))
    max_session_tokens: int = field(default_factory=lambda: _int("MAX_SESSION_TOKENS", 200_000))
    msgs_per_minute: int = field(default_factory=lambda: _int("MSGS_PER_MINUTE", 20))
    creates_per_hour: int = field(default_factory=lambda: _int("CREATES_PER_HOUR", 30))
    joins_per_minute: int = field(default_factory=lambda: _int("JOINS_PER_MINUTE", 20))
    kb_dir: Path = field(default_factory=lambda: Path(os.getenv("KB_DIR", str(Path(__file__).resolve().parents[2] / "knowledge_base"))))
    frontend_dir: Path = field(default_factory=lambda: Path(os.getenv("FRONTEND_DIR", str(Path(__file__).resolve().parents[2] / "frontend"))))
    weather: bool = field(default_factory=lambda: os.getenv("WEATHER", "1") == "1")


def get_settings() -> Settings:
    return Settings()
