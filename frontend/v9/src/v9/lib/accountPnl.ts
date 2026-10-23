// accountPnl — which P&L on GET /api/v9/account/state belongs to the account we trade.
//
// sierra_state.json carries two P&L blocks (backend/v9/api/v9/account_state_routes.py):
//   • the position struct of `trade_account` (Sim1 in DEMO): open_pnl / daily_pnl, is_sim
//   • the Account Monitor (sc.GetTradeAccountData, Michael 07-28): acct_* + acct_is_sim
// Audit 23.10 §3: the Account Monitor described ANOTHER account (acct_is_sim 0 while
// is_sim 1 / trade_account "Sim1") — acct_daily_pl 0.00 while Sim1 was −$175, and
// cash / account value / available funds were DBL_MAX sentinels (~1.8e308).
// Rule: use the Account Monitor only when it describes the same kind of account we
// trade (acct_is_sim === is_sim); otherwise the trade account's own numbers; never
// show a sentinel. Shared by SierraTruthStrip (P&L cells) and BannerStack (loss banner).

export interface SierraAccountState {
  ok?: boolean; stale?: boolean; age_s?: number | null;
  position_qty?: number | null; avg_price?: number | null;
  working_orders?: number | null; is_sim?: number | null;
  order_placement_armed?: number | null;
  open_pnl?: number | null; daily_pnl?: number | null;
  high_during_pos?: number | null; low_during_pos?: number | null;
  trade_account?: string | null; symbol?: string | null;
  last_price?: number | null; daily_total_qty_filled?: number | null;
  // Account-Monitor block — null until the DLL exports it (acct_ok=false)
  acct_ok?: boolean;
  acct_cash_balance?: number | null; acct_account_value?: number | null;
  acct_available_funds?: number | null; acct_open_positions_pl?: number | null;
  acct_daily_pl?: number | null; acct_trading_disabled?: number | null;
  acct_under_margin?: number | null; acct_loss_limit_reached?: number | null;
  acct_is_sim?: number | null;
}

/** A number Sierra really reported. Sentinels (±DBL_MAX ≈ 1.8e308, ±inf, anything
 *  ≥ 1e15 — the backend's own cut-off) and non-numbers → null, so the UI shows "—". */
export function finiteOrNull(v: unknown): number | null {
  if (v == null || v === '') return null;
  const n = Number(v);
  if (!Number.isFinite(n) || Math.abs(n) >= 1e15) return null;
  return n;
}

export type AccountPnlSource = 'account_monitor' | 'trade_account' | null;

export interface AccountPnl {
  open: number | null;
  daily: number | null;
  /** account_monitor = acct_* block · trade_account = open_pnl/daily_pnl of trade_account. */
  source: AccountPnlSource;
  /** The Account-Monitor block exists but describes another account than trade_account. */
  monitorMismatch: boolean;
  /** The account we trade (sierra_state.trade_account), e.g. "Sim1". */
  account: string | null;
}

export function pickAccountPnl(s: SierraAccountState | null | undefined): AccountPnl {
  const account = s?.trade_account ?? null;
  if (!s || s.acct_ok !== true) {
    // No Account-Monitor block (DLL without it): keep the 07-28 rule — "—" rather than
    // the position-struct number (it read 0.00 while the live account was down).
    return { open: null, daily: null, source: null, monitorMismatch: false, account };
  }
  const comparable = s.acct_is_sim != null && s.is_sim != null;
  if (!comparable || Number(s.acct_is_sim) === Number(s.is_sim)) {
    return {
      open: finiteOrNull(s.acct_open_positions_pl),
      daily: finiteOrNull(s.acct_daily_pl),
      source: 'account_monitor',
      monitorMismatch: false,
      account,
    };
  }
  // The Account Monitor looks at another account → the trade account's own numbers.
  return {
    open: finiteOrNull(s.open_pnl),
    daily: finiteOrNull(s.daily_pnl),
    source: 'trade_account',
    monitorMismatch: true,
    account,
  };
}
