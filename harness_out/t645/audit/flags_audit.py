#!/usr/bin/env python3
# read-only: RULED_FLAGS (date >= cutoff) vs current .env vs .env loaded at the last boot
import sys, re, yaml, os
RULED = "config/RULED_FLAGS.yaml"
ENV_NOW = ".env"
ENV_BOOT = os.path.expanduser("~/mems26_snapshots/20261023T094934Z_pre-restart-t638-2026-10-23/env/.env")
cutoff = sys.argv[1] if len(sys.argv) > 1 else "2026-10-17"
show_all = len(sys.argv) > 2 and sys.argv[2] == "all"

def parse_env(p):
    d = {}
    with open(p, encoding="utf-8") as f:
        for line in f:
            s = line.strip()
            if not s or s.startswith("#") or "=" not in s:
                continue
            if s.startswith("export "):
                s = s[7:]
            k, v = s.split("=", 1)
            v = v.strip()
            # strip inline comment
            if " #" in v:
                v = v.split(" #", 1)[0].strip()
            v = v.strip('"').strip("'")
            d[k.strip()] = v  # last one wins (like env_loader? check)
    return d

def dupes(p):
    seen = {}
    out = []
    with open(p, encoding="utf-8") as f:
        for i, line in enumerate(f, 1):
            s = line.strip()
            if not s or s.startswith("#") or "=" not in s:
                continue
            k = s.split("=", 1)[0].replace("export ", "").strip()
            if k in seen:
                out.append((k, seen[k], i))
            seen[k] = i
    return out

with open(RULED, encoding="utf-8") as f:
    y = yaml.safe_load(f)
ruled = y.get("ruled", {})
now = parse_env(ENV_NOW)
boot = parse_env(ENV_BOOT)

def ok(expected, actual):
    e = str(expected)
    if e == "unset_or_0":
        return actual in (None, "", "0")
    return actual == e

rows = []
for k, v in ruled.items():
    if not isinstance(v, dict):
        continue
    date = str(v.get("date", ""))
    if date < cutoff and not show_all:
        continue
    exp = v.get("expected")
    a_now = now.get(k)
    a_boot = boot.get(k)
    st_now = "OK" if ok(exp, a_now) else "MISMATCH"
    st_boot = "OK" if ok(exp, a_boot) else "MISMATCH"
    rows.append((date, k, str(exp), a_now, a_boot, st_now, st_boot, str(v.get("ruled_by", "")), str(v.get("note", ""))[:160]))
rows.sort()
for r in rows:
    print(" | ".join(str(x) for x in r[:8]))
    print("      note:", r[8])
print("TOTAL ruled entries:", len(ruled), " shown:", len(rows))
print("mismatch_now:", [r[1] for r in rows if r[5] != "OK"])
print("mismatch_boot:", [r[1] for r in rows if r[6] != "OK"])
print("env dupes now:", dupes(ENV_NOW)[:40])
diffkeys = sorted(set(now) ^ set(boot)) + sorted(k for k in set(now) & set(boot) if now[k] != boot[k])
print("env keys differing now vs boot:", diffkeys)
