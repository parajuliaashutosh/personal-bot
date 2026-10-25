CREATE MATERIALIZED VIEW IF NOT EXISTS admin_overview_mv AS
SELECT
  1 AS id,
  (SELECT count(*) FROM sessions) AS sessions,
  (SELECT count(*) FROM sessions WHERE last_active > now() - interval '24 hours') AS sessions_24h,
  (SELECT count(*) FROM messages) AS messages,
  (SELECT count(*) FROM messages WHERE created_at > now() - interval '24 hours') AS messages_24h,
  (SELECT count(*) FROM messages WHERE is_partial AND role = 'assistant') AS partial_messages,
  (SELECT count(*) FROM error_logs WHERE occurred_at > now() - interval '24 hours' AND NOT recovered) AS unrecovered_errors_24h,
  (SELECT count(*) FROM error_logs WHERE occurred_at > now() - interval '24 hours') AS errors_24h,
  (SELECT count(*) FROM documents WHERE status = 'ready') AS documents_ready,
  (SELECT count(*) FROM chunks) AS chunks,
  now() AS refreshed_at;

CREATE UNIQUE INDEX IF NOT EXISTS admin_overview_mv_id ON admin_overview_mv (id);
