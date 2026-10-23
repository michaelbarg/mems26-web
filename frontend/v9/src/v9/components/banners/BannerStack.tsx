'use client';
import { useEffect, useState } from 'react';
import { COLORS } from '../../design/tokens';
import { pickAccountPnl } from '../../lib/accountPnl';

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// Daily-loss banner thresholds.
// TODO backend: expose RISK_DAILY_LOSS_CAP (e.g. on /api/v9/gateway/status). No desktop
// endpoint returns it (checked 23.10: /cockpit/heartbeat, /gateway/status, /account/state;
// only the key-gated /mobile/data has halt_cap), so the number stays hard-coded here.
// The backend itself disagrees on the default of that one env var — risk_checks.py 800,
// trading_gateway.py 450, mobile_monitor.py 400 — plus fixed caps 250 (risk_validator)
// and 200 (woodies a7). Not changed here (risk defaults are backend decisions).
const DAILY_LOSS_CAP_USD = 250;
const DAILY_LOSS_WARN_USD = 200;

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
    let inFlight = false;
    const check = async () => {
      if (inFlight) return;
      inFlight = true;
      try {
        const active: BannerDef[] = [];

        // Lightweight heartbeat for bridge/price file health
        const hb = await fetch(`${API}/api/v9/cockpit/heartbeat`).then(r => r.json()).catch(() => null);
        if (hb && hb.price_file_age_ms < 0) {
          active.push({ id: 'bridge_down', text: 'Connection lost — price file missing', color: '#fca5a5', bg: '#7f1d1d' });
        }

        // Gateway risk state (cheap endpoint)
        const gw = await fetch(`${API}/api/v9/gateway/status`).then(r => r.json()).catch(() => null);
        // Day P&L of the account we actually trade (Sim1 in DEMO) — same rule as
        // SierraTruthStrip (lib/accountPnl). Audit 23.10: gateway.daily_pnl stays 0.0
        // in DEMO (trades_today 0 while Sim1 was −$175), so the banner could never fire.
        const acct = await fetch(`${API}/api/v9/account/state`).then(r => r.json()).catch(() => null);
        const acctPnl = pickAccountPnl(acct?.sierra_state);
        const gwDaily = typeof gw?.daily_pnl === 'number' ? gw.daily_pnl : null;
        const dayPnl = acctPnl.daily ?? gwDaily;
        const dayPnlFrom = acctPnl.daily != null ? (acctPnl.account ?? 'Sierra') : 'gateway';
        if (gw) {
          // "Cooldown active" only when the real gate blocks (cooldown.cooldown_active).
          // The 2-stop block is OFF by standing decision (Michael 07-02); showing
          // "active" off consecutive_losses>=2 was a false banner — that counter
          // also hydrates from YESTERDAY's session before 09:30 ET.
          if (gw.cooldown?.cooldown_active) {
            active.push({ id: 'cooldown', text: `Cooldown active — ${gw.cooldown.consecutive_stops} consecutive stops`, color: '#fde68a', bg: '#78350f' });
          } else if (gw.consecutive_losses >= 2) {
            active.push({ id: 'loss_streak', text: `מונה: ${gw.consecutive_losses} הפסדים רצופים (cooldown כבוי — החלטה קבועה)`, color: '#a3a3a3', bg: '#262626' });
          }
        }
        // Michael 23.10 20:0x: "אין מגבלת הפסד ביום כשאנחנו על דמו — מבחינתי אין הפסקה על דמו".
        // On a Sim account the day loss is information only (gray, no cap); the cap banner is LIVE-only.
        const isDemoAcct = /^sim/i.test(String(acctPnl.account ?? '')) || (gw && gw.live_slot == null && gwDaily === 0 && acctPnl.daily != null);
        if (dayPnl != null && dayPnl <= -DAILY_LOSS_WARN_USD) {
          if (isDemoAcct) {
            active.push({ id: 'loss_demo', text: `דמו (${dayPnlFrom}) · יום $${dayPnl.toFixed(0)} · אין עצירת-הפסד בדמו`, color: '#a3a3a3', bg: '#262626' });
          } else {
            const pct = Math.min(100, Math.abs(dayPnl) / DAILY_LOSS_CAP_USD * 100);
            active.push({ id: 'loss_cap', text: `Daily loss $${Math.abs(dayPnl).toFixed(0)}/$${DAILY_LOSS_CAP_USD} (${pct.toFixed(0)}%) · ${dayPnlFrom}`, color: '#fdba74', bg: '#7c2d12' });
          }
        }

        // System health from systemStateStore (already polled elsewhere)
        // Only show banners for systems the store flags as 'error'
        // No additional HTTP calls needed — the store handles polling
        setBanners(active);
      } finally {
        inFlight = false;
      }
    };
    check();
    const id = setInterval(check, 30000); // 30s, not 10s — banners are not latency-critical
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
