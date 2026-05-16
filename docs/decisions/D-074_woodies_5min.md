# D-074 — Woodies Runs on 5-Minute Bars

**Status:** LOCKED  
**Date:** 2026-05-16  
**Decided by:** Michael  
**Scope:** S4 Woodies CCI, data layer, bridge, DB, UI labels

## Decision

S4 Woodies must run on **5-minute bars**, not the current `woodies_30min`
pipeline.

## Why

Michael wants the Woodies firing system to operate at the same practical
decision tempo as the intraday execution workflow. The current implementation
uses synthetic 30-minute Woodies bars and must be treated as legacy until the
5-minute migration is complete.

## Impact

| Area | Current | Target |
|------|---------|--------|
| DLL export | `woodies_30min.json` | `woodies_5min.json` |
| Bridge stream | `woodies_30min` | `woodies_5min` |
| Backend subscription | `WoodiesSystem.subscribed_bar_types()` returns `woodies_30min` | returns `woodies_5min` |
| DB table | `v9_bars_30min_woodies` | `v9_bars_5min_woodies` or unified `v9_bars_5min` with Woodies fields |
| UI labels | "30-min" | "5-min" |
| Docs/spec references | 30-minute synthetic bars | 5-minute Woodies bars |

## Migration Rule

Do **not** continue building new S4 execution behavior against `woodies_30min`
unless the task is explicitly marked as legacy compatibility. New Woodies work
must either use 5-minute naming or include an impact note explaining why it is
temporarily still on 30-minute data.

## Safety Notes

- This decision does not enable SHADOW, DEMO, or LIVE.
- Sierra/DLL changes require a separate deploy task and manual Sierra validation.
- The 30-minute references in Day Type, TPO letters, cooldown, and other non-S4
  contexts are not automatically wrong; D-074 applies to **S4 Woodies runtime**.

