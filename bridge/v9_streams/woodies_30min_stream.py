"""V9 stream: Woodies 30-min CCI bars (System 4).

Source: DLL exports woodies_30min.json with fields:
  - type: "woodies_30min"
  - export_ts: unix timestamp
  - bar_count: int
  - history: [  <-- note: key is "history", not "bars"
      {ts, o, h, l, c, vol, cci_14, cci_6_tcci, lsma_value,
       swi_value, czi_value, ema_34, trend_state,
       predictor_next_cci, zlr_detected, zlr_direction}
    ]
"""

from .base_stream import BaseV9Stream


class Woodies30MinStream(BaseV9Stream):
    name = "woodies_30min"
    filename = "woodies_30min.json"
    redis_key = "mems26:v9:woodies"
    api_path = "/api/v9/bars/woodies"
