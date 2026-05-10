# DLL v9.1.2 Fix — Path + CPU Exception

## Bugs Fixed

### 1. Path: Y:\ → Mac native
Sierra on Mac/CrossOver: `Y:\` is a symlink that triggers "File compression not supported" errors.

Changed default paths:
- `Y:\SierraChart\Data\mes_ai_data.json` → `/Users/michael/SierraChart/Data/mes_ai_data.json`
- `Y:\SierraChart\Data\v9_export\` → `/Users/michael/SierraChart/Data/v9_export/`
- `C:\SierraChart_Data\v9_export\` (V9_EXPORT_DIR constant) → same Mac path

User can override via Study Settings in Sierra Chart.

### 2. CPU Exception: ImbLevel struct scope
`struct ImbLevel` was defined inside the function body, then used for a `static std::vector<ImbLevel>`. MSVC may fail runtime initialization of static local variables with function-local types.

Fix: moved `struct ImbLevel` to file scope (before `scsf_MES_AI_DataExport`).

### 3. CPU Exception: v9_detect_zlr null guard
`cci14_hist.data()` can return nullptr if the vector is empty. Added explicit guards:
```cpp
if (!cci14_hist.empty() && bi + 1 > 0) {
    zlr = v9_detect_zlr(cci14_hist.data(), bi + 1, 12);
}
```

### 4. AddMessageToLog parameter
Changed from `1` (auto-show log window) to `0` (silent log). Per SKILL.md: "sc.AddMessageToLog → only on errors".

## Version
v9.1.1 → v9.1.2
