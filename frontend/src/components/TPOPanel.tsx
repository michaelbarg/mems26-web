"use client";

import { useState, useEffect } from "react";

interface TPOLevels {
  poc_price: number;
  vah: number;
  val: number;
  tpo_letter_minutes: number;
  developing: boolean;
  study_id: number;
  calculated_at: number;
}

interface TPOState {
  current_day: TPOLevels | null;
  previous_day: TPOLevels | null;
}

interface TPOResponse {
  ok: boolean;
  tpo?: TPOState;
  error?: string;
  message?: string;
  last_updated?: number;
}

const POLL_MS = 5000;

function timeAgo(ts: number): string {
  const sec = Math.floor(Date.now() / 1000 - ts);
  if (sec < 5) return "just now";
  if (sec < 60) return `${sec}s ago`;
  if (sec < 3600) return `${Math.floor(sec / 60)}m ago`;
  return `${Math.floor(sec / 3600)}h ago`;
}

function LevelRow({ label, price, color }: { label: string; price: number; color: string }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, padding: '1px 0' }}>
      <span style={{ color: '#6b7280' }}>{label}</span>
      <span style={{ color, fontFamily: 'monospace', fontWeight: 700 }}>{price.toFixed(2)}</span>
    </div>
  );
}

function DaySection({ title, levels, badge }: { title: string; levels: TPOLevels; badge?: string }) {
  const vaRange = levels.vah - levels.val;
  return (
    <div style={{ marginBottom: 4 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 3 }}>
        <span style={{ fontSize: 11, fontWeight: 700, color: '#9ca3af' }}>{title}</span>
        {badge && (
          <span style={{
            fontSize: 9, fontWeight: 700, padding: '0px 4px',
            borderRadius: 3, background: '#0a2e1a', color: '#22c55e',
          }}>{badge}</span>
        )}
        {levels.developing && (
          <span style={{
            fontSize: 9, fontWeight: 700, padding: '0px 4px',
            borderRadius: 3, background: '#2a2a0a', color: '#ca8a04',
          }}>DEV</span>
        )}
      </div>
      <LevelRow label="POC" price={levels.poc_price} color="#f6c90e" />
      <LevelRow label="VAH" price={levels.vah} color="#60a5fa" />
      <LevelRow label="VAL" price={levels.val} color="#60a5fa" />
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 10, padding: '1px 0', marginTop: 1 }}>
        <span style={{ color: '#4b5563' }}>VA Range</span>
        <span style={{ color: '#6b7280', fontFamily: 'monospace' }}>{vaRange.toFixed(2)}pt</span>
      </div>
    </div>
  );
}

interface TPOPanelProps {
  apiUrl?: string;
}

export default function TPOPanel({ apiUrl }: TPOPanelProps) {
  const [tpo, setTpo] = useState<TPOState | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [errorType, setErrorType] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [lastUpdated, setLastUpdated] = useState<number | null>(null);
  const base = apiUrl || "https://mems26-web.onrender.com";

  useEffect(() => {
    let active = true;
    const poll = async () => {
      try {
        const res = await fetch(`${base}/tpo/state`);
        const data: TPOResponse = await res.json();
        if (!active) return;
        if (data.ok && data.tpo) {
          setTpo(data.tpo);
          setError(null);
          setErrorType(null);
          const ts = data.tpo.current_day?.calculated_at || data.tpo.previous_day?.calculated_at;
          if (ts) setLastUpdated(ts);
        } else {
          setError(data.message || data.error || "Unknown error");
          setErrorType(data.error || null);
          setTpo(null);
          if (data.last_updated) setLastUpdated(data.last_updated);
        }
      } catch {
        if (!active) return;
        setError("Connection error — retrying...");
        setErrorType("NETWORK");
        setTpo(null);
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
        <span style={{ fontSize: 12, color: '#6b7280' }}>Loading TPO...</span>
      </div>
    );
  }

  if (!tpo) {
    let icon = "❌";
    let msg = error || "Unknown error";
    let color = "#ef5350";
    if (errorType === "TPO_NOT_AVAILABLE") {
      icon = "⏳"; msg = "TPO warming up..."; color = "#ca8a04";
    } else if (errorType === "TPO_STALE") {
      icon = "⚠️"; msg = `TPO data stale${lastUpdated ? ` (${timeAgo(lastUpdated)})` : ""}`;
      color = "#f97316";
    } else if (errorType === "NETWORK") {
      icon = "🔌"; color = "#ef5350";
    }
    return (
      <div style={{ ...box, borderColor: `${color}44` }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
          <span style={{ fontSize: 14, fontWeight: 700, color: '#e5e7eb' }}>TPO Profile</span>
        </div>
        <div style={{ fontSize: 13, color, textAlign: 'center', padding: '8px 0' }}>
          {icon} {msg}
        </div>
      </div>
    );
  }

  return (
    <div style={box}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
        <span style={{ fontSize: 14, fontWeight: 700, color: '#e5e7eb' }}>TPO Profile</span>
        {lastUpdated && (
          <span style={{ fontSize: 10, color: '#4b5563' }}>{timeAgo(lastUpdated)}</span>
        )}
      </div>

      {/* Current day */}
      {tpo.current_day && (
        <DaySection title="Today" levels={tpo.current_day} badge="LIVE" />
      )}

      {/* Separator */}
      {tpo.current_day && tpo.previous_day && (
        <div style={{ borderTop: '1px solid #1e2738', margin: '4px 0' }} />
      )}

      {/* Previous day */}
      {tpo.previous_day && (
        <DaySection title="Yesterday" levels={tpo.previous_day} />
      )}

      {/* No data for either */}
      {!tpo.current_day && !tpo.previous_day && (
        <div style={{ fontSize: 12, color: '#4b5563', textAlign: 'center', padding: '6px 0' }}>
          No TPO data available
        </div>
      )}
    </div>
  );
}
