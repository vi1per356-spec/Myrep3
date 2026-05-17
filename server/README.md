# Ukraine Threat Tracker — Server (Termux)

Reads Telegram channels (read-only), parses messages/images with Gemini, runs a
physics simulation of every air target, and streams the live picture to the
phone client over WebSocket.

## Credentials

- **Username:** `admin`
- **Password:** `Trident-3848`

(Defined in `config.py` — change there if needed.)

## Install on Termux

```bash
pkg update && pkg install python rust binutils -y
pip install -r requirements.txt
```

`rust`/`binutils` are needed because some deps build native wheels on Android.

## Configure `config.py`

Set before first run:

- `GEMINI_API_KEY`
- `TG_API_ID`, `TG_API_HASH`, `TG_PHONE`
- `TG_CHANNELS` — list of channel links/usernames to read

## First run (Telegram login is interactive)

```bash
bash run.sh
```

On the first start Telethon asks in the terminal for the **login code** sent to
your Telegram and your **2FA password**. After that the session is cached in
`utt_session.session` and later runs are non-interactive.

## How it works

| Module | Role |
|---|---|
| `telegram_reader.py` | Reads new messages from configured channels |
| `gemini_parser.py` | Gemini turns text/images into structured events |
| `simulation.py` | Per-target physics: speed, smooth turns, route history |
| `state.py` | Track store + WebSocket broadcast + sim loop |
| `training.py` | The two training buttons (routes / past moment) |
| `app.py` | FastAPI HTTP + WebSocket API |

Targets keep flying straight when no new info arrives, and perform smooth
(rounded) turns when redirected. Speeds per type are in `threats.py`.

The phone client connects to `http://<phone-LAN-ip>:8765`.
