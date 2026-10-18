# -*- coding: utf-8 -*-
"""T-598 — proof the default path is byte-identical: run the PRE-PATCH harness (git HEAD:scripts/fwd_harness.py,
before the BE_AFTER_MFE_R_V1 block) on one session with the reference env and compare its JSON with the
t598ref output of the same session produced by the patched harness (flag unset). The only allowed difference
is the new output key "be_after_mfe". usage: python3 harness_out/t598/byte_identical_check.py <session> <out.json>"""
import json, os, subprocess, sys
ROOT = "/Users/michael/Downloads/mems26_web_git"
sess, out = sys.argv[1], sys.argv[2]
path = os.path.join(ROOT, "scripts", "fwd_harness.py")
src = subprocess.check_output(["git", "-C", ROOT, "show", "HEAD:scripts/fwd_harness.py"]).decode("utf-8")
assert "BE_AFTER_MFE_R_V1" not in src, "HEAD already carries the flag — compare against HEAD~1 instead"
sys.argv = ["fwd_harness.py", "--session", sess, "--variant", "t598head", "--out", out, "--quiet"]
exec(compile(src, path, "exec"), {"__file__": path, "__name__": "__main__"})
a = json.load(open(out)); b = json.load(open(os.path.join(ROOT, "harness_out", "t466", f"t598ref_{sess}.json")))
a.pop("variant", None); b.pop("variant", None)
extra = b.pop("be_after_mfe", None)
diff = [k for k in sorted(set(a) | set(b)) if a.get(k) != b.get(k)]
print("session", sess, "extra key in patched output:", extra, "| keys that differ:", diff or "NONE",
      "| trades", len(a.get("trades") or []), "pnl", sum(float(t.get("pnl_usd") or 0) for t in a.get("trades") or []))
