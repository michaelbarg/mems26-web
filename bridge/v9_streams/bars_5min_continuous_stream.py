"""V9 stream: Continuous 24h 5-minute bars from chart #5.

Source: DLL export — 5min_continuous.json (chart #5, 24h Globex).
Replaces RTH-only 5min.json for continuous bar coverage.
"""

from .base_stream import BaseV9Stream


class Bars5MinContinuousStream(BaseV9Stream):
    name = "bars_5min_continuous"
    filename = "5min_continuous.json"
    redis_key = "mems26:v9:bars_5min_continuous"
    api_path = "/api/v9/bars/5min_continuous"
