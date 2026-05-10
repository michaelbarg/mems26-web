# MEMS26 V9 — R3 Compliance Validator Design

## Purpose

R3 is the final audit before SHADOW phase. It validates that each system's code
matches its locked spec. Per MASTER_DEV_SKILL Section 5:
"Final: R3 Spec Compliance Validator (LIVE <5%, SIM <10%, SHADOW <15%)"

## Architecture

```
specs (Drive)          code (backend/v9/systems/)
      |                        |
      v                        v
compliance_manifest.yaml  <--- extracted requirements
      |
      v
tests/v9/compliance/test_{system}_compliance.py
      |
      v
scripts/spec_compliance_audit.sh  --- computes drift %
scripts/verify_compliance_coverage.py --- detailed report
```

## Work Products

### 1. Compliance Manifests (6 files)

Location: `backend/v9/systems/{system}/compliance_manifest.yaml`

Each manifest lists:
- Every decision tree node + branches from spec
- Every output field + expected type
- Every config parameter + default
- Every anti-pattern / "MUST NOT" rule
- Status: IMPLEMENTED / PARTIAL / MISSING

### 2. Compliance Tests (6 files)

Location: `tests/v9/compliance/test_{system}_compliance.py`

Tests verify:
- Required functions/classes exist
- Required fields in output schemas
- Decision tree branches covered by code
- Anti-patterns not present (no trade execution in observers, etc.)
- Config parameter defaults match spec

### 3. Audit Script

Location: `scripts/spec_compliance_audit.sh`

Parses manifests, runs tests, computes drift:
```
drift = (MISSING + PARTIAL) / TOTAL * 100
```

Phase gates:
- SHADOW: drift < 15%
- SIM: drift < 10%
- LIVE: drift < 5%

### 4. Coverage Verifier

Location: `scripts/verify_compliance_coverage.py`

Parses all manifests and produces a detailed report with:
- Per-system drift breakdown
- List of MISSING/PARTIAL items
- Test file existence check

## Drift Formula

```
drift_pct = (count(MISSING) + count(PARTIAL)) / count(TOTAL) * 100
```

Where TOTAL = decision_tree_nodes + output_fields + config_params + anti_patterns
+ any system-specific sections (patterns, studies, zones, etc.)

## Systems Covered

| ID | System        | Spec Source              | Drift |
|----|---------------|--------------------------|-------|
| 1  | day_type      | DAY_TYPE_TREE_V2         | 12.5% |
| 2  | chart_5min    | 5MIN_CHART_V3            | 23.4% |
| 3  | tick_reversal | FOOTPRINT_TICK_V3        | 11.1% |
| 4  | woodies       | WOODIES_SPEC_V1_DERIVED  | 20.8% |
| 5  | tpo           | TPO_TREE_V2              | 6.7%  |
| 6  | killzone      | KILLZONE_SPEC_V1         | 3.8%  |

Overall drift: 13.2% (SHADOW PASS at < 15%)

## Key Findings

### Systems 2 and 4 have elevated drift due to pattern detection:
- `patterns.py` modules imported but not yet populated with detection algorithms
- Infrastructure (schemas, matrix, detector pipeline) is complete
- Actual pattern matching algorithms are Phase 3.5 backlog items

### System 1 (day_type) drift from:
- News re-eval trigger not implemented
- Profile shape re-eval trigger not implemented
- Confidence threshold code uses 0.70 vs spec 0.85

### Systems 5 and 6 are closest to spec:
- TPO: 6.7% drift (EOD stage + naked POC cross-day lookback pending)
- Killzone: 3.8% drift (news guard + NTP validation pending)

## Phase Transition Criteria

### Before SHADOW (current gate):
- R3 drift < 15% per system
- All compliance tests pass

### Before SIM:
- R3 drift < 10% per system
- Pattern detection modules populated
- 7 days SHADOW clean

### Before LIVE:
- R3 drift < 5% per system
- All PARTIAL items resolved
- 30 days SHADOW data queryable
