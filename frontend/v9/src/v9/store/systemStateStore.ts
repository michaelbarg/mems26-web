import { create } from 'zustand';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export interface SystemState {
  id: number;
  name: string;
  state: string | null;
  subState: string | null;
  confidence: number;
  lastUpdate: number;
  raw?: Record<string, any>;
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
          confidence: (dt.confidence ?? 0) > 1 ? (dt.confidence / 100) : (dt.confidence ?? 0),
        });
      }
    } catch {}
    try {
      const fm = await fetch(`${API_BASE}/api/v9/five_min/current`).then((r) => r.json()).catch(() => null);
      if (fm) {
        update(2, {
          state: fm.last_pattern ?? fm.mode ?? 'UNKNOWN',
          subState: fm.mode ?? null,
          confidence: fm.last_confluence ? fm.last_confluence / 4 : 0,
          raw: fm,
        });
      }
    } catch {}
    try {
      const fp = await fetch(`${API_BASE}/api/v9/footprint/current`).then((r) => r.json()).catch(() => null);
      if (fp) {
        update(3, {
          state: fp.dominance ?? fp.combined_class ?? fp.last_classification ?? 'NO_SETUP',
          subState: fp.initiative_type ?? null,
          confidence: fp.last_confluence ? fp.last_confluence / 10 : 0,
          raw: fp,
        });
      }
    } catch {}
    try {
      const wo = await fetch(`${API_BASE}/api/v9/woodies/current`).then((r) => r.json()).catch(() => null);
      if (wo) {
        const patterns = wo.active_patterns;
        const topPattern = Array.isArray(patterns) && patterns.length > 0 ? patterns[0].pattern_id : null;
        update(4, {
          state: topPattern ?? wo.last_signal_type ?? wo.signal ?? 'NEUTRAL',
          subState: wo.direction ?? null,
          confidence: wo.strength ? wo.strength / 3 : 0,
          raw: wo,
        });
      }
    } catch {}
    try {
      const tpo = await fetch(`${API_BASE}/api/v9/tpo/current`).then((r) => r.json()).catch(() => null);
      if (tpo) {
        const migDir = tpo.poc_migration?.direction ?? null;
        update(5, {
          state: migDir ?? tpo.profile_shape ?? 'NA',
          subState: tpo.session_type ?? null,
          confidence: tpo.letter_count ? Math.min(tpo.letter_count / 13, 1) : 0,
          raw: tpo,
        });
      }
    } catch {}
    try {
      const kz = await fetch(`${API_BASE}/api/v9/killzone/current`).then((r) => r.json()).catch(() => null);
      if (kz) {
        const cz = kz.current_zone || {};
        update(6, {
          state: cz.name ?? 'UNKNOWN',
          subState: cz.edge_class ?? null,
          confidence: cz.edge_class === 'high' ? 1 : cz.edge_class === 'medium' ? 0.5 : 0.2,
          raw: kz,
        });
      }
    } catch {}
  },
}));
