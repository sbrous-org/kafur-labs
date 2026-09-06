import os
import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import Config
from models.schemas import QueryRequest, BotResponse
from services.knowledge_base import KnowledgeBase
from services.router import QueryRouter
from services.weather import WeatherService
from services.synthesis import AnswerSynthesis
from services.recommendations import HiddenGems
from services.experts import ExpertDirectory
from services.llm_provider import create_llm_provider

app = FastAPI(
    title="Oxomiai — Assam Travel Bot",
    description=(
        "POC: structured query-answering companion for Northeast Assam. Routes to a curated "
        "knowledge base, live weather, curated hidden gems, a local-expert directory, or human "
        "escalation. See ARCHITECTURE.md for the target microservices design."
    ),
    version="0.2.0"
)

# CORS for UI frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Validate and load configuration
try:
    Config.validate()
except ValueError as e:
    print(f"❌ Configuration error: {e}")
    raise

# Initialize LLM provider
llm_config = Config.get_llm_config()
llm_provider = create_llm_provider(llm_config)
print(f"✓ Using LLM: {Config.LLM_PROVIDER.upper()}")

# Initialize services
# KB path: in Docker, mounted at /app/knowledge_base; locally, at ../knowledge_base
kb_dir = Path(__file__).parent.parent / "knowledge_base"
knowledge_base = KnowledgeBase(str(kb_dir / "places.jsonl"))
hidden_gems = HiddenGems(str(kb_dir / "hidden_gems.jsonl"))
expert_directory = ExpertDirectory(str(kb_dir / "local_experts.jsonl"))
router = QueryRouter(llm_provider=llm_provider)
weather_service = WeatherService()
synthesis = AnswerSynthesis(llm_provider=llm_provider)

# Session store (POC: in-memory, not persistent)
sessions = {}


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "ok",
        "service": "oxomiai-assam-travel-bot",
        "kb_places": len(knowledge_base.places),
        "hidden_gems": len(hidden_gems.gems),
        "local_experts": len(expert_directory.experts),
    }


@app.get("/kb/hidden-gems")
async def get_hidden_gems():
    """List all curated hidden gems."""
    gems = hidden_gems.get_all()
    return {"total": len(gems), "hidden_gems": gems}


@app.get("/experts")
async def get_experts():
    """List all local experts in the directory."""
    experts = expert_directory.get_all()
    return {"total": len(experts), "experts": experts}


@app.get("/kb/places")
async def get_all_places():
    """List all places in the knowledge base."""
    places = knowledge_base.get_all()
    return {
        "total": len(places),
        "places": [
            {
                "site_id": p["site_id"],
                "site_name": p["site_name"],
                "site_type": p["site_type"],
                "district": p["district"],
                "latitude": p["latitude"],
                "longitude": p["longitude"]
            }
            for p in places
        ]
    }


@app.post("/query")
async def answer_query(request: QueryRequest) -> BotResponse:
    """
    Main bot endpoint: answer a traveler query.

    Pipeline:
    1. Understand intent & extract entities
    2. Route to appropriate source(s)
    3. Retrieve from KB / weather / expert
    4. Synthesize natural-language answer
    """
    session_id = request.session_id or str(uuid.uuid4())
    query = request.query.strip()

    if not query:
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    # Load session history
    session_history = sessions.get(session_id, {"messages": []})

    try:
        # Step 1: Route the query
        routing_result = router.route(query, session_history["messages"][-3:] if session_history["messages"] else None)
        intent = routing_result.get("intent", "unknown")
        route = routing_result.get("route", ["REFUSE"])
        entities = routing_result.get("entities", {})

        # Step 2: Retrieve sources based on route
        kb_results = []
        weather_data = None
        gem_results = []
        matched_expert = None
        sources_used = {}

        region = entities.get("region") or entities.get("district") or ""
        interests = entities.get("interests") or []
        if isinstance(interests, str):
            interests = [interests]
        if entities.get("activity"):
            interests = interests + [entities["activity"]]

        if "GEMS" in route:
            gem_results = hidden_gems.retrieve(query, region=region or None, top_k=3)
            if gem_results:
                sources_used["hidden_gems"] = [
                    {"name": g["name"], "near": g.get("near"), "score": g.get("match_score", 0)}
                    for g in gem_results
                ]

        if "EXPERT" in route:
            matched_expert = expert_directory.match(region=region or None, interests=interests)
            if matched_expert:
                sources_used["local_expert"] = {
                    "name": matched_expert["name"],
                    "region": matched_expert["region"],
                }

        if "KB" in route:
            filters = {}
            if "place_names" in entities and entities["place_names"]:
                # First try direct KB search
                kb_results = knowledge_base.retrieve(
                    query,
                    top_k=3,
                    filters={"district": entities.get("district", "")} if entities.get("district") else None
                )
            else:
                kb_results = knowledge_base.retrieve(query, top_k=3, filters=None)

            if kb_results:
                sources_used["kb_results"] = [
                    {
                        "site_id": p["site_id"],
                        "site_name": p["site_name"],
                        "score": p.get("retrieval_score", 0)
                    }
                    for p in kb_results
                ]

        if "WX" in route:
            if kb_results and kb_results[0]:
                # Prefer coordinates from the matched KB place.
                place = kb_results[0]
                lat, lon, loc_name = place["latitude"], place["longitude"], place["site_name"]
            else:
                # Pure weather query for a place not in the KB — geocode the
                # named place / region (falls back to Guwahati).
                target = region or (entities.get("place_names") or ["Guwahati"])[0]
                geo = weather_service.geocode(target) or weather_service.geocode("Guwahati")
                if geo:
                    lat, lon, loc_name = geo["latitude"], geo["longitude"], geo["name"]
                else:
                    lat = lon = loc_name = None

            if lat is not None:
                weather_data = weather_service.get_weather(
                    latitude=lat, longitude=lon, place_name=loc_name
                )
                if weather_data:
                    sources_used["weather_location"] = weather_data["location"]

        # Step 3: Synthesize answer
        gems_payload = None
        expert_payload = None

        if "REFUSE" in route:
            answer = synthesis.handle_no_match(query)
        elif "GEMS" in route:
            answer = synthesis.intro_hidden_gems(query, gem_results)
            gems_payload = [
                {
                    "name": g["name"],
                    "near": g.get("near"),
                    "category": g.get("category"),
                    "short_description": g["short_description"],
                    "why_hidden": g.get("why_hidden"),
                    "how_to_reach": g.get("how_to_reach"),
                    "best_time": g.get("best_time"),
                    "tag": g.get("tag", "Local pick"),
                }
                for g in gem_results
            ] or None
        elif "EXPERT" in route:
            answer = synthesis.intro_local_expert(query, matched_expert)
            if matched_expert:
                expert_payload = {
                    "name": matched_expert["name"],
                    "region": matched_expert["region"],
                    "specialties": matched_expert.get("specialties", []),
                    "languages": matched_expert.get("languages", []),
                    "years_experience": matched_expert.get("years_experience", 0),
                    "bio": matched_expert.get("bio"),
                    "availability_label": matched_expert.get("availability_label", "By appointment"),
                    "avg_response_minutes": matched_expert.get("avg_response_minutes"),
                    "session_modes": matched_expert.get("session_modes", []),
                    "photo_emoji": matched_expert.get("photo_emoji"),
                    "verification_status": matched_expert.get("verification_status", "verified"),
                }
        elif "EXP" in route:
            answer = synthesis.handle_escalation(
                query,
                "Hyperlocal expertise needed for current bookings and conditions"
            )
        else:
            answer = synthesis.synthesize(
                query=query,
                route=route,
                kb_results=kb_results,
                weather_data=weather_data,
                context_history=session_history.get("messages", [])
            )

        # Build response
        response = BotResponse(
            answer=answer,
            sources=sources_used,
            route_taken=", ".join(route),
            requires_expert_escalation="EXP" in route,
            confidence=routing_result.get("confidence", 0.5),
            session_id=session_id,
            timestamp=datetime.utcnow().isoformat() + "Z",
            hidden_gems=gems_payload,
            local_expert=expert_payload,
        )

        # Store in session history
        session_history["messages"].append({
            "query": query,
            "answer": answer,
            "route": route,
            "intent": intent,
            "timestamp": response.timestamp
        })
        sessions[session_id] = session_history

        return response

    except Exception as e:
        print(f"Error processing query: {e}")
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@app.get("/session/{session_id}")
async def get_session(session_id: str):
    """Retrieve session history."""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    return sessions[session_id]


@app.delete("/session/{session_id}")
async def delete_session(session_id: str):
    """Clear session history."""
    if session_id in sessions:
        del sessions[session_id]
    return {"status": "ok", "session_id": session_id}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=os.getenv("ENV", "production") == "development"
    )
