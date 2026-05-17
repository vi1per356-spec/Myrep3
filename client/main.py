"""Ukraine Threat Tracker — phone client (Kivy / buildable to APK).

Light default OpenStreetMap map, camera locked to Ukraine, live targets from
the Termux server, zoom-reactive icons, tap-to-trace route, and the two
training upload buttons.
"""

from __future__ import annotations

import os

from kivy.app import App
from kivy.clock import Clock
from kivy.graphics import Color, Line
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.image import AsyncImage
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.screenmanager import Screen, ScreenManager
from kivy.uix.textinput import TextInput

from kivy_garden.mapview import MapLayer, MapMarker, MapView

from network import Api

# Default server URL — change to your phone's LAN IP running Termux.
DEFAULT_SERVER = "http://127.0.0.1:8765"

UA = {"min_lat": 44.0, "max_lat": 52.5, "min_lon": 22.0, "max_lon": 40.3}
UA_CENTER = (49.0, 31.2)
MIN_ZOOM = 6      # Ukraine fills the screen at this zoom
MAX_ZOOM = 13
REF_ZOOM = 7      # icon reference zoom


class TargetMarker(MapMarker):
    """A target icon that shrinks when zoomed in and grows when zoomed out."""

    def __init__(self, target: dict, api: Api, on_tap, **kw):
        self.target = target
        self.api = api
        self._on_tap = on_tap
        super().__init__(lat=target["lat"], lon=target["lon"],
                         source=api.icon_url(target["icon"]), **kw)

    def rescale(self, zoom: int):
        # zoom in (higher zoom) -> smaller icon; zoom out -> bigger.
        factor = max(0.4, min(2.2, (REF_ZOOM / max(zoom, 1)) ** 0.9))
        s = int(48 * factor)
        self.size = (s, s)

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            self._on_tap(self.target)
            return True
        return super().on_touch_down(touch)


class RouteLayer(MapLayer):
    """Draws the tapped target's travelled route as a polyline."""

    def __init__(self, **kw):
        super().__init__(**kw)
        self.points: list[tuple[float, float]] = []

    def set_route(self, history):
        self.points = [(h[0], h[1]) for h in history]
        self.reposition()

    def clear(self):
        self.points = []
        self.reposition()

    def reposition(self, *a):
        self.canvas.clear()
        if len(self.points) < 2:
            return
        mv = self.parent
        with self.canvas:
            Color(0.85, 0.18, 0.18, 0.9)
            pts = []
            for lat, lon in self.points:
                x, y = mv.get_window_xy_from(lat, lon, mv.zoom)
                pts += [x, y]
            Line(points=pts, width=2)


class UkraineMapView(MapView):
    """MapView clamped to Ukraine's bounding box and zoom range."""

    def on_map_relocated(self, zoom, coord):
        super().on_map_relocated(zoom, coord)
        Clock.schedule_once(lambda *_: self._clamp(), 0)

    def _clamp(self):
        changed = False
        z = max(MIN_ZOOM, min(MAX_ZOOM, self.zoom))
        if z != self.zoom:
            self.zoom = z
            changed = True
        lat = max(UA["min_lat"], min(UA["max_lat"], self.lat))
        lon = max(UA["min_lon"], min(UA["max_lon"], self.lon))
        if abs(lat - self.lat) > 1e-6 or abs(lon - self.lon) > 1e-6:
            self.center_on(lat, lon)
            changed = True
        return changed


class LoginScreen(Screen):
    def __init__(self, app, **kw):
        super().__init__(**kw)
        self.app = app
        root = BoxLayout(orientation="vertical", padding=24, spacing=12)
        root.add_widget(Label(text="Ukraine Threat Tracker",
                              font_size="22sp", size_hint_y=0.3))
        self.server = TextInput(text=DEFAULT_SERVER, multiline=False,
                                hint_text="Server URL")
        self.user = TextInput(text="admin", multiline=False,
                              hint_text="Username")
        self.pwd = TextInput(text="", password=True, multiline=False,
                             hint_text="Password")
        self.msg = Label(text="", color=(1, 0.4, 0.4, 1))
        for w in (self.server, self.user, self.pwd):
            w.size_hint_y = None
            w.height = "44dp"
            root.add_widget(w)
        btn = Button(text="Connect", size_hint_y=None, height="48dp")
        btn.bind(on_release=self._connect)
        root.add_widget(btn)
        root.add_widget(self.msg)
        self.add_widget(root)

    def _connect(self, *_):
        self.app.api = Api(self.server.text.strip())
        try:
            ok = self.app.api.login(self.user.text.strip(), self.pwd.text)
        except Exception as e:
            self.msg.text = f"Connection error: {e}"
            return
        if not ok:
            self.msg.text = "Invalid credentials"
            return
        self.app.sm.current = "map"
        self.app.start_stream()


class MapScreen(Screen):
    def __init__(self, app, **kw):
        super().__init__(**kw)
        self.app = app
        self.markers: dict[str, TargetMarker] = {}
        root = BoxLayout(orientation="vertical")
        self.map = UkraineMapView(zoom=MIN_ZOOM,
                                  lat=UA_CENTER[0], lon=UA_CENTER[1])
        self.route_layer = RouteLayer()
        self.map.add_layer(self.route_layer)
        root.add_widget(self.map)

        bar = BoxLayout(size_hint_y=None, height="48dp")
        b1 = Button(text="Upload route")
        b2 = Button(text="Upload moment")
        b3 = Button(text="Clear route")
        b1.bind(on_release=lambda *_: self._upload("route"))
        b2.bind(on_release=lambda *_: self._upload("situation"))
        b3.bind(on_release=lambda *_: self.route_layer.clear())
        for b in (b1, b2, b3):
            bar.add_widget(b)
        root.add_widget(bar)
        self.add_widget(root)
        self.map.bind(zoom=lambda *_: self._rescale())

    # -- live data ---------------------------------------------------------
    def update_targets(self, targets: list[dict]):
        seen = set()
        for t in targets:
            seen.add(t["id"])
            m = self.markers.get(t["id"])
            if m is None:
                m = TargetMarker(t, self.app.api, self._tap_target)
                self.markers[t["id"]] = m
                self.map.add_marker(m)
            else:
                m.lat, m.lon = t["lat"], t["lon"]
            m.rescale(self.map.zoom)
        for tid in [i for i in self.markers if i not in seen]:
            self.map.remove_marker(self.markers.pop(tid))
        self.map.trigger_update(True)

    def _rescale(self):
        for m in self.markers.values():
            m.rescale(self.map.zoom)
        self.route_layer.reposition()

    def _tap_target(self, target):
        try:
            data = self.app.api.route(target["id"])
            self.route_layer.set_route(data.get("history", []))
        except Exception as e:
            self._popup("Route error", str(e))

    # -- training uploads --------------------------------------------------
    def _upload(self, kind):
        try:
            from plyer import filechooser
            filechooser.open_file(
                on_selection=lambda sel: self._do_upload(kind, sel))
        except Exception as e:
            self._popup("File picker unavailable", str(e))

    def _do_upload(self, kind, selection):
        if not selection:
            return
        path = selection[0]
        try:
            if kind == "route":
                r = self.app.api.upload_route(path)
            else:
                r = self.app.api.upload_situation(path)
            self._popup("Uploaded", str(r))
        except Exception as e:
            self._popup("Upload failed", str(e))

    def _popup(self, title, text):
        Popup(title=title, content=Label(text=text[:500]),
              size_hint=(0.8, 0.4)).open()


class TrackerApp(App):
    def build(self):
        self.api: Api | None = None
        self.sm = ScreenManager()
        self.sm.add_widget(LoginScreen(self, name="login"))
        self.map_screen = MapScreen(self, name="map")
        self.sm.add_widget(self.map_screen)
        return self.sm

    def start_stream(self):
        self.api.stream(
            lambda targets: Clock.schedule_once(
                lambda *_: self.map_screen.update_targets(targets), 0))


if __name__ == "__main__":
    TrackerApp().run()
