"""V9 stream: Footprint (bid×ask per price level per bar)."""

from .base_stream import BaseV9Stream


class FootprintStream(BaseV9Stream):
    name = "footprint"
    filename = "footprint.json"
    redis_key = "mems26:v9:footprint"
    api_path = "/api/v9/bars/footprint"
