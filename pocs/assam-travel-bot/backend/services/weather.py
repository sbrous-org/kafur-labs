import requests
from typing import Dict, Any, Optional
from datetime import datetime


class WeatherService:
    """Fetch weather data from Open-Meteo (free, no API key needed)."""

    def __init__(self):
        self.base_url = "https://api.open-meteo.com/v1"
        self.geocoding_url = "https://geocoding-api.open-meteo.com/v1"

    def geocode(self, place_name: str) -> Optional[Dict[str, Any]]:
        """
        Resolve a place name to coordinates via Open-Meteo's free geocoding API.
        Used when a weather query names a place that isn't in the knowledge base
        (so we have no coordinates from KB metadata). Biased to Assam / India.
        """
        if not place_name:
            return None
        try:
            resp = requests.get(
                f"{self.geocoding_url}/search",
                params={"name": place_name, "count": 5, "language": "en"},
                timeout=5,
            )
            resp.raise_for_status()
            results = resp.json().get("results") or []
            if not results:
                return None
            # Prefer an Indian (ideally Assam) match, else the first result.
            pick = next(
                (r for r in results if r.get("admin1", "").lower() == "assam"),
                next((r for r in results if r.get("country_code") == "IN"), results[0]),
            )
            return {
                "name": pick.get("name", place_name),
                "latitude": pick["latitude"],
                "longitude": pick["longitude"],
            }
        except Exception as e:
            print(f"Geocoding error for {place_name!r}: {e}")
            return None

    def get_weather(self, latitude: float, longitude: float, place_name: str = "") -> Optional[Dict[str, Any]]:
        """
        Fetch current weather, forecast, and sunrise/sunset for a location.

        Uses Open-Meteo free API (no authentication needed).

        Returns:
            {
                "location": "Place name",
                "lat": 26.166,
                "lon": 91.705,
                "current": {
                    "temp_c": 28,
                    "condition": "Clear",
                    "humidity": 65,
                    "wind_speed_kmh": 12
                },
                "forecast_3days": [
                    {"date": "2024-09-06", "high_c": 32, "low_c": 25, "condition": "Cloudy"},
                    ...
                ],
                "sunrise": "05:45",
                "sunset": "17:30",
                "timestamp": "2024-09-05T18:30:00Z"
            }
        """
        try:
            # Current weather + 3-day forecast + daily sunrise/sunset
            weather_url = f"{self.base_url}/forecast?latitude={latitude}&longitude={longitude}&current=temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m&daily=weather_code,temperature_2m_max,temperature_2m_min,sunrise,sunset&timezone=auto"

            weather_resp = requests.get(weather_url, timeout=5)
            weather_resp.raise_for_status()
            weather_data = weather_resp.json()

            # Parse current weather
            current = weather_data.get("current", {})
            daily = weather_data.get("daily", {})

            current_condition = self._get_condition_text(current.get("weather_code", 0))

            # Extract sunrise/sunset from today
            sunrise = None
            sunset = None
            if daily.get("sunrise"):
                sunrise = daily["sunrise"][0].split("T")[1]  # Extract time
            if daily.get("sunset"):
                sunset = daily["sunset"][0].split("T")[1]

            # Parse 3-day forecast
            forecast_3days = []
            dates = daily.get("time", [])
            temps_max = daily.get("temperature_2m_max", [])
            temps_min = daily.get("temperature_2m_min", [])
            codes = daily.get("weather_code", [])

            for i in range(min(3, len(dates))):
                forecast_3days.append({
                    "date": dates[i],
                    "high_c": int(temps_max[i]),
                    "low_c": int(temps_min[i]),
                    "condition": self._get_condition_text(codes[i])
                })

            return {
                "location": place_name or f"Location ({latitude}, {longitude})",
                "lat": latitude,
                "lon": longitude,
                "current": {
                    "temp_c": current.get("temperature_2m", 0),
                    "condition": current_condition,
                    "humidity": current.get("relative_humidity_2m", 0),
                    "wind_speed_kmh": current.get("wind_speed_10m", 0)
                },
                "forecast_3days": forecast_3days,
                "sunrise": sunrise,
                "sunset": sunset,
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }

        except Exception as e:
            print(f"Weather API error for {place_name}: {e}")
            return self._mock_weather(place_name, latitude, longitude)

    def _get_condition_text(self, code: int) -> str:
        """Convert WMO weather code to human-readable text."""
        conditions = {
            0: "Clear",
            1: "Mostly Clear",
            2: "Partly Cloudy",
            3: "Overcast",
            45: "Foggy",
            48: "Foggy",
            51: "Light Drizzle",
            53: "Moderate Drizzle",
            55: "Heavy Drizzle",
            61: "Slight Rain",
            63: "Moderate Rain",
            65: "Heavy Rain",
            71: "Slight Snow",
            73: "Moderate Snow",
            75: "Heavy Snow",
            77: "Snow Grains",
            80: "Slight Showers",
            81: "Moderate Showers",
            82: "Heavy Showers",
            85: "Slight Snow Showers",
            86: "Heavy Snow Showers",
            95: "Thunderstorm",
            96: "Thunderstorm with Hail",
            99: "Thunderstorm with Hail"
        }
        return conditions.get(code, "Unknown")

    def _mock_weather(self, place_name: str, latitude: float, longitude: float) -> Dict[str, Any]:
        """Return mock weather for testing."""
        return {
            "location": place_name or f"Location ({latitude}, {longitude})",
            "lat": latitude,
            "lon": longitude,
            "current": {
                "temp_c": 28,
                "condition": "Partly Cloudy",
                "humidity": 65,
                "wind_speed_kmh": 12
            },
            "forecast_3days": [
                {"date": "2024-09-06", "high_c": 32, "low_c": 25, "condition": "Sunny"},
                {"date": "2024-09-07", "high_c": 30, "low_c": 24, "condition": "Cloudy"},
                {"date": "2024-09-08", "high_c": 28, "low_c": 22, "condition": "Rainy"}
            ],
            "sunrise": "05:45",
            "sunset": "17:30",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "_note": "Mock data (API error occurred)"
        }
