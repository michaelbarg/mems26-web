# CC PROMPT — Fix Extreme-CCI Trend Relabel: Single Source of Truth + Flag · 2026-06-02

**תווית החלטה:** `D-WDIAG` (gray-classifier fix — done right) · ראה `docs/plans/DECISION_LEDGER.md`
**מאת:** Michael (approved "clean path") → **אל:** Claude Code
**הקשר:** הבקרה הבלתי-תלויה (`INDEPENDENT_VERIFICATION_2026-06-02.md`) אישרה שה-override `1c0397a` הוא **partial-wired** — הוא משנה `_ts`+`current_state` אבל **לא** `studies["trend_state"]`, וה-`decision_tree._a1_trend_gate` קורא את `studies` הגלמי → ה-override לא מגיע ל-`ready_to_route`. תוצאה: התצוגה אומרת BLUE אבל העסקה לא מנותבת.

> **משמעת Pre-LIVE:** diagnose/read-first · smallest-correct-change · **flag-gated** · **No silent failures** · **Rule 5 (command+raw output)** · **strategic-stop לפני הדלקת הדגל ל-live** · תווית `# D-WDIAG` בכל מקום שנוגעים.
>
> **עיקרון:** מקור-אמת **יחיד** ל-`trend_state`. ה-relabel חייב לקרות פעם אחת, **לפני** שכל הצרכנים (detection / dispatcher / decision_tree / display / persist) קוראים את הערך — לא אחרי.

---

## Phase 1 · Revert ה-override השבור

- `git revert 1c0397a` (או הסרה ידנית של הבלוק ~שורות 358-361 ב-`woodies_system.py` — הבלוק שמשנה `_ts`/`current_state` על `abs(_cci)>=200`).
- אמת: `git show` של ה-revert · הרץ את הטסטים הקיימים → ירוקים.
- **Rule 5:** הדבק diff + פלט טסטים.

## Phase 2 · Relabel במקור יחיד, מאחורי דגל

**דגל חדש:** `S4_EXTREME_TREND_RELABEL` (env, default **OFF**). OFF = התנהגות post-revert (trend גלמי מ-Sierra). תיעוד בפרומפט הדגלים.

**מיקום התיקון:** ב-`woodies_system.py::process_bar`, **מיד אחרי בניית `studies`** (~אחרי שורה 267, שם `studies["trend_state"] = str(bar.get("trend_state") or "GRAY")`) ו**לפני**: `wb = WoodiesBar(**studies)` (~290), `detect_all_patterns` (~302), ובניית `WoodiesDecisionContext(studies=studies)` (~401-411).

**הלוגיקה (תווית `# D-WDIAG`):**
```python
# D-WDIAG: extreme-CCI trend relabel at the SINGLE source (studies) so EVERY
# consumer — detection, dispatcher, decision_tree A1 gate, display, persist —
# sees one consistent trend_state. |CCI|>=200 = strong established trend, not
# no-trend; Sierra's GRAY/YELLOW here is a transition-lag misclassification
# (audit: 6 bars confirmed). Flag-gated; default OFF = raw Sierra trend.
if _EXTREME_TREND_RELABEL and studies["trend_state"] in ("GRAY", "YELLOW", "GREY"):
    _cci = studies.get("cci_14") or 0
    if abs(_cci) >= 200:
        studies["trend_state"] = "BLUE" if _cci > 0 else "RED"
```
(אין override מאוחר נוסף — זה המקום היחיד.)

**הערה דוקטרינרית:** על בר ±200 זו מגמה חזקה אמיתית, ולכן נכון שגם תבניות המשך וגם HFE יורשו שם (לא רק HFE). הדגל + ה-shadow נותנים רשת ביטחון אם זה רועש.

## Phase 3 · Regression + Shadow validation

- **טסט regression:** (א) flag OFF → trend_state בכל הצרכנים **זהה-בייט** ל-post-revert. (ב) flag ON על בר fixture עם CCI=331+GRAY → `studies["trend_state"]`, ה-bar buffer, ה-dispatcher `_ts`, **וגם `decision_tree._a1_trend_gate`** כולם רואים BLUE; HFE עובר ל-`ready_to_route`.
- **אימות חי (shadow, Rule 5):** הדלק את הדגל ב-SHADOW והדבק — בר ±200 שבעבר נחסם: האם עכשיו `ready_to_route=True` וה-HFE מנותב? ובמקביל — האם נוצרו fires שגויים בברים רגילים (לא ±200)? אם רועש → דווח, אל תדליק live.
- **4 צירי UAT** אם נוגעים ב-endpoint כלשהו.

## ⛔ Strategic stop
לפני הפיכת הדגל ל-ON קבוע ב-live (ולא רק shadow-compare) — **עצור ושאל את Michael**. זה משנה אילו תבניות מנותבות על ברי extreme = risk surface.

## בסיום
עדכן `DECISION_LEDGER.md` (D-WDIAG override → 🟢 FIXED-FLAGGED, מקור יחיד) + `STATUS_BOARD.md` (root→fix→verification, Rule 5) + `ROADMAP_TO_LIVE.html`. תווית `D-WDIAG` בכל קובץ.

---

### עיגון קוד
- `backend/v9/systems/woodies/woodies_system.py`: בניית `studies` (~251-267), `wb=WoodiesBar(**studies)` (~290), `detect_all_patterns` (~302), בלוק ה-override להסרה (~358-361), `WoodiesDecisionContext(studies=studies)` (~401-411).
- `backend/v9/systems/woodies/decision_tree.py:176` — `_a1_trend_gate` קורא `ctx.studies.get("trend_state")` (זה הצרכן שהיה מנותק).
- דגל: היכן שנקראים שאר דגלי S4 (env).
