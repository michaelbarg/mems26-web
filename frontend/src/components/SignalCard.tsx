// frontend/src/components/SignalCard.tsx
"use client";
import { Signal } from "@/types/signal";

type Props = { signal: Signal | null };

const scoreColors: Record<string, { bg: string; border: string; text: string }> = {
  LOW:    { bg: "rgba(239,68,68,.05)",    border: "#ef4444", text: "#ef4444" },
  MEDIUM: { bg: "rgba(245,158,11,.05)",   border: "#f59e0b", text: "#f59e0b" },
  HIGH:   { bg: "rgba(34,197,94,.05)",    border: "#22c55e", text: "#22c55e" },
  ULTRA:  { bg: "rgba(16,185,129,.08)",   border: "#10b981", text: "#10b981" },
};

function rr(entry: number, target: number, stop: number, isLong: boolean): string {
  const risk   = Math.abs(entry - stop);
  const reward = Math.abs(target - entry);
  if (!risk) return "—";
  return (reward / risk).toFixed(1) + ":1";
}

export default function SignalCard({ signal }: Props) {
  if (!signal || signal.direction === "NO_TRADE") {
    return (
      <div className="bg-[#111118] rounded-xl border border-[#1e1e2e] p-3 text-xs text-gray-500">
        <span className="font-bold text-gray-600 mr-2">—</span>
        AWAITING SIGNAL — waiting for confluence 7+
      </div>
    );
  }

  const isLong  = signal.direction === "LONG";
  const colors  = scoreColors[signal.confidence] ?? scoreColors.LOW;
  const riskUSD = (signal.risk_pts * 5 * 3).toFixed(0);
  const t1USD   = (Math.abs(signal.target1 - signal.entry) * 5 * 3).toFixed(0);
  const t2USD   = (Math.abs(signal.target2 - signal.entry) * 5 * 3).toFixed(0);
  const t3USD   = (Math.abs(signal.target3 - signal.entry) * 5 * 3).toFixed(0);

  return (
    <div
      className="rounded-xl border p-3"
      style={{ background: colors.bg, borderColor: colors.border }}
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <span className="font-bold text-sm" style={{ color: colors.text }}>
          {isLong ? "▲" : "▼"} {signal.direction} MEMS26 × 3
        </span>
        <span
          className="text-[10px] font-bold px-2 py-1 rounded"
          style={{ background: colors.border + "22", color: colors.text }}
        >
          {signal.score}/10 · {signal.confidence}
        </span>
      </div>

      {/* TP/SL Ladder */}
      <div className="flex flex-col gap-1 mb-3">
        {/* T3 */}
        <div className="grid grid-cols-[52px_1fr_68px_52px] gap-2 items-center bg-green-900/10 border border-green-500/25 rounded px-2 py-1">
          <span className="text-[10px] font-bold text-green-400">TARGET 3</span>
          <div className="h-1 bg-gray-800 rounded overflow-hidden">
            <div className="h-full bg-green-500 rounded" style={{ width: "100%" }} />
          </div>
          <span className="text-xs font-bold text-green-400 text-right">{signal.target3.toFixed(2)}</span>
          <span className="text-[9px] text-gray-500 text-right">
            {rr(signal.entry, signal.target3, signal.stop, isLong)} · +${t3USD}
          </span>
        </div>
        {/* T2 */}
        <div className="grid grid-cols-[52px_1fr_68px_52px] gap-2 items-center bg-green-900/10 border border-green-500/20 rounded px-2 py-1">
          <span className="text-[10px] font-bold text-green-400">TARGET 2</span>
          <div className="h-1 bg-gray-800 rounded overflow-hidden">
            <div className="h-full bg-green-500/70 rounded" style={{ width: "70%" }} />
          </div>
          <span className="text-xs font-bold text-green-400/80 text-right">{signal.target2.toFixed(2)}</span>
          <span className="text-[9px] text-gray-500 text-right">
            {rr(signal.entry, signal.target2, signal.stop, isLong)} · +${t2USD}
          </span>
        </div>
        {/* T1 */}
        <div className="grid grid-cols-[52px_1fr_68px_52px] gap-2 items-center bg-green-900/10 border border-green-500/15 rounded px-2 py-1">
          <span className="text-[10px] font-bold text-green-400/70">TARGET 1</span>
          <div className="h-1 bg-gray-800 rounded overflow-hidden">
            <div className="h-full bg-green-400/50 rounded" style={{ width: "45%" }} />
          </div>
          <span className="text-xs font-bold text-green-400/60 text-right">{signal.target1.toFixed(2)}</span>
          <span className="text-[9px] text-gray-500 text-right">
            {rr(signal.entry, signal.target1, signal.stop, isLong)} · +${t1USD}
          </span>
        </div>
        {/* Entry */}
        <div className="grid grid-cols-[52px_1fr_68px_52px] gap-2 items-center bg-amber-900/10 border border-amber-500/40 rounded px-2 py-1">
          <span className="text-[10px] font-bold text-amber-400">ENTRY</span>
          <div className="h-1 bg-gray-800 rounded overflow-hidden">
            <div className="h-full w-0.5 bg-amber-400 mx-auto" />
          </div>
          <span className="text-sm font-bold text-amber-400 text-right">{signal.entry.toFixed(2)}</span>
          <span className="text-[9px] text-gray-500 text-right">limit</span>
        </div>
        {/* Stop */}
        <div className="grid grid-cols-[52px_1fr_68px_52px] gap-2 items-center bg-red-900/10 border border-red-500/25 rounded px-2 py-1">
          <span className="text-[10px] font-bold text-red-400">STOP</span>
          <div className="h-1 bg-gray-800 rounded overflow-hidden">
            <div className="h-full bg-red-500/60 rounded" style={{ width: "35%" }} />
          </div>
          <span className="text-xs font-bold text-red-400 text-right">{signal.stop.toFixed(2)}</span>
          <span className="text-[9px] text-gray-500 text-right">
            {signal.risk_pts.toFixed(2)}pts · -${riskUSD}
          </span>
        </div>
      </div>

      {/* Rationale */}
      <div className="text-[10px] text-gray-400 bg-[#0d0d14] rounded px-2 py-1.5">
        ⚡ {signal.rationale}
      </div>
    </div>
  );
}
