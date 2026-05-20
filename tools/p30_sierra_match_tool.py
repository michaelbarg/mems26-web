#!/usr/bin/env python3
"""P30 Sierra Match Tool — compare DLL JSON exports against expected Sierra values.

Usage:
    python3 tools/p30_sierra_match_tool.py
    python3 tools/p30_sierra_match_tool.py --watch   # re-run every 30s

Reads from: /Users/michael/SierraChart_Data/v9_export/
Writes to:  /tmp/p30_diagnostic/sierra_match_<timestamp>.log
"""

import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

EXPORT_DIR = Path("/Users/michael/SierraChart_Data/v9_export")
LOG_DIR = Path("/tmp/p30_diagnostic")
LOG_DIR.mkdir(parents=True, exist_ok=True)


def load_json(name: str):
    p = EXPORT_DIR / name
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text())
    except Exception:
        return None


def verdict(actual, expected, tolerance, label=""):
    """Return verdict emoji + detail."""
    if actual is None or expected is None:
        return "⚪ NO_DATA", f"{label}: actual={actual} expected={expected}"
    try:
        diff = abs(float(actual) - float(expected))
    except (TypeError, ValueError):
        if str(actual) == str(expected):
            return "🟢 MATCH", f"{label}: {actual}"
        return "🔴 MISMATCH", f"{label}: actual={actual} expected={expected}"

    if diff <= tolerance:
        return "🟢 MATCH", f"{label}: {actual} (diff={diff:.2f})"
    elif diff <= tolerance * 2:
        return "🟡 DRIFT", f"{label}: actual={actual} expected={expected} diff={diff:.2f}"
    else:
        return "🔴 MISMATCH", f"{label}: actual={actual} expected={expected} diff={diff:.2f}"


def check_bool(actual, expected, label=""):
    if actual is None:
        return "⚪ NO_DATA", f"{label}: actual=None"
    if bool(actual) == bool(expected):
        return "🟢 MATCH", f"{label}: {actual}"
    return "🔴 MISMATCH", f"{label}: actual={actual} expected={expected}"


def run_check():
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    results = []

    # --- Woodies 5min ---
    w5 = load_json("woodies_5min.json")
    if w5:
        cb = w5.get("current_bar", {})
        results.append(("woodies", "sierra_source", *check_bool(cb.get("sierra_source"), True, "sierra_source")))
        results.append(("woodies", "version", "🟢 MATCH" if "p30.11" in w5.get("version", "") else "🟡 DRIFT",
                         f"version={w5.get('version')}"))

        # Self-consistency checks (no Sierra reference needed)
        cci14 = cb.get("cci_14")
        cci6 = cb.get("cci_6_tcci")
        ccidiff = cb.get("ccidiff")
        if cci14 is not None and cci6 is not None and ccidiff is not None:
            expected_diff = cci14 - cci6
            results.append(("woodies", "ccidiff_consistency",
                            *verdict(ccidiff, expected_diff, 0.5, "ccidiff vs cci14-cci6")))

        # Indicator range sanity
        for name, val, lo, hi in [
            ("cci_14", cci14, -500, 500),
            ("cci_6_tcci", cci6, -500, 500),
            ("swi_value", cb.get("swi_value"), -300, 300),
            ("czi_value", cb.get("czi_value"), -100, 100),
            ("ema_34", cb.get("ema_34"), 3000, 10000),
            ("lsma_value", cb.get("lsma_value"), 3000, 10000),
        ]:
            if val is not None:
                in_range = lo <= val <= hi
                v = "🟢 MATCH" if in_range else "🔴 MISMATCH"
                results.append(("woodies", f"{name}_range", v, f"{name}={val} range=[{lo},{hi}]"))
            else:
                results.append(("woodies", f"{name}_range", "⚪ NO_DATA", f"{name}=None"))

        # ProjHigh/ProjLow sanity (should be far from current price if valid)
        proj_hi = cb.get("proj_hi")
        proj_lo = cb.get("proj_lo")
        if proj_hi is not None and proj_lo is not None and proj_hi != "null" and proj_lo != "null":
            results.append(("woodies", "proj_hi_range",
                            "🟢 MATCH" if 5000 < proj_hi < 12000 else "🔴 MISMATCH",
                            f"proj_hi={proj_hi}"))
            results.append(("woodies", "proj_lo_range",
                            "🟢 MATCH" if 3000 < proj_lo < 10000 else "🔴 MISMATCH",
                            f"proj_lo={proj_lo}"))
            results.append(("woodies", "proj_spread",
                            "🟢 MATCH" if proj_hi > proj_lo else "🔴 MISMATCH",
                            f"proj_hi={proj_hi} > proj_lo={proj_lo}"))
        else:
            results.append(("woodies", "proj_hi", "⚪ NO_DATA", f"proj_hi={proj_hi}"))
            results.append(("woodies", "proj_lo", "⚪ NO_DATA", f"proj_lo={proj_lo}"))
    else:
        results.append(("woodies", "file", "🔴 MISMATCH", "woodies_5min.json NOT FOUND"))

    # --- TPO ---
    tpo = load_json("tpo.json")
    if tpo:
        results.append(("tpo", "version", "🟢 MATCH" if "p30.11" in tpo.get("version", "") else "🟡 DRIFT",
                         f"version={tpo.get('version')}"))

        sess = tpo.get("session", {})
        prev = tpo.get("previous_session", {})

        # Today session
        for name, val in [("poc", sess.get("poc")), ("vah", sess.get("vah")), ("val", sess.get("val"))]:
            if val is not None and val > 3000:
                results.append(("tpo", f"today_{name}", "🟢 MATCH", f"{val} (in MES range)"))
            elif val == 0 or val is None:
                results.append(("tpo", f"today_{name}", "🟡 DRIFT", f"{val} (zero/null — Sierra not calculated?)"))
            else:
                results.append(("tpo", f"today_{name}", "🔴 MISMATCH", f"{val} (out of range)"))

        results.append(("tpo", "va_ok", *check_bool(sess.get("va_ok"), True, "va_ok")))

        # Yesterday
        results.append(("tpo", "prev_found", *check_bool(prev.get("found"), True, "prev_found")))
        for name, val in [("y_poc", prev.get("poc")), ("y_vah", prev.get("vah")), ("y_val", prev.get("val"))]:
            if val is not None and 3000 < val < 10000:
                results.append(("tpo", name, "🟢 MATCH", f"{val} (valid MES)"))
            else:
                results.append(("tpo", name, "🔴 MISMATCH", f"{val} (invalid/corrupt)"))

        # VAH >= POC >= VAL consistency
        if prev.get("found") and all(prev.get(k) for k in ("poc", "vah", "val")):
            ok = prev["vah"] >= prev["poc"] >= prev["val"]
            results.append(("tpo", "y_ordering",
                            "🟢 MATCH" if ok else "🔴 MISMATCH",
                            f"VAH={prev['vah']} >= POC={prev['poc']} >= VAL={prev['val']}"))
    else:
        results.append(("tpo", "file", "🔴 MISMATCH", "tpo.json NOT FOUND"))

    # --- CVD ---
    cvd = load_json("cumulative_delta.json")
    if cvd:
        pts = cvd.get("points", [])
        interval = cvd.get("output_interval")
        no_t = sum(1 for p in pts if "t" not in p or p["t"] is None)
        results.append(("cvd", "output_interval", *verdict(interval, 300, 0, "output_interval")))
        results.append(("cvd", "points_with_t",
                         "🟢 MATCH" if no_t == 0 else "🔴 MISMATCH",
                         f"{no_t} points missing .t out of {len(pts)}"))
        results.append(("cvd", "point_count",
                         "🟢 MATCH" if len(pts) > 10 else "🟡 DRIFT",
                         f"{len(pts)} points"))
    else:
        results.append(("cvd", "file", "🔴 MISMATCH", "cumulative_delta.json NOT FOUND"))

    # --- Freshness ---
    now_ts = int(time.time())
    for name in ["woodies_5min.json", "tpo.json", "cumulative_delta.json", "live_price.json"]:
        d = load_json(name)
        if d:
            exp_ts = d.get("export_ts") or d.get("ts") or 0
            age = now_ts - int(exp_ts) if exp_ts else 999
            results.append(("freshness", name,
                            "🟢 MATCH" if age < 30 else "🟡 DRIFT" if age < 120 else "🔴 MISMATCH",
                            f"age={age}s"))
        else:
            results.append(("freshness", name, "🔴 MISMATCH", "file missing"))

    # --- Print + Log ---
    counts = {"🟢": 0, "🟡": 0, "🔴": 0, "⚪": 0}
    lines = []
    lines.append(f"P30 Sierra Match — {ts}")
    lines.append(f"{'System':<12} {'Field':<25} {'Verdict':<15} Detail")
    lines.append("-" * 90)
    for system, field, verd, detail in results:
        line = f"{system:<12} {field:<25} {verd:<15} {detail}"
        lines.append(line)
        for k in counts:
            if k in verd:
                counts[k] += 1

    lines.append("-" * 90)
    summary = f"TOTAL: {sum(counts.values())} checks | 🟢 {counts['🟢']} | 🟡 {counts['🟡']} | 🔴 {counts['🔴']} | ⚪ {counts['⚪']}"
    lines.append(summary)

    output = "\n".join(lines)
    print(output)

    log_path = LOG_DIR / f"sierra_match_{ts}.log"
    log_path.write_text(output)
    return counts, summary


if __name__ == "__main__":
    watch = "--watch" in sys.argv
    if watch:
        print("Watching mode — re-running every 30s. Ctrl+C to stop.\n")
        while True:
            try:
                run_check()
                print()
                time.sleep(30)
            except KeyboardInterrupt:
                break
    else:
        counts, summary = run_check()
