"use client";

interface ConditionStatus {
  name: string;
  status: 'pass' | 'pending' | 'fail';
  detail: string;
}

interface AwaitingTriggerPanelProps {
  direction: 'LONG' | 'SHORT';
  entry: number;
  stop: number;
  score: number;
  footprintScore?: number;
  scoreReasons?: string[];
  stopMin?: number;
  stopMax?: number;
}

function getETTime(): { hour: number; minute: number } {
  const now = new Date();
  const et = new Date(now.toLocaleString('en-US', { timeZone: 'America/New_York' }));
  return { hour: et.getHours(), minute: et.getMinutes() };
}

function getKillzoneStatus(): { name: string; status: 'pass' | 'pending' | 'fail'; detail: string } {
  const { hour, minute } = getETTime();
  const t = hour * 60 + minute;
  const zones = [
    { name: 'London', start: 180, end: 300 },
    { name: 'NY Open', start: 570, end: 630 },
    { name: 'NY Close', start: 900, end: 960 },
  ];
  for (const z of zones) {
    if (t >= z.start && t < z.end) {
      const left = z.end - t;
      return { name: `Killzone ${z.name}`, status: 'pass', detail: `active (${left}min left)` };
    }
  }
  // Find next zone
  let nextZone = zones.find(z => z.start > t);
  if (!nextZone) nextZone = zones[0]; // wrap to tomorrow's London
  const minsTo = nextZone.start > t ? nextZone.start - t : (1440 - t) + nextZone.start;
  const h = Math.floor(minsTo / 60);
  const m = minsTo % 60;
  if (t >= 960) {
    return { name: 'Killzone', status: 'fail', detail: 'past NY Close (EOD)' };
  }
  return { name: `Killzone ${nextZone.name}`, status: 'pending', detail: `starts in ${h}h ${m}m` };
}

function evaluateConditions(props: AwaitingTriggerPanelProps): ConditionStatus[] {
  const { direction, entry, stop, score, footprintScore, scoreReasons, stopMin = 3.0, stopMax = 15.0 } = props;
  const conditions: ConditionStatus[] = [];
  const risk = Math.abs(entry - stop);

  // 1. Score threshold
  if (score >= 70) {
    conditions.push({ name: 'Score \u2265 70', status: 'pass', detail: `${score}/100` });
  } else {
    conditions.push({ name: 'Score \u2265 70', status: 'fail', detail: `${score}/100 (need \u226570)` });
  }

  // 2. Stop in range
  if (risk >= stopMin && risk <= stopMax) {
    conditions.push({ name: 'Stop in range', status: 'pass', detail: `${risk.toFixed(1)}pt (${stopMin}-${stopMax} OK)` });
  } else {
    conditions.push({ name: 'Stop in range', status: 'fail', detail: `${risk.toFixed(1)}pt (need ${stopMin}-${stopMax})` });
  }

  // 3. Footprint flow
  if (footprintScore != null && footprintScore > 0) {
    conditions.push({ name: 'Footprint confirm', status: 'pass', detail: `score ${footprintScore}` });
  } else {
    // Try to extract delta from reasons
    let deltaInfo = '';
    if (scoreReasons) {
      const fpReason = scoreReasons.find(r => r.toLowerCase().includes('delta'));
      if (fpReason) {
        const m = fpReason.match(/delta=([+-]?\d+)/);
        if (m) deltaInfo = `delta ${m[1]}`;
      }
      if (fpReason?.toLowerCase().includes('opposes')) {
        deltaInfo += ' opposes';
      }
    }
    conditions.push({
      name: 'Footprint confirm',
      status: 'pending',
      detail: deltaInfo || 'waiting for flow alignment',
    });
  }

  // 4. Killzone
  conditions.push(getKillzoneStatus());

  // 5. Pre-close check
  const { hour, minute } = getETTime();
  const etMin = hour * 60 + minute;
  if (etMin >= 930) { // 15:30 ET
    conditions.push({ name: 'Pre-close', status: 'fail', detail: 'market closing soon' });
  }

  // Sort: pass first, then pending, then fail
  const order = { pass: 0, pending: 1, fail: 2 };
  conditions.sort((a, b) => order[a.status] - order[b.status]);
  return conditions;
}

export default function AwaitingTriggerPanel(props: AwaitingTriggerPanelProps) {
  const conditions = evaluateConditions(props);
  const passed = conditions.filter(c => c.status === 'pass').length;
  const total = conditions.length;
  const allPass = passed === total;
  const pct = total > 0 ? (passed / total) * 100 : 0;

  const iconMap = { pass: '\u2713', pending: '\u23F3', fail: '\u2717' };
  const colorMap = { pass: '#22c55e', pending: '#eab308', fail: '#ef4444' };

  return (
    <div style={{ marginTop: 4, fontSize: 10 }}>
      {/* Progress bar */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 3 }}>
        <span style={{ color: '#6b7280' }}>
          {allPass ? 'Ready' : 'Awaiting trigger'}
        </span>
        <span style={{ color: '#9ca3af', fontFamily: 'monospace' }}>{passed}/{total}</span>
        <div style={{ flex: 1, height: 4, background: '#1e2738', borderRadius: 2, overflow: 'hidden' }}>
          <div style={{
            width: `${pct}%`, height: '100%', borderRadius: 2,
            background: allPass ? '#22c55e' : pct > 50 ? '#eab308' : '#ef4444',
            transition: 'width 0.3s',
          }} />
        </div>
      </div>
      {/* Conditions list */}
      {conditions.map((c, i) => (
        <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '1px 0' }}>
          <span style={{ color: colorMap[c.status], fontWeight: 700, width: 12, textAlign: 'center' }}>
            {iconMap[c.status]}
          </span>
          <span style={{ color: '#9ca3af', minWidth: 100 }}>{c.name}</span>
          <span style={{ color: c.status === 'pass' ? '#6b7280' : '#4b5563', fontFamily: 'monospace', marginLeft: 'auto' }}>
            {c.detail}
          </span>
        </div>
      ))}
    </div>
  );
}
