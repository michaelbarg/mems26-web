import { create } from 'zustand';
import type { Trade, AccountStatus, TradeMode, SystemId, TradeOutcome } from '../types';
import { computeAuxStatus, type TradeAuxStatus } from '../lib/tradeAuxStatus';
import { stopMovement, rLevels, durationMinutes } from '../lib/tradeMath';

/** Convert ISO timestamp to YYYY-MM-DD in America/New_York timezone (DST-safe).
 *  Uses Intl.DateTimeFormat('en-CA') which natively outputs YYYY-MM-DD. */
const _etFmt = new Intl.DateTimeFormat('en-CA', { timeZone: 'America/New_York', year: 'numeric', month: '2-digit', day: '2-digit' });
function toETDate(ts: string): string {
  try { return _etFmt.format(new Date(ts)); } catch { return ts.slice(0, 10); }
}

/** Today (ET) as YYYY-MM-DD — /trades filters default to the current trading day.
 *  Evaluated once at store creation; the TradeFilters "Today (RTH)" preset and the
 *  ✕ clear button let the user widen the range at any time. */
function etTodayStr(): string {
  try { return _etFmt.format(new Date()); } catch { return new Date().toISOString().slice(0, 10); }
}

type OverlapFilter = 'all' | 'parallel' | 'sequential';
type LiveGateFilter = 'all' | 'eligible' | 'skipped';
type ConfluenceFilter = 'all' | 'agree' | 'disagree';
type StopMoveFilter = 'all' | 'moved' | 'static';
type SortKey = 'new' | 'old' | 'pnl_dn' | 'pnl_up' | 'dur_dn' | 'rr_dn';

interface TradeFilters {
  mode: TradeMode | 'ALL';
  systemId: SystemId | 'ALL';
  outcome: TradeOutcome | 'ALL';
  dateFrom: string | null;
  dateTo: string | null;
  pattern: string | null;
  /** Time-overlap with another trade in the loaded set. */
  overlap: OverlapFilter;
  /** Sequential gating: at most one open trade at a time (LIVE-style). */
  liveGated: LiveGateFilter;
  /** systems_agreement: at least one observer disagreeing with direction. */
  confluence: ConfluenceFilter;
  /** Direction filter: LONG / SHORT / null (all). */
  direction: string | null;
  /** Stop management: moved to BE (SMART_BE) vs stayed at initial stop. */
  stopMove: StopMoveFilter;
  /** Row ordering. */
  sort: SortKey;
  /** Michael 07-12: shadow trades hidden by default EVERYWHERE on /trades —
   *  one truth for table AND summary (the +841-vs-+111 aggregate bug: the
   *  table hid shadow locally while the summary strip still counted it). */
  hideShadow: boolean;
}

interface TradeState {
  trades: Trade[];
  /** Derived per-trade context (overlap / live-eligible / confluence). */
  auxStatus: Map<number, TradeAuxStatus>;
  accountStatus: AccountStatus | null;
  filters: TradeFilters;
  /** Row expanded inline (recognition panel); toggle on second click. */
  expandedTradeId: number | null;
  /** Alias for TradeDetailsModal compatibility. */
  selectedTradeId: number | null;

  setTrades: (trades: Trade[]) => void;
  addTrade: (trade: Trade) => void;
  updateTrade: (trade: Trade) => void;
  setAccountStatus: (status: AccountStatus) => void;
  setFilters: (filters: Partial<TradeFilters>) => void;
  toggleExpandedTradeId: (id: number) => void;
  /** Chart marker click — opens same inline panel on /trades if navigated. */
  setSelectedTradeId: (id: number | null) => void;
  filteredTrades: () => Trade[];
  auxFor: (id: number) => TradeAuxStatus | undefined;
}

const DEFAULT_FILTERS: TradeFilters = {
  mode: 'ALL',
  systemId: 'ALL',
  outcome: 'ALL',
  // Trade Review default = today (ET). filteredTrades() is consumed only by
  // /trades components (TradeCardList / TradesTable / summary + edge strips),
  // so this does not affect dashboard surfaces (TopBar reads raw `trades`).
  dateFrom: etTodayStr(),
  dateTo: etTodayStr(),
  pattern: null,
  overlap: 'all',
  liveGated: 'all',
  confluence: 'all',
  direction: null,
  stopMove: 'all',
  sort: 'new',
  hideShadow: true,
};

function recomputeAux(trades: Trade[]): Map<number, TradeAuxStatus> {
  return computeAuxStatus(trades);
}

export const useTradeStore = create<TradeState>((set, get) => ({
  trades: [],
  auxStatus: new Map(),
  accountStatus: null,
  filters: DEFAULT_FILTERS,
  expandedTradeId: null,
  selectedTradeId: null,

  setTrades: (trades) => {
    const arr = Array.isArray(trades) ? trades : [];
    set({ trades: arr, auxStatus: recomputeAux(arr) });
  },
  addTrade: (trade) =>
    set((state) => {
      const next = [trade, ...state.trades];
      return { trades: next, auxStatus: recomputeAux(next) };
    }),
  updateTrade: (trade) =>
    set((state) => {
      const next = state.trades.map((t) => (t.id === trade.id ? trade : t));
      return { trades: next, auxStatus: recomputeAux(next) };
    }),
  setAccountStatus: (status) => set({ accountStatus: status }),
  setFilters: (filters) => set((state) => ({ filters: { ...state.filters, ...filters } })),
  toggleExpandedTradeId: (id) =>
    set((state) => ({
      expandedTradeId: state.expandedTradeId === id ? null : id,
    })),
  setSelectedTradeId: (id) => set({ expandedTradeId: id, selectedTradeId: id }),

  auxFor: (id) => get().auxStatus.get(id),

  filteredTrades: () => {
    const { trades, filters, auxStatus } = get();
    const out = trades.filter((t) => {
      if (filters.hideShadow && String(t.mode).toUpperCase() === 'SHADOW') return false;
      if (filters.mode !== 'ALL' && t.mode !== filters.mode) return false;
      if (filters.systemId !== 'ALL' && t.system !== filters.systemId) return false;
      if (filters.outcome !== 'ALL' && t.outcome !== filters.outcome) return false;
      if (filters.direction && t.direction !== filters.direction) return false;
      if (filters.dateFrom || filters.dateTo) {
        // ET-aware date extraction (G6 fix): convert entry_ts to America/New_York date,
        // not UTC slice. An afternoon ET trade (e.g. 2026-06-03T23:30:00Z = 19:30 ET)
        // must fall on the ET date (06-03), not the UTC date (06-04).
        const entryDate = t.entry_ts ? toETDate(t.entry_ts) : '';
        if (filters.dateFrom && entryDate < filters.dateFrom) return false;
        if (filters.dateTo && entryDate > filters.dateTo) return false;
      }
      if (filters.pattern) {
        const needle = filters.pattern.toLowerCase();
        const hay = [t.pattern_id, t.trigger, t.classification, t.direction]
          .filter(Boolean)
          .join(' ')
          .toLowerCase();
        if (!hay.includes(needle)) return false;
      }
      const aux = auxStatus.get(t.id);
      if (filters.overlap !== 'all') {
        const isPar = aux?.isParallel ?? false;
        if (filters.overlap === 'parallel' && !isPar) return false;
        if (filters.overlap === 'sequential' && isPar) return false;
      }
      if (filters.liveGated !== 'all') {
        const elig = aux?.liveEligible ?? false;
        if (filters.liveGated === 'eligible' && !elig) return false;
        if (filters.liveGated === 'skipped' && elig) return false;
      }
      if (filters.confluence !== 'all') {
        const conf = aux?.confluence ?? 'neutral';
        if (filters.confluence === 'agree' && conf !== 'agree') return false;
        if (filters.confluence === 'disagree' && conf !== 'disagree') return false;
      }
      if (filters.stopMove !== 'all') {
        const sm = stopMovement(t);
        if (filters.stopMove === 'moved' && sm !== 'moved') return false;
        if (filters.stopMove === 'static' && sm === 'moved') return false;
      }
      return true;
    });

    const s = filters.sort;
    if (s && s !== 'new') {
      out.sort((a, b) => {
        switch (s) {
          case 'old': return a.id - b.id;
          case 'pnl_dn': return (b.pnl_usd ?? 0) - (a.pnl_usd ?? 0);
          case 'pnl_up': return (a.pnl_usd ?? 0) - (b.pnl_usd ?? 0);
          case 'dur_dn': return (durationMinutes(b) ?? 0) - (durationMinutes(a) ?? 0);
          case 'rr_dn': return (rLevels(b).t2R ?? -Infinity) - (rLevels(a).t2R ?? -Infinity);
          default: return 0;
        }
      });
    } else {
      out.sort((a, b) => b.id - a.id); // 'new' — newest first
    }
    return out;
  },
}));
