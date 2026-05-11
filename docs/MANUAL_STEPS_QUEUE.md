# MEMS26 — Manual Steps Queue (Sierra Chart)
# Terminal 2 queues steps here. Michael processes when available.

## PENDING

### STEP 1: Sierra Build + Re-add Study (for T2.1 + T2.2 + T2.3)
- Action: Build Custom Studies DLL in Sierra Chart
- Then: Re-add Study to chart (Analysis → Studies → Add → "MES AI Data Export v9.2.0")
- Then: Configure NEW Inputs:
  - Input 10: "Live Price Export (1=on)" → 1
  - Input 11: "Live Price Interval (ms)" → 200
  - Input 12: "Trade Command JSON Path" → Y:\SierraChart_Data\v9_export\trade_command.json
  - Input 13: "Trade Result JSON Path" → Y:\SierraChart_Data\v9_export\trade_result.json
- Verify after:
  ```
  ls -la ~/SierraChart/Data/v9_export/live_price.json
  ls -la ~/SierraChart/Data/v9_export/reversal_cluster.json
  ```
  Both files should have mtime < 5 seconds old during market hours.

### STEP 2: Verify live_price.json is being written (Prompt 1)
- Prerequisite: STEP 1 completed
- Check: `ls -la ~/SierraChart_Data/v9_export/live_price.json`
- Expected: file updates every ~200ms during market hours
- If missing: ensure "Live Price Export (1=on)" is set to 1 in study inputs

## COMPLETED
(none yet)
