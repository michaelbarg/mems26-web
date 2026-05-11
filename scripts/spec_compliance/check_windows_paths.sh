#!/usr/bin/env bash
# AP-T03: No Windows paths in DLL source
set -euo pipefail
DLL="$HOME/SierraChart/ACS_Source/MES_AI_DataExport.cpp"
if [[ ! -f "$DLL" ]]; then
    echo "SKIP: DLL source not found"
    exit 0
fi
# Exclude comments (lines starting with //)
hits=$(grep -vE '^\s*//' "$DLL" | grep -n 'C:\\' || true)
if [[ -n "$hits" ]]; then
    echo "FAIL: Windows paths found in DLL (AP-T03):"
    echo "$hits"
    exit 1
fi
echo "PASS: No Windows paths in DLL code"
