#!/data/data/com.termux/files/usr/bin/bash
# Termux launcher for the Ukraine Threat Tracker server.
set -e
cd "$(dirname "$0")"
python -m uvicorn app:app --host 0.0.0.0 --port "${UTT_PORT:-8765}"
