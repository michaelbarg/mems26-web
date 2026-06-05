'use client';
/**
 * Heat MAE/MFE strip — client-side from existing mfe_pts/mae_pts fields.
 * Shows distribution of max favorable / adverse excursion.
 * If mfe_pts/mae_pts not available → "pending G4" gated.
 */
import { useMemo, useState } from 'react';
import { useTradeStore } from '../../stores/tradeStore';

export function HeatMaeStrip() {
  const filteredTrades = useTradeStore((s) => s.filteredTrades);
  const allTrades = filteredTrades();
  const trades = useMemo(() => allTrades.filter((t) => !t.is_synthetic && t.pnl_usd != null), [allTrades]);
  const [open, setOpen] = useState(false);

  const stats = useMemo(() => {
    let mfeSum = 0, maeSum = 0, mfeCount = 0, maeCount = 0, mfeMax = 0, maeMax = 0;
    for (const t of trades) {
      if (t.mfe_pts != null) { mfeSum += t.mfe_pts; mfeCount++; mfeMax = Math.max(mfeMax, t.mfe_pts); }
      if (t.mae_pts != null) { maeSum += t.mae_pts; maeCount++; maeMax = Math.max(maeMax, t.mae_pts); }
    }
    return {
      mfeAvg: mfeCount > 0 ? mfeSum / mfeCount : null,
      maeAvg: maeCount > 0 ? maeSum / maeCount : null,
      mfeMax,
      maeMax,
      mfeCount,
      maeCount,
      hasMfe: mfeCount > 0,
      hasMae: maeCount > 0,
    };
  }, [trades]);

  if (trades.length === 0) return null;

  const fmtPts = (v: number | null) => v == null ? '—' : `${v.toFixed(1)} pts`;
  const hasData = stats.hasMfe || stats.hasMae;

  return (
    <div className="border-b shrink-0" style={{ background: 'var(--bg-secondary)', borderColor: 'var(--border)' }}>
      <div className="flex items-center justify-between px-4 py-2">
        <div className="flex items-center gap-3">
          <span className="text-[10px] uppercase tracking-wide" style={{ color: 'var(--text-muted)' }}>
            Heat · MAE / MFE
          </span>
          {hasData ? (
            <>
              <span className="font-mono text-[10px]" style={{ color: 'var(--green)' }}>
                avg MFE {fmtPts(stats.mfeAvg)} · max {fmtPts(stats.mfeMax)}
              </span>
              <span className="font-mono text-[10px]" style={{ color: 'var(--red)' }}>
                avg MAE {fmtPts(stats.maeAvg)} · max {fmtPts(stats.maeMax)}
              </span>
            </>
          ) : (
            <span className="text-[10px]" style={{ color: 'var(--text-muted)' }}>pending G4 — mfe_pts/mae_pts not populated</span>
          )}
        </div>
        {hasData && (
          <button onClick={() => setOpen((o) => !o)} className="text-[10px] uppercase tracking-wide hover:underline" style={{ color: 'var(--text-secondary)' }}>
            {open ? '▾ Collapse' : '▸ Expand'}
          </button>
        )}
      </div>
      {open && hasData && (
        <div className="px-4 pb-2">
          <div className="flex gap-4">
            <div className="flex-1">
              <div className="text-[9px] uppercase mb-1" style={{ color: 'var(--green)' }}>MFE distribution ({stats.mfeCount} trades)</div>
              <div style={{ display: 'flex', gap: 1, height: 32, alignItems: 'flex-end' }}>
                {trades.filter((t) => t.mfe_pts != null).map((t) => {
                  const h = stats.mfeMax > 0 ? ((t.mfe_pts ?? 0) / stats.mfeMax) * 28 + 4 : 4;
                  return <div key={t.id} style={{ width: 3, height: h, background: 'var(--green)', borderRadius: 1, opacity: 0.6 }} />;
                })}
              </div>
            </div>
            <div className="flex-1">
              <div className="text-[9px] uppercase mb-1" style={{ color: 'var(--red)' }}>MAE distribution ({stats.maeCount} trades)</div>
              <div style={{ display: 'flex', gap: 1, height: 32, alignItems: 'flex-end' }}>
                {trades.filter((t) => t.mae_pts != null).map((t) => {
                  const h = stats.maeMax > 0 ? ((t.mae_pts ?? 0) / stats.maeMax) * 28 + 4 : 4;
                  return <div key={t.id} style={{ width: 3, height: h, background: 'var(--red)', borderRadius: 1, opacity: 0.6 }} />;
                })}
              </div>
            </div>
          </div>
          <div className="mt-1 text-[9px] font-mono" style={{ color: 'var(--text-muted)' }}>
            indicative client-side · ≤500 rows — full server-side = G3 DEFERRED
          </div>
        </div>
      )}
    </div>
  );
}
