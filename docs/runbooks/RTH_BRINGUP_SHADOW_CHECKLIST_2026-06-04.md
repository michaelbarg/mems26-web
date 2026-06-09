# RTH Bring-Up + Verification Checklist — פתיחת SHADOW על PG | 2026-06-04

מטרה: ב-RTH הבא, להעלות את ה-stack על Postgres ולאמת שהכל חי ונכון — כולל מבחן-האמת של ירי S2.
מצב: DB סגור (PG) · 3 תיקוני-firing בוצעו ואומתו (S1 fallback, D-090 observer, S2 VSA enable) · ירי-S2-חי טרם הוכח.
Mac-side = Michael/CC. אחרי כל שלב — Cowork מצליב (raw).

## שלב 0 — לפני RTH (bring-up)
- [ ] backend רץ על PG: `DATABASE_URL=postgresql://localhost/mems26` (לא SQLite). אמת `SELECT 1`.
- [ ] בדוק שאין מאזינים כפולים על `127.0.0.1:3000`/`8000` (להימנע מ-instance כפול).
- [ ] bridge רץ, `CLOUD_URL=http://localhost:8000` (Local-Only), `/tmp/bridge.err.log` נקי מ-"API push FAILED".
- [ ] Sierra מחובר לפיד; ה-export JSONs ב-`~/SierraChart_Data/v9_export/` מתעדכנים.
- [ ] דגלים פעילים: `S2_VSA_VOLUME=1` (env בזמן ריצה, לא רק plist) + שאר דגלי-SHADOW.

## שלב 1 — feed חי (אחרי פתיחת RTH)
- [ ] `MAX(ts) FROM v9_bars_5min` ב-**PG** מתקדם תוך דקות (2 קריאות).
- [ ] ⚠️ **frozen-tail:** `5min.json` — מערך-הברים מתקדם (לא רק mtime). אם תקוע → Reload Study (ידני). **אם חוזר תכופות = הצעד הבא הופך ל-auto-recovery.**
- [ ] בר אחרון בתוך RTH (עובר גייט B4).

## שלב 2 — כתיבות PG (split-brain fix מאומת חי)
- [ ] `COUNT(*)` עולה ב-**PG** ל: `v9_bars_5min`, `v9_bars_5min_woodies` (S4), `v9_day_type_state` (S1), `v9_bars_cumulative_delta`, `v9_tpo_*`.
- [ ] `data/mems26_local.db` mtime **לא** זז (אין split-brain).
- [ ] איכות: 0 ברי is_synthetic=0 עם vol≥100K (גייט axis4/B4 מחזיק חי).

## שלב 3 — firing per-system
- [ ] **S2 (מבחן-האמת):** האם נורה setup? `SELECT * FROM v9_five_min_setups` — שורות עם `variant_tag`/`variants_passed`. אם 0 → לאמת שהתנאים הנוספים (COT/AMT, b1/b3/b4, belly) נבדקו, לא שהגייט חוסם.
- [ ] **S1:** observer — `v9_day_type_state` מתעדכן (classification חי), **אבל 0 signals** מ-S1 (D-090). אמת `v9_system_signals WHERE system_id=1 = 0`.
- [ ] **S4:** woodies בר נכתב ל-PG (6b fix) + fires אם יש.
- [ ] **S3:** מושבת (footprint) — אמת שאין כתיבה/ירי לא-צפוי.

## שלב 4 — דאשבורד + נראות
- [ ] פאנלים מציגים נתון חי מ-PG (לא ריק/stale). build-status מציג armed/blocked/fired אמיתי.
- [ ] עמוד trades מציג עסקאות מ-PG (אם נורו).
- [ ] **P0-2 consistency:** לעסקה שנורתה — ה-`stop`/`r_t1` שמוצג ב-build-status == ה-`stop`/`r_t1` שהמנוע השתמש בו בפועל (raw, אותו ערך). (acceptance שטרם אומת חי.)

## שער GO ל-SHADOW soak
- [ ] feed מתקדם · כתיבות ל-PG (לא SQLite) · S1 observer (0 signals) · S2 גייט פעיל · איכות נקייה.
- [ ] אם הכל ✓ → **SHADOW soak מתחיל** (יום 1). מעקב יומי: WR · setups · S2 variants pass · frozen-tail.

## אחרי השלב — להעביר ל-Cowork (raw) להצלבה
ספירות PG פר-טבלה · `v9_five_min_setups` (S2) · `system_signals WHERE system_id=1` (אמור 0) · SQLite mtime · דגימת is_synthetic.
