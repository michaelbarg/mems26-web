"""
News Guard — ForexFactory USD High-Impact event integration.

State machine:
  CLEAR → PRE_NEWS_FREEZE (-10m to +3m) → POST_NEWS_OPPORTUNITY (+3m onward) → CLEAR

Critical: every API call wrapped in try/except. Failure → WARNING + system continues.
"""

import asyncio
import json
import logging
import time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from typing import Optional

log = logging.getLogger("news_guard")
ET = ZoneInfo("America/New_York")

# ── States ───────────────────────────────────────────────────────────────────
STATE_CLEAR       = "CLEAR"
STATE_PRE_FREEZE  = "PRE_NEWS_FREEZE"
STATE_POST_OPP    = "POST_NEWS_OPPORTUNITY"

# ForexFactory JSON calendar endpoint
FF_CALENDAR_URL = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"


class NewsGuard:
    def __init__(self, pre_freeze_min: int = 10, post_release_min: int = 3,
                 api_timeout: float = 5.0):
        self.pre_freeze_min = pre_freeze_min
        self.post_release_min = post_release_min
        self.api_timeout = api_timeout
        self.state = STATE_CLEAR
        self.events: list[dict] = []           # today's USD high-impact events
        self.last_fetch_date: str = ""         # "YYYY-MM-DD"
        self.active_event: Optional[dict] = None
        self.available = True                  # False if fetch failed

    async def fetch_daily_events(self, http):
        """Fetch today's USD high-impact events from ForexFactory JSON.
        Called once per day around NEWS_FETCH_HOUR_ET."""
        today = datetime.now(ET).strftime("%Y-%m-%d")
        if self.last_fetch_date == today:
            return  # already fetched today

        try:
            import aiohttp as _aio
            async with http.get(
                FF_CALENDAR_URL,
                timeout=_aio.ClientTimeout(total=self.api_timeout)
            ) as resp:
                if resp.status != 200:
                    log.warning(f"[NEWS] ForexFactory HTTP {resp.status}")
                    self.available = False
                    return
                data = await resp.json()

            # Filter: USD + High impact + today
            usd_high = []
            for ev in data:
                try:
                    if ev.get("country") != "USD":
                        continue
                    if ev.get("impact") not in ("High", "high"):
                        continue
                    # Parse date — FF format: "2026-04-17T08:30:00-04:00" or "YYYY-MM-DD"
                    ev_date_str = ev.get("date", "")
                    if "T" in ev_date_str:
                        ev_date = ev_date_str.split("T")[0]
                    else:
                        ev_date = ev_date_str[:10]
                    if ev_date != today:
                        continue
                    # Parse time
                    ev_time = ""
                    if "T" in ev_date_str:
                        ev_time = ev_date_str.split("T")[1][:5]  # "HH:MM"
                    else:
                        ev_time = ev.get("time", "")
                    if not ev_time or ev_time == "All Day":
                        continue
                    usd_high.append({
                        "title": ev.get("title", "Unknown"),
                        "time_et": ev_time,
                        "date": ev_date,
                        "impact": ev.get("impact", "High"),
                    })
                except Exception:
                    continue

            self.events = usd_high
            self.last_fetch_date = today
            self.available = True
            if usd_high:
                log.info(f"[NEWS] {len(usd_high)} USD High-Impact events today: "
                         f"{[e['time_et']+' '+e['title'] for e in usd_high]}")
            else:
                log.info("[NEWS] No USD High-Impact events today")

        except Exception as e:
            log.warning(f"[NEWS] ForexFactory fetch failed: {e} — guard unavailable")
            self.available = False

    def update_state(self) -> str:
        """Update state machine based on current time vs event times.
        Returns current state."""
        if not self.events or not self.available:
            self.state = STATE_CLEAR
            self.active_event = None
            return self.state

        now_et = datetime.now(ET)

        for ev in self.events:
            try:
                h, m = map(int, ev["time_et"].split(":"))
                event_time = now_et.replace(hour=h, minute=m, second=0, microsecond=0)

                freeze_start = event_time - timedelta(minutes=self.pre_freeze_min)
                release_time = event_time + timedelta(minutes=self.post_release_min)

                if freeze_start <= now_et < release_time:
                    if now_et < event_time + timedelta(minutes=self.post_release_min):
                        if now_et < event_time:
                            self.state = STATE_PRE_FREEZE
                        else:
                            # Between event time and +3m = still freeze
                            self.state = STATE_PRE_FREEZE
                        self.active_event = ev
                        return self.state

                # Post-news opportunity: +3m to +30m after event
                opp_end = event_time + timedelta(minutes=30)
                if release_time <= now_et < opp_end:
                    self.state = STATE_POST_OPP
                    self.active_event = ev
                    return self.state
            except Exception:
                continue

        self.state = STATE_CLEAR
        self.active_event = None
        return self.state

    def is_entry_blocked(self) -> tuple[bool, str]:
        """Check if entries should be blocked.
        Returns (blocked: bool, reason: str)."""
        state = self.update_state()
        if state == STATE_PRE_FREEZE:
            ev = self.active_event or {}
            return True, f"PRE_NEWS_FREEZE: {ev.get('title', '?')} @ {ev.get('time_et', '?')} ET"
        return False, ""

    def to_dict(self) -> dict:
        """State for Redis / WS broadcast."""
        return {
            "state": self.state,
            "available": self.available,
            "active_event": self.active_event,
            "events_today": len(self.events),
            "events": self.events,
        }


async def news_guard_loop(http, guard: NewsGuard, redis_url: str, redis_token: str,
                          redis_key: str, cloud_url: str, bridge_token: str,
                          fetch_hour: int = 7):
    """Background task: fetch events daily, update state every 30s, push to Redis."""
    while True:
        try:
            now_et = datetime.now(ET)

            # Fetch once per day around fetch_hour
            if now_et.hour == fetch_hour and guard.last_fetch_date != now_et.strftime("%Y-%m-%d"):
                await guard.fetch_daily_events(http)
            # Also fetch on startup if never fetched today
            elif not guard.last_fetch_date:
                await guard.fetch_daily_events(http)

            # Update state
            prev_state = guard.state
            guard.update_state()

            # Log state transitions
            if guard.state != prev_state:
                log.info(f"[NEWS] State: {prev_state} → {guard.state}"
                         f"{' — ' + guard.active_event['title'] if guard.active_event else ''}")
                # Broadcast state change
                try:
                    import aiohttp as _aio
                    await http.post(
                        f"{cloud_url}/ws/broadcast",
                        headers={"x-bridge-token": bridge_token, "content-type": "application/json"},
                        json={"type": "NEWS_STATE", **guard.to_dict()},
                        timeout=_aio.ClientTimeout(total=3),
                    )
                except Exception:
                    pass

            # Push state to Redis
            try:
                import aiohttp as _aio
                async with http.post(
                    f"{redis_url}/set/{redis_key}",
                    headers={"Authorization": f"Bearer {redis_token}"},
                    json=json.dumps(guard.to_dict()),
                    timeout=_aio.ClientTimeout(total=3.0)
                ) as resp:
                    pass
            except Exception:
                pass

        except Exception as e:
            log.warning(f"[NEWS] Loop error: {e}")

        await asyncio.sleep(30)
