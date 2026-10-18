# -*- coding: utf-8 -*-
"""T-598 — add BE_AFTER_MFE_R_V1 (BRIEF §2.3 variant 1, default off) to scripts/fwd_harness.py by ONE atomic
rename: another session's hist_* sweep launches fwd_harness.py workers every ~30 s (cowork run 327, trap 38), so
the file is never left half-edited on disk — patch a copy, py_compile it, os.replace() it over the original."""
import os, py_compile, sys
ROOT = "/Users/michael/Downloads/mems26_web_git"
P = os.path.join(ROOT, "scripts", "fwd_harness.py")
src = open(P, encoding="utf-8").read()

def rep(old, new):
    global src
    n = src.count(old)
    assert n == 1, (n, old[:80])
    src = src.replace(old, new)

# 1. the flag block — after T-567c's
rep('_SLOT_RELEASE_STATS = {"checked": 0, "released": 0}\n',
    '_SLOT_RELEASE_STATS = {"checked": 0, "released": 0}\n'
    '# BE_AFTER_MFE_R_V1 (T-598, BRIEF §2.3 variant 1 — METHOD_AUDIT 05.10 (ז): "34% of the losers were at +1R before the\n'
    '# stop"; harness measurement, default off): at the close of a bar a FILLED, pre-T1 trade survived, if the MFE since the\n'
    '# fill bar (highs for LONG / lows for SHORT, this bar included) has reached R × the initial risk (|fill − initial stop|),\n'
    '# the stop moves to the fill price (BE) — tighten only, never widen, never flatten, effective from the NEXT bar (the live\n'
    '# counterpart would be a closed-bar MODIFY_STOP in bar_level_detector — NOT wired live; today\'s live protective BE is\n'
    '# "after T1", which a 1-contract ladder never reaches before the exit). Unset/0 ⇒ byte-identical replay.\n'
    '_BE_MFE_R = float(os.getenv("BE_AFTER_MFE_R_V1", "0") or 0)\n'
    '_BE_MFE_STATS = {"checked": 0, "moved": 0}\n')

# 2. the mechanism — after the T1→BE / all-legs-closed block, before the pre-T1 structure tighten
rep('        if all(l["exit"] for l in tr["legs"]):\n'
    '            _close_trade(tr, il)\n'
    '            continue\n'
    '        # STRUCTURE_EXIT_TIGHTEN_PRE_T1_V1 — at the close of a bar the trade survived, pre-T1 only (the live\n',
    '        if all(l["exit"] for l in tr["legs"]):\n'
    '            _close_trade(tr, il)\n'
    '            continue\n'
    '        # BE_AFTER_MFE_R_V1 (T-598) — at the close of a bar the filled trade survived, stop not yet at BE: MFE since\n'
    '        # the fill ≥ R × initial risk ⇒ stop → fill price, effective from the next bar (pure rule: be_after_mfe.py).\n'
    '        if _BE_MFE_R > 0 and tr.get("filled") and not tr["be_moved"]:\n'
    '            from backend.v9.services.trade_manager.be_after_mfe import be_stop_after_mfe\n'
    '            _BE_MFE_STATS["checked"] += 1\n'
    '            _fb = tr.get("fill_bar_index", bar_index)\n'
    '            _ns = be_stop_after_mfe(d, e, tr["stop"], tr["stop_initial"],\n'
    '                                    [float(BARS[i]["high"]) for i in range(_fb, bar_index + 1)],\n'
    '                                    [float(BARS[i]["low"]) for i in range(_fb, bar_index + 1)], _BE_MFE_R)\n'
    '            if _ns is not None:\n'
    '                tr.setdefault("tightened", []).append({"il": il, "from": float(tr["stop"]), "to": round(float(_ns), 2),\n'
    '                                                       "reason": f"be_after_mfe r={_BE_MFE_R}"})\n'
    '                tr["stop"] = float(_ns); tr["be_moved"] = True\n'
    '                _BE_MFE_STATS["moved"] += 1\n'
    '        # STRUCTURE_EXIT_TIGHTEN_PRE_T1_V1 — at the close of a bar the trade survived, pre-T1 only (the live\n')

# 3. the output — proof the mechanism ran (r=0 ⇒ off)
rep('    "slot_release": dict(_SLOT_RELEASE_STATS, bars=_SLOT_RELEASE_N, mfe_r=_SLOT_RELEASE_R),   # T-567c (bars=0 ⇒ off)\n',
    '    "slot_release": dict(_SLOT_RELEASE_STATS, bars=_SLOT_RELEASE_N, mfe_r=_SLOT_RELEASE_R),   # T-567c (bars=0 ⇒ off)\n'
    '    "be_after_mfe": dict(_BE_MFE_STATS, r=_BE_MFE_R),   # T-598 (r=0 ⇒ off)\n')

tmp = P + ".t598"
open(tmp, "w", encoding="utf-8").write(src)
py_compile.compile(tmp, doraise=True)
os.replace(tmp, P)   # atomic on APFS — a worker launching now sees either the old file or the whole new one
print("patched", P, "lines", src.count("\n"))
