from typing import Dict, List, Any
from services.llm_provider import LLMProvider


class AnswerSynthesis:
    """Synthesize final answer from retrieved sources."""

    def __init__(self, llm_provider: LLMProvider):
        self.llm = llm_provider

    def synthesize(
        self,
        query: str,
        route: List[str],
        kb_results: List[Dict[str, Any]] = None,
        weather_data: Dict[str, Any] = None,
        context_history: List[Dict[str, str]] = None
    ) -> str:
        """
        Synthesize a natural-language answer from retrieved sources.

        Guardrails:
        - Weather facts come from the API result verbatim, never fabricated
        - Place facts are grounded in KB chunks with source reference
        - Unknown places are admitted, not invented
        """
        kb_results = kb_results or []
        context_str = ""

        if context_history:
            context_str = "\n\nConversation context:\n" + "\n".join(
                [f"Q: {t['query']}\nA: {t['answer'][:100]}..." for t in context_history[-2:]]
            )

        # Build source summaries
        sources_info = ""

        if "KB" in route and kb_results:
            sources_info += "Knowledge base results:\n"
            for place in kb_results:
                sources_info += f"\n- {place['site_name']}: {place['short_description']}\n"
                sources_info += f"  Hours: {place['visiting_hours']}\n"
                sources_info += f"  Attractions: {', '.join(place['unique_attractions'][:3])}\n"

        if "WX" in route and weather_data:
            sources_info += f"\n☀️ Weather at {weather_data['location']}:\n"
            sources_info += f"- Temperature: {weather_data['current']['temp_c']}°C\n"
            sources_info += f"- Condition: {weather_data['current']['condition']}\n"
            sources_info += f"- Humidity: {weather_data['current']['humidity']}%\n"
            sources_info += f"- Wind: {weather_data['current']['wind_speed_kmh']} km/h\n"

            if weather_data.get('sunrise'):
                sources_info += f"\n🌅 Sunrise: {weather_data['sunrise']}\n"
                sources_info += f"🌇 Sunset: {weather_data['sunset']}\n"

            sources_info += f"\n📅 3-day forecast:\n"
            for day in weather_data.get('forecast_3days', []):
                sources_info += f"  {day['date']}: {day['high_c']}°C / {day['low_c']}°C, {day['condition']}\n"

        if "EXP" in route:
            sources_info += "\nNote: This query requires expert consultation for hyperlocal details.\n"

        system_prompt = """You are a knowledgeable travel guide for Assam, India.

        Your job is to synthesize helpful, accurate answers from provided sources.

        GUARDRAILS:
        1. Weather facts: State only what's in the weather data. Never invent weather or make forecasts beyond provided data.
        2. Place facts: Ground answers in the provided KB results. Add source place names. If something isn't in the KB, say so.
        3. Honesty: If you don't have enough information to answer, say so and suggest what would help.
        4. Expert escalation: If the query is hyperlocal/booking/current-conditions-critical, recommend they contact a local expert.

        Tone: Helpful, conversational, friendly, and always honest about limitations."""

        user_message = f"""Query: {query}

{sources_info}

{context_str}

Provide a natural, helpful answer using only the sources above. Be specific (cite place names, facts), honest about unknowns, and conversational."""

        try:
            answer = self.llm.invoke(system_prompt, user_message, max_tokens=500)
            return answer

        except Exception as e:
            # Log full detail server-side; never surface raw provider errors
            # (they can include internal request/user IDs) to the end user.
            print(f"Synthesis error: {e}")
            return "Sorry, I'm having trouble reaching my answer engine right now. Please try again in a moment."

    def intro_hidden_gems(self, query: str, gems: List[Dict[str, Any]]) -> str:
        """
        One-line intro for a hidden-gems card. The gem data itself is returned
        verbatim in the response — the LLM only frames it, and must not add
        places that aren't in the provided list.
        """
        if not gems:
            return (
                "I don't have curated hidden gems for that area yet — I keep this list "
                "small and local, so I'd rather say so than pad it with the usual stops."
            )

        names = ", ".join(g["name"] for g in gems)
        system_prompt = (
            "You are Oxomiai, a Northeast Assam travel companion. Write ONE short, warm "
            "sentence introducing a list of hidden-gem spots. Do not list the spots "
            "yourself, do not invent any, do not add detail beyond framing. Under 25 words."
        )
        user_message = f"Traveller asked: {query}\nSpots being shown: {names}"
        try:
            return self.llm.invoke(system_prompt, user_message, max_tokens=80, temperature=0.6).strip()
        except Exception as e:
            print(f"Gems intro error: {e}")
            return "Beyond the guidebook stops — here's what most travellers miss:"

    def intro_local_expert(self, query: str, expert: Dict[str, Any]) -> str:
        """One-line intro for a local-expert card. Never invents guide details."""
        if not expert:
            return (
                "I couldn't find an available local guide for that area right now. "
                "Try again a little later, or ask me to widen the search."
            )
        system_prompt = (
            "You are Oxomiai, a Northeast Assam travel companion. Write ONE short, warm "
            "sentence saying you're connecting the traveller with a verified local guide. "
            "Do not state the guide's name, experience, or availability — a card below does "
            "that. Under 22 words."
        )
        try:
            return self.llm.invoke(system_prompt, f"Traveller asked: {query}",
                                   max_tokens=70, temperature=0.6).strip()
        except Exception as e:
            print(f"Expert intro error: {e}")
            return "Of course — here's a verified local guide who can help, live."

    def handle_no_match(self, query: str) -> str:
        """Handle case where query doesn't match KB."""
        return (
            "I didn't find matching information in my knowledge base for that query. "
            "This could mean it's about a place outside my coverage area, or something very specific that needs local expertise. "
            "Would you like to know about popular places in Assam, or can you rephrase your question?"
        )

    def handle_escalation(self, query: str, reason: str) -> str:
        """Handle expert escalation."""
        return (
            f"This question needs local expertise: {reason}\n\n"
            "I'm connecting you with a local expert who can help with current conditions, bookings, and hyperlocal details. "
            "Please hold while they're contacted."
        )
