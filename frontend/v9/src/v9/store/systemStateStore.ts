import { create } from 'zustand';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export interface SystemState {
  id: number;
  name: string;
  state: string | null;
  subState: string | null;
  confidence: number;
  lastUpdate: number;
}

interface SystemStateStore {
  systems: Record<number, SystemState>;
  updateSystem: (id: number, patch: Partial<SystemState>) => void;
  fetchAllStates: () => Promise<void>;
}

export const useSystemStateStore = create<SystemStateStore>((set, get) => ({
  systems: {
    1: { id: 1, name: 'Day Type',  state: null, subState: null, confidence: 0, lastUpdate: 0 },
    2: { id: 2, name: '5-Min',     state: null, subState: null, confidence: 0, lastUpdate: 0 },
    3: { id: 3, name: 'Footprint', state: null, subState: null, confidence: 0, lastUpdate: 0 },
    4: { id: 4, name: 'Woodies',   state: null, subState: null, confidence: 0, lastUpdate: 0 },
    5: { id: 5, name: 'TPO',       state: null, subState: null, confidence: 0, lastUpdate: 0 },
    6: { id: 6, name: 'Killzone',  state: null, subState: null, confidence: 0, lastUpdate: 0 },
  },

  updateSystem: (id, patch) =>
    set((s) => ({
      systems: {
        ...s.systems,
        [id]: { ...s.systems[id], ...patch, lastUpdate: Date.now() },
      },
    })),

  fetchAllStates: async () => {
    const update = get().updateSystem;
    try {
      const dt = await fetch(`${API_BASE}/api/v9/day_type/current`).then((r) => r.json()).catch(() => null);
      if (dt) {
        update(1, {
          state: dt.day_type ?? 'UNKNOWN',
          confidence: dt.confidence ?? 0,
        });
      }
    } catch {}
    try {
      const fm = await fetch(`${API_BASE}/api/v9/five_min/current`).then((r) => r.json()).catch(() => null);
      if (fm) {
        update(2, {
          state: fm.mode ?? 'UNKNOWN',
          subState: fm.last_pattern ?? null,
          confidence: fm.last_confluence ? fm.last_confluence / 4 : 0,
        });
      }
    } catch {}
    try {
      const fp = await fetch(`${API_BASE}/api/v9/footprint/current`).then((r) => r.json()).catch(() => null);
      if (fp) {
        update(3, {
          state: fp.last_classification ?? 'NO_SETUP',
          subState: fp.last_pattern ?? null,
          confidence: fp.last_confluence ? fp.last_confluence / 10 : 0,
        });
      }
    } catch {}
    // Systems 4-6: placeholder until Prompts 7-9
  },
}));
