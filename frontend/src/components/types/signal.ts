export type Signal = {
  direction: "LONG" | "SHORT" | "NO_TRADE";
  score: number;
  confidence: string;
  entry: number;
  stop: number;
  target1: number;
  target2: number;
  target3: number;
  risk_pts: number;
  rationale: string;
  tl_color: string;
  ts?: number;
};
