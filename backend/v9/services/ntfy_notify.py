"""Push notifications via ntfy.sh for trading events (P1.6 + K7a).

Sends to the NTFY_TOPIC from .env. Events: fire, fill, close, alert,
pause, eod, emergency. Rate-limited to avoid flooding the watch.
Fire-and-forget on a daemon thread — never blocks the trading loop.
"""

from __future__ import annotations

import logging
import os
import subprocess
import threading
import time
import traceback
from typing import Optional
import urllib.request

logger = logging.getLogger(__name__)

NTFY_URL = "https://ntfy.sh"

# K7a rate limiter: max RATE_LIMIT_MAX sends per RATE_LIMIT_WINDOW_S seconds
RATE_LIMIT_WINDOW_S = 60.0
RATE_LIMIT_MAX = 10
_send_timestamps: list = []
_rate_lock = threading.Lock()


def _topic() -> Optional[str]:
    t = os.getenv("NTFY_TOPIC", "").strip()
    return t if t else None


def _rate_limited() -> bool:
    """True if we've exceeded the rate limit. Thread-safe."""
    now = time.monotonic()
    with _rate_lock:
        # Prune old timestamps
        _send_timestamps[:] = [
            ts for ts in _send_timestamps
            if now - ts < RATE_LIMIT_WINDOW_S
        ]
        if len(_send_timestamps) >= RATE_LIMIT_MAX:
            return True
        _send_timestamps.append(now)
        return False


def _machine_tag() -> str:
    """Per-machine notification prefix (Michael 13.08: two Macs live in
    parallel → every push must say WHICH machine sent it).

    MACHINE_TAG env wins; falls back to the short hostname so an unset
    machine is still distinguishable (never silently identical)."""
    tag = os.getenv("MACHINE_TAG", "").strip()
    if not tag:
        try:
            import socket
            tag = socket.gethostname().split(".")[0]
        except Exception:
            tag = ""
    return tag


def notify(title: str, message: str, *, priority: str = "default",
           tags: str = "") -> None:
    """Send a push notification. Never raises — fire-and-forget."""
    _mt = _machine_tag()
    if _mt and not title.startswith(f"[{_mt}]"):
        title = f"[{_mt}] {title}"
    topic = _topic()

    if _rate_limited():
        logger.warning("ntfy rate-limited: dropping '%s' (%d sends in last %.0fs)",
                        title, RATE_LIMIT_MAX, RATE_LIMIT_WINDOW_S)
        return

    def _send():
        # 13.08 fix: a missing NTFY_TOPIC must skip only the ntfy leg — it used
        # to return from notify() BEFORE the Pushover thread, holding the
        # working channel hostage to the backup channel's config.
        if not topic:
            return
        # 10.08 root-fix: urllib on Framework-Python 3.9 fails SSL verification
        # against ntfy.sh (certs not installed) — every live notification died
        # with CERTIFICATE_VERIFY_FAILED while manual /usr/bin/curl worked.
        # Use system curl (macOS trust store) as the primary transport.
        try:
            url = f"{NTFY_URL}/{topic}"
            cmd = ["/usr/bin/curl", "-s", "-m", "6",
                   "-H", f"Title: {title}", "-H", f"Priority: {priority}"]
            if tags:
                cmd += ["-H", f"Tags: {tags}"]
            cmd += ["-d", message, url]
            r = subprocess.run(cmd, capture_output=True, timeout=8)
            if r.returncode != 0:
                logger.warning("ntfy curl send failed rc=%s: %s",
                               r.returncode, r.stderr.decode()[:200])
        except Exception:
            # K7a: failures must be visible, not swallowed (No Silent Failures rule)
            logger.warning("ntfy send failed: %s", traceback.format_exc())

    t = threading.Thread(target=_send, daemon=True)
    t.start()
    # dual-transport: Pushover (primary on iPhone/Watch) + ntfy (backup)
    threading.Thread(target=_pushover,
                     args=(title, message, priority, tags),
                     daemon=True).start()


def _pushover(title: str, message: str, priority: str, tags: str) -> None:
    """Pushover transport (Michael 11.08) — APNs-backed, has a native Apple
    Watch app; ntfy proved unreliable on iOS background delivery. Sends only
    when both PUSHOVER_USER_KEY and PUSHOVER_API_TOKEN are set. Emergency
    priority=urgent maps to Pushover priority 1 (bypasses quiet hours)."""
    user = os.getenv("PUSHOVER_USER_KEY", "").strip()
    token = os.getenv("PUSHOVER_API_TOKEN", "").strip()
    if not (user and token):
        return
    prio = {"urgent": "1", "high": "1", "default": "0", "low": "-1"}.get(priority, "0")
    try:
        cmd = ["/usr/bin/curl", "-s", "-m", "6",
               "--form-string", f"token={token}",
               "--form-string", f"user={user}",
               "--form-string", f"title={title}",
               "--form-string", f"message={message}",
               "--form-string", f"priority={prio}",
               "https://api.pushover.net/1/messages.json"]
        r = subprocess.run(cmd, capture_output=True, timeout=8)
        if r.returncode != 0 or b'"status":1' not in r.stdout:
            logger.warning("pushover send failed rc=%s: %s",
                           r.returncode, (r.stdout or r.stderr).decode()[:200])
    except Exception:
        logger.warning("pushover send failed: %s", traceback.format_exc())


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


# ── K7a: new event types (PAUSE/EOD/emergency) ──────────────────────────────

def on_pause(reason: str) -> None:
    """Notify when trading is paused (risk halt, manual pause, etc.)."""
    notify("⏸ PAUSE", reason, priority="high", tags="pause")


def on_resume(reason: str) -> None:
    """Notify when trading resumes after a pause."""
    notify("▶️ RESUME", reason, priority="default", tags="resume")


def on_eod(summary: str) -> None:
    """End-of-day summary notification."""
    notify("📊 EOD", summary, priority="default", tags="eod")


def on_emergency(title: str, message: str) -> None:
    """Critical system emergency — max priority."""
    notify(f"🚨 {title}", message, priority="urgent", tags="emergency,skull")
