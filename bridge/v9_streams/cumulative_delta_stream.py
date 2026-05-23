"""V9 stream: Cumulative Delta (running delta with divergence detection)."""

from . import base_stream as _bs
from .base_stream import BaseV9Stream


class CumulativeDeltaStream(BaseV9Stream):
    name = "cumulative_delta"
    filename = "cumulative_delta.json"
    redis_key = "mems26:v9:cumulative_delta"
    api_path = "/api/v9/bars/cumulative_delta"

    # P31 §A — same Chicago-wall-clock-as-UTC DLL bug as §9, but the field
    # name differs: bars use `ts`, CVD points use `t`. The base class only
    # rewrites `ts` keys, so we override `_fix_chicago_bar_ts` to also
    # touch each `points[].t`. Without this fix, CVD points stay ~5h behind
    # real UTC, the frontend's heuristic (4h/5h diff detection) sees an
    # ~9h gap (price bar time was already shifted +4h by the EDT parse in
    # `tsToUnix`) and gives up — so CVD candles render far to the LEFT of
    # the price candles on the shared chart timeScale. Set
    # `V9_DISABLE_CHICAGO_TS_FIX=1` in env to disable when the DLL canonical
    # fix (§9 Option A) ships.
    def _fix_chicago_bar_ts(self, data: dict) -> dict:
        data = super()._fix_chicago_bar_ts(data)
        # Honour the same kill-switch as the base class so the DLL canonical
        # fix (§9 Option A) can ship without bridge churn.
        if _bs._DISABLE_CHICAGO_TS_FIX or not isinstance(data, dict):
            return data
        try:
            pts = data.get("points")
            if isinstance(pts, list):
                for pt in pts:
                    if isinstance(pt, dict) and "t" in pt:
                        pt["t"] = self._chicago_to_utc(pt["t"])
        except Exception:  # never crash a live stream on a TS bug
            # logged downstream by base class semantics
            pass
        return data
