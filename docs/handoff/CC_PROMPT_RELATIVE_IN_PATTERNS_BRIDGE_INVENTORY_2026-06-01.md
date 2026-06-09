# CC PROMPT — יחסי גם בתוך התבנית + רשימת נתוני הגשר ב-Build Status

**תאריך:** 2026-06-01 · **מקור:** Cowork (Michael) · **מצב:** SHADOW · Rule 5 · אפס שינוי order/risk/sizing · **strategic-stop על שינוי מספרי-זיהוי (trading-logic).**

## #1 · החישוב היחסי גם בתוך זיהוי התבנית עצמו
**מצב (Cowork):** OFA expansion/POC-return כבר יחסיים בתבנית; ratios (vol_drop 10%, belly 1.5, symmetry 5%, retrace 50%, imbalance 2.5) יחסיים מטבעם; CCI ±100/±200 + ספירות ברים = מבני (לא להמיר). **נשארו ספי-מרחק קבועים בתוך הזיהוי שצריך להמיר.**
- **audit:** עבור על כל ספי ה**זיהוי** ב-S2 (OFA reactive/initiative + H&S/Double/Flags), S3 (4 גלאים), S4 (9 patterns). לכל סף: **fixed-price (tick/pt)** / **ratio (כבר יחסי)** / **מבני (Woodies/ספירה)**. הדבק טבלה.
- **חשודים fixed-price להמרה ליחסי (×ATR):** H&S head extension ≥2T · breakout +1T · double-bottom neckline · sweep-return ±2T · flag pole-min 4pt/16t · SR proximity · stop floor. ולכל אחד הצע המרה (k×ATR5m) עם prior.
- **שמור ratios + מבני כמו שהם** (תעד למה CCI ±100 קבוע — מתודולוגיה).
- ⚠️ **strategic-stop:** הצג טבלת audit + ההמרות המוצעות **לאישור Michael לפני שינוי** (שינוי ספי-זיהוי = trading-logic). k = priors, ננעל אחרי soak.
- **השלם את ה-consistency מהדוח הקודם:** הנתיבים שעדיין flag-gated (quality_tier proximity, adaptive_stop floor, sr_proximity, detectors range_ticks) — ליישר ל-relative-always (Michael בחר יחסי-תמיד). [אם Michael מעדיף לשמור flags always-on לצורך revert ב-soak — לאשר.]

## #2 · Build Status — רשימת כל נתוני הגשר (real-time + מיפוי)
הוסף ל-Build Status פאנל **"Bridge Data Inventory"**: לכל נתון/stream שמתקבל מהגשר —
- **שם השדה/stream** · **ערך זמן-אמת** · **טריות** (age/FRESH) · **לאיזו מערכת** (S1-S6) · **לאיזו תבנית** (אם רלוונטי — איזה pattern צורך אותו).
- כלול: 5min OHLCV, woodies studies (CCI/TCCI/SWI/CZI/LSMA/EMA/Proj/trend), footprint (ask/bid/delta/levels), tick_reversal, tpo (POC/VAH/VAL/IB), cumulative_delta, 5min_continuous, live_price.
- מקור המיפוי: BarRouter subscriptions + מי קורא כל שדה. observability בלבד.

## פלט
`docs/reports/RELATIVE_IN_PATTERNS_BRIDGE_INVENTORY_2026-06-01.md`: (1) טבלת audit ספי-זיהוי (fixed-price/ratio/structural) + המרות מוצעות **לאישור** · (2) Bridge Data Inventory ב-Build Status (screenshot + מיפוי שדה→מערכת→תבנית). עדכון STATUS_BOARD.

**שערים:** #1 audit+propose בלבד — **לא לשנות ספי-זיהוי בלי אישור Michael** (strategic-stop). #2 = observability. אפס שינוי order/risk/sizing.
