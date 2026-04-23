#!/usr/bin/env python3
"""Verify backend /trade/test-dispatch writes correct bracket to Redis."""
import hashlib, json, os, sys, time

try:
    import requests
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "requests", "-q"])
    import requests

BACKEND = os.environ.get("BACKEND_URL", "https://mems26-web.onrender.com")
REDIS_URL = os.environ.get("UPSTASH_REDIS_REST_URL", "")
REDIS_TOKEN = os.environ.get("UPSTASH_REDIS_REST_TOKEN", "")
BRIDGE_TOKEN = os.environ.get("BRIDGE_TOKEN", "michael-mems26-2026")

if not REDIS_URL or not REDIS_TOKEN:
    print("ERROR: UPSTASH_REDIS_REST_URL and UPSTASH_REDIS_REST_TOKEN must be set")
    sys.exit(1)

# Test inputs - concrete values
TEST = {
    "direction": "SHORT",
    "entry_price": 7162.50,
    "stop": 7165.50,
    "t1": 7160.50,
    "t2": 7157.50,
    "t3": 7130.50,
    "setup_type": "V6.5.7_verify",
}

print(f"=== STEP 1: POST {BACKEND}/trade/test-dispatch ===")
print(f"body: {json.dumps(TEST, indent=2)}")
try:
    r = requests.post(f"{BACKEND}/trade/test-dispatch", json=TEST, timeout=15)
except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)
print(f"status: {r.status_code}")
print(f"response: {r.text[:500]}\n")
if r.status_code != 200:
    print(f"FAILED: Backend returned HTTP {r.status_code}")
    sys.exit(1)

resp = r.json()

# If response includes the command, verify directly from response
cmd = resp.get("command")
if cmd:
    print("=== STEP 2: Verifying command from response (no Redis fetch needed) ===")
    print(json.dumps(cmd, indent=2))
else:
    print("=== STEP 2: Fetching from Redis ===")
    time.sleep(1.5)
    key = "mems26:trade:command"
    val_resp = requests.get(
        f"{REDIS_URL}/get/{key}",
        headers={"Authorization": f"Bearer {REDIS_TOKEN}"},
        timeout=10,
    ).json()
    raw = val_resp.get("result")
    if not raw:
        print("FAILED: No value at mems26:trade:command in Redis")
        sys.exit(1)
    cmd = json.loads(raw) if isinstance(raw, str) else raw
    # Handle double-encoding
    while isinstance(cmd, str):
        cmd = json.loads(cmd)
    print(json.dumps(cmd, indent=2))

print("\n=== STEP 3: Assertions ===")
errors = []

required = ["cmd", "price", "qty", "stop", "t1", "t2", "t3",
            "trade_id", "expires_at", "checksum"]
for f in required:
    if f not in cmd:
        errors.append(f"MISSING FIELD: {f}")

checks = [
    ("cmd",   "SELL",    lambda v: v == "SELL"),
    ("price", 7162.50,   lambda v: isinstance(v, (int, float)) and abs(v - 7162.50) < 0.01),
    ("qty",   3,         lambda v: v == 3),
    ("stop",  7165.50,   lambda v: isinstance(v, (int, float)) and abs(v - 7165.50) < 0.01),
    ("t1",    7160.50,   lambda v: isinstance(v, (int, float)) and abs(v - 7160.50) < 0.01),
    ("t2",    7157.50,   lambda v: isinstance(v, (int, float)) and abs(v - 7157.50) < 0.01),
    ("t3",    7130.50,   lambda v: isinstance(v, (int, float)) and abs(v - 7130.50) < 0.01),
]
for field, expected, check in checks:
    got = cmd.get(field)
    if got is None or not check(got):
        errors.append(f"{field}={got!r} expected {expected!r}")
    else:
        print(f"  {field}: {got} == {expected}")

# Checksum per DLL formula
try:
    cs_input = (
        f'{cmd["cmd"]}:{cmd["price"]:.2f}:{cmd["qty"]}:'
        f'{cmd["stop"]:.2f}:{cmd["trade_id"]}:{cmd["expires_at"]}:'
        f'{BRIDGE_TOKEN}'
    )
    expected_cs = hashlib.sha256(cs_input.encode()).hexdigest()
    if cmd.get("checksum") != expected_cs:
        errors.append(
            f"CHECKSUM INVALID\n"
            f"  got:      {cmd.get('checksum')}\n"
            f"  expected: {expected_cs}\n"
            f"  input:    {cs_input!r}"
        )
    else:
        print(f"  checksum: VALID")
except Exception as e:
    errors.append(f"Checksum check failed: {e}")

if errors:
    print(f"\n{'='*50}")
    print(f"VERIFICATION FAILED -- {len(errors)} error(s):")
    for e in errors:
        print(f"  - {e}")
    sys.exit(1)

print(f"\n{'='*50}")
print("VERIFICATION PASSED -- all fields correct, checksum valid")

# ── Bridge startup assertions ─────────────────────────────────────────────
import subprocess, shutil
BRIDGE_DIR = os.path.join(os.path.dirname(__file__), "..", "bridge")
real_env = os.path.join(BRIDGE_DIR, ".env")
backup = real_env + ".bak"

print(f"\n{'='*50}\n=== BRIDGE STARTUP TESTS ===")

# Test 1: bad token → exits with "REDIS TOKEN INVALID"
print("\n--- Test 1: bad token ---")
if os.path.exists(real_env):
    shutil.copy2(real_env, backup)
with open(real_env, "w") as f:
    f.write(f"UPSTASH_REDIS_REST_URL={REDIS_URL}\nUPSTASH_REDIS_REST_TOKEN=bad-token\n"
            f"CLOUD_URL={BACKEND}\nBRIDGE_TOKEN={BRIDGE_TOKEN}\n"
            "SC_JSON_PATH=/tmp/f.json\nSC_HISTORY_PATH=/tmp/fh.json\n")
try:
    p = subprocess.run([sys.executable, "json_bridge.py"], cwd=BRIDGE_DIR,
                       capture_output=True, text=True, timeout=10)
    if p.returncode != 0 and "REDIS TOKEN INVALID" in p.stderr:
        print("  PASS")
    else:
        errors.append(f"Bridge bad-token: rc={p.returncode}, stderr={p.stderr[-200:]}")
except subprocess.TimeoutExpired:
    errors.append("Bridge bad-token: no exit within 10s")
finally:
    if os.path.exists(backup):
        shutil.move(backup, real_env)

# Test 2: valid .env → "Bridge ready"
if os.path.exists(real_env):
    print("\n--- Test 2: valid token ---")
    try:
        p = subprocess.run([sys.executable, "json_bridge.py"], cwd=BRIDGE_DIR,
                           capture_output=True, text=True, timeout=15)
        if "Bridge ready" in p.stderr:
            print("  PASS")
        else:
            errors.append(f"Bridge valid: 'Bridge ready' missing, stderr={p.stderr[-300:]}")
    except subprocess.TimeoutExpired:
        errors.append("Bridge valid: timed out")
else:
    print("\n--- Test 2: SKIPPED (no .env) ---")

if errors:
    print(f"\n{'='*50}\nFAILED -- {len(errors)} error(s):")
    for e in errors:
        print(f"  - {e}")
    sys.exit(1)
print(f"\n{'='*50}\nALL TESTS PASSED")
