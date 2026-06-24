'use client';
// useLiveDayType — the NEW state-machine classifier's current call for TODAY, as a live shadow.
// Polls /api/v9/day_type/classify_replay?date=today (read-only; no engine change). Lets the S1
// square + any S1 surface show the validated 7-type classifier instead of the old live engine,
// BEFORE the promotion to the trading gate (Michael 2026-06-20). 30s poll (CLAUDE.md floors-safe).
import { useEffect, useState } from 'react';

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const todayISO = () => new Intl.DateTimeFormat('en-CA', { timeZone: 'America/New_York', year: 'numeric', month: '2-digit', day: '2-digit' }).format(new Date());

export interface LiveDayType { day_type: string; status: string; invalidated?: boolean }

export function useLiveDayType(): LiveDayType | null {
  const [dt, setDt] = useState<LiveDayType | null>(null);
  useEffect(() => {
    let cancel = false;
    const load = () =>
      fetch(`${API}/api/v9/day_type/classify_replay?date=${todayISO()}`)
        .then((r) => (r.ok ? r.json() : null))
        .then((d) => { if (!cancel && d?.final?.day_type) setDt({ day_type: d.final.day_type, status: d.final.status, invalidated: d.final.invalidated }); })
        .catch(() => { /* offline → keep last / null; the caller falls back to the live store */ });
    load();
    const id = setInterval(load, 30000);
    return () => { cancel = true; clearInterval(id); };
  }, []);
  return dt;
}
