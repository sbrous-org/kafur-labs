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

from models.schemas import QueryRequest, BotResponse
from services.knowledge_base import KnowledgeBase
from services.router import QueryRouter
from services.weather import WeatherService
from services.synthesis import AnswerSynthesis

app = FastAPI(
    title="Assam Travel Bot",
    description="POC: Structured query-answering bot for Assam travel with KB, weather, and expert escalation.",
    version="0.1.0"
)

# CORS for UI frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
kb_path = Path(__file__).parent.parent.parent / "knowledge_base" / "places.jsonl"
knowledge_base = KnowledgeBase(str(kb_path))
router = QueryRouter()
weather_service = WeatherService()
synthesis = AnswerSynthesis()

# Session store (POC: in-memory, not persistent)
sessions = {}


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "ok",
        "service": "assam-travel-bot",
        "kb_places": len(knowledge_base.places)
    }


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
        sources_used = {}

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
                # Get weather for the top KB result
                place = kb_results[0]
                weather_data = weather_service.get_weather(
                    latitude=place["latitude"],
                    longitude=place["longitude"],
                    place_name=place["site_name"]
                )
                if weather_data:
                    sources_used["weather_location"] = weather_data["location"]

        # Step 3: Synthesize answer
        if "REFUSE" in route:
            answer = synthesis.handle_no_match(query)
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
            timestamp=datetime.utcnow().isoformat() + "Z"
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
