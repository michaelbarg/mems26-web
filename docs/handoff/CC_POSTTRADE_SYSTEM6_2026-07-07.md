# CC unified work order — post-trade management + System 6 supervision + ground-truth gate (2026-07-07)

Michael approved (07-07): build P1 safety-net + P2 System 6 wiring as ONE supervisor (merge
orphan/reconcile INTO System 6 — do NOT build 3 parallel implementations). **Supervise strictly.**
**Ground-truth tests (real SIM/live data, raw paste) MUST pass before RTH 16:30 IL — else no
real money today.** Rule 5 (paste command+output) + a NOT-DONE section on every item. Snapshot
before any .env/DLL change. Advisory-first: `SYSTEM6_AUTOCORRECT=0` until it proves out.

Audit-before-build (CLAUDE.md): the executor plumbing ALREADY EXISTS — reuse it, don't rebuild.
- MODIFY path: `manager._emit_modify_stop` (manager.py:114) / `_emit_modify_target` (:127) →
  `sierra_command.write_modify_stop/target` (:76/:94) → DLL `sc.ModifyOrder` (cpp:1131/1155). Works live.
- CANCEL/flatten: `sierra_command` op CANCEL (:138) → DLL FlattenAndCancelAllOrders (CC: CANCEL_OK).
- System 6 module: `diagnose_trade` (system6_supervisor.py:69, 9 checks) + `scan_active_trade`
  (:173, applies AUTO corrections when `SYSTEM6_AUTOCORRECT=1` + executor given) — **ZERO callers
  today** (only the manual endpoint). Per-bar loop: `main.py` bar_router `subscribe("5min", …)` + trade_manager.

---
## P0 — verify the SIM proof is REAL (ground-truth, before anything else)
CC claims SIM fill @7578.50. Paste, don't assert:
1. `ls -la ~/SierraChart*/ACS_Source/MES_AI_DataExport_64.dll` — mtime MUST be after 07-07 06:42
   (proves the SendOrders fix 9d314d0 is in the binary). If not → rebuild first.
2. The Sierra Message Log line(s): `ORDER_SUBMITTED` + the ENTRY fill @price. Paste raw.
3. Re-fire a **2-contract** SIM order → both fill. Paste. (Michael point 2 — "2 successful contracts.")

## P1 — SAFETY NET (hard gate before real money) — fold into ONE supervisor
### 1. Auto-flatten 22:15 IL / EOD  (CC gap 2 · OPEN_ITEMS A4)
**Cowork verified (audit-before-build):** `EOD_RISK_WINDOW_V1` (gateway:176) is an ENTRY-CUTOFF
only (`blocked_by=eod_entry_cutoff`, no position close) — so gap 2 is real. BUT a flatten
EVALUATOR already exists: `B2EodCheck` (woodies/stages/b2_eod_check.py) returns `CLOSE_ALL` at
≥15:59 ET, and B7 "EOD flatten" is a gateway-owned stage. **Do NOT build a fresh flatten** — check
whether anything CONSUMES `B2Output.action==CLOSE_ALL` to actually write a CANCEL; if not, wire
that output → `sierra_command` CANCEL (:136) + mark TM trade CLOSED(FLATTEN_EOD). **Reconcile the
time:** B2 uses 15:59 ET; Michael asked 22:15 IL (= 15:15 ET summer) — confirm which Michael wants
and use ONE constant with a TZ comment (Rule 4). **No new scheduled task** — drive off the existing
bar/poll clock check.
- **Ground-truth test:** open a SIM position, force the clock past the flatten time (or call the
  flatten path directly) → Sierra flattens + TM CLOSED(FLATTEN_EOD). Paste the command + fill + DB row.

### 2. Orphan / fill-drop protection  (CC gaps 1+5) → make it a System-6 check, not standalone
**Cowork verified:** the I-58 fallback (fill_poller.py:245) ALREADY filters demo/live and adopts
the most-recent active demo/live trade — it only drops (`fill dropped` WARNING, :258) when NO
active demo/live trade exists (e.g. restart with zero live trades). So this is HARDEN-the-edge +
raise the drop from WARNING→CRITICAL, NOT a demo-only bug. Surface the drop as System 6's
**orphan/reconcile invariant** (one place) + attempt to rebuild the TM trade from the fill.
- **Ground-truth test:** with a SIM position open, restart the backend (`launchctl kickstart -k
  gui/$UID/com.mems26.backend`) → the fill is re-adopted (not dropped) OR a CRITICAL alert fires.
  Paste the log.

### 3. Reconcile for LIVE  (CC gap 3 · OPEN_ITEMS A2 / item-20) → System-6 check
The reconcile module checks demo/shadow only. Add `mode=live` + run it from the per-bar/poll loop
when a `live_slot` is active — detect orphan / naked-stop / slot↔DB mismatch. This IS System 6's
reconcile invariant — wire it there, don't duplicate.
- **Ground-truth test:** with a live/SIM slot active, run one reconcile pass → paste the 3-way
  (slot ↔ DB ↔ Sierra) comparison output showing MATCH.

## P2 — SYSTEM 6 WIRING (Michael's ask: "manage the trade after execution, make changes per System 6")
### 4. Wire `scan_active_trade` into the per-bar management loop  (D2)
**Cowork verified the exact interface (ready to receive):**
`scan_active_trade(*, trade, atr, t1_hit=False, reconcile_verdict=None, reconcile_mismatch=False,
expected_contracts=None, now_ct_min=None, executor=None)` (system6_supervisor.py:173). `executor:
Callable[[Dict], bool]` applies ONE correction dict (MODIFY_STOP / DROP_TARGET) — System 6 never
writes to Sierra itself. It ALREADY handles advisory: when `SYSTEM6_AUTOCORRECT=0` it logs
`"…recommended (SYSTEM6_AUTOCORRECT off): [codes]"` (:210) and applies nothing.
Wire: each 5-min bar, on the active demo/live trade, build the `trade` dict + `atr` + pass the
reconcile verdict (from item 3) + an executor lambda that maps `{MODIFY_STOP,price}` →
`write_modify_stop(trade_id, order_id, new_stop)` and `{DROP_TARGET,…}` → `write_modify_target`
(the plumbing at manager.py:114/:127). Advisory-first — zero-risk, runs today.
- **Ground-truth test:** on the SIM trade, paste one bar's System 6 diagnosis log (the 9 checks +
  any recommended correction, "SYSTEM6_AUTOCORRECT off"). Confirms it runs every bar on the real trade.

### 5. Enable AUTOCORRECT — only after advisory proves out  (D3)
Not today by default. After advisory logs show the diagnoses are correct on real trades → Michael
sign-off → `SYSTEM6_AUTOCORRECT=1`. AUTO applies only non-CRITICAL fixes (BE move, drop wrong-side
target); CRITICAL stays ALERT-only.

### 6. Timer-button  (D1 · task #20) — after the above
Michael's design: on a System 6 recommendation, press to apply / auto-decide after 2 min. Depends
on 4+5. Build last.

## P3 — the rest of CC's list
7. **A7 fire_setup** (gap 4 · A6): verify a ZLR/GHOST ROUTES on the next RTH auto-fire (no
   `failed_stages=['A7']`); if it still fails, log `best.stop` + `_effective_stop` at the fail point.
8. **contracts=2 with Sim Mode OFF** (gap 6): **Cowork verified** it's wired at BOTH the sizing
   source (sizing.py FIXED_CONTRACTS_2, precedence over _3) and the command choke
   (sierra_command:160 reads `setup["contracts"]`) per 6ec3209 → VERIFY-not-build. Ground-truth:
   paste the live trade_command.json showing `contracts:2`.
9. **Frontend :3000** (gap 7): raise it so Michael sees dashboard + journal + trade panel.

---
## GROUND-TRUTH GATE before 16:30 (Michael: "בדיקות אמת לפני זמן מסחר")
Real SIM/live data, raw-pasted — NO synthetic unit tests count for this gate:
- [ ] P0: DLL binary mtime > 06:42 + SIM fill line + 2-contract fill.
- [ ] P1.1: auto-flatten fires + Sierra flattens + TM CLOSED.
- [ ] P1.2: backend-restart mid-trade → fill re-adopted or CRITICAL alert.
- [ ] P1.3: reconcile-live pass shows slot↔DB↔Sierra MATCH.
- [ ] P2.4: System 6 advisory logs the 9 checks on the real SIM trade each bar.
- [ ] P3.8: live command shows contracts=2.

If any box is not raw-green by 16:30 → **no real money today**; run DEMO/SIM only and close the
gaps first. Report each with command+output + a NOT-DONE section.
