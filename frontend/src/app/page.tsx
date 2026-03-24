"use client";
import { useEffect, useState } from "react";
import TradingChart   from "@/components/TradingChart";
import TrafficLight   from "@/components/TrafficLight";
import SignalCard     from "@/components/SignalCard";
import LevelsBadges   from "@/components/LevelsBadges";
import DailyTracker   from "@/components/DailyTracker";
import ReversalStatus from "@/components/ReversalStatus";
import CVDPanel       from "@/components/CVDPanel";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "https://mems26-web.onrender.com";

export type Signal = {
  direction: "LONG"|"SHORT"|"NO_TRADE"; 
  score: number;
  confidence: "LOW"|"MEDIUM"|"HIGH"|"ULTRA";
  entry: number; stop: number; target1: number; target2: number; target3: number;
  risk_pts: number; rationale: string; tl_color: "red"|"orange"|"green"|"green_bright"; ts: number;
};

export type MarketUpdate = {
  type: string; ts: number; price: number; session: string; ses_min: number;
  features: Record<string,any>; woodi: Record<string,number>; levels: Record<string,number>;
  cvd: Record<string,any>; bar: Record<string,number>;
  signal: Signal|null; daily_stats: { trades_taken: number; trades_remaining: number };
};

function useMarketPolling() {
  const [update, setUpdate] = useState<MarketUpdate|null>(null);
  const [connected, setConnected] = useState(false);

  useEffect(() => {
    let active = true;
    const poll = async () => {
      while (active) {
        try {
          // פנייה לכתובת המלאה שמכילה את כל הנתונים (מחיר + סיגנלים + CVD)
          const response = await fetch(`${API_URL}/market/latest`);
          if (response.ok) {
            const data = await response.json();
            if (data.type === "market_update") {
              setConnected(true);
              setUpdate(data);
            }
          } else {
            setConnected(false);
          }
        } catch (err) {
          setConnected(false);
        }
        await new Promise(r => setTimeout(r, 2000));
      }
    };
    poll();
    return () => { active = false; };
  }, []);

  return { update, connected };
}

export default function Dashboard() {
  const { update, connected } = useMarketPolling();
  const [priceHistory, setPriceHistory] = useState<number[]>([]);

  useEffect(() => {
    if (update?.price) {
      setPriceHistory(prev => [...prev, update.price].slice(-200));
    }
  }, [update]);

  // חילוץ נתונים להצגה
  const price = update?.price ?? 0;
  const session = update?.session ?? "—";
  const sesMin = update?.ses_min ?? -1;
  const bar = update?.bar ?? {};
  const signal = update?.signal ?? null;
  const score = signal?.score ?? 0;

  return (
    <main className="min-h-screen bg-[#0a0a0f] text-white p-3 flex flex-col gap-3 font-mono">
      {/* Header */}
      <div className="flex items-center justify-between px-3 py-2 bg-[#111118] rounded-lg border border-[#1e1e2e]">
        <span className="font-bold text-sm tracking-widest">MEMS26 · AI TRADER</span>
        <div className="flex items-center gap-4 text-xs text-gray-400">
          <span className={connected ? "text-green-400" : "text-red-400"}>
            {connected ? "● LIVE" : "○ CONNECTING..."}
          </span>
          <span suppressHydrationWarning>
            {new Date().toLocaleTimeString("he-IL", {timeZone: "Asia/Jerusalem"})} IST
          </span>
        </div>
      </div>

      <div className="grid grid-cols-[1fr_92px] gap-3">
        {/* Main Content */}
        <div className="flex flex-col gap-3">
          <div className="flex items-center gap-4 px-2 text-xs text-gray-400">
            <span className="text-white text-base font-bold">{price ? price.toLocaleString() : "—"}</span>
            <span>O <b className="text-white">{bar.o?.toFixed(2) ?? "—"}</b></span>
            <span>H <b className="text-green-400">{bar.h?.toFixed(2) ?? "—"}</b></span>
            <span>L <b className="text-red-400">{bar.l?.toFixed(2) ?? "—"}</b></span>
            <span className={`text-[10px] px-2 py-0.5 rounded font-bold ${session.includes("SESSION") ? "text-green-400 bg-green-900/20" : "text-gray-500 bg-gray-900/20"}`}>
              {session} {sesMin >= 0 ? `${sesMin}m` : ""}
            </span>
          </div>

          <TradingChart 
            priceHistory={priceHistory} 
            signal={signal} 
            woodi={update?.woodi ?? {}} 
            levels={update?.levels ?? {}} 
            features={update?.features ?? {}} 
          />
          
          <CVDPanel cvd={update?.cvd ?? {}} bar={bar} />
          <LevelsBadges price={price} woodi={update?.woodi ?? {}} levels={update?.levels ?? {}} features={update?.features ?? {}} />

          <div className="bg-[#111118] rounded-lg border-l-4 border-[#7f77dd] px-3 py-2 text-xs text-gray-400">
            <div className="text-[10px] text-[#7f77dd] font-bold tracking-widest mb-1">CLAUDE AI</div>
            {signal ? <span>{signal.rationale}</span> : <span>Monitoring MEMS26 active.</span>}
          </div>
        </div>

        {/* Sidebar */}
        <div className="flex flex-col gap-3">
          <TrafficLight color={signal?.tl_color ?? (connected ? "orange" : "red")} score={score} signal={signal} sesMin={sesMin} />
          <DailyTracker daily={update?.daily_stats ?? {trades_taken: 0, trades_remaining: 3}} />
          <ReversalStatus features={update?.features ?? {}} sesMin={sesMin} />
        </div>
      </div>
      
      <SignalCard signal={signal} />
    </main>
  );
}
