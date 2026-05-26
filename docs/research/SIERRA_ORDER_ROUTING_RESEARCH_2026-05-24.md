# Sierra Chart Order Routing for Pipeline 5 (MEMS26): Tactical + Strategic Research Report

**Scope:** Implementation guidance for D-093 — wiring `MES_AI_DataExport.cpp` ACSIL DLL → Python `TradeCommandHandler` file bridge → backend gateway, with MES futures (CME Group, $5 × S&P 500 Index, 0.25 index-point tick = $1.25/tick), SHADOW → DEMO → LIVE ladder.

**Headline:**
1. Replace the TODO at lines 813-815 with **`sc.BuyEntry(NewOrder)` / `sc.SellEntry(NewOrder)`** using directly-defined Attached Orders (`Target1Offset` / `Stop1Offset` on `s_SCNewOrder`). The function name `sc.SubmitOrder()` in your task description **does not exist** in ACSIL. `sc.SubmitOCOOrder()` exists but is reserved for the three native `SCT_ORDERTYPE_OCO_*` parent types — not for entry+stop+target brackets (Sierra calls those "Attached Orders").
2. **Keep the file-bridge** for P5-1 LIVE cutover; migrate to DTC only when (a) you need multi-instance Sierra or cross-machine Python, (b) you hit a real latency budget violation >5–10 ms end-to-end, or (c) per-bar order rates exceed file-system throughput.
3. **Canonical gateway = `backend/v9/services/trading_gateway/`** (the unwired one with W11 TradeManager + W14 RiskValidator). Deprecate the legacy `backend/v9/gateway/` *after* parity tests pass.

---

## TL;DR

- Bracket pattern: `sc.BuyEntry(NewOrder)` with `Target1Offset`/`Stop1Offset` set on `s_SCNewOrder` — Sierra's "Attached Orders" feature, server-managed OCO when Teton or another server-OCO-capable service is connected. Three Internal Order IDs come back on the same struct: `NewOrder.InternalOrderID` (parent), `NewOrder.Target1InternalOrderID`, `NewOrder.Stop1InternalOrderID`. Persist via `sc.GetPersistentInt64` for later `sc.ModifyOrder` / `sc.CancelOrder`.
- The file bridge is defensible because Sierra already provides robust server-side bracket atomicity; the bridge only carries intent and state. Atomic writes use `os.replace` (atomic on NTFS via `MoveFileEx`) + SHA256 + UUID `client_order_id`.
- The #1 silent-failure mode: `sc.SendOrdersToTradeService` must be consistent with global `Trade > Trade Simulation Mode On` — mismatched, all orders are rejected with only a Trade Service Log entry. The SHADOW/DEMO/LIVE ladder must toggle both in lockstep.

---

## Area 1 — ACSIL Trading Deep-Dive

### 1.1 Function inventory (verified vs Sierra docs)

`sc.SubmitOrder()` **does not exist**. Documented entry points:

| Function | Purpose |
|---|---|
| `int sc.BuyEntry(s_SCNewOrder&)` | Buy entry, chart's Symbol/Account; Attached Orders supported |
| `int sc.SellEntry(s_SCNewOrder&)` | Mirror |
| `int sc.BuyExit(s_SCNewOrder&)` / `sc.SellExit(...)` | Reduce/flatten |
| `int sc.BuyOrder(s_SCNewOrder&)` / `sc.SellOrder(...)` | Same as BuyEntry but supports different Symbol/TradeAccount; **unmanaged** (auto-trade variables don't apply) |
| `int sc.SubmitOCOOrder(s_SCNewOrder&)` | Native OCO parent types only: `SCT_ORDERTYPE_OCO_BUY_STOP_SELL_STOP`, `SCT_ORDERTYPE_OCO_BUY_STOP_LIMIT_SELL_STOP_LIMIT`, `SCT_ORDERTYPE_OCO_BUY_LIMIT_SELL_LIMIT` |
| `int sc.ModifyOrder(s_SCNewOrder&)` | Modify Price1/Price2/Quantity by InternalOrderID — **direct modify**, not cancel+resubmit |
| `int sc.CancelOrder(int InternalOrderID)` | Cancel one |
| `sc.CancelAllOrders()`, `sc.FlattenPosition()`, `sc.FlattenAndCancelAllOrders()` | Bulk |

`sc.ModifyOrder` is the canonical path for MODIFY_STOP / MODIFY_TARGET / ARM_BE — it preserves exchange queue priority and avoids the brief naked-position race of cancel+resubmit. Per Sierra docs: *"Only Price1 and/or Price2 of an order and the order quantity can be modified… The entire s_SCNewOrder does not need to be filled in, except for the InternalOrderID member."* For Attached Order children: *"If you wish to modify the prices of these Attached Orders, then you will need to set the Price1 member, and not the \*Offset/\*Price members."*

### 1.2 Required preconditions (the "free trading" recipe)

For unmanaged-style trading (recommended — your Python brain handles gating), set in `sc.SetDefaults`:

```cpp
sc.AllowMultipleEntriesInSameDirection = 1;
sc.MaximumPositionAllowed              = 10;
sc.SupportReversals                    = 0;
sc.AllowOppositeEntryWithOpposingPositionOrOrders = 0;
sc.SupportAttachedOrdersForTrading     = 1;
sc.CancelAllOrdersOnEntriesAndReversals = 0;
sc.AllowEntryWithWorkingOrders         = 1;
sc.CancelAllWorkingOrdersOnExit        = 0;
sc.AllowOnlyOneTradePerBar             = 0;   // CRITICAL: default is 1 → silent skip
sc.MaintainTradeStatisticsAndTradesData = 1;
// sc.SendOrdersToTradeService set OUTSIDE SetDefaults (see §1.3)
```

**`AllowOnlyOneTradePerBar = 1` is the default**: second BuyEntry within a bar returns `SCT_SKIPPED_ONLY_ONE_TRADE_PER_BAR` with no exception. Set to 0 explicitly.

### 1.3 Mode-ladder toggle map

| Mode | Global `Trade Simulation Mode On` | `sc.SendOrdersToTradeService` | Trade Account |
|---|---|---|---|
| SHADOW | ON | 0 | `Sim*` |
| DEMO (SC Sim) | ON | 0 | `Sim*` |
| DEMO (Trading Evaluator) | OFF | 1 | evaluator account |
| LIVE | OFF | 1 | live broker account |

**Inconsistency = silent rejection.** Per Sierra Chart Auto Trade Management docs (verbatim): *"If global Trade Simulation Mode is OFF (unchecked), then SendOrdersToTradeService must be set to Yes/TRUE for any order action (submitting, modifying, canceling order) to work, otherwise they will be ignored and there will be an error given when these order actions occur. There will also be a message added to the Trade > Trade Service Log."*

Bridge MUST read both states on startup and refuse to arm if mismatched. Read via `sc.GlobalTradeSimulationIsOn`; DLL sets `sc.SendOrdersToTradeService` itself.

### 1.4 OCO bracket atomicity

Sierra explicitly tells you not to roll your own: *"It definitely is not recommended for you to implement yourself in an ACSIL trading system, Target and Stop orders by sending both of them after the parent order fills, and handling the related OCO functionality. The reason for this, is there is a very high degree of sophistication involved to actually implement OCO functionality properly. And it is something that Sierra Chart internally will manage for you through the Attached Orders feature."*

**Atomicity model:**
- **Teton** (Sierra Chart's own routing): server-managed OCO and Bracket, always on. Per Sierra: *"Server Managed OCO (Order Cancels Order): Yes. Cannot be disabled. Always enabled regardless of how Global Settings >> General Trade Settings >> Use Server Side OCO Orders is set. Server Managed Bracket Orders: Yes."* Latency: *"Orders are routed direct to the exchange with high reliability and very low latency, in under 500 microseconds. In the case of CME Group order routing, Sierra Chart servers are located in Aurora Illinois colocated with the CME order matching computers."* (sierrachart.com Teton Futures Order Routing page).
- **CQG**: explicitly substandard. Per Sierra Chart Teton page (verbatim): *"the bracket order management is on the client side with a much higher delay from when the parent order fills, to when the Target and Stop orders are transmitted. This can be for example 300 ms and higher, rather than below 1 millisecond when managed on the server as they are with this service."* And: *"CQG users need to move to the Teton Order Routing service for properly managed OCO and Bracket orders."*

**Recommend Teton for LIVE** if your clearing firm supports it (Marex is named on Sierra's Teton page; AMP is confirmed via AMP Futures' own FAQ; Ironbeam is confirmed via ironbeam.com/sierra-chart-teton-futures-order-routing/; Optimus Futures is an introducing broker routing through Ironbeam, not a clearing firm itself). Apex Trader Funding evaluator accounts are documented to work with Teton via the supporting clearing firm.

**Partial fill on entry:** attached Target/Stop quantities are auto-reduced to match. Per Sierra docs (verbatim): *"if the calculated Trade Position Quantity from the order fills is out of sync with the reported Trade Service Position Quantity from the external trading service, then after about 8 seconds the order fill calculated Position Quantity will be synchronized to the Trade Service Position Quantity after there has been an unsolicited update of the Trade Service Position Quantity."* Set DRIFT_ALERT threshold ≥10s.

### 1.5 Order ID linkage

After `int Result = sc.BuyEntry(NewOrder);` with `NewOrder.Target1Offset` and `NewOrder.Stop1Offset` set:
- `Result > 0`: success; value = actual submitted quantity (may be < requested due to SC reduction rules).
- `Result < 0`: ignored — possible constants include `SCTRADING_ORDER_ERROR`, `SCT_SKIPPED_FULL_RECALC`, `SCT_SKIPPED_ONLY_ONE_TRADE_PER_BAR`, `SCT_SKIPPED_DOWNLOADING_HISTORICAL_DATA`.
- `NewOrder.InternalOrderID` = **parent's ID** (single-OCO-group case).
- `NewOrder.Target1InternalOrderID` = Target child's ID. *"This is set to the Internal Order ID of the Target 1, 2, 3, 4, 5 Attached Order, after you call one of the Order Action functions and the order has been accepted by the Auto-Trade Management System."*
- `NewOrder.Stop1InternalOrderID` = Stop child's ID. *"This is set to the Internal Order ID of the Stop 1, 2, 3, 4, 5 Attached Order after calling one of the Order Action functions."*

For `StopAllOffset` with multiple targets: each `Stop#InternalOrderID` is populated; `StopAllInternalOrderID` = link ID common to all stops.

**`ParentInternalOrderID` is parent↔child**; `LinkID` is sibling-link across split parents in multi-OCO-group submissions. Per Sierra docs (verbatim): *"If the order is an Attached Order, then this member is set to the Internal Order ID of the Parent. Otherwise it will be 0."* Newer members on `s_SCTradeOrder`: `TargetChildInternalOrderID`, `StopChildInternalOrderID`, `OCOSiblingInternalOrderID`. Helper: `sc.GetParentOrderIDFromAttachedOrderID()`.

### 1.6 Order status enum

Documented `SCT_OSC_*` constants observed across Sierra docs and support board: `SCT_OSC_OPEN`, `SCT_OSC_FILLED`, `SCT_OSC_CANCELED`, `SCT_OSC_UNSPECIFIED`, `SCT_OSC_ORDER_SENT`, plus partial/pending variants. Authoritative list lives in `sierrachart.h`.

Map for bridge `status`:

| Sierra status | Bridge status |
|---|---|
| OPEN, PENDING_OPEN, ORDER_SENT | WORKING |
| FILLED | FILLED |
| PARTIALLY_FILLED | PARTIAL |
| CANCELED, CANCEL_SENT | CANCELLED |
| Any `*REJECT` reason from `OrderUpdateReason` | REJECTED |

`sc.GetOrderByOrderID(id, OrderDetails)` returns `SCTRADING_ORDER_ERROR` once the order is cleared from memory (see §1.8).

### 1.7 Position query

`sc.GetTradePosition(s_SCPositionData&)` — chart's Symbol/Account. For different scope: `sc.GetTradePositionForSymbolAndAccount(pos, Symbol, Account)`. Key fields:
- `PositionQuantity` (signed)
- `AveragePrice`
- `PositionQuantityWithAllWorkingOrders` — use for risk
- `LastFillDateTime`
- `OpenProfitLoss`, `CashBalance` (where supported)

Position quantity is **fill-driven**, not service-driven: *"The Trade Position Quantity which is the Quantity displayed in Sierra Chart and given to automated trading systems is updated by fills/executions. It is not directly updated by Trade Position data updates from the external trading service."* (Sierra Trade Status Windows docs.)

### 1.8 Order ID lifecycle

Per Sierra Trade Status Windows docs: *"When the Status of an order changes from Open or Order Sent to Canceled, Filled or Error, it will still be listed on this tab, but it is not persistent and will be cleared when Sierra Chart is restarted."* And: *"In the case of non-simulated working/open orders, they are cleared 20 minutes after the order becomes non-working from a working/open status."*

**Snapshot terminal state to Python at status transition.** `sc.GetOrderFillEntry()` against the chart's Trades List survives even after `sc.GetOrderByOrderID` returns ERROR.

**Cross-instance uniqueness** (Sierra docs verbatim): *"In the case where you have more than one instance of Sierra Chart running and connected to the same external trading account, non-simulated orders will be listed in each instance and for the same order with the same Service Order ID, the Internal Order ID will be unique for each instance."* Always pair `internal_order_id` with `sc_session_id` + `client_order_id`.

### 1.9 Thread safety

Per `ACS_ArraysAndLooping.html` (verbatim): *"Study calculations, the calling of a study function, the updating of a chart, and the drawing of the chart, all occurs on a single thread and this is the main thread of Sierra Chart. Only one study function can run and be called at the same time."*

**All trading calls must originate from the study function (main thread).** Background threads in the DLL for file polling MUST NOT call `sc.BuyEntry` / `sc.ModifyOrder` / `sc.CancelOrder` directly. Use a lock-free queue or atomic flag drained from the study tick.

### 1.10 Trade Account targeting

Two paths:
1. **Chart's Trade Account** (Chart Settings > Trading), read via `sc.SelectedTradeAccount`. `sc.BuyEntry`/`sc.SellEntry` route here.
2. **Per-order override**: use `sc.BuyOrder`/`sc.SellOrder` with `NewOrder.TradeAccount = "AMP-LIVE-12345"`. Bypasses Sierra auto-trade management.

`sc.GetTradeAccountsList` enumerates available accounts. For SHADOW vs LIVE, configure the chart's Trade Account manually; bridge reads `sc.SelectedTradeAccount` into heartbeat.

### 1.11 ATM templates vs programmatic

Sierra's equivalent of an ATM template is the `.twconfig` (Trade Window configuration file). Specify via `sc.TradeWindowConfigFileName = "MES_Bracket.twconfig";`. **For Pipeline 5, do NOT use `.twconfig`** — version control hassle, reload race conditions. Define Attached Orders inline on `s_SCNewOrder` (the path Sierra explicitly documents as preferred for ACSIL — see the `scsf_TradingExampleWithAttachedOrdersDirectlyDefined` example in `/ACS_Source/TradingSystem.cpp`).

### 1.12 Idempotency

Sierra has **no client-side `ClientOrderID` dedup** in ACSIL. Two back-to-back identical `sc.BuyEntry` calls submit two orders. Implement idempotency in the bridge:
- Python-side map `client_order_id → last_submission_state`.
- DLL caches `LastClientOrderId` in `sc.GetPersistentSCString`; on match, returns cached IDs instead of re-submitting.
- Pass `client_order_id` through to `NewOrder.TextTag` (round-trips on `s_SCTradeOrder::TextTag`) for cross-system correlation including in post-trade Trade Activity Log lookups.

DTC has native `ClientOrderID` on `SUBMIT_NEW_SINGLE_ORDER` (echoed in `ORDER_UPDATE`). ACSIL does not — you must build it.

---

## Area 2 — File-Based Bridge Architecture

### 2.1 Atomic write — the only safe pattern

On Windows, `os.replace(temp, final)` (Python 3.3+) is the canonical atomic replacement, mapping to `MoveFileEx(MOVEFILE_REPLACE_EXISTING)`. Direct `open(final, 'w')` truncates immediately, exposing a zero-byte file to concurrent readers.

```python
def atomic_write_json(path: pathlib.Path, payload: dict) -> str:
    body = json.dumps(payload, sort_keys=True, separators=(',', ':'))
    digest = "sha256:" + hashlib.sha256(body.encode('utf-8')).hexdigest()
    payload_with_checksum = json.dumps({**payload, "checksum": digest}, sort_keys=True)
    tmp = path.with_suffix(path.suffix + f".tmp.{os.getpid()}.{uuid.uuid4().hex[:8]}")
    with open(tmp, 'w', encoding='utf-8', newline='\n') as f:
        f.write(payload_with_checksum)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)
    return digest
```

DLL-side reader must tolerate momentary file absence. Open with `FILE_SHARE_READ | FILE_SHARE_WRITE | FILE_SHARE_DELETE`; retry on `ERROR_SHARING_VIOLATION` up to N times with 1-2 ms backoff.

**Do NOT use `LockFileEx`** — creates contention with the DLL's main-thread study function which can't block. Atomic-rename + checksum is cooperative and lock-free.

### 2.2 Checksum + idempotency

- **SHA256 of canonical payload** (sorted keys, no whitespace) for integrity.
- **Sequence numbers** (`cmd_seq`): monotonic counter persisted to disk. Bridge rejects `cmd_seq <= last_processed`.
- **`client_order_id`** (UUIDv4): end-to-end correlation key. Goes into `NewOrder.TextTag` (text tag on the order, round-trips on `s_SCTradeOrder::TextTag`).

### 2.3 Polling intervals

- **DLL → command poll**: every study-function tick (typically 100-500 ms). No additional timer.
- **Python → result poll**: 50 ms initial, exponential backoff to 250 ms, deadline 5 s SHADOW / 2 s LIVE. The deadline IS the timeout; on timeout, surface `TIMEOUT_AWAITING_DLL` — do NOT auto-retry (order may have already been submitted).
- **Heartbeat**: DLL writes `dll_heartbeat.json` every 5 s. Python checks freshness on 1 Hz watchdog. **30 s stale threshold** — shorter false-positives during chart recalcs (10-15 s pauses are normal on heavy chartbooks); longer leaves crashes undetected mid-trade.

### 2.4 JSON schemas

```json
// trade_command.json
{
  "schema_version":"1.0",
  "cmd_id":"a6f3e9d0-…",
  "cmd_seq":128493,
  "client_order_id":"MES-20260524-0042",
  "mode":"LIVE",
  "action":"BRACKET",
  "symbol":"MESM26",
  "trade_account":"APEX-EVAL-12345",
  "side":"BUY","qty":1,
  "entry_type":"LIMIT","entry_price":5832.50,
  "stop_price":5828.50,"target_price":5840.50,
  "time_in_force":"DAY",
  "created_at":"2026-05-24T13:45:16.969Z",
  "deadline_ms":2000,
  "ref_order_id":null,
  "checksum":"sha256:…"
}
```

```json
// trade_result.json
{
  "schema_version":"1.0",
  "cmd_id":"a6f3e9d0-…",
  "client_order_id":"MES-20260524-0042",
  "status":"WORKING",
  "sc_session_id":"SC-2026052408301",
  "sc_parent_id":51234,"sc_target_id":51235,"sc_stop_id":51236,
  "fill_price":null,"fill_qty":0,"remaining_qty":1,
  "error_code":null,"error_message":null,"rejection_reason":null,
  "dll_received_at":"2026-05-24T13:45:16.971Z",
  "dll_completed_at":"2026-05-24T13:45:17.012Z",
  "latency_ms":41,
  "checksum":"sha256:…"
}
```

```json
// position_state.json
{
  "schema_version":"1.0",
  "ts":"2026-05-24T13:46:00.000Z",
  "sc_session_id":"SC-2026052408301",
  "account":"APEX-EVAL-12345","symbol":"MESM26",
  "position_qty":1,"position_qty_with_working":1,
  "avg_price":5832.50,
  "open_pnl":12.50,"realized_pnl_today":87.50,
  "last_fill_ts":"2026-05-24T13:45:18.103Z",
  "working_orders":[
    {"id":51235,"type":"LIMIT","side":"SELL","qty":1,"price":5840.50,"parent_id":51234,"role":"TARGET"},
    {"id":51236,"type":"STOP","side":"SELL","qty":1,"price":5828.50,"parent_id":51234,"role":"STOP"}
  ]
}
```

```json
// dll_heartbeat.json
{
  "schema_version":"1.0",
  "last_seen_ts":"2026-05-24T13:46:05.000Z",
  "dll_version":"MES_AI_DataExport-1.4.2",
  "sc_version":2913,
  "chart_id":14,"chart_book":"MES_AI.cht",
  "symbol":"MESM26","trade_account":"APEX-EVAL-12345",
  "global_sim_mode":false,"send_to_service":true,
  "trading_locked":false,
  "auto_trade_enabled_global":true,"auto_trade_enabled_chart":true,
  "connection_status":"CONNECTED",
  "study_tick_count":3812904,
  "last_cmd_seq_processed":128493
}
```

### 2.5 Concurrency hazards

- **DLL mid-poll while Python writes new command**: avoided by atomic rename — Python's write becomes visible only at the rename instant.
- **Python reading partial DLL result**: same protection — DLL must atomically rename too. In C++, write to `.tmp` then `MoveFileExW` with `MOVEFILE_REPLACE_EXISTING`.
- **File sharing**: open with `FILE_SHARE_READ | FILE_SHARE_DELETE` on C++ side; avoid `O_EXCL` semantics.
- **Polling cost at low Chart Update Interval (10-25 ms)**: stat-only sentinel file (`cmd_pending.flag`) touched by Python on write; DLL reads JSON only when sentinel mtime advances.

---

## Area 3 — Strategic Comparison

### 3.1 Matrix

| Dimension | A. File bridge | B. DTC over TCP/WS | C. ACSIL named pipes | D. Out-of-SC direct |
|---|---|---|---|---|
| Latency p50/p95 | ~5-50 ms / 50-200 ms (Chart Update Interval bound) | <1 / ~5 ms intra-machine; ~10 / 50 ms over LAN | <1 / ~3 ms | Broker-dependent, ~5-20 ms |
| Impl cost | Low (existing 193-line Python handler) | Medium-high (encoder, framing, reconnect) | Medium (Win32 pipes + Python client) | High (broker SDK / FIX) |
| Sierra crash mid-trade | Orders persist broker-side; Python sees stale heartbeat → DRIFT_ALERT | DTC server dies; broker holds orders; client must reconnect | Pipe broken; same as DTC | Unaffected |
| Python crash | Command file unprocessed; safe | Connection drops | Pipe broken | Same as Python crash |
| Idempotency | Bridge implements | Native `ClientOrderID` field | Bridge implements | Broker-dep |
| Observability | Files = inspectable artifacts for postmortems | Wire capture (tcpdump/Wireshark) needed | Ephemeral | Broker logs only |
| Vendor coupling | Tight to Sierra | DTC open spec; portable | Tight to Sierra | None — but loses charting/data |
| Multi-symbol | Schema scales | Native | Schema scales | Native |
| Multi-instance Sierra | Per-instance dirs | Per-instance ports | Per-instance names | N/A |
| Test surface | File fixtures trivial | Mock DTC server needed | Mock pipe needed | Broker sim |

### 3.2 Recommendation

**Stay on file bridge through P5-1 (LIVE).** Reasons:

1. Sierra already provides server-side OCO via Teton (sub-millisecond bracket-leg transmission per Sierra's documented figure of "below 1 millisecond when managed on the server"). The bridge carries intent and reports state — it does not implement bracket atomicity. File granularity matches mode-ladder cadence.
2. `TradeCommandHandler` is *already written* (193 lines) and tested in SHADOW. DTC requires rewriting for stateful socket I/O, framing, encoding, heartbeat, reconnect — high-risk on the P5-1 timeline.
3. File artifacts are gold for postmortems. After a bad LIVE trade you have `trade_command.json` and `trade_result.json` on disk with timestamps and checksums. DTC traffic is ephemeral unless you build capture infra.
4. For swing/intraday MES with seconds-to-minutes holds, even p95 = 200 ms is irrelevant.

**Migrate to DTC when ALL of:**
- >1 Sierra Chart instance per box, or Python on a different machine.
- Strategy holds positions <10 s and intra-bar reaction matters.
- File-bridge throughput ceiling reached (~50 cmds/s practical).
- 2-engineer-week budget available for a robust DTC client. JSON Compact via WebSocket is the easy path; per Sierra Chart DTC Protocol Server documentation (verbatim): *"Effective with version 1798 or higher of Sierra Chart, a websocket connection is also now supported. When a websocket connection is used, the encoding will always be JSON Compact."*

**Never recommend named pipes (C):** more code than DTC for the same vendor coupling, less observability than files, no advantage.

**Option D** (drop Sierra entirely) only if you're willing to lose Sierra's charting and study integration that the DLL leverages.

### 3.3 D-093.Q1 — canonical gateway

**Canonical = `backend/v9/services/trading_gateway/`.** It has W11 TradeManager + W14 RiskValidator pre-integrated — exactly the risk plumbing LIVE requires. Reconcile drift by: (a) run both in SHADOW for one week, (b) assert byte-equal `trade_command.json` outputs given identical synthetic signals, (c) cut over and freeze legacy as read-only.

---

## Area 4 — Risk Model + Safety Patterns

### 4.1 Kill switches (layered)

| Layer | Mechanism | Purpose |
|---|---|---|
| L0 process | `BRIDGE_LIVE_ENABLED=1` env var | Default-off boot guard |
| L1 file | `KILL_TRADING.flag` presence | **Primary** — operator `touch` in <1s; both Python and DLL check |
| L2 Sierra | `Trade > Trading Locked` / `Auto Trading Disabled` | Belt-and-suspenders; persists across SC restart |
| L3 broker | Sierra Global P/L Mgmt + clearing-firm risk | Auto-flatten on breach |

### 4.2 Position drift detection

Compare every N seconds (N=5 LIVE, 30 SHADOW): DLL `position_qty` vs Python ledger `expected_qty` vs broker (via `s_SCPositionData` external service reflection).

| Class | Detection | Action |
|---|---|---|
| Transient (Sierra fill→service lag ≤8s) | <10s diff | Log only |
| Real | Persistent >10s | Drop `KILL_TRADING.flag`, page operator, refuse new orders |
| Sign-flip | Any sign mismatch | Immediate `sc.FlattenPosition()` + `DRIFT_CRITICAL` |

### 4.3 Heartbeat watchdog

- **5 s emit, 30 s stale, 120 s critical.**
- Action ladder:
  - 30 s stale, flat → log WARN.
  - 30 s stale, open position → `KILL_TRADING.flag`, page operator. Do NOT attempt programmatic recovery.
  - 120 s stale, open position → manual broker-desk intervention.
- Distinguish causes:
  - File absent → chart unloaded.
  - File mtime stale → study not running.
  - File advancing but `connection_status: DISCONNECTED` → SC running, no feed; do not submit.

### 4.4 Rejection handling

Two channels: synchronous return value from entry/exit functions; asynchronous via `OrderStatusCode` + `OrderUpdateReason` on subsequent `sc.GetOrderByOrderID` polls.

| Class | Retry? | Why |
|---|---|---|
| SCT_SKIPPED_FULL_RECALC | Yes, next tick | Transient, study init |
| SCT_SKIPPED_DOWNLOADING_HISTORICAL_DATA | Yes after load | Transient |
| SCT_SKIPPED_ONLY_ONE_TRADE_PER_BAR | No — surface | Config bug |
| SCTRADING_ORDER_ERROR (generic) | No — read Trade Service Log | Could be margin, price, account |
| External REJECT (margin/price/limit) | No — surface, halt | Capital or logic |
| External REJECT (market_closed) | Schedule retry at open | Operational |
| Timeout (DLL no response) | **No — state unknown, manual reconcile** | Order may exist |

### 4.5 OCO bracket failure modes

| Failure | Cause | Mitigation |
|---|---|---|
| Entry fills, stop fails | Trade service rejects child (rare with Teton server-side OCO; possible with CQG client-side, where Sierra documents ~300 ms+ bracket-leg delay vs <1 ms server-side) | On filled-entry, query stop/target IDs within 2 s; if not WORKING → `NAKED_POSITION` + flatten |
| Stop fires, target lingers | Should not happen with proper OCO | Trust Sierra attached-order mgmt; if observed, file bug |
| Partial fill on entry | Standard | Auto-reduce + 8 s resync window |
| Sierra crash before broker ack | Order may exist without local record | On restart, query open orders via `sc.GetOrderByIndex` loop matched on `TextTag` (= your `client_order_id`); reconcile |

---

## Area 5 — Concrete Code Patterns

### 5.1 ACSIL OCO bracket submission (the lines 813-815 replacement)

```cpp
if (sc.SetDefaults) {
    sc.GraphName = "MES_AI_DataExport";
    sc.AutoLoop = 0; sc.UpdateAlways = 1;
    sc.MaintainTradeStatisticsAndTradesData = 1;
    sc.SupportAttachedOrdersForTrading = 1;
    sc.AllowOnlyOneTradePerBar = 0;
    sc.AllowMultipleEntriesInSameDirection = 1;
    sc.SupportReversals = 0;
    sc.MaximumPositionAllowed = 10;
    sc.CancelAllOrdersOnEntriesAndReversals = 0;
    sc.CancelAllWorkingOrdersOnExit = 0;
    sc.AllowEntryWithWorkingOrders = 1;
    sc.AllowOppositeEntryWithOpposingPositionOrOrders = 0;
    return;
}
// MUST be outside SetDefaults
sc.SendOrdersToTradeService = Input_SendToService.GetYesNo();

if (sc.IsFullRecalculation || sc.DownloadingHistoricalData) return;

int64_t& ParentID = sc.GetPersistentInt64(1);
int64_t& TargetID = sc.GetPersistentInt64(2);
int64_t& StopID   = sc.GetPersistentInt64(3);
SCString& LastClientOrderId = sc.GetPersistentSCString(10);

// --- BRACKET handler ---
if (cmd_client_order_id == LastClientOrderId) {
    WriteResultJsonAck(cmd_id, /*idempotent=*/true, ParentID, TargetID, StopID);
    return;
}

s_SCNewOrder NewOrder;
NewOrder.OrderQuantity = cmd_qty;
NewOrder.OrderType     = (cmd_entry_type == "MARKET") ? SCT_ORDERTYPE_MARKET
                       : (cmd_entry_type == "LIMIT")  ? SCT_ORDERTYPE_LIMIT
                       : SCT_ORDERTYPE_STOP;
NewOrder.Price1        = cmd_entry_price;
NewOrder.TimeInForce   = SCT_TIF_DAY;
NewOrder.Target1Price  = cmd_target_price;
NewOrder.Stop1Price    = cmd_stop_price;
NewOrder.AttachedOrderTarget1Type = SCT_ORDERTYPE_LIMIT;
NewOrder.AttachedOrderStop1Type   = SCT_ORDERTYPE_STOP;
NewOrder.OCOGroup1Quantity = cmd_qty;
NewOrder.TextTag = cmd_client_order_id.GetChars();

int Result = (cmd_side == "BUY") ? sc.BuyEntry(NewOrder) : sc.SellEntry(NewOrder);

if (Result > 0) {
    ParentID = NewOrder.InternalOrderID;
    TargetID = NewOrder.Target1InternalOrderID;
    StopID   = NewOrder.Stop1InternalOrderID;
    LastClientOrderId = cmd_client_order_id;
    WriteResultJsonAck(cmd_id, false, ParentID, TargetID, StopID);
} else {
    WriteResultJsonReject(cmd_id, SCString().Format("ACSIL submit failed: code=%d", Result));
}
```

### 5.2 ACSIL position query, exported to JSON

```cpp
void ExportPosition(SCStudyInterfaceRef sc) {
    s_SCPositionData pos; sc.GetTradePosition(pos);
    SCString json;
    json.Format(
      "{\"schema_version\":\"1.0\",\"ts\":\"%s\",\"sc_session_id\":\"%s\","
      "\"account\":\"%s\",\"symbol\":\"%s\","
      "\"position_qty\":%d,\"position_qty_with_working\":%d,"
      "\"avg_price\":%.5f,\"open_pnl\":%.2f}",
      FormatDateTimeISO8601(sc.CurrentSystemDateTime).GetChars(),
      g_SessionId.GetChars(), sc.SelectedTradeAccount, sc.Symbol.GetChars(),
      (int)pos.PositionQuantity,
      (int)pos.PositionQuantityWithAllWorkingOrders,
      pos.AveragePrice, pos.OpenProfitLoss);
    AtomicWriteFile(g_BridgeDir + "\\position_state.json", json);
}
```

### 5.3 ACSIL stop modification (direct, no cancel+resubmit)

```cpp
int64_t& StopID = sc.GetPersistentInt64(3);
if (StopID == 0) return;
s_SCTradeOrder Existing;
if (sc.GetOrderByOrderID(StopID, Existing) == SCTRADING_ORDER_ERROR) {
    WriteResultJsonReject(cmd_id, "Stop no longer retrievable");
    return;
}
if (Existing.OrderStatusCode != SCT_OSC_OPEN) {
    WriteResultJsonReject(cmd_id, SCString().Format("Stop not open: status=%d", Existing.OrderStatusCode));
    return;
}
s_SCNewOrder Mod;
Mod.InternalOrderID = StopID;
Mod.Price1 = new_stop_price;  // ABSOLUTE price — attached child uses Price1
int mr = sc.ModifyOrder(Mod);
if (mr > 0) WriteResultJsonAck(cmd_id, StopID);
else        WriteResultJsonReject(cmd_id, SCString().Format("ModifyOrder failed: %d", mr));
```

### 5.4 Python command-write + result-poll loop

```python
def submit_command(cmd: dict, deadline_ms: int = 2000) -> dict:
    cmd_id = cmd["cmd_id"]
    cmd_path = BRIDGE_DIR / "trade_command.json"
    result_path = BRIDGE_DIR / f"trade_result.{cmd_id}.json"
    sentinel = BRIDGE_DIR / "cmd_pending.flag"
    atomic_write_json(cmd_path, cmd)
    sentinel.touch()
    deadline = time.monotonic() + (deadline_ms / 1000.0)
    interval = 0.050
    while time.monotonic() < deadline:
        if result_path.exists():
            payload = json.loads(result_path.read_text("utf-8"))
            if payload.get("cmd_id") == cmd_id:
                claimed = payload.pop("checksum", None)
                expected = "sha256:" + hashlib.sha256(
                    json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
                ).hexdigest()
                if claimed != expected:
                    raise BridgeIntegrityError(f"Checksum mismatch for {cmd_id}")
                shutil.move(str(result_path), str(ARCHIVE_DIR / result_path.name))
                return payload
        time.sleep(interval); interval = min(interval * 1.5, 0.250)
    return {"cmd_id": cmd_id, "status": "TIMEOUT",
            "error_code": "TIMEOUT_AWAITING_DLL",
            "error_message": f"No result from DLL within {deadline_ms}ms"}
```

### 5.5 Pytest fixture (no live DLL)

```python
@pytest.fixture
def fake_dll(tmp_path, monkeypatch):
    monkeypatch.setattr("bridge.trade_commands.BRIDGE_DIR", tmp_path)
    results: dict[str, dict] = {}
    def respond(cmd_id, result): results[cmd_id] = result
    stop = threading.Event()
    def runner():
        seen = set()
        while not stop.is_set():
            p = tmp_path / "trade_command.json"
            if p.exists():
                cmd = json.loads(p.read_text())
                if cmd["cmd_id"] not in seen and cmd["cmd_id"] in results:
                    seen.add(cmd["cmd_id"])
                    r = results[cmd["cmd_id"]]; r.setdefault("cmd_id", cmd["cmd_id"])
                    atomic_write_json(tmp_path / f"trade_result.{cmd['cmd_id']}.json", r)
            time.sleep(0.01)
    t = threading.Thread(target=runner, daemon=True); t.start()
    yield respond; stop.set(); t.join(1.0)

def test_bracket_filled(fake_dll):
    cmd = make_test_command("BRACKET", side="BUY", qty=1)
    fake_dll(cmd["cmd_id"], {"status":"FILLED","sc_parent_id":1001,
        "sc_target_id":1002,"sc_stop_id":1003,"fill_price":5832.5,"fill_qty":1})
    result = submit_command(cmd, deadline_ms=500)
    assert result["status"] == "FILLED"
    assert result["sc_stop_id"] == 1003
```

---

## Area 6 — Gotchas Checklist (run during P5-1)

### Critical (silent-break LIVE)

- [ ] **`sc.SendOrdersToTradeService` vs global `Trade Simulation Mode On` MUST match.** Mismatched → silent rejection with only a Trade Service Log entry. Bridge MUST validate at boot.
- [ ] **`sc.AllowOnlyOneTradePerBar` defaults to 1.** First entry succeeds, second returns `SCT_SKIPPED_ONLY_ONE_TRADE_PER_BAR`. Set to 0.
- [ ] **`sc.SubmitOrder()` does not exist.** Use `sc.BuyEntry`/`sc.SellEntry`/`sc.BuyOrder`/`sc.SellOrder`/`sc.SubmitOCOOrder`.
- [ ] **Internal Order IDs do not survive Sierra restart.** Pair with session UUID; reconcile via `TextTag`.
- [ ] **20-minute auto-clear** of non-working orders. Snapshot terminal state at status transition.
- [ ] **`Trade > Disable Auto Trading on Startup`** blocks ALL ACSIL submissions if checked. Include `auto_trade_enabled_global` in heartbeat.
- [ ] **`Trade > Trading Locked`** blocks all order submission including DTC. Include in heartbeat.

### Important (confusing during testing)

- [ ] **`sc.IsFullRecalculation`** is true during chartbook open/reload/study add/modify/replay start — all trading returns `SCT_SKIPPED_FULL_RECALC`. Guard: `if (sc.IsFullRecalculation || sc.DownloadingHistoricalData) return;`.
- [ ] **Replays skip trading on historical bars.** Only the live tail triggers orders.
- [ ] **Trade Account name is case-sensitive** against broker-listed accounts.
- [ ] **CQG has no server-side OCO/Bracket** — Sierra explicitly documents a ~300 ms+ client-side leg-transmission delay versus <1 ms server-side. Move to Teton.
- [ ] **All ACSIL trading calls run on Sierra's main thread.** Background threads in DLL must NOT call them.
- [ ] **For Attached Order modification, use `Price1`** — not `Target1Price`/`Stop1Price` (which only apply at submission).
- [ ] **Prices auto-round to `sc.TickSize`.** MES tick is 0.25 index points ($1.25 per tick) per CME Group's product spec; 5832.45 will be rounded to 5832.50. Pre-round in bridge to avoid surprise.
- [ ] **8-second position resync** between SC and broker. DRIFT_ALERT threshold ≥10 s.
- [ ] **`SCT_TIF_DAY` for futures bracket legs**, not `SCT_TIF_GTC` (GTC persists across sessions; some clearing firms reject GTC stops).

### Operational

- [ ] **Chart Trade Mode** enabled for chart-side operator visibility.
- [ ] **`sc.TradeAndCurrentQuoteSymbol`** must point to the symbol you're trading if chart's symbol differs.
- [ ] **`Number of Stored Time and Sales Records` ≥ 10000** for high-frequency strategies; default may drop fills.
- [ ] **`Chart Update Interval`** controls study call frequency. 25-50 ms for low latency, weigh against CPU.
- [ ] **DTC Server port conflicts**: only one SC instance per machine should have it enabled (or distinct ports).
- [ ] **DLL rebuild resets globals** — persist via `sc.PersistVars` or file.

### Uncertainty flags

- [ ] Exact `SCT_OSC_*` list varies by Sierra version. Authoritative source = `sierrachart.h` shipping with your version (current: 2913).
- [ ] `s_SCTradeOrder::TextTag` round-trip through Teton — documented to work but verify in DEMO before LIVE.
- [ ] `OCOSiblingInternalOrderID` population for parent↔child Attached Orders — documented for OCO siblings broadly; test for the Attached Order child case specifically.

---

## Recommendations (decision-ready)

1. **D-093.Q1:** Canonical gateway = `backend/v9/services/trading_gateway/`. Freeze legacy after one week SHADOW parity.
2. **Lines 813-815 wiring:** §5.1 pattern. Function is `sc.BuyEntry(NewOrder)` / `sc.SellEntry(NewOrder)` — NOT `sc.SubmitOrder`. Reserve `sc.SubmitOCOOrder` for native OCO main types.
3. **Architecture:** Keep file bridge through P5-1. Defer DTC until concrete pain point (multi-instance Sierra, cross-machine Python, sub-10-second holds, or file-throughput ceiling).
4. **Modifications:** Direct `sc.ModifyOrder`. Cancel+resubmit only as fallback after a modify rejection.
5. **Mode gate:** Boot verifies `(global_sim_mode XOR send_to_service) == (mode == LIVE)` and refuses to arm otherwise.
6. **Heartbeat:** 5 s emit, 30 s stale, 120 s critical, with graduated action.
7. **Correlation:** `client_order_id` UUID end-to-end, written to `NewOrder.TextTag`.
8. **Risk caps before LIVE:** `sc.MaximumPositionAllowed`; Sierra Global P/L Mgmt daily loss limit; broker-side position limits at the clearing firm; L1 file kill switch wired to Python's DRIFT/REJECTION handlers.

---

## Caveats

- **Specific Sierra version assumed: 2913** (current pre-release at writing). Field names and enums are stable across recent versions but `sierrachart.h` is the source of truth — diff against your installed copy.
- **Teton clearing-firm support varies.** Sierra's Teton page names Marex; AMP confirmed via AMP Futures' own FAQ; Ironbeam confirmed via their Teton landing page. Optimus Futures is an introducing broker (not a clearing firm) routing through Ironbeam. Verify your exact arrangement with your firm directly.
- **`sc.SubmitOCOOrder` semantics** for the three native OCO parent types are NOT the same as Attached Orders. For bracket entry+target+stop, use Attached Orders (Target#Offset/Stop#Offset on a regular Buy/Sell entry). Use `sc.SubmitOCOOrder` only if you actually want a "either Buy Stop OR Sell Stop, whichever triggers first" semantic.
- **Latency figures in Area 3** are order-of-magnitude estimates from documentation and community reports; Sierra's documented Teton figure of <500 microseconds is the colo-direct number, not end-to-end from your DLL. Measure on your hardware before treating as commitments.
- **The 8-second position resync window** is documented but exact behavior may differ across CQG vs Teton vs Rithmic; verify in DEMO with deliberate partial fills.
- **The `OrderStatusCode` enum** has documented values for the common transitions but not every `SCT_OSC_*` constant is in the public docs; treat unrecognized codes as "unknown" rather than crashing.
- **No benchmarks of the named-pipe option** were performed; Option C is dismissed on architectural grounds.
- **`SUBMIT_NEW_SINGLE_ORDER`** is the exact DTC message name (the draft earlier referenced the conceptual "SUBMIT_NEW_ORDER" — verify the precise message constant in the DTC docs before implementing).