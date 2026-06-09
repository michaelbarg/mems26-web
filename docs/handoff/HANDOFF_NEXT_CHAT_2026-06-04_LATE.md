# Cowork Handoff — Next Chat (2026-06-04 late) — config-tunable done, designs cross-checked, gate = RTH bring-up

**אתה (Cowork chat הבא):** orchestrator + verifier בלתי-תלוי. CC מבצע על ה-Mac; אתה כותב פרומפטים, **מצליב (Rule 5: פקודה+פלט גולמי)**, מעדכן בורדים.
**לא** שולט backend/launchctl/Sierra/RTH מה-sandbox · **לא** מגיע ל-PG של ה-Mac → ספירות-PG נשענות על raw של CC; אתה מאמת **קוד/git/constraints**.
CC נטה ל-over-claim → **תמיד הצלב** (תפסנו השבוע: woodies upsert · split-brain · אבחון-על-DB-שגוי · grep-S2 שגוי · S4-ticks mirror-אינרטי · staleness מסמכי-מעצב). הצלבות אחרונות נקיות.

## 0 · הנחיות-על
`CLAUDE.md` (§DB=Postgres · §Bridge Local-Only · §Pre-LIVE · §Source-of-Truth) · `CC_HANDOFF_CONTRACT.md` · זיכרון: [[project-postgres-migration]] · [[project-config-tunable-stop-exits-contracts]] · roadmap auto-update · **אין present_files לקבצי-מעקב**.
מקור-אמת: `docs/plans/STATUS_BOARD.md` + `ROADMAP_TO_LIVE.html` ("מה לבצע" P1–P5 ב-banner; לוג 1/1b/1c מקופל).

## 1 · ✅ נסגר ואומת (Cowork) — DB + firing + config + designs
- **DB מלא על PG:** migration+constraints+tests+axis4/6b+**split-brain** (`69744bb`). corruption חוסל.
- **S1/S2 firing:** S1 atr-fallback (`9cac12f`) · D-096 observer (`d785b2c`/`48f9bdd`) · S2 VSA enable (`5343755`).
- **frozen-tail watchdog** (`11e82e9`) · **P0-2 backend** חשיפת stop/r_t1 (`8eb5747`) · **P0-2 frontend** BuildTreeView מרנדר חי + de-trust הוסר (`66bd45c`).
- **config→YAML (Michael: stop+exits+contracts גמישים):** round-trip 0-שינוי-ערכים אומת (`182862b`) · S2 firing-variant knob 5-ערכים (`e72883c`) · **S4 ticks חוּוטו reload-proof** (`e41ac5d`). חי-YAML: S2 stop · auth · targets · min_r_t1 · S4 ticks.
- **2 תוצרי מעצבים הוצלבו (Rule 1 נקי):** Trades redesign (design-only) · Build-Status (BuildTreeView committed; **cull מאומת בטוח + מאושר אופציה A** — prompt `CC_PROMPT_BUILD_STATUS_CULL_2026-06-04.md` מוכן: port→swap→delete, Build חי ב-`/build` בלבד).

## 2 · 🟢 הצעד המיידי (הגייט לפתיחת SHADOW): P1 bring-up ב-RTH
Mac-side (Michael/CC). צ'ק-ליסט: `docs/runbooks/RTH_BRINGUP_SHADOW_CHECKLIST_2026-06-04.md`. כש-RTH זורם → להעלות stack על PG ולאמת:
feed מתקדם (frozen-tail watch) · כתיבות ל-**PG** לא SQLite · S1 observer (0 signals) · **ירי S2 חי** (מבחן-אמת לגייט VSA) · **P0-2 consistency** (stop מוצג == stop בעסקה שנורתה) · is_synthetic נקי. → אם ✓ **SHADOW soak מתחיל**. החזר raw ל-Cowork להצלבה.

## 3 · ✅ החלטות שכבר אושרו (אומת מול docs/decisions + DECISION_LEDGER — לא להציג כפתוחות)
- **D-RVX** ✅ APPROVED (DECISION_LEDGER) — וריאציה סופית תיבחר מדאטת soak; knob ב-`config/s2_firing.yaml` (default A_VSA).
- **Build-Status cull** ✅ מאושר אופציה A (`/build` בלבד) — prompt מוכן: `CC_PROMPT_BUILD_STATUS_CULL_2026-06-04.md`.
- **S3 firing/observer** ✅ **נעול = Firing** (`docs/decisions/D-089_S3_FIRING_LOCKED.md`, מבטל D-082).
- **Killzone 8/11** — `D-093:141` "S6 Killzone = Observer, no change" → לא החלטה פתוחה.

### ⏳ פתוח באמת
- **stop-anchor:** היחידה הפתוחה — go + אילו anchors (VAH/POC/daily/swing) + כללים → design proposal (נשען על P0-2). אין החלטה/prompt עדיין.
- **post-soak (תלוי-דאטה):** נעילת k · כיבוי תבניות (GB100/ZLR/VEGAS) — אחרי ≥10 ימי soak.

## 4 · 🟡 residuals + working-tree לא-committed (לא-חוסמי-SHADOW)
- **working-tree (CC/Michael ל-commit):** חיזוק litmus S4-ticks (`importlib.reload(zlr)`+assert `STOP_TICKS==9`, revert→RED הוכח).
- **S4 config gap:** ticks **כעת** YAML-authoritative (`e41ac5d`) — אבל ודא reload-endpoint + ש-contracts-count מניע sizing בפועל + exits מלאים ([[project-config-tunable-stop-exits-contracts]] NOT-DONE).
- **P0-2 #2** chart-patterns S2 (preview R-based ≠ pattern-measure) · **#3** min_r_t1 בקונפיג (נסגר) · BuildTreeView render-test חסר (אין jest) · `BuildTreeView.tsx:1176` הערה stale (1R כבר הגיע).
- **Trades gap-list:** G1 (write-at-entry day_type/pattern/killzone) + Frontend-1 = scope פעיל; **G2–G7 DEFERRED** עד G1+Frontend-1. verify: G5 `v9_trade_management_log` — לאמת אם כותב-שבור.
- **S1 trigger#1** (extreme move) חלקי — `move_30=None` (`state_machine.py:783`, deque(maxlen=6)) · ניקוי PG: shim · main.py SQLite fallback · 3 טסטי woodies HFE/B3.

## 5 · Invariants קשיחים
local Postgres בלבד (localhost) · ❌ לעולם לא Render/Upstash/prod-PG · Bridge Local-Only · get_db בלי lock · No silent failures · אל תיגע sc_study/DLL/risk-VALUES/polling בלי Michael (חשיפה/externalize≠שינוי-ערך) · SHADOW=paper · Rule 5 · אין present_files לקבצי-מעקב.

## 6 · הצעד הראשון בצ'אט הבא
1. אם CC החזיר תוצרים חדשים → **הצלב** (raw, code/git).
2. **P1 bring-up ב-RTH** = הגייט; אמת ירי-S2 חי + P0-2 consistency (§2).
3. ההחלטה הפתוחה היחידה = **stop-anchor** (go+anchors+כללים); D-RVX-final + post-soak תלויי-דאטה. cull/S3/Killzone כבר מוכרעים (§3). עדכן בורדים פר-שלב.
