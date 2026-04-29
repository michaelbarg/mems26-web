"use client";

import { useState, useEffect } from "react";

interface StrategyData {
  day_type: string;
  targets?: { c1: number; c2: number; R: number; c3_enabled?: boolean; c2_method?: string };
  be_strategy?: string;
}

function mapBeStrategy(be?: string): string {
  if (!be) return 'After C1';
  switch (be) {
    case 'on_c1_fill': return 'After C1';
    case 'on_c2_fill': return 'After C2';
    case 'after_c2_plus_half_R': return 'After C2 + 0.5R';
    default: return be.replace(/_/g, ' ');
  }
}

const POLL_MS = 30000;

interface StrategyPreviewProps {
  apiUrl?: string;
}

export default function StrategyPreview({ apiUrl }: StrategyPreviewProps) {
  const [data, setData] = useState<StrategyData | null>(null);
  const base = apiUrl || "https://mems26-web.onrender.com";

  useEffect(() => {
    let active = true;
    const poll = async () => {
      try {
        const mktRes = await fetch(`${base}/market/latest`);
        const mkt = await mktRes.json();
        const price = mkt?.price || mkt?.bar?.c;
        if (!price || price <= 0) return;

        const res = await fetch(`${base}/quality/preview`, {
          method: 'POST',
          headers: { 'content-type': 'application/json' },
          body: JSON.stringify({ direction: 'LONG', entry: price, stop: price - 5 }),
        });
        const j = await res.json();
        if (!active) return;
        if (j.ok) {
          setData({
            day_type: (j.day_type && j.day_type !== 'UNKNOWN') ? j.day_type : 'NORMAL',
            targets: j.targets,
            be_strategy: j.be_strategy,
          });
        }
      } catch { /* retry next poll */ }
    };
    poll();
    const iv = setInterval(poll, POLL_MS);
    return () => { active = false; clearInterval(iv); };
  }, [base]);

  if (!data) return null;

  const R = data.targets?.R || 5;
  const c1r = data.targets?.c1 && R > 0
    ? ((data.targets.c1 - (data.targets.c1 - R)) / R).toFixed(0) : '1';
  const c2r = data.targets?.c2 && data.targets?.c1 && R > 0
    ? (Math.abs(data.targets.c2 - (data.targets.c1 - R)) / R).toFixed(0) : '2';
  const c3 = data.targets?.c3_enabled === false ? 'Off' : 'Trail';
  const be = mapBeStrategy(data.be_strategy);

  return (
    <div style={{
      background: '#1e2738',
      borderRadius: 4,
      padding: '4px 10px',
      marginTop: 4,
      display: 'flex',
      alignItems: 'center',
      gap: 8,
      fontSize: 10,
      color: '#9ca3af',
      flexWrap: 'wrap',
    }}>
      <span style={{ fontWeight: 700, color: '#6b7280' }}>
        Strategy: {data.day_type.replace('_', ' ')}{data.day_type === 'NORMAL' || data.day_type === 'DEVELOPING' ? ' (default)' : ''}
      </span>
      <span style={{ color: '#4b5563' }}>|</span>
      <span>
        C1={c1r}R
        {' \u00B7 '}C2={c2r}R
        {' \u00B7 '}C3={c3}
      </span>
      <span style={{ color: '#4b5563' }}>|</span>
      <span>BE: {be}</span>
    </div>
  );
}
