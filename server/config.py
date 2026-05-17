"""Central configuration for the Ukraine Threat Tracker server (Termux side).

Edit the API keys / Telegram credentials below before running.
The admin password is intentionally embedded here as requested.
"""

import os

# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------
# A client APK must send these credentials. Only one account exists.
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "Trident-3848"  # change here if you want a different one

# Random secret used to sign session tokens. Regenerate for production.
SECRET_KEY = os.environ.get("UTT_SECRET", "change-me-9f3a1c7e2b8d4f60")

# ---------------------------------------------------------------------------
# Gemini (Google Generative AI)
# ---------------------------------------------------------------------------
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "AIzaSyCXvm6tQI0rgn1uztICb8-kRwfnl2DXMEQ")
GEMINI_MODEL = "gemini-2.0-flash"

# ---------------------------------------------------------------------------
# Telegram (Telethon user session – reads channels, never subscribes)
# ---------------------------------------------------------------------------
TG_API_ID = int(os.environ.get("TG_API_ID", "29312779"))
TG_API_HASH = os.environ.get("TG_API_HASH", "71dce4edf2a60aed6aced69e202fa8dd")
# Leave blank: Telethon will prompt for the phone number, login code and
# 2FA password in the Termux terminal on first run.
TG_PHONE = os.environ.get("TG_PHONE", "")
# Session string can be created interactively the first time the reader runs.
TG_SESSION_NAME = "utt_session"

# Channels to read (public @usernames or t.me links or numeric ids).
# Fill this list once you provide the channel links.
TG_CHANNELS: list[str] = [
    "https://t.me/ukraine_pyxx",
    "https://t.me/kudy_letyt",
    "https://t.me/Ukrainian_Intelligence",
    "https://t.me/povitryanatrivogaaa",
    "https://t.me/testchanel1488_67",
]

# Fallback numeric ids (used automatically if a username fails to resolve).
TG_CHANNEL_IDS: list[int] = [
    -1002133315828,
    -1001875486764,
    -1001884189327,
    -1001547049625,
    -1003990673187,
]

# ---------------------------------------------------------------------------
# Map / geography
# ---------------------------------------------------------------------------
# Ukraine bounding box (lat/lon). Clients must clamp the camera to this.
UA_BOUNDS = {
    "min_lat": 44.0,
    "max_lat": 52.5,
    "min_lon": 22.0,
    "max_lon": 40.3,
}
UA_CENTER = {"lat": 49.0, "lon": 31.2}

# ---------------------------------------------------------------------------
# Server
# ---------------------------------------------------------------------------
HOST = "0.0.0.0"
PORT = int(os.environ.get("UTT_PORT", "8765"))

# Simulation tick (seconds). Lower = smoother movement, more CPU.
SIM_TICK = 1.0
