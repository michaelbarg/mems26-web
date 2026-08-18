"""The size that ships must be the size that was computed.

Michael, 2026-08-18: "עסקאות מערכת 4 היו על 2 שהיו צריכות להיות מינימום על 3
או 4 חוזים."

All 17 fires on 17.08 shipped exactly 2 contracts. The reason was not the risk
cap alone — the count was being squeezed through a three-value enum:

    sizing = "full" if _c >= 3 else ("half" if _c >= 2 else
             ("reject" if _c == 0 else "half"))

which loses in both directions:
  * a computed 3 became "full" and shipped 4  — over-sized
  * a computed 1 became "half" and shipped 2  — SILENTLY DOUBLED, on 7 of the
    16 fires that day, including live trade 693
  * and 3 had no representation at all, so "minimum 3" was not merely unused,
    it was impossible

The number now travels next to the enum, and `effective_contracts` reads it
first. The enum stays for the older readers.
"""
import pytest


@pytest.fixture(autouse=True)
def _live_config(monkeypatch):
    monkeypatch.setenv("FIXED_CONTRACTS_4", "1")
    monkeypatch.setenv("SIZE_CAP_OVER_FIXED_V1", "1")
    for k in ("FIXED_CONTRACTS_5", "FIXED_CONTRACTS_6"):
        monkeypatch.delenv(k, raising=False)


def _ship(**setup):
    from backend.v9.services.sierra_command import effective_contracts
    return effective_contracts(setup)


class TestTheNumberSurvives:
    @pytest.mark.parametrize("computed", [1, 2, 3, 4])
    def test_what_was_computed_is_what_ships(self, computed):
        assert _ship(metadata={"sizing_contracts": computed}) == computed

    def test_one_contract_is_no_longer_doubled(self):
        """The live defect: 7 of 16 fires on 17.08, including trade 693."""
        assert _ship(metadata={"sizing_contracts": 1}) == 1, (
            "a computed 1 shipping 2 is a silent RISK INCREASE, not a cut")

    def test_three_contracts_finally_exist(self):
        """'minimum 3' was impossible — the enum had no value for it."""
        assert _ship(metadata={"sizing_contracts": 3}) == 3

    def test_three_is_not_rounded_up_to_four(self):
        assert _ship(metadata={"sizing_contracts": 3}) != 4

    def test_a_reject_is_still_a_reject(self):
        assert _ship(metadata={"sizing_contracts": 0}) == 0
        assert _ship(metadata={"sizing": "reject"}) == 0


class TestNothingElseMoved:
    """The enum path must keep behaving exactly as it did for anything that
    still speaks it."""

    def test_full_still_means_the_ruled_size(self):
        assert _ship(metadata={"sizing": "full"}) == 4

    def test_half_still_means_two(self):
        assert _ship(metadata={"sizing": "half"}) == 2

    def test_no_sizing_info_keeps_the_ruled_count(self):
        assert _ship() == 4

    def test_an_explicit_numeric_setup_field_still_wins(self):
        assert _ship(contracts=2) == 2

    def test_the_number_beats_the_enum_when_both_are_present(self):
        """A producer sending both must not be judged by the lossy one."""
        assert _ship(metadata={"sizing": "half", "sizing_contracts": 3}) == 3


class TestTheProducersShipTheNumber:
    def test_s4_carries_sizing_contracts(self):
        import inspect
        from backend.v9.systems.woodies import woodies_system as w
        src = inspect.getsource(w)
        assert '"sizing_contracts"' in src, (
            "S4 must send the number, not only the bucket")
        assert '("reject" if _c == 0 else "half")' not in src, (
            "the 1 -> half -> 2 branch must be gone")

    def test_s2_no_longer_maps_one_to_half(self):
        import inspect
        from backend.v9.systems.five_min import five_min_system as f
        src = inspect.getsource(f)
        assert '("reject" if _c == 0 else "half")' not in src

    def test_the_reader_prefers_the_number(self):
        import inspect
        from backend.v9.services import sierra_command as sc
        src = inspect.getsource(sc)
        i_num = src.index('"sizing_contracts"')
        i_enum = src.index('.get("sizing")')
        assert i_num < i_enum, "the number must be read before the bucket"
