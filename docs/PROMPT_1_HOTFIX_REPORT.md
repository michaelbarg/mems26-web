# PROMPT 1 HOTFIX — DLL Mac Paths (CrossOver Compat)

**Date:** 2026-05-11
**File:** `~/SierraChart/ACS_Source/MES_AI_DataExport.cpp`
**Note:** DLL source is outside the mems26_web_git repo — changes are local only.

---

## Lines Changed

| Line | Field | Old Value | New Value |
|------|-------|-----------|-----------|
| 32 | `V9_EXPORT_DIR` static | `C:\SierraChart_Data\v9_export\` | `/Users/michael/SierraChart_Data/v9_export/` |
| 1108 | `ExportPath` default | `C:\SierraChart2\Data\mes_ai_data.json` | `/Users/michael/SierraChart_Data/v9_export/mes_ai_data.json` |
| 1120 | `V9ExportPath` default | `C:\SierraChart_Data\v9_export\` | `/Users/michael/SierraChart_Data/v9_export/` |
| 1141 | `TradeCommandPath` default | `C:\SierraChart_Data\v9_export\trade_command.json` | `/Users/michael/SierraChart_Data/v9_export/trade_command.json` |
| 1144 | `TradeResultPath` default | `C:\SierraChart_Data\v9_export\trade_result.json` | `/Users/michael/SierraChart_Data/v9_export/trade_result.json` |

## Verification

```
grep -n "C:\\\\" ~/SierraChart/ACS_Source/MES_AI_DataExport.cpp
→ (no output — zero Windows paths remain)
```

## Michael Action Required

1. **Rebuild DLL** in Sierra Chart:
   Analysis menu → Build Advanced Custom Study DLL → Build
2. **Re-add Study** to chart (or just rebuild if study is still attached)
3. Verify Study Input defaults now show Mac paths

## Anti-Pattern Reference

This is **AP-T03: Windows paths in DLL** from the Anti-Patterns Log.
Rule: ALL paths in DLL = Mac native (`/Users/michael/...`), NEVER Windows (`C:\...`).
