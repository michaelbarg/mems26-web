"""TS_OFFSET_INGEST_GATE_V1 — 2026-07-20 loop-closure (Michael approved).

Incident: the morning backend wrote the whole RTH session -1h; the offset sat
below _hour_shift_fix's tight 3600±120s window so the batch was neither shifted
nor rejected → wrong first-12-bars IB → S1 IB-sanity replaced the CORRECT
Sierra IB → false Neutral_Extreme label from 13:40 ET.

The gate: a feed whose newest bar-ts ADVANCES (live) while staying more than
TS_OFFSET_REJECT_SEC behind server-now is live-but-mislabeled → REJECT the
batch honestly (no guessed shift). Paused/idempotent re-push (newest ts
unchanged) always passes. Flag default OFF.

Anti-tautological: drives the real _ts_offset_ingest_gate with real clock math.
"""
import time

import backend.v9.api.v9.bars as bars_mod


def _bars(newest_epoch):
    return [{"ts": newest_epoch - 300}, {"ts": newest_epoch}]


def _reset():
    bars_mod._ts_gate_last_newest.clear()


def test_flag_off_by_default_never_rejects(monkeypatch):
    monkeypatch.delenv("TS_OFFSET_INGEST_GATE_V1", raising=False)
    _reset()
    now = time.time()
    # even a blatant -1h live-advancing feed passes when the flag is OFF
    assert bars_mod._ts_offset_ingest_gate(_bars(now - 3600), "t") is None
    assert bars_mod._ts_offset_ingest_gate(_bars(now - 3300), "t") is None


def test_fresh_feed_passes(monkeypatch):
    monkeypatch.setenv("TS_OFFSET_INGEST_GATE_V1", "1")
    _reset()
    now = time.time()
    assert bars_mod._ts_offset_ingest_gate(_bars(now - 60), "t") is None
    assert bars_mod._ts_offset_ingest_gate(_bars(now - 30), "t") is None


def test_live_but_mislabeled_rejected(monkeypatch):
    """The 07-20 class: ts advances push-to-push but sits ~1h behind now."""
    monkeypatch.setenv("TS_OFFSET_INGEST_GATE_V1", "1")
    _reset()
    now = time.time()
    assert bars_mod._ts_offset_ingest_gate(_bars(now - 3600), "t") is None  # first push: no baseline
    reason = bars_mod._ts_offset_ingest_gate(_bars(now - 3300), "t")
    assert reason is not None and "live-but-mislabeled" in reason


def test_paused_market_repush_passes(monkeypatch):
    """Old bars re-pushed with UNCHANGED newest ts (weekend/idempotent) pass."""
    monkeypatch.setenv("TS_OFFSET_INGEST_GATE_V1", "1")
    _reset()
    now = time.time()
    old = now - 7200
    assert bars_mod._ts_offset_ingest_gate(_bars(old), "t") is None
    assert bars_mod._ts_offset_ingest_gate(_bars(old), "t") is None  # same newest → pass
    assert bars_mod._ts_offset_ingest_gate(_bars(old), "t") is None


def test_threshold_env_respected(monkeypatch):
    monkeypatch.setenv("TS_OFFSET_INGEST_GATE_V1", "1")
    monkeypatch.setenv("TS_OFFSET_REJECT_SEC", "10000")
    _reset()
    now = time.time()
    bars_mod._ts_offset_ingest_gate(_bars(now - 3600), "t")
    assert bars_mod._ts_offset_ingest_gate(_bars(now - 3300), "t") is None  # under 10000s → pass


def test_streams_isolated(monkeypatch):
    monkeypatch.setenv("TS_OFFSET_INGEST_GATE_V1", "1")
    _reset()
    now = time.time()
    bars_mod._ts_offset_ingest_gate(_bars(now - 3600), "a")
    # advancing mislabeled on stream a; stream b has no baseline yet → passes
    assert bars_mod._ts_offset_ingest_gate(_bars(now - 3300), "b") is None
    assert bars_mod._ts_offset_ingest_gate(_bars(now - 3200), "a") is not None


# ═══ P2 (2026-07-22): hour-fix default OFF + gate ordering ═══

def test_hour_fix_default_off(monkeypatch):
    """P2: WOODIES_TS_HOUR_FIX defaults to 0 — no shifting."""
    monkeypatch.delenv("WOODIES_TS_HOUR_FIX", raising=False)
    now = time.time()
    bars_in = [{"ts": now - 3600}]  # exactly 1h old — the old trigger zone
    shift = bars_mod._hour_shift_fix(bars_in, "test")
    assert shift == 0
    assert abs(bars_in[0]["ts"] - (now - 3600)) < 1  # ts unchanged


def test_hour_fix_on_when_explicitly_enabled(monkeypatch):
    """When WOODIES_TS_HOUR_FIX=1, the fix still works for genuine chartbook TZ."""
    monkeypatch.setenv("WOODIES_TS_HOUR_FIX", "1")
    now = time.time()
    bars_in = [{"ts": now - 3600}]
    shift = bars_mod._hour_shift_fix(bars_in, "test")
    assert shift == 3600
    assert abs(bars_in[0]["ts"] - now) < 2  # ts shifted forward
