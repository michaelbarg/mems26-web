// frontend/src/app/page.tsx - Polling mode
"use client";
import { useEffect, useState } from "react";
import TradingChart   from "@/components/TradingChart";
import TrafficLight   from "@/components/TrafficLight";
import SignalCard     from "@/components/SignalCard";
import LevelsBadges  from "@/components/LevelsBadges";
import DailyTracker  from "@/components/DailyTracker";
import ReversalStatus from "@/components/ReversalStatus";
import CVDPanel       from "@/components/CVDPanel";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "https://mems26-web.onrender.com";

export type Signal = {
  direction: "LONG"|"SHORT"|"NO_TRADE"; score: number;
  confidence: "LOW"|"MEDIUM"|"HIGH"|"ULTRA";
  entry: number; stop: number; target1: number; target2: number; target3: number;
  risk_pts: number; rationale: string; tl_color: "red"|"orange"|"green"|"green_bright"; ts: number;
};
export type MarketUpdate = {
  type: string; ts: number; price: number; session: string; ses_min: number;
  features: Record<string,unknown>; woodi: Record<string,number>; levels: Record<string,number>;
  cvd: Record<string,unknown>; bar: Record<string,number>;
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
          const [hRes, sRes] = await Promise.all([fetch(`${API_URL}/health`), fetch(`${API_URL}/signals/latest`)]);
          if (hRes.ok) {
            const h = await hRes.json();
            const s = sRes.ok ? await sRes.json() : null;
            const sig: Signal|null = s?.direction ? s : null;
            if (h.last_price) {
              setConnected(true);
              setUpdate(prev => ({
                type:"market_update", ts:Date.now(), price:h.last_price,
                session: prev?.session??"—", ses_min: prev?.ses_min??-1,
                features: prev?.features??{}, woodi: prev?.woodi??{},
                levels: prev?.levels??{}, cvd: prev?.cvd??{}, bar: prev?.bar??{},
                signal: sig??prev?.signal??null,
                daily_stats:{ trades_taken:h.trades_today??0, trades_remaining:3-(h.trades_today??0) },
              }));
            } else { setConnected(false); }
          } else { setConnected(false); }
        } catch { setConnected(false); }
        await new Promise(r => setTimeout(r, 2000));
      }
    };
    poll();
    return () => { active = false; };
  }, []);
  return { update, connected };
}

function scoreColor(s: number) {
  if (s <= 4) return "#ef4444"; if (s <= 6) return "#f59e0b";
  if (s <= 8) return "#22c55e"; return "#16a34a";
}

export default function Dashboard() {
  const { update, connected } = useMarketPolling();
  const [signal, setSignal] = useState<Signal|null>(null);
  const [priceHistory, setPriceHistory] = useState<number[]>([]);
  useEffect(() => {
    if (update?.signal) setSignal(update.signal);
    if (update?.price) setPriceHistory(prev => [...prev, update.price].slice(-200));
  }, [update]);
  const price=update?.price??0, session=update?.session??"—", sesMin=update?.ses_min??-1;
  const features=update?.features??{}, woodi=update?.woodi??{}, levels=update?.levels??{};
  const cvd=update?.cvd??{}, bar=update?.bar??{};
  const daily=update?.daily_stats??{trades_taken:0,trades_remaining:3};
  const tlColor=signal?.tl_color??(connected?"orange":"red"), score=signal?.score??0;
  return (
    <main className="min-h-screen bg-[#0a0a0f] text-white p-3 flex flex-col gap-3 font-mono">
      <div className="flex items-center justify-between px-3 py-2 bg-[#111118] rounded-lg border border-[#1e1e2e]">
        <span className="font-bold text-sm tracking-widest">MEMS26 · AI TRADER</span>
        <div className="flex items-center gap-4 text-xs text-gray-400">
          <span className={connected?"text-green-400":"text-red-400"}>{connected?"● LIVE":"○ CONNECTING..."}</span>
          <span>{new Date().toLocaleTimeString("he-IL",{timeZone:"Asia/Jerusalem"})} IST</span>
        </div>
      </div>
      <div className="grid grid-cols-[1fr_92px] gap-3">
        <div className="flex flex-col gap-3">
          <div className="flex items-center gap-4 px-2 text-xs text-gray-400">
            <span className="text-white text-base font-bold">{price?price.toLocaleString("en",{minimumFractionDigits:2}):"—"}</span>
            <span>O <b className="text-white">{bar.o?.toFixed(2)??"—"}</b></span>
            <span>H <b className="text-green-400">{bar.h?.toFixed(2)??"—"}</b></span>
            <span>L <b className="text-red-400">{bar.l?.toFixed(2)??"—"}</b></span>
            <span className="ml-2 px-2 py-0.5 rounded text-[10px] font-bold" style={{background:`${scoreColor(score)}22`,color:scoreColor(score)}}>Score: {score}/10</span>
            <span className={`text-[10px] px-2 py-0.5 rounded font-bold ${session==="AM_SESSION"||session==="PM_SESSION"?"text-green-400 bg-green-900/20":session==="OPEN"?"text-yellow-400 bg-yellow-900/20":"text-gray-500 bg-gray-900/20"}`}>{session} {sesMin>=0?`${sesMin}m`:""}</span>
          </div>
          <TradingChart priceHistory={priceHistory} signal={signal} woodi={woodi} levels={levels} features={features as Record<string,number|string|boolean>} />
          <CVDPanel cvd={cvd} bar={bar} />
          <LevelsBadges price={price} woodi={woodi} levels={levels} features={features} />
          <div className="bg-[#111118] rounded-lg border-l-4 border-[#7f77dd] px-3 py-2 text-xs text-gray-400">
            <div className="text-[10px] text-[#7f77dd] font-bold tracking-widest mb-1">CLAUDE AI</div>
            {signal?<span>{signal.rationale}</span>:<span>Monitoring MEMS26 — CVD + TPO + Woodi + Rev 15/22 active.</span>}
          </div>
        </div>
        <div className="flex flex-col gap-3">
          <TrafficLight color={tlColor} score={score} signal={signal} sesMin={sesMin} />
          <DailyTracker daily={daily} />
          <ReversalStatus features={features as Record<string,string|number>} sesMin={sesMin} />
        </div>
      </div>
      <SignalCard signal={signal} />
    </main>
  );
}
