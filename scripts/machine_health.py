#!/usr/bin/env python3
"""machine_health.py — one-screen read-only health of the trading Mac.

Michael 16.09 11:25: "תוסיף גם בדיקה ותיקון למה המחשב והמערכת התחילו לעבוד לאט".
Measured that morning: 16 GB RAM fully used (120 MB unused, 3.2 GB compressed,
730 MB swap, 3.7M swapouts) — the machine was swapping. The consumers were not the
trading stack (backend 120 MB · bridge 20 MB · postgres 0.5 GB · Sierra+CrossOver
0.7 GB) but the tooling around it: Cowork sandbox VM 2.1 GB · Claude app 1.8 GB ·
two claude agent processes 0.8 GB · Chrome 1.0 GB · Adobe CC 0.2 GB · Spotlight 0.3 GB.

This script only READS. It prints load, memory, swap, the top consumers and the
trading-stack processes, and ends with WARN lines when a threshold is crossed.
It never kills anything — the fixes are Michael's (close tabs/apps) or a ruling
(Spotlight privacy for the repo, VM off). Wired into the 15:40 gate as a report
line; exit code is always 0 so it can never turn a GO into a NO-GO by itself.
"""
from __future__ import annotations

import re
import subprocess
import sys

# Thresholds (WARN only). Chosen from the 16.09 measurement: the machine felt slow
# at unused<200MB / swap>500MB / load>6 on 8 cores.
UNUSED_MB_MIN = 400
SWAP_USED_MB_MAX = 500
LOAD_MAX = 6.0
TOP_N = 10


def sh(cmd: str) -> str:
    try:
        return subprocess.run(cmd, shell=True, capture_output=True, text=True,
                              timeout=30).stdout
    except Exception as e:  # pragma: no cover
        return f"<{e}>"


def main() -> int:
    warns: list[str] = []
    up = sh("uptime").strip()
    m = re.search(r"load averages?: ([\d.]+)[, ]+([\d.]+)[, ]+([\d.]+)", up)
    load1 = float(m.group(1)) if m else -1
    ncpu = sh("sysctl -n hw.ncpu").strip()
    print(f"load 1/5/15: {m.group(1)}/{m.group(2)}/{m.group(3)}  (cores {ncpu})" if m else up)
    if load1 > LOAD_MAX:
        warns.append(f"load {load1} > {LOAD_MAX}")

    top1 = sh("top -l 1 -n 0")
    pm = re.search(r"PhysMem: (.*)", top1)
    print("mem:", pm.group(1) if pm else "?")
    un = re.search(r"(\d+)M unused", top1)
    unused = int(un.group(1)) if un else -1
    if 0 <= unused < UNUSED_MB_MIN:
        warns.append(f"unused RAM {unused}M < {UNUSED_MB_MIN}M — the Mac is compressing/swapping")
    sw = sh("sysctl -n vm.swapusage").strip()
    print("swap:", sw)
    su = re.search(r"used = ([\d.]+)M", sw)
    swap_used = float(su.group(1)) if su else 0.0
    if swap_used > SWAP_USED_MB_MAX:
        warns.append(f"swap used {swap_used:.0f}M > {SWAP_USED_MB_MAX}M")

    print(f"\ntop {TOP_N} by RSS:")
    rows = sh("ps -axo rss=,pid=,%cpu=,etime=,comm=").splitlines()
    parsed = []
    for r in rows:
        p = r.split(None, 4)
        if len(p) == 5 and p[0].isdigit():
            parsed.append((int(p[0]), p[1], p[2], p[3], p[4]))
    parsed.sort(reverse=True)
    for rss, pid, cpu, et, comm in parsed[:TOP_N]:
        print(f"  {rss/1024:7.0f} MB  pid {pid:<6} cpu {cpu:>5}  up {et:<12} {comm[-70:]}")

    print("\ntrading stack:")
    full = []
    for line in sh("ps -axo rss=,pid=,%cpu=,etime=,command=").splitlines():
        p = line.split(None, 4)
        if len(p) == 5 and p[0].isdigit():
            full.append((int(p[0]), p[1], p[2], p[3], p[4]))
    for pat, label in (("uvicorn backend.main", "backend"), ("bridge/json_bridge.py", "bridge"),
                       ("SierraChart_64", "sierra"), ("postgres:", "postgres"),
                       ("next dev", "frontend"), ("mobile_relay.py", "phone-relay")):
        hits = [x for x in full if pat in x[4]]
        tot = sum(h[0] for h in hits) / 1024
        print(f"  {label:11} n={len(hits):<2} rss {tot:6.0f} MB  " +
              (f"cpu {hits[0][2]}%" if hits else "NOT RUNNING"))
        if label in ("backend", "bridge", "sierra") and not hits:
            warns.append(f"{label} not running")

    # Claude tooling footprint (the usual culprit on this 16 GB machine)
    fam = {}
    for rss, pid, cpu, et, comm in parsed:
        key = None
        if "Virtualization.VirtualMachine" in comm:
            key = "cowork-vm"
        elif "/Claude.app/" in comm or comm.endswith("/Claude"):
            key = "claude-app"
        elif "claude-code" in comm or comm.endswith("/claude"):
            key = "claude-agents"
        elif "Google Chrome" in comm:
            key = "chrome"
        elif "Adobe" in comm or "CCXProcess" in comm:
            key = "adobe"
        elif "mds" in comm.split("/")[-1]:
            key = "spotlight"
        if key:
            fam[key] = fam.get(key, 0) + rss
    print("\nnon-trading footprint (MB):", {k: round(v / 1024) for k, v in sorted(fam.items(), key=lambda kv: -kv[1])})

    print()
    if warns:
        for w in warns:
            print("WARN:", w)
    else:
        print("OK: no threshold crossed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
