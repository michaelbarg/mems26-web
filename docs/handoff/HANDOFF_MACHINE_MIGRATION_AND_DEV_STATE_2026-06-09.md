# HANDOFF — מעבר-מחשב + מצב-פיתוח (אפיון + משימות) · 2026-06-09

**מטרה כפולה:** (1) להעביר את מחסנית-MEMS26 למחשב חדש שיהיה סביבת-העבודה, ו-(2) שכל
הפיתוח הפתוח יעבור איתה **כאפיון + רשימת-משימות** — כך שמ-Cowork על המחשב החדש ממשיכים
בלי לאבד הקשר. **אני (Cowork) לא מבצע את ההעברה — היא על המכונות שלך; זה צ'קליסט לך/ל-CC.**

> **מסמכי-תשתית קיימים (KEEP — לא משוכפלים כאן):** בצע את שלבי-התשתית מתוך
> `docs/runbooks/MIGRATION_TO_NEW_MACHINE.md` (§1–7, מלא) או `docs/handoff/CC_NEW_MACHINE_SETUP_2026-06-08.md`
> (גרסת-CC self-contained). מודל שתי-מכונות-Tailscale הוא **חלופה אחרת** — `docs/runbooks/TWO_MAC_TAILSCALE_SETUP.md`;
> אם המטרה היא "להעביר ולעבוד מהמחשב החדש" (לא split prod/dev), המסמך הזה גובר.

---

## 0 · ⛔ שער-חובה לפני כל clone — אחרת מאבדים את כל העבודה

המעבר מבוסס `git clone`. בדיקת-Cowork 2026-06-09 (מהסנדבוקס):

| סיכון | מצב נוכחי | פעולה לפני clone |
|-------|-----------|-------------------|
| **commits לא-דחופים** | הענף `stabilize/mems26-local-truth-2026-05-16` **26 commits לפני origin** (HEAD=`23163d9`, כולל **כל 4 תיקוני-הבאגים**). `CC_NEW_MACHINE` עדיין מצביע על `75bc08d` הישן. | `git push origin HEAD` מה-**Mac** → ודא `git status` מראה `ahead 0`. |
| **קבצי-קוד untracked** | `frontend/v9/src/v9/components/build_status/ReadinessHeader.tsx` · `scripts/pattern_watch.py` · `scripts/research/verify_cvd_atr_availability.py` — **לא ב-git** → לא יעברו ב-clone. | commit + push, או החלט-במפורש שהם disposable. |
| **ROADMAP modified** | `docs/plans/ROADMAP_TO_LIVE.html` שינוי לא-committed. | commit + push (חלק מ-T4). |
| **~300 מסמכים untracked** | רוב `docs/reports/*` · `docs/handoff/*` · `docs/plans/*` לא ב-git (כולל ההאנד-אוף הזה + דוח-החקירה + `ISSUES_AND_RECOMMENDATIONS`). | החלט: commit את אלה שצריך לשמר (לפחות החקירה, ה-issues, ההאנד-אופים הפעילים, ה-STATUS_BOARD/ROADMAP). השאר אפשר לוותר. |

**כלל:** הסנדבוקס של Cowork **חסום מ-git remote** (`github-mems26:22 Forbidden`) — אני לא יכול
לדחוף. ה-push חייב לרוץ מה-Mac. **אל תתחיל clone במחשב החדש לפני אישור `ahead 0` + הקבצים הקריטיים ב-origin.**

---

## 1 · תמצית-תשתית (מצביע למסמכים הקיימים)

הסדר המלא ב-`MIGRATION_TO_NEW_MACHINE.md`. תקציר השלבים + העדכונים הנדרשים:

1. **קדם:** macOS · Python 3.9.7 · Node 23.x/npm 10.x · `brew install postgresql@16 screen` · CrossOver.
2. **Repo:** `git clone` (אחרי §0!) → `git checkout stabilize/mems26-local-truth-2026-05-16` →
   ❗`git log --oneline -1` חייב להראות את ה-HEAD ה**מעודכן** (לא `75bc08d`) → `pip3 install -r requirements.txt --break-system-packages` → `cd frontend/v9 && npm install`. **אל תעתיק** `node_modules`/`__pycache__`/`*.pyc`.
3. **Secrets ידני-מאובטח (לא ב-git):** `.env` (חובה: `DATABASE_URL=postgresql://localhost/mems26` · `MEMS26_MODE=shadow` · `CLOUD_URL=http://localhost:8000` · 7 דגלי-הכיול + `BRIDGE_TOKEN`) · `frontend/v9/.env.local`.
4. **DB:** `createdb mems26` → `./scripts/db_init.sh` (נקי, מומלץ — דאטת-עבר disposable). **localhost בלבד, לעולם לא cloud-PG.**
5. **Sierra+DLL (ידני, הארוך):** CrossOver+Sierra · chart#5 (MES)+studies · `~/SierraChart_Data/v9_export/` + Study **Input 4** = הספרייה · `./scripts/build_monolithic_cpp.sh --deploy` → Remote Build → reload · `./scripts/verify_sierra_dll_deploy.sh`.
6. **LaunchAgent (אל תשנה!):** `CLOUD_URL=http://localhost:8000` · `export V9_DISABLE_WATCHDOG=1` · KeepAlive מותנה (`SuccessfulExit=false`). עדכן נתיב-repo + `V9_EXPORT_DIR`.
7. **אם שם-משתמש ≠ `michael`:** `grep -rln "/Users/michael" scripts/ ~/Library/LaunchAgents/ ~/Documents/Claude/Scheduled/` ועדכן (לא לגעת ב-`CLOUD_URL`).
8. **אימות-GO:** כתוב `docs/reports/NEW_MACHINE_VERIFY.txt` — health 200 · בריג' push · frontend :3000 · Sierra fresh<1s · soak-PG מקבילי 0-errors ≥10דק'.

---

## 2 · אפיון מצב-הפיתוח (מה הושלם / מה פתוח)

### 2a · נסגר ב-קוד + committed (טרם אומת end-to-end)
4 באגים שמנעו ירי, + ניתוק S2⟂S3 — כולם committed (ראה §0 — חייבים push):

| Commit | מה | סטטוס-אימות |
|--------|-----|-------------|
| `638e664` | S2⟂S3 — COT/AMT מאחורי `S2_REQUIRE_COT_AMT` (default off) | ✅ code-review Cowork |
| `0bc1d20` | #1 S4 stop=None → stop אמיתי דרך `compute_stop` | ✅ code; ⚠️ end-to-end חסר |
| `2aef154` | #3 S2 detection על `buffer[:-1]` (בר מושלם) | ⚠️ **חלקי** — inspector לא יושר |
| `23163d9` | #2/#4 ts-parse עמיד (S2 persist + Woodies write) | ✅ code; ⚠️ ללא טסט |

### 2b · החלטות-קבע (PERMANENT עד ש-Michael מבטל בכתב)
מ-`CLAUDE.md §Standing Decisions`: S2 `choppiness_ok` OFF · Layer-0 chop veto OFF ·
`tick_reversal_15`/`tpo` non-critical · **S2 ⟂ S3 (COT/AMT לא נדרש)**. **אסור** להדליק אף
דגל default-off בלי אישור-Michael — גם לא ב-clone/refactor/migration.

---

## 3 · רשימת-המשימות (Master Worklist — ממשיכים מ-Cowork על המחשב החדש)

מקורות: ביקורת-Cowork (8 פערים) + `ISSUES_AND_RECOMMENDATIONS_2026-06-09.txt` (7 בעיות) +
`CC_MEGA_BUGFIX_4`. פרומפט-הפערים המלא: `docs/handoff/CC_EXPLAIN_AND_CLOSE_GAPS_2026-06-09.md`.

| # | משימה | עדיפות | בעלים | אימות | סטטוס |
|---|-------|--------|-------|-------|-------|
| **T1** | Inspector = engine (display תוצאת-engine / יישור b4→מושלם). מאומת: inspector קורא in-memory `_bar_buffer` (`s2_inspector.py:125`) ומריץ `compute_stop` על `[-1]` חלקי (`:346`) — **לא** מ-DB. | **P0** | CC | `inspector.b4==engine.b4` raw | 🟡 פרומפט נשלח |
| **T2** | טסטי-regression אמיתיים #1/#2/#3/#4 (קוראים לנתיב; #3 הנוכחי טאוטולוגי; #2/#4 ללא טסט; #1 לא מפעיל `process_bar`). RED-on-revert ע"י `git stash`. | **P0** | CC | `pytest` גולמי בשני המצבים | ⬜ |
| **T3** | Flag-gate ל-#3 + דוח-תיקון עם `pytest` גולמי (Rule 5) + NOT-DONE; רענון השורה ה-stale בדוח-החקירה. | P1 | CC | קריאת-דוח | ⬜ |
| **T4** | ROADMAP + STATUS_BOARD (שורת-לוג finding→fix→verification לכל באג) + `gen_index.py` לקבצי-טסט חדשים. | P1 | Cowork+CC | diff | 🟡 בעבודה |
| **T5** | אימות-ירי-חי RTH (§6.2) — ZLR/Reactive **באמת יורים**: `active_patterns` + שורות ב-`v9_trades`. 4 צירי-UAT. | P0-gate | CC | raw + DB | ⬜ (אחרי T1+T2) |
| **T6** | Triage מערכתי (להלן). trading-logic → STRATEGIC-STOP + אישור-Michael. | mixed | CC+Michael | טבלת-triage | ⬜ |

**T6 — פירוט (אל תממש trading-logic בלי אישור-Michael):**
- **בעיה 6 [P0]** CCI של Python ≠ DLL (פער 1.8 → מפספס ZLR). אבחן-קודם; §Sierra ⇒ להשתמש ב-CCI מה-export. STRATEGIC.
- **בעיה 3 [P1]** Double-Top יורה 43× (דטקטורים stateless). dedup ברמת-engine (`last_fire_pattern_id+ts`). STRATEGIC.
- **בעיה 4 [P1]** `ensure_iso_ts` מרכזית + audit רוחבי לכל `safe_execute` שמעביר ts (11+ טבלאות). לא-fire-path.
- **בעיה 2 [P2]** מודל `on_bar_close` מפורש (במקום convention של `buffer[:-1]`).
- **בעיה 1 [P2]** לכייל Python ZLR/HFE מול DLL ואז לבטל DLL-fallback (תלוי בבעיה 6).
- **בעיה 7 [—]** Initiative expansion calibration — **החלטת-Michael, לא באג.** לא לגעת.

---

## 4 · מודל-עבודה מהמחשב החדש
- **Cowork (המחשב החדש) = orchestrator + verifier בלתי-תלוי.** מנפק תת-פרומפט אחד למשימה,
  מצליב פלט-גולמי (Rule 5: פקודה+פלט, לא "confirmed"), מעדכן boards, מאשר לפני fire-path.
- **CC (על ה-Mac) = executor.** קוד, טסטים, ריצות-RTH. מדביק ראיות גולמיות.
- **לולאה:** T1→T2→T3→T4 → (אחרי T1+T2 חיים) → T5 RTH → T6 triage לפי אישור-Michael.
- **שערים-אסטרטגיים:** כל שינוי-fire-path/trading-logic = STRATEGIC-STOP + אישור-Michael.

## 5 · הצעד הראשון על המחשב החדש
1. ודא §0 הושלם (push `ahead 0` + קבצי-קוד ב-origin) — אחרת עצור.
2. הקם תשתית (§1) → `NEW_MACHINE_VERIFY.txt` GO.
3. המשך מ-**T1** (פרומפט מוכן ב-`CC_EXPLAIN_AND_CLOSE_GAPS_2026-06-09.md`) → צליבה → T2…
