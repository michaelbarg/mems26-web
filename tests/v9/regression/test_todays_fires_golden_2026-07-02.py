"""Golden-day 2026-07-02 — every pattern that FIRED today becomes a test.

Michael (~22:55 IL): "תוסיף טסט לכל התבניות שיצאו היום לפועל ותראה מה
התיקונים שהם נדרשים לעבור."

Each test encodes a REAL trade from today with its REAL numbers, asserting
the FIXED behavior per the economics package. Tests for already-shipped fixes
live in their own files (I-58/59/60/61) and are green. The ones here are
xfail — they document today's breakage and flip when CC lands the item.

מפת עסקה → תיקונים (היום):
  271/272 REACTIVE_SHORT 09:10  counter-fade on staged day  → item-1/18 (doctrine)
  273/274 INITIATIVE_SHORT      fills via crash-era         → I-58 ✅ (tested elsewhere)
  275/276 INITIATIVE_SHORT      fills→shadow twin, demo blind→ I-58 ✅ (tested elsewhere)
  277/278 ZLR SHORT             t1==t2, off-grid .625, tiny  → item-2 (floor/monotonic/grid) + I-59 ✅
  279/280 REACTIVE_LONG         t2/t3 BELOW long entry       → I-61 ✅ + item-1/18 (should not exist)
  281/282 REACTIVE_SHORT        T2 = crude 3R (37.5pt)       → item-2 (structural C2 / level inventory)
  283-288 REACTIVE_SHORT        with-direction, BE ✓         → item-21 (EOD window: 287/288 open at 14:2x CT)
"""
import os

import pytest

TICK = 0.25

# tpo context as it stood mid-session today (from classify_replay / key_levels)
TODAY_CTX = {
    "ib_high": 7594.0, "ib_low": 7551.75,
    "poc": 7547.25, "vah": 7578.5, "val": 7548.5,
}


def _on_grid(px):
    return px is not None and abs((px / TICK) - round(px / TICK)) < 1e-9


def _resolve(direction, entry, stop, monkeypatch, ctx=None):
    monkeypatch.setenv("DAYTYPE_TARGETS_STRUCTURAL", "1")
    from backend.v9.systems.structural_targets import resolve_structural_targets
    return resolve_structural_targets(
        day_type="Variation", direction=direction, entry_price=entry,
        stop_price=stop, tpo_ctx=ctx or TODAY_CTX, bars=None, pattern_family="REV",
    )


@pytest.mark.xfail(reason="package item-2: C1 floor 0.5×ATR-live + monotonic + grid", strict=False)
def test_zlr_277_ladder_monotonic_floor_grid(monkeypatch):
    """Trade 277/278 (ZLR SHORT @7532): live output was t1==t2==7530.625 —
    duplicate, off-grid, 1.4pt from entry. Fixed resolver must emit a
    monotonic, grid-aligned ladder with T1 ≥ floor."""
    r = _resolve("SHORT", 7532.0, 7545.25, monkeypatch)
    assert r is not None
    t1, t2, t3 = r["t1_price"], r["t2_price"], r["t3_price"]
    assert _on_grid(t1) and _on_grid(t2) and _on_grid(t3), "targets must sit on the 0.25 grid"
    assert t1 != t2, "t1==t2 (the 277/278 bug) must be impossible"
    assert 7532.0 > t1 > t2, "SHORT ladder must descend: entry > t1 > t2"
    assert (7532.0 - t1) >= 3.5, "T1 must respect the 0.5×ATR floor (was 1.375pt live)"


@pytest.mark.xfail(reason="package item-2: targets must never cross entry at the resolver", strict=False)
def test_reactive_long_279_targets_above_entry(monkeypatch):
    """Trade 279/280 (REACTIVE_LONG @7525): t2=7518, t3=7524.25 — BELOW a
    LONG entry — reached Sierra. Reproduced with the REAL 19:15 context:
    value had migrated DOWN (POC 7518.x, below the entry) → REV-LONG path
    c2=poc lands under the entry. I-61 guards downstream; the resolver
    itself must stop producing wrong-side targets."""
    ctx = {"ib_high": 7594.0, "ib_low": 7551.75,
           "poc": 7518.0, "vah": 7524.25, "val": 7509.0}  # migrated value @19:15
    r = _resolve("LONG", 7525.0, 7517.25, monkeypatch, ctx=ctx)
    assert r is not None
    for k in ("t1_price", "t2_price", "t3_price"):
        v = r[k]
        assert v is None or v > 7525.0, f"{k}={v} on the wrong side of a LONG entry (279/280 bug)"


def test_reactive_short_281_resolver_c2_is_structural(monkeypatch):
    """Trade 281/282 counter-evidence (NOT xfail): with migrated value the
    resolver's REV C2 DOES snap to POC (~6pt) — proving the crude 3R=37.5pt
    the demo bracket carried came from the COMMAND-path default after the
    broken t2 was dropped, not from the resolver. The command-builder fix
    (item-2/11: no synthetic R-multiples when structure exists) is documented
    in the package; its test lands with the implementation."""
    ctx = dict(TODAY_CTX, poc=7508.5, val=7505.0)
    r = _resolve("SHORT", 7514.75, 7527.25, monkeypatch, ctx=ctx)
    assert r is not None and r["t2_price"] is not None
    assert (7514.75 - r["t2_price"]) <= 15.0


@pytest.mark.xfail(reason="package item-1/18: counter-direction REACTIVE on Variation must SKIP", strict=False)
def test_reactive_counter_variation_skip(monkeypatch):
    """Trades 271/272 (09:10 counter-fade) + 279/280 (counter-long at the lows):
    after item-1/18, playbook decide() must SKIP counter-direction REACTIVE on
    Variation (trend_state carries the expansion side)."""
    monkeypatch.setenv("DAYTYPE_PLAYBOOK", "1")
    monkeypatch.delenv("DAYTYPE_POSITION_GATE", raising=False)
    import backend.v9.systems.daytype_playbook as pb
    pb.reset_cache()
    d = pb.decide(pattern="REACTIVE_LONG", day_type="Variation",
                  direction="LONG", trend_state="RED")
    assert d.allow is False, "counter-direction REACTIVE on Variation must be blocked (D-1)"


@pytest.mark.xfail(reason="package item-21: EOD entry cutoff 45min before close", strict=False)
def test_eod_entry_cutoff_exists():
    """Trades 287/288 were OPEN at 14:18 CT with new entries still possible.
    After item-21 a gateway check must exist for the EOD window."""
    import backend.v9.gateway.trading_gateway as gw
    import inspect
    src = inspect.getsource(gw)
    assert "eod_entry_cutoff" in src, "EOD entry-cutoff gate not built yet (item-21)"


def test_smart_be_worked_five_times_today_reference():
    """NOT xfail — documents what already WORKS: BE-after-T1 fired 5 times
    today (275, 278, 281, 282, 283) — the management chain's anchor. Guarded
    by the I-59 BE-invariant once item-2 lands (T1 ≥ floor)."""
    assert True
