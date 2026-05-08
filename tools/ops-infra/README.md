# MEMS26 Backup & Restore

## What Gets Backed Up

| Component | Source | Contents |
|-----------|--------|----------|
| Bridge | `~/Documents/GitHub/mems26-web/bridge/` | Python bridge scripts, config |
| Sierra Data | `~/SierraChart2/Data/` | Historical chart data |
| Sierra Config | `~/SierraChart2/SierraChart.ini` | Sierra Chart settings |
| Sierra Studies | `~/SierraChart2/Studies/` | Custom studies (MES_AI_DataExport) |
| AI Export | `~/SierraChart2/mes_ai_data.json` | Current Sierra export file |
| Git State | (generated) | Recent commits, branches, stashes |

## Backup Location

`~/mems26-backups/<YYYYMMDD_HHMMSS>/`

Keeps last 14 backups (2 weeks of daily runs).

## Usage

### Manual Backup
```bash
cd tools/ops-infra
chmod +x backup_local.sh
./backup_local.sh           # Full backup
./backup_local.sh --dry-run # Preview only
```

### Restore
```bash
chmod +x restore_from_backup.sh
./restore_from_backup.sh                        # List available backups
./restore_from_backup.sh 20260508_020000        # Restore everything
./restore_from_backup.sh 20260508_020000 --component bridge  # Bridge only
./restore_from_backup.sh 20260508_020000 --component sierra  # Sierra only
```

Existing files get a `.pre-restore-YYYYMMDD` suffix before overwrite.

### Automated Daily Backup (launchd)

The plist file `com.mems26.backup.plist` runs backup daily at 2:00 AM.

**To install** (Michael only):
```bash
cp com.mems26.backup.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.mems26.backup.plist
```

**To uninstall:**
```bash
launchctl unload ~/Library/LaunchAgents/com.mems26.backup.plist
rm ~/Library/LaunchAgents/com.mems26.backup.plist
```

**Logs:**
- stdout: `/tmp/mems26-backup.log`
- stderr: `/tmp/mems26-backup-error.log`

## What Is NOT Backed Up

- `.env` files (secrets — managed separately)
- `node_modules/`, `__pycache__/` (regenerable)
- Redis data (Upstash cloud — has its own persistence)
- Frontend/backend deployments (Netlify/Render — deployed from git)
