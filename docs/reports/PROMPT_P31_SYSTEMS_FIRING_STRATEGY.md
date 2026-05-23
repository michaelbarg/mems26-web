# מצב אסטרטגי — מי יורה, איך, ומה לא עובד

**נחקר:** 2026-05-22 09:30 IL · עודכן 09:55 IL · **שאלת מיכאל:** "מה כל מערכת עושה? למה רק Woodies יורה? איך הstop/T1/T2/T3 מחושבים?"
**סטטוס:** אבחון מלא + 2 החלטות (S1=observer, S3=firing) + 1 תיקון בוצע (types.ts) + פרומפט CC מוכן ל-3 באגי S3.

> **🎨 גרסה ויזואלית של הדוח הזה** — `~/.cursor/projects/Users-michael-Downloads-mems26-web-git/canvases/firing-systems-decision-trees.canvas.tsx`  
> פותחים מ-Cursor (canvas רץ ליד הצ'אט). מכיל את כל עצי ההחלטה, בלוקים צבעוניים לפי סוג שלב (input/decision/fire/fail), טבלאות פטרנים, וכרטיסי באג מודגשים.

> **עדכונים מהחקירה (לסעיף 7) + תיקון 2026-05-22 10:15 אחרי גילוי D-082/D-086:**
> - ❌ **טעות בקריאה ראשונית:** חשבתי ש-`wrappers.py:9` (Master Matrix V1.0) הוא מקור האמת ל-S3=firing. בפועל **D-082 LOCKED** (post-Master Matrix) קובע ש-S3 = Observer בלבד, ו-**D-086** (2026-05-20 LOCKED) דוחה את ה-fix ל-post-SHADOW.
> - ✅ **S1 = Observer** — נכון, תוקן ב-types.ts.
> - ✅ **S3 = Observer** — תוקן ב-types.ts (S3: firing → observer חזרה).
> - ❌ **Bug #1 (`if mode == "LIVE":`) הוא לא באג** — זה safety net מכוון per D-082. **לא לתקן.**
> - ✅ **Bug #2 (AMT per-bar)** ו-**Bug #3 (COT לא reset)** הם בעיות אמיתיות — כי S3 כprovider של data ל-S2 חייב לעבוד נכון.
> - ✅ **CC תיקן Bug #3** (COT session-aware) — uncommitted, 4/4 pytest PASS.
> - ⬜ **Bug #2 (AMT rolling)** — לא תוקן עדיין.

---

## TL;DR (תקציר 90 שניות)

| מערכת | תפקיד מתוכנן | מצב בפועל | חוסם עיקרי |
|---|---|---|---|
| **S1 Day Type** | firing | **observer בפועל** (אין `route_setup` בקוד) | by design — לא באג |
| **S2 5-Min** | **firing** | רץ אבל לא יורה (0 trades מ-1,229) | **AMT=0 + COT היסטורי −144K** → תנאי `cot/amt` לא מתקיימים |
| **S3 Footprint** | observer | רץ, מספק data ל-S2 | **AMT=0** — חישוב לא רץ |
| **S4 Woodies** | **firing** | **1,229 trades** ✓ | — |
| **S5 TPO** | observer | רץ, מספק POC/VAH/VAL | — |
| **S6 Killzone** | gate | רץ, מספק `edge_class` | **באג RCA-1** (לא קשור לירי, רק לדיווח confluence) |

**בשורה התחתונה:** מתוך 3 firing systems רק 1 פעיל (S4). S2 מוכן בקוד אבל **נחסם** ע"י נתון שגוי מ-S3. S1 בכלל לא firing למרות התיוג.

---

## 1. מצב נתונים נוכחי (DB snapshot, 2026-05-22 09:00 IL)

| טבלה | שורות | משמעות |
|---|---|---|
| `v9_trades` | 1,230 (כולם S4 / shadow) | רק Woodies מייצר trades |
| `v9_woodies_signals` | 30,348 | זיהויי תבניות (לא כולם הופכים ל-trade — decision_tree מסנן) |
| `v9_five_min_setups` | **0** | S2 מעולם לא ירה |
| `v9_five_min_state` | **0** | S2 לא שומר state |
| `v9_footprint_setups` | **0** | S3 לא יוצר setups (by design — observer) |
| `v9_bars_5min` | 1,887 | בארים זורמים תקין |
| `v9_bars_footprint` | 2,457 | footprint zoom תקין |
| `v9_system_signals` | 41,310 | אגרגציה של signals לכל המערכות |

נתוני live state מה-API (אותה שעה):

```text
S1 (day_type/current):
  day_type="Normal", IB classified, opening_type="INDETERMINATE"
  → אין route_setup. observer בלבד.

S2 (five_min/current):
  running=true, hydrated=true, mode="OVERNIGHT_MODE"
  buffer_size=629, last_pattern=null
  → קוד רץ אבל אף תבנית לא מתגלה

S3 (footprint/current):
  running=true, hydrated=true, last_classification="NO_SETUP"
  cot=-144,527, amt=0.0    ← הבעיה כאן
  dominance="BALANCED", initiative_type="NEUTRAL"

S4 (Woodies) — לא נדגם, אבל מ-DB ידוע שירה 1,229 trades
```

---

## 2. עץ החלטות — S4 Woodies (היחיד שעובד)

```
Input: 5min Woodies bar (OHLCV + 11 studies מ-Sierra)
    ↓
buffer.append(bar) → trim ל-50 בארים
    ↓
compute_all_studies(highs, lows, closes)
    [cci_14, cci_6_tcci, ema_34, lsma, swi, czi, trend_state, predictor_next_cci]
    ↓
detect_all_patterns(buffer)  ← 9 detectors:
    [ZLR, TLB, TT, GB100, VEGAS, GHOST, FAMIR, HTLB, HFE]
    כל אחד מחזיר PatternResult(detected, entry_price, stop, targets[], confidence)
    ↓
best = max(patterns, key=confidence)
    ↓
WoodiesDecisionTree.evaluate_bar(ctx)  ← A1-A8 + B1-B3 stages
    ready_to_route? failed_stages?
    ↓ ready_to_route=True
gateway.route_setup({
    firing_system: 4,
    direction: best.direction,
    entry_price: best.entry_price,    ← מהtbnht
    stop:        best.stop,           ← 8 ticks = 2.00pt מהentry (ZLR)
    t1:          best.targets[0],     ← 12 ticks = 3.00pt (ZLR; 1.5R)
    t2:          best.targets[1],     ← 24 ticks = 6.00pt (ZLR; 3R)
    t3:          0.0                  ← לא קיים — Woodies תמיד 2 targets
}, 4)
    ↓
TradeManager.accept_setup()
INSERT v9_trades
```

### Stop/T1/T2 לכל תבנית Woodies (קבועים בקוד)

| Pattern | Stop | T1 | T2 | T3 | Risk:Reward |
|---|---|---|---|---|---|
| **ZLR** | 8 ticks (2.00pt) | 12 ticks (3.00pt) | 24 ticks (6.00pt) | — | 1:1.5 / 1:3 |
| **TLB** | (ככה"נ דומה) | | | — | |
| **TT** | (ככה"נ דומה) | | | — | |
| **GB100** | (ככה"נ דומה) | | | — | |
| **VEGAS** | (ככה"נ דומה) | | | — | |
| **GHOST** | (ככה"נ דומה) | | | — | |
| **FAMIR** | (ככה"נ דומה) | | | — | |
| **HTLB** | (ככה"נ דומה) | | | — | |
| **HFE** | (ככה"נ דומה) | | | — | |

⚠️ **לא בדקתי את כל ה-9 קבצי patterns; ZLR מאומת. שאר ה-8 צריך לוודא — סביר שיש שונות.**

**ה-Pattern Engine קובע את הtargets בעצמו** — לא ה-TradeManager, לא הGateway. כל detector מציב entry/stop/targets ב-PatternResult ומעביר ל-route_setup.

---

## 3. עץ החלטות — S2 FiveMin (קיים בקוד, לא יורה)

```
Input: 5min bar event (event.payload או dict)
    ↓
buffer.append(bar) → trim ל-20 בארים
    ↓
_detect_reactive(buffer) — 4-bar pattern:
    LONG:
      bar1: c<o + vol>0          (sellers dominate)
      bar2: vol <= 10% × bar1    (90% volume drop)
      bar3: c>o + belly_dominant (buyers + footprint belly)
      bar4: c>o                  (confirmation)
      AND: cot > amt             ← נדרש cot מ-S3 לעבור amt מ-S3
    SHORT: mirror, AND: cot < amt
    ↓
אם detect_reactive החזיר None:
_detect_initiative(buffer) — 4-bar (לא בדקנו פרטי)
    ↓
direction found?
    ↓ YES
entry = bar.c
stop  = bar.l - 2.00pt  (LONG)  או  bar.h + 2.00pt  (SHORT)   ← 2pt קבוע
t1_risk = abs(entry - stop)
t1 = entry + t1_risk        (1R)
t2 = entry + 2 × t1_risk    (2R)
t3 = 0.0                    ← לא מחושב
    ↓
emit_t1_setup(...) → pre_fire_validator → gateway.route_setup(2)
INSERT v9_trades
```

### למה לא יורה כרגע

**Three blocking conditions, all from S3 (Footprint) data:**

1. **AMT = 0.0** (API: `"amt": 0.0`). זה נתון שאמור להיות ממוצע נע 90-min של COT, ולא מחושב כרגע.
2. **COT = −144,527** (היסטורי מצטבר, לא reset יומי).
3. **תנאי `cot > amt`** עבור LONG: `-144,527 > 0` = **False** תמיד.
4. **תנאי `cot < amt`** עבור SHORT: `-144,527 < 0` = **True** תמיד, אבל **רק** אם 4-bar pattern של SHORT (b1=buyers, b2=90%drop, b3=sellers+belly, b4=confirm) מתקיים — סיכוי נמוך מאוד באוברנייט.

**אז זה לא בעיית wiring** (process_bar רץ), זה **נתון שגוי מ-S3** שחוסם.

---

## 4. עץ החלטות — S1 Day Type

```
Input: 5min bars + opening type detection
    ↓
classify into Day Type (Trend, Normal, ROT, Gap-Fill, NeutralExtreme...)
    ↓
publish classification → context for S2/S4
    ↓
**NO route_setup() call**    ← S1 לא יוצר trades
```

**מסקנה:** S1 בעצם observer / context-provider. הסיווג "firing" ב-`SYSTEM_ROLES` של ה-frontend היה כנראה תכנון מקורי שלא יושם. אין `accept_setup` מ-S1 בכל הקוד.

**זה לא בהכרח באג** — אבל יוצר חוסר אחידות בין הtypes ל-runtime. צריך להחליט: או להפוך את S1 ל-firing אמיתי, או לסמן אותו רשמית כ-observer ב-types.

---

## 5. ניהול עסקה — TradeManager (אותו עבור כולם)

```
accept_setup(setup)  →  INSERT v9_trades (state=PENDING)
                        stop, t1, t2, t3 = מהsetup
    ↓
on_fill(fill_price)  →  state=FILLED, entry_price=fill_price, entry_ts=now()
    ↓
[market moves]
    ↓
on_target_hit("T1") →  state=PARTIAL
                       t1_hit_ts=now()
                       **Smart BE: stop ← entry** (קבוע, ללא option לכבות)
                       PnL recalc
    ↓
on_target_hit("T2") →  t2_hit_ts=now()
                       PnL recalc
                       **לא סוגר** — נשאר PARTIAL
    ↓
on_target_hit("T3") →  state=CLOSED, exit_reason="T3_HIT"
                       (אבל t3=0 ב-Woodies/FiveMin — אף פעם לא יקרה)
    ↓ או:
on_stop_hit()       →  state=CLOSED, exit_reason="STOP_HIT"
                       exit_price=trade.stop (= entry אם Smart BE התרחש)
```

### חסרים ניכרים ב-TradeManager

| חסר | מה זה אומר | משמעות לpre-LIVE |
|---|---|---|
| **אין trailing stop** | אחרי Smart BE, stop נשאר ב-entry עד שT2/T3 מגיע | מפספס move של 4-5pt + ואז חוזר ל-BE |
| **אין partial exit ב-T1** | כל ה-3 חוזים נשארים עד stop/T2/T3 | הקופסה אומרת C1/C2/C3 אבל בפועל זה 3 חוזים שמתנהלים יחד |
| **אין time stop** | `time_stop_minutes=90` ב-setup אבל לא נאכף | trade יכול להישאר open שעות בלי תזוזה |
| **אין volatility adjustment** | stop קבוע (8 ticks Woodies / 2pt FiveMin) לכל תנאי שוק | ATR=0.5 ל-ATR=3.0 = אותו stop |
| **אין T3 דינמי** | Woodies/FiveMin תמיד t3=0; T3 hit לא קורה לעולם | מפספס runner |

---

## 6. ההמלצות — סדר עבודה לפני LIVE

לפי עקרון "Diagnose first, fix second" + "Smallest correct change":

### 🔴 Priority 1 — חוסם פרה-LIVE (השבוע)

#### P31-STRAT-1: תקן AMT calc ב-S3
- **למה**: בלי AMT, S2 לא יכול לירות לעולם.
- **איפה לחקור**: `backend/v9/systems/footprint/` — מצא את ה-publisher של AMT, ודא ש-90-min rolling window רץ.
- **פעולה צפויה**: ייתכן שmissing init / מצב חדש (`AMT = 0`) במקום לחשב mean. צריך probe.
- **זמן**: 1-2 שעות חקירה + תיקון.

#### P31-STRAT-2: החלט על COT — Reset יומי או מצטבר?
- **למה**: COT=−144K זה אזורית סבל, לא יכול לתת אינדיקציה רלוונטית.
- **שאלה אסטרטגית**: ה-CVD מיועד להיות יומי או מצטבר? לפי הspec, אמור להיות יומי.
- **פעולה צפויה**: לוודא ש-`reset_at_session_open` מוגדר; אם לא, להוסיף.
- **זמן**: 30 דק' חקירה + 30 דק' תיקון.

### 🟡 Priority 2 — לפני SHADOW soak (השבוע הבא)

#### P31-STRAT-3: סדר את התפקיד של S1
- **שאלה**: האם S1 אמור לירות trades עצמאיים? או רק לספק context?
- **פעולה צפויה**: עדכן `SYSTEM_ROLES` ב-types.ts ל-`'observer'`, או בנה route_setup ל-S1 (גדול).
- **זמן**: 15 דק' (אם רק תיוג) או 4-8 שעות (אם logic).

#### P31-STRAT-4: סקירת targets לכל 9 patterns של Woodies
- **למה**: ZLR יש stop=8 ticks/T1=12/T2=24, אבל לא בדקתי את 8 השאר. סביר שיש שונות שלא תכננו.
- **פעולה צפויה**: טבלת השוואה — לכל pattern, מה ה-tick values + מה ה-R:R + האם הם מתאימים לתנאי שוק שונים?
- **זמן**: 1 שעה לקריאת 8 קבצים + 1 שעה לטבלה.

### 🟢 Priority 3 — תכונות לDEMO (לא חוסם LIVE micro)

#### P31-STRAT-5: Trailing stop ב-TradeManager
- **פעולה**: אחרי T1, stop = max(entry, last_swing_low + buffer) במקום קבוע ב-entry.
- **זמן**: 3-4 שעות (חדש) + טסטים.

#### P31-STRAT-6: Partial exit ב-T1
- **פעולה**: ב-T1 לסגור 1/3 או 1/2 מהcontracts, השאר נשאר עם trailing.
- **זמן**: 4-6 שעות (משנה את ה-state machine + PnL calc).

#### P31-STRAT-7: Time stop אמיתי
- **פעולה**: `time_stop_minutes` ב-setup כבר קיים — לאכוף אותו (background task שבודק כל דק').
- **זמן**: 2-3 שעות.

#### P31-STRAT-8: ATR-adaptive stops
- **פעולה**: במקום 8 ticks קבוע, להשתמש ב-`stop = max(8_ticks, 1.5 * ATR_14)`.
- **זמן**: 2-3 שעות + UAT.

---

## 7. שאלות אסטרטגיות שצריך להחליט (Michael)

לפני שאני נוגע בקוד, יש 3 החלטות שלא ברורות לי מהדוח:

1. **האם S1 (Day Type) צריך להיות firing אמיתי?** או רק observer?
   - אם firing — מה ה-trigger? מה הtargets? צריך spec.
   - אם observer — לתקן את types.ts ולסיים.

2. **COT — יומי או מצטבר?** הספץ V3 לא ברור (לדעתי הוא יומי, אבל הקוד לא reset).

3. **Trade management — אסטרטגיה?**
   - 3 חוזים נפרדים שכל אחד יוצא בT1/T2/T3?
   - או 1 trade שמתחלק לחתיכות (current = הכל ביחד)?
   - האם רוצים trailing stop אחרי T2 או רק ahari T1?

---

## 8. מה אני לא טיפלתי בו (גילוי מלא)

- **לא** קראתי את 8 detectors של Woodies מלבד ZLR. סביר שיש שונות בstop/targets.
- **לא** ראיתי את הspec של V3 Constitution לגבי COT reset behavior.
- **לא** קראתי את snapshot service (`backend/v9/services/snapshot_service/`) לעומק.
- **לא** הרצתי probe על AMT/COT ל-S3 (זה ה-next step אם מאשרים P31-STRAT-1).

---

## 8.1 הרחבה — 4 ה-detectors של S3 (Footprint firing signals)

S3 מריץ 4 detectors במקביל בכל בר. הכי חזק (לפי `strength`) זוכה. כל אחד מזהה תופעה אחרת:

| Detector | מזהה | מתאים ל-direction |
|---|---|---|
| **detect_absorption** | מחיר מנסה לפרוץ extreme של בר, אבל volume גבוה ב-עיכוב — מצביע על "absorber" מנגד | Reversal (against the breakout) |
| **detect_stacked_imbalance** | 3+ levels רצופים עם imbalance ratio > 250% — אגרסיביות חד-צדדית חזקה | Continuation (with the imbalance) |
| **detect_sweep_return** | liquidity sweep מעבר ל-extreme, ואז חזרה לתוך הrange — false breakout classic | Reversal (against the sweep) |
| **detect_exhaustion** | בר directional עם diminishing volume — תנועה גוססת | Reversal |

**Sizing**:
- `strength >= 0.6` + 3 confirmations (delta/dominance/initiative aligned) → **full = 3 חוזים**
- `strength >= 0.4` + 2 confirmations → **half = 2 חוזים**
- `strength >= 0.3` + 1 confirmation → **half = 2 חוזים**
- אחרת → **reject**

**Stop / T1 / T2 ב-S3:** הקוד מוודא pre_fire_validator (`backend/v9/shared/pre_fire_validator.py`), שמחשב את הtargets לפי tier. לא בדקתי לעומק — צריך לבדוק לפני שS3 מתחיל לירות.

---

## 8.2 הרחבה — 9 הפטרנים של S4 (Woodies CCI)

| Pattern | קבוצה | מזהה | כיוון |
|---|---|---|---|
| **ZLR** (Zero Line Reject) | Continuation | CCI היה מעל +100, נסוג לאזור 0, ועולה שוב | LONG / SHORT mirror |
| **TLB** (Trend Line Break) | Continuation | פריצה של trendline של CCI עם confirmation | LONG / SHORT |
| **TT** (Tony's Trade) | Continuation | CCI cross של +/-100 עם TCCI alignment | LONG / SHORT |
| **GB100** (Ghost Bar at +100) | Continuation | בר ספציפי שנוגע ב-100 והופך מיד | LONG / SHORT |
| **VEGAS** | Reversal | CCI ב-extreme עם EMA-34/LSMA confluence | LONG / SHORT |
| **GHOST** | Reversal | "ghost bar" pattern — בר שמכחיש מה שהיה | LONG / SHORT |
| **FAMIR** | Reversal | extreme reversal pattern | LONG / SHORT |
| **HTLB** (Hook TLB) | Reversal | hook variation של TLB | LONG / SHORT |
| **HFE** (Hook From Extreme) | Reversal | CCI הגיע ל-extreme ועושה hook אחורה | LONG / SHORT |

**רק ZLR מאומת ב-code-level**: stop=8 ticks, T1=12 ticks, T2=24 ticks, T3=0. שאר 8 הפטרנים — צריך לקרוא את ה-detector. סביר שיש שונות.

---

## 8.3 הרחבה — Event flow: מבר Sierra ל-trade ב-DB

```
Sierra DLL                                 (sc_study/v9_woodies_export.h)
   ↓ writes JSON
~/SierraChart_Data/v9_export/woodies_5min.json
   ↓ polls every ~1s
Bridge (bridge/v9_streams/woodies_5min_stream.py)
   ↓ POST /api/v9/bars/woodies_5min
Backend API (backend/v9/api/v9/bars.py)
   ↓ INSERT v9_bars_5min_woodies + BarRouter.dispatch("woodies_5min", bar)
BarRouter (backend/v9/services/bar_router.py)
   ↓ async dispatch
WoodiesSystem.process_bar(event)           (backend/v9/systems/woodies/woodies_system.py:147)
   ↓ compute studies + detect patterns
gateway.route_setup(setup, firing_system=4)  (backend/v9/gateway/trading_gateway.py)
   ↓ shadow_executor.execute(setup)
TradeManager.accept_setup(setup, mode="shadow")  (backend/v9/services/trade_manager/manager.py:59)
   ↓ INSERT v9_trades (state=PENDING)
TradeManager.on_fill(trade_id, fill_price)
   ↓ UPDATE v9_trades (state=FILLED, entry_price set)
[market moves — BarLevelDetector watches]
   ↓ on_target_hit / on_stop_hit
TradeManager.on_target_hit("T1") → state=PARTIAL + Smart BE
   ↓
TradeManager.on_stop_hit() → state=CLOSED + pnl_usd computed
   ↓
event_emitter.emit("trade_closed", ...) → frontend updates
```

---

## 9. סטטוס נוכחי (עודכן 2026-05-22 09:55 IL)

| # | פעולה | סטטוס | הערה |
|---|--------|--------|------|
| 1 | חקירת כל firing system + עצי החלטה | ✅ הושלם | דוח זה + canvas |
| 2 | החלטה: S1 = observer, S3 = firing | ✅ אישר Michael | Master Matrix V1.0 |
| 3 | עדכון `frontend/v9/src/v9/types/index.ts` SYSTEM_ROLES | ✅ הושלם | תוקן: S1→observer, S3→firing |
| 4 | זיהוי 3 באגי S3 (SHADOW gate, AMT, COT) | ✅ הושלם | code review |
| 5 | פרומפט CC לתיקון 3 הבאגים | ✅ הושלם | `docs/handoff/agents/CC_S3_S2_FIRING_FIX_PROMPT.md` |
| 6 | תיקון 3 הבאגים בקוד | ⬜ ממתין | יועבר ל-CC |
| 7 | אימות חי ב-RTH: S2 + S3 יורים | ⬜ blocked-by-CC | UAT 4-axis |
| 8 | סקירת 8 patterns של Woodies (P31-STRAT-4) | ⬜ ממתין | DEMO priority |
| 9 | החלטה על trade management (trailing/partial/time) | ⬜ ממתין | מיכאל — אחרי LIVE micro |

---

## 10. קישורים

| קובץ | תוכן |
|---|---|
| **🎨 Canvas ויזואלי** — `~/.cursor/projects/Users-michael-Downloads-mems26-web-git/canvases/firing-systems-decision-trees.canvas.tsx` | עצי החלטה + טבלאות + כרטיסי באג ויזואליים |
| `docs/reports/PROMPT_P31_CONFLUENCE_FILTER_RCA.md` | RCA-1: Killzone direction bug |
| `docs/handoff/agents/CC_S3_S2_FIRING_FIX_PROMPT.md` | פרומפט מוכן ל-CC ל-3 באגי S3 |
| `docs/handoff/P31_TASK_BOARD.md` | Task board הראשי |
| `backend/v9/systems/wrappers.py:8-14` | מקור Master Matrix V1.0 לתפקידי systems |
| `backend/v9/services/trade_manager/manager.py` | TradeManager lifecycle |
| `frontend/v9/src/v9/types/index.ts:222-233` | SYSTEM_ROLES (עודכן 2026-05-22) |
