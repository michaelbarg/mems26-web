#!/usr/bin/env python3
"""build_monolithic.py — cross-platform monolith generator for Sierra Chart remote build.

Windows-friendly twin of scripts/build_monolithic_cpp.sh (which needs bash).
Concatenates sc_study/{v9_types.h, v9_exports.h, v9_woodies_export.h,
MES_AI_DataExport.cpp} into ONE self-contained .cpp that Sierra's Remote Build
can compile. The merged file is .gitignored, so on a fresh clone (e.g. Windows)
you regenerate it locally with this script instead of copying it.

Usage:
  python scripts/build_monolithic.py
      -> writes sc_study/MES_AI_DataExport_merged.cpp

  python scripts/build_monolithic.py "<extra output path>"
      -> ALSO writes to that path (e.g. straight into Sierra's ACS_Source)

Windows example (writes straight into Sierra's build folder, correct name):
  python scripts\\build_monolithic.py "C:\\SierraChart\\ACS_Source\\MES_AI_DataExport.cpp"

Then in Sierra:  Analysis > Build Custom Studies DLL > Remote Build.
"""
import os
import re
import sys
import datetime

SRCDIR = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "sc_study"))
REQUIRED = ["v9_types.h", "v9_exports.h", "v9_woodies_export.h", "MES_AI_DataExport.cpp"]


def strip_lines(text, patterns):
    """Drop any line matching any regex in patterns (mirrors `grep -v -E`)."""
    rx = re.compile("|".join(patterns))
    return "\n".join(l for l in text.splitlines() if not rx.search(l))


def main():
    for f in REQUIRED:
        p = os.path.join(SRCDIR, f)
        if not os.path.isfile(p):
            sys.exit("ERROR: %s not found" % p)

    def read(name):
        with open(os.path.join(SRCDIR, name), encoding="utf-8") as fh:
            return fh.read()

    cpp = read("MES_AI_DataExport.cpp")
    m = re.search(r"v9\.[0-9]+\.[0-9]+", cpp)
    version = m.group(0) if m else "v9.2.0"

    types_h = strip_lines(read("v9_types.h"),
                          [r'#pragma once', r'#include "sierrachart\.h"'])
    exports_h = strip_lines(read("v9_exports.h"),
                            [r'#pragma once', r'#include "sierrachart\.h"', r'#include "v9_types\.h"'])
    woodies_h = strip_lines(read("v9_woodies_export.h"),
                            [r'#pragma once', r'#include "sierrachart\.h"', r'#include "v9_types\.h"', r'#include <cmath>'])
    main_cpp = strip_lines(cpp,
                           [r'#include "sierrachart\.h"', r'#include "v9_types\.h"',
                            r'#include "v9_exports\.h"', r'#include "v9_woodies_export\.h"', r'^SCDLLName'])
    main_cpp = re.sub(r'struct ImbLevel \{[^}]*\};', '', main_cpp)

    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    parts = [
        "// MES_AI_DataExport_merged.cpp — %s monolith for Sierra Chart remote build" % version,
        "// Generated %s by build_monolithic.py" % ts,
        "// CRITICAL: sierrachart.h + SCDLLName MUST be in first 10 lines",
        "",
        '#include "sierrachart.h"',
        "",
        'SCDLLName("MES_AI_DataExport")',
        "",
        "// ====== v9_types.h (inlined) ======",
        types_h,
        "",
        "// ====== v9_exports.h (inlined) ======",
        exports_h,
        "",
        "// ====== v9_woodies_export.h (inlined) ======",
        woodies_h,
        "",
        "// ====== ImbLevel struct (file scope — Bug #16 fix) ======",
        "struct ImbLevel { float price; float buy_vol; float sell_vol; float ratio; };",
        "",
        "// ====== MES_AI_DataExport.cpp main function ======",
        main_cpp,
    ]
    out = "\n".join(parts) + "\n"

    # ── verification (mirror the bash checks) ──
    lines = out.count("\n")
    scdll = len(re.findall(r'(?m)^SCDLLName\(', out))
    sierra = out.count('#include "sierrachart.h"')
    scdll_line = next((i + 1 for i, l in enumerate(out.splitlines()) if l.startswith("SCDLLName(")), 0)
    maintain_vap = out.count("MaintainVolumeAtPriceData")
    isnotempty = out.count("IsNotEmpty")
    fail = []
    if lines < 1400:
        fail.append("only %d lines (need >=1400)" % lines)
    if scdll != 1:
        fail.append("SCDLLName appears %dx (need 1)" % scdll)
    if sierra != 1:
        fail.append('sierrachart.h appears %dx (need 1)' % sierra)
    if scdll_line > 10:
        fail.append("SCDLLName at line %d (must be <=10)" % scdll_line)
    if maintain_vap < 1:
        fail.append("MaintainVolumeAtPriceData missing")
    if isnotempty > 0:
        fail.append("IsNotEmpty still present (not valid ACSIL)")
    if fail:
        sys.exit("VERIFICATION FAILED — monolith NOT safe to deploy:\n  - " + "\n  - ".join(fail))

    default_out = os.path.join(SRCDIR, "MES_AI_DataExport_merged.cpp")
    targets = [default_out] + sys.argv[1:]
    for t in targets:
        with open(t, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(out)
        print("WROTE %s  (%d lines, SCDLLName@line%d)" % (t, lines, scdll_line))
    print("OK")


if __name__ == "__main__":
    main()
