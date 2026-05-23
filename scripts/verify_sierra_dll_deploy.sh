#!/bin/bash
# verify_sierra_dll_deploy.sh — confirm Sierra source/DLL/export alignment
set -euo pipefail

EXPORT="${V9_EXPORT_DIR:-$HOME/SierraChart_Data/v9_export/woodies_5min.json}"
PRIMARY_CPP="$HOME/SierraChart/ACS_Source/MES_AI_DataExport.cpp"
PRIMARY_DLL="$HOME/SierraChart/Data/MES_AI_DataExport_64.dll"
SECONDARY_CPP="$HOME/SierraChart2/ACS_Source/MES_AI_DataExport.cpp"

echo "=== Sierra DLL deploy verify ==="
echo "Running app: CrossOver → Y:\\SierraChart (maps to ~/SierraChart)"
echo ""

for pair in \
  "Primary cpp|$PRIMARY_CPP" \
  "Primary dll|$PRIMARY_DLL" \
  "Secondary cpp|$SECONDARY_CPP"; do
  label="${pair%%|*}"
  path="${pair#*|}"
  if [ -f "$path" ]; then
    stat -f "%Sm  $label: $path" "$path"
  else
    echo "MISSING  $label: $path"
  fi
done

echo ""
if [ -f "$PRIMARY_CPP" ] && [ -f "$PRIMARY_DLL" ]; then
  cpp_epoch=$(stat -f '%m' "$PRIMARY_CPP")
  dll_epoch=$(stat -f '%m' "$PRIMARY_DLL")
  if [ "$dll_epoch" -lt "$cpp_epoch" ]; then
    echo "STATUS: DLL OLDER than source — Remote Build needed in Sierra (Analysis → Build Custom Studies DLL)"
  else
    echo "STATUS: DLL mtime >= source (build likely current)"
  fi
fi

echo ""
if grep -q 'v9_sc_datetime_to_unix(sc.BaseDateTimeIn\[b\])' "$PRIMARY_CPP" 2>/dev/null; then
  echo "SOURCE: woodies bar timestamp fix PRESENT in ~/SierraChart/ACS_Source"
else
  echo "SOURCE: woodies bar timestamp fix MISSING — run ./scripts/build_monolithic_cpp.sh --deploy"
fi

if [ -f "$SECONDARY_CPP" ]; then
  if grep -q 'v9_sc_datetime_to_unix(sc.BaseDateTimeIn\[b\])' "$SECONDARY_CPP" 2>/dev/null; then
    echo "SOURCE: SierraChart2 cpp synced"
  else
    echo "SOURCE: SierraChart2 cpp STALE (not used by CrossOver, but confusing if opened there)"
  fi
fi

echo ""
if [ -f "$EXPORT" ]; then
  python3 - <<'PY'
import json, os, time
from pathlib import Path
p = Path(os.environ.get("EXPORT", str(Path.home() / "SierraChart_Data/v9_export/woodies_5min.json")))
d = json.load(open(p))
hist = d.get("history") or []
ts = [b.get("ts") for b in hist]
age = time.time() - p.stat().st_mtime
print(f"EXPORT: {p}")
print(f"  age_s={age:.1f} version={d.get('version')} history={len(hist)} unique_ts={len(set(ts))}")
if len(set(ts)) <= 1 and len(hist) > 1:
    print("  FAIL: all history bars share one ts — OLD DLL still running")
elif len(hist) > 1:
    print(f"  OK: timestamps span {ts[0]} .. {ts[-1]}")
cb = d.get("current_bar") or {}
print(f"  current cci={cb.get('cci_14')} proj_hi={cb.get('proj_hi')} sierra_source={cb.get('sierra_source')}")
PY
else
  echo "EXPORT: woodies_5min.json not found"
fi
