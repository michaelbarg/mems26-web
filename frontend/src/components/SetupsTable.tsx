"use client";

import { useState, useEffect } from "react";

const POLL_MS = 30000;
const API_URL = "https://mems26-web.onrender.com";

interface Setup {
  setup_id: string;
  direction: string;
  trigger_type: string;
  killzone: string;
  day_type: string;
  initial_score: number;
  peak_score: number;
  observation_count: number;
  status: string;
  first_detected_ts: number;
  [key: string]: any;
}

interface Summary {
  total_setups: number;
  building: number;
  live: number;
  expired: number;
  executed: number;
  avg_observations: number;
  max_observations: number;
}

function fmtTime(ts: number): string {
  if (!ts) return "--";
  return new Date(ts * 1000).toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit", hour12: false });
}

function statusStyle(s: string): { color: string; bg: string } {
  switch (s) {
    case "LIVE": return { color: "#22c55e", bg: "#0a2e1a" };
    case "BUILDING": return { color: "#9ca3af", bg: "#1e2738" };
    case "EXECUTED": return { color: "#3b82f6", bg: "#0a1a2e" };
    case "EXPIRED": default: return { color: "#4b5563", bg: "#1a1a1a" };
  }
}

interface SetupsTableProps {
  apiUrl?: string;
}

export default function SetupsTable({ apiUrl }: SetupsTableProps) {
  const [setups, setSetups] = useState<Setup[]>([]);
  const [summary, setSummary] = useState<Summary | null>(null);
  const [loading, setLoading] = useState(true);
  const base = apiUrl || API_URL;

  useEffect(() => {
    let active = true;
    const poll = async () => {
      try {
        const [setupsRes, summaryRes] = await Promise.all([
          fetch(`${base}/analytics/setups/recent?limit=30`),
          fetch(`${base}/analytics/setups/summary`),
        ]);
        const setupsData = await setupsRes.json();
        const summaryData = await summaryRes.json();
        if (!active) return;
        if (setupsData.ok) setSetups(setupsData.setups || []);
        if (summaryData.ok) setSummary(summaryData);
      } catch { /* retry */ }
      finally { if (active) setLoading(false); }
    };
    poll();
    const iv = setInterval(poll, POLL_MS);
    return () => { active = false; clearInterval(iv); };
  }, [base]);

  if (loading) {
    return (
      <div style={{ background: "#0d1117", border: "1px solid #1e2738", borderRadius: 6, padding: "8px 12px", marginTop: 8 }}>
        <span style={{ fontSize: 12, color: "#6b7280" }}>Loading setups...</span>
      </div>
    );
  }

  const cell: React.CSSProperties = {
    padding: "2px 4px", fontSize: 10, borderBottom: "1px solid #1e2738", whiteSpace: "nowrap",
  };

  return (
    <div style={{
      background: "#0d1117", border: "1px solid #1e2738",
      borderRadius: 6, padding: "8px 10px", marginTop: 8,
    }}>
      <div style={{ fontSize: 12, fontWeight: 700, color: "#e5e7eb", marginBottom: 6 }}>
        Unique Setups
      </div>

      {/* Summary card */}
      {summary && (
        <div style={{
          display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 6,
          fontSize: 10, color: "#9ca3af",
        }}>
          <span>Total: <b style={{ color: "#e5e7eb" }}>{summary.total_setups}</b></span>
          <span style={{ color: "#4b5563" }}>|</span>
          <span>Building: <b>{summary.building}</b></span>
          <span>Live: <b style={{ color: "#22c55e" }}>{summary.live}</b></span>
          <span>Expired: <b>{summary.expired}</b></span>
          <span>Executed: <b style={{ color: "#3b82f6" }}>{summary.executed}</b></span>
          <span style={{ color: "#4b5563" }}>|</span>
          <span>Avg obs: <b>{(summary.avg_observations || 0).toFixed(1)}</b></span>
        </div>
      )}

      {!setups.length ? (
        <div style={{ fontSize: 11, color: "#4b5563", padding: "4px 0" }}>No setups detected yet</div>
      ) : (
        <div style={{ overflowX: "auto" }}>
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr>
                {["Time", "Dir", "Type", "KZ", "Day", "Score", "Obs", "Status"].map(h => (
                  <th key={h} style={{
                    ...cell, color: "#4b5563", fontWeight: 600,
                    textAlign: h === "Score" || h === "Obs" ? "right" : "left",
                    borderBottom: "1px solid #2d3748",
                  }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {setups.map(s => {
                const st = statusStyle(s.status);
                const dirColor = s.direction === "LONG" ? "#22c55e" : "#ef5350";
                return (
                  <tr key={s.setup_id}>
                    <td style={{ ...cell, color: "#9ca3af" }}>{fmtTime(s.first_detected_ts)}</td>
                    <td style={{ ...cell, color: dirColor, fontWeight: 700, fontSize: 9 }}>
                      {s.direction === "LONG" ? "\u25B2" : "\u25BC"}{s.direction === "LONG" ? "LG" : "SH"}
                    </td>
                    <td style={{ ...cell, color: "#9ca3af", fontSize: 9 }}>{s.trigger_type || "-"}</td>
                    <td style={{ ...cell, color: "#6b7280", fontSize: 8 }}>{s.killzone || "-"}</td>
                    <td style={{ ...cell, color: "#6b7280", fontSize: 8 }}>
                      {(s.day_type || "").replace("_DAY", "").replace("_", " ") || "-"}
                    </td>
                    <td style={{ ...cell, textAlign: "right", fontFamily: "monospace", color: "#e5e7eb" }}>
                      {s.initial_score || 0}/{s.peak_score || 0}
                    </td>
                    <td style={{ ...cell, textAlign: "right", fontFamily: "monospace", color: "#9ca3af" }}>
                      {s.observation_count || 0}
                    </td>
                    <td style={{
                      ...cell, textAlign: "center", fontWeight: 700, fontSize: 9,
                      color: st.color, background: st.bg, borderRadius: 2, padding: "1px 5px",
                    }}>
                      {s.status}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
