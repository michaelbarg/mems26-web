// frontend/src/components/ReversalStatus.tsx
"use client";
type Props = { features: Record<string, string | number>; sesMin: number };
export default function ReversalStatus({ features, sesMin }: Props) {
  const r15 = String(features.rev15 ?? "NONE");
  const r22 = String(features.rev22 ?? "NONE");
  const ibH = Number(features.ib_high ?? 0);
  const ibL = Number(features.ib_low  ?? 0);

  const hasRev = (r: string) => r !== "NONE";
  const isLong  = (r: string) => r.includes("LONG");
  const col  = (r: string) => !hasRev(r) ? "#555" : isLong(r) ? "#22c55e" : "#ef4444";

  return (
    <div className="bg-[#111118] border border-[#1e1e2e] rounded-xl p-2.5 flex flex-col gap-1.5">
      <span className="text-[9px] text-gray-600">REVERSAL</span>
      <div className="text-[9px]" style={{ color: col(r15) }}>
        Rev 15: {sesMin < 15 ? `${15 - sesMin}m` : hasRev(r15) ? r15.replace("_", " ") : "checked ✓"}
      </div>
      <div className="text-[9px]" style={{ color: col(r22) }}>
        Rev 22: {sesMin < 22 ? `${22 - sesMin}m` : hasRev(r22) ? r22.replace("_", " ") : "checked ✓"}
      </div>
      {ibH > 0 && (
        <div className="text-[9px] text-gray-600">
          IB: {ibH.toFixed(2)} / {ibL.toFixed(2)}
        </div>
      )}
    </div>
  );
}
