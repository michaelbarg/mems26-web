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
  c1_target?: number;
  c2_target?: number;
  c3_target?: number;
  vegas_score?: number;
  tpo_score?: number;
  fvg_score?: number;
  footprint_score?: number;
  score_reasons?: string;
  executed?: boolean;
  be_strategy?: string;
}

const POLL_MS = 30000;
const API_URL = "https://mems26-web.onrender.com";

function fmtTime(ts: number): string {
  if (!ts) return "--";
  const d = new Date(ts * 1000);
  return d.toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit", hour12: false });
}

function fmtPrice(v?: number | null): string {
  if (v == null || v === 0) return "\u2014";
  return v.toFixed(1);
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

function outcomeShort(a: Attempt): { text: string; color: string } {
  const now = Date.now() / 1000;
  if ((now - a.ts) < 3600 && a.hypothetical_mae_60min_pts == null) {
    return { text: "\u23F0", color: "#6b7280" };
  }
  const oc = a.outcome;
  if (oc === "HIT_C1") return { text: "HC1", color: "#22c55e" };
  if (oc === "HIT_STOP") return { text: "STOP", color: "#ef5350" };
  if (oc === "TIMEOUT") return { text: "TO", color: "#9ca3af" };
  if (a.hypothetical_mae_60min_pts != null) return { text: "TO", color: "#9ca3af" };
  return { text: "\u23F0", color: "#6b7280" };
}

interface AttemptsTableProps {
  apiUrl?: string;
}

export default function AttemptsTable({ apiUrl }: AttemptsTableProps) {
  const [attempts, setAttempts] = useState<Attempt[]>([]);
  const [loading, setLoading] = useState(true);
  const [expandedId, setExpandedId] = useState<number | null>(null);
  const base = apiUrl || API_URL;

  useEffect(() => {
    let active = true;
    const poll = async () => {
      try {
        const [scoreRes, outcomeRes] = await Promise.all([
          fetch(`${base}/analytics/attempts/recent_with_score?limit=30`),
          fetch(`${base}/analytics/attempts/with_outcomes?limit=30`),
        ]);
        const scoreData = await scoreRes.json();
        const outcomeData = await outcomeRes.json();
        if (!active) return;

        const outcomeMap = new Map<number, Attempt>();
        for (const a of (outcomeData.attempts || [])) {
          outcomeMap.set(a.id, a);
        }

        const merged: Attempt[] = [];
        for (const a of (scoreData.attempts || [])) {
          const oc = outcomeMap.get(a.id);
          merged.push({ ...a, ...oc, ...a, // a fields take priority for non-outcome fields
            hypothetical_mae_60min_pts: oc?.hypothetical_mae_60min_pts ?? a.hypothetical_mae_60min_pts,
            hypothetical_mfe_60min_pts: oc?.hypothetical_mfe_60min_pts ?? a.hypothetical_mfe_60min_pts,
            outcome: oc?.outcome ?? a.outcome,
          });
        }
        for (const a of (outcomeData.attempts || [])) {
          if (!merged.find(m => m.id === a.id)) merged.push(a);
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

  const cell: React.CSSProperties = {
    padding: "2px 4px", fontSize: 10, borderBottom: "1px solid #1e2738", whiteSpace: "nowrap",
  };

  const headers = ["Time", "Dir", "Score", "Day", "Entry", "Stop", "C1", "C2", "Exec", "Out"];
  const aligns: Record<string, string> = {
    Time: "left", Dir: "left", Day: "left", Exec: "center", Out: "center",
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
              {headers.map(h => (
                <th key={h} style={{
                  ...cell, color: "#4b5563", fontWeight: 600,
                  textAlign: (aligns[h] || "right") as any,
                  borderBottom: "1px solid #2d3748",
                }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {attempts.map(a => {
              const score = a.setup_quality_score ?? a.health_score_at_entry ?? 0;
              const oc = outcomeShort(a);
              const dirColor = a.direction === "LONG" ? "#22c55e" : a.direction === "SHORT" ? "#ef5350" : "#6b7280";
              const dirShort = a.direction === "LONG" ? "\u25B2LG" : "\u25BCSH";
              const expanded = expandedId === a.id;

              return (
                <>
                  <tr key={a.id} onClick={() => setExpandedId(expanded ? null : a.id)}
                    style={{ cursor: "pointer" }}>
                    <td style={{ ...cell, color: "#9ca3af" }}>{fmtTime(a.ts)}</td>
                    <td style={{ ...cell, color: dirColor, fontWeight: 700, fontSize: 9 }}>{dirShort}</td>
                    <td style={{
                      ...cell, textAlign: "right", fontFamily: "monospace",
                      fontWeight: 700, color: scoreColor(score), background: scoreBg(score),
                      borderRadius: 2, padding: "1px 5px",
                    }}>{score}</td>
                    <td style={{ ...cell, color: "#6b7280", fontSize: 8 }}>
                      {(a.day_type || "").replace("_DAY", "").replace("_", " ")}
                    </td>
                    <td style={{ ...cell, textAlign: "right", fontFamily: "monospace", color: "#e5e7eb" }}>
                      {fmtPrice(a.entry_price_hypothetical)}
                    </td>
                    <td style={{ ...cell, textAlign: "right", fontFamily: "monospace", color: "#ef5350" }}>
                      {fmtPrice(a.stop_hypothetical)}
                    </td>
                    <td style={{ ...cell, textAlign: "right", fontFamily: "monospace", color: "#22c55e" }}>
                      {fmtPrice(a.c1_target)}
                    </td>
                    <td style={{ ...cell, textAlign: "right", fontFamily: "monospace", color: "#16a34a" }}>
                      {fmtPrice(a.c2_target)}
                    </td>
                    <td style={{ ...cell, textAlign: "center" }}>
                      {a.executed ? "\u2705" : "\u26AA"}
                    </td>
                    <td style={{ ...cell, textAlign: "center", color: oc.color, fontWeight: 700, fontSize: 9 }}>
                      {oc.text}
                    </td>
                  </tr>
                  {expanded && (
                    <tr key={`${a.id}_detail`}>
                      <td colSpan={10} style={{
                        padding: "4px 8px", background: "#0a0f1a",
                        borderBottom: "1px solid #2d3748", fontSize: 9,
                      }}>
                        <div style={{ display: "flex", gap: 12, flexWrap: "wrap", color: "#9ca3af" }}>
                          <span>Vegas: <b style={{ color: (a.vegas_score || 0) > 0 ? "#22c55e" : "#4b5563" }}>{a.vegas_score ?? "?"}</b></span>
                          <span>TPO: <b style={{ color: (a.tpo_score || 0) > 0 ? "#22c55e" : "#4b5563" }}>{a.tpo_score ?? "?"}</b></span>
                          <span>FVG: <b style={{ color: (a.fvg_score || 0) > 0 ? "#22c55e" : "#4b5563" }}>{a.fvg_score ?? "?"}</b></span>
                          <span>FP: <b style={{ color: (a.footprint_score || 0) > 0 ? "#22c55e" : "#4b5563" }}>{a.footprint_score ?? "?"}</b></span>
                          {a.hypothetical_mae_60min_pts != null && (
                            <span>MAE: <b style={{ color: "#ef5350" }}>{a.hypothetical_mae_60min_pts.toFixed(1)}</b></span>
                          )}
                          {a.hypothetical_mfe_60min_pts != null && (
                            <span>MFE: <b style={{ color: "#22c55e" }}>{a.hypothetical_mfe_60min_pts.toFixed(1)}</b></span>
                          )}
                          {a.be_strategy && (
                            <span>BE: <b>{a.be_strategy.replace(/_/g, " ")}</b></span>
                          )}
                        </div>
                        {a.score_reasons && (
                          <div style={{ color: "#6b7280", marginTop: 2, fontSize: 8, lineHeight: 1.4 }}>
                            {a.score_reasons}
                          </div>
                        )}
                      </td>
                    </tr>
                  )}
                </>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
