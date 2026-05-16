"""Pre-fire validator — D-063 Self-Validation Mandate (BASE).

Validates a fire request against minimum safety checks before
any system (S2/S3/S4) can emit a trade signal.

BASE checks (this wave):
  1. Bridge health (data freshness < 5s)
  2. RTH open (via market_clock if available)
  3. Basic schema correctness

Wave 2+ adds: cool-down, daily cap, stop range, news window, etc.
"""

import logging
import time
from typing import Optional

from .schemas import FireRequest, ValidationResult

logger = logging.getLogger("mems26.pre_fire_validator")


class PreFireValidator:
    """Stateless validator — call validate() per fire attempt."""

    def validate(self, req: FireRequest) -> ValidationResult:
        reasons = []
        checks_run = 0
        checks_passed = 0

        # Check 1: Schema correctness
        checks_run += 1
        if req.direction not in ("LONG", "SHORT"):
            reasons.append(f"invalid_direction: {req.direction}")
        elif req.entry_price <= 0:
            reasons.append("invalid_entry_price: must be > 0")
        elif req.stop_price <= 0:
            reasons.append("invalid_stop_price: must be > 0")
        elif req.system_id not in ("S2", "S3", "S4"):
            reasons.append(f"invalid_system_id: {req.system_id}")
        else:
            checks_passed += 1

        # Check 2: Bridge health (data freshness)
        checks_run += 1
        bridge_ok = self._check_bridge_health()
        if bridge_ok:
            checks_passed += 1
        else:
            reasons.append("bridge_stale: data older than 5s or unreachable")

        # Check 3: RTH open
        checks_run += 1
        rth_ok = self._check_rth_open()
        if rth_ok is None:
            # market_clock not available — pass with note
            checks_passed += 1
            reasons.append("rth_check_skipped: market_clock unavailable")
        elif rth_ok:
            checks_passed += 1
        else:
            reasons.append("rth_closed: market not in RTH hours")

        passed = checks_passed == checks_run or (
            checks_passed >= checks_run - 1 and "rth_check_skipped" in str(reasons)
        )
        # If only rth_check_skipped is in reasons and everything else passed, still pass
        real_failures = [r for r in reasons if "skipped" not in r]
        passed = len(real_failures) == 0

        return ValidationResult(
            passed=passed,
            reasons=reasons,
            checks_run=checks_run,
            checks_passed=checks_passed,
        )

    def _check_bridge_health(self) -> bool:
        """Check bridge data freshness < 5s."""
        import os
        live_price_path = "/Users/michael/SierraChart_Data/v9_export/live_price.json"
        try:
            mtime = os.path.getmtime(live_price_path)
            age = time.time() - mtime
            return age < 5.0
        except Exception:
            return False

    def _check_rth_open(self) -> Optional[bool]:
        """Check if RTH is open via market_clock. Returns None if unavailable."""
        try:
            from backend.v9.services.market_clock import MarketClock
            clock = MarketClock()
            return clock.is_rth_open()
        except ImportError:
            return None
        except Exception:
            return None
