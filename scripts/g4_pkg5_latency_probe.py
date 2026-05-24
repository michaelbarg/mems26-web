"""g4_pkg5_latency_probe.py · G4 UAT Axis 4 · process_bar latency measurement.

Measures end-to-end latency of FiveMinSystem.process_bar with all chart-pattern
detectors in chain (initiative + reactive + inv_hns + hns_top + db_ee + dt_aa + flags).

Usage:
    BRIDGE_TOKEN=dummy python scripts/g4_pkg5_latency_probe.py

Exit codes:
    0 · p95 < 50ms · LATENCY PASS
    1 · p95 >= 50ms · LATENCY FAIL
"""
import asyncio
import statistics
import sys
import time

from backend.v9.systems.five_min.five_min_system import FiveMinSystem, FiveMinMode


def _random_walk_bars(n: int, seed: int = 42) -> list:
    """Generate n bars in random walk that does NOT form any chart pattern."""
    import random
    rng = random.Random(seed)
    bars = []
    price = 4500.0
    for i in range(n):
        delta = rng.uniform(-0.5, 0.5)
        price += delta
        bars.append({
            "o": price,
            "h": price + rng.uniform(0, 0.5),
            "l": price - rng.uniform(0, 0.5),
            "c": price + delta,
            "v": rng.randint(800, 1200),
            "ts": 1748208900 + i * 300,
        })
    return bars


async def main() -> int:
    fm = FiveMinSystem()
    fm.mode = FiveMinMode.DAY_TYPE_MODE
    fm.current_day_type = "Variation"

    fm._bar_buffer = _random_walk_bars(30, seed=42)
    plain_bar = {
        "o": 4500, "h": 4501, "l": 4499, "c": 4500.5,
        "v": 1000, "ts": 1748209200,
    }

    latencies_ms = []
    for i in range(100):
        start = time.perf_counter()
        await fm.process_bar(plain_bar)
        elapsed = (time.perf_counter() - start) * 1000
        latencies_ms.append(elapsed)

    p50 = statistics.median(latencies_ms)
    p95 = statistics.quantiles(latencies_ms, n=20)[18]
    p99 = max(latencies_ms)

    print(f"process_bar latency over 100 calls:")
    print(f"  p50 = {p50:.2f} ms")
    print(f"  p95 = {p95:.2f} ms")
    print(f"  p99 = {p99:.2f} ms")

    if p95 >= 50.0:
        print(f"LATENCY FAIL · p95={p95:.2f}ms >= 50ms budget", file=sys.stderr)
        return 1
    if p99 >= 80.0:
        print(f"LATENCY WARN · p99={p99:.2f}ms >= 80ms hard cap", file=sys.stderr)
        return 1

    print("LATENCY PASS")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
