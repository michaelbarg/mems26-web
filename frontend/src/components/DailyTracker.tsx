// frontend/src/components/DailyTracker.tsx
"use client";
type Props = { daily: { trades_taken: number; trades_remaining: number } };
export default function DailyTracker({ daily }: Props) {
  return (
    <div className="bg-[#111118] border border-[#1e1e2e] rounded-xl p-2.5 flex flex-col items-center gap-2">
      <span className="text-[9px] text-gray-600">TODAY</span>
      <div className="flex gap-1.5">
        {[1, 2, 3].map(n => (
          <div key={n} className={`w-6 h-6 rounded-full flex items-center justify-center text-[10px] font-bold border ${
            n <= daily.trades_taken
              ? "border-green-500 text-green-400 bg-green-900/20"
              : n === daily.trades_taken + 1
              ? "border-amber-500 text-amber-400 bg-amber-900/20 animate-pulse"
              : "border-gray-700 text-gray-600"
          }`}>{n}</div>
        ))}
      </div>
      <span className="text-[9px] text-gray-500">
        {daily.trades_remaining > 0 ? `${daily.trades_remaining} left` : "Done ✓"}
      </span>
    </div>
  );
}
