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
      // 11.08 fix: identical ticks still bumped tickCount + lastUpdateMs on every
      // message, so every subscriber re-rendered on every tick — React hit
      // "Maximum update depth exceeded". A tick that changes nothing is now a
      // no-op (same object back = zustand skips the notify).
      const same =
        newPrice === s.price &&
        (tick.bid ?? s.bid) === s.bid &&
        (tick.ask ?? s.ask) === s.ask &&
        (tick.last_size ?? s.lastSize) === s.lastSize;
      if (same) return s;
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
