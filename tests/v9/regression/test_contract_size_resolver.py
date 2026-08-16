"""One resolver for "how many contracts did Michael rule for?".

The ladder `4 → 2 → 3` was copy-pasted into eight files. That is not a style
problem: the sizing path is `min(_fixed, _cut)`, where `_fixed` comes from
`sierra_command` and `_cut` comes from `quality_tier`. Teaching one of them
about a bigger size does not make the system trade bigger — it makes the system
**trade the old size and report the new one**.

The single most important test in this file is the byte-identity one: with
today's live configuration (`FIXED_CONTRACTS_4=1`, no `_5`/`_6`), every site
must still answer exactly 4. A refactor the night before a live session earns
its place only by proving it changed nothing.
"""
import pytest

from backend.v9.services import contract_size as cs


@pytest.fixture(autouse=True)
def _clear(monkeypatch):
    for k in ("FIXED_CONTRACTS_2", "FIXED_CONTRACTS_3", "FIXED_CONTRACTS_4",
              "FIXED_CONTRACTS_5", "FIXED_CONTRACTS_6"):
        monkeypatch.delenv(k, raising=False)
    yield


class TestTodaysConfigIsUnchanged:
    def test_four_is_still_four(self, monkeypatch):
        monkeypatch.setenv("FIXED_CONTRACTS_4", "1")
        assert cs.ruled_contracts() == 4

    def test_every_choke_point_agrees_on_four(self, monkeypatch):
        """quality_tier and stop_anchors feed the `_cut`; sierra_command feeds
        the `_fixed`. If they disagree the system trades one number and reports
        another."""
        monkeypatch.setenv("FIXED_CONTRACTS_4", "1")
        from backend.v9.systems.stop_anchors import sizing as sz
        import backend.v9.systems.five_min.quality_tier as qt
        import backend.v9.services.sierra_command as sc
        import backend.v9.api.v9.mobile_monitor as mm
        import re
        for mod in (qt, sz, sc, mm):
            src = __import__("inspect").getsource(mod)
            # comments may still name the flag (they carry the ruling history);
            # what must be gone is any site that READS it and decides a size.
            reads = re.findall(r'(?:getenv|environ\.get)\(\s*["\']FIXED_CONTRACTS_\d', src)
            assert not reads, (
                f"{mod.__name__} still reads FIXED_CONTRACTS_* directly "
                f"({len(reads)} site(s)) — that is how the system ends up "
                f"trading one size and reporting another")
            assert "contract_size" in src, f"{mod.__name__} must use the resolver"

    def test_no_ruling_is_none_not_zero(self):
        assert cs.ruled_contracts() is None, (
            "None means 'no fixed-size ruling' — a 0 here would silence every fire")

    def test_precedence_newest_ruling_wins(self, monkeypatch):
        monkeypatch.setenv("FIXED_CONTRACTS_4", "1")
        monkeypatch.setenv("FIXED_CONTRACTS_3", "1")
        assert cs.ruled_contracts() == 4
        monkeypatch.setenv("FIXED_CONTRACTS_5", "1")
        assert cs.ruled_contracts() == 5
        monkeypatch.setenv("FIXED_CONTRACTS_6", "1")
        assert cs.ruled_contracts() == 6


class TestEveryContractIsProtected:
    """Michael's 2026-08-16 ruling: t0=1 · t1=2 · t2=2 · t3=1.

    The rule that must hold at EVERY size is that the four OCO-group quantities
    sum to the order quantity. Before the fix each group was hard-coded to 1
    (sum 4), so a 5- or 6-contract order would have entered with 1-2 contracts
    carrying no stop and no target — invisible, because the position looks
    bracketed. That is the naked-orphan class that cost money five times in July.
    """

    @pytest.mark.parametrize("n", [1, 2, 3, 4, 5, 6])
    def test_ladder_sums_to_the_order(self, n):
        assert sum(cs.ladder_for(n)) == n, (
            f"{n} contracts -> {cs.ladder_for(n)}: a contract with no stop")

    def test_the_ruling_shape_at_six(self):
        assert cs.ladder_for(6) == (1, 2, 2, 1)

    def test_five_keeps_the_same_shape_one_lighter(self):
        assert cs.ladder_for(5) == (1, 2, 1, 1)

    def test_four_groups_only_never_five(self):
        """ACSIL gives OCOGroup1..5, but the deployed study builds four."""
        for n in range(1, 7):
            assert len(cs.ladder_for(n)) == 4

    def test_oversize_clamps_the_order_not_the_protection(self):
        assert sum(cs.ladder_for(9)) == cs.MAX_PROTECTED_CONTRACTS

    def test_backend_ladder_matches_the_dll_table(self):
        """The two must agree — this is what the backend thinks it bought
        versus what the broker was told to protect."""
        src = open("sc_study/MES_AI_DataExport_merged.cpp", encoding="utf-8",
                   errors="surrogateescape").read()
        assert "lq[0]=1; lq[1]=2; lq[2]=2; lq[3]=1;" in src, "DLL missing the 6 ladder"
        assert "lq[0]=1; lq[1]=2; lq[2]=1; lq[3]=1;" in src, "DLL missing the 5 ladder"
        assert "o.OrderQuantity = lq_sum;" in src, (
            "the DLL must order exactly what it protects")
        for g in (1, 2, 3, 4):
            assert f"o.OCOGroup{g}Quantity" in src
            assert f"o.OCOGroup{g}Quantity        = 1;" not in src
            assert f"o.OCOGroup{g}Quantity      = 1;" not in src


class TestTargetMapping:
    """At six, two contracts ride T1 and two ride T2 — so "contract i takes
    target i" under-books a winner (the same class of bug as the [:3] slice)."""

    def test_six_contract_mapping(self):
        got = [cs.target_index_for_contract(i, 6) for i in range(6)]
        assert got == [0, 1, 1, 2, 2, 3]

    def test_five_contract_mapping(self):
        assert [cs.target_index_for_contract(i, 5) for i in range(5)] == [0, 1, 1, 2, 3]

    def test_four_is_one_to_one_as_today(self):
        assert [cs.target_index_for_contract(i, 4) for i in range(4)] == [0, 1, 2, 3]
