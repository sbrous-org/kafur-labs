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
        system_prompt = """You are a travel query router for an Assam-focused travel bot.

        Analyze each query and determine:
        1. Intent: place_info (asking about a place), weather (asking about weather/timing),
           itinerary (multi-part trip planning), expert_needed (hyperlocal/booking), chitchat (out of scope)
        2. Entities: extract place names, seasons, activities, dates mentioned
        3. Route: which source(s) to use:
           - KB: for place descriptions, history, attractions, logistics
           - WX: for current/forecast weather only (not general seasonal info)
           - EXP: for hyperlocal, current conditions, live bookings, or safety judgments the bot
             cannot responsibly make from general knowledge
           - REFUSE: if completely out of scope or safety-critical without expert routing

        IMPORTANT: a request to "plan a trip" or build a multi-day itinerary using known places
        (e.g. "plan a 2-day Assam trip") is intent=itinerary, route=["KB", "WX"] — it does NOT need
        EXP unless the user explicitly asks for a human guide, a live booking, or something no
        general itinerary can answer (e.g. "is the road currently passable").

        Output JSON:
        {
            "intent": "...",
            "entities": {"place_names": [...], "season": "...", "activity": "..."},
            "route": ["KB"] or ["WX"] or ["KB", "WX"] or ["EXP"] or ["REFUSE"],
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
