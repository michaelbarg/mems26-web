# VA_FADE Calibration — All Variants Negative · 2026-08-26

## Verdict: **ALL NEGATIVE. VA_FADE path stopped.**

| Variant | Total | Median/day | Days+ | Cands | Worst |
|---------|-------|-----------|-------|-------|-------|
| baseline | -$1,316 | -$31.88 | 9/26 | 34 | -$292 |
| tight_rejection (33%) | -$963 | -$3.75 | 9/26 | 32 | -$288 |
| **rearm** (after stop) | **-$532** | **$0.00** | **12/26** | 94 | -$348 |
| wide_stop (2.5pt) | -$1,256 | -$69.38 | 8/26 | 34 | -$318 |
| combined (tight+rearm+wide) | -$1,027 | -$35.62 | 8/26 | 80 | -$431 |

## Analysis

- **Rearm is the best variant** (-$532, 12/26 positive) — multi-rotation days
  are real, and capturing them helps. But still net negative.
- **Tight rejection helps marginally** (-$963 vs -$1,316) — fewer bad entries.
- **Wide stop makes it worse** — the extra room doesn't save trades, just costs more.
- **Combined is worse than rearm alone** — the tight rejection filters out too many
  of the good re-arm trades.

## Root cause

The edge detection is correct (finds real VA rejections), but the **entry timing is
one bar too early**. The rejection bar is the PROBE — not the confirmation. By the time
VA_FADE fires, the bar is probing the edge; the actual turn happens 1-3 bars later.

This is the same finding as the extreme detection audit: 83-88% reversal rate at
extremes, but MAE eats MFE when entering at detection instead of confirmation.

## Recommendation

**Stop the VA_FADE-as-standalone path.** The correct architecture (from the Dalton
simulation) is to use VA_FADE detection as a **context signal** for the existing REACTIVE
detector — not as a separate entry generator. REACTIVE already has the confirmation bar
(b1-b4 geometry). VA_FADE should ARM and REACTIVE should ENTER, exactly like the
edge_fade ARM→RELEASE two-stage design.

This is Phase 4 territory (CONTEXT_ENTRY_V1), not a calibration fix.

*cc-macbook · 2026-08-26. Config: `config/va_fade.yaml`. Code: `va_fade.py` parameterized.*
