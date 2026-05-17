"""In-memory track store + async broadcast to connected clients."""

from __future__ import annotations

import asyncio
import time

from geo import angle_diff, bearing_deg, geocode, haversine_km
from simulation import Target, spawn_from_event


class TrackStore:
    def __init__(self):
        self.targets: dict[str, Target] = {}
        self._subs: set[asyncio.Queue] = set()
        self._lock = asyncio.Lock()

    # -- subscriptions -----------------------------------------------------
    def subscribe(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue(maxsize=64)
        self._subs.add(q)
        return q

    def unsubscribe(self, q: asyncio.Queue):
        self._subs.discard(q)

    async def _broadcast(self, msg: dict):
        for q in list(self._subs):
            try:
                q.put_nowait(msg)
            except asyncio.QueueFull:
                pass

    # -- ingestion ---------------------------------------------------------
    async def apply_events(self, events: list[dict]):
        """Apply parsed Gemini events: spawn new or update existing tracks."""
        async with self._lock:
            for ev in events or []:
                action = (ev.get("action") or "spawn").lower()
                if action in ("update", "redirect", "course_change"):
                    self._update_existing(ev)
                else:
                    t = spawn_from_event(ev)
                    if t:
                        self.targets[t.id] = t
        await self._broadcast({"type": "snapshot", "targets": self.snapshot()})

    def _update_existing(self, ev: dict):
        """Find the closest matching live target and redirect it."""
        ttype = ev.get("type")
        ref = geocode(ev.get("near") or ev.get("origin") or "")
        candidates = [t for t in self.targets.values()
                      if t.alive and (ttype is None or t.type == ttype)]
        if not candidates:
            t = spawn_from_event(ev)
            if t:
                self.targets[t.id] = t
            return
        if ref:
            candidates.sort(key=lambda t: haversine_km((t.lat, t.lon), ref))
        target = candidates[0]
        dest = geocode(ev.get("destination") or "")
        if dest:
            target.set_destination(dest)
        elif ev.get("heading") is not None:
            target.set_heading(float(ev["heading"]))

    # -- simulation loop ---------------------------------------------------
    async def run(self, tick: float):
        last = time.time()
        while True:
            await asyncio.sleep(tick)
            now = time.time()
            dt = now - last
            last = now
            async with self._lock:
                for t in list(self.targets.values()):
                    t.step(dt)
                    # Drop very old tracks (30 min without updates).
                    if now - t.updated > 1800:
                        t.alive = False
                self.targets = {i: t for i, t in self.targets.items()
                                if t.alive or now - t.updated < 120}
            await self._broadcast({"type": "snapshot", "targets": self.snapshot()})

    # -- queries -----------------------------------------------------------
    def snapshot(self) -> list[dict]:
        return [t.to_dict() for t in self.targets.values() if t.alive]

    def route(self, target_id: str) -> dict | None:
        t = self.targets.get(target_id)
        return t.to_dict(full_history=True) if t else None


store = TrackStore()
