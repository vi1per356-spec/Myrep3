"""Telethon user client. Reads (does NOT join) the configured channels and
feeds new text/image messages through Gemini into the track store.

First run is interactive: it asks for the login code and 2FA password in the
Termux terminal, then caches the session so later runs are non-interactive.
"""

from __future__ import annotations

import asyncio
import io

import config
from gemini_parser import parse_message
from state import store
from training import route_hint_text


async def run_telegram():
    try:
        from telethon import TelegramClient, events
    except ImportError:
        print("[tg] telethon not installed; Telegram reader disabled")
        return

    if not config.TG_API_ID or config.TG_API_HASH.startswith("PUT-"):
        print("[tg] Telegram credentials not set in config.py; reader disabled")
        return

    client = TelegramClient(config.TG_SESSION_NAME,
                            config.TG_API_ID, config.TG_API_HASH)
    await client.start(phone=config.TG_PHONE)
    print("[tg] connected as Telegram user")

    # Resolve channels (read-only; we never join).
    entities = []
    for ch in config.TG_CHANNELS:
        try:
            entities.append(await client.get_entity(ch))
        except Exception as e:
            print(f"[tg] cannot resolve {ch}: {e}")
    if not entities:
        print("[tg] no channels configured/resolved")

    @client.on(events.NewMessage(chats=entities or None))
    async def handler(event):
        text = event.message.message or ""
        img = None
        if event.message.photo:
            buf = io.BytesIO()
            await client.download_media(event.message, buf)
            img = buf.getvalue()
        hint = route_hint_text()
        full_text = (hint + "\n" + text) if hint else text
        events_out = await asyncio.to_thread(parse_message, full_text, img)
        if events_out:
            await store.apply_events(events_out)
            print(f"[tg] {len(events_out)} event(s) from message")

    print("[tg] listening for new messages…")
    await client.run_until_disconnected()
