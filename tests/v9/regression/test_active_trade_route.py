"""The route has to answer, and it has to describe every contract.

Two defects, both found on 2026-08-18 when Michael said the dashboard "doesn't
show target percentages and the position properly":

1. THE ROUTE WAS BOUND TO THE WRONG FUNCTION. A commit inserted two helpers
   between `@router.get("/active")` and `get_active_trade`, so FastAPI
   registered the decorator against `_contracts_of`. GET /active answered
   422 "field required: trade"; the dashboard's fetch returned null and every
   surface fell through to "No Active Trade" — no position, no target rows, no
   percentages. Six string-asserting tests passed throughout, because none of
   them made a request.

2. ONLY THREE LEGS COULD EVER BE BUILT. The rows were written C1/C2/C3 → t1/t2/t3
   and then sliced, so above four contracts the slice did nothing: a 5-contract
   trade rendered three bars under "0/5 hit", the first bar measured against T1
   when that contract exits at T0, and the P&L summed three legs out of five.
"""
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def api():
    from backend.v9.app import app
    return TestClient(app)


class TestTheRouteAnswers:
    def test_active_does_not_demand_a_query_parameter(self, api):
        """422 here means the decorator is attached to the wrong function."""
        r = api.get("/api/v9/trades/active")
        assert r.status_code != 422, (
            "GET /active asked for a query parameter — the route is bound to a "
            "helper, not to get_active_trade: %s" % r.text)
        assert r.status_code == 200

    def test_it_returns_a_trade_or_an_honest_null(self, api):
        body = api.get("/api/v9/trades/active").json()
        assert body is None or isinstance(body, dict), (
            "expected the trade object or null, got %r" % (body,))
        if isinstance(body, dict):
            assert "trade_id" in body

    def test_it_is_the_right_function(self):
        """Belt and braces: the operation id names the endpoint, not a helper."""
        from backend.v9.app import app
        for route in app.routes:
            if getattr(route, "path", "") == "/api/v9/trades/active":
                assert route.endpoint.__name__ == "get_active_trade", (
                    "/active is served by %s" % route.endpoint.__name__)
                return
        pytest.fail("/api/v9/trades/active is not registered at all")


class TestEveryContractGetsARow:
    """The leg list must come from the ladder the DLL actually brackets with."""

    @pytest.mark.parametrize("n,expected_legs", [
        (1, [0]),
        (3, [0, 1, 2]),
        (4, [0, 1, 2, 3]),
        (5, [0, 1, 1, 2, 3]),      # the 08-16 ruling: T1 carries two
        (6, [0, 1, 1, 2, 2, 3]),
    ])
    def test_the_row_count_and_mapping_follow_the_ladder(self, n, expected_legs):
        from backend.v9.services.contract_size import target_index_for_contract
        assert [target_index_for_contract(i, n) for i in range(n)] == expected_legs

    def test_five_contracts_would_not_be_described_by_three_rows(self):
        """The exact shape of the defect: rows must equal contracts."""
        from backend.v9.services.contract_size import target_index_for_contract
        rows = [target_index_for_contract(i, 5) for i in range(5)]
        assert len(rows) == 5, "three bars under '0/5 hit' is the bug"

    def test_the_first_contract_exits_at_t0_not_t1(self):
        from backend.v9.services.contract_size import target_index_for_contract
        assert target_index_for_contract(0, 5) == 0, (
            "C1 pointed at T1, so its percentage bar measured the wrong target")

    def test_the_endpoint_builds_rows_from_the_resolver(self):
        import inspect
        from backend.v9.api.v9 import trades
        src = inspect.getsource(trades.get_active_trade)
        assert "target_index_for_contract" in src
        assert '_contract("C3", trade.t3' not in src, (
            "the hardcoded three-row list is back")

    def test_the_phone_builds_rows_from_the_resolver_too(self):
        import inspect
        from backend.v9.api.v9 import mobile_monitor
        src = inspect.getsource(mobile_monitor)
        assert "target_index_for_contract" in src, (
            "the phone had the same three-leg list, and never used the t0 its "
            "own query already selects")
