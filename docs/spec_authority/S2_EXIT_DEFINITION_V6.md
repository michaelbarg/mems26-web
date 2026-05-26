# S2_EXIT_DEFINITION_V6.md
# הגדרת יציאה מעסקה · S2 מערכת 5 דקות

**Status:** 🔒 LOCKED
**Date:** 2026-05-23
**Version:** V6 (V5 + Type C time-based exit added per Michael 23/5 17:00)
**מטרה:** להגדיר מתי יוצאים מעסקה — ולמנוע זריקת עסקאות על רעש שוק

**Amendments log:**
- V5 → V6 (23/5 17:00) · Added "Type C · Time-based Exit (DD only)" — per Day Type windows, DD = price ≤ entry − 1 tick (LONG) / ≥ entry + 1 tick (SHORT). Clock from FIRE. Triggers only if T1 NOT hit. Section header renamed "שני סוגי יציאה" → "שלושת סוגי יציאה". Summary expanded.
- V6 (23/5 17:30) · Day Type fix — 6 → **7 day types** per Master Summary Sheet 3 (NeuE 45min + NeuC 30min split + NT 20min listed but NO TRADE).

---

## ארכיטקטורת יציאה — שתי שכבות מקבילות

**Stop order ו-Exit rules הם לא חלופות. שניהם פעילים תמיד.**

```
[FIRE]
  │
  ├── Stop order → מוגש לפלטפורמה מיידית (הגנה מכנית קשה)
  │   גם אם הקוד קורס / connectivity נפסק / אין signal — יש הגנה
  │
  └── TradeManager → מנטר כל bar במקביל (חוכמה)
        IF thesis broken (Type A) → cancel stop + market exit מוקדם
        IF noise (Type B)         → לא עושה כלום
        IF T1 hit                 → מזיז stop ל-BE+1T
        IF T2 hit                 → מפעיל trail
```

| מצב | Stop order | Exit rule | תוצאה |
|-----|-----------|-----------|-------|
| הכל תקין | בשוק | לא מופעל | ממשיכים ל-T1/T2/T3 |
| Thesis נשבר מוקדם | בשוק (לא נפגע) | מופעל | יציאה מוקדמת · stop מבוטל |
| Noise בלבד | בשוק | לא מופעל | נשארים · stop נשאר |
| Stop נפגע | נפגע | — | יציאה מכנית (last resort) |

**הסדר המדויק לאחר כניסה:**
```
1. FIRE → place stop order מיידי at structural anchor
2. TradeManager מנטר כל bar:
     Type A trigger → cancel stop + market exit
     Type B / noise → do nothing
     T1 hit         → move stop to BE+1T
     T2 hit         → cancel stop + activate trail
3. Stop = last resort בלבד
```

> **Stop הוא רשת הביטחון. Exit rules הם החוכמה.**
> ה-Exit rules מוציאים אותך לפני שהstop נפגע — כשהthesis משתנה.
> זה חוסך כסף כי לא מחכים עד הקצה.

---

## עיקרון יסוד

> **יציאה היא לא אירוע מחיר — היא אירוע thesis.**
>
> הכניסה נבנתה על סיבה ספציפית.
> יוצאים רק כאשר הסיבה הזו **כבר לא תקפה** — לא כאשר המחיר הגיע לנקודה מסוימת.

---

## שלושת סוגי יציאה

### Type A · Thesis Invalidation — לצאת מיד

הסיבה לכניסה נשברה. הthesis לא עוד תקף.

| Trigger | תנאי | פעולה |
|---------|------|-------|
| **Close through stop** | close של 5-min bar מתחת לstop (LONG) / מעלה (SHORT) **+ volume ≥ avg** | EXIT מיד |
| **New opposing belly** | belly footprint חדש נוצר מהכיוון ההפוך | EXIT מיד |
| **TCCI × CCI14 cross** | TCCI חוצה את CCI14 נגד הכיוון | EXIT מיד |
| **Direction change confirmed** | S1 מדווח direction change | EXIT מיד |
| **Close back through broken level** | Initiative: close חזרה מתחת/מעל הרמה השבורה + volume | EXIT מיד |

### Type B · Noise — לא לצאת

המחיר "הגיע" לstop אבל הthesis עדיין תקף.

| מה שקורה | למה זה רעש | פעולה |
|---------|-----------|-------|
| **Wick בלבד מתחת לstop** | אין close confirmation · market makers testing | להישאר |
| **Throwback לneckline** (H&S / Double) | נורמלי לחלוטין · 65-68% מהמקרים לפי Bulkowski | להישאר |
| **Spike על volume נמוך** | אין אישור · לא institutional | להישאר |
| **Consolidation / base building** | thesis מתפתח · accumulation בתוך range | להישאר |
| **Flag pullback (Bull/Bear Flag)** | חלק מהpattern · pole completion עדיין תקף | להישאר |

### Type C · Time-based Exit (DD only) — לצאת בסוף החלון

עסקה שתקועה ב-DD זמן רב — ה-thesis התפוגג. יוצאים לפני שה-stop ייפגע.

**מקור:** D-091 §"Day-type targets" — עמודת Time Stop.

**תנאי trigger (כל התנאים חייבים להתקיים בו-זמנית):**

| # | תנאי |
|---|---|
| 1 | עסקה עדיין פתוחה (stop לא נגע) |
| 2 | T1 עוד לא נפגע · אם T1 נפגע → stop נמצא ב-BE+1T → לא DD יותר → Type C לא רלוונטי |
| 3 | **DD מוגדר עם buffer של 1 tick:**<br>LONG: `current_price ≤ entry_price − 1 tick`<br>SHORT: `current_price ≥ entry_price + 1 tick` |
| 4 | זמן שעבר מ-FIRE ≥ Time Stop window לפי Day Type (טבלה למטה) |

**Time Stop windows (מ-FIRE · in clock minutes · per Master Summary Sheet 3):**

| Day Type | Code | Window | פעולה ב-expiry |
|----------|------|--------|------------------|
| Trend Normal | TN | None | לעולם לא · ride the trail |
| Trend DD | TDD | 90 min | DD → market exit · אחרת ride |
| Variation | NV | 60 min | DD → market exit · אחרת ride |
| Neutral Extreme | NeuE | 45 min | DD → market exit · אחרת ride |
| Neutral Center | NeuC | 30 min | DD → market exit · אחרת ride |
| Normal | Norm | 30 min | DD → market exit · אחרת ride |
| Nontrend | NT | n/a | NO TRADE לכתחילה |

**הערה על Neutral split (Master Summary 23/5):** NeuE (Extreme) ו-NeuC (Center) הם שני day types שונים — חלון הם 45 vs 30 דקות. בעבר היה day type "Neutral" אחד עם 45 דקות · זה תוקן.

**Action:** cancel stop order · market exit כל ה-contracts הנותרים.

**הגיון:** עסקה שתקועה ב-DD זמן רב → ה-thesis התפוגג → צא לפני שה-stop ייפגע. חיסכון 2-4 ticks בממוצע לעומת stop hit.

**Flat (price within ±1 tick של entry):** לא DD · Type C **לא** מופעל · ride.

---

## כלל הבסיס — Close-based, לא Wick-based

```
Stop = נקודת invalidation מבנית (לפי תבנית)

Exit trigger = 5-min bar CLOSE × volume confirmation

wick בלבד = אין exit · גם אם ה-wick נוגע בstop
spike < avg_volume = אין exit
```

**החריגים היחידים שיוצאים ללא close:**
- TCCI × CCI14 cross (flow indicator — real-time)
- New opposing belly (footprint — real-time)
- Direction change ב-S1 (system-level signal)

---

## הגדרת Exit לפי משפחת תבנית

### Reactive LONG/SHORT

```
thesis = sellers exhausted + buyers belly + COT confirmation + at support

thesis נשבר (Type A):
  ✅ Close מתחת ל-belly low (LONG) / מעל belly high (SHORT)
  ✅ Belly חדש מהצד השני על high volume
  ✅ POC migration התהפך (ל-3 ברים)
  ✅ TCCI cross

thesis בתקפו (Type B · noise):
  ❌ Wick מתחת לbelly low על low volume
  ❌ Test של support level ללא close breakthrough
  ❌ 1-bar spike עם immediate recovery
```

### Initiative LONG/SHORT

```
thesis = breakout מעל רמה + accumulation + 2 tests + expansion

thesis נשבר (Type A):
  ✅ Close חזרה מתחת/מעל הרמה השבורה + volume ≥ avg (recapture = failed breakout)
  ✅ 2nd test נכשל — price breaks HL (LONG) / LH (SHORT)
  ✅ Direction change confirmed

thesis בתקפו (Type B):
  ❌ Wick מתחת לרמה השבורה על low volume
  ❌ Normal consolidation (base building אחרי breakout)
  ❌ Pullback עד 50% של expansion — עדיין בריא
```

### Inverse H&S · H&S Top

```
thesis = reversal confirmation + neckline break + volume expansion

threshold: throwback לneckline = נורמלי לחלוטין (65% LONG · 68% SHORT)
  → אין לצאת על throwback · זה part of the pattern

thesis נשבר (Type A):
  ✅ Close מעל right shoulder (Inverse H&S) / מתחת ל-right shoulder (H&S Top)
  ✅ Head re-tested (pattern reset)
  ✅ TCCI cross בזמן throwback (לא recovery)

thesis בתקפו (Type B):
  ❌ Throwback לneckline (64-68% מהמקרים · תן לו להגיע ולחזור)
  ❌ Wick מעל neckline בלי close
```

### Double Bottom (Eve&Eve) · Double Top (Adam&Adam)

```
thesis = 2nd bottom higher than 1st (Eve&Eve) / 2nd top lower (Adam&Adam) + volume

thesis נשבר (Type A):
  ✅ Close מתחת ל-1st bottom (Double Bottom) / מעל 1st top (Double Top)
  ✅ Pattern fully resets

thesis בתקפו (Type B):
  ❌ Throwback לneckline (64%)
  ❌ Wick מתחת ל-2nd bottom על low volume
```

### Bull Flag · Bear Flag

```
thesis = pole + consolidation + continuation signal (H2 / L2)

flag low/high = structural stop · לא מחיר arbitrary

thesis נשבר (Type A):
  ✅ Close מתחת ל-flag low (Bull Flag) / מעל flag high (Bear Flag)
  ✅ Pole ≥ 50% retraced (flag became reversal not continuation)
  ✅ TCCI cross תוך כדי flag

thesis בתקפו (Type B):
  ❌ Normal consolidation בתוך ה-flag channel
  ❌ Wick מחוץ ל-flag על low volume
  ❌ Deep pullback ≤ 61.8% של pole (עדיין בריא)
```

---

## שילוב עם Trail Logic

```
לפני T1:
  → Stop = structural anchor (לפי תבנית)
  → יציאה רק על Type A trigger

T1 hit:
  → Stop → Break-Even + 1T
  → Type B tolerance מצטמצמת (יש לנו profit to protect)

T2 hit:
  → Trail מתחת ל-HL closes (LONG) / מעל LH (SHORT)
  → Type B עדיין בתוקף אבל חלון צר יותר

Post-T2:
  → ATR chandelier (1× today_typical)
  → כל close נגד הkiוון שנוגע ב-chandelier = exit
```

---

## Volume Confirmation — מה זה "high volume"?

```python
avg_volume = rolling_mean(bar_volumes, window=20)  # 20 ברים = 100 דקות

high_volume = bar.volume >= 1.0 × avg_volume   # threshold ל-Type A
low_volume  = bar.volume <  0.7 × avg_volume   # noise zone
```

---

## מה זה אומר לקוד

הקוד הנוכחי ב-TradeManager:
```python
# הגרסה הנוכחית (שגויה):
if bar.low <= stop_price:
    exit_trade()  # wick trigger! יזרוק עסקאות על noise

# הגרסה הנכונה (thesis-based):
if bar.close <= stop_price and bar.volume >= avg_volume * 1.0:
    exit_trade()  # Type A: close + volume
elif new_opposing_belly_detected():
    exit_trade()  # Type A: footprint
elif tcci_crosses_cci14():
    exit_trade()  # Type A: flow
# else: wick בלבד = אין יציאה
```

---

## סיכום — 3 שאלות per-bar + Type C clock check

ה-TradeManager בודק **שני תהליכים מקבילים**:

### תהליך 1 · Per-bar decision (Type A vs B)

על כל close של 5-min bar — 3 שאלות:

```
1. האם זה CLOSE או WICK?
   → Wick בלבד = Type B = לא לצאת

2. האם ה-volume מאשר?
   → Volume < 0.7× avg = noise = לא לצאת

3. האם ה-thesis עדיין תקף?
   → כן (throwback נורמלי / consolidation) = לא לצאת
   → לא (belly חדש / direction change / TCCI) = לצאת מיד
```

### תהליך 2 · Time clock check (Type C)

על כל minute (independent of bars) — 4 תנאים:

```
1. עסקה פתוחה (stop לא נגע)?
2. T1 לא נפגע עדיין?
3. DD active לפי buffer 1-tick (LONG: price ≤ entry−1T · SHORT: price ≥ entry+1T)?
4. (now − fire_time) ≥ Time Stop window לפי Day Type?

כל ה-4 = כן → market exit · cancel stop
```

---

*End of S2_EXIT_DEFINITION_V6.md · 2026-05-23 · Michael Barg*
