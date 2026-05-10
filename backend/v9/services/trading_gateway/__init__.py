"""W13 Trading Gateway — 3-mode routing layer.

Routes setups from firing systems (1, 2, 4) to SHADOW/DEMO/LIVE executors.
SHADOW: parallel, no caps, no slot limit.
DEMO: ONE slot, first-wins, Sierra demo account PA-APEX-125218-01.
LIVE: ONE slot, first-wins + W14 risk caps, Sierra live account APEX-125218-13.
"""

from backend.v9.services.trading_gateway.gateway import TradingGateway

__all__ = ["TradingGateway"]
