import { create } from 'zustand';
import type { Trade, AccountStatus, TradeMode, SystemId, TradeOutcome } from '../types';
import { computeAuxStatus, type TradeAuxStatus } from '../lib/tradeAuxStatus';

type OverlapFilter = 'all' | 'parallel' | 'sequential';
type LiveGateFilter = 'all' | 'eligible' | 'skipped';
type ConfluenceFilter = 'all' | 'agree' | 'disagree';

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
}

interface TradeState {
  trades: Trade[];
  /** Derived per-trade context (overlap / live-eligible / confluence). */
  auxStatus: Map<number, TradeAuxStatus>;
  accountStatus: AccountStatus | null;
  filters: TradeFilters;
  /** Row expanded inline (recognition panel); toggle on second click. */
  expandedTradeId: number | null;

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
  mode: 'SHADOW',
  systemId: 'ALL',
  outcome: 'ALL',
  dateFrom: null,
  dateTo: null,
  pattern: null,
  overlap: 'all',
  liveGated: 'all',
  confluence: 'all',
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
  setSelectedTradeId: (id) => set({ expandedTradeId: id }),

  auxFor: (id) => get().auxStatus.get(id),

  filteredTrades: () => {
    const { trades, filters, auxStatus } = get();
    return trades.filter((t) => {
      if (filters.mode !== 'ALL' && t.mode !== filters.mode) return false;
      if (filters.systemId !== 'ALL' && t.system !== filters.systemId) return false;
      if (filters.outcome !== 'ALL' && t.outcome !== filters.outcome) return false;
      if (filters.dateFrom && (t.entry_ts ?? '') < filters.dateFrom) return false;
      if (filters.dateTo && (t.entry_ts ?? '') > filters.dateTo) return false;
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
      return true;
    });
  },
}));
