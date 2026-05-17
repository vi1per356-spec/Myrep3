"""Geo helpers: city geocoding, distance, bearing, and great-circle stepping."""

from __future__ import annotations

import math

# Frequently mentioned Ukrainian places (lat, lon). Extend freely.
CITIES: dict[str, tuple[float, float]] = {
    "kyiv": (50.4501, 30.5234),
    "kiev": (50.4501, 30.5234),
    "kharkiv": (49.9935, 36.2304),
    "odesa": (46.4825, 30.7233),
    "odessa": (46.4825, 30.7233),
    "dnipro": (48.4647, 35.0462),
    "lviv": (49.8397, 24.0297),
    "zaporizhzhia": (47.8388, 35.1396),
    "zaporizhia": (47.8388, 35.1396),
    "kryvyi rih": (47.9105, 33.3918),
    "mykolaiv": (46.9750, 31.9946),
    "vinnytsia": (49.2331, 28.4682),
    "poltava": (49.5883, 34.5514),
    "chernihiv": (51.4982, 31.2893),
    "cherkasy": (49.4444, 32.0598),
    "sumy": (50.9077, 34.7981),
    "zhytomyr": (50.2547, 28.6587),
    "rivne": (50.6199, 26.2516),
    "ivano-frankivsk": (48.9226, 24.7111),
    "ternopil": (49.5535, 25.5948),
    "lutsk": (50.7472, 25.3254),
    "uzhhorod": (48.6208, 22.2879),
    "khmelnytskyi": (49.4229, 26.9871),
    "chernivtsi": (48.2917, 25.9352),
    "kropyvnytskyi": (48.5079, 32.2623),
    "kherson": (46.6354, 32.6169),
    "boryspil": (50.3527, 30.9550),
    "bila tserkva": (49.7950, 30.1310),
    "kremenchuk": (49.0631, 33.4170),
    "kamianske": (48.5110, 34.6021),
    "nizhyn": (51.0480, 31.8860),
    "okhtyrka": (50.3100, 34.8990),
    "starokostiantyniv": (49.7570, 27.2030),
    "pavlohrad": (48.5350, 35.8700),
    "kremenchug": (49.0631, 33.4170),
    "fastiv": (50.0780, 29.9170),
    "izmail": (45.3510, 28.8360),
    "konotop": (51.2370, 33.2030),
    "shostka": (51.8730, 33.4790),
    "kropyvnytsky": (48.5079, 32.2623),
}

EARTH_R_KM = 6371.0088


def geocode(name: str) -> tuple[float, float] | None:
    """Best-effort name -> (lat, lon). Case/space tolerant."""
    if not name:
        return None
    key = name.strip().lower().replace("’", "'").replace("`", "'")
    if key in CITIES:
        return CITIES[key]
    for city, coord in CITIES.items():
        if city in key or key in city:
            return coord
    return None


def haversine_km(a: tuple[float, float], b: tuple[float, float]) -> float:
    lat1, lon1 = map(math.radians, a)
    lat2, lon2 = map(math.radians, b)
    dlat, dlon = lat2 - lat1, lon2 - lon1
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 2 * EARTH_R_KM * math.asin(math.sqrt(h))


def bearing_deg(a: tuple[float, float], b: tuple[float, float]) -> float:
    """Initial bearing from point a to point b, degrees [0,360)."""
    lat1, lon1 = map(math.radians, a)
    lat2, lon2 = map(math.radians, b)
    dlon = lon2 - lon1
    x = math.sin(dlon) * math.cos(lat2)
    y = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dlon)
    return (math.degrees(math.atan2(x, y)) + 360.0) % 360.0


def destination(point: tuple[float, float], bearing: float, dist_km: float) -> tuple[float, float]:
    """Point reached by travelling dist_km along `bearing` from `point`."""
    lat1, lon1 = math.radians(point[0]), math.radians(point[1])
    brng = math.radians(bearing)
    dr = dist_km / EARTH_R_KM
    lat2 = math.asin(math.sin(lat1) * math.cos(dr) + math.cos(lat1) * math.sin(dr) * math.cos(brng))
    lon2 = lon1 + math.atan2(
        math.sin(brng) * math.sin(dr) * math.cos(lat1),
        math.cos(dr) - math.sin(lat1) * math.sin(lat2),
    )
    return (math.degrees(lat2), (math.degrees(lon2) + 540) % 360 - 180)


def angle_diff(a: float, b: float) -> float:
    """Signed smallest difference b-a in degrees, range (-180,180]."""
    d = (b - a + 180.0) % 360.0 - 180.0
    return d + 360.0 if d <= -180.0 else d
