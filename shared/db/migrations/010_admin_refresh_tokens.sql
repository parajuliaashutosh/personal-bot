CREATE TABLE IF NOT EXISTS admin_refresh_tokens (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID NOT NULL REFERENCES admin_users(id) ON DELETE CASCADE,
    family_id   UUID NOT NULL,
    token_hash  TEXT NOT NULL UNIQUE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at  TIMESTAMPTZ NOT NULL,
    revoked_at  TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS admin_refresh_tokens_family ON admin_refresh_tokens (family_id);
CREATE INDEX IF NOT EXISTS admin_refresh_tokens_user ON admin_refresh_tokens (user_id);
