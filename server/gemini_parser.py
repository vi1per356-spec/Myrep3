"""Gemini wrapper: turn Telegram text/images into structured threat events.

Output schema (list of events):
[
  {
    "action": "spawn" | "update" | "redirect",
    "type": "shahed|molniya|cruise_missile|ballistic_missile|recon_uav|kinzhal|kab",
    "origin": "city name or null",
    "destination": "city name or null",
    "near": "city the target is currently passing or null",
    "heading": <degrees or null>,
    "label": "short human label"
  }
]
"""

from __future__ import annotations

import json

import config

_model = None


def _get_model():
    global _model
    if _model is not None:
        return _model
    try:
        import google.generativeai as genai
    except ImportError as e:
        raise RuntimeError("google-generativeai not installed") from e
    genai.configure(api_key=config.GEMINI_API_KEY)
    _model = genai.GenerativeModel(config.GEMINI_MODEL)
    return _model


SYSTEM_PROMPT = """You are an air-situation parser for Ukraine. You receive a
Telegram message (Ukrainian/Russian/English) and optionally an image. Extract
every air threat mentioned (Shahed, Molniya, cruise missile, ballistic missile,
reconnaissance UAV, Kinzhal aeroballistic missile, guided aviation bomb / KAB).

If the image is a map showing the current UAV/missile situation, infer each
target's location and heading from it.

Return ONLY valid JSON: a list of event objects with keys:
action (spawn|update|redirect), type (one of:
shahed, molniya, cruise_missile, ballistic_missile, recon_uav, kinzhal, kab),
origin, destination, near (city currently being passed), heading (0-359 or null),
label. Use null for unknown fields. Use Latin-transliterated city names
(e.g. "Chernihiv", "Kyiv", "Zaporizhzhia"). If nothing relevant, return [].
"""


def _coerce_json(text: str) -> list[dict]:
    text = (text or "").strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:]
    try:
        data = json.loads(text)
        if isinstance(data, dict):
            data = [data]
        return [d for d in data if isinstance(d, dict)]
    except Exception:
        return []


def parse_message(text: str, image_bytes: bytes | None = None) -> list[dict]:
    """Parse one Telegram message into events. Returns [] on any failure."""
    try:
        model = _get_model()
    except Exception:
        return []
    parts: list = [SYSTEM_PROMPT, f"\nMESSAGE:\n{text or '(no text)'}"]
    if image_bytes:
        parts.append({"mime_type": "image/jpeg", "data": image_bytes})
    try:
        resp = model.generate_content(parts)
        return _coerce_json(resp.text)
    except Exception:
        return []


def parse_situation_image(image_bytes: bytes, hint: str = "") -> list[dict]:
    """Parse a standalone situation/route screenshot into spawn events."""
    try:
        model = _get_model()
    except Exception:
        return []
    prompt = (SYSTEM_PROMPT +
              "\nThis image is a map of Ukraine showing air targets. "
              "Treat every target as action=spawn. " + (hint or ""))
    try:
        resp = model.generate_content(
            [prompt, {"mime_type": "image/jpeg", "data": image_bytes}]
        )
        return _coerce_json(resp.text)
    except Exception:
        return []
