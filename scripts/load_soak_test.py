"""Load soak test — concurrent high-frequency pushes to all hot endpoints.

Phase 4 gate: proves the safe_writer root fix holds under concurrent write load.
Run for ≥10 minutes, then stop backend + integrity_check.
"""

import json
import random
import threading
import time
import urllib.request

BASE = "http://localhost:8000"
TOKEN = "michael-mems26-2026"
DURATION_SEC = 600  # 10 minutes
PUSH_INTERVAL = 0.1  # 100ms between pushes per thread

stats = {"pushes": 0, "errors": 0, "lock": threading.Lock()}


def _post(path, payload):
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        f"{BASE}{path}",
        data=data,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {TOKEN}",
        },
    )
    try:
        resp = urllib.request.urlopen(req, timeout=10)
        with stats["lock"]:
            stats["pushes"] += 1
        return json.loads(resp.read())
    except Exception as e:
        with stats["lock"]:
            stats["errors"] += 1
        return {"error": str(e)}


def soak_5min(end_time):
    ts_base = 1700100000
    i = 0
    while time.time() < end_time:
        ts = ts_base + i * 300
        _post("/api/v9/bars/5min", [
            {"ts": ts, "symbol": "MES", "o": 5000 + random.random() * 100,
             "h": 5100 + random.random() * 50, "l": 4950 + random.random() * 50,
             "c": 5050 + random.random() * 50, "vol": random.randint(100, 5000)}
        ])
        i += 1
        time.sleep(PUSH_INTERVAL)


def soak_cumulative_delta(end_time):
    i = 0
    while time.time() < end_time:
        ts = 1700100000 + i * 300
        _post("/api/v9/bars/cumulative_delta", {
            "type": "cumulative_delta",
            "points": [{"i": i % 2000, "t": ts, "d": random.randint(-100, 100),
                         "cum": random.randint(-5000, 5000), "p": 5000 + random.random() * 100}],
        })
        i += 1
        time.sleep(PUSH_INTERVAL)


def soak_imbalance(end_time):
    i = 0
    while time.time() < end_time:
        ts = 1700100000 + i * 300
        _post("/api/v9/bars/imbalance", {
            "type": "imbalance_flags",
            "bars": [{"ts": ts, "bar_idx": i % 500, "price": 5000 + random.random() * 100,
                       "stacked_buy": random.randint(0, 10), "stacked_sell": random.randint(0, 10)}],
        })
        i += 1
        time.sleep(PUSH_INTERVAL * 2)


def soak_woodies(end_time):
    i = 0
    while time.time() < end_time:
        ts = 1700100000 + i * 300
        _post("/api/v9/bars/woodies_5min", {
            "type": "woodies_5min",
            "bars": [{"ts": f"2025-01-01T{(i // 60) % 24:02d}:{i % 60:02d}:00",
                       "o": 5000, "h": 5050, "l": 4950, "c": 5025, "vol": 1000,
                       "cci_14": random.uniform(-200, 200), "swi_value": random.random()}],
        })
        i += 1
        time.sleep(PUSH_INTERVAL)


def soak_tpo(end_time):
    i = 0
    while time.time() < end_time:
        ts = 1700100000 + i * 300
        _post("/api/v9/bars/tpo", {
            "bars": [{"ts": ts, "letter": chr(65 + (i % 26)),
                       "price": 5000 + random.randint(0, 100),
                       "level": i % 50, "period_id": i % 10}],
        })
        i += 1
        time.sleep(PUSH_INTERVAL * 2)


def main():
    end_time = time.time() + DURATION_SEC
    print(f"=== LOAD SOAK: {DURATION_SEC}s across 5 concurrent writers ===")
    print(f"Endpoints: /5min, /cumulative_delta, /imbalance, /woodies_5min, /tpo")

    threads = [
        threading.Thread(target=soak_5min, args=(end_time,), daemon=True),
        threading.Thread(target=soak_cumulative_delta, args=(end_time,), daemon=True),
        threading.Thread(target=soak_imbalance, args=(end_time,), daemon=True),
        threading.Thread(target=soak_woodies, args=(end_time,), daemon=True),
        threading.Thread(target=soak_tpo, args=(end_time,), daemon=True),
    ]
    for t in threads:
        t.start()

    # Progress updates
    start = time.time()
    while time.time() < end_time:
        elapsed = int(time.time() - start)
        with stats["lock"]:
            p, e = stats["pushes"], stats["errors"]
        print(f"  [{elapsed:>4d}s] pushes={p:>6d}  errors={e}", flush=True)
        time.sleep(30)

    for t in threads:
        t.join(timeout=5)

    with stats["lock"]:
        p, e = stats["pushes"], stats["errors"]
    print(f"\n=== SOAK COMPLETE: {p} pushes, {e} errors in {DURATION_SEC}s ===")


if __name__ == "__main__":
    main()
