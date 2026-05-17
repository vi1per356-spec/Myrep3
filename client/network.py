"""Thin HTTP/WebSocket client for the Termux server."""

from __future__ import annotations

import json
import threading

import requests
import websocket  # websocket-client


class Api:
    def __init__(self, base_url: str):
        self.base = base_url.rstrip("/")
        self.token: str | None = None
        self._ws: websocket.WebSocketApp | None = None

    # -- auth --------------------------------------------------------------
    def login(self, username: str, password: str) -> bool:
        r = requests.post(f"{self.base}/login",
                          json={"username": username, "password": password},
                          timeout=10)
        if r.status_code == 200:
            self.token = r.json()["token"]
            return True
        return False

    def _headers(self):
        return {"Authorization": f"Bearer {self.token}"}

    # -- rest --------------------------------------------------------------
    def get_config(self) -> dict:
        return requests.get(f"{self.base}/config", timeout=10).json()

    def route(self, target_id: str) -> dict:
        return requests.get(f"{self.base}/route/{target_id}",
                            headers=self._headers(), timeout=10).json()

    def upload_route(self, path: str) -> dict:
        with open(path, "rb") as f:
            return requests.post(f"{self.base}/training/route",
                                 headers=self._headers(),
                                 files={"file": f}, timeout=60).json()

    def upload_situation(self, path: str) -> dict:
        with open(path, "rb") as f:
            return requests.post(f"{self.base}/training/situation",
                                 headers=self._headers(),
                                 files={"file": f}, timeout=60).json()

    def icon_url(self, name: str) -> str:
        return f"{self.base}/icons/{name}.png"

    # -- websocket ---------------------------------------------------------
    def stream(self, on_snapshot):
        url = self.base.replace("http", "ws", 1) + f"/ws?token={self.token}"

        def _on_message(_ws, message):
            try:
                msg = json.loads(message)
                if msg.get("type") == "snapshot":
                    on_snapshot(msg.get("targets", []))
            except Exception:
                pass

        self._ws = websocket.WebSocketApp(url, on_message=_on_message)
        t = threading.Thread(target=self._ws.run_forever, daemon=True)
        t.start()

    def close(self):
        if self._ws:
            self._ws.close()
