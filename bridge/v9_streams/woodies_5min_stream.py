"""V9 stream: Woodies 5-min CCI bars (System 4) — per D-074.

Source: DLL exports woodies_5min.json with same fields as legacy 30-min
but computed on 5-minute bars:
  - type: "woodies_5min"
  - export_ts: unix timestamp
  - bar_count: int
  - history: [
      {ts, o, h, l, c, vol, cci_14, cci_6_tcci, lsma_value,
       swi_value, czi_value, ema_34, trend_state,
       predictor_next_cci, zlr_detected, zlr_direction}
    ]

Supersedes: woodies_30min_stream.py (legacy — kept for replay only)
Decision: D-074 LOCKED 2026-05-16
"""

from .base_stream import BaseV9Stream


class Woodies5MinStream(BaseV9Stream):
    name = "woodies_5min"
    filename = "woodies_5min.json"
    redis_key = "mems26:v9:woodies_5min"
    api_path = "/api/v9/bars/woodies_5min"
