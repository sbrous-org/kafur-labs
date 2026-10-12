"""Optional live weather (Open-Meteo, free, no key). Failures are silent: the bot just has no weather block."""
import time

import httpx

_cache: dict[tuple, tuple[float, str]] = {}


async def forecast(lat: float, lon: float, name: str) -> str | None:
    key = (round(lat, 1), round(lon, 1))
    hit = _cache.get(key)
    if hit and time.time() - hit[0] < 1800:
        return hit[1]
    try:
        async with httpx.AsyncClient(timeout=3.5) as c:
            r = await c.get("https://api.open-meteo.com/v1/forecast", params={
                "latitude": lat, "longitude": lon, "forecast_days": 7, "timezone": "auto",
                "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum"})
            r.raise_for_status()
            d = r.json()["daily"]
        txt = (f"{name}, next 7 days: highs {min(d['temperature_2m_max']):.0f}-{max(d['temperature_2m_max']):.0f} C, "
               f"lows {min(d['temperature_2m_min']):.0f}-{max(d['temperature_2m_min']):.0f} C, "
               f"total rain {sum(x or 0 for x in d['precipitation_sum']):.0f} mm")
    except Exception:
        return None
    _cache[key] = (time.time(), txt)
    return txt
