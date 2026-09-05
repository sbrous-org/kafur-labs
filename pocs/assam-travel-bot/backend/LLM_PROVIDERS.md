# LLM Provider Architecture

The bot uses a pluggable LLM provider architecture, making it easy to swap providers without modifying core logic.

## How it works

1. **Config** (`config.py`) — Loads LLM settings from `.env` (provider, API key, model)
2. **LLM Provider** (`services/llm_provider.py`) — Abstract interface + implementations (Claude, OpenAI)
3. **Factory** (`services/llm_provider.py::create_llm_provider`) — Creates the right provider instance
4. **Services** (`router.py`, `synthesis.py`) — Use the provider via its abstract interface

The services don't care which LLM they're using — just call `llm.invoke(system_prompt, user_message)`.

## Supported providers

### Claude (Anthropic) — RECOMMENDED
- **Cheapest**: $0.80 per 1M input tokens, $4 per 1M output tokens
- Model: `claude-3-5-haiku-20241022` (default)
- API Key: Get free at https://console.anthropic.com/

```bash
LLM_PROVIDER=claude
ANTHROPIC_API_KEY=sk-ant-...
```

### OpenAI
- Model: `gpt-3.5-turbo` (default)
- API Key: Get free trial at https://platform.openai.com/account/api-keys

```bash
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...
```

### Mock — offline stub, no key / network (default)

Deterministic canned responses. Lets you run the bot end to end (routing, KB search,
weather guardrails, synthesis wiring) for local dev and the eval harness without any
real model. **Answer text is fake** — not for judging answer quality.

```bash
LLM_PROVIDER=mock
```

No `.env` keys required — this is the default. Switch to a hosted provider above for
real answers.

## Adding a new provider (e.g., Gemini, Llama)

### 1. Create a new class in `services/llm_provider.py`

```python
class GeminiProvider(LLMProvider):
    """Google Gemini provider."""

    def __init__(self, api_key: str, model: str = "gemini-pro"):
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        self.client = genai.GenerativeModel(model)

    def invoke(self, system_prompt: str, user_message: str, max_tokens: int = 500) -> str:
        response = self.client.generate_content(
            f"{system_prompt}\n\n{user_message}",
            max_output_tokens=max_tokens
        )
        return response.text
```

### 2. Update the factory in `services/llm_provider.py`

```python
def create_llm_provider(config: Dict[str, Any]) -> LLMProvider:
    provider_type = config.get("provider", "claude").lower()
    api_key = config.get("api_key")

    # ... existing code ...

    elif provider_type == "gemini":
        model = config.get("model", "gemini-pro")
        return GeminiProvider(api_key=api_key, model=model)

    else:
        raise ValueError(f"Unknown LLM provider: {provider_type}")
```

### 3. Update `.env.example` and `config.py`

Add the new provider's API key env var and update `Config.get_llm_config()` to know how to load it.

### 4. That's it!

No changes needed to `router.py`, `synthesis.py`, or `main.py`. They just work with the new provider.

## Configuration precedence

1. Environment variables (`.env` or system)
2. Default models per provider (e.g., Haiku for Claude)
3. Optional `LLM_MODEL` override for non-default models

Example:
```bash
LLM_PROVIDER=claude
ANTHROPIC_API_KEY=sk-ant-...
LLM_MODEL=claude-3-opus-20240229  # Use Opus instead of Haiku
```

## Cost comparison (POC testing)

For ~60 queries (typical 2-week POC):

| Provider | Model | Input | Output | Est. Total |
|----------|-------|-------|--------|-----------|
| Claude | Haiku | $0.01 | $0.04 | **$0.05** ✓ |
| OpenAI | GPT-3.5 | $0.03 | $0.09 | **$0.12** |

Claude Haiku is **10x cheaper** and almost as capable.

## Testing different providers

```bash
# Switch to OpenAI
cp .env.example .env
# Edit: LLM_PROVIDER=openai, add OPENAI_API_KEY
python -m uvicorn app.main:app --reload

# Switch back to Claude
# Edit: LLM_PROVIDER=claude, add ANTHROPIC_API_KEY
python -m uvicorn app.main:app --reload
```

No other code changes needed.
