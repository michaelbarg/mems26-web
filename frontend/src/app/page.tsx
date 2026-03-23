// frontend/src/app/page.tsx
// Next.js 14 App Router — Dashboard ראשי

"use client";
import { useEffect, useRef, useState, useCallback } from "react";
import TradingChart     from "@/components/TradingChart";
import TrafficLight     from "@/components/TrafficLight";
import SignalCard       from "@/components/SignalCard";
import LevelsBadges     from "@/components/LevelsBadges";
import DailyTracker     from "@/components/DailyTracker";
import ReversalStatus   from "@/components/ReversalStatus";
import CVDPanel         from "@/components/CVDPanel";

const WS_URL = process.env.NEXT_PUBLIC_API_WS_URL || "wss://mems26-api.onrender.com/ws";

// ─────────────────────────────────────────────
//  Types
// ─────────────────────────────────────────────
export type Signal = {
  direction:  "LONG" | "SHORT" | "NO_TRADE";
  score:      number;
  confidence: "LOW" | "MEDIUM" | "HIGH" | "ULTRA";
  entry:      number;
  stop:       number;
  target1:    number;
  target2:    number;
  target3:    number;
  risk_pts:   number;
  rationale:  string;
  tl_color:   "red" | "orange" | "green" | "green_bright";
  ts:         number;
};

export type MarketUpdate = {
  type:        string;
  ts:          number;
  price:       number;
  session:     string;
  ses_min:     number;
  features:    Record<string, unknown>;
  woodi:       Record<string, number>;
  levels:      Record<string, number>;
  cvd:         Record<string, unknown>;
  bar:         Record<string, number>;
  signal:      Signal | null;
  daily_stats: { trades_taken: number; trades_remaining: number };
};

// ─────────────────────────────────────────────
//  Hook: WebSocket connection
// ─────────────────────────────────────────────
function useMarketWS() {
  const ws = useRef<WebSocket | null>(null);
  const [update, setUpdate] = useState<MarketUpdate | null>(null);
  const [connected, setConnected] = useState(false);
  const pingRef = useRef<ReturnType<typeof setInterval>>();

  const connect = useCallback(() => {
    if (ws.current?.readyState === WebSocket.OPEN) return;

    const socket = new WebSocket(WS_URL);
    ws.current = socket;

    socket.onopen = () => {
      setConnected(true);
      // ping every 25s to keep alive
      pingRef.current = setInterval(() => {
        if (socket.readyState === WebSocket.OPEN) socket.send("ping");
      }, 25_000);
    };

    socket.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data);
        if (data === "pong") return;
        setUpdate(data);
      } catch {}
    };

    socket.onclose = () => {
      setConnected(false);
      clearInterval(pingRef.current);
      // Reconnect after 3s
      setTimeout(connect, 3_000);
    };

    socket.onerror = () => socket.close();
  }, []);

  useEffect(() => {
    connect();
    return () => {
      clearInterval(pingRef.current);
      ws.current?.close();
    };
  }, [connect]);

  return { update, connected };
}

// ─────────────────────────────────────────────
//  Score color
// ─────────────────────────────────────────────
function scoreColor(score: number): string {
  if (score <= 4) return "#ef4444";
  if (score <= 6) return "#f59e0b";
  if (score <= 8) return "#22c55e";
  return "#16a34a";
}

// ─────────────────────────────────────────────
//  Page
// ─────────────────────────────────────────────
export default function Dashboard() {
  const { update, connected } = useMarketWS();
  const [signal, setSignal] = useState<Signal | null>(null);
  const [priceHistory, setPriceHistory] = useState<number[]>([]);

  // Keep latest non-null signal
  useEffect(() => {
    if (update?.signal) setSignal(update.signal);
    if (update?.price) {
      setPriceHistory(prev => {
        const next = [...prev, update.price];
        return next.slice(-200);
      });
    }
  }, [update]);

  const price      = update?.price ?? 0;
  const session    = update?.session ?? "—";
  const sesMin     = update?.ses_min ?? -1;
  const features   = update?.features ?? {};
  const woodi      = update?.woodi ?? {};
  const levels     = update?.levels ?? {};
  const cvd        = update?.cvd ?? {};
  const bar        = update?.bar ?? {};
  const daily      = update?.daily_stats ?? { trades_taken: 0, trades_remaining: 3 };
  const tlColor    = signal?.tl_color ?? (connected ? "orange" : "red");
  const score      = signal?.score ?? 0;

  return (
    <main className="min-h-screen bg-[#0a0a0f] text-white p-3 flex flex-col gap-3 font-mono">

      {/* ── Top bar ── */}
      <div className="flex items-center justify-between px-3 py-2 bg-[#111118] rounded-lg border border-[#1e1e2e]">
        <span className="font-bold text-sm tracking-widest text-white">MEMS26 · AI TRADER</span>
        <div className="flex items-center gap-4 text-xs text-gray-400">
          <span className={connected ? "text-green-400" : "text-red-400"}>
            {connected ? "● LIVE" : "○ RECONNECTING"}
          </span>
          <span>{new Date().toLocaleTimeString("he-IL", { timeZone: "Asia/Jerusalem" })} IST</span>
        </div>
      </div>

      {/* ── Main grid ── */}
      <div className="grid grid-cols-[1fr_92px] gap-3">

        {/* ── Left: chart + panels ── */}
        <div className="flex flex-col gap-3">

          {/* Price bar */}
          <div className="flex items-center gap-4 px-2 text-xs text-gray-400">
            <span className="text-white text-base font-bold">
              {price ? price.toLocaleString("en", { minimumFractionDigits: 2 }) : "—"}
            </span>
            <span>O <b className="text-white">{bar.o?.toFixed(2) ?? "—"}</b></span>
            <span>H <b className="text-green-400">{bar.h?.toFixed(2) ?? "—"}</b></span>
            <span>L <b className="text-red-400">{bar.l?.toFixed(2) ?? "—"}</b></span>
            <span>Vol <b className="text-white">{bar.v ? (bar.v/1000).toFixed(1)+"K" : "—"}</b></span>
            <span className="ml-2 px-2 py-0.5 rounded text-[10px] font-bold"
              style={{ background: `${scoreColor(score)}22`, color: scoreColor(score) }}>
              Score: {score}/10
            </span>
            <span className={`text-[10px] px-2 py-0.5 rounded font-bold
              ${session === "AM_SESSION" || session === "PM_SESSION" ? "text-green-400 bg-green-900/20"
              : session === "OPEN" ? "text-yellow-400 bg-yellow-900/20"
              : "text-gray-500 bg-gray-900/20"}`}>
              {session} {sesMin >= 0 ? `${sesMin}m` : ""}
            </span>
          </div>

          {/* Chart */}
          <TradingChart
            priceHistory={priceHistory}
            signal={signal}
            woodi={woodi}
            levels={levels}
            features={features as Record<string, number | string | boolean>}
          />

          {/* CVD Panel */}
          <CVDPanel cvd={cvd} bar={bar} />

          {/* Levels badges */}
          <LevelsBadges price={price} woodi={woodi} levels={levels} features={features} />

          {/* AI box */}
          <div className="bg-[#111118] rounded-lg border-l-4 border-[#7f77dd] px-3 py-2 text-xs text-gray-400">
            <div className="text-[10px] text-[#7f77dd] font-bold tracking-widest mb-1">CLAUDE AI</div>
            {signal
              ? <span>{signal.rationale}</span>
              : <span>Monitoring MEMS26 — CVD + TPO + Woodi + Rev 15/22 active.</span>
            }
          </div>

        </div>

        {/* ── Right: traffic light + daily ── */}
        <div className="flex flex-col gap-3">
          <TrafficLight color={tlColor} score={score} signal={signal} sesMin={sesMin} />
          <DailyTracker daily={daily} />
          <ReversalStatus features={features as Record<string, string | number>} sesMin={sesMin} />
        </div>
      </div>

      {/* ── Signal card ── */}
      <SignalCard signal={signal} />

    </main>
  );
}
