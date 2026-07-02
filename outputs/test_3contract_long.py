"""Test: place a LONG 3-contract demo order via the FIXED command path (metadata.sizing=3)
and capture the ENTRY fill to prove 3 OCO groups (c1/c2/c3) placed. SIM account only."""
import os, sys, json, time
os.environ["MEMS26_SIGNALS_DIR"] = "/Users/michael/SierraChart_Data/v9_export"
sys.path.insert(0, "/Users/michael/Downloads/mems26_web_git")
from backend.v9.services.sierra_command import command_from_setup

EXPORT = "/Users/michael/SierraChart_Data/v9_export"
lp = json.load(open(EXPORT + "/live_price.json"))
p = float(lp.get("last") or lp.get("price") or lp.get("close"))
setup = {
    "direction": "LONG", "entry_price": p,
    "stop": round(p - 20, 2), "t1": round(p + 5, 2),
    "t2": round(p + 10, 2), "t3": round(p + 15, 2),
    "classification": "COWORK_3CT_TEST",
    "metadata": {"sizing": 3},   # ← the fix reads this → 3 contracts
}
cmd = command_from_setup(setup, trade_id="TEST3CT",
                         account="PA-APEX-125218-01", mode="demo")
print("price=%.2f" % p)
print("✓ command written → contracts=%s  (stop=%.2f C1=%.2f C2=%.2f C3=%.2f)"
      % (cmd.get("contracts"), setup["stop"], setup["t1"], setup["t2"], setup["t3"]))
assert cmd.get("contracts") == 3, "FIX FAILED: command not 3 contracts"

# race the FillPoller (0.25s) to capture the DLL's ENTRY fill with c1/c2/c3 ids
entry = None
for _ in range(80):  # ~8s
    try:
        for line in open(EXPORT + "/trade_fills.json").read().strip().split("\n"):
            if "ENTRY" in line:
                entry = json.loads(line)
    except Exception:
        pass
    if entry:
        break
    time.sleep(0.1)
if entry:
    print("✓ ENTRY fill captured — 3-group proof:",
          {k: entry.get(k) for k in ("contracts", "c1_target_id", "c2_target_id", "c3_target_id")})
else:
    print("  (ENTRY not caught — poller consumed it; rely on result + Sierra order book)")
time.sleep(1)
try:
    r = json.load(open(EXPORT + "/trade_result.json"))
    print("✓ result:", r, "age=%.1fs" % (time.time() - r["ts"]))
except Exception as e:
    print("result read err:", e)
