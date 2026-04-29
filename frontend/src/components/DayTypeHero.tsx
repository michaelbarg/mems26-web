"use client";

import { useState, useEffect } from "react";

interface DayHeroData {
  day_type: string;
  day_confidence: number;
  weights_applied?: Record<string, number>;
  be_strategy?: { trigger: string; offset: string };
  targets?: { c1: number; c2: number; R: number };
}

const POLL_MS = 30000;

function getHeroStyle(type: string): { bg: string; border: string; color: string; label: string } {
  switch (type) {
    case 'TREND_DAY':
      return { bg: '#0a2e1a', border: '#22c55e33', color: '#22c55e', label: 'TREND DAY' };
    case 'RANGE_DAY':
      return { bg: '#2a2a0a', border: '#ca8a0433', color: '#ca8a04', label: 'RANGE DAY' };
    case 'GAP_FILL':
      return { bg: '#1a0a2e', border: '#a78bfa33', color: '#a78bfa', label: 'GAP FILL' };
    case 'NORMAL':
      return { bg: '#1e2738', border: '#4b556333', color: '#6b7280', label: 'NORMAL' };
    case 'DEVELOPING':
    default:
      return { bg: '#2a2a0a', border: '#ca8a0433', color: '#ca8a04', label: 'DEVELOPING' };
  }
}

const DEFAULT_WEIGHTS: Record<string, number> = { vegas: 30, tpo: 25, fvg: 25, footprint: 20 };

interface DayTypeHeroProps {
  apiUrl?: string;
}

export default function DayTypeHero({ apiUrl }: DayTypeHeroProps) {
  const [data, setData] = useState<DayHeroData | null>(null);
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
            day_type: j.day_type || 'UNKNOWN',
            day_confidence: j.day_confidence || 0,
            weights_applied: j.weights_applied,
            be_strategy: j.be_strategy,
            targets: j.targets,
          });
        }
      } catch { /* retry next poll */ }
    };
    poll();
    const iv = setInterval(poll, POLL_MS);
    return () => { active = false; clearInterval(iv); };
  }, [base]);

  if (!data || data.day_type === 'UNKNOWN') return null;

  const style = getHeroStyle(data.day_type);
  const weights = data.weights_applied || DEFAULT_WEIGHTS;
  const be = data.be_strategy;

  return (
    <div style={{
      background: style.bg,
      border: `1px solid ${style.border}`,
      borderRadius: 6,
      padding: '8px 12px',
      marginTop: 8,
    }}>
      {/* Title row */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
        <span style={{ fontSize: 14, fontWeight: 800, color: style.color, letterSpacing: 1 }}>
          {style.label}
        </span>
        <span style={{ fontSize: 11, color: '#6b7280' }}>
          {data.day_confidence}% confident
        </span>
      </div>

      {/* Strategy details */}
      <div style={{ fontSize: 10, color: '#9ca3af', lineHeight: 1.6 }}>
        <div>
          Weights: Vegas {weights.vegas || 30}%
          {' \u00B7 '}TPO {weights.tpo || 25}%
          {' \u00B7 '}FVG {weights.fvg || 25}%
          {' \u00B7 '}FP {weights.footprint || 20}%
        </div>
        {data.targets && (
          <div>
            Targets: C1={data.targets.R?.toFixed(1)}R
            {' \u00B7 '}C2={data.targets.c2 ? ((data.targets.c2 - (data.targets.c1 - data.targets.R)) / data.targets.R).toFixed(1) : '2'}R
            {' \u00B7 '}C3=Trail
          </div>
        )}
        {be && (
          <div>BE: {be.trigger} + {be.offset}</div>
        )}
      </div>
    </div>
  );
}
