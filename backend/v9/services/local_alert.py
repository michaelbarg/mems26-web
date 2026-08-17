"""local_alert — LOUD local alerts on the trading Mac (Michael 2026-07-27, after
a >½-account manual loss went unseen: 12 CRITICAL naked-stop alerts fired into
the log while PHONE_ALERTS_V1 was never configured → push() returned on line 1
and Michael was blind for 41 minutes on 10 naked contracts).

Design (Michael's ruling 07-27, "לבנות התראה-מקומית עכשיו"):
  • ZERO external services / credentials — must work out of the box, forever.
  • Sound FIRST (afplay, repeated) — audible even when the screen is elsewhere.
  • Then a modal macOS alert window (osascript) — impossible to miss on screen.
  • Never raises, never blocks the caller (background thread, hard timeouts):
    an alert failure may NEVER touch the trading path.
  • Rate-limited per key (default 120s) so a stuck alarm does not loop forever.

Flag: LOCAL_ALERTS_V1 (default ON — this is a safety net; opting OUT is the
explicit action, not opting in. That inversion is deliberate: the previous
default-OFF is exactly what made Michael blind).
"""
from __future__ import annotations

import logging
import os
import shutil
import subprocess
import threading
import time
from typing import Dict

logger = logging.getLogger(__name__)

_last_sent: Dict[str, float] = {}
_RATE_S_DEFAULT = 120.0

# Loud, distinct, always present on macOS.
_SOUND = "/System/Library/Sounds/Sosumi.aiff"


def _under_test() -> bool:
    """True while pytest is running.

    2026-08-17 — this is why Michael got modal windows on his screen this
    morning reading "t / m1": those are TEST fixture strings. The test suite is
    run with `env -i` (a clean environment, deliberately, so tests cannot be
    poisoned by .env), which means LOCAL_ALERTS_V1 is unset — and this module
    defaults ON. So every test that exercised an alert path opened a real
    osascript dialog and played a real sound on the trading Mac.

    The default-ON is correct and stays: it exists because on 07-27 twelve
    CRITICAL naked-stop alerts died silently while Michael was blind for 41
    minutes on 10 naked contracts. What was missing is that a TEST is not a
    trading session.
    """
    return bool(os.getenv("PYTEST_CURRENT_TEST")) or "pytest" in os.getenv("_", "")


def enabled() -> bool:
    """Default ON (safety net). Set LOCAL_ALERTS_V1=0 to silence."""
    if _under_test():
        return False
    return os.getenv("LOCAL_ALERTS_V1", "1").lower() not in ("0", "false", "no")


def _beep(times: int = 3) -> None:
    """Play the alert sound `times` (each ~1s). Falls back to the terminal bell."""
    afplay = shutil.which("afplay")
    for _ in range(max(1, times)):
        try:
            if afplay and os.path.exists(_SOUND):
                subprocess.run([afplay, _SOUND], timeout=6,
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            else:
                print("\a", end="", flush=True)
        except Exception:
            return


def _window(title: str, msg: str) -> None:
    """Modal alert window via osascript (no focus-stealing risk to Sierra:
    System Events dialog is separate and non-blocking for other apps)."""
    osa = shutil.which("osascript")
    if not osa:
        return
    safe_t = title.replace('"', "'")[:80]
    safe_m = msg.replace('"', "'")[:400]
    script = (f'display alert "🔴 {safe_t}" message "{safe_m}" as critical '
              f'buttons {{"OK"}} default button "OK" giving up after 120')
    try:
        subprocess.run([osa, "-e", script], timeout=130,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass


def alert(key: str, title: str, msg: str, beeps: int = 3,
          rate_s: float = _RATE_S_DEFAULT) -> bool:
    """Fire a loud local alert. Returns True if dispatched (not if seen).
    Fire-and-forget: sound + window run on a daemon thread. Never raises."""
    try:
        if not enabled():
            return False
        now = time.time()
        if now - _last_sent.get(key, 0.0) < rate_s:
            return False
        _last_sent[key] = now

        def _bg() -> None:
            try:
                _beep(beeps)          # sound first — audible away from the screen
                _window(title, msg)   # then the modal window
            except Exception as e:    # pragma: no cover - defensive
                logger.warning("[local_alert] failed (never blocks trading): %s", e)

        threading.Thread(target=_bg, daemon=True, name="local-alert").start()
        logger.critical("[local_alert] 🔴 %s — %s", title, msg[:200])
        return True
    except Exception as e:  # pragma: no cover - defensive
        logger.warning("[local_alert] dispatch error: %s", e)
        return False
