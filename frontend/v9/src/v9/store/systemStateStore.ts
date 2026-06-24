import { create } from 'zustand';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export type HealthStatus = 'healthy' | 'warn' | 'error' | 'unknown';

export interface SystemState {
  id: number;
  name: string;
  state: string | null;
  subState: string | null;
  confidence: number;
  lastUpdate: number;
  health: HealthStatus;
  raw?: Record<string, unknown>;
}

interface SystemStateStore {
  systems: Record<number, SystemState>;
  updateSystem: (id: number, patch: Partial<SystemState>) => void;
  fetchAllStates: () => Promise<void>;
}

let _fetchInFlight = false;

export const useSystemStateStore = create<SystemStateStore>((set, get) => ({
  systems: {
    1: { id: 1, name: 'Day Type',  state: null, subState: null, confidence: 0, lastUpdate: 0, health: 'unknown' },
    2: { id: 2, name: '5-Min',     state: null, subState: null, confidence: 0, lastUpdate: 0, health: 'unknown' },
    3: { id: 3, name: 'Footprint', state: null, subState: null, confidence: 0, lastUpdate: 0, health: 'unknown' },
    4: { id: 4, name: 'Woodies',   state: null, subState: null, confidence: 0, lastUpdate: 0, health: 'unknown' },
    5: { id: 5, name: 'TPO',       state: null, subState: null, confidence: 0, lastUpdate: 0, health: 'unknown' },
    6: { id: 6, name: 'Killzone',  state: null, subState: null, confidence: 0, lastUpdate: 0, health: 'unknown' },
  },

  updateSystem: (id, patch) =>
    set((s) => ({
      systems: {
        ...s.systems,
        [id]: { ...s.systems[id], ...patch, lastUpdate: Date.now() },
      },
    })),

  fetchAllStates: async () => {
    if (_fetchInFlight) return; // Prevent overlapping polls when backend is slow
    _fetchInFlight = true;
    const update = get().updateSystem;
    try {
      const snapshot = await fetch(`${API_BASE}/api/v9/cockpit/systems-snapshot`)
        .then((r) => (r.ok ? r.json() : null))
        .catch(() => null);
      // Display-promotion (Michael 2026-06-20): override System 1 with the NEW validated
      // state-machine classifier (read-only shadow over TODAY's bars via classify_replay), so
      // EVERY S1 surface (pill, lens, plan) shows it. Falls back to the old engine's value when
      // there are no bars yet (pre-RTH / closed market) or offline. DISPLAY only — the trade gate
      // still uses the live engine until the full promotion.
      const overrideS1 = async () => {
        try {
          const today = new Intl.DateTimeFormat('en-CA', { timeZone: 'America/Chicago', year: 'numeric', month: '2-digit', day: '2-digit' }).format(new Date());
          const nc = await fetch(`${API_BASE}/api/v9/day_type/classify_replay?date=${today}`).then((r) => (r.ok ? r.json() : null)).catch(() => null);
          if (nc?.final?.day_type) {
            update(1, { state: nc.final.day_type, subState: nc.final.status ?? null, raw: { ...nc.final, measured: nc.measured, source: 'new_classifier' } });
          }
        } catch { /* keep the old-engine value set above */ }
      };

      if (snapshot?.systems) {
        for (const [idStr, system] of Object.entries(snapshot.systems as Record<string, Partial<SystemState>>)) {
          if (Number(idStr) === 1) continue; // S1 comes ONLY from the NEW classifier (classify_replay) — one source of truth across all surfaces
          update(Number(idStr), system);
        }
        await overrideS1();
        return;
      }

      // Fallback: fetch all 6 systems in parallel (not sequential) — ~80ms vs ~400ms
      // S1 (Day Type) is no longer read from the legacy /current wrappers — it comes solely
      // from the NEW validated classifier via overrideS1() below (one source of truth). The
      // dead day_type/v9/current + day_type/current endpoints (None / old 3-type engine) are retired.
      const [fm, fp, wo, tpo, kz] = await Promise.all([
        fetch(`${API_BASE}/api/v9/five_min/current`).then((r) => r.json()).catch(() => null),
        fetch(`${API_BASE}/api/v9/footprint/current`).then((r) => r.json()).catch(() => null),
        fetch(`${API_BASE}/api/v9/woodies/current`).then((r) => r.json()).catch(() => null),
        fetch(`${API_BASE}/api/v9/tpo/current`).then((r) => r.json()).catch(() => null),
        fetch(`${API_BASE}/api/v9/killzone/current`).then((r) => r.json()).catch(() => null),
      ]);

      if (fm) update(2, { state: fm.last_pattern ?? fm.mode ?? 'UNKNOWN', subState: fm.mode ?? null, confidence: fm.last_confluence ? fm.last_confluence / 4 : 0, raw: fm });
      if (fp) update(3, { state: fp.dominance ?? fp.combined_class ?? fp.last_classification ?? 'NO_SETUP', subState: fp.initiative_type ?? null, confidence: fp.last_confluence ? fp.last_confluence / 10 : 0, raw: fp });
      if (wo) {
        const patterns = wo.active_patterns;
        const topPattern = Array.isArray(patterns) && patterns.length > 0 ? patterns[0].pattern_id : null;
        update(4, { state: topPattern ?? wo.last_signal_type ?? wo.signal ?? 'NEUTRAL', subState: wo.direction ?? null, confidence: wo.strength ? wo.strength / 3 : 0, raw: wo });
      }
      if (tpo) update(5, { state: tpo.poc_migration?.direction ?? tpo.profile_shape ?? 'NA', subState: tpo.session_type ?? null, confidence: tpo.letter_count ? Math.min(tpo.letter_count / 13, 1) : 0, raw: tpo });
      if (kz) {
        const cz = kz.current_zone || {};
        update(6, { state: cz.name ?? 'UNKNOWN', subState: cz.edge_class ?? null, confidence: cz.edge_class === 'high' ? 1 : cz.edge_class === 'medium' ? 0.5 : 0.2, raw: kz });
      }
      await overrideS1();
    } finally {
      _fetchInFlight = false;
    }
  },
}));
