"""V9 stream: Tick Reversal 12-tick bars."""

from .base_stream import BaseV9Stream


class TickReversal12Stream(BaseV9Stream):
    name = "tick_reversal_12"
    filename = "tick_reversal_12.json"
    redis_key = "mems26:v9:tick_reversal_12"
    api_path = "/api/v9/bars/tick_reversal?tick_count=12"
    # DLL uses time(nullptr) for tick_reversal bars — already real UTC.
    SKIP_CHICAGO_TS_FIX = True
