from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime


class QueryRequest(BaseModel):
    """Traveler query to the bot."""
    query: str
    session_id: Optional[str] = None
    context_history: Optional[List[Dict[str, str]]] = []


class PlaceInfo(BaseModel):
    """Knowledge base place entry."""
    site_id: str
    site_name: str
    site_type: str  # temple, wildlife, cultural, wetland
    district: str
    address: str
    latitude: float
    longitude: float
    short_description: str
    historical_significance: Optional[str]
    unique_attractions: List[str]
    visiting_hours: str
    average_time_spent_hours: float
    best_seasons: List[str]
    avoid_seasons: List[str]
    entry_fee_details: str
    entry_required: bool
    food_options: str
    nearby_hotels: List[str]
    nearby_restaurants: List[str]
    targeted_festivals: List[str]
    verification_status: str
    last_verified_date: str


class WeatherData(BaseModel):
    """Weather data from external API."""
    location: str
    temperature_c: float
    condition: str
    humidity: int
    wind_speed_kmh: float
    forecast_next_3days: List[Dict[str, Any]]
    timestamp: str


class QueryUnderstanding(BaseModel):
    """Extracted intent and entities from query."""
    intent: str  # place_info | weather | itinerary | expert_needed | chitchat
    entities: Dict[str, Any]
    confidence: float


class RouteDecision(BaseModel):
    """Routing decision for the query."""
    route: List[str]  # ["KB"] | ["WX"] | ["KB", "WX"] | ["EXP"] | ["REFUSE"]
    reasoning: str
    confidence: float


class HiddenGem(BaseModel):
    """A curated lesser-known spot surfaced by the hidden-gems service."""
    name: str
    near: Optional[str] = None
    category: Optional[str] = None
    short_description: str
    why_hidden: Optional[str] = None
    how_to_reach: Optional[str] = None
    best_time: Optional[str] = None
    tag: str = "Local pick"


class LocalExpert(BaseModel):
    """A verified local guide the traveller can connect with."""
    name: str
    region: str
    specialties: List[str] = []
    languages: List[str] = []
    years_experience: int = 0
    bio: Optional[str] = None
    availability_label: str = "By appointment"
    avg_response_minutes: Optional[int] = None
    session_modes: List[str] = []
    photo_emoji: Optional[str] = None
    verification_status: str = "verified"


class BotResponse(BaseModel):
    """Final response from the bot."""
    answer: str
    sources: Dict[str, Any]  # which KB entries, weather data, etc. were used
    route_taken: str
    requires_expert_escalation: bool
    confidence: float
    session_id: str
    timestamp: str
    # Populated only for the differentiator routes. The traveller acts on this
    # structured data directly — it is never paraphrased by the LLM.
    hidden_gems: Optional[List[HiddenGem]] = None
    local_expert: Optional[LocalExpert] = None
