from dataclasses import dataclass

import httpx

from app.config import settings


@dataclass(frozen=True)
class VerifiedLocation:
    display_name: str
    latitude: float
    longitude: float


async def verify_location(query: str) -> VerifiedLocation | None:
    if not settings.location_validation_enabled:
        return None

    try:
        async with httpx.AsyncClient(
            timeout=5,
            headers={"User-Agent": "LandwiseAI/1.0 location verification"},
        ) as client:
            response = await client.get(
                "https://nominatim.openstreetmap.org/search",
                params={"q": query, "format": "jsonv2", "limit": 1},
            )
            response.raise_for_status()
            places = response.json()
    except (httpx.HTTPError, ValueError):
        raise RuntimeError("Location verification is temporarily unavailable.")

    if not places:
        return None

    place = places[0]
    return VerifiedLocation(
        display_name=str(place["display_name"]),
        latitude=float(place["lat"]),
        longitude=float(place["lon"]),
    )
