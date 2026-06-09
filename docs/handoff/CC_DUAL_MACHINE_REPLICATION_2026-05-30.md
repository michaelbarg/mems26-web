# CC משימה (דחויה) — שכפול המערכת ל‑2 מחשבים

> ⏸️ **לא לבצע עכשיו.** משימה זו מתחילה **רק על פי אות מפורש מ‑Michael** ("תתחיל את
> שכפול 2 המחשבים"). עד אז — להשאיר כפריט מתוכנן בלבד ב‑ROADMAP/STATUS_BOARD.

**תאריך:** 2026-05-30 · **כותב:** Cowork.
**מטרה:** מחשב A (ה‑Mac הנוכחי) = פיתוח/עבודה. מחשב B = מסחר רציף (SHADOW/DEMO עכשיו,
LIVE רק כשהחוסמים ייסגרו). שני המחשבים מריצים **stack מלא ומקומי** (bridge→backend→DB→
frontend), כל אחד על `localhost` בלבד (CLAUDE.md § Bridge Local-Only).

## 0. תנאי כניסה — לא LIVE, ולא לפני סגירת חוסמים
מחשב B יריץ **SHADOW/DEMO 24/7**, לא LIVE, עד שכל החוסמים ב-ROADMAP §1 נסגרו (כולל
frozen-tail deep-fix + TZ tick_reversal + footprint dedup + fake-5900 + gateway/RiskValidator).
**אסור** להפעיל מסחר רציף לפני כן — אחרת B ייצר 24/7 את אותו רעש. "24/7" בפועל = שעות
החוזים (ראשון 18:00 ET → שישי 17:00 ET, עם הפסקת תחזוקה יומית 17:00–18:00 ET).

## 1. מה לשכפל (Inventory)

| רכיב | מקור (A) | הערה לשכפול ל-B |
|------|----------|------------------|
| Repo | `/Users/michael/Downloads/mems26_web_git` | `git clone` + checkout אותו commit. לא להעתיק `.git` ידנית |
| `.env` | UPSTASH_REDIS, BRIDGE_TOKEN, V9_EXPORT_DIR, CLOUD_URL | צור מחדש על B. `CLOUD_URL=http://localhost:8000` **חובה** |
| `.env.local` (frontend) | NEXT_PUBLIC_API_URL/WS_URL/BRIDGE_TOKEN | localhost |
| DB | `data/mems26_local.db` | **DB נקי ונפרד ל-B!** אל תעתיק את DB הפיתוח (זיהום עסקאות/state). migrations מאפס |
| Sierra + DLL | `~/SierraChart/ACS_Source/` + `~/SierraChart_Data/v9_export/` | התקן Sierra (CrossOver) על B, deploy אותו DLL (אותה גרסה) |
| Scripts/LaunchAgent | `scripts/start_all.sh`, `com.mems26.bridge.plist` | מגיע עם ה-repo; התקן LaunchAgent על B |

## 2. אילוצי בידוד (אסור לפספס)
- כל מחשב **עצמאי על localhost** — bridge של אחד לא דוחף ל-IP של השני/לענן (CLAUDE.md:
  bridge מסרב לעלות אם `CLOUD_URL` != localhost/127.0.0.1).
- **DB נפרד לחלוטין** לכל מחשב. אין שיתוף sqlite דרך רשת.
- **אותה גרסת DLL** בשני המחשבים — אמת `scripts/verify_sierra_dll_deploy.sh`.
- אותו commit (או B מאחורי A בכוונה) — אמת `git rev-parse HEAD`.

## 3. צעדי הקמה על מחשב B (runbook)
```
1. דרישות: macOS, Python 3.9.x, Node 23.x, CrossOver+Sierra Chart, screen.
2. git clone <repo> ; git checkout <commit>
3. pip install -r requirements.txt --break-system-packages ; (cd frontend/v9 && npm ci)
4. צור .env + .env.local (localhost, BRIDGE_TOKEN מקומי)
5. אתחל DB נקי: migrations (לא להעתיק DB מ-A)
6. התקן Sierra, פתח Chart 12 (Woodies), deploy DLL (אותה גרסה), Input 18 לפי הכרעת frozen-tail
7. bash scripts/check_env.sh
8. bash scripts/start_all.sh
9. curl localhost:8000/health ; python3 scripts/sot_health.py --strict
10. התקן LaunchAgent (conditional KeepAlive, V9_DISABLE_WATCHDOG=1) לחיים אחרי reboot
```

## 4. שיקולי 24/7 (מחשב B ללא השגחה)
- Auto-restart: LaunchAgent conditional KeepAlive (CLAUDE.md § LaunchAgent Stability).
- יציבות אחרי reboot: P30 stability controls.
- ניטור מרחוק: דרך לראות את B מ-A (health ב-LAN לקריאה בלבד / sot_health מתוזמן).
  **קריאה בלבד — לא לפתוח את ה-bridge החוצה.**
- הפסקת תחזוקה יומית (17:00–18:00 ET): ודא התאוששות אוטומטית כשהפיד חוזר.

## 5. שאלות ל-Michael לפני שמתחילים (לשאול, לא לנחש)
1. מערכת ההפעלה של B — Mac נוסף? (כל הנתיבים/CrossOver מניחים macOS)
2. רישיון Sierra + פיד נתונים נפרד ל-B? (אותו חשבון/feed?)
3. גישה מרחוק לניטור — VNC/SSH/Tailscale?
4. B יריץ SHADOW או DEMO ראשון? (LIVE רק אחרי שער P-L0)

## 6. אימות
- שני stacks עולים עצמאית; `health`=200 בשניהם; `sot_health --strict` ירוק.
- `verify_sierra_dll_deploy.sh` — אותה גרסת DLL.
- DB של B נקי (0 עסקאות seed/5900, 0 future-ts).
- bridge של B דוחף **רק** ל-localhost (`/tmp/bridge.err.log` ל-`https://` → ריק).

## מקורות
`scripts/start_all.sh` · `scripts/check_env.sh` · `scripts/verify_sierra_dll_deploy.sh` ·
`scripts/build_monolithic_cpp.sh` · `docs/ENVIRONMENT.md` · `~/Library/LaunchAgents/com.mems26.bridge.plist` ·
CLAUDE.md §§ Bridge Local-Only · LaunchAgent Stability · Service Bring-Up.
