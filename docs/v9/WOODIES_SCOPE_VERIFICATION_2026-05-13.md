# Woodies Verification Result — 2026-05-13

## In scope for P-WCC-CORE (build now):
- ZLR (Zero Line Reject)
- TT (Trend Trader, 6-bar persistence)
- TLB (Trend Line Break)
- Zero Line context: CZI ±100, SWI ±200
- 6-bar trend persistence rule (CORE methodology)

## Already in code (keep as-is):
- ZLC (Zero Line Cross)
- OB (Overbought ±200)
- OS (Oversold ±200)
- Trend (basic)

## Deferred to post-SHADOW:
- GB100, GHOST, FAMIR, HTLB, HFE
- Reason: complex pattern detection, lower frequency,
  can iterate after SHADOW data accumulates.
