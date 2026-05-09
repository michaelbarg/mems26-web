"""V9 stream: Stacked Imbalances (bars with 3+ consecutive imbalances)."""

from .base_stream import BaseV9Stream


class StackedImbalancesStream(BaseV9Stream):
    name = "stacked_imbalances"
    filename = "stacked_imbalances.json"
    redis_key = "mems26:v9:stacked_imbalance"
    api_path = "/api/v9/bars/stacked_imbalance"
