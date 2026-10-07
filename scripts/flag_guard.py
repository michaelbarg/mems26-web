#!/usr/bin/env python3
"""flag_guard — אימות שדגלים שנפסקו לא זזו (מייקל 2026-07-08).

משווה את .env מול config/RULED_FLAGS.yaml. כל סטייה = NO-GO (exit 1) עם פירוט.
רץ בשלב 0 של LIVE_MORNING_PROTOCOL ובתוך fire_drill; אפשר ידנית בכל רגע:
    python3 scripts/flag_guard.py [--env PATH]
"""
import argparse
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RULED = os.path.join(ROOT, "config", "RULED_FLAGS.yaml")


def parse_env(path):
    envs = {}
    if not os.path.exists(path):
        return envs
    for line in open(path, encoding="utf-8", errors="replace"):
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        envs[k.strip()] = v.strip().strip('"').strip("'")
    return envs


def parse_ruled(path):
    """Minimal YAML subset parser (flat `KEY: {expected: "..", ...}` under `ruled:`)."""
    ruled = {}
    in_ruled = False
    rx = re.compile(r'^\s{2}([A-Z0-9_]+):\s*\{(.*)\}\s*$')
    for line in open(path, encoding="utf-8"):
        if line.startswith("ruled:"):
            in_ruled = True
            continue
        if not in_ruled:
            continue
        m = rx.match(line)
        if not m:
            continue
        key, body = m.group(1), m.group(2)
        # T-219/T-168: match both single and double quoted expected values.
        # T-168 converted note values to single quotes; some expected values
        # followed. The parser must handle both.
        em = re.search(r"""expected:\s*["']([^"']*)["']""", body)
        nm = re.search(r"""note:\s*["']([^"']*)["']""", body)
        if em:
            ruled[key] = {"expected": em.group(1), "note": nm.group(1) if nm else ""}
    return ruled


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--env", default=os.path.join(ROOT, ".env"))
    args = ap.parse_args()

    envs = parse_env(args.env)
    ruled = parse_ruled(RULED)
    if not ruled:
        print("FLAG-GUARD: ERROR — RULED_FLAGS.yaml empty/unparsable")
        return 1

    bad = []
    for flag, spec in sorted(ruled.items()):
        want = spec["expected"]
        have = envs.get(flag)
        if want == "unset_or_0":
            ok = have is None or have == "0" or have == ""
            shown = "unset" if have is None else have
        else:
            ok = have == want
            shown = "MISSING" if have is None else have
        mark = "✓" if ok else "✗"
        print(f"  {mark} {flag}: expected={want} actual={shown}" + ("" if ok else f"  ← {spec['note']}"))
        if not ok:
            bad.append(flag)

    if bad:
        print(f"\nFLAG-GUARD: NO-GO — {len(bad)} ruled flag(s) drifted: {', '.join(bad)}")
        print("שינוי דגל שנפסק = פסיקת מייקל בכתב + עדכון config/RULED_FLAGS.yaml באותו קומיט.")
        return 1

    # ── BUDGET × MIN ≤ CAP consistency (T-198, cowork 01.09) ──
    # The daily loss cap bounds the risk budget: raising the budget without
    # raising the cap just advances the shutdown. 225×3=675 ≤ 800 today.
    try:
        _budget = float(envs.get("RISK_BUDGET_USD", "0") or 0)
        _min_c = int(envs.get("RISK_MIN_CONTRACTS", "0") or 0)
        _cap = float(envs.get("RISK_DAILY_LOSS_CAP", "0") or 0)
        _budget_on = envs.get("RISK_BUDGET_SIZING_V1", "0") in ("1", "true", "yes")
        if _budget_on and _budget > 0 and _min_c > 0 and _cap > 0:
            _product = _budget * _min_c
            if _product > _cap:
                bad.append("BUDGET_CAP_CONSISTENCY")
                print(f"\n  ✗ BUDGET×MIN > CAP: {_budget}×{_min_c}={_product} > {_cap}")
                print("    העלאת תקציב בלי העלאת תקרה = כיבוי שגרתי.")
            else:
                print(f"\n  ✓ BUDGET×MIN ≤ CAP: {_budget}×{_min_c}={_product} ≤ {_cap}")
    except (TypeError, ValueError):
        pass  # missing values → skip check

    if bad:
        print(f"\nFLAG-GUARD: NO-GO — {len(bad)} issue(s)")
        return 1
    print(f"\nFLAG-GUARD: PASS — all {len(ruled)} ruled flags match.")

    # ── Second tooth (3ROOTS audit, 25.08): liveness checks ──
    # These REPORT but do not block GO.
    _second_tooth(ruled, envs)

    # ── Third tooth (T-563b, cowork 08.10): what the LaunchAgent exports AFTER
    # `source .env` overrides .env for those keys (env_loader never overrides).
    # REPORTS only — the ownership decision (T-435 step 3) is Michael's.
    _third_tooth_plist(envs, ruled)

    return 0


_PLIST = os.path.expanduser("~/Library/LaunchAgents/com.mems26.backend.plist")
_PLIST_EXPORT_RE = re.compile(r'export\s+([A-Z0-9_]+)=("?)([^";]*)\2')


def _plist_exports(path=_PLIST):
    """{KEY: value} of the `export KEY=VAL` statements in the LaunchAgent's
    bash -c wrapper (ProgramArguments[2]). Values of the form
    ${KEY:-default} resolve to the default. [] if the plist is unreadable."""
    try:
        import plistlib
        with open(path, "rb") as fh:
            prog = plistlib.load(fh).get("ProgramArguments") or []
    except Exception:
        return {}
    script = " ; ".join(a for a in prog if isinstance(a, str) and "export " in a)
    out = {}
    for m in _PLIST_EXPORT_RE.finditer(script):
        key, val = m.group(1), m.group(3).strip()
        dm = re.match(r'\$\{' + re.escape(key) + r':-(.*)\}$', val)
        out[key] = dm.group(1) if dm else val
    return out


def _live_backend_env(keys):
    """{KEY: value} from the environment of the listening backend (the
    LaunchAgent's pid via launchctl, `ps -E` on macOS). For keys the plist
    exports this IS what the process sees: they were in the environment before
    env_loader ran, and env_loader skips keys already present. (For keys set
    by code at runtime — gate overrides — ps shows nothing; feedback
    verify_live_flags_not_ps_eww still holds for those.) {} if unknown."""
    import subprocess
    try:
        uid = os.getuid()
        txt = subprocess.run(["launchctl", "print", f"gui/{uid}/com.mems26.backend"],
                             capture_output=True, text=True, timeout=10).stdout
        pm = re.search(r"^\s*pid = (\d+)", txt, re.M)
        if not pm:
            return {}
        env_txt = subprocess.run(["ps", "-E", "-p", pm.group(1), "-o", "command=", "-ww"],
                                 capture_output=True, text=True, timeout=10).stdout
    except Exception:
        return {}
    out = {}
    for tok in env_txt.split():
        if "=" in tok:
            k, v = tok.split("=", 1)
            if k in keys:
                out[k] = v
    return out


def _mask(key, val):
    """Never print a credential: tokens/secrets/urls-with-userinfo show as ***."""
    if val is None:
        return None
    if re.search(r"TOKEN|SECRET|PASSWORD|PASSWD|APIKEY|API_KEY", key) or "@" in str(val):
        return "***"
    return val


def _third_tooth_plist(envs, ruled):
    exports = _plist_exports()
    if not exports:
        print("\n  ── PLIST REPORT: LaunchAgent plist not readable — skipped ──")
        return
    live = _live_backend_env(set(exports))
    envs = {k: _mask(k, v) for k, v in envs.items()}
    live = {k: _mask(k, v) for k, v in live.items()}
    exports = {k: _mask(k, v) for k, v in exports.items()}
    def _norm(v):
        """flag() semantics: 1/true/yes are one value, 0/false/no/'' another."""
        s = str(v).strip().lower()
        if s in ("1", "true", "yes"):
            return "on"
        if s in ("0", "false", "no", ""):
            return "off"
        return s

    drift = []
    for key, pval in sorted(exports.items()):
        eval_ = envs.get(key)
        lval = live.get(key)
        if eval_ is not None and _norm(eval_) != _norm(pval):
            drift.append((key, pval, eval_, lval, "plist ≠ .env"))
        elif eval_ is None and ruled.get(key):
            drift.append((key, pval, "unset", lval, "ruled, set only by plist"))
    print(f"\n  ── PLIST REPORT (T-563b): {len(exports)} keys exported by the LaunchAgent "
          f"AFTER `source .env` — they win over .env for the live process ──")
    for key, pval in sorted(exports.items()):
        tag = "live=" + (live[key] if key in live else "?")
        if envs.get(key) is None:
            print(f"  · {key}: plist={pval} .env=unset {tag}")
        elif _norm(envs.get(key)) == _norm(pval):
            print(f"  · {key}: plist={pval} .env={envs[key]} {tag}")
    for key, pval, eval_, lval, why in drift:
        print(f"  ⚠ {key}: plist={pval} .env={eval_} live={lval if lval is not None else '?'}  ← {why} "
              f"— .env is DEAD for this key under the LaunchAgent")
    if drift:
        print(f"  ⚠ {len(drift)} key(s) where the plist overrides .env — REPORT only; "
              f"ownership (T-435 step 3 / T-563) is Michael's ruling.")
    else:
        print("  ✓ no plist/.env disagreement")


def _second_tooth(ruled, envs):
    """Report flags that are technically correct but functionally dead."""
    import glob
    src_dirs = [
        os.path.join(ROOT, "backend"),
        os.path.join(ROOT, "bridge"),
    ]
    # Exclude non-production files
    exclude_patterns = {"_INDEX.md", "FLAG_REGISTRY", "RULED_FLAGS", "__pycache__"}
    test_patterns = {"/tests/", "/test_", "conftest"}

    inert = []

    for flag, spec in sorted(ruled.items()):
        want = spec["expected"]
        have = envs.get(flag)
        if want == "unset_or_0" or have in (None, "", "0"):
            continue  # OFF flags are intentionally silent

        # Check 1: ≥1 read-site in production code
        read_sites = 0
        for src_dir in src_dirs:
            for root_d, _, files in os.walk(src_dir):
                for fname in files:
                    if not fname.endswith(".py"):
                        continue
                    fpath = os.path.join(root_d, fname)
                    if any(p in fpath for p in exclude_patterns):
                        continue
                    is_test = any(p in fpath for p in test_patterns)
                    if is_test:
                        continue
                    try:
                        content = open(fpath, encoding="utf-8", errors="replace").read()
                        if flag in content:
                            read_sites += 1
                    except Exception:
                        pass
        if read_sites == 0:
            inert.append((flag, "NO_READ_SITE", "0 production code references"))

    if inert:
        print(f"\n  ── LIVENESS REPORT ({len(inert)} flags with no production read-site) ──")
        for flag, code, detail in inert:
            print(f"  ⚠ {flag}: {code} — {detail}")
    else:
        print(f"\n  ── LIVENESS REPORT: all ON flags have ≥1 production read-site ──")


if __name__ == "__main__":
    sys.exit(main())
