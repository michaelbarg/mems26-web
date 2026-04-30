"use client";
import { useState, useEffect } from "react";

const API = "https://mems26-web.onrender.com";

interface Summary {
  date: string;
  total_setups: number;
  total_all_detected: number;
  min_score_filter: number;
  closed: number;
  still_open: number;
  wins: number;
  losses: number;
  breakeven: number;
  win_rate: number;
  total_pnl_usd: number;
  avg_pnl_per_trade: number;
  best_trade: { setup_id: string; direction: string; pnl_usd: number; close_reason: string } | null;
  worst_trade: { setup_id: string; direction: string; pnl_usd: number; close_reason: string } | null;
}

export default function ShadowTradesTodayCard() {
  const [data, setData] = useState<Summary | null>(null);
  const [execOnly, setExecOnly] = useState(() => {
    if (typeof window !== 'undefined') return localStorage.getItem('mems26_view_mode') !== 'all';
    return true;
  });

  useEffect(() => {
    const poll = async () => {
      try {
        const ms = execOnly ? 70 : 0;
        const r = await fetch(`${API}/analytics/setups/today_summary?min_score=${ms}`);
        if (r.ok) {
          const j = await r.json();
          if (j.ok) setData(j);
        }
      } catch {}
    };
    poll();
    const iv = setInterval(poll, 30000);
    return () => clearInterval(iv);
  }, [execOnly]);

  const toggleMode = () => {
    const next = !execOnly;
    setExecOnly(next);
    if (typeof window !== 'undefined') localStorage.setItem('mems26_view_mode', next ? 'exec' : 'all');
  };

  if (!data) return null;

  const pnlColor = data.total_pnl_usd > 0 ? "#22c55e" : data.total_pnl_usd < 0 ? "#ef4444" : "#6b7280";

  return (
    <div style={{ background: "#0d1117", border: "1px solid #1e2738", borderRadius: 6, padding: "8px 12px" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 6 }}>
        <span style={{ fontSize: 13, fontWeight: 700, color: "#e5e7eb" }}>Today Shadow Trades</span>
        <div style={{ display: "flex", gap: 4, alignItems: "center" }}>
          <button onClick={toggleMode} style={{
            fontSize: 9, padding: "2px 6px", borderRadius: 3, border: "none", cursor: "pointer",
            background: execOnly ? "#1a2e1a" : "#1e2738", color: execOnly ? "#22c55e" : "#6b7280",
          }}>{execOnly ? "Executed Only" : "All Detected"}</button>
          <span style={{ fontSize: 9, color: "#4b5563" }}
            title={`${data.total_setups} shown of ${data.total_all_detected} total. ${execOnly ? 'Score >= 70 = would execute in LIVE.' : 'All detections shown.'}`}>
            {data.total_setups}/{data.total_all_detected}
          </span>
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr 1fr", gap: 6, marginBottom: 6 }}>
        <div style={{ textAlign: "center" }}>
          <div style={{ fontSize: 10, color: "#6b7280" }}>Total</div>
          <div style={{ fontSize: 16, fontWeight: 700, color: "#e5e7eb" }}>{data.total_setups}</div>
        </div>
        <div style={{ textAlign: "center" }}>
          <div style={{ fontSize: 10, color: "#6b7280" }}>Wins</div>
          <div style={{ fontSize: 16, fontWeight: 700, color: "#22c55e" }}>{data.wins}</div>
        </div>
        <div style={{ textAlign: "center" }}>
          <div style={{ fontSize: 10, color: "#6b7280" }}>Losses</div>
          <div style={{ fontSize: 16, fontWeight: 700, color: "#ef4444" }}>{data.losses}</div>
        </div>
        <div style={{ textAlign: "center" }}>
          <div style={{ fontSize: 10, color: "#6b7280" }}>Net P&L</div>
          <div style={{ fontSize: 16, fontWeight: 700, color: pnlColor, fontFamily: "monospace" }}>
            {data.total_pnl_usd >= 0 ? "+" : ""}${data.total_pnl_usd.toFixed(0)}
          </div>
        </div>
      </div>

      {data.closed > 0 && (
        <div style={{ marginBottom: 4 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 10 }}>
            <span style={{ color: "#6b7280" }}>WR</span>
            <div style={{ flex: 1, background: "#1e2738", borderRadius: 3, height: 6 }}>
              <div style={{
                width: `${data.win_rate}%`, background: data.win_rate >= 50 ? "#22c55e" : "#ef4444",
                height: "100%", borderRadius: 3, transition: "width 0.5s",
              }} />
            </div>
            <span style={{ color: data.win_rate >= 50 ? "#22c55e" : "#ef4444", fontWeight: 700 }}>
              {data.win_rate}%
            </span>
          </div>
        </div>
      )}

      <div style={{ display: "flex", gap: 8, fontSize: 10, color: "#6b7280" }}>
        <span>Open: {data.still_open}</span>
        <span>Closed: {data.closed}</span>
        <span>Avg: ${data.avg_pnl_per_trade.toFixed(0)}</span>
      </div>
    </div>
  );
}
