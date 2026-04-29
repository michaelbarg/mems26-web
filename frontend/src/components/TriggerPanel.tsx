"use client";

import { useState, useEffect } from "react";

interface Trigger {
  id: string;
  type: 'FVG' | 'SWEEP' | 'REVERSAL';
  direction: 'bullish' | 'bearish';
  price_high?: number | null;
  price_low?: number | null;
  gap_size?: number | null;
  swept_level?: string | null;
  swept_price?: number | null;
  current_price: number;
  detected_at: number;
  expires_at: number;
}

interface FootprintBar {
  buy_vol: number;
  sell_vol: number;
  delta: number;
  imbalance_ratio: number;
  is_reversal: boolean;
}

interface TriggerState {
  active: Trigger[];
  footprint_last_bar: FootprintBar | null;
}

interface TriggerResponse {
  ok: boolean;
  triggers?: TriggerState;
  error?: string;
  received_at?: number;
}

const POLL_MS = 5000;

const fmt = (v: number | null | undefined) => v?.toFixed(2) ?? "\u2014";

function timeAgo(ts: number): string {
  const sec = Math.floor(Date.now() / 1000 - ts);
  if (sec < 5) return "just now";
  if (sec < 60) return `${sec}s ago`;
  if (sec < 3600) return `${Math.floor(sec / 60)}m ago`;
  return `${Math.floor(sec / 3600)}h ago`;
}

function formatTime(unix: number): string {
  return new Date(unix * 1000).toLocaleTimeString('en-US', {
    hour: '2-digit', minute: '2-digit', hour12: false,
  });
}

function typeLabel(type: string): string {
  switch (type) {
    case 'FVG': return 'FVG';
    case 'SWEEP': return 'Sweep';
    case 'REVERSAL': return 'Rev';
    default: return type;
  }
}

function extraInfo(t: Trigger): string {
  switch (t.type) {
    case 'FVG': return t.gap_size != null ? `${t.gap_size.toFixed(2)}pt` : '';
    case 'SWEEP': return t.swept_level || '';
    case 'REVERSAL': return 'FP';
    default: return '';
  }
}

interface TriggerPanelProps {
  apiUrl?: string;
}

export default function TriggerPanel({ apiUrl }: TriggerPanelProps) {
  const [data, setData] = useState<TriggerState | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [errorType, setErrorType] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [receivedAt, setReceivedAt] = useState<number | null>(null);
  const base = apiUrl || "https://mems26-web.onrender.com";

  useEffect(() => {
    let active = true;
    const poll = async () => {
      try {
        const res = await fetch(`${base}/trigger/state`);
        const j: TriggerResponse = await res.json();
        if (!active) return;
        if (j.ok && j.triggers) {
          setData(j.triggers);
          setError(null);
          setErrorType(null);
          if (j.received_at) setReceivedAt(j.received_at);
        } else {
          setError(j.error || "Unknown error");
          setErrorType(j.error || null);
          setData(null);
        }
      } catch {
        if (!active) return;
        setError("Connection error \u2014 retrying...");
        setErrorType("NETWORK");
        setData(null);
      } finally {
        if (active) setLoading(false);
      }
    };
    poll();
    const iv = setInterval(poll, POLL_MS);
    return () => { active = false; clearInterval(iv); };
  }, [base]);

  const box: React.CSSProperties = {
    background: '#0d1117', border: '1px solid #1e2738',
    borderRadius: 6, padding: '8px 12px', marginTop: 8,
  };

  if (loading) {
    return (
      <div style={box}>
        <span style={{ fontSize: 12, color: '#6b7280' }}>Loading Triggers...</span>
      </div>
    );
  }

  if (!data) {
    let icon = "\u274C";
    let msg = error || "Unknown error";
    let color = "#ef5350";
    if (errorType === "TRIGGERS_NOT_AVAILABLE") {
      icon = "\u23F3"; msg = "Triggers warming up..."; color = "#ca8a04";
    } else if (errorType === "TRIGGERS_STALE") {
      icon = "\u26A0\uFE0F"; msg = "Triggers stale"; color = "#f97316";
    } else if (errorType === "NETWORK") {
      icon = "\uD83D\uDD0C"; color = "#ef5350";
    }
    return (
      <div style={{ ...box, borderColor: `${color}44` }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
          <span style={{ fontSize: 14, fontWeight: 700, color: '#e5e7eb' }}>Triggers</span>
        </div>
        <div style={{ fontSize: 13, color, textAlign: 'center', padding: '8px 0' }}>
          {icon} {msg}
        </div>
      </div>
    );
  }

  const triggers = data.active.slice(-5).reverse();
  const fp = data.footprint_last_bar;

  const cellStyle: React.CSSProperties = {
    padding: '2px 6px', fontSize: 11, borderBottom: '1px solid #1e2738',
  };

  return (
    <div style={box}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
        <span style={{ fontSize: 14, fontWeight: 700, color: '#e5e7eb' }}>Triggers</span>
        <span style={{ fontSize: 10, color: '#4b5563' }}>
          {triggers.length > 0 ? `${triggers.length} active` : ''}
        </span>
      </div>

      {triggers.length > 0 ? (
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr style={{ background: '#161b22' }}>
              <th style={{ ...cellStyle, textAlign: 'left', color: '#6b7280', fontWeight: 600 }}>Time</th>
              <th style={{ ...cellStyle, textAlign: 'left', color: '#6b7280', fontWeight: 600 }}>Type</th>
              <th style={{ ...cellStyle, textAlign: 'right', color: '#6b7280', fontWeight: 600 }}>Price</th>
              <th style={{ ...cellStyle, textAlign: 'right', color: '#6b7280', fontWeight: 600 }}>Direction</th>
            </tr>
          </thead>
          <tbody>
            {triggers.map((t) => {
              const dirColor = t.direction === 'bullish' ? '#22c55e' : '#ef5350';
              const dirArrow = t.direction === 'bullish' ? '\u2191' : '\u2193';
              const dirLabel = t.direction === 'bullish' ? 'Bull' : 'Bear';
              const extra = extraInfo(t);
              const price = t.price_high ?? t.swept_price ?? t.current_price;
              return (
                <tr key={t.id}>
                  <td style={{ ...cellStyle, color: '#9ca3af', fontFamily: 'monospace' }}>
                    {formatTime(t.detected_at)}
                  </td>
                  <td style={{ ...cellStyle, color: '#e5e7eb', fontWeight: 600 }}>
                    {typeLabel(t.type)}
                  </td>
                  <td style={{ ...cellStyle, textAlign: 'right', color: '#f6c90e', fontFamily: 'monospace', fontWeight: 700 }}>
                    {fmt(price)}
                  </td>
                  <td style={{ ...cellStyle, textAlign: 'right' }}>
                    <span style={{ color: dirColor, fontWeight: 700 }}>{dirArrow} {dirLabel}</span>
                    {extra && <span style={{ color: '#6b7280', marginLeft: 3 }}>({extra})</span>}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      ) : (
        <div style={{ fontSize: 12, color: '#4b5563', textAlign: 'center', padding: '6px 0' }}>
          No active triggers
        </div>
      )}

      {/* Footer: footprint + updated */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 4, fontSize: 10, color: '#4b5563' }}>
        <span>
          {fp ? (
            <>
              <span style={{ color: fp.delta >= 0 ? '#22c55e' : '#ef5350' }}>
                Delta: {fp.delta >= 0 ? '+' : ''}{fp.delta}
              </span>
              <span style={{ margin: '0 4px' }}>|</span>
              <span>Imb: {fp.imbalance_ratio.toFixed(2)}</span>
            </>
          ) : null}
        </span>
        {receivedAt && <span>{timeAgo(receivedAt)}</span>}
      </div>
    </div>
  );
}
