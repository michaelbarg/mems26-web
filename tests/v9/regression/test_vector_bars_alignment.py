"""vol_ratio must key on the CLOSED bar's 5-minute bucket, not on the decision
timestamp (cowork 17.09 14:50). Live decisions arrive seconds into the next
bar (18:53:07Z for the 18:50 bar); keyed on that timestamp no prior-session
bar ever matched and vol_ratio was always None."""
import unittest

from backend.v9.services.situation_vector import _compute_vol_ratio


def _session(vol_at_1850: float, day: int):
    return [
        {"ts": f"2026-09-{day:02d}T18:45:00+00:00", "v": 1000.0},
        {"ts": f"2026-09-{day:02d}T18:50:00+00:00", "v": vol_at_1850},
        {"ts": f"2026-09-{day:02d}T18:55:00+00:00", "v": 1000.0},
    ]


class TestVectorBarsAlignment(unittest.TestCase):

    def test_decision_seconds_into_next_bar_still_matches(self):
        today = [{"ts": "2026-09-16T18:50:00+00:00", "v": 6000.0}]
        prior = [_session(1000.0, d) for d in (9, 10, 11, 12, 15)]
        # decision at 18:53:07Z — must key on the 18:50 bar
        r = _compute_vol_ratio("2026-09-16T18:53:07+00:00", today, prior)
        self.assertIsNotNone(r)
        self.assertAlmostEqual(r, 6.0, places=3)

    def test_fewer_than_five_prior_sessions_is_none(self):
        today = [{"ts": "2026-09-16T18:50:00+00:00", "v": 6000.0}]
        prior = [_session(1000.0, d) for d in (9, 10, 11)]
        self.assertIsNone(_compute_vol_ratio("2026-09-16T18:53:07+00:00", today, prior))

    def test_causal_only_prior_sessions_define_the_median(self):
        # a huge bar in TODAY's list must not move the denominator
        today = [{"ts": "2026-09-16T18:45:00+00:00", "v": 90000.0},
                 {"ts": "2026-09-16T18:50:00+00:00", "v": 2000.0}]
        prior = [_session(1000.0, d) for d in (9, 10, 11, 12, 15)]
        r = _compute_vol_ratio("2026-09-16T18:53:07+00:00", today, prior)
        self.assertAlmostEqual(r, 2.0, places=3)


if __name__ == "__main__":
    unittest.main()
