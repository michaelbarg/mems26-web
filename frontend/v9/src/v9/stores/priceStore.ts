import { create } from 'zustand';
import type { PriceTickEvent } from '../types/events';

export type PriceDirection = 'up' | 'down' | 'unchanged';
export type ConnectionStatus = 'live' | 'stale' | 'disconnected';

interface PriceState {
  price: number | null;
  prevPrice: number | null;
  direction: PriceDirection;
  bid: number | null;
  ask: number | null;
  lastSize: number | null;
  lastUpdateMs: number | null;
  connected: boolean;
  tickCount: number;

  // Actions
  onTick: (tick: PriceTickEvent) => void;
  setConnected: (v: boolean) => void;
}

export const usePriceStore = create<PriceState>()((set) => ({
  price: null,
  prevPrice: null,
  direction: 'unchanged',
  bid: null,
  ask: null,
  lastSize: null,
  lastUpdateMs: null,
  connected: false,
  tickCount: 0,

  onTick: (tick) =>
    set((s) => {
      const newPrice = tick.price;
      let dir: PriceDirection = 'unchanged';
      if (s.price != null && newPrice !== s.price) {
        dir = newPrice > s.price ? 'up' : 'down';
      }
      return {
        prevPrice: s.price,
        price: newPrice,
        direction: dir,
        bid: tick.bid ?? s.bid,
        ask: tick.ask ?? s.ask,
        lastSize: tick.last_size ?? s.lastSize,
        lastUpdateMs: tick.ts_ms ?? Date.now(),
        tickCount: s.tickCount + 1,
      };
    }),

  setConnected: (v) => set({ connected: v }),
}));

/** Derive connection status from store state. */
export function getConnectionStatus(connected: boolean, lastUpdateMs: number | null): ConnectionStatus {
  if (!connected) return 'disconnected';
  if (lastUpdateMs == null) return 'disconnected';
  const age = Date.now() - lastUpdateMs;
  if (age < 2000) return 'live';
  if (age < 10000) return 'stale';
  return 'disconnected';
}
