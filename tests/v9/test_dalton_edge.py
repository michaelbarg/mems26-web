"""DALTON_EDGE_V1 tests (T-118, Michael ruling a65f13aa 2026-08-28).

Pure-detector tests + a real-bar acceptance fixture (frozen from
v9_bars_5min_woodies, psql 2026-08-28 — the 09:00-IL specimen Michael marked
on IMG_3305) + wiring-harness tests for the flag modes (OFF byte-identical /
shadow / live) on FiveMinSystem._maybe_dalton_edge.

Env discipline: every harness test pins/clears ALL DALTON_EDGE_* env vars via
monkeypatch (known env-bleed failure class — ruled-ON flags leak into pytest).
The detector itself is pure (no env, no I/O) so its tests need no pinning.
"""
import time as _time

import pytest

from backend.v9.systems.dalton_edge import (
    build_dalton_edge_setup,
    detect_dalton_edge,
)

_ENV_KEYS = (
    "DALTON_EDGE_V1",
    "DALTON_EDGE_LOOKBACK_N",
    "DALTON_EDGE_VOL_MULT",
    "DALTON_EDGE_STOP_BUFFER_PTS",
)


def _pin_env(monkeypatch, **values):
    for k in _ENV_KEYS:
        monkeypatch.delenv(k, raising=False)
    for k, v in values.items():
        monkeypatch.setenv(k, v)


def _quiet(n=24, o=100.0, h=101.0, l=99.0, c=100.0, v=400):
    return [{"o": o, "h": h, "l": l, "c": c, "v": v} for _ in range(n)]


# ── REAL-BAR ACCEPTANCE FIXTURE ─────────────────────────────────────────────
# v9_bars_5min_woodies, 2026-08-28 06:40→09:00 IL (03:40→06:00 UTC), frozen
# from psql on 2026-08-28 (Rule-2 verified: low 7731.00 / close 7734.00 /
# volume 885 match Michael's chart; preceding SMA20 = 382.45 → ratio 2.31).
# (il_hhmm, o, h, l, c, v)
REAL_BARS_0828 = [
    ("06:40", 7742.50, 7742.50, 7739.00, 7739.25, 1325),
    ("06:45", 7739.00, 7741.75, 7738.00, 7741.25, 1438),
    ("06:50", 7741.25, 7742.25, 7740.25, 7741.75, 542),
    ("06:55", 7741.75, 7742.25, 7741.00, 7741.50, 426),
    ("07:00", 7741.25, 7741.50, 7738.50, 7739.00, 646),
    ("07:05", 7739.00, 7739.25, 7738.25, 7738.50, 419),
    ("07:10", 7738.75, 7741.00, 7738.50, 7740.25, 314),
    ("07:15", 7740.25, 7741.25, 7740.00, 7740.50, 387),
    ("07:20", 7740.25, 7740.75, 7739.75, 7739.75, 235),
    ("07:25", 7739.75, 7740.25, 7739.25, 7739.75, 151),
    ("07:30", 7740.00, 7740.00, 7738.25, 7738.25, 194),
    ("07:35", 7738.50, 7739.00, 7737.75, 7738.75, 363),
    ("07:40", 7738.50, 7739.00, 7737.50, 7738.25, 320),
    ("07:45", 7738.25, 7738.75, 7738.00, 7738.25, 205),
    ("07:50", 7738.00, 7738.25, 7737.50, 7737.75, 246),
    ("07:55", 7737.75, 7737.75, 7736.75, 7737.75, 346),
    ("08:00", 7737.75, 7738.00, 7736.25, 7737.50, 518),
    ("08:05", 7737.25, 7737.50, 7736.00, 7736.50, 328),
    ("08:10", 7736.75, 7736.75, 7735.50, 7735.75, 547),
    ("08:15", 7735.75, 7736.25, 7735.50, 7735.50, 147),
    ("08:20", 7735.50, 7736.00, 7734.25, 7735.50, 592),
    ("08:25", 7735.50, 7735.75, 7734.00, 7735.00, 550),
    ("08:30", 7735.25, 7735.50, 7734.25, 7735.00, 498),
    ("08:35", 7735.00, 7735.25, 7732.00, 7733.25, 1107),
    ("08:40", 7733.25, 7734.25, 7733.00, 7734.25, 297),
    ("08:45", 7734.00, 7734.25, 7732.50, 7733.00, 233),
    ("08:50", 7733.00, 7733.50, 7731.50, 7733.00, 528),
    ("08:55", 7733.00, 7733.25, 7731.50, 7732.00, 244),
    ("09:00", 7731.50, 7734.50, 7731.00, 7734.00, 885),
]


def _real_bars(upto_hhmm):
    out = []
    for hhmm, o, h, l, c, v in REAL_BARS_0828:
        out.append({"o": o, "h": h, "l": l, "c": c, "v": v})
        if hhmm == upto_hhmm:
            break
    return out


def test_acceptance_real_0900_bar_long():
    """The 09:00-IL specimen Michael marked MUST detect LONG with defaults."""
    trig = detect_dalton_edge(_real_bars("09:00"))
    assert trig is not None
    assert trig["type"] == "DALTON_EDGE_LONG"
    assert trig["direction"] == "LONG"
    assert trig["entry"] == 7734.00           # rejection close
    assert trig["extreme"] == 7731.00         # the session low he marked
    assert trig["stop"] == 7729.00            # extreme - 2.0 buffer
    assert trig["volume"] == 885
    assert trig["vol_sma20"] == 382.45        # preceding 20 bars
    assert trig["vol_ratio"] == 2.31          # crossed the dashed line (>=2.0)


def test_acceptance_real_0835_flush_bar_rejected():
    """08:35 (v=1107, new low 7732) passed volume+termination but closed only
    38% up the bar — no rejection close → correctly None (real-data negative)."""
    assert detect_dalton_edge(_real_bars("08:35")) is None


def test_synthetic_long():
    bars = _quiet(24) + [{"o": 99.0, "h": 102.0, "l": 96.0, "c": 101.0, "v": 900}]
    trig = detect_dalton_edge(bars)
    assert trig is not None
    assert trig["type"] == "DALTON_EDGE_LONG"
    assert trig["entry"] == 101.0
    assert trig["stop"] == 94.0               # 96 - 2.0
    assert trig["vol_sma20"] == 400.0


def test_synthetic_short():
    bars = _quiet(24) + [{"o": 101.0, "h": 104.0, "l": 98.0, "c": 99.0, "v": 900}]
    trig = detect_dalton_edge(bars)
    assert trig is not None
    assert trig["type"] == "DALTON_EDGE_SHORT"
    assert trig["entry"] == 99.0
    assert trig["stop"] == 106.0              # 104 + 2.0


def test_volume_fail_none():
    """Same LONG geometry, volume below 2x SMA20 → None."""
    bars = _quiet(24) + [{"o": 99.0, "h": 102.0, "l": 96.0, "c": 101.0, "v": 700}]
    assert detect_dalton_edge(bars) is None


def test_rejection_fail_none():
    """New low + volume spike but close in the lower 60% of the bar → None."""
    bars = _quiet(24) + [{"o": 99.0, "h": 100.5, "l": 96.0, "c": 97.0, "v": 900}]
    assert detect_dalton_edge(bars) is None


def test_not_lowest_low_none():
    """A lower low inside the lookback window → not a termination → None."""
    bars = _quiet(24)
    bars[-6] = {"o": 100.0, "h": 101.0, "l": 97.0, "c": 100.0, "v": 400}
    bars.append({"o": 100.0, "h": 101.0, "l": 98.5, "c": 100.9, "v": 900})
    assert detect_dalton_edge(bars) is None


def test_equal_low_retest_counts():
    """Equal-low retest (double-bottom excess) is a valid termination."""
    bars = _quiet(24) + [{"o": 100.0, "h": 101.0, "l": 99.0, "c": 100.5, "v": 900}]
    trig = detect_dalton_edge(bars)
    assert trig is not None and trig["type"] == "DALTON_EDGE_LONG"


def test_tiny_range_none():
    """range < 2.0 pts sanity → None even with volume + new low."""
    bars = _quiet(24) + [{"o": 100.0, "h": 100.3, "l": 98.9, "c": 100.2, "v": 900}]
    assert detect_dalton_edge(bars) is None


def test_too_few_bars_none():
    bars = _quiet(19) + [{"o": 99.0, "h": 102.0, "l": 96.0, "c": 101.0, "v": 900}]
    assert detect_dalton_edge(bars) is None    # 20 < SMA20+1


def test_already_fired_blocks():
    bars = _quiet(24) + [{"o": 99.0, "h": 102.0, "l": 96.0, "c": 101.0, "v": 900}]
    assert detect_dalton_edge(bars, already_fired={"DALTON_EDGE_LONG"}) is None


def test_cfg_vol_mult_tunable():
    """vol_mult=2.5 makes the 2.25x specimen fail; 2.0 default passes."""
    bars = _quiet(24) + [{"o": 99.0, "h": 102.0, "l": 96.0, "c": 101.0, "v": 900}]
    assert detect_dalton_edge(bars, {"vol_mult": 2.5}) is None
    assert detect_dalton_edge(bars, {"vol_mult": 2.0}) is not None


def test_build_setup_live_and_shadow():
    trig = {"type": "DALTON_EDGE_LONG", "direction": "LONG", "entry": 7734.0,
            "stop": 7729.0, "extreme": 7731.0, "volume": 885,
            "vol_sma20": 382.45, "vol_ratio": 2.31, "lookback_n": 12}
    setup = build_dalton_edge_setup(trig, contracts=2)
    assert setup["firing_system"] == 2
    assert setup["pattern"] == "DALTON_EDGE_LONG"
    assert setup["classification"] == "DALTON_EDGE_LONG"
    assert setup["entry_price"] == 7734.0
    assert setup["stop"] == 7729.0            # → metadata.stop_initial (manager)
    assert setup["t1"] == 7739.0              # 1R near bank
    assert setup["t2"] == 7744.0              # 2R
    assert setup["t3"] is None
    assert setup["contracts"] == 2
    assert "shadow_only" not in setup["metadata"]          # live-capable
    shadow = build_dalton_edge_setup(trig, contracts=2, shadow_only=True)
    assert shadow["metadata"]["shadow_only"] is True       # FAILED_BREAK precedent


# ── wiring harness: FiveMinSystem._maybe_dalton_edge flag modes ────────────

class _GatewayRecorder:
    def __init__(self):
        self.calls = []

    def route_setup(self, setup, system_id):
        self.calls.append((setup, system_id))


def _fresh_rows(last_age_s=60):
    """Synthetic-LONG scenario as DB-shaped rows (ets/o/h/l/c/v), newest fresh."""
    bars = _quiet(24) + [{"o": 99.0, "h": 102.0, "l": 96.0, "c": 101.0, "v": 900}]
    now = _time.time()
    rows = []
    for i, b in enumerate(bars):
        rows.append({"ets": now - last_age_s - (len(bars) - 1 - i) * 300.0, **b})
    return rows


def _make_system(monkeypatch, rows):
    from backend.v9.systems.five_min.five_min_system import FiveMinSystem
    sys_obj = FiveMinSystem.__new__(FiveMinSystem)   # skip heavy __init__
    sys_obj._gateway = _GatewayRecorder()
    import backend.v9.db.read as _read_mod
    # honor the wiring's SQL contract: ORDER BY ts DESC (newest first)
    monkeypatch.setattr(
        _read_mod, "read_all",
        lambda sql, params=None: list(reversed(rows)))
    import backend.v9.services.contract_size as _cs_mod
    monkeypatch.setattr(_cs_mod, "ruled_contracts", lambda: 2)
    return sys_obj


def test_wiring_flag_unset_off_byte_identical(monkeypatch):
    """Unset flag → immediate return: no DB read, no route_setup."""
    _pin_env(monkeypatch)

    def _boom(sql, params=None):
        raise AssertionError("DB read must not happen when flag unset")

    from backend.v9.systems.five_min.five_min_system import FiveMinSystem
    sys_obj = FiveMinSystem.__new__(FiveMinSystem)
    sys_obj._gateway = _GatewayRecorder()
    import backend.v9.db.read as _read_mod
    monkeypatch.setattr(_read_mod, "read_all", _boom)
    sys_obj._maybe_dalton_edge()
    assert sys_obj._gateway.calls == []

    _pin_env(monkeypatch, DALTON_EDGE_V1="0")      # explicit "0" → same OFF
    sys_obj._maybe_dalton_edge()
    assert sys_obj._gateway.calls == []


def test_wiring_shadow_emits_shadow_only(monkeypatch):
    _pin_env(monkeypatch, DALTON_EDGE_V1="shadow")
    sys_obj = _make_system(monkeypatch, _fresh_rows())
    sys_obj._maybe_dalton_edge()
    assert len(sys_obj._gateway.calls) == 1
    setup, system_id = sys_obj._gateway.calls[0]
    assert system_id == 2
    assert setup["pattern"] == "DALTON_EDGE_LONG"
    assert setup["metadata"]["shadow_only"] is True
    assert setup["contracts"] == 2                 # ruled_contracts, not .env


def test_wiring_live_no_shadow_marker(monkeypatch):
    _pin_env(monkeypatch, DALTON_EDGE_V1="1")
    sys_obj = _make_system(monkeypatch, _fresh_rows())
    sys_obj._maybe_dalton_edge()
    assert len(sys_obj._gateway.calls) == 1
    setup, _ = sys_obj._gateway.calls[0]
    assert "shadow_only" not in setup["metadata"]


def test_wiring_stale_rows_anti_phantom(monkeypatch):
    """Newest closed bar older than 10 min → no signal (replay/hydration)."""
    _pin_env(monkeypatch, DALTON_EDGE_V1="1")
    sys_obj = _make_system(monkeypatch, _fresh_rows(last_age_s=700))
    sys_obj._maybe_dalton_edge()
    assert sys_obj._gateway.calls == []


def test_wiring_one_per_side_per_day(monkeypatch):
    _pin_env(monkeypatch, DALTON_EDGE_V1="shadow")
    sys_obj = _make_system(monkeypatch, _fresh_rows())
    sys_obj._maybe_dalton_edge()
    sys_obj._maybe_dalton_edge()                   # same bar/day again
    assert len(sys_obj._gateway.calls) == 1


def test_wiring_vol_mult_env_tunable(monkeypatch):
    """DALTON_EDGE_VOL_MULT=2.5 read at the wiring layer suppresses the 2.25x fire."""
    _pin_env(monkeypatch, DALTON_EDGE_V1="shadow", DALTON_EDGE_VOL_MULT="2.5")
    sys_obj = _make_system(monkeypatch, _fresh_rows())
    sys_obj._maybe_dalton_edge()
    assert sys_obj._gateway.calls == []
