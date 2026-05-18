"""P29 Replay Scenario Pack — offline governance and route contract tests.

This suite intentionally avoids live Sierra, bridge, HTTP services, and any
trade_command writes. It verifies the 10 P29 scenarios against local pure
components and mocks only.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict
from unittest.mock import MagicMock
from zoneinfo import ZoneInfo

import pytest

from backend.v9.services.trading_gateway.gateway import TradingGateway
from backend.v9.shared.pre_fire_validator import FireRequest, validate_fire
from backend.v9.systems.day_type.decision_matrix import DecisionMatrix
from backend.v9.systems.day_type.schemas import BarInput, DayType
from backend.v9.systems.day_type.state_machine import DayTypeStateMachine
from backend.v9.systems.killzone.detector import get_killzone_status
from backend.v9.systems.tpo import profile_builder as tpo_builder
from backend.v9.systems.tpo.schemas import TPOConfig


FIXTURE_PATH = Path(__file__).parent / "fixtures" / "p29" / "scenarios.json"
ET = ZoneInfo("America/New_York")
EXPECTED_IDS = [f"P29.{idx}" for idx in range(1, 11)]
FIRING_SYSTEMS = {"S2", "S3", "S4"}
OBSERVING_SYSTEMS = {"S1", "S5", "S6"}


def _load_scenarios() -> list[Dict[str, Any]]:
    return json.loads(FIXTURE_PATH.read_text())


def _utc_from_et(iso_without_tz: str) -> datetime:
    return datetime.fromisoformat(iso_without_tz).replace(tzinfo=ET).astimezone(timezone.utc)


def _make_gateway() -> TradingGateway:
    trade_manager = MagicMock()
    trade_manager.accept_setup.side_effect = iter(range(1, 100))

    risk_validator = MagicMock()
    risk_validator.check_setup.return_value = (True, None)

    return TradingGateway(
        trade_manager=trade_manager,
        risk_validator=risk_validator,
        demo_enabled=False,
        live_enabled=False,
    )


def _assert_day_type_contract(scenario: Dict[str, Any]) -> None:
    day_type = scenario["day_type"]

    if day_type["missing_prior_day"]:
        state = DayTypeStateMachine().process_bar(
            BarInput(
                ts=0,
                session_min=0,
                open=7400.0,
                high=7401.0,
                low=7399.0,
                close=7400.5,
            )
        )
        assert state.day_type == DayType.UNKNOWN
        assert state.meta["pd_context_status"] == "DEGRADED"
        assert state.meta["pd_degraded_reason"] == "missing_previous_day_context"
        return

    probs = DecisionMatrix().get_probabilities(
        day_type["opening_type"],
        day_type["ib_width"],
    )
    winner = max(probs, key=probs.get)
    assert winner == day_type["expected_top1"].lower()


def _assert_killzone_contract(scenario: Dict[str, Any]) -> None:
    killzone = scenario["killzone"]
    status = get_killzone_status(_utc_from_et(killzone["et"]))
    assert status["current_killzone"] == killzone["expected_zone"]
    assert status["is_blocked"] is killzone["expected_blocked"]


def _assert_tpo_contract(scenario: Dict[str, Any]) -> None:
    tpo_profile = scenario.get("tpo_profile")
    if not tpo_profile:
        return

    profile = tpo_builder.init_profile(TPOConfig())
    for letter, prices in tpo_profile["prices_by_letter"].items():
        profile.current_letter = letter
        for price in prices:
            profile = tpo_builder.add_price(profile, price, TPOConfig())
    profile = tpo_builder.refresh_levels(profile, TPOConfig())

    assert profile.poc == tpo_profile["expected_poc"]
    assert profile.vah is not None
    assert profile.val is not None


def _assert_fire_and_route_contract(scenario: Dict[str, Any]) -> None:
    firing = scenario["firing"]
    expected_route = firing["expected_route"]

    if expected_route == "no_fire":
        assert firing["system"] == "NONE"
        return

    assert firing["system"] in FIRING_SYSTEMS

    request = FireRequest(
        system_id=firing["pre_fire_system_id"],
        direction=firing["direction"],
        entry_price=firing["entry_price"],
        stop_price=firing["stop_price"],
        t1_price=firing["t1_price"],
        t2_price=firing["t2_price"],
        time_stop_minutes=firing["time_stop_minutes"],
        confidence=firing["confidence"],
    )
    response = validate_fire(request)
    assert response.valid is firing["expected_pre_fire_valid"]

    if not response.valid:
        assert expected_route == "blocked"
        assert firing["expected_block_reason_contains"] in (response.fail_reason or "")
        return

    setup = {
        "firing_system": firing["system_id"],
        "direction": firing["direction"],
        "entry_price": firing["entry_price"],
        "stop": firing["stop_price"],
        "t1": firing["t1_price"],
        "t2": firing["t2_price"],
        "t3": firing["t2_price"],
    }
    route = _make_gateway().route_setup(setup, system_id=firing["system_id"])

    assert expected_route == "shadow_only"
    assert route["shadow_trade_id"] > 0
    assert route["demo_trade_id"] is None
    assert route["live_trade_id"] is None
    assert route["rejections"] == []


def _assert_reason_tree_contract(scenario: Dict[str, Any]) -> None:
    reason_tree = scenario["reason_tree"]
    assert len(reason_tree) >= 3
    assert all(isinstance(reason, str) and reason for reason in reason_tree)

    advisory_keys = set(scenario["advisory_context"])
    assert advisory_keys == OBSERVING_SYSTEMS


def test_p29_scenario_manifest_has_exactly_10_ordered_scenarios():
    scenarios = _load_scenarios()

    assert [scenario["id"] for scenario in scenarios] == EXPECTED_IDS
    assert len({scenario["source"] for scenario in scenarios}) == 10
    assert all(scenario["expected_result"] == "PASS" for scenario in scenarios)


@pytest.mark.parametrize("scenario", _load_scenarios(), ids=lambda s: s["id"])
def test_p29_scenario_pack_contracts(scenario):
    _assert_day_type_contract(scenario)
    _assert_killzone_contract(scenario)
    _assert_tpo_contract(scenario)
    _assert_fire_and_route_contract(scenario)
    _assert_reason_tree_contract(scenario)

    firing = scenario["firing"]
    if firing.get("required_stream"):
        assert firing["required_stream"] == "woodies_5min"

