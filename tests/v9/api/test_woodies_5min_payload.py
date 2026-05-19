from backend.v9.api.v9.bars import Woodies5MinPayload


def test_woodies_5min_payload_accepts_current_bar_only():
    payload = Woodies5MinPayload(
        type="woodies_5min",
        current_bar={"ts": "2026-05-18 10:00:00", "cci_14": 12.3, "trend_state": "BLUE"},
    )
    bars = payload.all_bars
    assert len(bars) == 1
    assert bars[0]["cci_14"] == 12.3


def test_woodies_5min_payload_prefers_explicit_bars():
    payload = Woodies5MinPayload(
        type="woodies_5min",
        bars=[{"ts": "2026-05-18 09:55:00"}],
        current_bar={"ts": "2026-05-18 10:00:00"},
    )
    assert len(payload.all_bars) == 1
    assert payload.all_bars[0]["ts"] == "2026-05-18 09:55:00"
