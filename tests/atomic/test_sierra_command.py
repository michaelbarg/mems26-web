"""Atomic tests — Sierra command writer for DEMO/SIM."""
import json

from backend.v9.services.sierra_command import command_file, command_from_setup, write_trade_command


def test_write_trade_command_uses_env_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("MEMS26_SIGNALS_DIR", str(tmp_path))
    payload = write_trade_command(
        action="STATUS",
        trade_id="t1",
        context={"source": "test"},
    )
    assert payload["action"] == "STATUS"
    data = json.loads(command_file().read_text())
    assert data["trade_id"] == "t1"
    assert data["context"]["source"] == "test"


def test_command_from_setup_long_to_buy(tmp_path, monkeypatch):
    monkeypatch.setenv("MEMS26_SIGNALS_DIR", str(tmp_path))
    payload = command_from_setup(
        {
            "firing_system": 4,
            "direction": "LONG",
            "entry_price": 100.0,
            "stop": 99.0,
            "t1": 101.0,
            "contracts": 2,
        },
        trade_id="demo-1",
        account="PA-APEX-125218-01",
        mode="demo",
    )
    assert payload["action"] == "BUY"
    assert payload["account"] == "PA-APEX-125218-01"
    assert payload["contracts"] == 2


def test_command_from_setup_short_to_sell(tmp_path, monkeypatch):
    monkeypatch.setenv("MEMS26_SIGNALS_DIR", str(tmp_path))
    payload = command_from_setup(
        {
            "firing_system": 2,
            "direction": "SHORT",
            "entry_price": 100.0,
            "stop": 101.0,
            "t1": 99.0,
        },
        trade_id="demo-2",
        account="PA-APEX-125218-01",
        mode="demo",
    )
    assert payload["action"] == "SELL"
    assert payload["contracts"] == 1

