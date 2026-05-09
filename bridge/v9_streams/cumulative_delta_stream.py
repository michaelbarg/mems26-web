"""V9 stream: Cumulative Delta (running delta with divergence detection)."""

from .base_stream import BaseV9Stream


class CumulativeDeltaStream(BaseV9Stream):
    name = "cumulative_delta"
    filename = "cumulative_delta.json"
    redis_key = "mems26:v9:cumulative_delta"
    api_path = "/api/v9/bars/cumulative_delta"
