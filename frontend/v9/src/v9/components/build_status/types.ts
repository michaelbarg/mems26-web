/**
 * Types for /api/v9/build/pattern-status response.
 * Mirrors backend Pydantic schemas defined in
 * backend/v9/systems/build_status/types.py (CC HO-2 deliverable).
 * Authority: docs/reports/BUILD_STATUS_ENDPOINT_DESIGN.md §3.
 */

export type PatternStatus =
  | 'fired'
  | 'armed'
  | 'blocked'
  | 'vetoed'
  | 'not_applicable'
  | 'unknown';

export type FreshnessSource =
  | 'sierra_export'
  | 'db'
  | 'in_memory'
  | 'inspector_eval';

export interface Freshness {
  ts: string | null;
  lag_s: number | null;
  source: FreshnessSource | null;
}

export interface Component {
  stage: string;
  key: string;
  spec: string;
  present: boolean;
  value: string;
  // Additive fields (backend v1.1+). Older payloads may omit them.
  live?: string | null;
  required?: string | null;
  freshness?: Freshness | null;
}

export interface FormulaCondition {
  label: string;
  needed: string;
  actual: string | null;
  met: boolean;
}

export interface Pattern {
  id: string;
  name: string;
  status: PatternStatus;
  label: string;
  reason: string;
  fired_today: boolean;
  last_fire_ts: string | null;
  components: Component[];
  blockers: string[];
  formula?: FormulaCondition[];
  build_pct?: number | null;
}

export interface DataFreshness {
  last_bar_ts: string | null;
  lag_seconds: number | null;
  fresh: boolean;
  threshold_seconds: number;
}

export interface SystemGate {
  key: string;
  spec: string;
  present: boolean;
  value: string;
  // Additive fields (backend v1.1+). Older payloads may omit them.
  live?: string | null;
  required?: string | null;
  freshness?: Freshness | null;
  critical?: boolean;  // false for muted/not-wired streams (display as disabled, not red)
}

// D-OBS: Live input field
export interface LiveInput {
  field: string;
  value: string | null;
  source: string | null;
  age_s: number | null;
  fresh: boolean;
}

// D-OBS: Interpretation
export interface InterpretationItem {
  key: string;
  value: string | null;
  from_input: string | null;
  detail: string | null;
}

export interface SystemBlock {
  id: string;
  name: string;
  running: boolean;
  hydrated: boolean;
  mode: string;
  data_freshness: DataFreshness;
  // D-OBS: Live inputs + interpretations
  live_inputs?: LiveInput[];
  interpretations?: InterpretationItem[];
  global_gates: SystemGate[];
  patterns: Pattern[];
  // Aggregate of today's fires across all patterns (backend v1.2+).
  // Source: row_helpers.fires_today() reading v9_trades.firing_system.
  // UI surfaces these in the system header so the trader sees "S4 fired
  // 2× today, last 13:45 ET" without scanning every pattern row.
  fired_today_count?: number;
  last_fire_ts?: string | null;
}

export interface RtbSession {
  in_session: boolean;
  minutes_to_open: number;
  minutes_to_close: number;
}

// D-RDY: Readiness verdict (backend types.py:123-149)
export type ReadinessVerdict = 'READY' | 'DEGRADED' | 'BLOCKED';

export interface ReadinessCheck {
  key: string;
  passed: boolean;
  severity: 'block' | 'degrade' | 'info';
  detail?: string | null;
}

export interface Readiness {
  verdict: ReadinessVerdict;
  reason: string;
  checks: ReadinessCheck[];
}

export interface BuildStatusResponse {
  ts: string;
  build_version: string;
  session_date: string;
  rtb_session: RtbSession;
  systems: SystemBlock[];
  errors: string[];
  readiness?: Readiness;  // D-RDY
}
