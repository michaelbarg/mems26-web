"""V9 stream: Volume Profile (POC/VAH/VAL per bar with level breakdown)."""

from .base_stream import BaseV9Stream


class VolumeProfileStream(BaseV9Stream):
    name = "volume_profile"
    filename = "volume_profile.json"
    redis_key = "mems26:v9:volume_profile"
    api_path = "/api/v9/bars/volume_profile"
