# MEMS26 Registry Design

## Purpose

MEMS26_REGISTRY.yaml is the single source of truth for all V9 requirements. It bridges the gap between LOCKED Drive specs and actual implementation status, enabling automated tracking of what is specified, what is built, and what is blocking phase transitions.

## Schema

Each entry follows a fixed schema with fields: id, name, category, severity, source, status, owner_worker, code_path, test_path, last_verified, notes.

## Categories

| Prefix | Scope |
|--------|-------|
| REQ-S | System decision trees, patterns, signals, trading modes |
| REQ-DATA | Data collection, snapshots, predictions |
| REQ-ADMIN | Admin console, overrides, operator tools |
| REQ-UI | Dashboard layout, tabs, panels, interactions |
| REQ-EXPLAIN | Tooltips, narratives, post-mortems, glossary |
| REQ-INFRA | DLL, Bridge, Backend, Render, latency, credentials |
| REQ-GOVERN | Policies, principles, phase gates |

## Status Lifecycle

SPECIFIED -> IN_PROGRESS -> IMPLEMENTED -> VERIFIED -> LIVE -> ARCHIVED

## Audit

Run `scripts/registry_audit.sh` to check health: category/status/severity distribution, unowned SPECIFIED items, CRITICAL blockers, duplicate IDs, and missing test paths.

## Sources

Bootstrap drew from 9 LOCKED Drive docs, 6 compliance manifests, R3 drift report, and V-Audit findings documented in MASTER_DEV_SKILL.md.
