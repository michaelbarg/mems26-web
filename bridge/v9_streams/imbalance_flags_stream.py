"""V9 stream: Imbalance Flags (levels with 250%+ bid/ask ratio)."""

from .base_stream import BaseV9Stream


class ImbalanceFlagsStream(BaseV9Stream):
    name = "imbalance_flags"
    filename = "imbalance_flags.json"
    redis_key = "mems26:v9:imbalance"
    api_path = "/api/v9/bars/imbalance"
