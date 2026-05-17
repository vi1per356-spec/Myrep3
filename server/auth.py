"""Tiny token auth: single admin account, signed bearer tokens."""

from __future__ import annotations

import hashlib
import hmac
import time

import config


def _sign(payload: str) -> str:
    return hmac.new(config.SECRET_KEY.encode(), payload.encode(),
                     hashlib.sha256).hexdigest()


def login(username: str, password: str) -> str | None:
    if username == config.ADMIN_USERNAME and password == config.ADMIN_PASSWORD:
        issued = str(int(time.time()))
        return f"{issued}.{_sign(issued)}"
    return None


def verify(token: str | None) -> bool:
    if not token:
        return False
    try:
        issued, sig = token.split(".", 1)
    except ValueError:
        return False
    if not hmac.compare_digest(sig, _sign(issued)):
        return False
    # 30-day token lifetime.
    return (time.time() - int(issued)) < 30 * 86400
