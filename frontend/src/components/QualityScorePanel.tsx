"use client";

import { useState, useEffect } from "react";

interface QualityBreakdown {
  vegas: number;
  tpo: number;
  fvg: number;
  footprint: number;
}

interface QualityResponse {
  ok: boolean;
  score?: number;
  breakdown?: QualityBreakdown;
  reasons?: string[];
  position?: { qty: number; exits: string[]; action: string };
  targets?: { c1: number; c2: number; R: number };
  day_type?: string;
  error?: string;
}

const POLL_MS = 5000;
const fmt = (v: number | null | undefined) => v?.toFixed(2) ?? "\u2014";

function getScoreStyle(score: number): { bg: string; color: string; label: string } {
  if (score >= 80) return { bg: '#0a2e1a', color: '#22c55e', label: 'FULL CONVICTION' };
  if (score >= 70) return { bg: '#0a2e1a', color: '#4ade80', label: 'FULL SIZE' };
  if (score >= 50) return { bg: '#2a2a0a', color: '#ca8a04', label: 'HALF SIZE' };
  return { bg: '#2e0a0a', color: '#ef5350', label: 'REJECT' };
}

function getStars(score: number): string {
  if (score >= 90) return '\u2B50\u2B50\u2B50\u2B50\u2B50';
  if (score >= 80) return '\u2B50\u2B50\u2B50\u2B50';
  if (score >= 70) return '\u2B50\u2B50\u2B50';
  if (score >= 50) return '\u2B50\u2B50';
  return '\u2B50';
}

function checkIcon(val: number, max: number): string {
  const pct = max > 0 ? val / max : 0;
  if (pct >= 0.8) return '\u2705';
  if (pct >= 0.5) return '\u26A0\uFE0F';
  return '\u274C';
}

interface QualityScorePanelProps {
  apiUrl?: string;
}

export default function QualityScorePanel({ apiUrl }: QualityScorePanelProps) {
  const [data, setData] = useState<QualityResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [errorType, setErrorType] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const base = apiUrl || "https://mems26-web.onrender.com";

  useEffect(() => {
    let active = true;
    const poll = async () => {
      try {
        const res = await fetch(`${base}/quality/preview`, {
          method: 'POST',
          headers: { 'content-type': 'application/json' },
          body: JSON.stringify({ direction: 'LONG', entry: 0, stop: 0 }),
        });
        const j: QualityResponse = await res.json();
        if (!active) return;
        if (j.ok && j.score !== undefined) {
          setData(j);
          setError(null);
          setErrorType(null);
        } else {
          setError(j.error || "No score available");
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
        <span style={{ fontSize: 12, color: '#6b7280' }}>Loading Quality Score...</span>
      </div>
    );
  }

  if (!data || data.score === undefined) {
    let icon = "\u274C";
    let msg = error || "Unknown error";
    let color = "#ef5350";
    if (errorType === "QUALITY_NOT_AVAILABLE") {
      icon = "\u23F3"; msg = "Quality scoring warming up..."; color = "#ca8a04";
    } else if (errorType === "NETWORK") {
      icon = "\uD83D\uDD0C"; color = "#ef5350";
    }
    return (
      <div style={{ ...box, borderColor: `${color}44` }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
          <span style={{ fontSize: 14, fontWeight: 700, color: '#e5e7eb' }}>Quality Score</span>
        </div>
        <div style={{ fontSize: 13, color, textAlign: 'center', padding: '8px 0' }}>
          {icon} {msg}
        </div>
      </div>
    );
  }

  const score = data.score;
  const style = getScoreStyle(score);
  const bd = data.breakdown;

  const breakdownRows: { label: string; val: number; max: number; reason: string }[] = bd ? [
    { label: 'Vegas', val: bd.vegas, max: 30, reason: '' },
    { label: 'TPO', val: bd.tpo, max: 25, reason: '' },
    { label: 'FVG', val: bd.fvg, max: 25, reason: '' },
    { label: 'Footprint', val: bd.footprint, max: 20, reason: '' },
  ] : [];

  // Match reasons to breakdown rows
  if (data.reasons) {
    for (const r of data.reasons) {
      const lower = r.toLowerCase();
      if (lower.includes('vegas')) { const row = breakdownRows.find(x => x.label === 'Vegas'); if (row) row.reason = r; }
      else if (lower.includes('tpo') || lower.includes('poc')) { const row = breakdownRows.find(x => x.label === 'TPO'); if (row) row.reason = r; }
      else if (lower.includes('fvg') || lower.includes('gap')) { const row = breakdownRows.find(x => x.label === 'FVG'); if (row) row.reason = r; }
      else if (lower.includes('footprint') || lower.includes('delta')) { const row = breakdownRows.find(x => x.label === 'Footprint'); if (row) row.reason = r; }
    }
  }

  const cellStyle: React.CSSProperties = {
    padding: '2px 6px', fontSize: 11, borderBottom: '1px solid #1e2738',
  };

  return (
    <div style={box}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
        <span style={{ fontSize: 14, fontWeight: 700, color: '#e5e7eb' }}>Quality Score</span>
        {data.day_type && (
          <span style={{ fontSize: 10, color: '#6b7280' }}>{data.day_type}</span>
        )}
      </div>

      {/* Score badge */}
      <div style={{
        textAlign: 'center', padding: '6px 0', marginBottom: 6,
        borderRadius: 4, background: style.bg,
        border: `1px solid ${style.color}33`,
      }}>
        <span style={{ fontSize: 20, fontWeight: 900, color: style.color }}>{score}</span>
        <span style={{ fontSize: 13, color: '#6b7280' }}> / 100</span>
        <span style={{ fontSize: 12, marginLeft: 8 }}>{getStars(score)}</span>
        <div style={{ fontSize: 11, fontWeight: 700, color: style.color, marginTop: 2, letterSpacing: 1 }}>
          {style.label}
        </div>
      </div>

      {/* Breakdown table */}
      {breakdownRows.length > 0 && (
        <table style={{ width: '100%', borderCollapse: 'collapse', marginBottom: 4 }}>
          <tbody>
            {breakdownRows.map((row) => (
              <tr key={row.label}>
                <td style={{ ...cellStyle, color: '#9ca3af', fontWeight: 600, width: 70 }}>
                  {row.label}
                </td>
                <td style={{ ...cellStyle, textAlign: 'right', fontFamily: 'monospace', color: '#e5e7eb', width: 50 }}>
                  {row.val}/{row.max}
                </td>
                <td style={{ ...cellStyle, textAlign: 'center', width: 20 }}>
                  {checkIcon(row.val, row.max)}
                </td>
                <td style={{ ...cellStyle, color: '#6b7280', fontSize: 10 }}>
                  {row.reason}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      {/* Targets + Risk */}
      {data.targets && (
        <div style={{ fontSize: 10, color: '#6b7280', borderTop: '1px solid #1e2738', paddingTop: 4 }}>
          <div>
            <span style={{ color: '#9ca3af' }}>Targets: </span>
            <span style={{ color: '#22c55e', fontFamily: 'monospace' }}>C1={fmt(data.targets.c1)}</span>
            <span style={{ color: '#4b5563' }}> | </span>
            <span style={{ color: '#22c55e', fontFamily: 'monospace' }}>C2={fmt(data.targets.c2)}</span>
          </div>
          <div>
            <span style={{ color: '#9ca3af' }}>Risk: </span>
            <span style={{ color: '#ef5350', fontFamily: 'monospace' }}>{fmt(data.targets.R)}pt</span>
          </div>
        </div>
      )}
    </div>
  );
}
