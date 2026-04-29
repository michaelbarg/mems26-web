"use client";

import { useState, useEffect } from "react";

interface TPOLevels {
  poc_price: number;
  vah: number | null;
  val: number | null;
  above_poc?: boolean;
  in_value_area?: boolean;
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

const fmt = (val: number | null | undefined): string => {
  if (val === null || val === undefined) return "\u2014";
  return val.toFixed(2);
};

function timeAgo(ts: number): string {
  const sec = Math.floor(Date.now() / 1000 - ts);
  if (sec < 5) return "just now";
  if (sec < 60) return `${sec}s ago`;
  if (sec < 3600) return `${Math.floor(sec / 60)}m ago`;
  return `${Math.floor(sec / 3600)}h ago`;
}

function TodayStatus({ levels }: { levels: TPOLevels }) {
  const parts: JSX.Element[] = [];
  if (levels.above_poc === true) {
    parts.push(<span key="pos" style={{ color: '#22c55e', fontWeight: 700 }}>Above &#8593;</span>);
  } else if (levels.above_poc === false) {
    parts.push(<span key="pos" style={{ color: '#ef5350', fontWeight: 700 }}>Below &#8595;</span>);
  }
  if (levels.in_value_area) {
    parts.push(<span key="va" style={{ color: '#60a5fa' }}>In VA</span>);
  }
  if (levels.developing) {
    parts.push(<span key="dev" style={{ color: '#ca8a04' }}>DEV</span>);
  }
  if (parts.length === 0) {
    return <span style={{ color: '#6b7280' }}>Live</span>;
  }
  return <>{parts.reduce<JSX.Element[]>((acc, el, i) => {
    if (i > 0) acc.push(<span key={`dot${i}`} style={{ color: '#4b5563' }}> &bull; </span>);
    acc.push(el);
    return acc;
  }, [])}</>;
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
        setError("Connection error \u2014 retrying...");
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
    let icon = "\u274C";
    let msg = error || "Unknown error";
    let color = "#ef5350";
    if (errorType === "TPO_NOT_AVAILABLE") {
      icon = "\u23F3"; msg = "TPO warming up..."; color = "#ca8a04";
    } else if (errorType === "TPO_STALE") {
      icon = "\u26A0\uFE0F"; msg = `TPO data stale${lastUpdated ? ` (${timeAgo(lastUpdated)})` : ""}`;
      color = "#f97316";
    } else if (errorType === "NETWORK") {
      icon = "\uD83D\uDD0C"; color = "#ef5350";
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

  const hasData = tpo.current_day || tpo.previous_day;

  const cellStyle: React.CSSProperties = {
    padding: '3px 8px', fontSize: 11, borderBottom: '1px solid #1e2738',
  };

  return (
    <div style={box}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
        <span style={{ fontSize: 14, fontWeight: 700, color: '#e5e7eb' }}>TPO Profile</span>
        {lastUpdated && (
          <span style={{ fontSize: 10, color: '#4b5563' }}>{timeAgo(lastUpdated)}</span>
        )}
      </div>

      {hasData ? (
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr style={{ background: '#161b22' }}>
              <th style={{ ...cellStyle, textAlign: 'left', color: '#6b7280', fontWeight: 600 }}>Day</th>
              <th style={{ ...cellStyle, textAlign: 'right', color: '#6b7280', fontWeight: 600 }}>POC</th>
              <th style={{ ...cellStyle, textAlign: 'right', color: '#6b7280', fontWeight: 600 }}>Status</th>
            </tr>
          </thead>
          <tbody>
            {tpo.current_day && (
              <tr>
                <td style={{ ...cellStyle, color: '#e5e7eb', fontWeight: 600 }}>Today</td>
                <td style={{ ...cellStyle, textAlign: 'right', color: '#f6c90e', fontFamily: 'monospace', fontWeight: 700 }}>
                  {fmt(tpo.current_day.poc_price)}
                </td>
                <td style={{ ...cellStyle, textAlign: 'right', fontSize: 10 }}>
                  <TodayStatus levels={tpo.current_day} />
                </td>
              </tr>
            )}
            {tpo.previous_day && (
              <tr>
                <td style={{ ...cellStyle, color: '#9ca3af' }}>Previous</td>
                <td style={{ ...cellStyle, textAlign: 'right', color: '#f6c90e', fontFamily: 'monospace', fontWeight: 700, opacity: 0.7 }}>
                  {fmt(tpo.previous_day.poc_price)}
                </td>
                <td style={{ ...cellStyle, textAlign: 'right', fontSize: 10, color: '#6b7280' }}>
                  Final
                </td>
              </tr>
            )}
          </tbody>
        </table>
      ) : (
        <div style={{ fontSize: 12, color: '#4b5563', textAlign: 'center', padding: '6px 0' }}>
          No TPO data available
        </div>
      )}
    </div>
  );
}
