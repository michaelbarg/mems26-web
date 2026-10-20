"""T-617 (Michael 20.10: "for each losing trade — entry location, System 6, T1").

(a) TOUCH2_EDGE_TOL_MAX_ATR — the TOUCH2 edge tolerance is max(0.15×ATR, 0.15×IB); on 20.10
    the IB was 75.75 pt ⇒ 11.4 pt, so the 19:20/19:25 double bottom 7751–7752.75 (8–9.5 pt above
    the VAL 7743.25, zone=mid_value) fired LONG (#3572 cancelled, #3574 −165$, and the same
    shape again at 20:00/20:05: #3580 cancelled, #3582 −90$). The cap keeps normal-IB days as is.
(b) System 6 t0_hit wiring — T-368 S6_STUCK_TO_BE_V1 (ruled 16.09, ON) needs t0_hit, which the
    bar_level_detector call site never passed (#3582: stuck_trade ALERT 21:35, T0 banked 20:17,
    no BE move, stopped 21:42).
"""
import os
import pathlib
from unittest.mock import patch

from backend.v9.systems.ceiling_touch2 import detect_touch2, touch2_edge_tol_cap_k
from backend.v9.systems.system6_supervisor import diagnose_trade, AUTO

ROOT = pathlib.Path(__file__).resolve().parents[3]

# 20.10 RTH 5-min bars (IL time label, o, h, l, c) — v9_bars_5min_woodies
_B = [
    ("18:15", 7757.0, 7768.5, 7754.75, 7766.5), ("18:20", 7766.25, 7767.75, 7758.25, 7761.5),
    ("18:25", 7761.75, 7763.5, 7757.75, 7760.0), ("18:30", 7760.25, 7761.25, 7753.0, 7758.0),
    ("18:35", 7758.0, 7758.75, 7752.75, 7757.0), ("18:40", 7756.75, 7767.0, 7756.75, 7763.5),
    ("18:45", 7763.25, 7764.0, 7757.0, 7761.25), ("18:50", 7761.0, 7767.75, 7757.25, 7767.75),
    ("18:55", 7767.75, 7768.5, 7763.0, 7767.0), ("19:00", 7767.0, 7768.5, 7759.25, 7760.0),
    ("19:05", 7760.0, 7766.25, 7759.5, 7762.0), ("19:10", 7762.0, 7762.5, 7756.75, 7760.5),
    ("19:15", 7760.5, 7762.25, 7751.25, 7752.75), ("19:20", 7752.75, 7757.25, 7751.0, 7755.0),
    ("19:25", 7755.0, 7761.75, 7752.75, 7759.5),
]
# the levels the 19:25/19:30 fires saw (situation of #3572/#3574)
LV_2010 = {"vah": 7781.75, "val": 7743.25, "session_high": 7791.5, "session_low": 7710.25,
           "ib_high": 7786.0, "ib_low": 7710.25}
IB_2010 = 7786.0 - 7710.25          # 75.75
ATR = 7.9


def _bars(upto):
    out = []
    for t, o, h, l, c in _B:
        out.append({"ts": "2026-10-20 " + t, "o": o, "h": h, "l": l, "c": c})
        if t == upto:
            break
    return out


def _env(**kv):
    base = {k: v for k, v in os.environ.items() if k != "TOUCH2_EDGE_TOL_MAX_ATR"}
    base.update(kv)
    return patch.dict(os.environ, base, clear=True)


# ── (a) TOUCH2 edge-tolerance cap ───────────────────────────────────────────────

def test_cap_parse():
    with _env():
        assert touch2_edge_tol_cap_k() == 0.0
    for raw, want in (("0.5", 0.5), ("", 0.0), ("0", 0.0), ("-1", 0.0), ("abc", 0.0), (" 0.75 ", 0.75)):
        with _env(TOUCH2_EDGE_TOL_MAX_ATR=raw):
            assert touch2_edge_tol_cap_k() == want, raw


def test_3574_fires_without_cap_byte_identical_default():
    with _env():
        r = detect_touch2(_bars("19:25"), LV_2010, atr=ATR, ib_width=IB_2010)
    assert r is not None and r["state"] == "FLOOR_TOUCH2_REJECT"
    assert (r["p1"], r["p2"], r["edge"], r["edge_source"]) == (7751.0, 7752.75, 7743.25, "VAH")
    assert r["confirm_close"] == 7759.5


def test_3572_fires_without_cap():
    with _env():
        r = detect_touch2(_bars("19:20"), LV_2010, atr=ATR, ib_width=IB_2010)
    assert r is not None and (r["p1"], r["p2"]) == (7751.25, 7751.0)


def test_cap_blocks_the_mid_value_touches_on_the_wide_ib():
    with _env(TOUCH2_EDGE_TOL_MAX_ATR="0.5"):
        assert detect_touch2(_bars("19:25"), LV_2010, atr=ATR, ib_width=IB_2010) is None
        assert detect_touch2(_bars("19:20"), LV_2010, atr=ATR, ib_width=IB_2010) is None


def test_cap_leaves_a_normal_ib_unchanged():
    # IB 20 pt ⇒ edge_tol = 0.15×20 = 3.0 < 0.5×ATR = 3.95 ⇒ the cap does not bind
    lv = {"vah": 7790.0, "val": 7750.0, "session_high": 7791.5, "session_low": 7740.0,
          "ib_high": 7770.0, "ib_low": 7750.0}
    with _env():
        a = detect_touch2(_bars("19:25"), lv, atr=ATR, ib_width=20.0)
    with _env(TOUCH2_EDGE_TOL_MAX_ATR="0.5"):
        b = detect_touch2(_bars("19:25"), lv, atr=ATR, ib_width=20.0)
    assert a is not None and b is not None and a == b


def test_cap_never_goes_below_the_atr_term():
    # k tiny (0.01×ATR = 0.08) ⇒ the tolerance is still edge_tol_atr×ATR = 0.15×7.9 = 1.185
    with _env(TOUCH2_EDGE_TOL_MAX_ATR="0.01"):
        # touch-2 low 7752.75 is 1.0 above the edge ⇒ inside 1.185 ⇒ fires
        assert detect_touch2(_bars("19:25"), dict(LV_2010, val=7751.75), atr=ATR, ib_width=IB_2010) is not None
        # 1.5 above ⇒ outside 1.185 ⇒ no fire
        assert detect_touch2(_bars("19:25"), dict(LV_2010, val=7751.25), atr=ATR, ib_width=IB_2010) is None


# ── (b) System 6 t0_hit wiring ─────────────────────────────────────────────────

def test_t0_hit_reader():
    from backend.v9.services.trade_manager.bar_level_detector import t617_t0_hit
    seen = {}

    def read(sql, params):
        seen["sql"], seen["params"] = sql, params
        return [{"x": 1}]
    assert t617_t0_hit(3582, read) is True
    assert "v9_trade_management_log" in seen["sql"] and "T0_HIT" in seen["sql"]
    assert seen["params"] == {"tid": 3582}
    assert t617_t0_hit(3582, lambda s, p: []) is False
    assert t617_t0_hit(None, read) is False

    def boom(s, p):
        raise RuntimeError("db down")
    assert t617_t0_hit(3582, boom) is False


def test_call_site_passes_t0_hit():
    src = (ROOT / "backend/v9/services/trade_manager/bar_level_detector.py").read_text(encoding="utf-8")
    call = src[src.index("scan_active_trade(\n                trade=_t,"):]
    call = call[:call.index("\n            )\n")]      # the call's own closing paren
    assert "t0_hit=_s6_t0_hit" in call
    assert "_s6_t0_hit = t617_t0_hit(" in src


@patch.dict(os.environ, {"S6_STUCK_TO_BE_V1": "1"})
def test_3582_stuck_with_t0_moves_stop_to_be():
    trade = {"direction": "LONG", "entry_price": 7754.5, "stop": 7749.25, "contracts": 4,
             "t1": 7768.5, "t2": 7770.25, "t3": 7780.75}
    rep = diagnose_trade(trade=trade, atr=7.4, bars_since_entry=17, progress_pts=1.25, t0_hit=True)
    auto = [i for i in rep.issues if i.code == "stuck_trade_to_be"]
    assert len(auto) == 1 and auto[0].action == AUTO
    assert auto[0].correction == {"op": "MODIFY_STOP", "price": 7754.5}
    # what the live loop actually produced on 20.10 (t0_hit never passed ⇒ False): ALERT only
    trade2 = dict(trade)
    rep2 = diagnose_trade(trade=trade2, atr=7.4, bars_since_entry=17, progress_pts=1.25)
    assert not [i for i in rep2.issues if i.code == "stuck_trade_to_be"]
    assert [i for i in rep2.issues if i.code == "stuck_trade"]
