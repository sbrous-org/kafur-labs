from typing import Dict, List, Any
import os
from openai import OpenAI


class QueryRouter:
    """Routes queries to appropriate sources (KB, weather, expert, refuse)."""

    def __init__(self):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

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
           - EXP: for hyperlocal, current conditions, bookings, safety-critical info
           - REFUSE: if completely out of scope or safety-critical without expert routing

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

        try:
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                temperature=0.3,
                max_tokens=300
            )

            import json
            result = json.loads(response.choices[0].message.content)
            return result

        except Exception as e:
            print(f"Router error: {e}")
            return {
                "intent": "unknown",
                "entities": {},
                "route": ["REFUSE"],
                "reasoning": f"Internal error: {str(e)}",
                "confidence": 0.0
            }
