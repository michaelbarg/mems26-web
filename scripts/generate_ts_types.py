#!/usr/bin/env python3
"""Generate TypeScript event types from registry.yaml.

Usage: python scripts/generate_ts_types.py
Output: frontend/v9/src/v9/types/events.ts
"""

import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
REGISTRY = REPO_ROOT / "backend" / "v9" / "event_bus" / "schemas" / "registry.yaml"
OUTPUT = REPO_ROOT / "frontend" / "v9" / "src" / "v9" / "types" / "events.ts"

TYPE_MAP = {
    "float": "number",
    "int": "number",
    "str": "string",
    "bool": "boolean",
    "list": "unknown[]",
    "dict": "Record<string, unknown>",
}


def to_interface_name(event_type: str) -> str:
    """price.tick -> PriceTickEvent"""
    parts = event_type.split(".")
    return "".join(p.capitalize() for p in parts) + "Event"


def generate(registry: dict) -> str:
    lines = [
        "// Auto-generated from registry.yaml — do not edit manually",
        "// Run: python scripts/generate_ts_types.py",
        "",
        "export interface BaseEvent {",
        "  event_type: string;",
        "  correlation_id: string;",
        "  ts_ms: number;",
        "  source: string;",
        "  version: string;",
        "}",
        "",
    ]

    for event_type, spec in registry["events"].items():
        name = to_interface_name(event_type)
        lines.append(f"/** {spec.get('description', '')} */")
        lines.append(f"export interface {name} extends BaseEvent {{")
        lines.append(f'  event_type: "{event_type}";')
        for field_name, field_spec in spec.get("fields", {}).items():
            ts_type = TYPE_MAP.get(field_spec["type"], "unknown")
            optional = "" if field_spec.get("required") else "?"
            lines.append(f"  {field_name}{optional}: {ts_type};")
        lines.append("}")
        lines.append("")

    # Union type of all events
    event_names = [to_interface_name(et) for et in registry["events"]]
    lines.append("export type MemsEvent = " + " | ".join(event_names) + ";")
    lines.append("")

    # Channel map
    lines.append("export const EVENT_CHANNELS = {")
    for event_type, spec in registry["events"].items():
        channel = spec.get("channel", "")
        key = event_type.replace(".", "_").upper()
        lines.append(f'  {key}: "{channel}",')
    lines.append("} as const;")
    lines.append("")

    return "\n".join(lines)


def main():
    if not REGISTRY.exists():
        print(f"ERROR: {REGISTRY} not found", file=sys.stderr)
        sys.exit(1)

    with open(REGISTRY) as f:
        registry = yaml.safe_load(f)

    ts_code = generate(registry)

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(ts_code)
    print(f"Generated {OUTPUT} ({len(registry['events'])} event types)")


if __name__ == "__main__":
    main()
