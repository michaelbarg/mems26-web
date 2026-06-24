"""Engine-promotion parity: classify_session with live-wiring inputs == endpoint.

For each of the 11 validated days, loads the SAME context that the live engine
loads at IB-lock (bars + IB + profile_shape + prior-day levels + vol_ratio +
ib_width_hist), feeds it to classify_session, and asserts the day_type matches
the validated endpoint result.

This catches the 06-16/17 Trend_DD divergence: without profile_shape, the
classify_session sees 1-sided but no dd_second_dist → Normal_Variation instead
of Trend_DD.

Requires the live backend (Postgres) for the context load. Skipped when offline.
"""
import os
import pytest
import requests


ENDPOINT = "http://localhost:8000/api/v9/day_type/classify_replay"

VALIDATED = {
    "2026-06-05": "Trend_Normal",
    "2026-06-08": "Neutral_Extreme",
    "2026-06-09": "Neutral_Center",
    "2026-06-10": "Normal_Variation",
    "2026-06-11": "Neutral_Center",
    "2026-06-12": "Normal_Variation",
    "2026-06-15": "Normal_Variation",
    "2026-06-16": "Trend_DD",
    "2026-06-17": "Trend_DD",
    "2026-06-18": "Normal",
    "2026-06-19": "Normal_Variation",
}


def _endpoint_alive():
    try:
        return requests.get("http://localhost:8000/health", timeout=2).status_code == 200
    except Exception:
        return False


@pytest.mark.skipif(not _endpoint_alive(), reason="backend not running")
class TestEnginePromotionParity:
    """classify_session with full context == classify_replay on all 11 days."""

    @pytest.mark.parametrize("date,expected", list(VALIDATED.items()))
    def test_parity(self, date, expected):
        """Load context from endpoint response, feed to classify_session, assert match."""
        r = requests.get(f"{ENDPOINT}?date={date}", timeout=15)
        assert r.status_code == 200
        data = r.json()
        assert data.get("final"), f"No final for {date}"

        # The endpoint result is the ground truth
        endpoint_dt = data["final"]["day_type"]
        assert endpoint_dt == expected, f"Endpoint diverged: {endpoint_dt} != {expected}"

        # Now call classify_session with the same inputs the engine would use
        from backend.v9.systems.day_type.classifier_core import classify_session

        # Reconstruct bars from endpoint (we need the RTH bars it used)
        # The endpoint doesn't return raw bars, but we can get them from the same source
        from backend.v9.api.v9.chart_replay_routes import _bars_for_date
        from backend.v9.api.v9.daytype_classify_routes import _ff, _et_min

        os.environ.setdefault("DATABASE_URL", "postgresql://localhost/mems26")
        rows, _ = _bars_for_date(date)
        rth = []
        for row in rows:
            m = _et_min(row["ts"])
            o, h, l, c = _ff(row["o"]), _ff(row["h"]), _ff(row["l"]), _ff(row["c"])
            if m is None or not (570 <= m < 960) or None in (o, h, l, c):
                continue
            rth.append({"o": o, "h": h, "l": l, "c": c,
                        "v": _ff(row["v"]), "cum": _ff(row.get("cum_delta"))})

        assert len(rth) >= 12, f"Not enough RTH bars for {date}: {len(rth)}"

        # Get the context the endpoint used (from its response)
        # Load ib_width_hist from DB (same as the engine does at IB-lock)
        from backend.v9.db.read import read_all
        _hist_rows = read_all(
            "SELECT ib_width FROM v9_day_type_history WHERE date < :d AND ib_width IS NOT NULL",
            {"d": date})
        _ib_hist = [float(r["ib_width"]) for r in _hist_rows if r.get("ib_width") is not None]
        # Load IB medians for dd narrow-IB check (same as engine)
        _ibm_rows = read_all(
            "SELECT (ib_high - ib_low) AS w FROM v9_tpo_sessions "
            "WHERE session_type='CASH' AND trading_date < :d "
            "AND ib_high IS NOT NULL AND ib_low IS NOT NULL "
            "ORDER BY trading_date DESC LIMIT 20", {"d": date})
        # ib_width_hist is used by classify_session for percentile AND ib_median for DD
        # We pass the TPO-based IB widths as ib_width_hist when v9_day_type_history has fewer entries
        _tpo_ibs = [float(r["w"]) for r in _ibm_rows if r.get("w") is not None]
        _combined_hist = _ib_hist if len(_ib_hist) >= 5 else _tpo_ibs

        result = classify_session(
            bars=rth,
            ib_high=data["ib_high"],
            ib_low=data["ib_low"],
            open_price=rth[0]["o"],
            ib_width_hist=_combined_hist,
            profile_shape=data.get("profile_shape"),
            vol_ratio=data.get("vol_ratio"),
            prior_vah=data.get("prior_vah"),
            prior_val=data.get("prior_val"),
            pdh=data.get("pdh"),
            pdl=data.get("pdl"),
            poc_now=None,
            poc_at_ib=None,
            is_eod=True,
        )

        core_dt = result["day_type"]
        assert core_dt == expected, (
            f"{date}: classify_session={core_dt} != expected={expected} "
            f"(endpoint={endpoint_dt}, profile_shape={data.get('profile_shape')}, "
            f"vol_ratio={data.get('vol_ratio')})"
        )
