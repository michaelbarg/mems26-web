# RESEARCH 02 — כיול ספי S2 (תבניות/stops) ליחסי ATR

**מקור:** מחקר חיצוני (ספרות + פרקטיקה) שהתקבל 2026‑05‑31. **סטטוס:**
RECOMMENDATION ONLY — אין שינוי קוד. **שער:** אישור Michael + backtest.

## מסקנה מרכזית
להמיר את כל ספי המחיר ב‑S2 (expansion, proximity, stop, pole height, head
extension, double‑bottom tolerance) ממוחלטים ליחסיים — אך **לא לכולם אותו עוגן**:
stops ו‑expansion → ATR; tolerance של שיאים/שפלים → אחוז מהמחיר (LMW 1.5%) או
ATR קצר; pole height של flags → ATR (Katsanos).

## מקדמי k מומלצים (priors — לכייל ב‑backtest)

| פרמטר | המלצה יחסית | מקור |
|---|---|---|
| Expansion (בר חריג) | בר ≥ **1.5–2×ATR(5min)**; או ATR Δ≥5% | LeBeau (0.6–0.8× breakout); Katsanos (Δ5%) |
| Proximity ל‑S/R | buffer **1–1.5×ATR**; stop 1–1.5×ATR מעבר לאזור | LuxAlgo/TrendSpider; AlgoStorm |
| Stop loss | **1.5–2×ATR** (אינטראדיי), 3×ATR (swing) | Wilder 3×, Turtles/Van Tharp 2–3×, Chandelier (22,3.0) |
| Stop floor | רצפת מינ' — עדיף לבטא כ‑ATR מינ' או %מחיר | (להשאיר backstop) |
| Pole height (flags) | **≥5.5×ATR**; flag ≤2.5×ATR; ATR Δ≥5% | Katsanos, TASC Dec 2014 / thinkorswim |
| Head extension (H&S) | פרופורציונלי; כתפיים ביחס **0.80–1.20** | Bulkowski |
| Double bottom/top tolerance | שיאים within **1.5%** (יומי); ל‑5‑דק' עדיף **0.5–1×ATR** | Lo‑Mamaysky‑Wang (2000) |

## ATR — בחירה
- לסיגנלים 5‑דק' → **ATR 5‑דק'** (len 14, או **6–10** לזמן החזקה <1 שעה). לא ATR
  יומי (כולל overnight/gap לא רלוונטי → stops רחבים מדי).
- שיטה: Wilder(SMMA) איטית; EMA/lookback קצר מגיב מהר — לאינטראדיי עדיף קצר.

## עונתיות תוך‑יומית
ES: בר 5‑דק' טיפוסי ~3–7 נק'; בר פתיחה ראשון 12–18+ נק'; אמצע יום מתכווץ
30–50%. → סף expansion/stop אחיד לכל היום לא אופטימלי; עדיף ATR מתגלגל או נירמול
לפי שעה.

## כלל אצבע ATR יומי ES (הקשר)
VIX 12–15 → 15–25 נק' · 16–22 → 25–45 · 23–30 → 45–70 · 30+ → 70–120+.
MES=ES בנקודות (רק $5/נק' מול $50) → הכיול היחסי זהה, רק position size שונה.

## אזהרות (Davey + curve‑fit)
- Kevin Davey: אל תניח ש‑ATR תמיד עדיף — לעיתים dollar stops מנצחים, ו‑3×ATR
  מייצר stops עצומים בתנודתיות גבוהה. **לבדוק dollar vs ATR ב‑backtest** (≥200
  טריידים, profit factor + drawdown, ≥2 regimes).
- חלק ממקדמי הפלטפורמות מצוטטים ממקורות לא‑מאומתים/מפוברקים — priors בלבד.
- walk‑forward + out‑of‑sample חובה.

## מקורות
Lo‑Mamaysky‑Wang (2000, JoF 55(4)); Katsanos (TASC Dec 2014 / thinkorswim);
Wilder (1978); Van Tharp; Turtles (Faith); Chandelier (LeBeau/Elder); Bulkowski
(thepatternsite.com); Kevin Davey (kjtradingsystems); CME (MES specs);
Young Money Investments (ES ATR 2024‑25).

> STATUS: RECOMMENDATION ONLY — מימוש אחרי אישור + backtest.
