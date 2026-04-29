"use client";

import { useState, useEffect } from "react";

interface DayClassification {
  type: 'TREND_DAY' | 'RANGE_DAY' | 'GAP_FILL' | 'NORMAL' | 'DEVELOPING';
  confidence: number;
  direction?: 'bullish' | 'bearish' | null;
  calculated_at: number;
}

interface DayTypeResponse {
  ok: boolean;
  day_classification?: DayClassification;
  error?: string;
}

const POLL_MS = 30000;

function getTypeStyle(type: string, direction?: string | null): { bg: string; color: string; label: string } {
  switch (type) {
    case 'TREND_DAY':
      return direction === 'bearish'
        ? { bg: '#2e0a0a', color: '#ef5350', label: 'TREND BEARISH' }
        : { bg: '#0a2e1a', color: '#22c55e', label: 'TREND BULLISH' };
    case 'RANGE_DAY':
      return { bg: '#1e2738', color: '#9ca3af', label: 'RANGE' };
    case 'GAP_FILL':
      return { bg: '#1a0a2e', color: '#a78bfa', label: 'GAP FILL' };
    case 'NORMAL':
      return { bg: '#1e2738', color: '#6b7280', label: 'NORMAL' };
    case 'DEVELOPING':
    default:
      return { bg: '#2a2a0a', color: '#ca8a04', label: 'DEVELOPING' };
  }
}

interface DayTypeBadgeProps {
  apiUrl?: string;
}

export default function DayTypeBadge({ apiUrl }: DayTypeBadgeProps) {
  const [data, setData] = useState<DayClassification | null>(null);
  const [error, setError] = useState(false);
  const base = apiUrl || "https://mems26-web.onrender.com";

  useEffect(() => {
    let active = true;
    const poll = async () => {
      try {
        const res = await fetch(`${base}/market/latest`);
        const j = await res.json();
        if (!active) return;
        if (j?.day_classification) {
          setData(j.day_classification);
          setError(false);
        }
      } catch {
        if (active) setError(true);
      }
    };
    poll();
    const iv = setInterval(poll, POLL_MS);
    return () => { active = false; clearInterval(iv); };
  }, [base]);

  if (!data) return null;

  const style = getTypeStyle(data.type, data.direction);

  return (
    <div style={{
      display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6,
      background: style.bg, border: `1px solid ${style.color}33`,
      borderRadius: 4, padding: '3px 10px', marginTop: 8,
    }}>
      <span style={{ fontSize: 11, color: '#6b7280' }}>Day:</span>
      <span style={{ fontSize: 12, fontWeight: 800, color: style.color, letterSpacing: 1 }}>
        {style.label}
      </span>
      <span style={{ fontSize: 10, color: '#6b7280' }}>
        ({data.confidence}%)
      </span>
    </div>
  );
}
