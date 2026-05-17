"""Reference store for the two training buttons.

Button 1 ("routes"): user supplies map screenshots of typical target routes.
Button 2 ("moment"): user supplies a snapshot of how the situation looked at a
past moment.

Both are sent to Gemini, summarised into reusable route hints, and stored on
disk so the parser can use them as context to make visualisation more
realistic.
"""

from __future__ import annotations

import json
import os
import time

from gemini_parser import parse_situation_image

DATA_DIR = os.path.join(os.path.dirname(__file__), "training_data")
ROUTES_FILE = os.path.join(DATA_DIR, "routes.json")
MOMENTS_FILE = os.path.join(DATA_DIR, "moments.json")


def _load(path: str) -> list:
    if os.path.exists(path):
        try:
            return json.load(open(path))
        except Exception:
            return []
    return []


def _save(path: str, data: list):
    os.makedirs(DATA_DIR, exist_ok=True)
    json.dump(data, open(path, "w"), ensure_ascii=False, indent=2)


def add_route(image_bytes: bytes) -> dict:
    events = parse_situation_image(
        image_bytes,
        hint="This is a typical ROUTE map. Describe each target's full path "
             "as origin->destination with heading.",
    )
    rec = {"ts": time.time(), "events": events}
    data = _load(ROUTES_FILE)
    data.append(rec)
    _save(ROUTES_FILE, data)
    return rec


def add_moment(image_bytes: bytes) -> dict:
    events = parse_situation_image(
        image_bytes,
        hint="This is a SNAPSHOT of a past moment. For each target give its "
             "current position (near) and heading.",
    )
    rec = {"ts": time.time(), "events": events}
    data = _load(MOMENTS_FILE)
    data.append(rec)
    _save(MOMENTS_FILE, data)
    return rec


def route_hint_text() -> str:
    """Compact context injected into live parsing for realism."""
    routes = _load(ROUTES_FILE)[-10:]
    if not routes:
        return ""
    lines = []
    for r in routes:
        for e in r.get("events", []):
            o, d = e.get("origin"), e.get("destination")
            if o and d:
                lines.append(f"{e.get('type','target')}: {o} -> {d}")
    return ("Known typical routes:\n" + "\n".join(lines)) if lines else ""
