"""V9 stream: Continuous 24h Cumulative Delta from chart #5.

Source: DLL export — cumulative_delta_continuous.json (chart #5, 24h Globex).
"""

from .base_stream import BaseV9Stream


class CvdContinuousStream(BaseV9Stream):
    name = "cvd_continuous"
    filename = "cumulative_delta_continuous.json"
    redis_key = "mems26:v9:cvd_continuous"
    api_path = "/api/v9/bars/cvd_continuous"
