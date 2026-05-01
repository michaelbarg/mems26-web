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
  total_pnl_net_usd: number;
  total_costs_usd: number;
  avg_pnl_per_trade: number;
  best_trade: { setup_id: string; direction: string; pnl_usd: number; close_reason: string } | null;
  worst_trade: { setup_id: string; direction: string; pnl_usd: number; close_reason: string } | null;
}

interface SeqSummary {
  total_executed_in_sim: number;
  total_skipped: number;
  skip_reasons: Record<string, number>;
  sequential_pnl_usd: number;
  sequential_wr: number;
  executed_closed: number;
  executed_open: number;
}

export default function ShadowTradesTodayCard() {
  const [hypoData, setHypoData] = useState<Summary | null>(null);
  const [seqData, setSeqData] = useState<SeqSummary | null>(null);
  const [tab, setTab] = useState<'real' | 'hypo'>('real');

  useEffect(() => {
    const poll = async () => {
      try {
        const [r1, r2] = await Promise.all([
          fetch(`${API}/analytics/setups/today_summary?min_score=70`),
          fetch(`${API}/analytics/setups/sequential_today_summary`),
        ]);
        if (r1.ok) { const j = await r1.json(); if (j.ok) setHypoData(j); }
        if (r2.ok) { const j = await r2.json(); if (j.ok) setSeqData(j); }
      } catch {}
    };
    poll();
    const iv = setInterval(poll, 30000);
    return () => clearInterval(iv);
  }, []);

  if (!hypoData && !seqData) return null;

  const seqPnl = seqData?.sequential_pnl_usd ?? 0;
  const seqWr = seqData?.sequential_wr ?? 0;
  const seqClosed = seqData?.executed_closed ?? 0;
  const seqOpen = seqData?.executed_open ?? 0;
  const seqTotal = seqData?.total_executed_in_sim ?? 0;

  const tabBtn = (id: 'real' | 'hypo', label: string, color: string) => (
    <button onClick={() => setTab(id)} style={{
      fontSize: 10, padding: "2px 8px", borderRadius: 3, border: "none", cursor: "pointer",
      background: tab === id ? color : "#1e2738",
      color: tab === id ? "#fff" : "#6b7280", fontWeight: tab === id ? 700 : 400,
    }}>{label}</button>
  );

  return (
    <div style={{ background: "#0d1117", border: "1px solid #1e2738", borderRadius: 6, padding: "8px 12px" }}>
      {/* Header with tabs */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 6 }}>
        <span style={{ fontSize: 13, fontWeight: 700, color: "#e5e7eb" }}>Today&apos;s Trades</span>
        <div style={{ display: "flex", gap: 3 }}>
          {tabBtn('real', 'REAL', '#166534')}
          {tabBtn('hypo', 'HYPO', '#1e3a5f')}
        </div>
      </div>

      {tab === 'real' && seqData && (
        <>
          <div style={{ fontSize: 9, color: "#4b5563", marginBottom: 4 }}>Sequential (1 trade at a time)</div>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr 1fr", gap: 6, marginBottom: 6 }}>
            <div style={{ textAlign: "center" }}>
              <div style={{ fontSize: 10, color: "#6b7280" }}>Trades</div>
              <div style={{ fontSize: 16, fontWeight: 700, color: "#e5e7eb" }}>{seqTotal}</div>
            </div>
            <div style={{ textAlign: "center" }}>
              <div style={{ fontSize: 10, color: "#6b7280" }}>Closed</div>
              <div style={{ fontSize: 16, fontWeight: 700, color: "#e5e7eb" }}>{seqClosed}</div>
            </div>
            <div style={{ textAlign: "center" }}>
              <div style={{ fontSize: 10, color: "#6b7280" }}>WR</div>
              <div style={{ fontSize: 16, fontWeight: 700, color: seqWr >= 50 ? "#22c55e" : "#ef4444" }}>{seqWr}%</div>
            </div>
            <div style={{ textAlign: "center" }}>
              <div style={{ fontSize: 10, color: "#6b7280" }}>Net P&L</div>
              <div style={{ fontSize: 16, fontWeight: 700, fontFamily: "monospace",
                color: seqPnl > 0 ? "#22c55e" : seqPnl < 0 ? "#ef4444" : "#6b7280" }}>
                {seqPnl >= 0 ? "+" : ""}${seqPnl.toFixed(0)}
              </div>
            </div>
          </div>
          {seqOpen > 0 && <div style={{ fontSize: 10, color: "#6b7280" }}>Open: {seqOpen}</div>}
          {seqData.skip_reasons && Object.keys(seqData.skip_reasons).length > 0 && (
            <div style={{ fontSize: 9, color: "#4b5563", marginTop: 2 }}>
              Skipped: {Object.entries(seqData.skip_reasons).map(([k, v]) => `${k}=${v}`).join(', ')}
            </div>
          )}
        </>
      )}

      {tab === 'hypo' && hypoData && (
        <>
          <div style={{ fontSize: 9, color: "#f59e0b", marginBottom: 4 }}>
            All setups simulated in parallel (hypothetical)
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr 1fr", gap: 6, marginBottom: 6 }}>
            <div style={{ textAlign: "center" }}>
              <div style={{ fontSize: 10, color: "#6b7280" }}>Total</div>
              <div style={{ fontSize: 16, fontWeight: 700, color: "#e5e7eb" }}>{hypoData.total_setups}</div>
            </div>
            <div style={{ textAlign: "center" }}>
              <div style={{ fontSize: 10, color: "#6b7280" }}>Wins</div>
              <div style={{ fontSize: 16, fontWeight: 700, color: "#22c55e" }}>{hypoData.wins}</div>
            </div>
            <div style={{ textAlign: "center" }}>
              <div style={{ fontSize: 10, color: "#6b7280" }}>Losses</div>
              <div style={{ fontSize: 16, fontWeight: 700, color: "#ef4444" }}>{hypoData.losses}</div>
            </div>
            <div style={{ textAlign: "center" }}>
              <div style={{ fontSize: 10, color: "#6b7280" }}>Net</div>
              <div style={{ fontSize: 14, fontWeight: 700, fontFamily: "monospace",
                color: (hypoData.total_pnl_net_usd ?? hypoData.total_pnl_usd) > 0 ? "#22c55e" :
                       (hypoData.total_pnl_net_usd ?? hypoData.total_pnl_usd) < 0 ? "#ef4444" : "#6b7280" }}>
                ${(hypoData.total_pnl_net_usd ?? hypoData.total_pnl_usd).toFixed(0)}
              </div>
            </div>
          </div>
          {hypoData.closed > 0 && (
            <div style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 10, marginBottom: 4 }}>
              <span style={{ color: "#6b7280" }}>WR</span>
              <div style={{ flex: 1, background: "#1e2738", borderRadius: 3, height: 6 }}>
                <div style={{
                  width: `${hypoData.win_rate}%`, background: hypoData.win_rate >= 50 ? "#22c55e" : "#ef4444",
                  height: "100%", borderRadius: 3,
                }} />
              </div>
              <span style={{ color: hypoData.win_rate >= 50 ? "#22c55e" : "#ef4444", fontWeight: 700 }}>
                {hypoData.win_rate}%
              </span>
            </div>
          )}
          <div style={{ fontSize: 9, color: "#4b5563" }}>
            {hypoData.total_setups}/{hypoData.total_all_detected} detected
          </div>
        </>
      )}
    </div>
  );
}
