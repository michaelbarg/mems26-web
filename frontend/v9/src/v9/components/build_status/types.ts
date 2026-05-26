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

export interface Component {
  stage: string;
  key: string;
  spec: string;
  present: boolean;
  value: string;
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
}

export interface SystemBlock {
  id: string;
  name: string;
  running: boolean;
  hydrated: boolean;
  mode: string;
  data_freshness: DataFreshness;
  global_gates: SystemGate[];
  patterns: Pattern[];
}

export interface RtbSession {
  in_session: boolean;
  minutes_to_open: number;
  minutes_to_close: number;
}

export interface BuildStatusResponse {
  ts: string;
  build_version: string;
  session_date: string;
  rtb_session: RtbSession;
  systems: SystemBlock[];
  errors: string[];
}
