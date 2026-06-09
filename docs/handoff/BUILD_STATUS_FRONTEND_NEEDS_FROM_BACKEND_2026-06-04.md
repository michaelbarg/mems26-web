# Build Status — מה ה-frontend צריך מה-backend (רשימת חוסרים למפתח) · 2026-06-04

> כל `⧗ ממתין ל-backend` בעמוד `/build` = שדה שה-backend עדיין לא פולט ל-`/api/v9/build/pattern-status`.
> **source-of-truth (Rule 1):** חסר → `present=false`/`None`, **לא לסנתז**. **exposure-only** —
> מציגים מה שהמנוע כבר מחשב; שינוי ערך stop/target/risk = strategic-stop נפרד.
> פירוט מלא: `docs/plans/BUILD_STATUS_BACKEND_GAP_LIST_2026-06-04.md`. פרומפט ה-★: `CC_PROMPT_P0_2_…`.
> כל שדה חדש: regression test + 4 צירי UAT (Quality/Recency/Cardinality/Latency) + raw output.

---

## ★ חוסם-על — עושים ראשון (P0-2) · פרומפט: `CC_PROMPT_P0_2_EXPOSE_TARGETS_STOP_2026-06-04.md`
חשיפת `r_t1`/`risk_1R` מהמנוע סוגרת 3 דברים יחד: (א) שלב TARGETS/STOP בתצוגה · (ב) **גייט אמיתי**
(`r_t1≥min_r_t1_threshold` במקום `confidence≥0.5`) · (ג) stop/r_t1 לכל הצרכנים.

- [ ] **S2 TARGETS/STOP** → `s2_inspector.py` (מ-`five_min/adaptive_stop.compute_stop` + `targets_table.get_targets`):
  `stop_price` · `risk_1R` · `t1_price` · `t2_price` · `t3_price` · `r_t1` · `time_stop` · `sizing` (full/half/reject) · `variant_tag` (VSA).
- [ ] **S4 TARGETS/STOP** → `woodies_inspector.py` (stop שכבתי: primary 3 ticks / ATR-cap×group / floor):
  `stop_price` · `atr_14_ticks` · `r_t1` · `t1_price` · `t2_price` (ticks לפי תבנית) · `entry_price`.
- [ ] **S4 Day-Type Matrix verdict** → `woodies_inspector.py`: `matrix_verdict` (✅/⚠️/❌ לתבנית×יום) · `entry_hint` · `t1_ref`.
- [ ] **S3 TARGETS/STOP** → `footprint_inspector.py` (כשיופעל): `stop_price`=min(low,entry−tick) · `t1` · `t2` · `time_stop`=15.
- [ ] **החלפת הפרוקסי בגייט אמיתי** → `s2_inspector.py` + `woodies_inspector.py:344`:
  `confidence≥0.5` ⟵ `r_t1 ≥ min_r_t1_threshold` (+ `pre_fire R:R≥1.0`). חסר r_t1 לתבנית → `present=false`, לא פרוקסי.
- [ ] **אודיט prospective-vs-fire-time** (מה-CC prompt): אם stop/r_t1 מחושב רק ב-fire-time → preview read-only
  שקורא לאותו `compute_stop` (0 reimplement/synth). **אימות:** ל-עסקה שנורתה, ה-stop/r_t1 המוצג == מה שהמנוע השתמש בו.

## שערי-אש גלובליים (P0-1) · inspector חדש → `aggregator.py:106`
- [ ] **pre_fire_validator** (מ-`backend/v9/shared/pre_fire_validator.py`): 7 בדיקות —
  side · ordering · `R:R≥1.0` · confidence · time_stop · entry/stop≠provisional · dedup.
- [ ] **risk_checks LIVE** (מ-`backend/v9/gateway/risk_checks.py`): loss<$250 · ≤5 trades · ≤2 contracts ·
  14:30 ET cutoff · STOP אחרי 2 הפסדים רצופים · news ±10m (`risk_checks.py:70-74` → סמן `not_implemented`).
- [ ] **לאן בסכמה:** מבנה חדש `global_firewall` ברמת-התגובה (לא פר-מערכת): `{key, passed, detail, severity}`.

## שערים אמיתיים פר-מערכת (P1)
- [ ] **S6 Killzone** → `killzone_inspector.py` (חדש, מ-`zones.py` · 11 אזורים · קנוני-לעת-עתה):
  `is_gate_open` · `current_killzone` · `quality` · `volatility` · `sizing_modifier` · `block_reason` ·
  `time_in_zone_min` · `time_to_next_zone_min`. + להחליף את ה-RTH הגנרי בשער ה-killzone.
- [ ] **S2 S/R + COT/AMT** → `s2_inspector.py`: `sr_proximity` כשער עם ערך חי · COT>AMT directional (לא always-pass).
- [ ] **S4 anti-patterns + A7** → `woodies_inspector.py`: AP1/4/5/7/8/9 + `reject_reason` ·
  A7 (news ±5m · cool-down 30m · daily loss −$200 · stop 3–8pt · EOD>60m).
- [ ] **S4 dispatch** → `woodies_inspector.py`: `winning_pattern` + `r_t1` מול `min_r_t1_threshold` + GRAY/YELLOW. (תלוי P0-2.)

## טריות + שלמות-מקור (P1)
- [ ] **S2 · 3 קובצי Sierra freshness** → `s2_inspector.py`: `cumulative_delta.json` (COT/AMT) · `tpo.json` (POC) · `volume_profile.json` (S/R).
- [ ] **S4 · cci_6_tcci** → `woodies_inspector.py`: השדה מחושב in_memory ומסומן present — לפי Rule 1 להחזיר `missing` כשהמקור הקנוני (Sierra SG4) שותק, לא לשערך.

## חיווט מערכות + הקשר (P2)
- [ ] **S5 TPO** → `tpo_inspector.py` (חדש) → `aggregator.py:106`: POC/VAH/VAL · IB · `profile_shape` · `otf_clarity` · naked_pocs · `data_quality`.
- [ ] **S1 pre-open context** → `day_type_inspector.py`: pd_poc/vah/val · on_high/low · gap · overnight_bias · decision matrix · `get_targets()`.
- [ ] **S3 disabled flag** → `footprint_inspector.py`: מודעות ל-`FOOTPRINT_DISABLED` (`atr.py:101`) + לתקן `get_state()`→`get_current()`.
- [ ] **טבלאות אפיון מ-endpoint** → `aggregator.py`/route חדש: לחשוף `targets_table.py._TARGETS` + `atr_caps.py`
  (כרגע ממורקרים ב-`BuildTreeView.tsx` verbatim — חשיפה מבטלת drift ומאפשרת להסיר מה-frontend).

---

## מה ה-frontend כבר מציג חי (לא חסר — לידיעה)
`data_freshness` (שכבה 0) · `live_inputs` · `interpretations` · `global_gates` (כפי שנפלטים) ·
`patterns[].components[]` · `readiness` (verdict + checks). הטבלאות (📖 אפיון) מוצגות verbatim כ-config.

## תלות
P0-2 קודם לכול (חוסם-על). P1-5 (dispatch) ו-החלפת-הפרוקסי תלויים ב-P0-2. השאר עצמאי.
