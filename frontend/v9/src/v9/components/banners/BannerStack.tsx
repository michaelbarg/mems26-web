'use client';
import { useEffect, useState } from 'react';
import { COLORS } from '../../design/tokens';

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

interface BannerDef {
  id: string;
  text: string;
  color: string;
  bg: string;
  autoClear?: number; // ms, 0 = manual dismiss
}

/**
 * Banner stack — V5 §3.7 edge case banners.
 * Top of viewport, dismissable, auto-clears when condition resolves.
 * 7 conditional banners polled from system state.
 */
export function BannerStack() {
  const [banners, setBanners] = useState<BannerDef[]>([]);
  const [dismissed, setDismissed] = useState<Set<string>>(new Set());

  useEffect(() => {
    const check = async () => {
      const active: BannerDef[] = [];
      try {
        // Bridge health
        const status = await fetch(`${API}/api/v9/status`).then(r => r.json()).catch(() => null);
        if (status && !status.bridge?.running) {
          active.push({ id: 'bridge_down', text: 'Connection lost — bridge offline', color: '#fca5a5', bg: '#7f1d1d' });
        }

        // Gateway risk state
        const gw = await fetch(`${API}/api/v9/gateway/status`).then(r => r.json()).catch(() => null);
        if (gw) {
          if (gw.consecutive_losses >= 2) {
            active.push({ id: 'cooldown', text: `Cooldown active — ${gw.consecutive_losses} consecutive stops`, color: '#fde68a', bg: '#78350f' });
          }
          if (gw.daily_pnl <= -200) {
            const pct = Math.min(100, Math.abs(gw.daily_pnl) / 250 * 100);
            active.push({ id: 'loss_cap', text: `Daily loss $${Math.abs(gw.daily_pnl).toFixed(0)}/$250 (${pct.toFixed(0)}%)`, color: '#fdba74', bg: '#7c2d12' });
          }
        }

        // System health (check for any system not 200)
        for (const sys of ['day_type', 'five_min', 'footprint', 'woodies', 'tpo', 'killzone']) {
          try {
            const r = await fetch(`${API}/api/v9/${sys}/current`);
            if (r.status !== 200) {
              active.push({ id: `sys_${sys}`, text: `System ${sys} health failure (HTTP ${r.status})`, color: '#fca5a5', bg: '#7f1d1d' });
            }
          } catch {
            active.push({ id: `sys_${sys}`, text: `System ${sys} unreachable`, color: '#fca5a5', bg: '#7f1d1d' });
          }
        }
      } catch { /* status endpoint down — banner for bridge_down covers it */ }
      setBanners(active);
    };
    check();
    const id = setInterval(check, 10000);
    return () => clearInterval(id);
  }, []);

  const visible = banners.filter(b => !dismissed.has(b.id));
  if (visible.length === 0) return null;

  return (
    <div style={{ position: 'fixed', top: 0, left: 0, right: 0, zIndex: 10000 }}>
      {visible.map(b => (
        <div key={b.id} style={{
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          padding: '4px 12px', background: b.bg, color: b.color,
          fontSize: 11, fontFamily: 'ui-monospace, monospace', fontWeight: 500,
          borderBottom: `1px solid ${COLORS.borderFaint}`,
        }}>
          <span>{b.text}</span>
          <button onClick={() => setDismissed(prev => new Set(prev).add(b.id))}
            style={{ background: 'none', border: 'none', color: b.color, cursor: 'pointer', fontSize: 13 }}>
            {'\u00D7'}
          </button>
        </div>
      ))}
    </div>
  );
}
