#!/usr/bin/env python3
"""T-422 §3 — route-level diff: what exactly does the fix ADD vs the pre-fix base,
and is it byte-identical to the existing --oe-closed counterfactual?"""
import json
import sys

MAIN = "/Users/michael/Downloads/mems26_web_git/harness_out/t422"
BASE = "/tmp/mems_base_t422/harness_out/t422"
SESSIONS = ["2026-09-18", "2026-09-17", "2026-09-16", "2026-09-15", "2026-09-11"]


def key(r):
    return (r.get("il"), r.get("system"), r.get("classification"), r.get("direction"),
            r.get("entry"), r.get("blocked_by"))


def routes(p):
    with open(p) as fh:
        return [key(r) for r in json.load(fh)["routes"]]


for s in SESSIONS:
    b, f, o = (routes(f"{BASE}/base_{s}.json"), routes(f"{MAIN}/fix_{s}.json"),
               routes(f"{MAIN}/oeclosed_{s}.json"))
    add_f = [r for r in f if r not in b]
    rem_f = [r for r in b if r not in f]
    print(f"=== {s} ===  base={len(b)} fix={len(f)} oe-closed={len(o)}")
    print(f"  FIX routes == OE-CLOSED routes : {sorted(f) == sorted(o)}")
    for r in add_f:
        print(f"  + only in FIX : {r}")
    for r in rem_f:
        print(f"  - only in BASE: {r}")
    add_o = [r for r in o if r not in b]
    for r in add_o:
        print(f"  + only in OE-CLOSED: {r}")
    print()
