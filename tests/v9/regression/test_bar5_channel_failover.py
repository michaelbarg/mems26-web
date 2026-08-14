"""Regression — the '5min' channel must never go silent while canonical bars flow.

Michael 2026-08-14, mid-session: "לא יכול להיות שלא מתקבלים נתונים אם אני רואה
אותם" — and he was right. On mac-2, 11 of 12 streams were fresh (price, woodies,
TPO, CVD, ticks) while ONLY the '5min' BarRouter channel was dead. S2 and the
day-type machine subscribe to '5min', so both sat blind for a whole session
behind a screen that looked alive.

Chain: mac-2's Sierra does not export 5min.json → the raw publisher
(bars.py POST /5min) never fires → F2 (2026-08-12) had disabled the aggregator
publisher as the double-feed fix → zero publishers left on that machine.

Fix: the woodies ingest — the CANONICAL 5-min bar per docs/SOURCE_OF_TRUTH.md —
republishes the same closed bar on '5min' when the raw channel has been silent
past BAR5_FAILOVER_SECONDS. It stays quiet whenever the raw feed is alive, so
the F2 single-source guarantee holds on healthy machines.
"""
import inspect

from backend.v9.api.v9 import bars as bars_mod


def _src():
    return inspect.getsource(bars_mod.post_woodies_5min)


class TestFailoverWiring:
    def test_failover_exists_on_woodies_path(self):
        src = _src()
        assert "FAILOVER" in src
        assert '_route_bar("5min"' in src

    def test_threshold_is_env_tunable_with_safe_default(self):
        src = _src()
        assert "BAR5_FAILOVER_SECONDS" in src
        assert '"120"' in src

    def test_only_fires_when_raw_channel_silent(self):
        """Must compare against the raw channel's last push — never unconditional
        (that would recreate the F2 double feed)."""
        src = _src()
        assert "_fo_last" in src and "_fo_gap" in src
        assert "> _fo_gap" in src

    def test_records_push_so_health_reflects_reality(self):
        src = _src()
        assert '_record_push("5min")' in src

    def test_failover_never_breaks_ingest(self):
        """Any error in the failover must not fail the woodies push itself."""
        src = _src()
        i = src.index("FAILOVER")
        assert "except Exception" in src[i - 400:] or "_fo_err" in src

    def test_woodies_route_still_primary(self):
        src = _src()
        assert '_route_bar("woodies_5min", last_flat)' in src
        assert src.index('_route_bar("woodies_5min"') < src.index('_route_bar("5min"')


class TestStreamHealthShape:
    def test_snapshot_shape_used_by_failover(self):
        """The failover reads get_all_streams()['streams'] as a list of dicts
        with name/last_push_ts — lock the contract."""
        from backend.v9.services.stream_health import StreamHealthService
        s = StreamHealthService()
        s.record_push("5min")
        snap = s.get_all_streams()
        rows = snap.get("streams", snap) if isinstance(snap, dict) else snap
        assert isinstance(rows, list)
        row = next((r for r in rows if r.get("name") == "5min"), None)
        assert row is not None
        assert "last_push_ts" in row
