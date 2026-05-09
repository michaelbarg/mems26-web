-- V9_006: System visual markers for chart overlay
-- Source: All systems — chart annotation markers

CREATE TABLE IF NOT EXISTS v9_system_markers (
    id              BIGSERIAL PRIMARY KEY,
    ts              TIMESTAMP WITH TIME ZONE NOT NULL,
    system_id       INTEGER NOT NULL,
    marker_type     VARCHAR(30) NOT NULL,      -- ARROW, LINE, BOX, LABEL, ZONE
    price           DOUBLE PRECISION,
    color           VARCHAR(20),               -- hex or named color
    label           VARCHAR(100),
    border_style    VARCHAR(20),               -- solid, dashed, dotted
    payload         JSONB,
    created_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_v9_markers_system_ts ON v9_system_markers (system_id, ts);
CREATE INDEX IF NOT EXISTS idx_v9_markers_ts ON v9_system_markers (ts);
CREATE INDEX IF NOT EXISTS idx_v9_markers_type ON v9_system_markers (marker_type);
