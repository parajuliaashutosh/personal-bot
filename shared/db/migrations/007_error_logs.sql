-- Central error log. Written by the API on any failure that the user can feel:
-- a broken LLM stream, a failed retrieval step, an unhandled HTTP error.
CREATE TABLE IF NOT EXISTS error_logs (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    occurred_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    scope        TEXT NOT NULL,                 -- chat_stream | llm_provider | retrieval | http | ingest
    code         TEXT NOT NULL,                 -- shared.errors constant
    message      TEXT NOT NULL,
    exc_type     TEXT,
    provider     TEXT,                          -- openrouter | github_models | gemini | ollama
    attempt      INT  NOT NULL DEFAULT 0,       -- 0-based retry attempt that failed
    recovered    BOOLEAN NOT NULL DEFAULT FALSE,-- true = a retry/fallback rescued the request
    session_id   UUID REFERENCES sessions(id) ON DELETE SET NULL,
    path         TEXT,
    status_code  INT,
    partial_len  INT,                           -- chars already streamed when the stream broke
    context      JSONB NOT NULL DEFAULT '{}',
    stack        TEXT
);

CREATE INDEX IF NOT EXISTS error_logs_occurred_idx ON error_logs (occurred_at DESC);
CREATE INDEX IF NOT EXISTS error_logs_code_idx     ON error_logs (code, occurred_at DESC);
CREATE INDEX IF NOT EXISTS error_logs_session_idx  ON error_logs (session_id, occurred_at DESC);
CREATE INDEX IF NOT EXISTS error_logs_unrecovered_idx
    ON error_logs (occurred_at DESC) WHERE NOT recovered;

-- A half-streamed answer must not look like a clean one in history.
ALTER TABLE messages ADD COLUMN IF NOT EXISTS is_partial BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE messages ADD COLUMN IF NOT EXISTS error_code TEXT;
