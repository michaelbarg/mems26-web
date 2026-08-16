"""T7 — the opening fusion compared partial-bar volume to full-bar volume.

MEASURED (not theorised). Live log, 2026-08-14 16:55 IL:

    [OPENING_DIR_FUSION] SKIP: opening_vol 2212 < median 114590 — auction/low-conviction

The canonical table says that morning's first six RTH bars traded **89,246**.
The 40× gap is a unit mismatch: the bars handed to S2 are `current_bar`
snapshots (bars.py routing override, deliberate — they carry live study values),
so each holds only the volume accrued in the first seconds of its 5-minute
window. A partial sum measured against a full-bar median can only ever say "too
quiet", so the gate dropped 8/8 opening candidates it ever saw (08-13 DRIVE LONG
×5; 08-14 ORR LONG + DRIVE SHORT ×2).

Both sides must come from the same measure. After the fix the gate discriminates
— 15 PASS / 7 skip over the last 22 sessions — instead of always skipping.
Note honestly: 08-14 itself still skips (89,246 < 114,590). That day's open
really was quiet; the fix is that the gate now measures it correctly.
"""
import pytest

from backend.v9.services import trade_context as tc


def _bars(vol_each, n=6, base=7800.0):
    """current_bar-style snapshots: correct prices, PARTIAL volume."""
    return [{"o": base, "h": base + 3, "l": base - 1, "c": base + 2 + i,
             "v": vol_each} for i in range(n)]


@pytest.fixture
def _on(monkeypatch):
    monkeypatch.setenv("OPENING_DIR_FUSION_V1", "1")


class TestVolumeComesFromClosedBars:
    def test_partial_snapshot_volume_is_ignored(self, monkeypatch, _on):
        """The live incident: snapshots say 2,212; the table says 89,246."""
        seen = {}

        def _scalar(sql, params):
            s = " ".join(sql.split())
            if "sum(volume)" in s and "rn <= 6" in s:
                seen["opening_vol_from_db"] = True
                return 89246
            if s.startswith("SELECT count(*)"):
                return 6
            if "percentile_cont" in s:
                return 80000        # median BELOW the day → must pass the screen
            return None

        import backend.v9.db.read as _read
        monkeypatch.setattr(_read, "read_scalar", _scalar)
        monkeypatch.setattr(_read, "read_one", lambda sql, params: None)

        captured = {}
        import backend.v9.systems.opening_entry as _oe
        monkeypatch.setattr(_oe, "opening_dir_fusion",
                            lambda bars, op, ov, med, **kw: captured.update(
                                {"ov": ov, "med": med}) or "UP")

        out = tc.get_opening_dir_fusion(_bars(369))
        assert seen.get("opening_vol_from_db"), "volume must be read from the canonical table"
        assert captured["ov"] == 89246, (
            f"got {captured['ov']} — the partial current_bar sum leaked back in")
        assert out == "UP"

    def test_fewer_than_six_closed_bars_is_honest_none(self, monkeypatch, _on):
        """Rule 1: never pass a partial window off as a full one."""
        import backend.v9.db.read as _read
        monkeypatch.setattr(_read, "read_scalar",
                            lambda sql, params: 3 if "count(*)" in sql else 40000)
        monkeypatch.setattr(_read, "read_one", lambda sql, params: None)
        assert tc.get_opening_dir_fusion(_bars(369)) is None

    def test_the_query_excludes_the_forming_bar(self, monkeypatch, _on):
        """Same boundary as T6 — the in-progress bar is not a bar."""
        sqls = []
        import backend.v9.db.read as _read
        monkeypatch.setattr(_read, "read_scalar",
                            lambda sql, params: sqls.append(sql) or (6 if "count(*)" in sql else 1))
        monkeypatch.setattr(_read, "read_one", lambda sql, params: None)
        tc.get_opening_dir_fusion(_bars(369))
        joined = " ".join(" ".join(s.split()) for s in sqls)
        assert joined.count("ts <= now() - interval '5 minutes'") >= 2


class TestTheGateStillDiscriminates:
    """A gate that always passes is as useless as one that always skips."""

    def test_a_genuinely_quiet_open_still_skips(self, monkeypatch, _on):
        import backend.v9.db.read as _read

        def _scalar(sql, params):
            s = " ".join(sql.split())
            if "count(*)" in s:
                return 6
            if "percentile_cont" in s:
                return 114590      # the real 08-14 median
            return 89246           # the real 08-14 first-six volume

        monkeypatch.setattr(_read, "read_scalar", _scalar)
        monkeypatch.setattr(_read, "read_one", lambda sql, params: None)
        assert tc.get_opening_dir_fusion(_bars(369)) is None, (
            "08-14 really was a quiet open — the fix corrects the measure, "
            "it does not force the gate open")

    def test_flag_off_is_still_none(self, monkeypatch):
        monkeypatch.setenv("OPENING_DIR_FUSION_V1", "0")
        assert tc.get_opening_dir_fusion(_bars(369)) is None
