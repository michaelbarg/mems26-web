"use client";

import { useState, useEffect } from "react";

interface Attempt {
  id: number;
  ts: number;
  direction: string;
  setup_quality_score?: number | null;
  health_score_at_entry?: number | null;
  day_type?: string;
  hypothetical_mae_60min_pts?: number | null;
  hypothetical_mfe_60min_pts?: number | null;
  outcome?: string;
  entry_price_hypothetical?: number;
  stop_hypothetical?: number;
}

const POLL_MS = 30000;
const API_URL = "https://mems26-web.onrender.com";

function fmtTime(ts: number): string {
  if (!ts) return "--";
  const d = new Date(ts * 1000);
  return d.toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit", hour12: false });
}

function scoreColor(s: number): string {
  if (s >= 70) return "#22c55e";
  if (s >= 50) return "#ca8a04";
  return "#6b7280";
}

function scoreBg(s: number): string {
  if (s >= 70) return "#0a2e1a";
  if (s >= 50) return "#2a2a0a";
  return "#1e2738";
}

function outcomeDisplay(a: Attempt): { text: string; color: string } {
  const now = Date.now() / 1000;
  if ((now - a.ts) < 3600 && a.hypothetical_mae_60min_pts == null) {
    return { text: "\u23F0 pending", color: "#6b7280" };
  }
  const outcome = a.outcome;
  if (outcome === "HIT_C1") return { text: "\u2705 HIT_C1", color: "#22c55e" };
  if (outcome === "HIT_STOP") return { text: "\u274C HIT_STOP", color: "#ef5350" };
  if (outcome === "TIMEOUT") return { text: "\u23F3 TIMEOUT", color: "#9ca3af" };
  if (a.hypothetical_mae_60min_pts != null) {
    return { text: `MAE=${a.hypothetical_mae_60min_pts?.toFixed(1)}`, color: "#9ca3af" };
  }
  return { text: "\u23F0 pending", color: "#6b7280" };
}

interface AttemptsTableProps {
  apiUrl?: string;
}

export default function AttemptsTable({ apiUrl }: AttemptsTableProps) {
  const [attempts, setAttempts] = useState<Attempt[]>([]);
  const [loading, setLoading] = useState(true);
  const base = apiUrl || API_URL;

  useEffect(() => {
    let active = true;
    const poll = async () => {
      try {
        // Fetch both endpoints in parallel
        const [scoreRes, outcomeRes] = await Promise.all([
          fetch(`${base}/analytics/attempts/recent_with_score?limit=30`),
          fetch(`${base}/analytics/attempts/with_outcomes?limit=30`),
        ]);
        const scoreData = await scoreRes.json();
        const outcomeData = await outcomeRes.json();
        if (!active) return;

        // Merge by id: scored attempts are primary, outcomes overlay
        const outcomeMap = new Map<number, Attempt>();
        for (const a of (outcomeData.attempts || [])) {
          outcomeMap.set(a.id, a);
        }

        const merged: Attempt[] = [];
        for (const a of (scoreData.attempts || [])) {
          const oc = outcomeMap.get(a.id);
          merged.push({
            ...a,
            hypothetical_mae_60min_pts: oc?.hypothetical_mae_60min_pts ?? a.hypothetical_mae_60min_pts,
            hypothetical_mfe_60min_pts: oc?.hypothetical_mfe_60min_pts ?? a.hypothetical_mfe_60min_pts,
            outcome: oc?.outcome ?? a.outcome,
          });
        }
        // Add any outcome-only entries not in scored list
        for (const a of (outcomeData.attempts || [])) {
          if (!merged.find(m => m.id === a.id)) {
            merged.push(a);
          }
        }

        merged.sort((a, b) => (b.ts || 0) - (a.ts || 0));
        setAttempts(merged.slice(0, 30));
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

  if (!attempts.length) {
    return (
      <div style={{ background: "#0d1117", border: "1px solid #1e2738", borderRadius: 6, padding: "8px 12px", marginTop: 8 }}>
        <span style={{ fontSize: 12, color: "#4b5563" }}>No scored setups yet</span>
      </div>
    );
  }

  const cellStyle: React.CSSProperties = {
    padding: "3px 5px",
    fontSize: 10,
    borderBottom: "1px solid #1e2738",
    whiteSpace: "nowrap",
  };

  return (
    <div style={{
      background: "#0d1117", border: "1px solid #1e2738",
      borderRadius: 6, padding: "8px 10px", marginTop: 8,
    }}>
      <div style={{ fontSize: 12, fontWeight: 700, color: "#e5e7eb", marginBottom: 6 }}>
        Setup Attempts ({attempts.length})
      </div>
      <div style={{ overflowX: "auto" }}>
        <table style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead>
            <tr>
              {["Time", "Dir", "Score", "Day", "MAE", "MFE", "Outcome"].map(h => (
                <th key={h} style={{
                  ...cellStyle, color: "#4b5563", fontWeight: 600,
                  textAlign: h === "Time" || h === "Dir" || h === "Day" ? "left" : "right",
                  borderBottom: "1px solid #2d3748",
                }}>
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {attempts.map(a => {
              const score = a.setup_quality_score ?? a.health_score_at_entry ?? 0;
              const oc = outcomeDisplay(a);
              const dirColor = a.direction === "LONG" ? "#22c55e" : a.direction === "SHORT" ? "#ef5350" : "#6b7280";
              return (
                <tr key={a.id}>
                  <td style={{ ...cellStyle, color: "#9ca3af" }}>{fmtTime(a.ts)}</td>
                  <td style={{ ...cellStyle, color: dirColor, fontWeight: 700 }}>
                    {a.direction === "LONG" ? "\u25B2" : "\u25BC"} {a.direction}
                  </td>
                  <td style={{
                    ...cellStyle, textAlign: "right", fontFamily: "monospace",
                    fontWeight: 700, color: scoreColor(score), background: scoreBg(score),
                    borderRadius: 3, padding: "2px 6px",
                  }}>
                    {score}
                  </td>
                  <td style={{ ...cellStyle, color: "#6b7280", fontSize: 9 }}>
                    {(a.day_type || "").replace("_", " ")}
                  </td>
                  <td style={{
                    ...cellStyle, textAlign: "right", fontFamily: "monospace",
                    color: a.hypothetical_mae_60min_pts != null ? "#ef5350" : "#2d3748",
                  }}>
                    {a.hypothetical_mae_60min_pts != null ? a.hypothetical_mae_60min_pts.toFixed(1) : "\u2014"}
                  </td>
                  <td style={{
                    ...cellStyle, textAlign: "right", fontFamily: "monospace",
                    color: a.hypothetical_mfe_60min_pts != null ? "#22c55e" : "#2d3748",
                  }}>
                    {a.hypothetical_mfe_60min_pts != null ? a.hypothetical_mfe_60min_pts.toFixed(1) : "\u2014"}
                  </td>
                  <td style={{ ...cellStyle, textAlign: "right", color: oc.color, fontWeight: 600 }}>
                    {oc.text}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
