// frontend/src/components/LevelsBadges.tsx
"use client";
type Props = {
  price: number;
  woodi: Record<string, number>;
  levels: Record<string, number>;
  features: Record<string, unknown>;
};
function dist(a: number, b: number) { return b ? Math.abs(a - b).toFixed(2) : "—"; }
function badge(label: string, color: string, value: number, price: number) {
  return (
    <div key={label} className="flex items-center gap-1.5 px-2 py-0.5 rounded text-[9px]"
      style={{ background: color + "15", border: `0.5px solid ${color}44` }}>
      <span style={{ color }}>{label}</span>
      <span className="text-white font-bold">{value.toFixed(2)}</span>
      <span className="text-gray-600">{dist(price, value)}pts</span>
    </div>
  );
}
export default function LevelsBadges({ price, woodi, levels, features }: Props) {
  const f = features as Record<string, number>;
  return (
    <div className="flex flex-wrap gap-1.5 px-1">
      {f.poc_today ? badge("POC", "#6d28d9", f.poc_today, price) : null}
      {f.poc_yest  ? badge("POC-1", "#ea580c", f.poc_yest, price) : null}
      {woodi.pp    ? badge("PP",    "#f59e0b", woodi.pp,  price) : null}
      {woodi.r1    ? badge("R1",    "#22c55e", woodi.r1,  price) : null}
      {woodi.s1    ? badge("S1",    "#ef4444", woodi.s1,  price) : null}
      {levels.h72  ? badge("72H↑",  "#06b6d4", levels.h72, price) : null}
      {levels.l72  ? badge("72H↓",  "#06b6d4", levels.l72, price) : null}
    </div>
  );
}
