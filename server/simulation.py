"""Target physics: spawn, move along great circle, smooth (rounded) turns,
continue straight when no new info, and full route history for tap-to-trace.
"""

from __future__ import annotations

import time
import uuid

from geo import angle_diff, bearing_deg, destination, geocode
from threats import spec


class Target:
    def __init__(self, threat_type: str, lat: float, lon: float,
                 heading: float, label: str = ""):
        self.id = uuid.uuid4().hex[:10]
        self.type = threat_type
        s = spec(threat_type)
        self.speed_kmh = float(s["speed_kmh"])
        self.turn_rate = float(s["turn_rate"])
        self.icon = s["icon"]
        self.label = label or s["label"]
        self.lat = lat
        self.lon = lon
        self.heading = heading            # current heading, deg
        self.target_heading = heading     # desired heading (set by updates)
        self.destination: tuple[float, float] | None = None
        self.alive = True
        self.created = time.time()
        self.updated = time.time()
        # Route history: list of [lat, lon, t] for tap-to-trace.
        self.history: list[list[float]] = [[lat, lon, self.created]]

    # -- control -----------------------------------------------------------
    def set_destination(self, dest: tuple[float, float]):
        self.destination = dest
        self.target_heading = bearing_deg((self.lat, self.lon), dest)
        self.updated = time.time()

    def set_heading(self, heading: float):
        self.destination = None
        self.target_heading = heading % 360.0
        self.updated = time.time()

    # -- step --------------------------------------------------------------
    def step(self, dt: float):
        """Advance the target by dt seconds."""
        if not self.alive:
            return
        # Re-aim at a moving destination so the path stays correct.
        if self.destination:
            self.target_heading = bearing_deg((self.lat, self.lon), self.destination)

        # Smooth rounded turn toward target_heading.
        diff = angle_diff(self.heading, self.target_heading)
        max_turn = self.turn_rate * dt
        if abs(diff) <= max_turn:
            self.heading = self.target_heading
        else:
            self.heading = (self.heading + max_turn * (1 if diff > 0 else -1)) % 360.0

        # Advance along current heading.
        dist_km = self.speed_kmh * (dt / 3600.0)
        self.lat, self.lon = destination((self.lat, self.lon), self.heading, dist_km)

        # Reached destination -> keep flying straight (no further info case).
        if self.destination:
            from geo import haversine_km
            if haversine_km((self.lat, self.lon), self.destination) < dist_km * 1.2:
                self.destination = None  # continue straight on current heading

        now = time.time()
        last = self.history[-1]
        if now - last[2] >= 5.0:  # sample route every ~5s
            self.history.append([self.lat, self.lon, now])
            if len(self.history) > 2000:
                self.history = self.history[-2000:]

    def to_dict(self, full_history: bool = False) -> dict:
        d = {
            "id": self.id,
            "type": self.type,
            "icon": self.icon,
            "label": self.label,
            "lat": round(self.lat, 5),
            "lon": round(self.lon, 5),
            "heading": round(self.heading, 1),
            "speed_kmh": self.speed_kmh,
            "alive": self.alive,
            "updated": self.updated,
        }
        if full_history:
            d["history"] = self.history
        return d


def spawn_from_event(ev: dict) -> Target | None:
    """Build a Target from a parsed Gemini event dict.

    Expected keys (any may be missing):
      type, origin, destination, heading, label, near
    """
    ttype = ev.get("type") or "shahed"
    origin = ev.get("origin")
    dest = ev.get("destination")
    near = ev.get("near")

    start = geocode(origin) if origin else None
    if start is None and near:
        start = geocode(near)
    if start is None:
        return None  # cannot place without a known origin

    dest_c = geocode(dest) if dest else None
    if dest_c is not None:
        hdg = bearing_deg(start, dest_c)
    else:
        hdg = float(ev.get("heading", 0.0) or 0.0)

    t = Target(ttype, start[0], start[1], hdg, label=ev.get("label", ""))
    if dest_c is not None:
        t.set_destination(dest_c)
    return t
