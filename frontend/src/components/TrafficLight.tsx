// frontend/src/components/TrafficLight.tsx
"use client";
import { Signal } from "@/types/signal";
type Props = {
  color: string;
  score: number;
  signal: Signal | null;
  sesMin: number;
};

const CONFIG = {
  red:          { label: "DO NOT TRADE", side: "—",     sideColor: "#555",     labelColor: "#888" },
  orange:       { label: "WAIT",         side: "—",     sideColor: "#555",     labelColor: "#ff9900" },
  green:        { label: "GET IN",       side: "LONG",  sideColor: "#22c55e",  labelColor: "#22c55e" },
  green_bright: { label: "GET IN NOW",   side: "LONG",  sideColor: "#10b981",  labelColor: "#10b981" },
};

export default function TrafficLight({ color, score, signal, sesMin }: Props) {
  const cfg   = CONFIG[color as keyof typeof CONFIG] ?? CONFIG.orange;
  const side  = signal?.direction && signal.direction !== "NO_TRADE" ? signal.direction : cfg.side;
  const sideCol = signal?.direction === "LONG" ? "#22c55e" : signal?.direction === "SHORT" ? "#ef4444" : cfg.sideColor;

  return (
    <div className="bg-[#111118] border border-[#1e1e2e] rounded-xl p-2.5 flex flex-col items-center gap-2">
      <span className="text-[9px] text-gray-600 tracking-widest">SIGNAL</span>

      {/* Light housing */}
      <div className="bg-[#1a1a1a] rounded-xl px-2 py-2 flex flex-col items-center gap-0.5 border border-[#2a2a2a]">
        <div className={`w-7 h-7 rounded-full transition-all duration-400 ${
          color === "red" || color === "orange" || color === "green" || color === "green_bright"
            ? "" : ""
        }`}
          style={{
            background: (color === "red")          ? "#ff2020" :
                        (color === "orange")        ? "#1a0e00" :
                        (color === "green" || color === "green_bright") ? "#001400" : "#2a0000",
            boxShadow:  color === "red" ? "0 0 14px #ff202077" : undefined,
          }}
        />
        <div className="w-7 h-7 rounded-full transition-all duration-400"
          style={{
            background: color === "orange"         ? "#ff9900" :
                        (color === "green" || color === "green_bright") ? "#1a0e00" : "#1a0e00",
            boxShadow:  color === "orange" ? "0 0 14px #ff990077" : undefined,
          }}
        />
        <div className="w-7 h-7 rounded-full transition-all duration-400"
          style={{
            background: color === "green"          ? "#00ee44" :
                        color === "green_bright"   ? "#10b981" : "#001400",
            boxShadow:  (color === "green" || color === "green_bright") ? "0 0 14px #00ee4477" : undefined,
          }}
        />
      </div>

      <span className="text-[9px] font-bold text-center" style={{ color: cfg.labelColor }}>
        {cfg.label}
      </span>

      {/* Side badge */}
      <span className={`text-[9px] font-bold px-2 py-0.5 rounded ${
        side === "LONG"  ? "bg-green-900/20 text-green-400" :
        side === "SHORT" ? "bg-red-900/20 text-red-400"     :
                           "bg-gray-900/20 text-gray-600"
      }`}>{side}</span>

      {/* Score */}
      {score > 0 && (
        <span className="text-base font-bold" style={{
          color: score >= 7 ? "#22c55e" : score >= 5 ? "#f59e0b" : "#ef4444"
        }}>
          {score}<span className="text-[9px] text-gray-600">/10</span>
        </span>
      )}

      {/* Session minute */}
      {sesMin >= 0 && (
        <>
          <span className="text-[9px] text-gray-600 mt-1">session</span>
          <span className="text-sm font-bold text-white">{sesMin}m</span>
        </>
      )}
    </div>
  );
}
