"""DecisionMakerSystem — base for FIRING systems that make entry decisions.

Systems 1 (Day Type), 2 (5-min), 4 (Woodies) extend this.

NOTE per D-073: Day Type is FIRING because it publishes its own
classification decision (not just raw data). Even though it doesn't
generate trade entries, its "decision" output (day type classification)
is what other systems consume. This is distinct from OBSERVING systems
which publish raw market data without making decisions.
"""

from .trading_system import BaseV9TradingSystem, SystemType


class DecisionMakerSystem(BaseV9TradingSystem):
    """Base for systems that make and publish their own decisions."""

    system_type = SystemType.FIRING
