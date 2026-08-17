"""Michael, 2026-08-17: "אני כבר מבין שאתה בטח עשית משהו לא תקין שיחסום עסקאות
חיות — לבקר את עצמך ולבדוק שאכן הם לא ימנעו ירי."

Fair suspicion. Every guard added on 08-16/08-17 is checked here against the
only question that matters: can it stop a good trade from firing?

The audit, guard by guard:

  account_has_foreign_contracts  — called ONLY from the two System-6 EXIT paths
                                   and the exit verifier. Not on the entry path.
  exit_verifier                  — exit path + FillPoller. Not on entry. It CAN
                                   hold the LIVE slot, which blocks the NEXT
                                   fire; that is bounded below.
  contract_size.ruled_contracts  — IS on the sizing path. Must return exactly
                                   what the old ladder returned.
  scale-in Sierra check          — reinforcement path only.
  T6 closed-bars                 — delays TREND_STEP one bar, never blocks.
  T7 fusion latch                — covered in test_fusion_gate_does_not_block_early.
"""
import os
import sys

import pytest


def _load_env():
    for ln in open(".env", encoding="utf-8"):
        if "=" in ln and not ln.strip().startswith("#"):
            k, v = ln.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())


class TestTheSizingPathIsUnchanged:
    """The one guard that really is on the entry path."""

    @pytest.fixture(autouse=True)
    def _env(self, monkeypatch):
        monkeypatch.setenv("FIXED_CONTRACTS_4", "1")
        monkeypatch.setenv("SIZE_CAP_OVER_FIXED_V1", "1")
        for k in ("FIXED_CONTRACTS_5", "FIXED_CONTRACTS_6"):
            monkeypatch.delenv(k, raising=False)

    @pytest.mark.parametrize("setup,expected", [
        ({"contracts": 4}, 4),                                   # S2 numeric
        ({"metadata": {"sizing": "full"}}, 4),                    # S4 full
        ({"metadata": {"sizing": "half"}}, 2),                    # S4 judgment cut
        ({}, 4),                                                  # no sizing info
        ({"contracts": 0}, 0),                                    # explicit SKIP
    ])
    def test_a_fire_still_gets_its_contracts(self, setup, expected):
        from backend.v9.services.sierra_command import effective_contracts
        assert effective_contracts(setup) == expected, (
            "the resolver changed the size a fire ships — this is how a guard "
            "silently becomes a blocker")

    def test_the_resolver_never_returns_zero_for_a_live_ruling(self):
        from backend.v9.services.contract_size import ruled_contracts
        assert ruled_contracts() == 4, "a 0 here would silence every fire"


class TestNoGuardSitsOnTheEntryPath:
    def test_the_flatten_guard_is_exit_only(self):
        import subprocess
        out = subprocess.run(
            ["grep", "-rn", "account_has_foreign_contracts", "--include=*.py",
             "backend/"], capture_output=True, text=True).stdout
        for line in out.strip().splitlines():
            path = line.split(":", 1)[0]
            assert ("bar_level_detector" in path or "exit_verifier" in path
                    or "sierra_command" in path or "/tests/" in path), (
                f"the FLATTEN guard leaked onto {path} — it must never be "
                f"consulted when deciding whether to ENTER")

    def test_the_verifier_is_not_imported_by_the_gateway(self):
        """The gateway decides fires. If it ever imports the verifier, an exit
        problem could start vetoing entries."""
        src = open("backend/v9/gateway/trading_gateway.py", encoding="utf-8").read()
        assert "exit_verifier" not in src


class TestTheSlotHoldIsBounded:
    """The verifier holds the LIVE slot until an exit is proven — correct, since
    stacking a fire on top of a position that may still be live is worse. But it
    must not wedge for the day.

    It is bounded by the trade's OWN bracket: a Sierra stop or target fill goes
    through FillPoller -> close_trade -> gateway frees the slot, entirely
    independently of the verifier, and the pending then retires quietly via the
    `still_open` callback.

    This matters more than usual today: Michael is holding contracts by hand, so
    the account is never flat, so POSITION_TRUTH_SYNC's flat-based rescue cannot
    fire. The bracket is the remaining bound.
    """

    def test_a_bracket_fill_closes_the_trade_without_the_verifier(self):
        import inspect
        from backend.v9.services import fill_poller
        src = inspect.getsource(fill_poller)
        assert "_notify_gateway_close" in src
        i = src.index("def _notify_gateway_close")
        assert "on_trade_close" in src[i:i + 1500], (
            "the slot must be freeable by a real fill, independently of the "
            "exit verifier")

    def test_a_close_from_any_path_retires_the_pending(self):
        from backend.v9.services import exit_verifier as ev
        ev.clear()
        closed = []
        ev.register(900, source="mae_scratch", reason="x",
                    on_confirmed=lambda: closed.append(900),
                    still_open=lambda: False, contracts=4)
        ev.verify_pending()
        assert not ev.is_pending(900), (
            "a trade closed by its own stop must not stay pending forever")
        assert closed == []
        ev.clear()
