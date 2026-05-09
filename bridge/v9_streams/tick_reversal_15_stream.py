"""V9 stream: Tick Reversal 15-tick bars."""

from .base_stream import BaseV9Stream


class TickReversal15Stream(BaseV9Stream):
    name = "tick_reversal_15"
    filename = "tick_reversal_15.json"
    redis_key = "mems26:v9:tick_reversal_15"
    api_path = "/api/v9/bars/tick_reversal?tick_count=15"
