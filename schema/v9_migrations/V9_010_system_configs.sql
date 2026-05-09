-- V9_010: System configs — per-system, per-mode configuration with locking

CREATE TABLE IF NOT EXISTS v9_system_configs (
    id          BIGSERIAL PRIMARY KEY,
    system_id   INTEGER NOT NULL,
    mode        VARCHAR(10) NOT NULL,       -- SHADOW, SIM, LIVE
    params      JSONB NOT NULL DEFAULT '{}',
    locked_at   TIMESTAMP WITH TIME ZONE,
    locked_by   VARCHAR(50),
    created_at  TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at  TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_v9_configs_unique ON v9_system_configs (system_id, mode);
