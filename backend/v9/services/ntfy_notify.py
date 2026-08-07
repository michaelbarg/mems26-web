"""Push notifications via ntfy.sh for trading events (P1.6).

Sends to the NTFY_TOPIC from .env. Events: fire, fill, close, alert.
Fire-and-forget on a daemon thread — never blocks the trading loop.
"""

from __future__ import annotations

import logging
import os
import threading
import traceback
from typing import Optional
import urllib.request

logger = logging.getLogger(__name__)

NTFY_URL = "https://ntfy.sh"


def _topic() -> Optional[str]:
    t = os.getenv("NTFY_TOPIC", "").strip()
    return t if t else None


def notify(title: str, message: str, *, priority: str = "default",
           tags: str = "") -> None:
    """Send a push notification. Never raises — fire-and-forget."""
    topic = _topic()
    if not topic:
        return

    def _send():
        try:
            url = f"{NTFY_URL}/{topic}"
            data = message.encode("utf-8")
            headers = {
                "Title": title,
                "Priority": priority,
            }
            if tags:
                headers["Tags"] = tags
            req = urllib.request.Request(url, data=data, headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=5) as r:
                r.read()
        except Exception:
            logger.debug("ntfy send failed: %s", traceback.format_exc())

    t = threading.Thread(target=_send, daemon=True)
    t.start()


def on_fire(trade_id: int, direction: str, pattern: str, mode: str,
            entry_price: float) -> None:
    """Notify on a new fire (setup accepted by gateway)."""
    emoji = "🔫" if mode == "live" else "👁"
    notify(
        f"{emoji} {direction} #{trade_id}",
        f"{pattern} @ {entry_price} ({mode})",
        priority="high" if mode == "live" else "default",
        tags="fire," + mode,
    )


def on_fill(trade_id: int, kind: str, price: float) -> None:
    """Notify on a Sierra fill (ENTRY, T1, T2, T3, STOP)."""
    emoji = {"ENTRY": "📥", "T1": "🎯", "T2": "🎯🎯", "T3": "🏆",
             "STOP": "🛑"}.get(kind, "📋")
    notify(
        f"{emoji} {kind} #{trade_id}",
        f"Fill @ {price}",
        priority="high" if kind in ("T3", "STOP") else "default",
        tags="fill," + kind.lower(),
    )


def on_close(trade_id: int, outcome: str, pnl: float, reason: str) -> None:
    """Notify on trade close."""
    emoji = "✅" if outcome == "WIN" else "❌" if outcome == "LOSS" else "⚪"
    notify(
        f"{emoji} #{trade_id} {outcome}",
        f"${pnl:+.2f} — {reason}",
        priority="high" if abs(pnl) > 50 else "default",
        tags="close," + outcome.lower(),
    )


def on_alert(title: str, message: str) -> None:
    """Notify on a system alert."""
    notify(f"⚠️ {title}", message, priority="high", tags="warning")
