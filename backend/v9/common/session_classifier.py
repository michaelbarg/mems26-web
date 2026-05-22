"""Session Classifier — authoritative source for trading session detection.

D-083: SessionClassifier is the single source of truth for all systems.
Principle 8: SESSION-AWARE-NOT-TIME-AWARE — use this, not raw time checks.

MES trades 23/5 via Globex. "MARKET_CLOSED" only applies to
WEEKEND (Fri 17:00 - Sun 18:00 ET) and MAINTENANCE (17:00-18:00 ET daily).
"""

from dataclasses import dataclass
from datetime import datetime, time, timedelta, timezone
from enum import Enum
from typing import Optional

import pytz
from backend.v9.services.market_clock import now_et


class Session(str, Enum):
    OVERNIGHT = "OVERNIGHT"       # 18:00-08:00 ET (Globex)
    PRE_MARKET = "PRE_MARKET"     # 08:00-09:30 ET (active pre-cash)
    CASH_OPEN = "CASH_OPEN"       # 09:30-09:35 ET (opening rotation)
    FIRST_HOUR = "FIRST_HOUR"     # 09:35-10:30 ET
    CASH_HOURS = "CASH_HOURS"     # 10:30-16:00 ET
    AFTER_HOURS = "AFTER_HOURS"   # 16:00-17:00 ET
    MAINTENANCE = "MAINTENANCE"   # 17:00-18:00 ET (daily)
    WEEKEND = "WEEKEND"           # Friday 17:00 - Sunday 18:00 ET


@dataclass
class SessionInfo:
    session: Session
    et_time: datetime
    minutes_to_next: int
    next_session: Session
    is_trading_active: bool  # True except WEEKEND, MAINTENANCE


class SessionClassifier:
    """Authoritative classifier for trading sessions.

    All systems must use this to determine current session.
    """

    ET = pytz.timezone('America/New_York')

    def classify(self, now: Optional[datetime] = None) -> SessionInfo:
        if now is None:
            now = now_et()
        elif now.tzinfo is None:
            now = self.ET.localize(now)
        else:
            now = now.astimezone(self.ET)

        weekday = now.weekday()  # 0=Mon, 6=Sun
        h, m = now.hour, now.minute
        ct = time(h, m)

        # Weekend: Friday 17:00 → Sunday 18:00
        if weekday == 4 and h >= 17:
            return self._info(Session.WEEKEND, now, Session.OVERNIGHT)
        if weekday == 5:
            return self._info(Session.WEEKEND, now, Session.OVERNIGHT)
        if weekday == 6 and h < 18:
            return self._info(Session.WEEKEND, now, Session.OVERNIGHT)

        # Daily maintenance: 17:00-18:00 ET
        if time(17, 0) <= ct < time(18, 0):
            return self._info(Session.MAINTENANCE, now, Session.OVERNIGHT)

        # After hours: 16:00-17:00 ET
        if time(16, 0) <= ct < time(17, 0):
            return self._info(Session.AFTER_HOURS, now, Session.MAINTENANCE)

        # Cash hours: 10:30-16:00 ET
        if time(10, 30) <= ct < time(16, 0):
            return self._info(Session.CASH_HOURS, now, Session.AFTER_HOURS)

        # First hour: 09:35-10:30 ET
        if time(9, 35) <= ct < time(10, 30):
            return self._info(Session.FIRST_HOUR, now, Session.CASH_HOURS)

        # Cash open: 09:30-09:35 ET
        if time(9, 30) <= ct < time(9, 35):
            return self._info(Session.CASH_OPEN, now, Session.FIRST_HOUR)

        # Pre-market: 08:00-09:30 ET
        if time(8, 0) <= ct < time(9, 30):
            return self._info(Session.PRE_MARKET, now, Session.CASH_OPEN)

        # Overnight (Globex): all other weekday times
        return self._info(Session.OVERNIGHT, now, Session.PRE_MARKET)

    def _info(self, session: Session, now: datetime, next_sess: Session) -> SessionInfo:
        is_active = session not in (Session.WEEKEND, Session.MAINTENANCE)
        return SessionInfo(
            session=session,
            et_time=now,
            minutes_to_next=0,
            next_session=next_sess,
            is_trading_active=is_active,
        )

    def is_globex(self, session: Session) -> bool:
        return session in (Session.OVERNIGHT, Session.PRE_MARKET, Session.AFTER_HOURS)

    def is_cash(self, session: Session) -> bool:
        return session in (Session.CASH_OPEN, Session.FIRST_HOUR, Session.CASH_HOURS)

    def current_session_open_utc(self, now: Optional[datetime] = None) -> datetime:
        """Return the most recent Globex session open (18:00 ET) as UTC datetime.

        Globex session opens at 18:00 ET each trading day.
        If now is before 18:00 ET, the session opened yesterday at 18:00 ET.
        If now is at or after 18:00 ET, the session opened today at 18:00 ET.
        """
        if now is None:
            now = now_et()
        elif now.tzinfo is None:
            now = self.ET.localize(now)
        else:
            now = now.astimezone(self.ET)

        session_open_et = now.replace(hour=18, minute=0, second=0, microsecond=0)
        if now.time() < time(18, 0):
            session_open_et -= timedelta(days=1)

        return session_open_et.astimezone(timezone.utc)
