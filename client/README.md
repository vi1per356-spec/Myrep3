# Ukraine Threat Tracker — Client (APK)

Kivy app you install on the phone. It logs in to the Termux server, shows a
light OpenStreetMap map **locked to Ukraine**, draws live targets with
zoom-reactive red icons, lets you tap a target to see its full travelled
route, and has the two training-upload buttons.

## Login

- **Username:** `admin`
- **Password:** `Trident-3848`
- **Server URL:** `http://<your-phone-LAN-ip>:8765`

## Try on desktop first

```bash
pip install -r requirements.txt
python main.py
```

## Build the APK

The APK must be built with Buildozer (Linux/WSL, ~30 min first time):

```bash
pip install buildozer cython
sudo apt install -y openjdk-17-jdk autoconf libtool zlib1g-dev
buildozer android debug
```

The signed-debug APK appears in `bin/`. Copy it to the phone and install.

## Behaviour

- Camera and zoom are clamped to Ukraine (`UkraineMapView`).
- Icons shrink when you zoom in, grow when you zoom out (`TargetMarker.rescale`).
- Tapping a target requests `/route/{id}` and draws the polyline.
- "Upload route" / "Upload moment" POST a screenshot to the server's training
  endpoints so visualisation gets more realistic.

> Note: the icons are red SVGs traced from the supplied artwork; PNG copies are
> used as Kivy markers (Kivy markers can't render SVG directly). Both are in
> `icons/`.
