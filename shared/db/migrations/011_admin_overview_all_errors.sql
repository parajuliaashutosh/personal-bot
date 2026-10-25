-- Overview now covers the whole error log, not just the last 24 hours.
-- scope = 'client' rows are handled 4xx responses (404, 401, ...); they are
-- counted separately so bot noise does not inflate the unrecovered numbers.
DROP MATERIALIZED VIEW IF EXISTS admin_overview_mv;

CREATE MATERIALIZED VIEW admin_overview_mv AS
SELECT
  1 AS id,
  (SELECT count(*) FROM sessions) AS sessions,
  (SELECT count(*) FROM sessions WHERE last_active > now() - interval '24 hours') AS sessions_24h,
  (SELECT count(*) FROM messages) AS messages,
  (SELECT count(*) FROM messages WHERE created_at > now() - interval '24 hours') AS messages_24h,
  (SELECT count(*) FROM messages WHERE is_partial AND role = 'assistant') AS partial_messages,
  (SELECT count(*) FROM error_logs) AS errors_total,
  (SELECT count(*) FROM error_logs WHERE NOT recovered AND scope <> 'client') AS unrecovered_errors_total,
  (SELECT count(*) FROM error_logs WHERE scope = 'client') AS client_errors_total,
  (SELECT count(*) FROM error_logs WHERE occurred_at > now() - interval '24 hours') AS errors_24h,
  (SELECT count(*) FROM error_logs WHERE occurred_at > now() - interval '24 hours' AND NOT recovered AND scope <> 'client') AS unrecovered_errors_24h,
  (SELECT count(*) FROM error_logs WHERE occurred_at > now() - interval '24 hours' AND scope = 'client') AS client_errors_24h,
  (SELECT max(occurred_at) FROM error_logs) AS last_error_at,
  (SELECT coalesce(jsonb_object_agg(scope, n), '{}'::jsonb)
     FROM (SELECT scope, count(*) AS n FROM error_logs GROUP BY scope) s) AS errors_by_scope,
  (SELECT count(*) FROM documents WHERE status = 'ready') AS documents_ready,
  (SELECT count(*) FROM chunks) AS chunks,
  now() AS refreshed_at;

CREATE UNIQUE INDEX IF NOT EXISTS admin_overview_mv_id ON admin_overview_mv (id);
