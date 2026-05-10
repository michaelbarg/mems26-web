import { create } from 'zustand';
import type { SystemSignal, SystemMarker, SystemConfig, SystemId, TradeMode } from '../types';

interface SystemState {
  signals: SystemSignal[];
  markers: SystemMarker[];
  configs: SystemConfig[];
  activeSignals: Record<SystemId, SystemSignal | null>;

  setSignals: (signals: SystemSignal[]) => void;
  addSignal: (signal: SystemSignal) => void;
  setMarkers: (markers: SystemMarker[]) => void;
  addMarker: (marker: SystemMarker) => void;
  setConfigs: (configs: SystemConfig[]) => void;
  updateConfig: (systemId: SystemId, mode: TradeMode, params: Record<string, unknown>) => void;
}

export const useSystemStore = create<SystemState>((set) => ({
  signals: [],
  markers: [],
  configs: [],
  activeSignals: { 1: null, 2: null, 3: null, 4: null, 5: null, 6: null },

  setSignals: (signals) => set({ signals }),
  addSignal: (signal) => set((state) => {
    const newSignals = [...state.signals, signal];
    const activeSignals = { ...state.activeSignals, [signal.system_id]: signal };
    return { signals: newSignals, activeSignals };
  }),
  setMarkers: (markers) => set({ markers }),
  addMarker: (marker) => set((state) => ({ markers: [...state.markers, marker] })),
  setConfigs: (configs) => set({ configs }),
  updateConfig: (systemId, mode, params) => set((state) => ({
    configs: state.configs.map((c) =>
      c.system_id === systemId && c.mode === mode
        ? { ...c, params: { ...c.params, ...params } }
        : c
    ),
  })),
}));
