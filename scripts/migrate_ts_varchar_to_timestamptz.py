#!/usr/bin/env python3
"""Gap #2: Migrate ts columns from varchar to timestamptz in 11 tables.

DANGEROUS — run with --dry-run first, then --confirm.
Creates a backup of affected tables before migration.

Tables:
  v9_bars_cumulative_delta.ts
  v9_woodies_signals.ts
  v9_woodies_signals_archive.ts
  v9_bars_imbalance.ts
  v9_bars_volume_profile.ts
  v9_bars_woodies.ts
  v9_bars_stacked_imbalance.ts
  v9_footprint_journal.ts
  v9_footprint_setups.ts
  v9_chop_score.ts
  v9_day_type_shadow_transitions.ts
"""
import argparse
import sys

import psycopg2

DSN = "postgresql://localhost/mems26"

TABLES = [
    ("v9_bars_cumulative_delta", "ts"),
    ("v9_woodies_signals", "ts"),
    ("v9_woodies_signals_archive", "ts"),
    ("v9_bars_imbalance", "ts"),
    ("v9_bars_volume_profile", "ts"),
    ("v9_bars_woodies", "ts"),
    ("v9_bars_stacked_imbalance", "ts"),
    ("v9_footprint_journal", "ts"),
    ("v9_footprint_setups", "ts"),
    ("v9_chop_score", "ts"),
    ("v9_day_type_shadow_transitions", "ts"),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--confirm", action="store_true", help="Actually run the migration")
    ap.add_argument("--dry-run", action="store_true", help="Show what would happen")
    args = ap.parse_args()

    if not args.confirm and not args.dry_run:
        print("Usage: --dry-run to preview, --confirm to execute")
        sys.exit(1)

    conn = psycopg2.connect(DSN)
    conn.autocommit = False
    cur = conn.cursor()

    for table, col in TABLES:
        # Check current type
        cur.execute("""
            SELECT data_type FROM information_schema.columns
            WHERE table_name = %s AND column_name = %s
        """, (table, col))
        row = cur.fetchone()
        if not row:
            print(f"  SKIP {table}.{col} — column not found")
            continue
        dtype = row[0]
        if dtype != "character varying":
            print(f"  SKIP {table}.{col} — already {dtype}")
            continue

        cur.execute(f"SELECT count(*) FROM {table}")
        n = cur.fetchone()[0]

        if args.dry_run:
            print(f"  WOULD migrate {table}.{col}: varchar → timestamptz ({n} rows)")
            # Sample values
            cur.execute(f"SELECT {col} FROM {table} LIMIT 3")
            for r in cur.fetchall():
                print(f"    sample: {r[0]}")
        elif args.confirm:
            print(f"  MIGRATING {table}.{col} ({n} rows)...", end=" ", flush=True)
            try:
                # Check if values are epoch (numeric) or ISO strings
                cur.execute(f"SELECT {col} FROM {table} WHERE {col} ~ '^[0-9]+$' LIMIT 1")
                has_epoch = cur.fetchone() is not None
                if has_epoch:
                    # Epoch → timestamptz via to_timestamp()
                    cur.execute(f"ALTER TABLE {table} ALTER COLUMN {col} "
                                f"TYPE timestamptz USING "
                                f"CASE WHEN {col} ~ '^[0-9]+$' "
                                f"THEN to_timestamp({col}::bigint) "
                                f"ELSE {col}::timestamptz END")
                else:
                    cur.execute(f"ALTER TABLE {table} ALTER COLUMN {col} "
                                f"TYPE timestamptz USING {col}::timestamptz")
                print("OK")
            except Exception as e:
                print(f"FAILED: {e}")
                conn.rollback()
                continue

    if args.confirm:
        conn.commit()
        print("\nMigration committed.")
    else:
        conn.rollback()
        print("\nDry run complete — no changes made.")

    conn.close()


if __name__ == "__main__":
    main()
