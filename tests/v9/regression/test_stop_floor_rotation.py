"""Decision 5/6 (Michael 07-15): dynamic stop floor by day type.
Rotation days (Variation/Neutral) floor = 0.8×ATR; trend days keep 0.5×ATR.
Anti-tautological: the SAME ladder+ATR that produced #372's fatal 6pt stop
must skip to a deeper rung on a Variation day, and still pick it on Trend."""
import sys
from pathlib import Path
REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))

from backend.v9.systems.stop_anchors.stop_resolver import resolve_stop  # noqa: E402

# reconstruction of #372: entry 7597.25, ATR 10.8, near rung ~6pt, deeper rung ~9.5pt
ENTRY = 7597.25
ATR = 10.8
RUNGS = [7592.0, 7588.5]           # dists ≈ 6.0, 9.5 (before 3T offset)
NAMES = ["r0", "r1"]


def test_variation_floor_skips_noise_stop(monkeypatch):
    monkeypatch.delenv("STOP_FLOOR_ROTATION_ATR", raising=False)
    r = resolve_stop(direction="LONG", entry_price=ENTRY, rungs=RUNGS,
                     rung_names=NAMES, atr_5m=ATR, family="REV", day_type="Variation")
    assert r.floor_pts == max(0.8 * ATR, 1.0)          # 8.64
    assert r.rung_index == 1, f"must skip the 6pt noise rung, got {r.rung_name}"
    assert r.risk_points >= 0.8 * ATR - 0.01


def test_trend_keeps_tight_floor():
    r = resolve_stop(direction="LONG", entry_price=ENTRY, rungs=RUNGS,
                     rung_names=NAMES, atr_5m=ATR, family="REV", day_type="Trend_Normal")
    assert r.floor_pts == max(0.5 * ATR, 1.0)          # 5.4
    assert r.rung_index == 0, "trend day keeps the near structural rung"


def test_no_day_type_defaults_to_tight():
    r = resolve_stop(direction="LONG", entry_price=ENTRY, rungs=RUNGS,
                     rung_names=NAMES, atr_5m=ATR, family="REV", day_type=None)
    assert r.floor_pts == max(0.5 * ATR, 1.0)


def test_neutral_also_rotation(monkeypatch):
    monkeypatch.setenv("STOP_FLOOR_ROTATION_ATR", "0.9")
    r = resolve_stop(direction="LONG", entry_price=ENTRY, rungs=RUNGS,
                     rung_names=NAMES, atr_5m=ATR, family="REV", day_type="Neutral_Extreme")
    assert abs(r.floor_pts - 0.9 * ATR) < 0.01          # param respected
