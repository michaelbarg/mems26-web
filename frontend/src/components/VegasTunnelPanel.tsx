"use client";

import { useState, useEffect } from "react";

interface VegasState {
  ema144: number;
  ema169: number;
  tunnel_top: number;
  tunnel_bot: number;
  tunnel_width: number;
  price_position: "ABOVE" | "INSIDE" | "BELOW";
  trend: "BULLISH" | "BEARISH" | "NEUTRAL";
  data_quality: "FULL" | "PARTIAL";
  bar_count: number;
  calculated_at: number;
  received_at: number;
}

interface VegasResponse {
  ok: boolean;
  vegas?: VegasState;
  error?: string;
  message?: string;
  last_updated?: number;
}

const POLL_MS = 5000;

function getTrendStyle(trend: string): { bg: string; color: string } {
  switch (trend) {
    case "BULLISH":  return { bg: "#0a2e1a", color: "#22c55e" };
    case "BEARISH":  return { bg: "#2e0a0a", color: "#ef5350" };
    case "NEUTRAL":  return { bg: "#2a2a0a", color: "#ca8a04" };
    default:         return { bg: "#1e2738", color: "#9ca3af" };
  }
}

function getPositionStyle(pos: string): { color: string } {
  switch (pos) {
    case "ABOVE":  return { color: "#22c55e" };
    case "BELOW":  return { color: "#ef5350" };
    case "INSIDE": return { color: "#ca8a04" };
    default:       return { color: "#9ca3af" };
  }
}

function getStrength(width: number): { label: string; color: string } {
  if (width > 5)  return { label: "STRONG", color: "#22c55e" };
  if (width >= 2) return { label: "MODERATE", color: "#60a5fa" };
  return { label: "WEAK", color: "#6b7280" };
}

function timeAgo(ts: number): string {
  const sec = Math.floor(Date.now() / 1000 - ts);
  if (sec < 5) return "just now";
  if (sec < 60) return `${sec}s ago`;
  if (sec < 3600) return `${Math.floor(sec / 60)}m ago`;
  return `${Math.floor(sec / 3600)}h ago`;
}

interface VegasTunnelPanelProps {
  apiUrl?: string;
}

export default function VegasTunnelPanel({ apiUrl }: VegasTunnelPanelProps) {
  const [vegas, setVegas] = useState<VegasState | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [errorType, setErrorType] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [lastUpdated, setLastUpdated] = useState<number | null>(null);
  const base = apiUrl || "https://mems26-web.onrender.com";

  useEffect(() => {
    let active = true;
    const poll = async () => {
      try {
        const res = await fetch(`${base}/vegas/state`);
        const data: VegasResponse = await res.json();
        if (!active) return;
        if (data.ok && data.vegas) {
          setVegas(data.vegas);
          setError(null);
          setErrorType(null);
          setLastUpdated(data.vegas.received_at);
        } else {
          setError(data.message || data.error || "Unknown error");
          setErrorType(data.error || null);
          setVegas(null);
          if (data.last_updated) setLastUpdated(data.last_updated);
        }
      } catch {
        if (!active) return;
        setError("Connection error — retrying...");
        setErrorType("NETWORK");
        setVegas(null);
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

  // Loading
  if (loading) {
    return (
      <div style={box}>
        <span style={{ fontSize: 12, color: '#6b7280' }}>Loading Vegas Tunnel...</span>
      </div>
    );
  }

  // Error states
  if (!vegas) {
    let icon = "❌";
    let msg = error || "Unknown error";
    let color = "#ef5350";
    if (errorType === "VEGAS_NOT_AVAILABLE") {
      icon = "⏳"; msg = "Vegas warming up..."; color = "#ca8a04";
    } else if (errorType === "VEGAS_STALE") {
      icon = "⚠️"; msg = `Vegas data stale${lastUpdated ? ` (${timeAgo(lastUpdated)})` : ""}`;
      color = "#f97316";
    } else if (errorType === "NETWORK") {
      icon = "🔌"; color = "#ef5350";
    }
    return (
      <div style={{ ...box, borderColor: `${color}44` }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
          <span style={{ fontSize: 14, fontWeight: 700, color: '#e5e7eb' }}>Vegas Tunnel</span>
          <span style={{ fontSize: 10, color: '#4b5563' }}>V2.0</span>
        </div>
        <div style={{ fontSize: 13, color, textAlign: 'center', padding: '8px 0' }}>
          {icon} {msg}
        </div>
      </div>
    );
  }

  const trend = getTrendStyle(vegas.trend);
  const pos = getPositionStyle(vegas.price_position);
  const strength = getStrength(vegas.tunnel_width);

  return (
    <div style={box}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
        <span style={{ fontSize: 14, fontWeight: 700, color: '#e5e7eb' }}>Vegas Tunnel</span>
        <span style={{ fontSize: 10, color: '#4b5563' }}>V2.0</span>
      </div>

      {/* Trend badge */}
      <div style={{
        textAlign: 'center', padding: '4px 0', marginBottom: 6,
        borderRadius: 4, background: trend.bg,
        border: `1px solid ${trend.color}33`,
      }}>
        <span style={{ fontSize: 16, fontWeight: 900, color: trend.color, letterSpacing: 2 }}>
          {vegas.trend === "BULLISH" ? "▲" : vegas.trend === "BEARISH" ? "▼" : "◆"} {vegas.trend}
        </span>
      </div>

      {/* Tunnel visualization */}
      <div style={{ marginBottom: 6, padding: '4px 0' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, marginBottom: 2 }}>
          <span style={{ color: '#6b7280' }}>EMA 144</span>
          <span style={{ color: '#e5e7eb', fontFamily: 'monospace' }}>{vegas.ema144.toFixed(2)}</span>
        </div>
        {/* Tunnel bar */}
        <div style={{
          position: 'relative', height: 18, borderRadius: 3, overflow: 'hidden',
          background: `linear-gradient(180deg, ${trend.color}25 0%, ${trend.color}10 100%)`,
          border: `1px solid ${trend.color}33`,
        }}>
          {/* Position indicator */}
          <div style={{
            position: 'absolute',
            top: vegas.price_position === "ABOVE" ? -2 : vegas.price_position === "BELOW" ? 14 : 5,
            left: '50%', transform: 'translateX(-50%)',
            fontSize: 10, fontWeight: 800, color: pos.color,
          }}>
            {vegas.price_position === "ABOVE" ? "▲ ABOVE" : vegas.price_position === "BELOW" ? "▼ BELOW" : "◆ INSIDE"}
          </div>
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, marginTop: 2 }}>
          <span style={{ color: '#6b7280' }}>EMA 169</span>
          <span style={{ color: '#e5e7eb', fontFamily: 'monospace' }}>{vegas.ema169.toFixed(2)}</span>
        </div>
      </div>

      {/* Numeric grid 2x3 */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 4, marginBottom: 6, fontSize: 11 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
          <span style={{ color: '#6b7280' }}>Width</span>
          <span style={{ color: '#e5e7eb', fontFamily: 'monospace' }}>{vegas.tunnel_width.toFixed(2)}pt</span>
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
          <span style={{ color: '#6b7280' }}>Strength</span>
          <span style={{ color: strength.color, fontWeight: 700 }}>{strength.label}</span>
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
          <span style={{ color: '#6b7280' }}>Position</span>
          <span style={{ color: pos.color, fontWeight: 700 }}>{vegas.price_position}</span>
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
          <span style={{ color: '#6b7280' }}>Bars</span>
          <span style={{ color: '#e5e7eb', fontFamily: 'monospace' }}>{vegas.bar_count}</span>
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
          <span style={{ color: '#6b7280' }}>Quality</span>
          <span style={{ color: vegas.data_quality === "FULL" ? "#22c55e" : "#ca8a04", fontWeight: 700 }}>
            {vegas.data_quality}
          </span>
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
          <span style={{ color: '#6b7280' }}>Updated</span>
          <span style={{ color: '#9ca3af' }}>{timeAgo(vegas.received_at)}</span>
        </div>
      </div>

      {/* Data quality warning */}
      {vegas.data_quality === "PARTIAL" && (
        <div style={{
          fontSize: 11, color: '#ca8a04', textAlign: 'center',
          padding: '3px 0', background: '#2a2a0a', borderRadius: 3,
          border: '1px solid #ca8a0433',
        }}>
          Partial data — fewer than 169 bars
        </div>
      )}
    </div>
  );
}
