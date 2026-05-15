"""Extension Tracker — tracks IB extensions after 10:30 ET lock.

Per Mind Over Markets pp.78-86 + Zohar Chapter 5:
  After the Initial Balance (IB) period locks at 10:30 ET, price can
  extend beyond IB high or IB low. Each extension is tracked with
  direction (UP/DOWN). A "failed extension" occurs when price returns
  inside the IB range after extending.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional, Tuple


class Direction(str, Enum):
    """Extension direction relative to IB range."""
    UP = "UP"      # Zohar Ch.5: price above IB high
    DOWN = "DOWN"  # Zohar Ch.5: price below IB low


@dataclass(frozen=True)
class ExtensionEvent:
    """Immutable record of an IB extension."""
    direction: Direction
    price: float           # bar close that caused the extension
    ib_boundary: float     # IB high (UP) or IB low (DOWN) that was breached
    ts: float              # epoch seconds


@dataclass(frozen=True)
class FailedExtensionEvent:
    """Immutable record of a failed extension (return to IB range)."""
    direction: Direction   # which extension failed
    peak_price: float      # furthest price reached during extension
    return_price: float    # bar close back inside IB
    ts: float              # epoch seconds


class ExtensionTracker:
    """Tracks IB extensions after 10:30 ET lock.

    Usage:
        1. Call lock_ib(ib_high, ib_low) once IB period ends.
        2. Call on_bar_close(bar_close, ts) for each subsequent bar.
        3. Returns (ExtensionEvent | None, FailedExtensionEvent | None).
    """

    def __init__(self) -> None:
        self._ib_high: float = 0.0
        self._ib_low: float = 0.0
        self._locked: bool = False

        # Current extension state
        self._extending_up: bool = False
        self._extending_down: bool = False
        self._peak_up: float = 0.0       # highest price during UP extension
        self._peak_down: float = float("inf")  # lowest price during DOWN extension

        # Cumulative counts
        self.extensions_up: int = 0
        self.extensions_down: int = 0
        self.failed_extensions_up: int = 0
        self.failed_extensions_down: int = 0

    @property
    def is_locked(self) -> bool:
        """Whether IB has been locked."""
        return self._locked

    def lock_ib(self, ib_high: float, ib_low: float) -> None:
        """Lock the IB range. Called once at 10:30 ET.

        Args:
            ib_high: IB period high (09:30-10:30 ET)
            ib_low:  IB period low  (09:30-10:30 ET)
        """
        self._ib_high = ib_high
        self._ib_low = ib_low
        self._locked = True
        self._peak_up = ib_high
        self._peak_down = ib_low

    def on_bar_close(
        self, bar_close: float, ts: float
    ) -> Tuple[Optional[ExtensionEvent], Optional[FailedExtensionEvent]]:
        """Process a bar close after IB lock.

        Returns:
            (extension_event, failed_extension_event) — either or both may be None.
        """
        if not self._locked:
            return None, None

        ext_event: Optional[ExtensionEvent] = None
        fail_event: Optional[FailedExtensionEvent] = None

        # ── Check for new extension UP ──────────────────────────────────
        if bar_close > self._ib_high and not self._extending_up:
            self._extending_up = True
            self._peak_up = bar_close
            self.extensions_up += 1
            ext_event = ExtensionEvent(
                direction=Direction.UP,
                price=bar_close,
                ib_boundary=self._ib_high,
                ts=ts,
            )

        # ── Check for new extension DOWN ────────────────────────────────
        if bar_close < self._ib_low and not self._extending_down:
            self._extending_down = True
            self._peak_down = bar_close
            self.extensions_down += 1
            ext_event = ExtensionEvent(
                direction=Direction.DOWN,
                price=bar_close,
                ib_boundary=self._ib_low,
                ts=ts,
            )

        # ── Track peak during extension ─────────────────────────────────
        if self._extending_up and bar_close > self._peak_up:
            self._peak_up = bar_close
        if self._extending_down and bar_close < self._peak_down:
            self._peak_down = bar_close

        # ── Check for failed extension (return inside IB) ──────────────
        if self._extending_up and bar_close <= self._ib_high:
            self._extending_up = False
            self.failed_extensions_up += 1
            fail_event = FailedExtensionEvent(
                direction=Direction.UP,
                peak_price=self._peak_up,
                return_price=bar_close,
                ts=ts,
            )
            self._peak_up = self._ib_high

        if self._extending_down and bar_close >= self._ib_low:
            self._extending_down = False
            self.failed_extensions_down += 1
            fail_event = FailedExtensionEvent(
                direction=Direction.DOWN,
                peak_price=self._peak_down,
                return_price=bar_close,
                ts=ts,
            )
            self._peak_down = self._ib_low

        return ext_event, fail_event
