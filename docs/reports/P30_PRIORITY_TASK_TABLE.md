# P30 — טבלת משימות לפי סדר חשיבות

**תאריך:** 2026-05-20 (עדכון לילה — post Wave 0–2)  
**מקורות:** `P30_WAVE_0_CC_VERIFY.md`, `P30_P15_CLOCK_DONE.md`, `P30_S1_*_DONE.md`, `P30_CURSOR_P05_REPORT.md`  
**מחייב:** אין שינוי DLL / הגדרות Sierra / עיצוב בלי אישור Michael.

**סימונים:** ✅ הושלם · 🔄 בתהליך · ⬜ ממתין · 🔵 P2 · ⚪ DEFER

**מסמכים מרכזיים:**

| מסמך | תפקיד |
|------|--------|
| [`P30_ROAD_START_TO_LIVE.md`](./P30_ROAD_START_TO_LIVE.md) | **תוכנית + איפה אנחנו** |
| **זה** (`P30_PRIORITY_TASK_TABLE.md`) | **תור משימות + סטטוס** |
| [`docs/handoff/agents/WAVE_INDEX.md`](../handoff/agents/WAVE_INDEX.md) | פרומפטים לסוכנים |
| [`docs/decisions/D-087_REGISTRY_WAIVER.md`](../decisions/D-087_REGISTRY_WAIVER.md) | Registry SHADOW waiver |
| [`docs/decisions/D-088_CLUSTER_GUARD_SHADOW.md`](../decisions/D-088_CLUSTER_GUARD_SHADOW.md) | SHADOW under cluster_guard |

---

## איפה אנחנו (שורה אחת)

**Gates 0–2 סגורים** → **D-088 deploy PASS** (PID 46604) → **הבא:** Michael **P-S0** → SHADOW soak.

---

## ✅ COMPLETED

| ID | משימה | ראיה |
|----|--------|------|
| P0-HTTP / Redis | baseline | Michael 20/5 |
| GW-02 / GW-CHOP / FP-SQL | P0.5 | `8dd1ffb`, `a9138ce` |
| S2-PF | pre_fire בשרשרת | `P30_S2_PF_VERIFY.md` + errata Wave 0 |
| CC Wave 0 | GO-WITH-NOTES | `P30_WAVE_0_CC_VERIFY.md` |
| D-087 | Registry §18 waived (SHADOW) | `docs/decisions/D-087_REGISTRY_WAIVER.md` |
| D-088 | cluster_guard — SHADOW records | `trading_gateway.py` + `test_d088_*` |
| S1-PREV | `prev_day.py` + tests | `P30_S1_PREV_DONE.md` |
| S1-WIRE | `main.py` → prev_day | `P30_S1_WIRE_DONE.md` |
| P1.5 partial | CLOCK 1–3,5 KEEP; 5→prev_day | `P30_P15_CLOCK_DONE.md` |
| D-088-deploy | restart + verify | `P30_D088_DEPLOY_VERIFY.md` PASS · PID **46604** |

---

## 🔄 בתהליך (אופציונלי)

| ID | משימה | בעלים | הערה |
|----|--------|--------|------|
| SH-4 / live D-088 log | grep D-088 line ב-RTH | CC | in-process PASS; HTTP timeout post-restart |
| Drive-Sync | manifest → Drive | CC / cloud | `AGENT_DRIVE_SYNC.md` |
| GW-PERSIST | `datetime` not JSON serializable ב-persist | Cursor | WARN בדוח D-088 — נפרד מ-D-088 |

---

## ⬜ הבא בתור

| # | משימה | תלות | בעלים |
|---|--------|------|--------|
| 1 | **P-S0** SHADOW activation sign-off | D-088 PASS | Michael |
| 2 | **SHADOW soak** 5–10 ימים | P-S0 | Michael + CC |
| 3 | CLOCK-4 IB percentile (10d) | אופציונלי | DEFER — `P30_P15_CLOCK_DONE.md` |
| 4 | POST-SHADOW: D-086, Registry triage, L4/L5 | soak review | Michael |

---

## החלטות נעולות (D-082 … D-088)

| ID | החלטה | סטטוס |
|----|--------|--------|
| D-082 | S3 observer עד LIVE | VIOLATED → **D-086** |
| D-083 | S6 observational | LOCKED |
| D-084 | Woodies HFE | DEFER pre-LIVE |
| D-085 | TPO rename | DEFER cosmetic |
| D-086 | S3 fire tolerated ב-SHADOW | LOCKED |
| D-087 | §18 waived SHADOW; **ENFORCED לפני LIVE** | LOCKED |
| D-088 | SHADOW נרשם; cluster חוסם DEMO/LIVE בלבד | LOCKED + deploy ✅ |

---

## סיכום ל-Michael (3 שורות)

1. **עכשיו:** **P-S0** — Michael מאשר התחלת SHADOW soak.  
2. **ב-soak:** יומן יומי + CC health; אופציונלי: grep שורת D-088 בלוג ב-RTH.  
3. **לפני LIVE:** §18 GREEN, D-086, L4/L5, V6 §8; תיקון GW-PERSIST אם צריך DB rows.

---

## תור עבודה (מעודכן)

| עדיפות | משימה | סטטוס |
|--------|--------|--------|
| P0.5 CC verify | Wave 0 | ✅ GO-WITH-NOTES |
| D-087 | Registry waiver | ✅ LOCKED |
| D-088 code | gateway | ✅ |
| D-088 deploy | restart + verify | ✅ `P30_D088_DEPLOY_VERIFY.md` |
| S1-PREV / S1-WIRE | Wave 1 | ✅ |
| P1.5 CLOCK | audit + tpo dedupe | ✅ PARTIAL (CLOCK-4 DEFER) |
| P-S0 + soak | Wave 3 | ⬜ |
| L4 / L5 | pre-LIVE | ⬜ |
| V6 §11 Analyst | post-soak | ⬜ |
| V6 §8 Pre-flight | pre-LIVE | ⬜ |
| D-086 S3 fix | post-soak | ⬜ |

---

## P1.5 — פירוט

| ID | סטטוס | הערה |
|----|--------|------|
| CLOCK-1 | ✅ KEEP | `market_clock.py` |
| CLOCK-2 | ✅ KEEP | `/api/v9/clock/now` |
| CLOCK-3 | ✅ KEEP | 4 open types + API |
| CLOCK-4 | ⚪ DEFER | percentile 10d — לא חוסם soak |
| CLOCK-5 | ✅ ADAPT | `/api/v9/tpo/previous_day` → `prev_day` |

---

## Wave 0 — תיקוני CC (errata)

| CC מצא | אחרי בדיקה |
|--------|------------|
| FAIL S2 pre_fire | **בוטל** — `emit_t1_setup` → `validate_fire` → `route_setup` |
| WARN cluster_guard | **D-088** ✅ deploy PASS |
| FAIL latency cold | לא חוסם |

ראה: `P30_WAVE_0_CC_VERIFY_ERRATA.md`

---

## מה לא לעשות עכשיו

S2 pre_fire קוד · S3 fix (D-086) · push main · DLL · redesign · 6 agents עד סוף soak (אופציונלי מוקדם)

---

*עודכן: Cursor Parent · 2026-05-20 · לצפייה עם `P30_ROAD_START_TO_LIVE.md`*
