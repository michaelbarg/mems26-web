"""Pipeline 5 — place ONE test DEMO entry to Sierra Sim. MICHAEL runs this (he holds the
order-placement trigger). Writes a correctly-formatted trade_command.json via the backend's
own writer, to the export dir the DLL reads. SIM/demo account only.

Precondition (Michael verifies in Sierra): global Trade Simulation Mode ON + Sim account +
EnableOrderPlacement (Input #21) = 1. On a sim-mode mismatch the DLL rejects (no real order).

Result: the DLL places LONG 3 contracts @ market, with 3 attached targets (C1/C2/C3) at 3
prices + a protective stop. Then Cowork watches trade_result.json + trade_fills.json.
"""
import os, sys
os.environ["MEMS26_SIGNALS_DIR"] = "/Users/michael/SierraChart_Data/v9_export"
sys.path.insert(0, "/Users/michael/Downloads/mems26_web_git")
from backend.v9.services.sierra_command import command_from_setup

# LONG test around market ~7417. Wide stop (20pt) so the test position survives long
# enough to demonstrate the runner re-anchor. 3 contracts, 3 different targets.
ENTRY, STOP, T1, T2, T3 = 7417.0, 7397.0, 7422.0, 7427.0, 7432.0
setup = {
    "firing_system": 2, "direction": "LONG",
    "entry_price": ENTRY, "stop": STOP, "t1": T1, "t2": T2, "t3": T3,
    "contracts": 3, "classification": "COWORK_DEMO_TEST",
}
cmd = command_from_setup(setup, trade_id="DEMOTEST1",
                         account="PA-APEX-125218-01", mode="demo")
print("✓ wrote trade_command.json (Sierra Sim account PA-APEX-125218-01)")
print("  LONG 3 contracts @ market · stop=%.0f · C1 target=%.0f · C2=%.0f · C3=%.0f"
      % (STOP, T1, T2, T3))
print("  → watch Sierra: 3 contracts fill, 3 attached targets rest at 3 different prices.")
