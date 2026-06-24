'use client';
// useDirectionNow — the CURRENT detected market direction (UP/DOWN/NEUTRAL) from the
// #68 direction-context prototype (CVD + location + breakout-state on today's RTH bars).
// Polls /api/v9/day_type/direction_now. READ-ONLY / DISPLAY ONLY — does NOT affect any
// trading decision. 12s poll (light query; gentle on the single-worker backend).
import { useEffect, useState } from 'react';

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export interface DirectionNow {
  dir: string;
  reason: string;
  n_bars: number;
  cvd_slope?: number;
  lsma_side?: number | null;   // +1 = price ABOVE the LSMA, -1 = BELOW (LSMA-veto engine)
  mode?: string;               // 'lsma_cvd_veto' when DIRECTION_LSMA_VETO is on
  breakout_state?: string;
  ib_high?: number | null;
  ib_low?: number | null;
  poc?: number | null;
  close?: number | null;
}

export function useDirectionNow(): DirectionNow | null {
  const [d, setD] = useState<DirectionNow | null>(null);
  useEffect(() => {
    let cancel = false;
    const load = () =>
      fetch(`${API}/api/v9/day_type/direction_now`)
        .then((r) => (r.ok ? r.json() : null))
        .then((x) => { if (!cancel && x && x.dir) setD(x as DirectionNow); })
        .catch(() => { /* offline → keep last */ });
    load();
    const id = setInterval(load, 12000);
    return () => { cancel = true; clearInterval(id); };
  }, []);
  return d;
}
