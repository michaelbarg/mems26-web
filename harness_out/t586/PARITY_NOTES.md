# T-586 · parity notes (18.10) — live books vs the reference replay, same config window 06–09.10

Tool: `harness_out/t586/parity.py --mode live --from 2026-10-06 --to 2026-10-09 --detail` (reads v9_trades + the ledger + t567ref).

## Result
- 9 common trades: Σ live −237.50$ vs Σ replay −238.75$ ⇒ **Δ +1.25$ — fills and exits are the same system** (whole range 23.09→09.10: 19 common, live entry vs replay fill Σ −38.75$ of which −40$ is #2408 where the replay filled at the open while the live limit filled later at the entry).
- 0 live-only trades. 6 replay-only (Σ −45.65$): 2 on 07.10 = demo day (backend was in demo), 1 broker reject (#3402 09.10 18:10), 1 `tree:kind` (06.10 16:50 OPENING_DRIVE LONG +95.60), 2 "not in ledger" (08.10 17:15 INITIATIVE_LONG +32.50 — live S2 Auth Table T-315 killed it; 07.10 GB100 — live fired at 21:55:03 on the developing bar, replay at 21:59:58 on the closed bar).

## Divergence classes (root causes to fix, each measurable daily with parity.py)
P1 **Opening-type / day-type state at the open.** 06.10 16:30:05 live gateway already had `ot=OPEN_AUCTION_IN` (5 s after the open; the machine's own classifier said UNKNOWN — `[AppStateRootFix] SHADOW would-be opening_type_result: type=UNKNOWN`), at 16:50 `ot=OPEN_AUCTION_IN hint=LONG bias=BOTH kinds=['EDGE_FADE']` and `day_type=Variation` ⇒ `tree:kind` SKIP of OPENING_DRIVE LONG; the replay (and the replay with `--restart-at 15:40`) had UNKNOWN → OPEN_REJECTION_REVERSE / FORMING ⇒ TAKE (+95.60). On 08/09.10 live `ot=UNKNOWN` at 16:3x (correct). Source to diff per push: `_resolve_live_cls()` / `_opening_type_locked` (trading_gateway.py:1137-1160) vs `s1_on_bar` in the harness.
P2 **Two decision layers with two label sources.** S2's Auth Table (`build_status/auth_table_lookup.is_skip(pattern, _s2_det_dt)`, T-315) kills INITIATIVE_LONG on Normal/Neutral/FORMING before the tree sees it; the tree would TAKE. The S2-side label (`_s2_det_dt`) and the tree's label can differ (08.10 17:15).
P3 **S4 (woodies) timing.** Live fires on Sierra's real-time study values inside the bar (first push); the replay's developing-bar payload carries the previous bar's studies and `zlr_detected=False`, so S4 signals fire only on the closed bar (~5 min later, different entry). 29 of 205 reference trades are S4 (+480$); their replay fidelity is structurally limited — the demo parity will show the true live S4 behaviour.
P4 **Live-only gates.** `news_blackout` (hand-maintained calendar; the replay never blocks), `pre_send_entry_guard` (foreign position in the shared account; environmental), `rr_hard_floor` (pre-30.09 config). For parity the replay should apply the historical news calendar.
P5 **Broker rejects at the margin** (09.10 #3402/#3406) — account, not code.
P6 **Config drift.** Tree 3.0→3.4 in 12 days (25.09, 27.09, 03.10, 05.10, 06.10) + flag rulings 30.09 ⇒ the live never matched one measured configuration for more than two sessions; 23.09→05.10 parity is therefore not measurable against today's reference.

## Verdict
The money in 23.09→09.10 was lost by the strategy's own replay (−209$ on the 13 sessions; −436$ net on the last 10), not by execution. Live leaked ≈ −105$ more, mostly from P1/P2/P6 selection differences and the two margin rejects.
