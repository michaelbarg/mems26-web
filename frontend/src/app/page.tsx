"use client";
import { useEffect, useState } from "react";
import TradingChart   from "@/components/TradingChart";
import TrafficLight   from "@/components/TrafficLight";
import SignalCard     from "@/components/SignalCard";
import LevelsBadges   from "@/components/LevelsBadges";
import DailyTracker   from "@/components/DailyTracker";
import ReversalStatus from "@/components/ReversalStatus";
import CVDPanel       from "@/components/CVDPanel";

const API_URL = "https://mems26-web.onrender.com";

export default function Dashboard() {
  const [update, setUpdate] = useState<any>(null);
  const [connected, setConnected] = useState(false);
  const [priceHistory, setPriceHistory] = useState<number[]>([]);

  // מנגנון משיכת נתונים (Polling)
  useEffect(() => {
    let active = true;
    const poll = async () => {
      while (active) {
        try {
          // הוספת סימן שאלה וזמן כדי למנוע מהדפדפן לשמור נתונים ישנים (Cache)
          const res = await fetch(`${API_URL}/market/latest?t=${Date.now()}`, { cache: 'no-store' });
          if (res.ok) {
            const data = await res.json();
            if (data.bar) {
              setConnected(true);
              setUpdate(data);
              setPriceHistory(prev => [...prev, data.bar.c].slice(-200));
            }
          }
        } catch (e) {
          setConnected(false);
        }
        await new Promise(r => setTimeout(r, 2000)); // רענון כל 2 שניות
      }
    };
    poll();
    return () => { active = false; };
  }, []);

  const price = update?.bar?.c ?? 0;
  const signal = update?.signal ?? null;

  return (
    <main className="min-h-screen bg-[#0a0a0f] text-white p-3 flex flex-col gap-3 font-mono">
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
        <div className="flex flex-col gap-3">
          <div className="flex items-center gap-4 px-2 text-xs text-gray-400">
            <span className="text-white text-base font-bold">{price ? price.toLocaleString() : "—"}</span>
            <span>O <b className="text-white">{update?.bar?.o ?? "—"}</b></span>
            <span>H <b className="text-green-400">{update?.bar?.h ?? "—"}</b></span>
            <span>L <b className="text-red-400">{update?.bar?.l ?? "—"}</b></span>
          </div>

          <TradingChart 
            priceHistory={priceHistory} 
            signal={signal} 
            woodi={update?.woodi ?? {}} 
            levels={update?.levels ?? {}} 
            features={update?.features ?? {}} 
          />
          <CVDPanel cvd={update?.cvd ?? {}} bar={update?.bar ?? {}} />
          <LevelsBadges price={price} woodi={update?.woodi ?? {}} levels={update?.levels ?? {}} features={update?.features ?? {}} />
        </div>

        <div className="flex flex-col gap-3">
          <TrafficLight color={signal?.tl_color ?? (connected ? "orange" : "red")} score={signal?.score ?? 0} signal={signal} sesMin={update?.session?.min ?? -1} />
          <DailyTracker daily={update?.daily_stats ?? {trades_taken: 0, trades_remaining: 3}} />
          <ReversalStatus features={update?.features ?? {}} sesMin={update?.session?.min ?? -1} />
        </div>
      </div>
      <SignalCard signal={signal} />
    </main>
  );
}
