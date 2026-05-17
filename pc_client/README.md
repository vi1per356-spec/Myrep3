# Ukraine Threat Tracker — PC client

Desktop app (Windows / Linux / macOS). Same behaviour as the phone app:
Ukraine-locked OpenStreetMap, live targets with zoom-reactive red icons,
click a target to see its full route, and the two training-upload buttons.

## Requirements

- Python 3.9+ (Tkinter ships with the standard python.org installer; on
  Linux: `sudo apt install python3-tk`)

## Run

```bash
cd pc_client
pip install -r requirements.txt
python pc_app.py
```

A login window appears:

- **Server URL:** `http://<your-phone-LAN-IP>:8765`
  (e.g. `http://192.168.0.42:8765`; use `http://127.0.0.1:8765` only if the
  Termux server runs on this same machine)
- **Username:** `admin`
- **Password:** `Trident-3848`

## What you get

- Light OpenStreetMap, camera **clamped to Ukraine** (can't pan/zoom out of it).
- Live targets stream in over WebSocket; icons **shrink when you zoom in**,
  grow when you zoom out.
- **Click a target** → its travelled route is drawn as a red polyline.
- **Upload route / Upload moment** → sends a screenshot to the server's
  training endpoints.
- **Clear route** → removes the drawn route.

The `icons/` folder next to `pc_app.py` holds the red target icons — keep it
beside the script.

Make sure the Termux server (server branch) is running and reachable from this
PC on port 8765 (same Wi-Fi / LAN).
