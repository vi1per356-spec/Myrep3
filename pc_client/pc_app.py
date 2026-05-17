"""Ukraine Threat Tracker — desktop (PC) client.

Pure-Python Tkinter app. Connects to the Termux server, shows a light
OpenStreetMap map LOCKED to Ukraine, live targets with zoom-reactive red
icons, tap-to-trace routes, and the two training-upload buttons.

Run:  python pc_app.py
"""

from __future__ import annotations

import json
import os
import queue
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import requests
import tkintermapview
import websocket  # websocket-client
from PIL import Image, ImageTk

ICON_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icons")

# Ukraine bounding box — the camera is clamped to this.
UA = {"min_lat": 44.0, "max_lat": 52.5, "min_lon": 22.0, "max_lon": 40.3}
UA_CENTER = (49.0, 31.2)
MIN_ZOOM = 6
MAX_ZOOM = 14
REF_ZOOM = 7


class Api:
    def __init__(self, base):
        self.base = base.rstrip("/")
        self.token = None
        self._ws = None

    def login(self, user, pwd):
        r = requests.post(f"{self.base}/login",
                          json={"username": user, "password": pwd}, timeout=10)
        if r.status_code == 200:
            self.token = r.json()["token"]
            return True
        return False

    def _h(self):
        return {"Authorization": f"Bearer {self.token}"}

    def route(self, tid):
        return requests.get(f"{self.base}/route/{tid}",
                            headers=self._h(), timeout=10).json()

    def upload(self, kind, path):
        ep = "route" if kind == "route" else "situation"
        with open(path, "rb") as f:
            return requests.post(f"{self.base}/training/{ep}",
                                 headers=self._h(),
                                 files={"file": f}, timeout=60).json()

    def stream(self, on_snapshot):
        url = self.base.replace("http", "ws", 1) + f"/ws?token={self.token}"

        def on_msg(_w, m):
            try:
                d = json.loads(m)
                if d.get("type") == "snapshot":
                    on_snapshot(d.get("targets", []))
            except Exception:
                pass

        self._ws = websocket.WebSocketApp(url, on_message=on_msg)
        threading.Thread(target=self._ws.run_forever, daemon=True).start()


class LoginDialog(tk.Toplevel):
    def __init__(self, master):
        super().__init__(master)
        self.title("Connect")
        self.resizable(False, False)
        self.result = None
        frm = ttk.Frame(self, padding=16)
        frm.grid()
        ttk.Label(frm, text="Ukraine Threat Tracker",
                  font=("", 14, "bold")).grid(columnspan=2, pady=(0, 12))
        self.server = tk.StringVar(value="http://127.0.0.1:8765")
        self.user = tk.StringVar(value="admin")
        self.pwd = tk.StringVar()
        rows = [("Server URL", self.server, False),
                ("Username", self.user, False),
                ("Password", self.pwd, True)]
        for i, (lbl, var, secret) in enumerate(rows, start=1):
            ttk.Label(frm, text=lbl).grid(row=i, column=0, sticky="e", padx=4,
                                          pady=4)
            ttk.Entry(frm, textvariable=var, width=30,
                      show="*" if secret else "").grid(row=i, column=1, pady=4)
        ttk.Button(frm, text="Connect", command=self._ok).grid(
            columnspan=2, pady=(12, 0))
        self.bind("<Return>", lambda *_: self._ok())
        self.grab_set()

    def _ok(self):
        self.result = (self.server.get().strip(), self.user.get().strip(),
                       self.pwd.get())
        self.destroy()


class App:
    def __init__(self, root: tk.Tk, api: Api):
        self.root = root
        self.api = api
        self.markers: dict[str, object] = {}
        self.targets: dict[str, dict] = {}
        self.route_path = None
        self.q: queue.Queue = queue.Queue()
        self._base_imgs: dict[str, Image.Image] = {}
        self._photo_refs: dict[str, ImageTk.PhotoImage] = {}
        self._last_zoom = None

        root.title("Ukraine Threat Tracker")
        root.geometry("1100x780")

        bar = ttk.Frame(root)
        bar.pack(fill="x")
        ttk.Button(bar, text="Upload route",
                   command=lambda: self._upload("route")).pack(side="left",
                                                               padx=4, pady=4)
        ttk.Button(bar, text="Upload moment",
                   command=lambda: self._upload("situation")).pack(side="left",
                                                                   padx=4)
        ttk.Button(bar, text="Clear route",
                   command=self._clear_route).pack(side="left", padx=4)
        self.status = ttk.Label(bar, text="connecting…")
        self.status.pack(side="right", padx=8)

        self.map = tkintermapview.TkinterMapView(root, corner_radius=0)
        self.map.pack(fill="both", expand=True)
        self.map.set_tile_server(
            "https://a.tile.openstreetmap.org/{z}/{x}/{y}.png")
        self.map.max_zoom = MAX_ZOOM
        self.map.min_zoom = MIN_ZOOM
        self.map.set_position(*UA_CENTER)
        self.map.set_zoom(MIN_ZOOM)

        for name in ("shahed", "molniya", "cruise_missile",
                     "ballistic_missile", "recon_uav", "kinzhal", "kab"):
            p = os.path.join(ICON_DIR, f"{name}.png")
            if os.path.exists(p):
                self._base_imgs[name] = Image.open(p).convert("RGBA")

        self.api.stream(lambda t: self.q.put(t))
        self.root.after(200, self._pump)
        self.root.after(400, self._enforce_bounds)

    # -- icon scaling ------------------------------------------------------
    def _icon(self, name: str, zoom: float) -> ImageTk.PhotoImage:
        base = self._base_imgs.get(name)
        if base is None:
            base = Image.new("RGBA", (32, 32), (211, 47, 47, 255))
        factor = max(0.45, min(2.2, (REF_ZOOM / max(zoom, 1)) ** 0.9))
        s = max(16, int(46 * factor))
        img = base.resize((s, s), Image.LANCZOS)
        photo = ImageTk.PhotoImage(img)
        self._photo_refs[f"{name}:{s}"] = photo  # keep ref alive
        return photo

    # -- live data ---------------------------------------------------------
    def _pump(self):
        try:
            while True:
                self.targets = {t["id"]: t for t in self.q.get_nowait()}
                self._redraw()
        except queue.Empty:
            pass
        self.root.after(300, self._pump)

    def _redraw(self):
        z = self.map.zoom
        seen = set()
        for tid, t in self.targets.items():
            seen.add(tid)
            m = self.markers.get(tid)
            if m is not None:
                m.delete()
            icon = self._icon(t.get("icon", "shahed"), z)
            self.markers[tid] = self.map.set_marker(
                t["lat"], t["lon"], text="",
                icon=icon,
                command=lambda mk, _tid=tid: self._show_route(_tid))
        for tid in [i for i in list(self.markers) if i not in seen]:
            self.markers.pop(tid).delete()
        self.status.config(text=f"{len(self.targets)} target(s) · zoom {int(z)}")
        self._last_zoom = z

    def _show_route(self, tid):
        try:
            data = self.api.route(tid)
            pts = [(h[0], h[1]) for h in data.get("history", [])]
            self._clear_route()
            if len(pts) >= 2:
                self.route_path = self.map.set_path(pts, color="#D32F2F",
                                                    width=3)
        except Exception as e:
            messagebox.showerror("Route error", str(e))

    def _clear_route(self):
        if self.route_path is not None:
            self.route_path.delete()
            self.route_path = None

    # -- Ukraine lock ------------------------------------------------------
    def _enforce_bounds(self):
        try:
            lat, lon = self.map.get_position()
            clat = min(UA["max_lat"], max(UA["min_lat"], lat))
            clon = min(UA["max_lon"], max(UA["min_lon"], lon))
            if abs(clat - lat) > 1e-4 or abs(clon - lon) > 1e-4:
                self.map.set_position(clat, clon)
            if self.map.zoom < MIN_ZOOM:
                self.map.set_zoom(MIN_ZOOM)
            if self._last_zoom is not None and \
               abs(self.map.zoom - self._last_zoom) >= 1:
                self._redraw()
        except Exception:
            pass
        self.root.after(500, self._enforce_bounds)

    # -- training uploads --------------------------------------------------
    def _upload(self, kind):
        path = filedialog.askopenfilename(
            title=f"Select {kind} image",
            filetypes=[("Images", "*.png *.jpg *.jpeg *.webp"), ("All", "*")])
        if not path:
            return
        try:
            r = self.api.upload(kind, path)
            messagebox.showinfo("Uploaded", json.dumps(r)[:600])
        except Exception as e:
            messagebox.showerror("Upload failed", str(e))


def main():
    root = tk.Tk()
    root.withdraw()
    while True:
        dlg = LoginDialog(root)
        root.wait_window(dlg)
        if not dlg.result:
            return
        server, user, pwd = dlg.result
        api = Api(server)
        try:
            ok = api.login(user, pwd)
        except Exception as e:
            messagebox.showerror("Connection error", str(e))
            continue
        if not ok:
            messagebox.showerror("Login", "Invalid credentials")
            continue
        break
    root.deiconify()
    App(root, api)
    root.mainloop()


if __name__ == "__main__":
    main()
