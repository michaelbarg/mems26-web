import { create } from 'zustand';
import type { Bar5Min, TickReversalBar, WoodiesBar, TPOBar } from '../types';

interface MarketState {
  bars5min: Bar5Min[];
  tickReversalBars: TickReversalBar[];
  woodiesBars: WoodiesBar[];
  tpoBars: TPOBar[];
  currentPOC: number | null;
  currentVAH: number | null;
  currentVAL: number | null;
  pdh: number | null;
  pdl: number | null;
  onh: number | null;
  onl: number | null;
  openPrice: number | null;
  vegasEma12: number | null;
  vegasEma34: number | null;
  vegasEma144: number | null;
  vegasEma169: number | null;
  vegasEma576: number | null;
  vegasEma676: number | null;

  setBars5min: (bars: Bar5Min[]) => void;
  addBar5min: (bar: Bar5Min) => void;
  setTickReversalBars: (bars: TickReversalBar[]) => void;
  addTickReversalBar: (bar: TickReversalBar) => void;
  setWoodiesBars: (bars: WoodiesBar[]) => void;
  setTPOBars: (bars: TPOBar[]) => void;
  setLevels: (levels: Partial<Pick<MarketState, 'pdh' | 'pdl' | 'onh' | 'onl' | 'openPrice' | 'currentPOC' | 'currentVAH' | 'currentVAL'>>) => void;
  setVegas: (emas: Partial<Pick<MarketState, 'vegasEma12' | 'vegasEma34' | 'vegasEma144' | 'vegasEma169' | 'vegasEma576' | 'vegasEma676'>>) => void;
}

export const useMarketStore = create<MarketState>((set) => ({
  bars5min: [],
  tickReversalBars: [],
  woodiesBars: [],
  tpoBars: [],
  currentPOC: null,
  currentVAH: null,
  currentVAL: null,
  pdh: null,
  pdl: null,
  onh: null,
  onl: null,
  openPrice: null,
  vegasEma12: null,
  vegasEma34: null,
  vegasEma144: null,
  vegasEma169: null,
  vegasEma576: null,
  vegasEma676: null,

  setBars5min: (bars) => set({ bars5min: bars }),
  addBar5min: (bar) => set((state) => ({ bars5min: [...state.bars5min, bar] })),
  setTickReversalBars: (bars) => set({ tickReversalBars: bars }),
  addTickReversalBar: (bar) => set((state) => ({ tickReversalBars: [...state.tickReversalBars, bar] })),
  setWoodiesBars: (bars) => set({ woodiesBars: bars }),
  setTPOBars: (bars) => set({ tpoBars: bars }),
  setLevels: (levels) => set((state) => ({ ...state, ...levels })),
  setVegas: (emas) => set((state) => ({ ...state, ...emas })),
}));
