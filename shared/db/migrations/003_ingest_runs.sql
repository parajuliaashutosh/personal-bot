CREATE TABLE IF NOT EXISTS ingest_runs (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    triggered_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at TIMESTAMPTZ,
    status       TEXT NOT NULL DEFAULT 'running',  -- running | completed | failed
    file_names   TEXT[]   NOT NULL DEFAULT '{}',
    doc_count    INT      NOT NULL DEFAULT 0,
    chunk_count  INT      NOT NULL DEFAULT 0,
    error        TEXT
);

CREATE INDEX IF NOT EXISTS ingest_runs_triggered_idx ON ingest_runs (triggered_at DESC);
