import os
import requests
from typing import Dict, Any, Optional
from datetime import datetime


class WeatherService:
    """Fetch weather data from OpenWeatherMap free API."""

    def __init__(self):
        self.api_key = os.getenv("OPENWEATHER_API_KEY")
        if not self.api_key:
            print("Warning: OPENWEATHER_API_KEY not set")
        self.base_url = "https://api.openweathermap.org/data/2.5"

    def get_weather(self, latitude: float, longitude: float, place_name: str = "") -> Optional[Dict[str, Any]]:
        """
        Fetch current weather and 3-day forecast for a location.

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
                "timestamp": "2024-09-05T18:30:00Z"
            }
        """
        if not self.api_key:
            return self._mock_weather(place_name, latitude, longitude)

        try:
            # Current weather
            current_url = f"{self.base_url}/weather?lat={latitude}&lon={longitude}&appid={self.api_key}&units=metric"
            current_resp = requests.get(current_url, timeout=5)
            current_resp.raise_for_status()
            current_data = current_resp.json()

            # Forecast (using forecast endpoint for free tier data)
            forecast_url = f"{self.base_url}/forecast?lat={latitude}&lon={longitude}&appid={self.api_key}&units=metric"
            forecast_resp = requests.get(forecast_url, timeout=5)
            forecast_resp.raise_for_status()
            forecast_data = forecast_resp.json()

            # Parse forecast into daily summaries
            forecast_3days = self._parse_forecast(forecast_data)

            return {
                "location": place_name or current_data.get("name", "Unknown"),
                "lat": latitude,
                "lon": longitude,
                "current": {
                    "temp_c": current_data["main"]["temp"],
                    "condition": current_data["weather"][0]["main"],
                    "humidity": current_data["main"]["humidity"],
                    "wind_speed_kmh": current_data["wind"]["speed"] * 3.6
                },
                "forecast_3days": forecast_3days,
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }

        except Exception as e:
            print(f"Weather API error for {place_name}: {e}")
            return self._mock_weather(place_name, latitude, longitude)

    def _parse_forecast(self, forecast_data: Dict[str, Any]) -> list:
        """Parse 5-day forecast API into 3-day daily summaries."""
        days = {}
        for item in forecast_data.get("list", []):
            date = item["dt_txt"].split()[0]
            if date not in days:
                days[date] = []
            days[date].append(item)

        forecast_3days = []
        for date in sorted(days.keys())[:3]:
            entries = days[date]
            temps = [e["main"]["temp"] for e in entries]
            conditions = [e["weather"][0]["main"] for e in entries]
            most_common_condition = max(set(conditions), key=conditions.count)

            forecast_3days.append({
                "date": date,
                "high_c": max(temps),
                "low_c": min(temps),
                "condition": most_common_condition
            })

        return forecast_3days

    def _mock_weather(self, place_name: str, latitude: float, longitude: float) -> Dict[str, Any]:
        """Return mock weather for POC testing (when API key not available)."""
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
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "_note": "Mock data (API key not configured)"
        }
