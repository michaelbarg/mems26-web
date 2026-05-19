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

    def _push_api(self, data: dict):
        """Live 5min export contains full history; push only the latest bar.

        Full-history ingestion is handled by historical_load()/--history-only.
        During live polling Sierra rewrites 5min.json every few seconds with
        hundreds of bars, and re-posting the whole file can saturate backend.
        """
        bars = data.get("bars")
        if isinstance(bars, list) and bars:
            latest_only = dict(data)
            latest_only["bars"] = [bars[-1]]
            return super()._push_api(latest_only)
        return super()._push_api(data)
