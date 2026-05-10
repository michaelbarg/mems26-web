"""V9 stream: TPO (Time Price Opportunity) bars (System 5).

Source: DLL export — tpo.json (NOT YET IMPLEMENTED IN DLL).
Expected format once DLL exports are ready:
  {
    "type": "tpo",
    "export_ts": <unix timestamp>,
    "bar_count": <int>,
    "bars": [
      {"ts": <float>, "letter": "A", "price": 5432.25,
       "level": 12, "period_id": 3}
    ]
  }

Note: Until DLL export is created, this stream will log a warning
and skip on startup (file won't exist). System 5 currently feeds
TPO data via market_profile section of mes_ai_data.json — a
separate adapter may be needed.
"""

from .base_stream import BaseV9Stream


class TpoStream(BaseV9Stream):
    name = "tpo"
    filename = "tpo.json"
    redis_key = "mems26:v9:tpo"
    api_path = "/api/v9/bars/tpo"
