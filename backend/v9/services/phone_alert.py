"""phone_alert — IDEA-2: critical alerts to Michael's phone (Michael 07-13).

Fires a push to the phone on the events that matter when away from the screen:
🔴 CRITICAL alarms (naked-stop / divergence), risk-halt trip, live trade opened.

Providers (env PHONE_ALERT_PROVIDER):
  pushover  — PUSHOVER_TOKEN + PUSHOVER_USER
  telegram  — TELEGRAM_BOT_TOKEN + TELEGRAM_CHAT_ID
Credentials live in .env only (out-of-git), like ANTHROPIC_API_KEY.

Safety-by-design: flag PHONE_ALERTS_V1 (default OFF) · never raises (a push
failure may NEVER touch the trading path) · rate-limited per alert-key
(≤1 per 5 min) so a stuck alarm doesn't flood the phone · 5s network timeout
on a background thread (never blocks the caller).
"""
from __future__ import annotations

import json
import logging
import os
import threading
import time
import urllib.parse
import urllib.request
from typing import Dict

logger = logging.getLogger(__name__)

_last_sent: Dict[str, float] = {}
_RATE_S = 300.0

def enabled() -> bool:
    return os.getenv("PHONE_ALERTS_V1", "0").lower() in ("1", "true", "yes")


def _send_pushover(title: str, msg: str, priority: int) -> bool:
    """Legacy urllib transport — kept only as a last resort.

    It read PUSHOVER_TOKEN / PUSHOVER_USER, names that have never existed in
    `.env` (the real ones are PUSHOVER_API_TOKEN / PUSHOVER_USER_KEY), so this
    path returned False forever and the failure looked like "no credentials".
    Accept both spellings so a fallback is a fallback and not a dead end.
    """
    tok = os.getenv("PUSHOVER_API_TOKEN", "") or os.getenv("PUSHOVER_TOKEN", "")
    usr = os.getenv("PUSHOVER_USER_KEY", "") or os.getenv("PUSHOVER_USER", "")
    if not (tok and usr):
        return False
    data = urllib.parse.urlencode({
        "token": tok, "user": usr, "title": title, "message": msg[:900],
        "priority": 1 if priority >= 1 else 0,
    }).encode()
    req = urllib.request.Request("https://api.pushover.net/1/messages.json", data=data)
    with urllib.request.urlopen(req, timeout=5) as r:
        return r.status == 200


def _send_telegram(title: str, msg: str, priority: int) -> bool:
    tok, chat = os.getenv("TELEGRAM_BOT_TOKEN", ""), os.getenv("TELEGRAM_CHAT_ID", "")
    if not (tok and chat):
        return False
    body = json.dumps({"chat_id": chat, "text": f"{title}\n{msg[:900]}"}).encode()
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{tok}/sendMessage", data=body,
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=5) as r:
        return r.status == 200


def push(key: str, title: str, msg: str, priority: int = 1) -> None:
    """Fire-and-forget push. `key` rate-limits repeats (same key ≤1/5min).

    FIX 2026-07-27 (after Michael lost >½ account while 12 CRITICAL naked-stop
    alerts died in the log): the LOCAL alert now fires FIRST and ALWAYS —
    independent of PHONE_ALERTS_V1 and of any remote credentials. The remote
    push stays best-effort on top. Root cause of the blindness: this function
    returned on line 1 because PHONE_ALERTS_V1 was never set, so every caller
    silently no-op'd. A safety alert must never depend on optional config.
    """
    try:
        from backend.v9.services import local_alert as _la
        _la.alert(key, title, msg)
    except Exception:
        pass  # local alert must never break the caller

    if not enabled():
        return
    now = time.time()
    if now - _last_sent.get(key, 0.0) < _RATE_S:
        return
    _last_sent[key] = now

    def _bg():
        try:
            prov = os.getenv("PHONE_ALERT_PROVIDER", "pushover").strip().lower()
            if prov == "telegram":
                ok = _send_telegram(title, msg, priority)
                if not ok:
                    logger.warning("[phone_alert] send failed/no-creds (provider=%s, key=%s)", prov, key)
                return
            # ROOT-FIX 2026-08-13 (orphan-breach 08-12 died silently): delegate to
            # ntfy_notify — the proven transport (system curl, Pushover-primary with
            # the real env names PUSHOVER_USER_KEY/PUSHOVER_API_TOKEN + ntfy backup).
            # The old _send_pushover here used urllib (broken SSL on Framework-Python)
            # and read PUSHOVER_TOKEN/PUSHOVER_USER, which were never in .env.
            from backend.v9.services import ntfy_notify as _nn
            _nn.notify(title, msg,
                       priority=("urgent" if priority >= 1 else "default"),
                       tags="rotating_light")
        except Exception as e:
            logger.warning("[phone_alert] error (never blocks trading): %s", e)

    threading.Thread(target=_bg, daemon=True, name="phone-alert").start()
