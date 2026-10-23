'use client';
import { useEffect, useState } from 'react';

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export interface KeyLevelsToday {
  ib_high: number | null;
  ib_low: number | null;
  ib_width: number | null;
  ib_class: string | null;
  ib_status?: 'pre_open' | 'developing' | 'locked' | 'missing' | null;
  globex_high: number | null;
  globex_low: number | null;
  globex_range: number | null;
  rth_high: number | null;
  rth_low: number | null;
  rth_range: number | null;
  poc: number | null;
  vah: number | null;
  val: number | null;
  day_type: string | null;
  opening_type: string | null;
}

export interface KeyLevelsPrevDay {
  session_date: string | null;
  poc: number | null;
  vah: number | null;
  val: number | null;
  ib_high: number | null;
  ib_low: number | null;
  ib_width: number | null;
  ib_class: string | null;
  range_high: number | null;
  range_low: number | null;
  range: number | null;
  close: number | null;
  /** Sierra's previous_session numbers, kept beside the DB ones once the backend
   *  serves yesterday's VA from the DB CASH session (key_levels_routes, 23.10). */
  sierra_poc?: number | null;
  sierra_vah?: number | null;
  sierra_val?: number | null;
}

/** The backend's `sources` block — which feed each level came from. */
export type KeyLevelsSources = Record<string, string | null | undefined>;

export interface KeyLevels {
  today: KeyLevelsToday;
  prev_day: KeyLevelsPrevDay;
  sources: KeyLevelsSources;
}

/** Hover text for the IB width class shown by KeyLevelsStrip / KeyLevelsCard (audit 23.10 §3:
 *  WIDE here vs NORMAL in the S1 lens for the same 27.75 pt IB). */
export const IB_CLASS_TITLE = 'סיווג-רוחב מוחלט של key_levels: פחות מ-15 נק׳ NARROW · 15–25 MEDIUM · מעל 25 WIDE. מסווג סוג-היום (S1, classify_replay) מדרג את אותו IB יחסית להיסטוריה — ולכן יכול לומר אחרת (למשל NORMAL).';

/** Where yesterday's POC/VAH/VAL came from, for an on-screen label (audit 23.10 §3).
 *  The decision tree (/tree/state context.prev_va) and the gateway read the DB CASH
 *  session (tpo_routes._load_previous_cash_session, v9_tpo_sessions). /key_levels
 *  reports its source in sources.prev_day_va: "db.…" = that same row, "sierra.…" =
 *  Sierra's previous_session block (Study ID:1), which can differ from the tree's. */
export function prevVaSource(sources: KeyLevelsSources, p?: KeyLevelsPrevDay): {
  tag: string | null; sameAsTree: boolean | null; title: string;
} {
  const src = String(sources?.prev_day_va ?? '').trim();
  const sierraNums = p && (p.sierra_vah != null || p.sierra_val != null || p.sierra_poc != null)
    ? ` · סיירה: VAH ${p.sierra_vah ?? '—'} / VAL ${p.sierra_val ?? '—'} / POC ${p.sierra_poc ?? '—'}`
    : '';
  if (src.toLowerCase().startsWith('db')) {
    return { tag: 'DB = עץ', sameAsTree: true,
      title: `ערך-אתמול מסשן ה-CASH ב-DB (v9_tpo_sessions) — אותו מקור שהעץ והשער סוחרים לפיו${sierraNums}` };
  }
  if (src.toLowerCase().startsWith('sierra')) {
    return { tag: 'Sierra ≠ עץ', sameAsTree: false,
      title: 'ערך-אתמול מבלוק previous_session של סיירה (Study ID:1) — לא המקור של העץ. העץ והשער סוחרים לפי סשן ה-CASH ב-DB (v9_tpo_sessions, כמו קווי-אתמול הלבנים בגרף); המספרים עשויים להיות שונים.' };
  }
  return { tag: null, sameAsTree: null, title: src ? `מקור ערך-אתמול: ${src}` : 'מקור ערך-אתמול לא דווח' };
}

const EMPTY: KeyLevels = {
  today: {
    ib_high: null, ib_low: null, ib_width: null, ib_class: null,
    globex_high: null, globex_low: null, globex_range: null,
    rth_high: null, rth_low: null, rth_range: null,
    poc: null, vah: null, val: null,
    day_type: null, opening_type: null,
  },
  prev_day: {
    session_date: null, poc: null, vah: null, val: null,
    ib_high: null, ib_low: null, ib_width: null, ib_class: null,
    range_high: null, range_low: null, range: null, close: null,
  },
  sources: {},
};

export function useKeyLevels(intervalMs = 15_000): { data: KeyLevels; loading: boolean } {
  const [data, setData] = useState<KeyLevels>(EMPTY);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let mounted = true;
    const poll = async () => {
      try {
        const resp = await fetch(`${API}/api/v9/key_levels`);
        if (!resp.ok) return;
        const json = await resp.json();
        if (mounted) {
          setData({
            today: { ...EMPTY.today, ...(json.today ?? {}) },
            prev_day: { ...EMPTY.prev_day, ...(json.prev_day ?? {}) },
            sources: { ...(json.sources ?? {}) },
          });
          setLoading(false);
        }
      } catch { /* silent */ }
    };
    poll();
    const id = setInterval(poll, intervalMs);
    return () => { mounted = false; clearInterval(id); };
  }, [intervalMs]);

  return { data, loading };
}
