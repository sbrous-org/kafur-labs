from typing import Dict, List, Any
import json
import re
from services.llm_provider import LLMProvider


def extract_json(text: str) -> Dict[str, Any]:
    """
    Extract a JSON object from LLM output that may be wrapped in markdown
    code fences (```json ... ```) or have leading/trailing prose, both of
    which are common with GPT-4o and other chat models even when asked
    for raw JSON.
    """
    text = text.strip()

    # Strip markdown code fences: ```json ... ``` or ``` ... ```
    fence_match = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, re.DOTALL)
    if fence_match:
        text = fence_match.group(1)
    else:
        # Fall back to the first {...} block in the text
        brace_match = re.search(r"\{.*\}", text, re.DOTALL)
        if brace_match:
            text = brace_match.group(0)

    return json.loads(text)


class QueryRouter:
    """Routes queries to appropriate sources (KB, weather, expert, refuse)."""

    def __init__(self, llm_provider: LLMProvider):
        self.llm = llm_provider

    def route(self, query: str, context_history: List[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        Determine which sources to use for a query.

        Returns:
            {
                "intent": "place_info" | "weather" | "itinerary" | "expert_needed" | "chitchat",
                "entities": {"place_names": [...], "seasons": [...], ...},
                "route": ["KB"] | ["WX"] | ["KB", "WX"] | ["EXP"] | ["REFUSE"],
                "reasoning": "...",
                "confidence": 0.95
            }
        """
        system_prompt = """You are the query router for Oxomiai, a Northeast Assam travel companion.

        Analyze each query and determine:
        1. Intent: place_info (asking about a place), weather (weather/timing),
           itinerary (multi-part trip planning), hidden_gems (asking for offbeat / lesser-known /
           local-only spots), local_expert (wants to talk to / connect with a real local guide or
           person), expert_needed (hyperlocal live conditions or a booking/permit the bot cannot
           responsibly answer), chitchat (out of scope)
        2. Entities: place names, region/anchor (e.g. "Majuli", "Kaziranga"), season, activity,
           and interests (a list, e.g. ["birding", "culture"])
        3. Route: which source(s) to use:
           - KB: place descriptions, history, attractions, logistics, multi-day itineraries
           - WX: current/forecast weather only (not general seasonal info)
           - GEMS: hidden / offbeat / "what do most travellers miss" / "local pick" requests
           - EXPERT: user explicitly wants to talk to, video-call, or be connected with a real
             local guide / someone who lives there
           - EXP: hyperlocal live conditions ("is the road passable right now") or a real
             transaction (book a permit, reserve a safari) — bot must hand off, not guess
           - REFUSE: completely out of scope, or safety-critical with no expert route

        IMPORTANT:
        - "plan a trip" / build a multi-day itinerary using known places is intent=itinerary,
          route=["KB", "WX"]. It does NOT need EXP.
        - "show me hidden gems", "anything offbeat near X", "what do locals do" is
          intent=hidden_gems, route=["GEMS"].
        - "can I talk to someone local", "connect me with a guide", "I want a real person" is
          intent=local_expert, route=["EXPERT"].

        Output JSON:
        {
            "intent": "...",
            "entities": {"place_names": [...], "region": "...", "season": "...", "activity": "...", "interests": [...]},
            "route": ["KB"] or ["WX"] or ["KB","WX"] or ["GEMS"] or ["EXPERT"] or ["EXP"] or ["REFUSE"],
            "reasoning": "...",
            "confidence": 0.95
        }"""

        context_str = ""
        if context_history:
            context_str = "\n\nPrevious turns:\n" + "\n".join(
                [f"  Q: {t['query']}\n  A: {t['answer'][:100]}..." for t in context_history[-3:]]
            )

        user_message = f"Query: {query}{context_str}"

        response = None
        try:
            response = self.llm.invoke(system_prompt, user_message, max_tokens=300, temperature=0.1)
            result = extract_json(response)
            return result

        except Exception as e:
            print(f"Router error: {e} | raw response: {response!r}")
            return {
                "intent": "unknown",
                "entities": {},
                "route": ["REFUSE"],
                "reasoning": f"Internal error: {str(e)}",
                "confidence": 0.0
            }
