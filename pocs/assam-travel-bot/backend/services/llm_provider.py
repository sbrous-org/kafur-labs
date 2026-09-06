from abc import ABC, abstractmethod
from typing import Dict, Any
import json


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    def invoke(self, system_prompt: str, user_message: str, max_tokens: int = 500, temperature: float = 0.7) -> str:
        """
        Invoke the LLM with a prompt.

        Args:
            system_prompt: System context/instructions
            user_message: User query
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature. Use near-0 for deterministic
                classification/routing, higher (0.6-0.8) for natural-language synthesis.

        Returns:
            String response from the LLM
        """
        pass


class ClaudeProvider(LLMProvider):
    """Anthropic Claude provider."""

    def __init__(self, api_key: str, model: str = "claude-3-5-haiku-20241022"):
        from anthropic import Anthropic
        self.client = Anthropic(api_key=api_key)
        self.model = model

    def invoke(self, system_prompt: str, user_message: str, max_tokens: int = 500, temperature: float = 0.7) -> str:
        response = self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}]
        )
        return response.content[0].text


class OpenAIProvider(LLMProvider):
    """OpenAI GPT provider."""

    def __init__(self, api_key: str, model: str = "gpt-3.5-turbo"):
        from openai import OpenAI
        self.client = OpenAI(api_key=api_key)
        self.model = model

    def invoke(self, system_prompt: str, user_message: str, max_tokens: int = 500, temperature: float = 0.7) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            max_tokens=max_tokens,
            temperature=temperature
        )
        return response.choices[0].message.content


class OpenRouterProvider(LLMProvider):
    """OpenRouter API provider (supports multiple models via single API)."""

    def __init__(self, api_key: str, model: str = "openai/gpt-4o"):
        from openai import OpenAI
        self.client = OpenAI(
            api_key=api_key,
            base_url="https://openrouter.ai/api/v1"
        )
        self.model = model

    def invoke(self, system_prompt: str, user_message: str, max_tokens: int = 500, temperature: float = 0.7) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            max_tokens=max_tokens,
            temperature=temperature
        )
        return response.choices[0].message.content


class MockProvider(LLMProvider):
    """
    Offline stub — no GPU, no API key, no network (beyond the weather/geocoding
    calls the bot itself makes). Deterministic: keyword-routes queries and
    reformats the retrieved KB/weather sources into a readable answer, so the
    whole bot — routing, KB, weather, hidden gems, experts, and the UI — runs
    end to end and demos correctly without a hosted LLM. The prose is templated,
    not generated; switch to claude/openai/openrouter for natural answers and
    real answer-quality evaluation.
    """

    def __init__(self, model: str = "mock"):
        self.model = model

    def invoke(self, system_prompt: str, user_message: str, max_tokens: int = 500, temperature: float = 0.7) -> str:
        # Keyword-route on the *current* query only. QueryRouter appends prior
        # turns after a "Previous turns:" marker; matching keywords in that
        # history would make mock multi-turn routing stick to the first intent.
        text = user_message.lower().split("\n\nprevious turns:")[0]

        # Router calls ask for JSON intent/entity extraction — sniff for that shape
        # and return the schema router.QueryRouter.route expects.
        sp = system_prompt.lower()
        if "json" in sp and ("intent" in sp or "route" in sp):
            if any(w in text for w in ("hidden gem", "hidden gems", "offbeat", "off the beaten", "lesser known", "lesser-known", "local pick", "locals only", "what do locals", "most travellers miss", "most tourists miss")):
                intent, route = "hidden_gems", ["GEMS"]
            elif any(w in text for w in ("talk to someone", "talk to a local", "talk to a real", "connect me with", "connect with a", "speak to a guide", "real person", "someone who lives", "actual local", "video call with", "local expert")):
                intent, route = "local_expert", ["EXPERT"]
            elif any(w in text for w in ("weather", "rain", "temperature", "forecast", "climate")):
                # Compound "tell me about X and the weather" → KB + WX.
                if any(w in text for w in ("worth visiting", "tell me about", "what would i do",
                                           "what to do", "about ", "and what")):
                    intent, route = "itinerary", ["KB", "WX"]
                else:
                    intent, route = "weather", ["WX"]
            elif any(w in text for w in ("itinerary", "plan a", "-day", "day trip", "days in")):
                intent, route = "itinerary", ["KB", "WX"]
            elif any(w in text for w in ("book", "hire a guide", "contact", "phone number", "currently passable", "permit")):
                intent, route = "expert_needed", ["EXP"]
            else:
                intent, route = "place_info", ["KB"]
            # Region can be carried from earlier turns ("plan 3 days around Sivasagar"
            # → "talk to a local for this one"), so fall back to the full message.
            full = user_message.lower()
            region = None
            for r in ("majuli", "kaziranga", "sivasagar", "charaideo", "jorhat", "guwahati",
                      "kamrup", "morigaon", "tezpur", "hajo", "pobitora"):
                if r in text or r in full:
                    region = r.capitalize()
                    break
            interests = [
                w for w in ("birding", "wildlife", "culture", "heritage", "history", "tea",
                            "food", "safari", "temple", "craft", "photography", "trekking")
                if w in text
            ]
            return json.dumps({
                "intent": intent,
                "entities": {
                    "place_names": [region] if region else [],
                    "region": region,
                    "season": None,
                    "activity": interests[0] if interests else None,
                    "interests": interests,
                },
                "route": route,
                "reasoning": "mock provider: keyword-based routing",
                "confidence": 0.9,
            })

        # Short framing lines for the differentiator cards — keep these clean so
        # the mock UI still looks right without a hosted provider.
        if "hidden-gem" in sp:
            return "Beyond the guidebook stops — here's what most travellers miss:"
        if "connecting the traveller with a verified local guide" in sp:
            return "Of course — Oxomiai connects you straight to a verified local guide."

        # Synthesis call: build a readable answer straight from the structured
        # sources QueryRouter/synthesis put in the user message. Deterministic
        # and never invents facts — but presentable, so the offline demo works.
        if "travel guide for assam" in sp or "synthesize" in sp:
            return self._mock_synthesis(user_message)

        return (
            "[mock LLM] This is a deterministic offline response for local development. "
            "Set LLM_PROVIDER to a hosted provider (claude/openai/openrouter) for real answers. "
            f"Your query was: {user_message[:200]}"
        )

    @staticmethod
    def _mock_synthesis(user_message: str) -> str:
        """Reformat the sources block into a plain-language answer (offline)."""
        import re

        body = user_message.split("\n\nprevious turns:")[0]
        query = ""
        m = re.match(r"\s*Query:\s*(.+)", body)
        if m:
            query = m.group(1).strip()
        ql = query.lower()
        wants_itinerary = any(w in ql for w in ("day trip", "-day", " days", "itinerary", "plan a", "plan me"))

        out: List[str] = []
        kb_paras: List[str] = []
        wx_paras: List[str] = []

        # --- Knowledge base entries (collected first, rendered before weather) ---
        kb = re.search(r"Knowledge base results:\n(.*?)(?:\n\n☀|\n\nNote:|\Z)", body, re.DOTALL)
        kb_entries = []
        if kb:
            kb_entries = re.findall(
                r"-\s*([^:\n]+):\s*([^\n]+)\n(?:\s*Hours:\s*([^\n]+)\n)?(?:\s*Attractions:\s*([^\n]+))?",
                kb.group(1),
            )
            for name, desc, hours, attractions in kb_entries:
                para = f"**{name.strip()}** — {desc.strip()}"
                if attractions.strip():
                    para += f" Known for {attractions.strip().lower()}."
                if hours.strip():
                    para += f" Visiting hours: {hours.strip()}."
                kb_paras.append(para)

        # --- Itinerary shape: emit "Day N:" headers so the UI draws the timeline ---
        if wants_itinerary and len(kb_entries) >= 2:
            n = 2
            mnum = re.search(r"(\d+)\s*[- ]?day", ql)
            if mnum:
                n = max(1, min(int(mnum.group(1)), len(kb_entries)))
            lines = ["A quick offline outline — a hosted LLM adds pacing, travel time and stays:"]
            for i, (name, desc, _h, _a) in enumerate(kb_entries[:n], start=1):
                lines.append(f"Day {i}: {name.strip()}")
                lines.append(f"- {desc.strip()}")
            return "\n".join(lines)

        # --- Weather ---
        wx = re.search(r"Weather at ([^\n:]+):\n(.*?)(?:\n\n|\Z)", body, re.DOTALL)
        if wx:
            loc = wx.group(1).strip()
            fields = dict(re.findall(r"-\s*([A-Za-z ]+):\s*([^\n]+)", wx.group(1) + wx.group(2)))
            temp = fields.get("Temperature", "?")
            cond = fields.get("Condition", "conditions unclear")
            hum = fields.get("Humidity")
            wind = fields.get("Wind")
            line = f"Right now in {loc} it's {temp}, {cond.lower()}"
            if hum:
                line += f", humidity {hum}"
            if wind:
                line += f", wind {wind}"
            wx_paras.append(line + ".")

            fc = re.search(r"3-day forecast:\n(.*?)(?:\n\n|\Z)", body, re.DOTALL)
            if fc:
                days = [ln.strip() for ln in fc.group(1).splitlines() if ln.strip()]
                if days:
                    wx_paras.append("Next few days: " + "; ".join(days) + ".")
            sr = re.search(r"Sunrise:\s*([^\n]+)", body)
            ss = re.search(r"Sunset:\s*([^\n]+)", body)
            if sr and ss:
                wx_paras.append(f"Sun is up roughly {sr.group(1).strip()}–{ss.group(1).strip()}.")

        # --- Assemble: KB first, then weather ---
        if len(kb_paras) >= 2:
            out.append("Here's what the knowledge base has:")
        out.extend(kb_paras)
        out.extend(wx_paras)

        if "expert consultation" in body.lower():
            out.append(
                "For the current, on-the-ground details a local expert would answer this best."
            )

        if not out:
            return (
                "I don't have enough sourced information to answer that well. "
                "Try asking about a specific place, the weather somewhere, or a trip plan."
            )

        note = "\n\n(Offline preview — set a hosted LLM provider in .env for a natural, written answer.)"
        return "\n\n".join(out) + note


def create_llm_provider(config: Dict[str, Any]) -> LLMProvider:
    """
    Factory function to create LLM provider based on config.

    Args:
        config: Dict with 'provider' key and provider-specific settings

    Returns:
        LLMProvider instance

    Example:
        config = {
            "provider": "openrouter",
            "api_key": "sk-or-v1-...",
            "model": "openai/gpt-4o"
        }
        provider = create_llm_provider(config)
    """
    provider_type = config.get("provider", "claude").lower()
    api_key = config.get("api_key")

    # Mock runs anywhere with no GPU, key, or network — for local dev and eval.
    if provider_type == "mock":
        return MockProvider(model=config.get("model", "mock"))

    if not api_key:
        raise ValueError(f"API key required for {provider_type} provider")

    if provider_type == "claude":
        model = config.get("model", "claude-3-5-haiku-20241022")
        return ClaudeProvider(api_key=api_key, model=model)

    elif provider_type == "openai":
        model = config.get("model", "gpt-3.5-turbo")
        return OpenAIProvider(api_key=api_key, model=model)

    elif provider_type == "openrouter":
        model = config.get("model", "openai/gpt-4o")
        return OpenRouterProvider(api_key=api_key, model=model)

    else:
        raise ValueError(f"Unknown LLM provider: {provider_type}")
