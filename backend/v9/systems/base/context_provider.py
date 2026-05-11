"""ContextProviderSystem — base for OBSERVING systems that provide context.

Systems 3 (Footprint), 5 (TPO), 6 (Killzone) extend this.
They never generate trade entries — they publish context that
FIRING systems can read.
"""

from .trading_system import BaseV9TradingSystem, SystemType


class ContextProviderSystem(BaseV9TradingSystem):
    """Base for observing/gate systems that provide context only."""

    system_type = SystemType.OBSERVING
