# CC — מקיף: למה אף תבנית לא ירתה היום (טבלה) + ניקוי Build-Status frontend · 2026-06-08

פעל לפי `docs/handoff/CC_HANDOFF_CONTRACT.md` + `CC_VERIFICATION_PROTOCOL.md`.
כל "DONE" = פקודה + **פלט גולמי** (Rule 5) + סעיף NOT-DONE. **קרא קודם:** `CLAUDE.md`
(§Chop Gates · §Index — `backend/main.py`≠`backend/v9/main.py`) + `docs/reports/MEMS26_ISSUES_REGISTER.md`.

## מטרה (אחת)
לתת ל-Michael **טבלה מסודרת: לכל אחת מ-19 התבניות — מה בדיוק מנע ממנה לירות היום**,
ולהפוך את לוח ה-Build-Status ל**נקי**: רק מה שרלוונטי לנתיב-הירי, בלי פריטים מושתקים/לא-מחווטים
שמוצגים כ"שגיאה". **לא להמציא מנגנון חדש** — `GET /api/v9/build/pattern-status` כבר מחזיר
`status`+`blockers`+`reason` לכל תבנית; המשימה = להצליב מול נתיב-הירי האמיתי, לסווג, ולתקן תצוגה.

**אסור לגעת** (risk surface): מנועי-ירי, decision-tree, gateway-gates (מעבר למה שמפורט), CLOUD_URL/KeepAlive.

═══════════════════════════════════════════════════
## Phase 0 — commit עבודת-Cowork + restart (כדי שתיקוני-היום יהיו חיים לפני שמודדים)
═══════════════════════════════════════════════════
Cowork ביצע היום (uncommitted) — **בדוק `git diff`, אמת, ועשה commit**; אל תשכפל:
- `backend/v9/systems/build_status/s2_inspector.py` — `choppiness_ok` flag-gated `S2_CHOPPINESS_GATE` (default-off ⇒ chop_ok=True).
- `backend/v9/gateway/trading_gateway.py` — Layer0 chop veto flag-gated `LAYER0_CHOP_GATE` (default-bypass).
- `backend/v9/systems/build_status/aggregator.py` — `_NON_CRITICAL_STREAMS` += `tick_reversal_15`,`tpo` (S3-מושתק/S5-לא-מחווט לא חוסמים verdict).
- `CLAUDE.md` §"Chop Gates (DISABLED)" · `.env` (הערות-flags) · `STATUS_BOARD.md` · `ROADMAP_TO_LIVE.html`.
- טסטים חדשים: `tests/v9/regression/test_chop_gates_disabled.py` · `tests/v9/regression/test_readiness_noncritical_s3_streams.py`.

1. הרץ את 2 הטסטים החדשים + suite-הרגרסיה הרלוונטי → **paste raw** (הוכח GREEN).
2. commit נקי (הודעה תיאורית). paste `git log --oneline -3`.
3. **restart backend** (כדי ש-os.getenv + readiness ייטענו). **STRATEGIC-STOP אם אינך בטוח — שאל את Michael.**
4. אמת חי (paste raw): `S2_CHOPPINESS_GATE` unset · `LAYER0_CHOP_GATE` unset · `build/pattern-status` readiness **כבר לא** `dead: tick_reversal_15,tpo` (אם זה היה החוסם היחיד → verdict עלה מ-BLOCKED).

═══════════════════════════════════════════════════
## Phase 1 — טבלת "למה לא ירתה היום" (THE deliverable) → `docs/reports/PATTERN_NO_FIRE_TABLE_2026-06-08.md`
═══════════════════════════════════════════════════
ל**כל** 19 התבניות (10×S2 five_min + 9×Woodies), שלוף מ-`build/pattern-status` (+הצלב מול המנוע ו-`v9_trades`):

טבלה עם העמודות בדיוק האלה:

| # | תבנית | מערכת | סטטוס היום | **החוסם-היחיד-הקובע** | ערך-חי | **REAL fire-block / DISPLAY-only** | מה חסר כדי לירות |

חוקים מחייבים לטבלה:
1. **החוסם-הקובע** = הגייט הראשון בשרשרת שנכשל (לא רשימה — ה-bottleneck האמיתי).
2. **REAL vs DISPLAY** — הצלב כל חוסם מול נתיב-הירי האמיתי, **לא רק ה-inspector**:
   - fire-path = `gateway.route_setup` (session-window · cooldown · SSV · chop[כבוי] · cluster) + `PreFireValidator` (`live_price.json`<5s · RTH) + detection + `r_t1≥1.0`.
   - אם החוסם הוא inspector/תצוגה בלבד (למשל freshness-label, day_type instance-split, זרם-מושתק) → סמן **DISPLAY** ותכתוב למה הוא לא חוסם ירי אמיתי.
   - דוגמאות מהיום: `choppiness_ok` = inspector-only (כובה) · `tick_reversal_15/tpo` dead = S3-מושתק/S5 (DISPLAY) · Woodies `trend_state=GRAY` = REAL (Stage A1, דוקטרינה) · auth-SKIP×day_type = REAL.
3. שורת-סיכום: כמה תבניות נחסמו ב-REAL מול DISPLAY, ומהו החוסם-ה-REAL הנפוץ ביותר.
4. ל-S4: ציין `trend_state` הנוכחי ולמה (BLUE/RED/GRAY) — זה גייט-העל.

> מטרת-העל של Michael: לראות בבירור שמרבית ה"BLOCKED" של היום היו DISPLAY (זרמים-מושתקים + labels),
> ושהחוסמים-ה-REAL מצומצמים (trend-gate · auth-SKIP · detection · כיול) — לא "המערכת שבורה".

═══════════════════════════════════════════════════
## Phase 2 — ניקוי Build-Status frontend ("רק דברים שעובדים, כלום לא-רלוונטי")
═══════════════════════════════════════════════════
**2a · day_type freshness — תקלת-תצוגה (אובחן ע"י Cowork).** ב-`day_type_inspector.py:325-329` ה-backend
מחזיר `lag_seconds=None`, `last_bar_ts=last_updated`, `fresh=is_classified`, `threshold=360`. ה-frontend מחיל
סף-זרם-360s על `last_updated` של מסווג-יום (observer, לא זרם-ברים) ⇒ מציג שקרית "תקוע · lag ? · יצוא Sierra תקוע"
לצד נקודה ירוקה "● חי" (סתירה). **תקן:** day_type לא יוצג עם סף-זרם-360s ולא עם הינט-"Sierra תקוע".
הצג במקום: "מסווג · עודכן HH:MM" (או "LOCKED"). אם reclass מתמשך פעיל (`S1_DYNAMIC/LIVE_RECLASS`) ו-`last_updated`
באמת קפוא הרבה זמן ב-RTH → הצג חיווי-משני "reclass לא-מתעדכן" המצביע על feed (I-21), **לא** "Sierra תקוע" גנרי.

**2b · רק זרמים/מערכות בנתיב-הירי בלוח.** יישר את ה-frontend עם backend `_NON_CRITICAL_STREAMS`:
- זרמים מושתקים/לא-מחווטים — `footprint`,`tick_reversal_15` (S3, `S3_MUTE=1`) ו-`tpo`/`tpo_bars` (S5/TPO, I-24) —
  **אסור** שיופיעו אדומים "DEAD/stale/BLOCKED". הצג אותם כ-**"disabled (S3_MUTE)"** / **"not-wired (S5)"** באזור-מידע נפרד, או הסתר.
- ה-verdict בראש-הלוח ישקף רק זרמים-קריטיים-לירי (תואם ל-`_compute_readiness`).
- הסר את סתירת ה-"● חי" מול טקסט "תקוע" — מקור-רעננות-אחד-עקבי.

**2c · עקביות-TZ בתוויות-freshness (I-18/I-20, אם בהישג-יד).** אם תווית מציגה lag-שלילי/`fresh=true` על lag>סף
(ערבוב TZ) — נרמל ל-UTC בגבול. אם זה חורג מ-scope, רשום ב-NOT-DONE.

**קבצי-frontend לאיתור (התחל כאן, אמת):** `frontend/v9/src/v9/components/build_tree/BuildTreeView.tsx` ·
`components/sidebar/tabs/{MarketTab,SetupsTab,SignalTab,DecisionsTab}.tsx` · רכיב ה-DataFreshness/stream-row.
(Next dev עושה hot-reload.)

═══════════════════════════════════════════════════
## Phase 3 — דוחות + בורדים
═══════════════════════════════════════════════════
- `STATUS_BOARD.md` + `ROADMAP_TO_LIVE.html` — finding+fix+verification מתוארך (Roadmap auto-update).
- עדכן I-1/I-18/I-20/I-24 ב-`MEMS26_ISSUES_REGISTER.md` עם מה שנסגר.

## Acceptance Criteria (בינארי — ✓/✗)
- [ ] Phase 0: 2 הטסטים GREEN (paste) · commit · restart · readiness לא `dead: tick_reversal_15,tpo` (paste).
- [ ] Phase 1: `PATTERN_NO_FIRE_TABLE_2026-06-08.md` עם **כל 19** התבניות, עמודת REAL/DISPLAY מלאה, שורת-סיכום.
- [ ] Phase 2a: צילום Build-Status — day_type **בלי** "תקוע/lag?/Sierra תקוע"; מציג "מסווג · עודכן HH:MM".
- [ ] Phase 2b: צילום — זרמים מושתקים/לא-מחווטים **לא** אדומים-BLOCKED; verdict משקף רק fire-path.
- [ ] Phase 2: אין סתירת "● חי"↔"תקוע"; console נקי.
- [ ] regression לכל תיקון-תצוגה שמשנה לוגיקה (anti-tautological — ראה למטה).

## anti-tautological
טסט-תצוגה (אם נכתב) חייב לייבא+לקרוא את הפונקציה האמיתית (`_compute_readiness` / inspector), **לא** לשכפל את הסף.
מבחן-ליטמוס בכל טסט: "אם אהפוך את התיקון → RED כי ___". טבלת-Phase-1 = הצלבה מול endpoint+engine אמיתיים (raw),
לא נתונים מומצאים; אם קריאה נכשלת — כתוב "endpoint error", אל תמלא ניחוש.

## NOT-DONE (חובה למלא)
מה לא נבדק · כל סטייה · פריטים שנדחו (2c TZ?) · האם ה-table שיקף RTH-חי או סשן-סגור · שורש I-21 (tick_reversal session-non-start) אם עדיין פתוח.

## דוח-חובה (חלק C של החוזה) + מה Cowork יבקר אחריך
מסור: (1) `git log --oneline` · (2) raw של 2 הטסטים + restart-verify · (3) הטבלה המלאה · (4) 2 צילומי Build-Status (לפני/אחרי) ·
(5) רשימת קבצי-frontend ששונו. **Cowork יצליב (Rule 5):** REAL/DISPLAY בטבלה מול הקוד · שה-day_type-fix לא שובר freshness אמיתי של זרמים-קריטיים · שזרמים-מושתקים אכן הוסרו מה-verdict ולא הוסתר חוסם-אמיתי · console+screenshot.
