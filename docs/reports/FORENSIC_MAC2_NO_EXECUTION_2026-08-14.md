# FORENSIC — מק-2 לא כותב עסקאות: מפת מסלול-הביצוע והשורש המוכח

**תאריך:** 2026-08-14 · **סוכן:** cowork-dev (מריץ ממק-1, גישת-קריאה-בלבד למק-2)
**דרישת מייקל (מילולית):** *"מק-2 חייב להיות עצמאי ולקחת עסקאות בדיוק כמו מק-1. הוא על סים
ולקח אפס עסקאות — לא היום, לא השבוע. אני רוצה הוכחה, לא תיאוריה."*

**שום דבר לא שונה בשום מכונה.** כל הממצאים מ-API קריאה-בלבד, מ-DB קריאה-בלבד, ומהקוד.

---

## 0. תשובה בשורה אחת

מק-2 **כן** העביר היום לפחות **4 מועמדים דרך כל שרשרת-השערים**. הם מתו **אחרי** השערים
ו**לפני** ה-INSERT — בתוך `_execute_shadow`, בחריגה (exception) ש**נבלעת** ב-
`woodies_system.py:1268`. לכן: אין שורת `v9_trades`, אין רשומת-החלטה, ו-4 המועמדים
החוזרים נחסמו `duplicate_fire` — כי הרישום ל-`_recent_fires` קורה **לפני** הביצוע.
**`send_orders_to_trade_service=0` הוא לא הסיבה** — אף שער בבקאנד לא קורא אותו.

---

## 1. מפת מסלול-הביצוע: מ-`route_setup` עד שורה ב-`v9_trades`

### 1.1 מי קורא ל-`route_setup`

| מקור | קובץ:שורה | מערכת | עוטף ב-try? | מה קורה לחריגה |
|---|---|---|---|---|
| Woodies (ZLR/GHOST/TREND_STEP/FAMIR/GB100/HTLB) | `backend/v9/systems/woodies/woodies_system.py:1247` | S4 | **כן** (1246-1269) | **נבלעת** → `logger.warning("[Woodies] Gateway route_setup failed: %s", e)` + `current_state["last_route"]={"error": str(e)}` |
| FiveMin | `backend/v9/systems/five_min/five_min_system.py:1413`, `:1514`, `:2270` | S2 | כן (2271-2273) | נבלעת → `logger.warning("[FiveMin] Gateway route_setup failed: %s", gw_err)` |
| Footprint | `backend/v9/systems/footprint/footprint_system.py:457` | S3 | כן (471-472) | נבלעת |
| TrendStep detector | `backend/main.py:898` | S4 | — | — |
| Debug/SIM fire | `backend/v9/api/v9/trade_commands.py:320` | S4 | — | — |
| POST ידני | `backend/v9/api/v9/gateway_routes.py:132` | any | — | — |

### 1.2 השרשרת בתוך ה-Gateway

```
route_setup()                          trading_gateway.py:630
 ├─ normalize pattern                                    :637
 ├─ confluence observe_route (flag OFF → None)           :655
 ├─ result = _route_setup_inner(setup, system_id)        :660   ← כל השערים
 ├─ log BLOCKED                                          :685
 ├─ self.decisions.append(_dec)                          :713   ← ה"למה לא ירה"
 ├─ _persist_decision → gateway_decisions.jsonl          :714 / :451
 └─ ops_log FIRED/BLOCKED                                :722
```

```
_route_setup_inner()                   trading_gateway.py:758
 … ~30 שערים עם early-return …
 ├─ cluster_guard.is_blocked / record_attempt            :2866-2869
 ├─ ► DEDUP REGISTRATION  _recent_fires.append(...)      :2875   ← I-60: אחרי כל השערים
 ├─ shadow_trade = _execute_shadow(...)                  :2882   ← ה-INSERT האמיתי
 ├─ self.shadow_trades.append(shadow_trade)              :2883
 ├─ result["shadow"] = shadow_trade["trade_id"]          :2886
 ├─ confluence shadow-only return                        :2898
 ├─ cluster_blocked → return                             :2943
 ├─ trading_paused → return                              :2953
 ├─ _selfheal_demo_slot()                                :2965
 ├─ metadata.shadow_only → return                        :2971
 └─ RR_FIRE_SELECTION ? buffer(:2987) : first-wins demo(:2997)/live(:3007)
```

### 1.3 היכן נכתבת השורה ל-DB

```
_execute_shadow()                      trading_gateway.py:3226
 ├─ g1 = extract_g1_entry_context(cross_context)         :3231
 ├─ tm_setup = {...}                                     :3232-3253
 ├─ pattern_id_at_entry = resolve_pattern_id(setup, g1)  :3251
 ├─ trade_id = TradeManager.accept_setup(tm_setup,"shadow") :3254
 │    └─ manager.py:304 accept_setup
 │        ├─ ValueError guards (mode/firing_system/direction) :314-323
 │        ├─ float(setup["stop"])                             :327
 │        ├─ effective_contracts(setup)                        :340
 │        ├─ self._snapshot.capture(...)  ← None בפרודקשן      :369-373
 │        ├─ trade = V9Trade(...)                              :375
 │        ├─ self._db.add(trade)                               :409  ◄ ה-INSERT
 │        └─ self._db.flush()                                  :410  ◄ nextval נצרך
 ├─ on_fill(trade_id, entry)                             :3256
 └─ _db.commit()  (עטוף — לא זורק)                       :3258
```

**מסלול-גיבוי (כש-TradeManager הוא None):** `_build_trade` (:3646) + `_persist_trade` (:3684)
→ `safe_execute` ב-`backend/v9/db/safe_writer.py:135`. **חשוב:** `safe_execute` **לעולם לא
זורק** — הוא מחזיר `None` ומרשם warning (`safe_writer.py:159-161`). כלומר במסלול-הגיבוי
נוצר תמיד `trade_id` (uuid, `:3650`) ורשומת-החלטה `shadow_only` **הייתה** מופיעה. **היא לא
מופיעה** ⇒ מק-2 לא במסלול-הגיבוי.

---

## 2. טבלת השערים — ערך במק-1 מול ערך במק-2 (נמדד היום)

מקורות: `GET /api/v9/gateway/status`, `GET /api/v9/gateway/decisions?limit=200`,
`GET /api/v9/status`, DB של שתי המכונות, `.env` של מק-1, `docs/FLAG_INDEX.md`.

| # | שער / תנאי | קובץ:שורה | מק-1 | מק-2 | חוסם את מק-2? |
|---|---|---|---|---|---|
| 1 | `kill_switch` | `:804` | לא מופעל | לא מופעל (0 החלטות) | ❌ |
| 2 | `session_gate_closed` | `:813` | פתוח (החלטות עד 19:25Z) | פתוח (החלטות עד 19:25Z) | ❌ |
| 3 | `COLD_START_GUARD_V1` | `:824` | ON (`.env:463`) | ON — 3 חסימות 13:58-14:00Z ואז נפתח | ❌ (רק בבוט) |
| 4 | `SSV_GATE_V1` | `:903` | **OFF** (ברירת-מחדל) · `veto_active=true` תצוגה בלבד | OFF · `veto_active=false` | ❌ |
| 5 | `DEDUP_FIRE_GUARD` | `:914` | **ON** (`.env:109`) — 0 חסימות היום | **ON** — **4 חסימות `duplicate_fire`** | ⚠️ תסמין, לא שורש |
| 6 | `LAYER0_CHOP_GATE` | `:943` | OFF (פסיקה קבועה) · `chop_state=EXPANDING` | OFF · `chop_state=EXPANDING` | ❌ |
| 7 | `OPENING_TYPE_GATE` | `:956` | OFF (פסיקת מייקל `6f3614a5`) | OFF | ❌ |
| 8 | `daytype_playbook` | `:1051` | 1 חסימה | 2 חסימות | ❌ |
| 9 | `rr_hard_floor` / `rr_entry_gate` | `:600-628` | 4 חסימות | 4+4 — **כולן לפני 15:21Z** (תיקון ה-IB) | ❌ אחרי 15:21Z |
| 10 | `s4_risk_cap` / `pattern_loss_breaker` | `:2851` | 0 | 0 | ❌ |
| 11 | `cluster_guard` | `:2866` | `active=false`, 1 ניסיון | `active=false`, 1 ניסיון | ❌ |
| 12 | `cooldown` | `:2820` | 6 סטופים, `active=false` | 0 סטופים, `active=false` | ❌ |
| 13 | `trading_paused` (קובץ) | `:2953` | לא | לא (0 החלטות) | ❌ |
| 14 | `metadata.shadow_only` | `:2971` | לא | לא | ❌ |
| 15 | `MEMS26_MODE` | `.env:9` | `live` | `live` (`/api/v9/status → mode:"live"`) | ❌ |
| 16 | `demo_enabled_systems` | status | `[]` | `[]` | ❌ (זהה) |
| 17 | `live_enabled_systems` | status | `[2,4]` | `[2,4]` | ❌ (זהה) |
| 18 | `is_sim` / `trade_account` | sierra_state | live / APEX | **1 / Sim1** | ❌ — לא נקרא ע"י אף שער |
| 19 | `send_orders_to_trade_service` | sierra_state | 1 | **0** | ❌ — ראה §4 |
| 20 | **`_execute_shadow` → `accept_setup`** | `:3254` | ✅ עובד — 19 שורות היום | 🔴 **זורק חריגה** | ✅ **כן — זה השורש** |

### 2.1 שלוש המדידות שהן ההוכחה

| מדד | מק-1 | מק-2 | מסקנה |
|---|---|---|---|
| `gateway/decisions → today` | `fired=4, shadow_only=13, blocked=38` | `fired=0, shadow_only=0, blocked=46` | אף החלטה לא הגיעה לשורה 713 |
| `gateway/status → shadow_active_count` (`= len(self.shadow_trades)`, `:3199`) | **16** | **0** | שורה `:2883` מעולם לא רצה היום |
| `v9_trades_id_seq.last_value` מול `max(id)` | `687 / 687` | **`51 / 51`** | **אף INSERT לא נשלח לשרת** |

**למה מדד ה-sequence הוא הוכחה חותכת:** `nextval` ב-Postgres הוא **לא-טרנזקציוני**. INSERT
שנכשל על constraint, או טרנזקציה שעשתה rollback, **עדיין צורכים** את המונה. אילו
`accept_setup` היה מגיע ל-`self._db.flush()` (`manager.py:410`) ונכשל — `last_value` היה
עומד היום על 55 ומעלה. הוא עומד על **51** בדיוק, שווה ל-`max(id)`.
⇒ **הקוד לא הגיע ל-`self._db.add()`**. החריגה מוקדמת יותר.

וה-DB של מק-2 **כן** כתיב היום — אותו מסד קיבל היום 260 שורות ב-`v9_bars_5min_woodies`
(זהה למק-1), ו-`v9_bars_5min_woodies_id_seq`/`v9_bars_cumulative_delta_id_seq` מתקדמים.
זו לא בעיית DB כללית — זו בעיה ממוקדת במסלול-הביצוע.

### 2.2 ההוכחה שהמועמדים באמת עברו את כל השערים

הרישום ל-`_recent_fires` קיים ב**מקום אחד בלבד** בקוד — `trading_gateway.py:2875` — אחרי
כל שער חוסם (I-60, 2026-07-02). `duplicate_fire` (`:924`) יכול להיווצר **רק** מרישום קודם
בתוך 30 שניות.

**הפרכת החלופה "קוד ישן מלפני I-60":** אילו מק-2 היה מריץ קוד שבו הרישום קורה בבדיקת-ה-dedup
עצמה, כל ניסיון-שני באותו בר היה `duplicate_fire`. בפועל ב-15:50:01/15:50:04Z שני הניסיונות
נחסמו `structural_targets_wrong_side`, ובכל 46 ההחלטות רק 4 הן `duplicate_fire`. ⇒ מק-2
מריץ את הקוד הנוכחי, והרישום הוא אחרי-השערים. **HYPOTHESIS ELIMINATED.**

### 2.3 ארבעת המועמדים שמתו — מול מק-1 באותה שנייה

| שעה (UTC) | מועמד | מק-1 | מק-2 |
|---|---|---|---|
| 17:25:04-05 | S4 ZLR SHORT @7800.25 | `lsma_flat` (חסום) | **`duplicate_fire`** ⇒ היה רישום ב-17:24:35-17:25:05 |
| 17:35:03-07 | S4 ZLR SHORT @7800.25 | ✅ `shadow_only` → **trade 684** | **`duplicate_fire`** |
| 18:45:02-06 | S4 GHOST LONG @7804.75 | ✅ `shadow_only` → **trade 686** | **`duplicate_fire`** |
| 18:50:00-07 | S4 ZLR LONG @7805.25 | ✅ `shadow_only` → **trade 687** | **`duplicate_fire`** |

בשלושת המקרים האחרונים **מק-1 כתב שורה ומק-2 לא** — על אותו מועמד, באותה שנייה, באותו מחיר.
זו הנקודה המדויקת שבה שתי המכונות מתפצלות.

---

## 3. השורש המוכח

> **מק-2 עובר את כל השערים, נרשם ל-`_recent_fires` (`trading_gateway.py:2875`), ואז
> `_execute_shadow` (`:3226`) זורק חריגה לפני `self._db.add()` (`manager.py:409`).
> החריגה מתפשטת דרך `_route_setup_inner` → `route_setup` (מחוץ ל-try של שורה 693,
> כי היא נזרקת ב-`:660`) ונבלעת ב-`woodies_system.py:1268`.**

**התוצאה בשרשרת:**
1. אין `INSERT` → אין שורה ב-`v9_trades` (sequence לא זז).
2. הקוד לא מגיע ל-`route_setup:713` → **אין רשומת-החלטה** → הפאנל "למה לא ירה" עיוור לגמרי
   לכשל הזה. זהו **silent failure** בניגוד ל-CLAUDE.md § "No silent failures".
3. הרישום מ-`:2875` **נשאר** ב-`_recent_fires` 30 שניות → הניסיון-החוזר של אותו בר נחסם
   `duplicate_fire`. זהו **תקלת I-60 חוזרת, קפיצה אחת מאוחר יותר**: I-60 העביר את הרישום
   אחרי ה**שערים**, אבל הוא עדיין **לפני ה**ביצוע**. כשל-ביצוע מרעיל את חלון-ה-30-שניות.

**מדוע מק-1 לא נפגע:** `/tmp/backend.err.log` של מק-1 היום — `19` שורות
`[Gateway] SHADOW trade TM id=…`, ו-**0** שורות `route_setup failed` ו-**0** שורות
`SHADOW trade commit failed`. המסלול נקי אצלו. זו קבוצת-ביקורת מלאה: אותו קוד, אותה שרשרת,
אותו בר — הבדל סביבתי במק-2.

### 3.1 מה כן שולל, מה נשאר — **UNPROVEN: שורת-החריגה המדויקת**

| מועמד | סטטוס |
|---|---|
| `self._trade_manager is None` (מסלול-גיבוי) | **נשלל** — `safe_execute` לא זורק, ו-`_build_trade:3650` תמיד מחזיר `trade_id`; היינו רואים החלטת `shadow_only` עם uuid. גם `bar_router.subscribers["5min"]=7` **זהה** בשתי המכונות ⇒ `BarLevelDetector.subscribe` (main.py:1084) הצליח ⇒ `set_trade_manager` (main.py:1091) באותו בלוק רץ. |
| סחיפת-סכימה ב-`v9_trades` | **נשלל** — 33 עמודות זהות, אותם טיפוסים, אותה nullability, אותם 7 constraints. |
| מונה-PK לא-מסונכרן (duplicate key) | **נשלל** — `last_value=51 = max(id)`, אין התנגשות. |
| `on_fill` (`:3256`) | **נשלל** — הוא אחרי `flush()`; ה-sequence היה זז. |
| `_db.commit()` (`:3258`) | **נשלל** — עטוף ב-try (`:3257-3260`), רק warning. |
| `self._snapshot.capture` (`manager.py:370`) | **נשלל** — `TradeManager(db=tm_db)` (main.py:1077) בלי `snapshot_service` ⇒ `self._snapshot is None`. |
| `resolve_pattern_id` (`:3251` / `:58`) | **נשלל** — שלוש קריאות `.get` ואופרטור `or`; אין מסלול-זריקה. |
| **`extract_g1_entry_context`** (`:3231` → `trade_context.py:614`) | **נשאר מועמד** — הקריאות האחרות אליו (`:1054`, `:1252`) עטופות ב-try, ולכן לא מוכיחות שהוא בטוח. חשד מוגבר: הפורנזיקה של היום (commit `5642529e`) מצאה במק-2 **enum-repr** שנשמר במקום `.value` ו-`lock_state` תקוע ב-PENDING. |
| `accept_setup` guards `:314-323` / `float(setup["stop"])` `:327` | **נשאר מועמד** (נמוך) |
| `effective_contracts` (`manager.py:340` → `sierra_command.py:636`) | **נשאר מועמד** — החלק של המרג'ין עטוף (`:664`), אבל `_effective_contracts_raw` (`:543`) לא כולו. |
| `V9Trade(...)` ctor (`manager.py:375`) | **נשאר מועמד** (נמוך) |

**החריגה המדויקת כבר רשומה על מק-2** בשני מקומות — צריך רק להסתכל (§6).

---

## 4. `send_orders_to_trade_service=0` — הכרעה: **(b) תסמין של מצב-סים, ו-(c) חסר-רלוונטיות לכתיבה ל-DB**

**כל הקוראים בבקאנד — קריאת-grep מלאה על `backend/` ו-`sc_study/`:**

```
backend/v9/api/v9/context_radar.py:294:  "sendorders": st.get("send_orders_to_trade_service"),
```

**זהו. קורא יחיד, ותצוגתי בלבד** (שדה ב-JSON של רדאר-ההקשר, נצרך ב-
`frontend/v9/src/v9/components/layout/ContextRadar.tsx`). **אף שער, אף `if`, אף
early-return** ב-`trading_gateway.py`, `trade_manager/manager.py`, `sierra_command.py`
או `trade_commands.py` לא קורא את השדה.

**מי כותב אותו:** ה-DLL, ורק כמראה של מצב-הסימולציה של Sierra:
```cpp
sc_study/MES_AI_DataExport_merged.cpp:1956
    sc.SendOrdersToTradeService = !sc.GlobalTradeSimulationIsOn;
sc_study/MES_AI_DataExport_merged.cpp:2080,2099
    "\"send_orders_to_trade_service\":%d,"  … sc.SendOrdersToTradeService ? 1 : 0
```
מק-2 ב-Trade Simulation Mode (`is_sim=1`, `trade_account=Sim1`) ⇒ `GlobalTradeSimulationIsOn=1`
⇒ `SendOrdersToTradeService=0`. **זו ההתנהגות הנכונה והצפויה לסים** (וזה בדיוק התיקון של
07-07, `docs/decisions/D-093_SIERRA_ORDER_ROUTING.md`).

**ולעניין השאלה בסוף הסעיף:** גם אילו ה-DLL היה מסרב להציב הזמנה, **שורת ה-DB עדיין הייתה
נכתבת** — ה-INSERT מתבצע ב-`accept_setup` (`manager.py:409`) **לפני** כתיבת
`trade_command.json`, ובמסלול-SHADOW אין בכלל פקודת-Sierra. סירוב-DLL היה מייצר שורה עם
`state=CANCELLED`/`outcome=CANCELLED` (מסלול `#462` המתועד ב-`gateway_routes.py:76-84`).
**אין שום שורה כזו במק-2.** ⇒ הכשל מוקדם בהרבה מה-DLL, והשדה הזה הוא רעש.

> ⚠️ **אזהרה מבצעית:** אל תשנו את `send_orders_to_trade_service` ואל תכבו את מצב-הסים של
> Sierra במק-2 כ"תיקון". זה לא יכתוב אף שורה ל-`v9_trades`, וזה **כן** יהפוך את מק-2
> ממכונת-סים למכונה ששולחת הזמנות אמיתיות — שינוי משטח-סיכון-מסחר.

---

## 5. מתי מק-2 הפסיק לכתוב — ומה השתנה

### 5.1 המדידה

```
MAC-2  v9_trades:  count=51  max(id)=51   ·  שורות היום: 0
by_date (מק-2):  2026-07-17 → 7 שורות (id 44-50) · 07-16 → 8 · 07-15 → 6 ·
                 07-14 → 4 · 07-13 → 14 · 07-10 → 2 · 07-06 → 3 · (NULL entry_ts → 7)
by_mode (מק-2):  demo=14 (אחרון 2026-07-17)  shadow=25 (אחרון 07-16)  live=12 (אחרון 07-16)
MAC-1  v9_trades:  count=597 max(id)=687   ·  שורות היום: 21 (id 667-687)
```

**התאריך האחרון שמק-2 כתב שורה ל-`v9_trades`: 2026-07-17.** מאז — **28 ימים, אפס שורות.**

### 5.2 הקורלציה

- **2026-07-17 = יום המהפך.** המסחר עבר ל-MacBook והמכונה השנייה הפכה לסים
  (commits `5c8f51d0`, `85fd4b3b`: `MOBILE_REMOTE_URL` iMac→ריק "MacBook serves own live
  data"; זיכרון-פרויקט `project_0717_trading_cutover_to_macbook`). מאותו רגע מק-2 לא היה
  אמור לייצר עסקאות במהלך רוב התקופה.
- **מ-2026-08-07** מק-2 רץ SIM-parallel (LIVE_CHANNEL), אבל **עד היום ב-15:21Z** כל מועמד
  שלו מת על `rr_hard_floor`/`rr_entry_gate` בגלל ה-IB השגוי מ-Sierra שלו
  (commit `fc953a8b` + `aa49bcdf` `IB_BARS_VALIDATE_V1`). **שער ה-R:R הסתיר את הבאג הזה
  לגמרי** — שום מועמד לא הגיע לשלב הביצוע.
- **היום, אחרי `IB_BARS_VALIDATE_V1` (15:21Z), מק-2 הגיע לראשונה מאז 07-17 לשלב הביצוע —
  ומיד נחשף הכשל.** כלומר: זה **לא** רגרסיה של היום. זה באג שהיה חבוי מאחורי החסימות
  שנפתחו היום.

### 5.3 מה **לא** מוכח — **UNPROVEN**

לא ניתן להוכיח מרחוק האם בין 07-18 ל-08-13 היו מועמדים שעברו את השערים ומתו באותה דרך:
`self.decisions` הוא in-memory (`_deque(maxlen=300)`, `:380`) וה-JSONL היומי
(`~/SierraChart_Data/v9_export/gateway_decisions.jsonl`) **אינו נחשף בשום endpoint**.
פקודה מס' 3 ב-§6 סוגרת את זה בשאילתה אחת.

---

## 6. הפקודות שסוגרות את זה במכה אחת — **להריץ על מק-2**

מריץ: **מייקל / cc-mac2** (טרמינל מקומי על מק-2). הכל קריאה-בלבד.

```bash
# 1) ◄◄ הפקודה החשובה ביותר — טקסט החריגה המדויק כבר יושב בלוג
grep -n "route_setup failed" /tmp/backend.err.log | tail -20
# צפוי: "[Woodies] Gateway route_setup failed: <ExceptionType>: <message>"
#   ≥4 מופעים היום סביב 17:24-17:25, 17:34-17:35, 18:44-18:45, 18:49-18:50 UTC
#   (= 20:24, 20:34, 21:44, 21:49 שעון ישראל).
#   ⇒ אם ריק: הפרכת ההשערה — עברו מיד לפקודה 2.

# 2) חלון-הלוג סביב שני ה-duplicate_fire האחרונים (שעון ישראל בלוג)
grep -n -A3 -B25 "duplicate S4 LONG GHOST\|duplicate S4 LONG ZLR" /tmp/backend.err.log | tail -80
grep -nE "21:4[0-9]:|21:5[0-9]:" /tmp/backend.err.log | grep -iE "traceback|error|exception|Gateway|TradeManager|safe_writer" | tail -40

# 3) כמה זמן זה נמשך — היסטוריית ההחלטות היומית (סוגר את §5.3)
ls -la ~/SierraChart_Data/v9_export/gateway_decisions*.jsonl
python3 - <<'PY'
import json,glob,collections
for f in sorted(glob.glob("/Users/michael/SierraChart_Data/v9_export/gateway_decisions*.jsonl")):
    c=collections.Counter()
    for l in open(f):
        try: d=json.loads(l); c[d.get("blocked_by") or d.get("outcome")]+=1
        except Exception: pass
    print(f.split("/")[-1], dict(c))
PY

# 4) אימות שאין INSERT (חוזר על המדידה שלי מקומית)
psql postgresql://localhost/mems26 -c \
  "SELECT last_value FROM v9_trades_id_seq; SELECT count(*),max(id) FROM v9_trades;"

# 5) ודא ש-TradeManager באמת חובר בעלייה
grep -nE "TradingGateway → TradeManager wired|BarLevelDetector subscribed|TradingGateway startup failed" \
  /tmp/backend.err.log | tail -5

# 6) שורת-האתחול של הדגלים (לא ps eww — לפי feedback_verify_live_flags)
grep -n "\[env_loader\]" /tmp/backend.err.log | tail -3
```

**אם פקודה 1 מחזירה שורות** — יש לנו את שם-החריגה והשורה, וזה מסיים את החקירה.
**אם היא ריקה** — ההשערה מופרכת ויש להריץ את 2, שיראה מה קרה בין ה-fire לחסימה החוזרת.

**אל תריצו** `POST /api/v9/gateway/route_setup` או `/api/v9/trade/debug_gateway_fire`
כבדיקה: `debug_gateway_fire` (`trade_commands.py:322-327`) עוקף את שער-הסשן וקורא ישירות
ל-`_execute_demo` — הוא **יוצר עסקה אמיתית וכותב פקודה ל-Sierra**. זו לא בדיקה, זו עסקה.

---

## 7. רשימת-תיקונים מסודרת

| # | תיקון | קובץ:שורה | מי מריץ | אימות צפוי |
|---|---|---|---|---|
| **0** | **אבחון לפני תיקון** — פקודה 1 ב-§6 והדבקת הפלט הגולמי (חוק 5) | — | מייקל / cc-mac2 | שם-חריגה + הודעה |
| **1** | **לתקן את השורש שפקודה 0 חושפת.** אין לנחש ואין לתקן מהזיכרון (CLAUDE.md § Pre-LIVE). | לפי הממצא | cc-mac2 | טסט-רגרסיה חדש (חובה לכל תיקון-באג) |
| **2** | **לסגור את ה-silent-failure:** להחליף את הבליעה ב-`woodies_system.py:1268` ב-`logger.error` + `exc_info=True`, ולרשום החלטת-gateway עם `blocked_by="execution_error"` כדי שהפאנל "למה לא ירה" יראה את זה. אותו טיפול ב-`five_min_system.py:2273` ו-`footprint_system.py:472`. | `woodies_system.py:1268`, `five_min_system.py:2273`, `footprint_system.py:472` | cc-mac2 | כשל-ביצוע מלאכותי מופיע ב-`/api/v9/gateway/decisions` עם `execution_error` |
| **3** | **לתקן את הרעלת-חלון-ה-dedup (I-60, קפיצה שנייה):** להעביר את `_recent_fires.append` מ-`:2875` ל**אחרי** ש-`_execute_shadow` החזיר בהצלחה (אחרי `:2886`), או לבצע rollback לרישום אם הביצוע נכשל. **ניסיון-חוזר תקין לא יכול להיחסם ע"י ירי שמעולם לא נרשם.** | `trading_gateway.py:2871-2879` | cc-mac2 | טסט: `_execute_shadow` שזורק ⇒ המועמד הבא **לא** מקבל `duplicate_fire` |
| **4** | **ריצת-אימות סוף-יום למחרת** — לא `fire_drill` ולא `debug_gateway_fire`, אלא שוואה של יום-מסחר מלא | — | cowork-dev | `MAX(v9_trades_id_seq)` במק-2 **זז**; `shadow_active_count > 0`; `decisions.today.shadow_only > 0` |
| **5** | **מדד-פערים קבוע לפרוטוקול-הבוקר**: `mac2.shadow_active_count` ו-`v9_trades_id_seq` מול מק-1. אם ה-sequence לא זז ביום שבו היו gate-passes — התראה. | `scripts/mems26_verify.sh` | cc-mac2 | הרצה יומית ירוקה |

**אין לגעת:** ב-`send_orders_to_trade_service`, ב-Trade Simulation Mode של Sierra, ב-
`is_sim`, וב-`trade_account` של מק-2. הם לא בשרשרת הכשל (§4).

---

## 8. תמצית-הראיות (חוק 5 — פקודה + פלט גולמי)

```
$ python3 -c "psycopg2 … SELECT count(*),max(id) FROM v9_trades"
MAC-1 (597, 687)        MAC-2 (51, 51)
$ … SELECT entry_ts::date, count(*) … GROUP BY 1 ORDER BY 1 DESC
MAC-1 2026-08-14 → 21   MAC-2 (אחרון) 2026-07-17 → 7
$ … SELECT last_value,is_called FROM v9_trades_id_seq
MAC-1 (687, True)       MAC-2 (51, True)
$ … SELECT count(*) FROM v9_bars_5min_woodies WHERE ts::date=CURRENT_DATE
MAC-1 (260,)            MAC-2 (260,)          ← ה-DB של מק-2 כתיב היום
$ … information_schema.columns WHERE table_name='v9_trades'
v9_trades cols: mac1=33 mac2=33 · חסרות במק-2: 0 · חסרות במק-1: 0 · הפרשי-טיפוס: 0

$ curl .../api/v9/gateway/decisions?limit=200 → .today
MAC-1 {"fired":4,"blocked":38,"shadow_only":13,"by_gate":{rr_entry_gate:4, awaiting_release:7,
       lsma_flat:8, cont_trend_filter:5, direction_context:4, entry_not_confirmed:4,
       daytype_playbook:1, pattern_stop_cooldown:1, structural_targets_wrong_side:2,
       eod_entry_cutoff:2}}
MAC-2 {"fired":0,"blocked":46,"shadow_only":0,"by_gate":{cold_start_guard:3,
       cont_trend_filter:5, awaiting_release:8, daytype_playbook:2, rr_hard_floor:4,
       entry_not_confirmed:8, rr_entry_gate:4, structural_targets_wrong_side:2,
       direction_context:2, lsma_flat:2, duplicate_fire:4, eod_entry_cutoff:2}}

$ curl .../api/v9/gateway/status
MAC-1 shadow_active_count=16  demo_enabled=[] live_enabled=[2,4]
MAC-2 shadow_active_count=0   demo_enabled=[] live_enabled=[2,4]

$ grep -c "SHADOW trade TM id=" /tmp/backend.err.log      (מק-1)  → 19
$ grep -c "route_setup failed" /tmp/backend.err.log       (מק-1)  → 0
$ grep -rn "send_orders_to_trade_service" backend/ --include=*.py
backend/v9/api/v9/context_radar.py:294:  "sendorders": st.get("send_orders_to_trade_service"),
   (קורא יחיד בכל הבקאנד — תצוגה בלבד)
```

---

**חתום:** cowork-dev · 2026-08-14 · read-only forensic, שום שינוי בשום מכונה.
מה שמוכח מסומן כמוכח; שורת-החריגה המדויקת מסומנת **UNPROVEN** ונסגרת בפקודה 1 של §6.
