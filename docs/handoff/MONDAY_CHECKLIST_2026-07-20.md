# צ'קליסט מוכנות ליום שני — 2026-07-20

**מארגן:** cursor-agent · **יעד:** 20/07 נפתח ב-16:30 עם מסחר תקין מהרגע הראשון.
**מקור:** `CURSOR_MONDAY_READINESS_2026-07-18.md` · מצב-מערכת: `LIVE_CHANNEL.md`.
**חוק-5:** אין ✅ בלי פקודה + פלט-גולמי. סימון ✅ = בעלים + אימות cowork-dev.

| סוכן | תפקיד |
|---|---|
| **cursor-agent** | ארגון / מעקב / פערים — לא נוגע בקוד-מסחר |
| **cowork-dev** | מנהל · מאמת כל תוצר · git push |
| **cc-macbook** | מבצע קוד (מכונת-המסחר) |
| **cc-imac** | סים בלבד (חוק סוחר-יחיד) |
| **מייקל** | פסיקות · סיירה/צ'ארטבוק · חימוש |

---

## מפת-תלויות (מה חוסם מה)

```
B1 (סף 14:30) ──────────────► התנהגות-פתיחה/אחר-צהריים ביום ב'
B2 (entry_not_confirmed) ───► כמה תבניות-S4 עוברות בצ'ופ
B3 (StopResolver) ──────────► רוחב-סטופ ברוטציה (Normal)
B4 (A5-ביקורת OFA key) ─────► האם INITIATIVE×Normal נחסם או over-fires
B5 (A6-ביקורת S4 override) ─► האם S4 רואה DAY_TYPE_MANUAL_OVERRIDE
B6 (הדלקת ORPHAN) ──────────► דורש A1 DLL+סים ירוק; אחרת נשאר OFF

A1 (DLL PLACE_STOP) ────────► B6 + הגנה מיתום-עירום
A2 (PATTERN_LOSS_BREAKER) ──► C4 flag_guard (דריפט לא-RULED)
A3 (2 כשלי-סים) ────────────► C2 E2E ירוק
A4 (audit_pattern_miss) ────► כיסוי-זיהוי לפני כיול
A5 (CVD צ'ארטבוק) ──────────► אישור-זרימה S2 (fail-open היום; דק=דחייה-שקטה)
A6 (ZeroTier פלאפון) ───────► ניטור-כיס קבוע ביום ב'

A+B כולם ───────────────────► C (אימות ראשון-ערב)
C ירוק ─────────────────────► D (בוקר שני) → GO/NO-GO 16:25
```

---

## המלצת-מארגן: מה עדיף לבצע (cursor-agent → מייקל)

**עקרון:** יום ב' צריך **צינור נקי + פסיקות-שערים ברורות + אתה מכיר כל תבנית**.
לא צריך לסיים את כל ה-DLL/כיול לפני 16:30 — עדיף GO צר ויציב מאשר GO רחב עם חורים.

### סדר מומלץ (ראשון)

| # | מתי | מה | למה זה עדיף |
|---|---|---|---|
| **1** | ראשון בוקר · **מייקל** | **מעבר כל התבניות** (שער P למטה) + פסיקות B1–B5 באותה ישיבה | בלי זה B תקוע, ואתה נכנס ליום ב' בלי מפה. הפסיקות (14:30 / entry_confirm / StopResolver / OFA / S4-override) **תלויות** בזה שראית איך כל תבנית חיה מול יום ו' |
| **2** | במקביל ל-1 · **cowork** | **A2** (PATTERN_LOSS_BREAKER→RULED) — 15 דק' | זול, סוגר דריפט, מנקה C4 |
| **3** | במקביל ל-1 · **מייקל** | **A5 CVD** בצ'ארטבוק + **A6 ZeroTier** לפלאפון | תשתית-יום-ב'; לא קוד. CVD משפר S2; כיס = עיניים |
| **4** | אחרי 1 או במקביל · **cc-macbook** | **A3** קודם (2 כשלי HTLB/TLB), אחר-כך **A4** (הרחבת audit) | A3 חוסם אמון ב-E2E. A4 משרת את מעבר-התבניות שלך — עדיף שיהיה מוכן לפני/תוך כדי P, לא אחרי |
| **5** | ראשון אחר-צהריים · **cowork+cc** | **C1→C3→C4→C5**, ואז **C2** (E2E סים) | קודם מטריצה זולה (104) + רגרסיה + flag_guard; E2E רק כש-A3 ירוק ו-`is_sim=1` |
| **6** | רק אם נשאר זמן אחרי 1–5 · **cc-macbook** | **A1 DLL PLACE_STOP** | חשוב לבטיחות-יתום, **לא חוסם פתיחה** אם הדגל נשאר OFF. אל תשרוף את הראשון על DLL לפני מעבר-תבניות + C |
| **7** | דחוי במודע עד אחרי שני (אלא אם פסיקה אחרת) | **B6** הדלקת ORPHAN · כיולי-זיהוי מ-PATTERN_MISS · PATTERN_MGMT A1/A2/A4/A7 | משטח-סיכון / לא קריטי לפתיחה אם היום נפתח עם הדגלים הקיימים |

### מה לא לעשות בראשון
- לא להתחיל כיול-סף על ZLR/GB100 לפני שסיימת **P** (מעבר-תבניות) + B1/B2.
- לא להדליק דגל חדש ב-.env בלי RULED + פסיקה.
- לא להריץ C2 על שתי מכונות חמושות (סוחר-יחיד).
- לא לסמן A1 ✅ בלי DLL+סים — Monday יכול להיות GO עם ORPHAN=OFF.

### GO מינימלי ליום ב' (אם הזמן נגמר)
חובה ירוק: **P** (עברת על התבניות) · **B1** (סף 14:30 — גם אם "להשאיר") · **A2** · **A5** רצוי · **C1+C4+C5** · **D1–D5**.
ניתן צהוב/דחוי: A1/B6 · A3/A4 אם C1 ירוק ואתה מקבל סיכון על HTLB/TLB ב-Neutral · B3–B5 אם פסיקה מפורשת "דוחים אחרי שני".

---

## שער P — מעבר כל התבניות (מייקל, ראשון בוקר — לפני/עם B)

**מטרה:** לעבור אחת-אחת — זיהוי / שערים / סטופ+סולם / האם מותרת ביום-Normal כמו ביום ו' — ולכתוב ✅ או הערה.
מקורות: `config/daytype_playbook.yaml` · `PATTERN_MGMT_AUDIT` · `PATTERN_MISS_AUDIT` · EOD 07-17.
**קריטריון-סיום:** כל שורה למטה עם סימן + שורת-LOG ב-LIVE_CHANNEL "P done · הערות: …". אחר-כך סוגרים B1–B5.

### S4 — Continuation
| תבנית | מה לבדוק במעבר | סטטוס |
|---|---|---|
| **ZLR** | ירתה בצל 4/4 אחרי 14:30; חיתוך B1; צבע/CCI אחרי TREND_CCI_DIRECT | ⬜ |
| **TLB** | תא Neutral_Extreme×TLB נכשל ב-E2E (A3); ניהול OCO/MODIFY | ⬜ |
| **TT** | דורש BLUE/RED קשיח; האם עיוור בבוקר-גאפ כמו GB100 | ⬜ |
| **GB100** | קרוס-טרי + paint; פספוסי-בוקר מ-PATTERN_MISS | ⬜ |
| **INITIATIVE** (S2 CONT ב-playbook) | B4 — מפתח OFA עוקף SKIP; לייב #396 סטופ-צר | ⬜ |
| **FLAGS** | #400 לייב ירוק; T2-override (MGMT A7) | ⬜ |
| **CONFLUENCE_RI_ZLR** | דגל חי? האם מצפים לירי ביום ב' | ⬜ |

### S4 — Reversal
| תבנית | מה לבדוק במעבר | סטטוס |
|---|---|---|
| **HTLB** | Neutral_Center×HTLB נכשל E2E (A3); latch-bias בפתיחה | ⬜ |
| **VEGAS** | כיסוי חסר ב-audit_pattern_miss (A4); playbook FULL ב-Normal | ⬜ |
| **GHOST** | נחסם `entry_not_confirmed`×missed (B2) | ⬜ |
| **FAMIR** | אותו שער B2; גם eod_cutoff | ⬜ |
| **DBDT** | כיסוי חסר ב-A4; REV ב-Normal | ⬜ |

### S2
| תבנית | מה לבדוק במעבר | סטטוס |
|---|---|---|
| **REACTIVE** | edge-fix חי; CVD ריק (A5); #403 shadow הפסיד — השער צדק? | ⬜ |
| **HNS** | require_with_trend; האם ראית ירי השבוע | ⬜ |
| **HNS/DB/Flags chart** | detection על day_type מפגר (MGMT A2/A4) — מודע? | ⬜ |

**טיפ-מעבר:** לכל תבנית שלוש שאלות בלבד — (1) מותרת היום ב-playbook לסוג-היום הצפוי? (2) מה חסם אותה ביום ו' אם הגיעה? (3) האם אתה רוצה אותה חיה ביום ב' או shadow-only?

---

## שער A — עד ראשון בערב (קוד + תשתית)

| מזהה | משימה | בעלים | תלות | קריטריון-סיום (פקודה / פלט) | סטטוס |
|---|---|---|---|---|---|
| **A1** | ORPHAN_AUTO_STOP_V1 — סטופ-מגן ליתום. **קוד-גייטינג בוצע** (flag OFF). **חסר:** DLL op `PLACE_STOP` + אימות-סים | **cc-macbook** | מפרט: `CC_PROMPT_ORPHAN_AUTOSTOP_2026-07-17.md`. חוסם B6 | (1) stub מחזיר `NO_DLL_PATH` עד שיש op. (2) אחרי DLL: `pytest tests/v9/regression/test_orphan_auto_stop.py -q` → 11+ passed. (3) סים: יתום ידני → סטופ הונח בצד/מחיר נכון + לוג CRITICAL. פלט ב-LIVE_CHANNEL | 🟡 חסום-DLL |
| **A2** | `PATTERN_LOSS_BREAKER` 1→0 + הוספה ל-`RULED_FLAGS.yaml` (דריפט מפסיקת-מייקל 07-16; לא ב-RULED → flag_guard לא תפס) | **cowork-dev** | פסיקה קיימת 07-16; לא דורש B | `grep PATTERN_LOSS_BREAKER config/RULED_FLAGS.yaml` → expected `"0"`. `.env` =0. `python3 scripts/flag_guard.py` → PASS כולל השורה הזו. פלט גולמי | 🔴 |
| **A3** | 2 כשלי-סימולציה: `Neutral_Center×HTLB` · `Neutral_Extreme×TLB` (`oco_pairs=False`, `modify_stop_all=False`) | **cc-macbook** | מ-`sim_matrix_e2e`; חוסם C2 | `python3 scripts/sim_matrix_e2e.py` — שני התאים האלה ירוקים (OCO+MODIFY_STOP). פלט שורות-התאים | 🔴 |
| **A4** | הרחבת `audit_pattern_miss.py` ל-TLB/HTLB/VEGAS/GHOST/FAMIR/DBDT | **cc-macbook** | כיסוי חלקי (ZLR/GB100/TT בלבד היום) | `python3 scripts/audit_pattern_miss.py --selftest` עובר על 6 התבניות החדשות. ריצת `--date 2026-07-17` מפיקה קריטריון-כישלון לכל אחת | 🔴 |
| **A5** | **CVD לא מיוצא** — להוסיף סטאדי Cumulative Delta לצ'ארטבוק סיירה | **מייקל** | חוסם אישור-זרימה S2 איכותי (היום fail-open על ריק) | `ls -la ~/SierraChart_Data/v9_export/cumulative_delta.json` — קובץ מתעדכן ב-RTH; `jq 'length/.points|length' …` או `curl -s localhost:8000/api/v9/cumulative_delta/current` → נקודות טריות (לא ריק) | 🔴 |
| **A6** | פלאפון — כתובת קבועה דרך **ZeroTier** (לא Tailscale) | **מייקל + cowork-dev** | רשת ZT כבר: דב 10.1.118.147 | מהפלאפון (ZT 10.1.118.31): פתיחת `http://10.1.118.147:3000` (או פורט-המובייל המתועד) יציבה אחרי restart-frontend. **אין** URL של trycloudflare | 🟡 |

---

## שער B — פסיקות מייקל (חוסמות; בלעדיהן A/C חלקיים תקועים)

| מזהה | משימה | בעלים | תלות | קריטריון-סיום | סטטוס |
|---|---|---|---|---|---|
| **B1** | **סף 14:30 ET** — להשאיר / להזיז? (שלח 3 שורטי-S4 מנצחים ל-shadow ביום ו') | **מייקל** | חוסם התנהגות אחר-צהריים ביום ב' | פסיקה בכתב ב-LIVE_CHANNEL: שעה מדויקת (ET) או "להשאיר 14:30". אם זז — cowork מעדכן RULED + `.env` + ריסטארט + `flag_guard` | ⏳ |
| **B2** | **entry_not_confirmed** — לרכך? (חסם 3 תבניות בצ'ופ; missed-winners) | **מייקל** | `S4_ENTRY_CONFIRM_V1` חי=1 | פסיקה: להשאיר / לרכך-סובלנות / לכבות. שינוי = RULED באותו קומיט | ⏳ |
| **B3** | **StopResolver** — להרחיב-לרצפה על `"Normal"` או להמשיך לדחות? (סטופ-מבני צר; PATTERN_MGMT A3) | **מייקל** | משטח-סיכון | פסיקה בכתב. אם כן — דגל default-OFF + מפרט ל-cc-macbook; לא קוד בלי פסיקה | ⏳ |
| **B4** | **A5-ביקורת** — מפתח `OFA_Initiative` ≠ `INITIATIVE_LONG` (SKIP נעקף → over-fire). תיקון = פחות יריות | **מייקל** | PATTERN_MGMT A5; משטח-סיכון | פסיקה: לתקן (דגל OFF→RULED אחרי סים) / לדחות. **לא** לתקן בלי חתימה | ⏳ |
| **B5** | **A6-ביקורת** — S4 override-מודע (`get_live_day_type` במקום raw machine) | **מייקל** | PATTERN_MGMT A6 | פסיקה: לתקן / לדחות. אם כן — מפרט + דגל OFF ל-cc-macbook | ⏳ |
| **B6** | הדלקת `ORPHAN_AUTO_STOP_V1` | **מייקל** | **A1 סים-ירוק חובה** | פסיקה בכתב אחרי הוכחת-סים. אז: RULED=`1` + `.env` + ריסטארט + `flag_guard` PASS. **בלי סים → נשאר OFF** | ⏳ חסום-A1 |

---

## שער C — אימות (ראשון בערב, אחרי A ו-B הרלוונטיים)

| מזהה | משימה | בעלים | תלות | קריטריון-סיום | סטטוס |
|---|---|---|---|---|---|
| **C1** | `python3 scripts/sim_matrix.py` — 104 תאים ירוקים | **cowork-dev** | A2 לא חוסם ישירות; רצוי אחרי A3-fix אם נגע בפלייבוק | Exit 0 · `104` cells PASS · פלט ב-LIVE_CHANNEL או `docs/reports/SIM_MATRIX_*.md` | 🔴 |
| **C2** | סימולציית-E2E על סיירה-**סים** — כל תבנית×סוג-יום יורה ומנוהלת | **cc-macbook** → **cowork מאמת** | A3 ירוק; `is_sim=1` מאומת; iMac לא חמוש | `python3 scripts/sim_matrix_e2e.py` — 0 כשלים קריטיים (OCO/MODIFY_STOP/FLATTEN). **op=EXIT לא לבדוק.** cowork מדביק אימות | 🔴 |
| **C3** | חבילת-רגרסיה מלאה — 0 רגרסיות חדשות | **cowork-dev** | אחרי שינויי-A של cc-macbook | `pytest tests/v9/regression/ -q` (או החבילה המתועדת בריצה) → 0 failed חדשים. פלט גולמי | 🔴 |
| **C4** | `flag_guard` PASS + `fire_drill` 🟢 GO | **cowork-dev** | A2 ב-RULED; אחרי כל שינוי-.env | `python3 scripts/flag_guard.py` → PASS N/N. `python3 scripts/fire_drill.py` → 🟢 GO · `effective_contracts==4` | 🔴 |
| **C5** | כל הצינורות: Sierra→export→bridge→DB→API→פרונט/פלאפון | **cowork-dev** | A5 CVD רצוי; A6 לפלאפון | (1) export files mtime טרי. (2) bridge דוחף ל-`localhost:8000` בלבד. (3) `curl localhost:8000/api/v9/status` mode=live/writing. (4) ברי-woodies טריים ב-DB. (5) פרונט+כיס מציגים מחיר/סטטוס | 🔴 |

---

## שער D — בוקר שני (16:00–16:30 IL)

| מזהה | משימה | בעלים | תלות | קריטריון-סיום | סטטוס |
|---|---|---|---|---|---|
| **D1** | `is_sim=0` · מחיר-שפוי · **flat** | **cowork-dev** מאמת | C ירוק אתמול | קריאת `sierra_state.json`: `is_sim=0`, `position_qty=0`, `working_orders=0`, מחיר ≠ 996150 ובטווח-שוק סביר. פלט גולמי | 🔴 |
| **D2** | iMac על **סים** (חוק סוחר-יחיד, אותו חשבון 37138283) | **מייקל** מאשר | לפני חימוש MacBook | אישור מפורש: iMac Trade Simulation ON + disarmed + flat. **אל לחמש MacBook בלי זה** | 🔴 |
| **D3** | ברי-RTH זורמים + פיד טרי | **cowork-dev** | D1 | אחרי 16:30: `v9_bars_5min_woodies` מקבל ברים חדשים; `bar_gap_monitor` / status — פיד לא-stale. פלט | 🔴 |
| **D4** | `flag_guard` + `fire_drill` אחרונים | **cowork-dev** | D1–D2 | אותן פקודות כמו C4 — PASS + 🟢 GO על מצב-הבוקר | 🔴 |
| **D5** | **GO / NO-GO מפורש ב-16:25** | **cowork-dev** | D1–D4 | שורת-LOG ב-LIVE_CHANNEL: `GO` או `NO-GO` + סיבה + פלטים. בלי שורה = NO-GO כברירת-מחדל | 🔴 |

---

## חוקי-ברזל (הצ'קליסט אוכף — אל תרכך)

1. **דגל חדש = default OFF.** הדלקה = פסיקת-מייקל בכתב + `RULED_FLAGS.yaml` באותו קומיט + ריסטארט + `flag_guard`.
2. **op=EXIT שבור-אסור** עד EXIT-v2. יציאות: OCO / MODIFY_STOP / FLATTEN_ACCOUNT.
3. **סוחר-יחיד:** MacBook לייב, iMac סים. לעולם לא שתיהן חמושות.
4. **חוק-5:** "בוצע" = פקודה + פלט-גולמי. הצהרה בלי פלט = לא-בוצע.
5. **`git pull` לפני כתיבה, `commit`+`push` אחרי.** אל תמחק רשומות של סוכן אחר.
6. **רשת = ZeroTier בלבד** (פסיקת-מייקל 07-17). לא Tailscale.
7. שינוי משטח-סיכון → **עצירה-אסטרטגית + פסיקת-מייקל**.

---

## 🔶 פערים / כפילויות / התראות-מארגן (cursor-agent 2026-07-18)

| # | ממצא | פעולה |
|---|---|---|
| 1 | **התנגשות-שמות A5:** בשער-A, A5=CVD צ'ארטבוק; ב-PATTERN_MGMT_AUDIT, A5=`OFA_Initiative` (כאן = **B4**). לא לאחד — שני נושאים שונים | להשתמש במזהי-הצ'קליסט (A5/B4) בלבד בדיווח |
| 2 | **A1 מול B6:** קוד-גייטינג ORPHAN כבר ב-repo (LOG cc-macbook); עדיין **לא ✅** — חסר DLL `PLACE_STOP` + סים. B6 חסום עד אז; דגל נשאר OFF | לא לסמן A1 ✅ על "קוד מוכן" |
| 3 | **MASTER_FIX_LIST טוען** `PATTERN_LOSS_BREAKER=0` 🟢 RULED — אבל `config/RULED_FLAGS.yaml` **לא** מכיל את המפתח (אומת grep). LIVE_CHANNEL צודק: דריפט פתוח = **A2** | cowork-dev סוגר A2; לא לסמוך על MASTER_FIX_LIST כאן |
| 4 | **PATTERN_MGMT A1/A2/A4/A7** (Normal REV exemption, Nontrend skip, chart-patterns stale, Flag-T2) — **לא** בשערי A/B של המפרט. לא הוספתי כדי לא להרחיב scope | 🔶 מייקל/cowork: האם להכניס ל-B כפסיקות נוספות או לדחות אחרי שני? |
| 5 | **cc-imac** אין שורת-ביצוע בשער A–D (סים/גיבוי בלבד) — מכוון. C2 רץ על MacBook-סים או iMac-סים לפי חוק סוחר-יחיד | אם C2 על iMac — MacBook חייב disarmed באותו זמן |
| 6 | אין כפילות-בעלים בתוך הצ'קליסט; כל שורה בעלים יחיד (A6/C2 משותפים מפורשים) | — |

---

## סיכום-בעלות לפי שער

| שער | בעלים עיקריים | פריטים |
|---|---|---|
| **P** | **מייקל** — מעבר כל התבניות (לפני B) | 15 תבניות |
| **A** | cc-macbook (A1,A3,A4) · cowork-dev (A2) · מייקל (A5) · מייקל+cowork (A6) | 6 |
| **B** | מייקל (B1–B6) | 6 |
| **C** | cowork-dev (C1,C3,C4,C5) · cc-macbook→cowork (C2) | 5 |
| **D** | cowork-dev (D1,D3,D4,D5) · מייקל (D2) | 5 |
| **סה״כ שורות-עבודה** | | **22 + שער P** |

**סטטוס פתיחה:** 0 ✅ · רוב 🔴/⏳ · A1=🟡 חסום-DLL · A6=🟡 · B6 חסום-A1.
**סדר מומלץ:** P+B1–B5 → A2/A5/A6 → A3→A4 → C → (A1 רק אם נשאר זמן) → D.
