"""V9 stream: 5-minute OHLCV bars (System 2 data feed).

Source: DLL export — 5min.json (NOT YET IMPLEMENTED AS STANDALONE DLL EXPORT).
Expected format once DLL exports are ready:
  {
    "type": "5min",
    "export_ts": <unix timestamp>,
    "bar_count": <int>,
    "bars": [
      {"ts": <float>, "o": <float>, "h": <float>, "l": <float>,
       "c": <float>, "vol": <int>, "poc_vol": <int>,
       "vah": <float>, "val": <float>, "cumulative_delta": <float>}
    ]
  }

Note: 5-min bar data is currently part of the main mes_ai_data.json
export. A dedicated 5min.json DLL export needs to be added, or
this stream should be adapted to parse the relevant section from
mes_ai_data.json.
"""

from .base_stream import BaseV9Stream


class Bars5MinStream(BaseV9Stream):
    name = "bars_5min"
    filename = "5min.json"
    redis_key = "mems26:v9:bars_5min"
    api_path = "/api/v9/bars/5min"
