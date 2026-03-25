// frontend/src/app/page.tsx
"use client";
import { useEffect, useState } from "react";
import TradingChart     from "@/components/TradingChart";
import TrafficLight     from "@/components/TrafficLight";
import SignalCard       from "@/components/SignalCard";
import LevelsBadges     from "@/components/LevelsBadges";
import DailyTracker     from "@/components/DailyTracker";
import ReversalStatus   from "@/components/ReversalStatus";
import CVDPanel         from "@/components/CVDPanel";

const API_URL = "https://mems26-web.onrender.com";

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

function scoreColor(score: number): string {
  if (score <= 4) return "#ef4444";
  if (score <= 6) return "#f59e0b";
  if (score <= 8) return "#22c55e";
  return "#16a34a";
}

export default function Dashboard() {
  const [update, setUpdate]           = useState<any>(null);
  const [connected, setConnected]     = useState(false);
  const [signal, setSignal]           = useState<Signal | null>(null);
  const [priceHistory, setPriceHistory] = useState<number[]>([]);

  useEffect(() => {
    let active = true;
    const poll = async () => {
      while (active) {
        try {
          const res = await fetch(`${API_URL}/market/latest?t=${Date.now()}`, { cache: "no-store" });
          if (res.ok) {
            const data = await res.json();
            if (data?.bar) {
              setConnected(true);
              setUpdate(data);
              if (data.signal) setSignal(data.signal);
              const price = data.bar.c;
              if (price) setPriceHistory(prev => [...prev, price].slice(-200));
            }
          }
        } catch {
          setConnected(false);
        }
        await new Promise(r => setTimeout(r, 2000));
      }
    };
    poll();
    return () => { active = false; };
  }, []);

  const price    = update?.bar?.c ?? 0;
  const session  = update?.session?.phase ?? "—";
  const sesMin   = update?.session?.min ?? -1;
  const features = update?.features ?? {};
  const woodi    = update?.woodi ?? {};
  const levels   = update?.levels ?? {};
  const cvd      = update?.cvd ?? {};
  const bar      = update?.bar ?? {};
  const daily    = update?.daily_stats ?? { trades_taken: 0, trades_remaining: 3 };
  const tlColor  = signal?.tl_color ?? (connected ? "orange" : "red");
  const score    = signal?.score ?? 0;

  return (
    <main className="min-h-screen bg-[#0a0a0f] text-white p-3 flex flex-col gap-3 font-mono">

      {/* ── Top bar ── */}
      <div className="flex items-center justify-between px-3 py-2 bg-[#111118] rounded-lg border border-[#1e1e2e]">
        <span className="font-bold text-sm tracking-widest text-white">MEMS26 · AI TRADER</span>
        <div className="flex items-center gap-4 text-xs text-gray-400">
          <span className={connected ? "text-green-400" : "text-red-400"}>
            {connected ? "● LIVE" : "○ CONNECTING..."}
          </span>
          <span suppressHydrationWarning>
            {new Date().toLocaleTimeString("he-IL", { timeZone: "Asia/Jerusalem" })} IST
          </span>
        </div>
      </div>

      {/* ── Main grid ── */}
      <div className="grid grid-cols-[1fr_92px] gap-3">

        {/* ── Left ── */}
        <div className="flex flex-col gap-3">

          {/* Price bar */}
          <div className="flex items-center gap-4 px-2 text-xs text-gray-400">
            <span className="text-white text-base font-bold">
              {price ? price.toLocaleString("en", { minimumFractionDigits: 2 }) : "—"}
            </span>
            <span>O <b className="text-white">{bar.o?.toFixed(2) ?? "—"}</b></span>
            <span>H <b className="text-green-400">{bar.h?.toFixed(2) ?? "—"}</b></span>
            <span>L <b className="text-red-400">{bar.l?.toFixed(2) ?? "—"}</b></span>
            <span>Vol <b className="text-white">{bar.v ? (bar.v / 1000).toFixed(1) + "K" : "—"}</b></span>
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

          <TradingChart
            priceHistory={priceHistory}
            signal={signal}
            woodi={woodi}
            levels={levels}
            features={features as Record<string, number | string | boolean>}
          />

          <CVDPanel cvd={cvd} bar={bar} />

          <LevelsBadges price={price} woodi={woodi} levels={levels} features={features} />

          <div className="bg-[#111118] rounded-lg border-l-4 border-[#7f77dd] px-3 py-2 text-xs text-gray-400">
            <div className="text-[10px] text-[#7f77dd] font-bold tracking-widest mb-1">CLAUDE AI</div>
            {signal
              ? <span>{signal.rationale}</span>
              : <span>Monitoring MEMS26 active.</span>
            }
          </div>
        </div>

        {/* ── Right ── */}
        <div className="flex flex-col gap-3">
          <TrafficLight color={tlColor} score={score} signal={signal} sesMin={sesMin} />
          <DailyTracker daily={daily} />
          <ReversalStatus features={features as Record<string, string | number>} sesMin={sesMin} />
        </div>
      </div>

      <SignalCard signal={signal} />
    </main>
  );
}
