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
}

export interface KeyLevels {
  today: KeyLevelsToday;
  prev_day: KeyLevelsPrevDay;
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
