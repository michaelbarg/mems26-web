"""VA sanity check — flags impossible Value Areas.

Anchor 31.08: VA=3.50 with IB=29.50 → SUSPECT (impossible).
Anchor 25.08: VA=27.00 / range=38.50 = 70% → OK (the one correct day).
"""
from backend.v9.systems.va_sanity import va_quality


class TestVASanity:

    def test_31_08_impossible_va(self):
        """31.08: VA=3.50, IB=29.50 → SUSPECT (VA < IB/2)."""
        r = va_quality(vah=7695.5, val=7692.0, ib_high=7720.0, ib_low=7690.5)
        assert not r["ok"], f"31.08 VA should be SUSPECT: {r}"
        assert "ib" in r["reason"].lower()

    def test_25_08_correct_va(self):
        """25.08: VA=27.00, range=38.50 = 70% → OK."""
        r = va_quality(
            vah=7755.0, val=7728.0,
            session_high=7760.0, session_low=7721.5)
        assert r["ok"], f"25.08 should be OK: {r}"
        assert r["ratio"] and 0.5 <= r["ratio"] <= 0.9

    def test_missing_va(self):
        r = va_quality(vah=None, val=7700.0)
        assert not r["ok"]
        assert r["reason"] == "missing"

    def test_inverted_va(self):
        r = va_quality(vah=7700.0, val=7710.0)
        assert not r["ok"]
        assert "inverted" in r["reason"]

    def test_too_narrow(self):
        """VA = 5% of range → SUSPECT."""
        r = va_quality(vah=7701.0, val=7700.0,
                       session_high=7720.0, session_low=7700.0)
        assert not r["ok"]
        assert "narrow" in r["reason"]

    def test_normal_va(self):
        """VA = 60% of range → OK."""
        r = va_quality(vah=7718.0, val=7706.0,
                       session_high=7720.0, session_low=7700.0)
        assert r["ok"]
