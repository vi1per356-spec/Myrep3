"""Threat catalogue.

Speeds are cruising ground speeds in km/h (open-source approximate values).
`turn_rate` is max heading change in degrees/second used for smooth turns.
`icon` maps to the SVG/PNG asset name.
"""

from __future__ import annotations

THREATS: dict[str, dict] = {
    "shahed": {
        "label": "Shahed-136 / Geran-2",
        "speed_kmh": 180,
        "turn_rate": 4.0,
        "icon": "shahed",
        "keywords": ["shahed", "shaded", "geran", "герань", "шахед", "мопед"],
    },
    "molniya": {
        "label": "Molniya UAV",
        "speed_kmh": 150,
        "turn_rate": 5.0,
        "icon": "molniya",
        "keywords": ["molniya", "молния", "блискавка"],
    },
    "cruise_missile": {
        "label": "Cruise missile (Kh-101 / Kalibr class)",
        "speed_kmh": 800,
        "turn_rate": 3.0,
        "icon": "cruise_missile",
        "keywords": ["cruise", "kh-101", "x-101", "х-101", "kalibr", "калибр",
                     "крылат", "крилат", "ракета"],
    },
    "ballistic_missile": {
        "label": "Ballistic missile (Iskander-M class)",
        "speed_kmh": 4300,
        "turn_rate": 1.0,
        "icon": "ballistic_missile",
        "keywords": ["ballistic", "iskander", "искандер", "балист", "балліст"],
    },
    "recon_uav": {
        "label": "Reconnaissance UAV",
        "speed_kmh": 120,
        "turn_rate": 6.0,
        "icon": "recon_uav",
        "keywords": ["recon", "разведыв", "розвідув", "орлан", "zala", "supercam"],
    },
    "kinzhal": {
        "label": "Kh-47M2 Kinzhal (aeroballistic)",
        "speed_kmh": 12000,
        "turn_rate": 0.8,
        "icon": "kinzhal",
        "keywords": ["kinzhal", "кинжал", "кинджал", "kh-47", "х-47",
                     "aeroballistic", "аэробалист", "аеробаліст"],
    },
    "kab": {
        "label": "Guided aviation bomb (KAB / UMPK)",
        "speed_kmh": 900,
        "turn_rate": 2.0,
        "icon": "kab",
        "keywords": ["kab", "каб", "umpk", "умпк", "guided bomb", "фаб", "управляем"],
    },
}

DEFAULT_TYPE = "shahed"


def classify(text: str) -> str:
    """Pick a threat type from free text using keyword hits."""
    t = (text or "").lower()
    best, score = DEFAULT_TYPE, 0
    for name, spec in THREATS.items():
        s = sum(1 for kw in spec["keywords"] if kw in t)
        if s > score:
            best, score = name, s
    return best


def spec(threat_type: str) -> dict:
    return THREATS.get(threat_type, THREATS[DEFAULT_TYPE])
