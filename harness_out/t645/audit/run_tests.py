#!/usr/bin/env python3
# Audit test runner (T-645): runs each regression file separately, hermetic env
# (no .env sourced; any DB fallback pointed into the audit dir), no caches.
import os, subprocess, sys, time, re
ROOT = "/Users/michael/Downloads/mems26_web_git"
AUD = os.path.join(ROOT, "harness_out/t645/audit")
files = [l.strip() for l in open(os.path.join(AUD, "test_files.txt")) if l.strip() and not l.startswith("#")]
env = dict(os.environ)
for k in list(env):
    if k.startswith("MEMS26_") or k in ("DATABASE_URL",):
        env.pop(k, None)
env["PYTHONDONTWRITEBYTECODE"] = "1"; env.setdefault("BRIDGE_TOKEN", "michael-mems26-2026")
env["DATABASE_URL"] = "sqlite:///" + os.path.join(AUD, "pytest_fallback.db")
env["PATH"] = "/Library/Frameworks/Python.framework/Versions/3.9/bin:/usr/local/bin:" + env.get("PATH", "")
out = open(os.path.join(AUD, "tests_results.txt"), "w")
out.write(f"# started {time.strftime('%Y-%m-%d %H:%M:%S')}\n"); out.flush()
for f in files:
    t0 = time.time()
    try:
        p = subprocess.run([sys.executable, "-m", "pytest", f, "-q", "-rfE", "-p", "no:cacheprovider"],
                           cwd=ROOT, env=env, capture_output=True, text=True, timeout=300)
        txt = p.stdout + p.stderr
        rc = p.returncode
    except subprocess.TimeoutExpired as e:
        txt = "TIMEOUT"; rc = -9
    lines = [l for l in txt.splitlines() if l.strip()]
    summ = ""
    for l in reversed(lines):
        if re.search(r"(passed|failed|error|no tests ran)", l):
            summ = l.strip(); break
    fails = [l for l in lines if l.startswith("FAILED") or l.startswith("ERROR")][:12]
    out.write(f"{f} | rc={rc} | {summ} | {time.time()-t0:.1f}s\n")
    for l in fails:
        out.write(f"    {l[:300]}\n")
    out.flush()
out.write(f"# finished {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
out.close()
