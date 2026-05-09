import { create } from 'zustand';
import type { Trade, AccountStatus, TradeMode, SystemId, TradeOutcome } from '../types';

interface TradeFilters {
  mode: TradeMode | 'ALL';
  systemId: SystemId | 'ALL';
  outcome: TradeOutcome | 'ALL';
  dateFrom: string | null;
  dateTo: string | null;
  pattern: string | null;
}

interface TradeState {
  trades: Trade[];
  accountStatus: AccountStatus | null;
  filters: TradeFilters;
  selectedTradeId: number | null;

  setTrades: (trades: Trade[]) => void;
  addTrade: (trade: Trade) => void;
  updateTrade: (trade: Trade) => void;
  setAccountStatus: (status: AccountStatus) => void;
  setFilters: (filters: Partial<TradeFilters>) => void;
  setSelectedTradeId: (id: number | null) => void;
  filteredTrades: () => Trade[];
}

export const useTradeStore = create<TradeState>((set, get) => ({
  trades: [],
  accountStatus: null,
  filters: {
    mode: 'ALL',
    systemId: 'ALL',
    outcome: 'ALL',
    dateFrom: null,
    dateTo: null,
    pattern: null,
  },
  selectedTradeId: null,

  setTrades: (trades) => set({ trades }),
  addTrade: (trade) => set((state) => ({ trades: [trade, ...state.trades] })),
  updateTrade: (trade) => set((state) => ({
    trades: state.trades.map((t) => (t.id === trade.id ? trade : t)),
  })),
  setAccountStatus: (status) => set({ accountStatus: status }),
  setFilters: (filters) => set((state) => ({ filters: { ...state.filters, ...filters } })),
  setSelectedTradeId: (id) => set({ selectedTradeId: id }),

  filteredTrades: () => {
    const { trades, filters } = get();
    return trades.filter((t) => {
      if (filters.mode !== 'ALL' && t.mode !== filters.mode) return false;
      if (filters.systemId !== 'ALL' && t.system_id !== filters.systemId) return false;
      if (filters.outcome !== 'ALL' && t.outcome !== filters.outcome) return false;
      if (filters.dateFrom && t.entry_time < filters.dateFrom) return false;
      if (filters.dateTo && t.entry_time > filters.dateTo) return false;
      if (filters.pattern && !t.pattern_name.toLowerCase().includes(filters.pattern.toLowerCase())) return false;
      return true;
    });
  },
}));
