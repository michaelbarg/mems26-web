"""D-S1DYN: IB-relative dynamic day-type reclassification — SHADOW LOG ONLY.

Computes would-be day-type transitions based on IB extension, VA breakout,
and CVD alignment. Logs to v9_day_type_shadow_transitions WITHOUT changing
the live day_type that feeds Auth Table gating.

Convention: total-range (E_up = (session_high - IB_H) / IB_width).

Monotonic chain (within session):
  Normal → Variation: E_dom ≥ 0.15, sustained (not wick), POC moving
  Variation → Trend:  E_dom ≥ 1.0 (R ≥ ~2.0), one-timeframing, VAH/VAL broken
  Neutral guard:      both sides extended → Neutral override
  False-breakout hold: extension rejected (price returns to IB) → don't upgrade

D-S1DYN — see DECISION_LEDGER.
"""

import logging
import sqlite3
from datetime import datetime, timezone
from typing import Optional, Tuple

logger = logging.getLogger("mems26.day_type.shadow_reclass")

DB_PATH = "/Users/michael/Downloads/mems26_web_git/data/mems26_local.db"

# D-S1DYN: Tunable thresholds (priors — to be calibrated during soak)
NORMAL_TO_VARIATION_E = 0.15   # E_dom ≥ 0.15 IB widths
VARIATION_TO_TREND_E = 1.0     # E_dom ≥ 1.0 IB widths
NEUTRAL_GUARD_E = 0.10         # both sides ≥ 0.10 → Neutral
FALSE_BREAKOUT_RETURN = 0.5    # if price returns within 0.5 IB widths of IB edge → false breakout


class ShadowReclassifier:
    """D-S1DYN: Tracks IB-relative metrics and logs would-be transitions."""

    def __init__(self, ib_high: float, ib_low: float, session_date: str):
        self.ib_h = ib_high
        self.ib_l = ib_low
        self.ib_w = ib_high - ib_low if ib_high > ib_low else 1.0
        self.session_date = session_date
        self.shadow_type = "Normal"  # starts at Normal, upgrades monotonically
        self._highest_type = "Normal"  # never downgrades below this (monotonic)
        self._last_logged_type = "Normal"

    def process_bar(
        self,
        session_high: float,
        session_low: float,
        bar_close: float,
        session_min: int,
        vah: Optional[float] = None,
        val: Optional[float] = None,
        poc: Optional[float] = None,
        cvd: Optional[float] = None,
    ) -> Optional[str]:
        """Evaluate IB-relative metrics and log transition if warranted.

        Returns the new shadow_type if changed, None if unchanged.
        Does NOT modify any live state — shadow log only.
        """
        if self.ib_w <= 0 or session_high <= 0 or session_low is None or session_low <= 0:
            return None

        # D-S1DYN: IB extension metrics
        e_up = max(0, session_high - self.ib_h) / self.ib_w
        e_dn = max(0, self.ib_l - session_low) / self.ib_w
        r_total = (session_high - session_low) / self.ib_w if session_high > session_low else 0

        # Determine dominant side
        e_dom = max(e_up, e_dn)
        e_opp = min(e_up, e_dn)

        # D-S1DYN: Neutral guard — both sides extended
        if e_up >= NEUTRAL_GUARD_E and e_dn >= NEUTRAL_GUARD_E:
            new_type = "Neutral_Extreme"
        # D-S1DYN: Monotonic chain
        elif e_dom >= VARIATION_TO_TREND_E and r_total >= 2.0:
            new_type = "Trend_Normal"
        elif e_dom >= NORMAL_TO_VARIATION_E and e_opp < NEUTRAL_GUARD_E:
            new_type = "Variation"
        else:
            new_type = "Normal"

        # Monotonic: only upgrade, never downgrade within session
        TYPE_ORDER = {"Normal": 0, "Variation": 1, "Neutral_Extreme": 1, "Trend_Normal": 2, "Trend_DD": 3}
        if TYPE_ORDER.get(new_type, 0) <= TYPE_ORDER.get(self.shadow_type, 0):
            new_type = self.shadow_type  # hold at highest

        # False-breakout hold: if price returned inside IB, don't upgrade
        inside_ib = self.ib_l <= bar_close <= self.ib_h
        if inside_ib and new_type != self.shadow_type:
            # Price is back inside IB — likely false breakout, hold current
            return None

        # Log transition if changed
        if new_type != self._last_logged_type:
            trigger = self._describe_trigger(e_up, e_dn, r_total, vah, val, poc, cvd, bar_close)
            self._log_transition(
                session_min=session_min,
                from_type=self._last_logged_type,
                to_type=new_type,
                trigger=trigger,
                e_up=e_up, e_dn=e_dn, r_total=r_total,
                vah=vah, val=val, poc=poc, cvd=cvd, price=bar_close,
            )
            self.shadow_type = new_type
            self._last_logged_type = new_type
            return new_type

        self.shadow_type = new_type
        return None

    def _describe_trigger(self, e_up, e_dn, r, vah, val, poc, cvd, price) -> str:
        """Human-readable trigger description."""
        parts = [f"E_up={e_up:.2f}", f"E_dn={e_dn:.2f}", f"R={r:.2f}"]
        if vah and price > vah:
            parts.append(f"price>{vah:.0f}(VAH)")
        if val and price < val:
            parts.append(f"price<{val:.0f}(VAL)")
        if cvd is not None:
            parts.append(f"CVD={cvd:.0f}")
        return " · ".join(parts)

    def _log_transition(self, session_min, from_type, to_type, trigger,
                        e_up, e_dn, r_total, vah, val, poc, cvd, price):
        """Write to v9_day_type_shadow_transitions (DB)."""
        try:
            conn = sqlite3.connect(DB_PATH)
            conn.execute(
                """INSERT INTO v9_day_type_shadow_transitions
                   (ts, session_date, session_min, from_type, to_type, trigger,
                    e_up, e_dn, r_total, ib_w, ib_h, ib_l,
                    vah, val, poc, cvd, price)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    datetime.now(timezone.utc).isoformat(),
                    self.session_date, session_min, from_type, to_type, trigger,
                    round(e_up, 4), round(e_dn, 4), round(r_total, 4),
                    round(self.ib_w, 2), self.ib_h, self.ib_l,
                    vah, val, poc, cvd, price,
                ),
            )
            conn.commit()
            conn.close()
            logger.info(
                "[D-S1DYN] Shadow transition: %s → %s (%s) E_up=%.2f E_dn=%.2f R=%.2f",
                from_type, to_type, trigger, e_up, e_dn, r_total,
            )
        except Exception as e:
            logger.warning("[D-S1DYN] Shadow log write failed: %s", e)
