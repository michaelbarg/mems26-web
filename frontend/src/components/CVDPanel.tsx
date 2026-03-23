// CVDPanel.tsx
"use client";
type Props = { cvd: Record<string, unknown>; bar: Record<string, number> };
export default function CVDPanel({ cvd, bar }: Props) {
  const total = Number(cvd.total ?? 0);
  const d20   = Number(cvd.d20   ?? 0);
  const bull  = Boolean(cvd.bull);
  return (
    <div className="bg-[#0a0a0f] border border-[#1e1e2e] rounded-lg px-3 py-1.5 flex items-center gap-4 text-xs">
      <span className="text-gray-600 text-[9px]">CVD</span>
      <span className={bull ? "text-green-400 font-bold" : "text-red-400 font-bold"}>
        {total > 0 ? "+" : ""}{Math.round(total).toLocaleString()}
      </span>
      <span className="text-gray-600 text-[9px]">20-bar Δ</span>
      <span className={d20 >= 0 ? "text-green-400" : "text-red-400"}>
        {d20 > 0 ? "+" : ""}{Math.round(d20).toLocaleString()}
      </span>
      <span className="text-gray-600 text-[9px]">delta</span>
      <span className={bar.delta >= 0 ? "text-green-400" : "text-red-400"}>
        {bar.delta > 0 ? "+" : ""}{Math.round(bar.delta ?? 0).toLocaleString()}
      </span>
      <span className={`ml-auto text-[9px] font-bold px-2 py-0.5 rounded ${
        bull ? "bg-green-900/20 text-green-400" : "bg-red-900/20 text-red-400"
      }`}>{bull ? "BULLISH" : "BEARISH"}</span>
    </div>
  );
}
