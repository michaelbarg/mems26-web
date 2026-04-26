"use client";

import { useState, useEffect, useRef, useCallback } from "react";

interface TradeState {
  trade_id: string;
  status: string;
  c1_status: string;
  c2_status: string;
  c3_status: string;
  stop_status: string;
  c1_fill_price: number | null;
  c2_fill_price: number | null;
  c3_fill_price: number | null;
  stop_fill_price: number | null;
  c1_order_id: number | null;
  c2_order_id: number | null;
  c3_order_id: number | null;
  stop_c1_order_id: number | null;
  stop_c2_order_id: number | null;
  stop_c3_order_id: number | null;
  parent_order_id: number | null;
  active_management_state: string;
}

interface ActiveTradePanelV2Props {
  tradeId?: string;
  apiUrl?: string;
}

function getStatusColor(status: string): string {
  switch (status) {
    case "FILLED": return "#22c55e";
    case "OPEN": return "#3b82f6";
    case "PENDING": return "#6b7280";
    case "CANCELED": return "#ef4444";
    default: return "#9ca3af";
  }
}

function getStatusBg(status: string): string {
  switch (status) {
    case "FILLED": return "#0a2e1a";
    case "OPEN": return "#0a1a2e";
    case "PENDING": return "#1e2738";
    case "CANCELED": return "#2e0a0a";
    default: return "#1e2738";
  }
}

function getMgmtStateColor(state: string): { bg: string; text: string } {
  switch (state) {
    case "BE_ARMED": return { bg: "#1a0a2e", text: "#a78bfa" };
    case "TRAILING": return { bg: "#0a1a2e", text: "#60a5fa" };
    case "BAILED_OUT": return { bg: "#2e0a0a", text: "#ef5350" };
    default: return { bg: "#1e2738", text: "#9ca3af" };
  }
}

export default function ActiveTradePanelV2({ tradeId, apiUrl }: ActiveTradePanelV2Props) {
  const [data, setData] = useState<TradeState | null>(null);
  const [busy, setBusy] = useState("");
  const [toast, setToast] = useState<{ msg: string; color: string } | null>(null);
  const [modal, setModal] = useState<"stop" | "target" | null>(null);
  const [stopInput, setStopInput] = useState("");
  const [t1Input, setT1Input] = useState("");
  const [t2Input, setT2Input] = useState("");
  const [t3Input, setT3Input] = useState("");
  const [confirmBailout, setConfirmBailout] = useState(false);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const base = apiUrl || "https://mems26-web.onrender.com";

  const showToast = useCallback((msg: string, color: string) => {
    setToast({ msg, color });
    setTimeout(() => setToast(null), 4000);
  }, []);

  // Poll /trade/state/{tradeId} every 3s
  useEffect(() => {
    if (!tradeId) { setData(null); return; }
    let active = true;
    const poll = async () => {
      try {
        const res = await fetch(`${base}/trade/state/${tradeId}`, {
          headers: { "X-Bridge-Token": "michael-mems26-2026" },
        });
        if (res.ok && active) {
          const j = await res.json();
          setData(j);
        }
      } catch {}
    };
    poll();
    pollRef.current = setInterval(poll, 3000);
    return () => { active = false; if (pollRef.current) clearInterval(pollRef.current); };
  }, [tradeId, base]);

  const apiPost = useCallback(async (path: string, body: Record<string, unknown>) => {
    const res = await fetch(`${base}${path}`, {
      method: "POST",
      headers: {
        "content-type": "application/json",
        "X-Bridge-Token": "michael-mems26-2026",
      },
      body: JSON.stringify(body),
    });
    const j = await res.json();
    if (!res.ok) throw new Error(j.detail || `HTTP ${res.status}`);
    return j;
  }, [base]);

  const handleBailout = useCallback(async () => {
    if (!tradeId) return;
    setBusy("bailout");
    try {
      await apiPost("/trade/bailout", { trade_id: tradeId });
      showToast("BAILOUT sent", "#ef5350");
      setConfirmBailout(false);
    } catch (e: unknown) {
      showToast(`Bailout failed: ${e instanceof Error ? e.message : e}`, "#ef4444");
    }
    setBusy("");
  }, [tradeId, apiPost, showToast]);

  const handleModifyStop = useCallback(async () => {
    if (!tradeId) return;
    const price = parseFloat(stopInput);
    if (isNaN(price) || price <= 0) { showToast("Invalid stop price", "#ef4444"); return; }
    setBusy("stop");
    try {
      await apiPost("/trade/modify-stop", { trade_id: tradeId, new_stop_price: price });
      showToast(`Stop moved to ${price.toFixed(2)}`, "#ca8a04");
      setModal(null);
      setStopInput("");
    } catch (e: unknown) {
      showToast(`Modify stop failed: ${e instanceof Error ? e.message : e}`, "#ef4444");
    }
    setBusy("");
  }, [tradeId, stopInput, apiPost, showToast]);

  const handleModifyTarget = useCallback(async () => {
    if (!tradeId) return;
    const t1 = t1Input ? parseFloat(t1Input) : undefined;
    const t2 = t2Input ? parseFloat(t2Input) : undefined;
    const t3 = t3Input ? parseFloat(t3Input) : undefined;
    if (!t1 && !t2 && !t3) { showToast("Enter at least one target", "#ef4444"); return; }
    setBusy("target");
    try {
      const body: Record<string, unknown> = { trade_id: tradeId };
      if (t1) body.new_t1 = t1;
      if (t2) body.new_t2 = t2;
      if (t3) body.new_t3 = t3;
      await apiPost("/trade/modify-target", body);
      const parts = [t1 && `T1=${t1}`, t2 && `T2=${t2}`, t3 && `T3=${t3}`].filter(Boolean).join(" ");
      showToast(`Targets modified: ${parts}`, "#60a5fa");
      setModal(null);
      setT1Input(""); setT2Input(""); setT3Input("");
    } catch (e: unknown) {
      showToast(`Modify target failed: ${e instanceof Error ? e.message : e}`, "#ef4444");
    }
    setBusy("");
  }, [tradeId, t1Input, t2Input, t3Input, apiPost, showToast]);

  if (!tradeId) {
    return (
      <div style={{ background: '#0d1117', border: '1px solid #1e2738', borderRadius: 6, padding: '8px 12px', marginTop: 8 }}>
        <span style={{ fontSize: 12, color: '#4b5563' }}>No active trade</span>
      </div>
    );
  }

  const contracts = data ? [
    { label: "C1", status: data.c1_status, price: data.c1_fill_price },
    { label: "C2", status: data.c2_status, price: data.c2_fill_price },
    { label: "C3", status: data.c3_status, price: data.c3_fill_price },
    { label: "Stop", status: data.stop_status, price: data.stop_fill_price },
  ] : [];

  const mgmtColors = getMgmtStateColor(data?.active_management_state ?? "NORMAL");

  const btnStyle = (bg: string, color: string, disabled?: boolean): React.CSSProperties => ({
    padding: '6px 0', fontSize: 13, fontWeight: 700,
    background: bg, color: color,
    border: 'none', borderRadius: 4,
    cursor: disabled ? 'not-allowed' : 'pointer',
    opacity: disabled ? 0.5 : 1,
  });

  const inputStyle: React.CSSProperties = {
    width: '100%', padding: '4px 6px', fontSize: 13,
    background: '#111827', color: '#e5e7eb', border: '1px solid #374151',
    borderRadius: 4, fontFamily: 'monospace',
  };

  return (
    <div style={{ background: '#0d1117', border: '1px solid #1e2738', borderRadius: 6, padding: '8px 12px', marginTop: 8 }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
        <span style={{ fontSize: 14, fontWeight: 700, color: '#e5e7eb' }}>Active Trade Mgmt</span>
        <span style={{ fontSize: 11, color: '#6b7280', fontFamily: 'monospace' }}>{tradeId}</span>
      </div>

      {/* Per-contract grid */}
      {data && (
        <>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr 1fr', gap: 6, marginBottom: 8 }}>
            {contracts.map((item) => (
              <div key={item.label} style={{ textAlign: 'center' }}>
                <div style={{ fontSize: 11, color: '#6b7280', marginBottom: 2 }}>{item.label}</div>
                <div style={{
                  padding: '2px 4px', borderRadius: 3, fontSize: 11, fontWeight: 800,
                  color: getStatusColor(item.status), background: getStatusBg(item.status),
                }}>{item.status}</div>
                {item.price !== null && item.price > 0 && (
                  <div style={{ fontSize: 11, marginTop: 2, fontFamily: 'monospace', color: '#9ca3af' }}>
                    @{item.price.toFixed(2)}
                  </div>
                )}
              </div>
            ))}
          </div>

          {/* Mgmt state badge */}
          <div style={{ display: 'flex', alignItems: 'center', marginBottom: 8 }}>
            <span style={{ fontSize: 11, color: '#6b7280', marginRight: 6 }}>Mgmt State:</span>
            <span style={{
              display: 'inline-block', padding: '1px 6px', borderRadius: 3,
              fontSize: 11, fontWeight: 700,
              color: mgmtColors.text, background: mgmtColors.bg,
            }}>{data.active_management_state}</span>
          </div>
        </>
      )}

      {/* Action buttons */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 6 }}>
        <button
          disabled={!!busy}
          style={btnStyle('#2a2a0a', '#ca8a04', !!busy)}
          onClick={() => { setModal("stop"); setStopInput(""); }}
        >Move Stop</button>
        <button
          disabled={!!busy}
          style={btnStyle('#0a1a2e', '#60a5fa', !!busy)}
          onClick={() => { setModal("target"); setT1Input(""); setT2Input(""); setT3Input(""); }}
        >Move Target</button>
        <button
          disabled={!!busy}
          style={btnStyle('#2e1a0a', '#f97316', !!busy)}
          onClick={() => setConfirmBailout(true)}
        >Bailout</button>
        <button
          disabled={!!busy}
          style={btnStyle('#2e0a0a', '#ef5350', !!busy)}
          onClick={async () => {
            setBusy("close");
            try {
              await fetch(`${base}/trade/close`, {
                method: 'POST',
                headers: { 'content-type': 'application/json' },
                body: JSON.stringify({ exit_price: 0, reason: 'manual_v2' }),
              });
              showToast("Close sent", "#9ca3af");
            } catch {}
            setBusy("");
          }}
        >Manual Close</button>
      </div>

      {/* Toast */}
      {toast && (
        <div style={{
          marginTop: 6, padding: '4px 8px', borderRadius: 4,
          fontSize: 11, fontWeight: 700, color: toast.color,
          background: `${toast.color}15`, textAlign: 'center',
        }}>{toast.msg}</div>
      )}

      {/* Bailout confirm */}
      {confirmBailout && (
        <div style={{
          marginTop: 6, padding: 8, background: '#1a0a0a', border: '1px solid #ef4444',
          borderRadius: 4, textAlign: 'center',
        }}>
          <div style={{ fontSize: 12, color: '#ef5350', fontWeight: 700, marginBottom: 6 }}>
            Confirm BAILOUT? This exits ALL positions.
          </div>
          <div style={{ display: 'flex', gap: 8, justifyContent: 'center' }}>
            <button
              style={{ ...btnStyle('#ef4444', '#fff'), padding: '4px 16px' }}
              disabled={busy === "bailout"}
              onClick={handleBailout}
            >{busy === "bailout" ? "..." : "YES — Bailout"}</button>
            <button
              style={{ ...btnStyle('#374151', '#9ca3af'), padding: '4px 16px' }}
              onClick={() => setConfirmBailout(false)}
            >Cancel</button>
          </div>
        </div>
      )}

      {/* Modify Stop modal */}
      {modal === "stop" && (
        <div style={{
          marginTop: 6, padding: 8, background: '#111827', border: '1px solid #374151',
          borderRadius: 4,
        }}>
          <div style={{ fontSize: 12, color: '#ca8a04', fontWeight: 700, marginBottom: 6 }}>
            New Stop Price
          </div>
          <input
            style={inputStyle}
            type="number"
            step="0.25"
            placeholder="e.g. 7120.00"
            value={stopInput}
            onChange={(e) => setStopInput(e.target.value)}
            autoFocus
          />
          <div style={{ display: 'flex', gap: 8, marginTop: 6 }}>
            <button
              style={{ ...btnStyle('#ca8a04', '#fff'), padding: '4px 16px', flex: 1 }}
              disabled={busy === "stop"}
              onClick={handleModifyStop}
            >{busy === "stop" ? "..." : "Apply"}</button>
            <button
              style={{ ...btnStyle('#374151', '#9ca3af'), padding: '4px 16px' }}
              onClick={() => setModal(null)}
            >Cancel</button>
          </div>
        </div>
      )}

      {/* Modify Target modal */}
      {modal === "target" && (
        <div style={{
          marginTop: 6, padding: 8, background: '#111827', border: '1px solid #374151',
          borderRadius: 4,
        }}>
          <div style={{ fontSize: 12, color: '#60a5fa', fontWeight: 700, marginBottom: 6 }}>
            New Targets (leave blank to skip)
          </div>
          <div style={{ display: 'flex', gap: 4, marginBottom: 4 }}>
            <div style={{ flex: 1 }}>
              <div style={{ fontSize: 10, color: '#6b7280', marginBottom: 2 }}>T1</div>
              <input style={inputStyle} type="number" step="0.25" placeholder="T1" value={t1Input} onChange={(e) => setT1Input(e.target.value)} autoFocus />
            </div>
            <div style={{ flex: 1 }}>
              <div style={{ fontSize: 10, color: '#6b7280', marginBottom: 2 }}>T2</div>
              <input style={inputStyle} type="number" step="0.25" placeholder="T2" value={t2Input} onChange={(e) => setT2Input(e.target.value)} />
            </div>
            <div style={{ flex: 1 }}>
              <div style={{ fontSize: 10, color: '#6b7280', marginBottom: 2 }}>T3</div>
              <input style={inputStyle} type="number" step="0.25" placeholder="T3" value={t3Input} onChange={(e) => setT3Input(e.target.value)} />
            </div>
          </div>
          <div style={{ display: 'flex', gap: 8 }}>
            <button
              style={{ ...btnStyle('#3b82f6', '#fff'), padding: '4px 16px', flex: 1 }}
              disabled={busy === "target"}
              onClick={handleModifyTarget}
            >{busy === "target" ? "..." : "Apply"}</button>
            <button
              style={{ ...btnStyle('#374151', '#9ca3af'), padding: '4px 16px' }}
              onClick={() => setModal(null)}
            >Cancel</button>
          </div>
        </div>
      )}
    </div>
  );
}
