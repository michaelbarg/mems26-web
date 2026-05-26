# META-PROMPT · Pipeline 5 · DLL + Sierra DEMO Prep
**מיועד ל:** Claude Desktop
**תפקיד Desktop:** לכתוב את ה-mega-prompts לCC עבור Pipeline 5 (P5-0 עד P5-7)
**תפקיד Cursor:** לבדוק G3 כל mega-prompt לפני ביצוע
**תלויות:** SHADOW gate GREEN (P-S0) → P5-0 יכול לרוץ במקביל ל-SHADOW

---

## הקשר

**מה קיים היום:**
- הDLL כותב `trade_command.json` ← `ACK_SHADOW` בלבד (שורות 813-815 ב-`sc_study/MES_AI_DataExport.cpp`)
- `sc.SubmitOCOOrder()` / `sc.BuyEntry()` — אפס הפניות בDLL
- Gateway legacy (`backend/v9/gateway/trading_gateway.py`) — עובד ב-production
- Gateway new (`backend/v9/services/trading_gateway/gateway.py`) — לא מחובר ל-main
- `bridge/trade_commands.py::TradeCommandHandler` — קיים ומלא, לא מחובר ל-startup

**מה חסר לDEMO:**
1. DLL שקורא `sc.BuyEntry()` / `sc.SellEntry()` אמיתי (mode=demo בלבד)
2. gateway canonical (אחד מהשניים) — P5-0 קובע
3. Bridge handler מחובר ל-startup
4. Position reconciliation

**החלטות שעדיין פתוחות (מיכאל צריך לנעול לפני P5-1):**
- **D-093.Q1** — איזה gateway canonical? Legacy או New? (P5-0 audit נותן recommendation)
- **D-093.Q2** — מה ה-DEMO account identifier בSierra? (לא PA-APEX-125218-01 שהוא placeholder)
- **D-093 proposed re-locks** — `sc.BuyEntry()` + Attached Orders במקום `sc.SubmitOCOOrder()`?

---

## מה Desktop צריך לייצר

### Mega-Prompt 1 · P5-0 · Gateway Audit (CC)

**קובץ:** `docs/handoff/CC_MEGA_PROMPT_P5_0_GATEWAY_AUDIT_2026-05-26.md`

**המטרה:** CC מבצע audit מלא של שני ה-gateway paths ומגיש דוח recommendation.

**Desktop יכתוב mega-prompt שכולל:**

#### מה CC צריך לעשות:

**Step 1 — Read two paths in full:**
- `backend/v9/gateway/trading_gateway.py` (legacy · wired in main.py)
- `backend/v9/services/trading_gateway/gateway.py` + executors (new · unwired)
- `backend/v9/services/sierra_command.py` (shared · used by legacy)
- `bridge/trade_commands.py` (TradeCommandHandler · unwired)
- `backend/main.py` lines 340-360 (gateway init)

**Step 2 — 4-step KEEP/ADAPT/REPLACE/DEFER audit:**
```
Per file, classify:
KEEP   — good as-is, just wire
ADAPT  — good bones, needs 1-3 changes before wiring
REPLACE — rewrite from scratch
DEFER  — not needed for DEMO scope

For each classification include:
- Why this classification
- What changes if ADAPT
- Blast radius if REPLACE
```

**Step 3 — Recommendation for D-093.Q1:**
```
Format:
RECOMMENDATION: [Legacy/New/Merge]
RATIONALE: <3 bullet points>
RISK IF WRONG: <1 sentence>
PROPOSED MIGRATION PATH: <steps>
```

**Step 4 — Dead code map:**
```
3 dead executors to delete:
- backend/v9/gateway/live_executor.py
- backend/v9/gateway/demo_executor.py  
- backend/v9/gateway/shadow_executor.py
Confirm: rg these filenames — no production imports outside tests
```

**Step 5 — Research cross-check:**
CC צריך לקרוא `docs/research/SIERRA_ORDER_ROUTING_RESEARCH_2026-05-24.md` §3.3
ולציין האם הresearch recommendation תואם את הaudit שלו.

**Output:** `docs/reports/P5_0_GATEWAY_AUDIT.md` (≥300 שורות · כולל כל 5 steps · verbatim code excerpts לכל classification)

**Spec authority:**
- `docs/decisions/D-093_SIERRA_ORDER_ROUTING.md` §Gap 2 · §Gap 3 · §Implementation P5-0
- `docs/research/SIERRA_ORDER_ROUTING_RESEARCH_2026-05-24.md` §3.3

**Forbidden:** אין מחיקת קוד · אין שינויי wiring · audit בלבד

---

### Mega-Prompt 2 · P5-7 · Bridge Integration (CC)

**קובץ:** `docs/handoff/CC_MEGA_PROMPT_P5_7_BRIDGE_INTEGRATION_2026-05-26.md`

**המטרה:** Wire `bridge/trade_commands.py::TradeCommandHandler` לbridge startup.
זה הpackage הפשוט ביותר — "just wire, don't change" (193 lines שכבר עובדות).

**Desktop יכתוב mega-prompt שכולל:**

**Scope:**
```
MODIFY: bridge/v9_startup.py (or equivalent startup file — CC reads first)
ADD: health metric trade_handler_alive
DO NOT TOUCH: bridge/trade_commands.py itself
DO NOT TOUCH: sc_study/, frontend/, backend/
```

**מה CC עושה:**
1. קרא `bridge/trade_commands.py` — הבן את `TradeCommandHandler.__init__` signature
2. מצא את קובץ bridge startup (רוץ `rg "def main\|if __name__" bridge/`)
3. הוסף 3 שורות בלבד:
   ```python
   from bridge.trade_commands import TradeCommandHandler
   trade_handler = TradeCommandHandler()
   trade_handler.start()  # or equivalent
   ```
4. הוסף `trade_handler_alive` ל-health metric שbridge מדווח

**Tests:** 2 integration tests:
- `test_trade_handler_started_on_bridge_init`
- `test_trade_handler_alive_metric_present_in_health`

**Spec authority:** `docs/decisions/D-093_SIERRA_ORDER_ROUTING.md` §Gap 4 · §Implementation P5-7

---

### Mega-Prompt 3 · P5-1 · DLL DEMO Order (CC + DLL)

**קובץ:** `docs/handoff/CC_MEGA_PROMPT_P5_1_DLL_DEMO_ORDER_2026-05-26.md`

**⚠️ חשוב: זה מחכה להחלטת מיכאל על D-093.Q1 + Q2 + proposed re-locks.**
Desktop יכתוב את ה-mega-prompt **עם placeholders** לשאלות הפתוחות.

**המטרה:** החלף `MES_AI_DataExport.cpp:813-816` TODO בקוד ACSIL אמיתי לDEMO.

**Desktop יכתוב mega-prompt שכולל:**

**Spec authority שCC חייב לקרוא ראשון:**
- `sc_study/MES_AI_DataExport.cpp` lines 791-855 (T2.2 · trade command polling)
- `docs/research/SIERRA_ORDER_ROUTING_RESEARCH_2026-05-24.md` §1.1 (BuyEntry/SellEntry · Attached Orders · OCO note) + §5 (gotchas)
- `docs/decisions/D-093_SIERRA_ORDER_ROUTING.md` §Implementation P5-1

**מה CC כותב ב-DLL (lines 813-816 replacement):**

```cpp
// === P5-1 DEMO ORDER PLACEMENT ===
// Only activates when payload["mode"] == "demo"
// Uses sc.BuyEntry/SellEntry + Attached Orders
// [PENDING D-093.Q1 lock: verify account_id = __PLACEHOLDER_DEMO_ACCOUNT__]
// [PENDING D-093 re-lock: confirm BuyEntry+AttachedOrders vs SubmitOCOOrder]

if (payload_mode == "demo") {
    s_SCNewOrder NewOrder;
    NewOrder.OrderQuantity = payload_contracts;
    
    // Direction
    if (payload_direction == "LONG") {
        NewOrder.OrderType = SCT_ORDERTYPE_MARKET;
        // Attached stop
        NewOrder.Stop1Offset = entry_price - payload_stop_price;
        // Attached target
        NewOrder.Target1Offset = payload_t1_price - entry_price;
        result_status = sc.BuyEntry(NewOrder) ? "SUBMITTED_DEMO" : "REJECTED_DEMO";
    } else {
        // SHORT mirror
        NewOrder.Stop1Offset = payload_stop_price - entry_price;
        NewOrder.Target1Offset = entry_price - payload_t1_price;
        result_status = sc.SellEntry(NewOrder) ? "SUBMITTED_DEMO" : "REJECTED_DEMO";
    }
    
    // Write order_id to result
    result_json["sc_order_id"] = std::to_string(NewOrder.InternalOrderID);
    result_json["fill_price"] = 0;  // async fill · update via P5-2
    result_json["mode"] = "demo";
} else {
    result_status = "ACK_SHADOW";  // unchanged for SHADOW
}
```

**Result JSON changes (P5-1 scope):**
```json
{
  "status": "SUBMITTED_DEMO",
  "sc_order_id": "12345",
  "fill_price": 0,
  "mode": "demo",
  "error_code": ""
}
```

**Forbidden (P5-1):**
- אין שינוי מחוץ לlines 813-855
- LIVE path נשאר stub (P5-3)
- `SHADOW` path = `ACK_SHADOW` בלבד (unchanged)

**Build path:**
```bash
./scripts/build_monolithic_cpp.sh --deploy
# → ~/SierraChart/ACS_Source/MES_AI_DataExport.cpp
# → Remote Build in Sierra → reload study
```

**Spec:** `docs/runbooks/SIERRA_DLL_OPS.md`

**Gotchas שDesktop חייב לכלול במגה-פרומפט (מ-Research §5):**
1. `sc.SendOrdersToTradeService` חייב להיות מסונכרן עם `Trade Simulation Mode On` בSierra — mismatch = silent rejection
2. Attached Orders: `Stop1Offset` ו-`Target1Offset` הם **offset** מה-entry, לא מחיר מוחלט
3. `InternalOrderID` זמין מיד · `OrderID` (exchange) מגיע אסינכרוני — P5-2 עוסק בזה
4. בDEMO mode: `sc.GlobalTradeSimulationIsOn()` חייב להחזיר true — DLL אמור לvalid זאת בstartup

---

### Mega-Prompt 4 · P5-6 · Heartbeat + Watchdog (CC)

**קובץ:** `docs/handoff/CC_MEGA_PROMPT_P5_6_HEARTBEAT_WATCHDOG_2026-05-26.md`

**המטרה:** DLL כותב `dll_heartbeat.json` כל bar. Backend watchdog מתריע אם stale > 30s.

**Desktop יכתוב mega-prompt שכולל:**

**DLL changes (T2.5 new block — אחרי T2.4):**
```cpp
// === T2.5 DLL HEARTBEAT ===
// Write every bar to dll_heartbeat.json
// Backend watchdog reads this file
{
    Json::Value hb;
    hb["last_seen_ts"] = (Json::Int64)std::time(nullptr);
    hb["bar_index"] = sc.CurrentIndex;
    hb["symbol"] = std::string(sc.Symbol.GetChars());
    
    std::string hb_path = export_dir + "/dll_heartbeat.json";
    // write with same pattern as trade_result.json
}
```

**Backend service (new):** `backend/v9/services/dll_watchdog.py`
```python
class DLLWatchdog:
    STALE_THRESHOLD_S = 30
    
    def check(self) -> dict:
        hb_path = Path(settings.SIERRA_EXPORT_DIR) / "dll_heartbeat.json"
        if not hb_path.exists():
            return {"status": "missing", "alert": True}
        hb = json.loads(hb_path.read_text())
        age = time.time() - hb["last_seen_ts"]
        return {
            "status": "ok" if age < self.STALE_THRESHOLD_S else "stale",
            "age_s": round(age, 1),
            "alert": age >= self.STALE_THRESHOLD_S,
        }
```

**Integration:** הוסף `dll_heartbeat` ל-`/api/v9/status` response (אחרי `bridge`).

**Tests:** 3 tests:
- `test_watchdog_ok_when_fresh_heartbeat`
- `test_watchdog_stale_when_over_30s`
- `test_watchdog_missing_when_no_file`

**Spec:** `docs/decisions/D-093_SIERRA_ORDER_ROUTING.md` §Implementation P5-6

---

## Checklist לDesktop לפני שמחזיר

לפני שDesktop מחזיר למיכאל, בדוק:

- [ ] כל mega-prompt כולל 7 שדות: Goal / Spec authority / Scope / Forbidden / Tests / Stop signals / Deliverable format
- [ ] כל mega-prompt מפנה לנתיב מלא של כל spec authority
- [ ] P5-1 כולל placeholder ברור לD-093.Q1 ו-Q2 (לא מניח account ID)
- [ ] P5-0 מפנה ל-research document ל-§3.3
- [ ] כל "Gotcha" מ-Research §5 מופיע ב-P5-1
- [ ] P5-7 אומר במפורש "DO NOT TOUCH bridge/trade_commands.py"
- [ ] Stop signal קיים ב-P5-1 אם account ID לא נמצא בקוד

---

## רשימה שמיכאל נותן לDesktop

מיכאל נותן לDesktop:
1. את הmeta-prompt הזה (`META_PROMPT_PIPELINE5_DLL_SIERRA_DEMO_2026-05-26.md`)
2. + הנחיה: "תקרא את כל המסמכים המצוינים ותייצר 4 mega-prompts לCC"

**Cursor תבדוק (G3):**
כל 4 mega-prompts בסדר הבא:
1. P5-0 audit prompt — הכי קריטי · G3 adversarial (forbidden violations, gotchas from research)
2. P5-7 bridge wire — הכי פשוט · G3 spot check
3. P5-6 heartbeat — G3 moderate
4. P5-1 DLL — G3 full (after D-093.Q1 + Q2 locked)

---

## תלויות ותזמון

| Package | מתי יכול להתחיל | תלוי ב |
|---|---|---|
| P5-0 audit | עכשיו (מקביל ל-SHADOW) | לא תלוי בשום דבר |
| P5-7 bridge | עכשיו | לא תלוי בשום דבר |
| P5-6 heartbeat | עכשיו | לא תלוי בשום דבר |
| P5-1 DLL | אחרי D-093.Q1 + Q2 locked | P5-0 audit + מיכאל נועל |
| P5-2 result mapping | אחרי P5-1 | DLL order ID |
| P5-3 backend LIVE | אחרי P5-1 | canonical gateway |
| P5-4 position reconciliation | אחרי P5-2 | DLL result states |
| P5-5 order modification | אחרי P5-2 | DLL order states |
| P5-8 E2E UAT | אחרי P5-1..P5-7 | הכל |

---

*End of META-PROMPT · Pipeline 5 · DLL + Sierra DEMO Prep*
